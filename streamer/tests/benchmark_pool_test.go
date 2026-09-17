package tests

import (
	"context"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestBenchmarkPoolBinaryExecution(t *testing.T) {
	// Locate session.txt
	sessionPath := filepath.Join("..", "session.txt")
	if _, err := os.Stat(sessionPath); os.IsNotExist(err) {
		t.Skip("Skipping test: session.txt not found")
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
	defer cancel()

	// Ensure benchmark_pool.exe is compiled
	cmdBuild := exec.CommandContext(ctx, "go", "build", "-o", "benchmark_pool.exe", "benchmark_pool.go", "pool.go")
	cmdBuild.Dir = ".."
	out, err := cmdBuild.CombinedOutput()
	if err != nil {
		t.Fatalf("Failed to compile benchmark_pool.exe: %v\nOutput: %s", err, string(out))
	}

	// Verify binary exists
	binPath := filepath.Join("..", "benchmark_pool.exe")
	if _, err := os.Stat(binPath); os.IsNotExist(err) {
		t.Fatalf("Binary benchmark_pool.exe does not exist at %s", binPath)
	}

	t.Log("Successfully built benchmark_pool.exe with pool.go")
}

func TestPoolSourceStructure(t *testing.T) {
	poolPath := filepath.Join("..", "pool.go")
	content, err := os.ReadFile(poolPath)
	if err != nil {
		t.Fatalf("Failed to read pool.go: %v", err)
	}

	strContent := string(content)
	requiredSymbols := []string{
		"type ManagedClient struct",
		"type ClientPool struct",
		"func NewClientPool",
		"func (p *ClientPool) Acquire",
		"func (p *ClientPool) Release",
		"func (p *ClientPool) Close",
	}

	for _, sym := range requiredSymbols {
		if !strings.Contains(strContent, sym) {
			t.Errorf("pool.go missing required symbol: %s", sym)
		}
	}
}
