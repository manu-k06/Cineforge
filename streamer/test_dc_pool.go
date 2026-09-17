package main

import (
	"context"
	"fmt"
	"os"
	"strconv"
	"sync"
	"time"

	"github.com/gotd/log/logzap"
	"github.com/gotd/td/session"
	"github.com/gotd/td/telegram"
	"github.com/gotd/td/tg"
	"go.uber.org/zap"
)

func main() {
	if len(os.Args) < 4 {
		fmt.Println("Usage: go run test_dc_pool.go <api_id> <api_hash> <session_str>")
		return
	}

	apiID, _ := strconv.Atoi(os.Args[1])
	apiHash := os.Args[2]
	sessionStr := os.Args[3]

	ctx := context.Background()
	log, _ := zap.NewDevelopment()

	sessionData, err := session.TelethonSession(sessionStr)
	if err != nil {
		fmt.Printf("ERROR: %v\n", err)
		return
	}

	storage := &session.StorageMemory{}
	loader := session.Loader{Storage: storage}
	loader.Save(ctx, sessionData)

	client := telegram.NewClient(apiID, apiHash, telegram.Options{
		SessionStorage: storage,
		Logger:         logzap.New(log.Named("gotd")),
	})

	err = client.Run(ctx, func(ctx context.Context) error {
		api := client.API()

		// 1. Resolve message 9763
		res, err := api.MessagesGetMessages(ctx, []tg.InputMessageClass{&tg.InputMessageID{ID: 9763}})
		if err != nil {
			return fmt.Errorf("failed to get message: %w", err)
		}
		msgs := res.(*tg.MessagesMessages).Messages
		doc := msgs[0].(*tg.Message).Media.(*tg.MessageMediaDocument).Document.(*tg.Document)

		fmt.Printf("File: DC=%d, Size=%d bytes (%.2f MB)\n", doc.DCID, doc.Size, float64(doc.Size)/(1024*1024))

		location := doc.AsInputDocumentFileLocation("")

		// 2. Open MediaOnly Multi-Connection Pool to doc.DCID (8 connections)
		fmt.Printf("Opening 8-connection MediaOnly pool to DC %d...\n", doc.DCID)
		pool, err := client.MediaOnly(ctx, doc.DCID, 8)
		if err != nil {
			fmt.Printf("MediaOnly pool failed, falling back to client.DC: %v\n", err)
			pool, err = client.DC(ctx, doc.DCID, 8)
			if err != nil {
				return fmt.Errorf("failed to open DC pool: %w", err)
			}
		}
		defer pool.Close()

		dcAPI := tg.NewClient(pool)

		// 3. Parallel benchmark of 16 MB using 1 MB chunks across 8 workers
		chunkSize := 1024 * 1024 // 1 MB
		numChunks := 16          // 16 MB total

		fmt.Printf("Starting parallel download of %d MB (%d x 1MB chunks) across 8 workers...\n", numChunks, numChunks)

		startT := time.Now()

		var wg sync.WaitGroup
		sem := make(chan struct{}, 8) // 8 workers
		results := make([][]byte, numChunks)
		var fetchErr error
		var mu sync.Mutex

		for i := 0; i < numChunks; i++ {
			wg.Add(1)
			go func(idx int) {
				defer wg.Done()
				sem <- struct{}{}
				defer func() { <-sem }()

				offset := int64(idx * chunkSize)
				req := &tg.UploadGetFileRequest{
					Location: location,
					Offset:   offset,
					Limit:    chunkSize,
				}
				req.SetPrecise(true)
				res, err := dcAPI.UploadGetFile(ctx, req)
				if err != nil {
					mu.Lock()
					if fetchErr == nil {
						fetchErr = err
					}
					mu.Unlock()
					return
				}

				uploadFile := res.(*tg.UploadFile)
				results[idx] = uploadFile.Bytes
			}(i)
		}

		wg.Wait()
		dur := time.Since(startT)

		if fetchErr != nil {
			return fmt.Errorf("download error: %w", fetchErr)
		}

		bytesDownloaded := 0
		for _, b := range results {
			bytesDownloaded += len(b)
		}

		sec := dur.Seconds()
		mb := float64(bytesDownloaded) / (1024 * 1024)
		mbps := (float64(bytesDownloaded) * 8) / (sec * 1_000_000)
		mbPerSec := mb / sec

		fmt.Println("==================================================")
		fmt.Printf("BENCHMARK RESULT WITH 4 PARALLEL CONNECTIONS:\n")
		fmt.Printf("Downloaded: %.2f MB in %.2f seconds\n", mb, sec)
		fmt.Printf("Speed: %.2f MB/s (%.2f Mbps)\n", mbPerSec, mbps)
		fmt.Println("==================================================")

		return nil
	})

	if err != nil {
		fmt.Printf("Error: %v\n", err)
	}
}
