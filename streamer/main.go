package main

import (
	"context"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"syscall"
	"time"

	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
)

var (
	appLogger   *zap.Logger
	telegramSvc *TelegramService
)

func main() {
	fmt.Println("================================================================================")
	fmt.Println(" CINEFORGE NATIVE GO STREAMER (gotd/td)")
	fmt.Println("================================================================================")

	// Configure structured zap logger
	encoderConfig := zap.NewDevelopmentEncoderConfig()
	encoderConfig.EncodeLevel = zapcore.CapitalColorLevelEncoder
	core := zapcore.NewCore(
		zapcore.NewConsoleEncoder(encoderConfig),
		zapcore.AddSync(os.Stdout),
		zap.InfoLevel,
	)
	appLogger = zap.New(core)
	defer appLogger.Sync()

	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer cancel()

	// 1. Initialize persistent Telegram MTProto service
	appLogger.Info("Initializing Telegram MTProto background service...")
	var err error
	telegramSvc, err = NewTelegramService(ctx, appLogger)
	if err != nil {
		appLogger.Fatal("Failed to initialize Telegram service", zap.Error(err))
	}
	defer telegramSvc.Close()

	host := os.Getenv("HOST")
	if host == "" {
		host = "0.0.0.0"
	}

	port := os.Getenv("PORT")
	if port == "" {
		port = "8088"
	}

	listenAddr := net.JoinHostPort(host, port)

	// 2. Register HTTP routes
	mux := http.NewServeMux()
	mux.HandleFunc("/health", handleHealth)
	mux.HandleFunc("/stream/", handleStream)

	server := &http.Server{
		Addr:    listenAddr,
		Handler: withCORS(mux),
	}

	appLogger.Info("CineForge Go Streamer ready",
		zap.String("addr", "http://"+listenAddr),
		zap.String("health", "http://"+listenAddr+"/health"),
		zap.String("stream_pattern", "http://"+listenAddr+"/stream/{chat_id}/{message_id}"),
	)

	serverErr := make(chan error, 1)
	go func() {
		serverErr <- server.ListenAndServe()
	}()

	select {
	case err := <-serverErr:
		if !errors.Is(err, http.ErrServerClosed) {
			appLogger.Fatal("HTTP server error", zap.Error(err))
		}
	case <-ctx.Done():
		appLogger.Info("Shutting down streamer server gracefully...")
		shutdownCtx, sCancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer sCancel()
		_ = server.Shutdown(shutdownCtx)
	}

	appLogger.Info("Streamer service stopped.")
}

func handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write([]byte(`{"status":"healthy","service":"cineforge-streamer","engine":"gotd/td"}`))
}

func handleStream(w http.ResponseWriter, r *http.Request) {
	// Expected path: /stream/{chat}/{message_id}
	pathParts := strings.Split(strings.Trim(r.URL.Path, "/"), "/")
	if len(pathParts) < 3 {
		http.Error(w, "invalid stream path format. Expected: /stream/{chat_id}/{message_id}", http.StatusBadRequest)
		return
	}

	chatTarget := pathParts[1]
	messageID, err := strconv.Atoi(pathParts[2])
	if err != nil || messageID <= 0 {
		http.Error(w, "invalid message ID", http.StatusBadRequest)
		return
	}

	// 1. Verify stream token authorization if configured
	if ok, reason := VerifyStreamRequest(r, chatTarget, messageID); !ok {
		http.Error(w, "unauthorized: "+reason, http.StatusUnauthorized)
		return
	}

	reqCtx := r.Context()

	// 2. Resolve document metadata from Telegram
	doc, err := telegramSvc.ResolveDocument(reqCtx, chatTarget, messageID)
	if err != nil {
		appLogger.Warn("Failed to resolve document",
			zap.String("chat", chatTarget),
			zap.Int("msg_id", messageID),
			zap.Error(err),
		)
		http.Error(w, "document not found: "+err.Error(), http.StatusNotFound)
		return
	}

	fileSize := doc.Size
	rangeHeader := r.Header.Get("Range")

	// 3. Parse RFC 7233 Range header
	byteRange, isPartial, err := ParseRange(rangeHeader, fileSize)
	if err != nil {
		w.Header().Set("Content-Range", fmt.Sprintf("bytes */%d", fileSize))
		http.Error(w, err.Error(), http.StatusRequestedRangeNotSatisfiable)
		return
	}

	var start, end int64
	if isPartial && byteRange != nil {
		start = byteRange.Start
		end = byteRange.End
		SetRangeResponseHeaders(w, byteRange, fileSize, doc.MimeType, doc.FileName)
		w.WriteHeader(http.StatusPartialContent)
	} else {
		// Full file / direct request
		start = 0
		end = fileSize - 1
		fullRange := &ByteRange{Start: 0, End: end, Length: fileSize}
		SetRangeResponseHeaders(w, fullRange, fileSize, doc.MimeType, doc.FileName)
		w.WriteHeader(http.StatusOK)
	}

	// If HEAD request, headers are already written
	if r.Method == http.MethodHead {
		return
	}

	// 4. Construct StreamPipe over MTProto connection
	pipe, err := NewStreamPipe(reqCtx, telegramSvc.API(), doc.Location, start, end, appLogger)
	if err != nil {
		appLogger.Error("Failed to initialize StreamPipe", zap.Error(err))
		http.Error(w, "internal streaming error", http.StatusInternalServerError)
		return
	}
	defer pipe.Close()

	// 5. Pipe sequential byte stream to HTTP response
	contentLength := end - start + 1
	n, copyErr := io.CopyN(w, pipe, contentLength)

	if copyErr != nil && !isClientAbort(copyErr) {
		appLogger.Warn("Stream transmission ended prematurely",
			zap.Int64("bytes_served", n),
			zap.Int64("expected_bytes", contentLength),
			zap.Error(copyErr),
		)
	}
}

// isClientAbort checks whether stream was interrupted by browser disconnect / seek.
func isClientAbort(err error) bool {
	if errors.Is(err, io.EOF) || errors.Is(err, context.Canceled) {
		return true
	}
	var netErr net.Error
	if errors.As(err, &netErr) && netErr.Timeout() {
		return true
	}
	errStr := err.Error()
	return strings.Contains(errStr, "broken pipe") ||
		strings.Contains(errStr, "connection reset by peer") ||
		strings.Contains(errStr, "wsasend") ||
		strings.Contains(errStr, "use of closed network connection")
}

// withCORS adds CORS headers and handles preflight OPTIONS requests.
func withCORS(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Range, Origin, Content-Type, Accept, Authorization")
		w.Header().Set("Access-Control-Expose-Headers", "Content-Range, Content-Length, Accept-Ranges, Content-Type")
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusOK)
			return
		}
		next.ServeHTTP(w, r)
	})
}

