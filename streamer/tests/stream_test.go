package tests

import (
	"context"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"testing"
	"time"
)

// TestRangeHeaderParsing verifies RFC 7233 range parsing logic.
func TestRangeHeaderParsing(t *testing.T) {
	fileSize := int64(1000000)

	tests := []struct {
		header      string
		expectValid bool
		start       int64
		end         int64
		length      int64
	}{
		{"bytes=0-1048575", true, 0, 999999, 1000000}, // Clamped to fileSize-1
		{"bytes=0-499999", true, 0, 499999, 500000},
		{"bytes=500000-", true, 500000, 999999, 500000},
		{"bytes=-200000", true, 800000, 999999, 200000},
		{"bytes=1500000-", false, 0, 0, 0},            // Exceeds file size
		{"bytes=500-100", false, 0, 0, 0},             // Start > End
		{"invalid-header", false, 0, 0, 0},
	}

	for _, tt := range tests {
		t.Run(tt.header, func(t *testing.T) {
			r, isPartial, err := parseRangeHeaderMock(tt.header, fileSize)
			if tt.expectValid {
				if err != nil || !isPartial {
					t.Fatalf("Expected valid range for '%s', got err: %v", tt.header, err)
				}
				if r.Start != tt.start || r.End != tt.end || r.Length != tt.length {
					t.Fatalf("For '%s': expected [%d-%d, len=%d], got [%d-%d, len=%d]",
						tt.header, tt.start, tt.end, tt.length, r.Start, r.End, r.Length)
				}
			} else {
				if err == nil {
					t.Fatalf("Expected error for invalid header '%s', got nil", tt.header)
				}
			}
		})
	}
}

type mockRange struct {
	Start  int64
	End    int64
	Length int64
}

func parseRangeHeaderMock(header string, fileSize int64) (*mockRange, bool, error) {
	trimmed := strings.TrimSpace(header)
	if !strings.HasPrefix(trimmed, "bytes=") {
		return nil, false, fmt.Errorf("invalid prefix")
	}
	parts := strings.Split(strings.TrimPrefix(trimmed, "bytes="), "-")
	if len(parts) != 2 {
		return nil, false, fmt.Errorf("invalid format")
	}

	var start, end int64
	if parts[0] == "" {
		sfx, err := strconv.ParseInt(parts[1], 10, 64)
		if err != nil || sfx <= 0 {
			return nil, false, fmt.Errorf("invalid suffix")
		}
		start = fileSize - sfx
		end = fileSize - 1
	} else if parts[1] == "" {
		s, err := strconv.ParseInt(parts[0], 10, 64)
		if err != nil || s >= fileSize {
			return nil, false, fmt.Errorf("start out of range")
		}
		start = s
		end = fileSize - 1
	} else {
		s, err1 := strconv.ParseInt(parts[0], 10, 64)
		e, err2 := strconv.ParseInt(parts[1], 10, 64)
		if err1 != nil || err2 != nil || s > e || s >= fileSize {
			return nil, false, fmt.Errorf("invalid range coordinates")
		}
		start = s
		end = e
		if end >= fileSize {
			end = fileSize - 1
		}
	}

	return &mockRange{Start: start, End: end, Length: end - start + 1}, true, nil
}

// TestEndToEndStreamer verifies HTTP /health, HEAD, initial 64 KB probe, and seeking on live streamer.exe.
func TestEndToEndStreamer(t *testing.T) {
	sessionPath := filepath.Join("..", "session.txt")
	if _, err := os.Stat(sessionPath); os.IsNotExist(err) {
		t.Skip("Skipping live streamer test: session.txt not present")
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), 90*time.Second)
	defer cancel()

	streamerBin, err := filepath.Abs(filepath.Join("..", "streamer.exe"))
	if err != nil {
		t.Fatalf("filepath.Abs: %v", err)
	}
	if _, err := os.Stat(streamerBin); os.IsNotExist(err) {
		t.Fatalf("streamer.exe not built at %s", streamerBin)
	}

	// 1. Launch streamer on port 8089
	port := "8089"
	cmd := exec.CommandContext(ctx, streamerBin)
	cmd.Dir = ".."
	cmd.Env = append(os.Environ(), "PORT="+port)

	stdoutPipe, err := cmd.StdoutPipe()
	if err != nil {
		t.Fatalf("StdoutPipe: %v", err)
	}
	cmd.Stderr = os.Stderr

	if err := cmd.Start(); err != nil {
		t.Fatalf("Failed to start streamer.exe: %v", err)
	}
	defer func() {
		_ = cmd.Process.Kill()
		_ = cmd.Wait()
	}()

	// Monitor logs in background
	go func() {
		_, _ = io.Copy(os.Stdout, stdoutPipe)
	}()

	client := &http.Client{Timeout: 30 * time.Second}
	baseURL := "http://127.0.0.1:" + port

	// 2. Poll /health until server is up
	healthy := false
	for i := 0; i < 40; i++ {
		time.Sleep(500 * time.Millisecond)
		resp, err := client.Get(baseURL + "/health")
		if err == nil && resp.StatusCode == http.StatusOK {
			var body map[string]interface{}
			_ = json.NewDecoder(resp.Body).Decode(&body)
			_ = resp.Body.Close()
			if body["status"] == "healthy" {
				healthy = true
				break
			}
		}
	}

	if !healthy {
		t.Fatal("streamer.exe failed to become healthy within 20 seconds")
	}
	t.Log("Streamer /health check PASSED!")

	// 3. Test HEAD /stream/me/9763
	headURL := baseURL + "/stream/me/9763"
	headResp, err := client.Head(headURL)
	if err != nil {
		t.Fatalf("HEAD request failed: %v", err)
	}
	_ = headResp.Body.Close()

	if headResp.StatusCode != http.StatusOK {
		t.Fatalf("Expected HEAD status 200, got %d", headResp.StatusCode)
	}
	if headResp.Header.Get("Accept-Ranges") != "bytes" {
		t.Errorf("Expected Accept-Ranges: bytes, got %s", headResp.Header.Get("Accept-Ranges"))
	}
	contentLengthStr := headResp.Header.Get("Content-Length")
	if contentLengthStr != "744246327" {
		t.Errorf("Expected Content-Length 744246327, got %s", contentLengthStr)
	}
	t.Logf("HEAD check PASSED: Content-Length=%s, Accept-Ranges=%s",
		contentLengthStr, headResp.Header.Get("Accept-Ranges"))

	// 4. Test GET initial 64 KB probe (bytes=0-65535) -> RFC 7233 206 Partial Content
	probeReq, err := http.NewRequestWithContext(ctx, "GET", headURL, nil)
	if err != nil {
		t.Fatalf("NewRequest: %v", err)
	}
	probeReq.Header.Set("Range", "bytes=0-65535")

	t0 := time.Now()
	probeResp, err := client.Do(probeReq)
	if err != nil {
		t.Fatalf("Probe range request failed: %v", err)
	}
	defer probeResp.Body.Close()

	probeDur := time.Since(t0)
	if probeResp.StatusCode != http.StatusPartialContent {
		t.Fatalf("Expected status 206 Partial Content, got %d", probeResp.StatusCode)
	}

	contentRange := probeResp.Header.Get("Content-Range")
	expectedContentRange := "bytes 0-65535/744246327"
	if contentRange != expectedContentRange {
		t.Errorf("Expected Content-Range '%s', got '%s'", expectedContentRange, contentRange)
	}

	probeData, err := io.ReadAll(probeResp.Body)
	if err != nil {
		t.Fatalf("Failed reading probe response body: %v", err)
	}
	if len(probeData) != 65536 {
		t.Fatalf("Expected 65536 bytes, got %d bytes", len(probeData))
	}

	// Verify MKV EBML signature
	magicHex := hex.EncodeToString(probeData[:8])
	if !strings.HasPrefix(magicHex, "1a45dfa3") {
		t.Fatalf("Expected MKV signature (1a45dfa3...), got %s", magicHex)
	}
	t.Logf("Initial 64 KB probe PASSED: %d bytes in %.2fs (Header: %s)", len(probeData), probeDur.Seconds(), magicHex)

	// 5. Test SEEKING: Seek to offset 10 MB (bytes=10485760-11534335, exactly 1 MB)
	seekReq, err := http.NewRequestWithContext(ctx, "GET", headURL, nil)
	if err != nil {
		t.Fatalf("NewRequest seek: %v", err)
	}
	seekReq.Header.Set("Range", "bytes=10485760-11534335")

	t1 := time.Now()
	seekResp, err := client.Do(seekReq)
	if err != nil {
		t.Fatalf("Seek range request failed: %v", err)
	}
	defer seekResp.Body.Close()

	seekDur := time.Since(t1)
	if seekResp.StatusCode != http.StatusPartialContent {
		t.Fatalf("Expected status 206 for seek, got %d", seekResp.StatusCode)
	}

	seekData, err := io.ReadAll(seekResp.Body)
	if err != nil {
		t.Fatalf("Failed reading seek body: %v", err)
	}
	if len(seekData) != 1048576 {
		t.Fatalf("Expected 1048576 bytes on seek, got %d bytes", len(seekData))
	}

	seekHead := hex.EncodeToString(seekData[:8])
	t.Logf("Seek 10 MB range PASSED: %d bytes in %.2fs (Head: %s)", len(seekData), seekDur.Seconds(), seekHead)
}
