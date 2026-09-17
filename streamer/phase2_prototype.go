package main

import (
	"bufio"
	"context"
	"encoding/hex"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/gotd/td/session"
	"github.com/gotd/td/telegram"
	"github.com/gotd/td/tg"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
)

// readEnvFile parses a basic .env file into key-value pairs
func readEnvFile(path string) map[string]string {
	env := make(map[string]string)
	f, err := os.Open(path)
	if err != nil {
		return env
	}
	defer f.Close()

	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		parts := strings.SplitN(line, "=", 2)
		if len(parts) == 2 {
			key := strings.TrimSpace(parts[0])
			val := strings.TrimSpace(parts[1])
			val = strings.Trim(val, `"'`)
			env[key] = val
		}
	}
	return env
}

func main() {
	fmt.Println("================================================================================")
	fmt.Println(" CINEFORGE GO STREAMER: PHASE 1 & PHASE 2 VERIFICATION PROTOTYPE")
	fmt.Println("================================================================================")

	// 1. Locate and load credentials
	currentDir, _ := os.Getwd()
	backendEnvPath := filepath.Join(currentDir, "..", "backend", ".env")
	if _, err := os.Stat(backendEnvPath); os.IsNotExist(err) {
		backendEnvPath = filepath.Join(currentDir, "backend", ".env")
	}

	envVars := readEnvFile(backendEnvPath)

	apiIDStr := os.Getenv("TELEGRAM_API_ID")
	if apiIDStr == "" {
		apiIDStr = envVars["TELEGRAM_API_ID"]
	}
	apiHash := os.Getenv("TELEGRAM_API_HASH")
	if apiHash == "" {
		apiHash = envVars["TELEGRAM_API_HASH"]
	}

	// Read session string
	sessionStr := os.Getenv("TELEGRAM_SESSION_STRING")
	if sessionStr == "" {
		sessionPath := filepath.Join(currentDir, "session.txt")
		if data, err := os.ReadFile(sessionPath); err == nil {
			sessionStr = strings.TrimSpace(string(data))
		}
	}

	if apiIDStr == "" || apiHash == "" || sessionStr == "" {
		fmt.Printf("ERROR: Missing credentials.\n  API_ID: %t\n  API_HASH: %t\n  SESSION_STRING: %t\n",
			apiIDStr != "", apiHash != "", sessionStr != "")
		os.Exit(1)
	}

	apiID, err := strconv.Atoi(apiIDStr)
	if err != nil {
		fmt.Printf("ERROR: Invalid TELEGRAM_API_ID '%s': %v\n", apiIDStr, err)
		os.Exit(1)
	}

	// Target file parameters (default: Saved Messages, msg_id = 9763)
	targetChat := "me"
	targetMsgID := 9763

	if len(os.Args) > 1 {
		targetChat = os.Args[1]
	}
	if len(os.Args) > 2 {
		if id, err := strconv.Atoi(os.Args[2]); err == nil {
			targetMsgID = id
		}
	}

	fmt.Printf("[Config] Telegram API_ID: %d\n", apiID)
	fmt.Printf("[Config] Telegram API_HASH: %s...%s\n", apiHash[:4], apiHash[len(apiHash)-4:])
	fmt.Printf("[Config] Session String: loaded (%d characters)\n", len(sessionStr))
	fmt.Printf("[Target] Chat Target: '%s', Message ID: %d\n\n", targetChat, targetMsgID)

	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	// Configure logger: suppress noisy MTProto debug logs, keep warnings and errors
	encoderConfig := zap.NewDevelopmentEncoderConfig()
	encoderConfig.EncodeLevel = zapcore.CapitalColorLevelEncoder
	core := zapcore.NewCore(
		zapcore.NewConsoleEncoder(encoderConfig),
		zapcore.AddSync(os.Stdout),
		zap.WarnLevel, // only show warnings/errors from gotd internals
	)
	log := zap.New(core)

	// Decode Telethon Session
	sessionData, err := session.TelethonSession(sessionStr)
	if err != nil {
		fmt.Printf("ERROR: Failed to decode Telethon session: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("[Phase 1.1] Decoded Session: Primary DC=%d, Address=%s\n", sessionData.DC, sessionData.Addr)

	storage := &session.StorageMemory{}
	loader := session.Loader{Storage: storage}
	if err := loader.Save(ctx, sessionData); err != nil {
		fmt.Printf("ERROR: Failed to save session to memory storage: %v\n", err)
		os.Exit(1)
	}

	client := telegram.NewClient(apiID, apiHash, telegram.Options{
		SessionStorage: storage,
		Logger:         log.Named("gotd"),
	})

	// Run client and execute test inside
	runErr := client.Run(ctx, func(ctx context.Context) error {
		// Verify Connection and Self
		self, err := client.Self(ctx)
		if err != nil {
			return fmt.Errorf("client.Self failed: %w", err)
		}

		userDisplay := self.FirstName
		if self.Username != "" {
			userDisplay += fmt.Sprintf(" (@%s)", self.Username)
		}
		fmt.Printf("[Phase 1.2] MTProto Connected! Authorized as: %s (User ID: %d, Phone: +%s)\n",
			userDisplay, self.ID, self.Phone)

		api := client.API()

		// Phase 2: Resolve Document
		fmt.Printf("\n[Phase 2.1] Resolving document for chat='%s', msg_id=%d...\n", targetChat, targetMsgID)
		resolveStart := time.Now()

		res, err := api.MessagesGetMessages(ctx, []tg.InputMessageClass{
			&tg.InputMessageID{ID: targetMsgID},
		})
		if err != nil {
			return fmt.Errorf("MessagesGetMessages failed: %w", err)
		}
		resolveDuration := time.Since(resolveStart)

		var msg *tg.Message
		switch r := res.(type) {
		case *tg.MessagesMessages:
			if len(r.Messages) > 0 {
				if m, ok := r.Messages[0].(*tg.Message); ok {
					msg = m
				}
			}
		case *tg.MessagesMessagesSlice:
			if len(r.Messages) > 0 {
				if m, ok := r.Messages[0].(*tg.Message); ok {
					msg = m
				}
			}
		case *tg.MessagesChannelMessages:
			if len(r.Messages) > 0 {
				if m, ok := r.Messages[0].(*tg.Message); ok {
					msg = m
				}
			}
		default:
			return fmt.Errorf("unexpected Messages response type: %T", res)
		}

		if msg == nil {
			return fmt.Errorf("message %d not found in chat '%s'", targetMsgID, targetChat)
		}

		mediaDoc, ok := msg.Media.(*tg.MessageMediaDocument)
		if !ok || mediaDoc.Document == nil {
			return fmt.Errorf("message %d exists but does not contain a document media", targetMsgID)
		}

		doc, ok := mediaDoc.Document.AsNotEmpty()
		if !ok {
			return fmt.Errorf("message %d contains an empty document", targetMsgID)
		}

		fileName := "unnamed_media"
		for _, attr := range doc.Attributes {
			if fName, ok := attr.(*tg.DocumentAttributeFilename); ok {
				fileName = fName.FileName
				break
			}
		}

		fileSizeMB := float64(doc.Size) / (1024 * 1024)
		refHex := hex.EncodeToString(doc.FileReference)
		if len(refHex) > 32 {
			refHex = refHex[:32] + "..."
		}

		fmt.Println("[Phase 2.2] Document Metadata Extracted Successfully:")
		fmt.Printf("  • File Name:       %s\n", fileName)
		fmt.Printf("  • Document ID:     %d\n", doc.ID)
		fmt.Printf("  • Access Hash:     %d\n", doc.AccessHash)
		fmt.Printf("  • File Reference:  %s (%d bytes)\n", refHex, len(doc.FileReference))
		fmt.Printf("  • File Size:       %d bytes (%.2f MB)\n", doc.Size, fileSizeMB)
		fmt.Printf("  • MIME Type:       %s\n", doc.MimeType)
		fmt.Printf("  • Document DC ID:  %d (Primary Auth DC: %d)\n", doc.DCID, sessionData.DC)
		fmt.Printf("  • Resolution Time: %.2f ms\n", float64(resolveDuration.Microseconds())/1000.0)

		// Phase 2.3: Perform ONE aligned 1 MB file download
		chunkSize := 1024 * 1024 // 1 MB
		location := doc.AsInputDocumentFileLocation()

		fmt.Printf("\n[Phase 2.3] Requesting 1 MB block (offset=0, limit=%d bytes, precise=true)...\n", chunkSize)
		t0 := time.Now()

		req := &tg.UploadGetFileRequest{
			Location: location,
			Offset:   0,
			Limit:    chunkSize,
		}
		req.SetPrecise(true)

		uploadRes, err := api.UploadGetFile(ctx, req)
		dur := time.Since(t0)

		if err != nil {
			return fmt.Errorf("UploadGetFile failed: %w", err)
		}

		uploadFile, ok := uploadRes.(*tg.UploadFile)
		if !ok {
			return fmt.Errorf("unexpected UploadGetFile response type: %T", uploadRes)
		}

		receivedBytes := len(uploadFile.Bytes)
		latencyMs := float64(dur.Microseconds()) / 1000.0
		durSec := dur.Seconds()
		throughputMBps := (float64(receivedBytes) / (1024 * 1024)) / durSec
		throughputMbps := (float64(receivedBytes) * 8 / 1_000_000) / durSec

		// Verify byte content signature
		sigPreview := hex.EncodeToString(uploadFile.Bytes[:min(16, receivedBytes)])

		fmt.Println("[Phase 2.4] 1 MB Download Succeeded!")
		fmt.Printf("  • Bytes Received:     %d bytes (%.2f MB)\n", receivedBytes, float64(receivedBytes)/(1024*1024))
		fmt.Printf("  • Request Latency:    %.2f ms (%.3f s)\n", latencyMs, durSec)
		fmt.Printf("  • Measured Speed:     %.2f MB/s (%.2f Mbps)\n", throughputMBps, throughputMbps)
		fmt.Printf("  • Header Magic Hex:   %s\n", sigPreview)
		fmt.Printf("  • Memory Stored:      true (buffer held in memory, zero disk I/O)\n")

		return nil
	})

	if runErr != nil {
		fmt.Printf("\n[FAILURE] Prototype execution encountered an error:\n%v\n", runErr)
		os.Exit(1)
	}

	fmt.Println("\n================================================================================")
	fmt.Println(" [SUCCESS] PHASE 1 & PHASE 2 VERIFICATION COMPLETED CLEANLY")
	fmt.Println("================================================================================")
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
