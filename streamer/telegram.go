package main

import (
	"bufio"
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/gotd/log/logzap"
	"github.com/gotd/td/session"
	"github.com/gotd/td/telegram"
	"github.com/gotd/td/tg"
	"go.uber.org/zap"
)

// DocumentInfo encapsulates resolved metadata for a Telegram document.
type DocumentInfo struct {
	Location  *tg.InputDocumentFileLocation
	ID        int64
	Size      int64
	FileName  string
	MimeType  string
	DCID      int
	PrimaryDC int
}

// TelegramService manages a persistent gotd connection for the user account.
type TelegramService struct {
	apiID      int
	apiHash    string
	sessionStr string
	client     *telegram.Client
	api        *tg.Client
	ready      chan struct{}
	ctx        context.Context
	cancel     context.CancelFunc
	logger     *zap.Logger
	primaryDC  int
	mu         sync.RWMutex
	docCache   map[string]*DocumentInfo
	cacheMu    sync.RWMutex
}

// readEnvConfig loads credentials from backend/.env, .env, or environment variables.
func readEnvConfig() (int, string, string, error) {
	currentDir, _ := os.Getwd()
	candidatePaths := []string{
		filepath.Join(currentDir, ".env"),
		filepath.Join(currentDir, "..", "backend", ".env"),
		filepath.Join(currentDir, "backend", ".env"),
	}

	envMap := make(map[string]string)
	for _, envPath := range candidatePaths {
		if f, err := os.Open(envPath); err == nil {
			scanner := bufio.NewScanner(f)
			for scanner.Scan() {
				line := strings.TrimSpace(scanner.Text())
				if line == "" || strings.HasPrefix(line, "#") {
					continue
				}
				parts := strings.SplitN(line, "=", 2)
				if len(parts) == 2 {
					key := strings.TrimSpace(parts[0])
					if _, exists := envMap[key]; !exists {
						envMap[key] = strings.Trim(strings.TrimSpace(parts[1]), `"'`)
					}
				}
			}
			_ = f.Close()
		}
	}

	apiIDStr := os.Getenv("TELEGRAM_API_ID")
	if apiIDStr == "" {
		apiIDStr = envMap["TELEGRAM_API_ID"]
	}
	apiHash := os.Getenv("TELEGRAM_API_HASH")
	if apiHash == "" {
		apiHash = envMap["TELEGRAM_API_HASH"]
	}

	sessionStr := os.Getenv("TELEGRAM_SESSION_STRING")
	if sessionStr == "" {
		sessionPath := filepath.Join(currentDir, "session.txt")
		if data, err := os.ReadFile(sessionPath); err == nil {
			sessionStr = strings.TrimSpace(string(data))
		}
	}

	if apiIDStr == "" || apiHash == "" || sessionStr == "" {
		return 0, "", "", fmt.Errorf("missing credentials (TELEGRAM_API_ID, TELEGRAM_API_HASH, session.txt)")
	}

	apiID, err := strconv.Atoi(apiIDStr)
	if err != nil {
		return 0, "", "", fmt.Errorf("invalid TELEGRAM_API_ID: %w", err)
	}

	return apiID, apiHash, sessionStr, nil
}

// NewTelegramService initializes and starts the background MTProto daemon.
func NewTelegramService(parentCtx context.Context, logger *zap.Logger) (*TelegramService, error) {
	apiID, apiHash, sessionStr, err := readEnvConfig()
	if err != nil {
		return nil, err
	}

	sessionData, err := session.TelethonSession(sessionStr)
	if err != nil {
		return nil, fmt.Errorf("decode session: %w", err)
	}

	ctx, cancel := context.WithCancel(parentCtx)

	storage := &session.StorageMemory{}
	loader := session.Loader{Storage: storage}
	if err := loader.Save(ctx, sessionData); err != nil {
		cancel()
		return nil, fmt.Errorf("save session to storage: %w", err)
	}

	client := telegram.NewClient(apiID, apiHash, telegram.Options{
		SessionStorage: storage,
		Logger:         logzap.New(logger.Named("gotd")),
	})

	svc := &TelegramService{
		apiID:      apiID,
		apiHash:    apiHash,
		sessionStr: sessionStr,
		client:     client,
		ready:      make(chan struct{}),
		ctx:        ctx,
		cancel:     cancel,
		logger:     logger.Named("TelegramService"),
		primaryDC:  sessionData.DC,
		docCache:   make(map[string]*DocumentInfo),
	}

	go func() {
		for {
			select {
			case <-ctx.Done():
				return
			default:
			}

			err := client.Run(ctx, func(cCtx context.Context) error {
				self, err := client.Self(cCtx)
				if err != nil {
					svc.logger.Error("client.Self failed during startup", zap.Error(err))
					return err
				}

				svc.mu.Lock()
				svc.api = client.API()
				svc.mu.Unlock()

				select {
				case <-svc.ready:
				default:
					close(svc.ready)
				}

				svc.logger.Info("Telegram MTProto connection established",
					zap.String("name", self.FirstName),
					zap.Int64("id", self.ID),
					zap.Int("primary_dc", svc.primaryDC),
				)

				// Keepalive ping loop every 20 seconds to prevent Telegram server disconnect
				ticker := time.NewTicker(20 * time.Second)
				defer ticker.Stop()

				for {
					select {
					case <-cCtx.Done():
						return nil
					case <-ticker.C:
						pCtx, pCancel := context.WithTimeout(context.Background(), 5*time.Second)
						_ = client.Ping(pCtx)
						pCancel()
					}
				}
			})

			if err != nil && !errors.Is(err, context.Canceled) {
				svc.logger.Warn("Telegram client connection interrupted, reconnecting in 2s...", zap.Error(err))
				select {
				case <-ctx.Done():
					return
				case <-time.After(2 * time.Second):
				}
			}
		}
	}()

	// Wait up to 20 seconds for MTProto connection to become ready
	select {
	case <-svc.ready:
		return svc, nil
	case <-time.After(20 * time.Second):
		cancel()
		return nil, fmt.Errorf("timeout waiting for Telegram connection to establish")
	case <-parentCtx.Done():
		cancel()
		return nil, parentCtx.Err()
	}
}

// API returns the connected *tg.Client.
func (s *TelegramService) API() *tg.Client {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.api
}

// ResolveDocument fetches message and document location from Telegram with caching and retries.
func (s *TelegramService) ResolveDocument(ctx context.Context, chatTarget string, messageID int) (*DocumentInfo, error) {
	cacheKey := fmt.Sprintf("%s:%d", chatTarget, messageID)

	// 1. Check in-memory document cache first
	s.cacheMu.RLock()
	if cached, ok := s.docCache[cacheKey]; ok {
		s.cacheMu.RUnlock()
		return cached, nil
	}
	s.cacheMu.RUnlock()

	api := s.API()
	if api == nil {
		return nil, fmt.Errorf("telegram client is not ready")
	}

	var res tg.MessagesMessagesClass
	var err error

	// Retry up to 3 times with dedicated RPC timeout to guard against transient hiccups or layer reconnects
	for attempt := 1; attempt <= 3; attempt++ {
		rpcCtx, rpcCancel := context.WithTimeout(context.Background(), 15*time.Second)
		res, err = api.MessagesGetMessages(rpcCtx, []tg.InputMessageClass{
			&tg.InputMessageID{ID: messageID},
		})
		rpcCancel()

		if err == nil {
			break
		}

		s.logger.Warn("MessagesGetMessages attempt failed, retrying...",
			zap.Int("attempt", attempt),
			zap.Int("msg_id", messageID),
			zap.Error(err),
		)

		if attempt < 3 {
			time.Sleep(350 * time.Millisecond)
		}
	}

	if err != nil {
		return nil, fmt.Errorf("MessagesGetMessages failed after retries: %w", err)
	}

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
	}

	if msg == nil {
		return nil, fmt.Errorf("message %d not found in chat '%s'", messageID, chatTarget)
	}

	mediaDoc, ok := msg.Media.(*tg.MessageMediaDocument)
	if !ok || mediaDoc.Document == nil {
		return nil, fmt.Errorf("message %d does not contain document media", messageID)
	}

	doc, ok := mediaDoc.Document.AsNotEmpty()
	if !ok {
		return nil, fmt.Errorf("message %d contains empty document", messageID)
	}

	fileName := "video.mp4"
	for _, attr := range doc.Attributes {
		if fName, ok := attr.(*tg.DocumentAttributeFilename); ok {
			fileName = fName.FileName
			break
		}
	}

	mimeType := doc.MimeType
	if mimeType == "" {
		mimeType = "video/mp4"
	}

	info := &DocumentInfo{
		Location:  doc.AsInputDocumentFileLocation(""),
		ID:        doc.ID,
		Size:      doc.Size,
		FileName:  fileName,
		MimeType:  mimeType,
		DCID:      doc.DCID,
		PrimaryDC: s.primaryDC,
	}

	// Store in cache for instantaneous subsequent chunk/range serving
	s.cacheMu.Lock()
	s.docCache[cacheKey] = info
	s.cacheMu.Unlock()

	return info, nil
}

// Close disconnects the Telegram service.
func (s *TelegramService) Close() {
	s.cancel()
}
