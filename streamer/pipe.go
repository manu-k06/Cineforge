package main

import (
	"context"
	"errors"
	"fmt"
	"io"
	"sync"
	"time"

	"github.com/gotd/td/tg"
	"go.uber.org/zap"
)

var (
	ErrPipeClosed    = errors.New("stream pipe closed")
	ErrMaxRetries    = errors.New("maximum retries exceeded downloading block")
	ErrInvalidBounds = errors.New("invalid byte range boundaries")
)

const (
	DefaultPipeConcurrency = 1               // Sequential pipelining prevents MTProto message ID collision across DCs
	DefaultPipeQueueSize   = 8               // Maximum blocks buffered in memory for backpressure (~8 MB max)
	DefaultBlockTimeout    = 15 * time.Second // Timeout per block attempt
	DefaultMaxRetries      = 3               // Maximum retry attempts on transient failure
)

// CalculateBlockSize dynamically selects block size based on requested byte range span.
// Small ranges (e.g. metadata probes, initial seek frames) use small blocks to reduce first-byte latency.
func CalculateBlockSize(start, end int64) int64 {
	size := end - start + 1
	switch {
	case size < 512*1024: // < 512 KB
		return 64 * 1024 // 64 KB
	case size < 4*1024*1024: // < 4 MB
		return 256 * 1024 // 256 KB
	case size < 32*1024*1024: // < 32 MB
		return 512 * 1024 // 512 KB
	default:
		return 1024 * 1024 // 1 MB (Telegram MTProto maximum limit)
	}
}

// StreamPipe provides an io.ReadCloser over Telegram MTProto with concurrent prefetching and bounded backpressure.
type StreamPipe struct {
	ctx        context.Context
	cancel     context.CancelFunc
	api        *tg.Client
	location   tg.InputFileLocationClass
	start      int64
	end        int64
	totalBytes int64
	blockSize  int64

	blockQueue   chan []byte
	currentBlock []byte
	blockOffset  int64
	bytesRead    int64

	closeOnce sync.Once
	logger    *zap.Logger
}

// NewStreamPipe constructs and starts a prefetching StreamPipe.
func NewStreamPipe(
	parentCtx context.Context,
	api *tg.Client,
	location tg.InputFileLocationClass,
	start, end int64,
	logger *zap.Logger,
) (*StreamPipe, error) {
	if start > end || start < 0 {
		return nil, ErrInvalidBounds
	}

	ctx, cancel := context.WithCancel(parentCtx)
	totalBytes := end - start + 1
	blockSize := CalculateBlockSize(start, end)

	p := &StreamPipe{
		ctx:        ctx,
		cancel:     cancel,
		api:        api,
		location:   location,
		start:      start,
		end:        end,
		totalBytes: totalBytes,
		blockSize:  blockSize,
		blockQueue: make(chan []byte, DefaultPipeQueueSize),
		logger:     logger.Named("StreamPipe"),
	}

	go p.runPrefetch()

	return p, nil
}

// Read implements standard io.Reader, consuming blocks sequentially from the bounded queue.
func (p *StreamPipe) Read(buf []byte) (int, error) {
	if p.bytesRead >= p.totalBytes {
		return 0, io.EOF
	}

	if p.blockOffset >= int64(len(p.currentBlock)) {
		select {
		case block, ok := <-p.blockQueue:
			if !ok {
				if p.bytesRead >= p.totalBytes {
					return 0, io.EOF
				}
				return 0, ErrPipeClosed
			}
			p.currentBlock = block
			p.blockOffset = 0
		case <-p.ctx.Done():
			return 0, p.ctx.Err()
		}
	}

	n := copy(buf, p.currentBlock[p.blockOffset:])
	p.blockOffset += int64(n)
	p.bytesRead += int64(n)
	return n, nil
}

// Close aborts all background prefetching workers and frees queue buffers immediately.
func (p *StreamPipe) Close() error {
	p.closeOnce.Do(func() {
		p.cancel()
	})
	return nil
}

// runPrefetch drives the background batch downloader with ordered delivery and bounded backpressure.
func (p *StreamPipe) runPrefetch() {
	defer close(p.blockQueue)

	alignedStart := p.start - (p.start % p.blockSize)
	leftTrim := p.start - alignedStart
	rightTrim := (p.end % p.blockSize) + 1
	totalBlocks := int((p.end - alignedStart + p.blockSize - 1) / p.blockSize)

	currentBlock := 0
	offset := alignedStart

	for currentBlock < totalBlocks {
		select {
		case <-p.ctx.Done():
			return
		default:
		}

		batchSize := DefaultPipeConcurrency
		if totalBlocks-currentBlock < batchSize {
			batchSize = totalBlocks - currentBlock
		}

		blocks := make([][]byte, batchSize)
		var wg sync.WaitGroup
		var fetchErr error
		var errMu sync.Mutex

		for i := 0; i < batchSize; i++ {
			wg.Add(1)
			go func(idx int) {
				defer wg.Done()
				blockNum := currentBlock + idx
				blockOffset := offset + int64(idx)*p.blockSize

				data, err := p.downloadBlockWithRetry(blockOffset)
				if err != nil {
					errMu.Lock()
					if fetchErr == nil {
						fetchErr = err
					}
					errMu.Unlock()
					return
				}

				dataLen := int64(len(data))
				if totalBlocks == 1 {
					// Single block span with both left and right trim
					if dataLen < rightTrim {
						rightTrim = dataLen
					}
					if leftTrim > dataLen {
						leftTrim = dataLen
					}
					data = data[leftTrim:rightTrim]
				} else if blockNum == 0 {
					// First block in multi-block range
					if leftTrim > dataLen {
						leftTrim = dataLen
					}
					data = data[leftTrim:]
				} else if blockNum == totalBlocks-1 {
					// Last block in multi-block range
					if dataLen > rightTrim {
						data = data[:rightTrim]
					}
				}

				blocks[idx] = data
			}(i)
		}

		wg.Wait()

		if fetchErr != nil {
			if p.ctx.Err() == nil {
				p.logger.Warn("block batch fetch aborted with error", zap.Error(fetchErr))
			}
			return
		}

		// Push blocks in exact ascending order into bounded queue
		for _, b := range blocks {
			select {
			case p.blockQueue <- b:
			case <-p.ctx.Done():
				return
			}
		}

		currentBlock += batchSize
		offset += int64(batchSize) * p.blockSize
	}
}

// downloadBlockWithRetry executes UploadGetFile with exponential backoff and cancellation awareness.
func (p *StreamPipe) downloadBlockWithRetry(blockOffset int64) ([]byte, error) {
	backoff := 100 * time.Millisecond

	for attempt := 0; attempt <= DefaultMaxRetries; attempt++ {
		reqCtx, reqCancel := context.WithTimeout(p.ctx, DefaultBlockTimeout)
		req := &tg.UploadGetFileRequest{
			Location: p.location,
			Offset:   blockOffset,
			Limit:    int(p.blockSize),
		}
		req.SetPrecise(true)

		res, err := p.api.UploadGetFile(reqCtx, req)
		reqCancel()

		if err == nil {
			if uploadFile, ok := res.(*tg.UploadFile); ok {
				return uploadFile.Bytes, nil
			}
			return nil, fmt.Errorf("unexpected UploadGetFile result: %T", res)
		}

		p.logger.Warn("UploadGetFile attempt error",
			zap.Int64("offset", blockOffset),
			zap.Int64("limit", p.blockSize),
			zap.Int("attempt", attempt),
			zap.Error(err),
		)

		// Abort immediately if StreamPipe or HTTP request was canceled
		if p.ctx.Err() != nil {
			return nil, p.ctx.Err()
		}

		if attempt < DefaultMaxRetries {
			select {
			case <-time.After(backoff):
				backoff *= 2
				if backoff > 2*time.Second {
					backoff = 2 * time.Second
				}
			case <-p.ctx.Done():
				return nil, p.ctx.Err()
			}
		}
	}

	return nil, ErrMaxRetries
}
