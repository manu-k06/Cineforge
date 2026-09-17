package main

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/gotd/log/logzap"
	"github.com/gotd/td/session"
	"github.com/gotd/td/telegram"
	"github.com/gotd/td/tg"
	"go.uber.org/zap"
)

// ManagedClient represents an individual warm MTProto connection.
type ManagedClient struct {
	ID     int
	Client *telegram.Client
	API    *tg.Client
	ready  chan struct{}
}

// ClientPool manages a set of warm, reusable MTProto connections.
type ClientPool struct {
	apiID      int
	apiHash    string
	sessionStr string
	size       int
	clients    []*ManagedClient
	available  chan *ManagedClient
	ctx        context.Context
	cancel     context.CancelFunc
	logger     *zap.Logger
}

// NewClientPool initializes and starts 'size' independent gotd client connections.
func NewClientPool(parentCtx context.Context, apiID int, apiHash string, sessionStr string, size int, logger *zap.Logger) (*ClientPool, error) {
	if size < 1 {
		size = 1
	}

	ctx, cancel := context.WithCancel(parentCtx)

	p := &ClientPool{
		apiID:      apiID,
		apiHash:    apiHash,
		sessionStr: sessionStr,
		size:       size,
		clients:    make([]*ManagedClient, size),
		available:  make(chan *ManagedClient, size),
		ctx:        ctx,
		cancel:     cancel,
		logger:     logger.Named("ClientPool"),
	}

	sessionData, err := session.TelethonSession(sessionStr)
	if err != nil {
		cancel()
		return nil, fmt.Errorf("decode session: %w", err)
	}

	var wg sync.WaitGroup
	errCh := make(chan error, size)

	for i := 0; i < size; i++ {
		wg.Add(1)
		idx := i
		go func() {
			defer wg.Done()
			if idx > 0 {
				time.Sleep(time.Duration(idx*250) * time.Millisecond)
			}

			storage := &session.StorageMemory{}
			loader := session.Loader{Storage: storage}
			if err := loader.Save(ctx, sessionData); err != nil {
				errCh <- fmt.Errorf("client %d storage save: %w", idx, err)
				return
			}

			client := telegram.NewClient(apiID, apiHash, telegram.Options{
				SessionStorage: storage,
				Logger:         logzap.New(logger.Named(fmt.Sprintf("gotd-%d", idx))),
			})

			mc := &ManagedClient{
				ID:     idx,
				Client: client,
				ready:  make(chan struct{}),
			}

			go func() {
				_ = client.Run(ctx, func(cCtx context.Context) error {
					mc.API = client.API()
					close(mc.ready)
					<-cCtx.Done()
					return nil
				})
			}()

			select {
			case <-mc.ready:
				p.clients[idx] = mc
				p.available <- mc
			case <-time.After(30 * time.Second):
				errCh <- fmt.Errorf("client %d timed out connecting", idx)
			case <-ctx.Done():
				errCh <- ctx.Err()
			}
		}()
	}

	wg.Wait()
	close(errCh)

	for e := range errCh {
		if e != nil {
			p.Close()
			return nil, e
		}
	}

	return p, nil
}

// Acquire gets an available warm connection from the pool.
func (p *ClientPool) Acquire(ctx context.Context) (*ManagedClient, error) {
	select {
	case c := <-p.available:
		return c, nil
	case <-ctx.Done():
		return nil, ctx.Err()
	}
}

// Release returns the connection back to the pool for reuse.
func (p *ClientPool) Release(c *ManagedClient) {
	if c != nil {
		p.available <- c
	}
}

// Size returns total connections in pool.
func (p *ClientPool) Size() int {
	return p.size
}

// Close gracefully closes all client connections.
func (p *ClientPool) Close() {
	p.cancel()
}
