package main

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"net/http"
	"os"
	"strconv"
	"time"
)

// VerifyStreamRequest validates optional HMAC signatures if STREAM_SECRET_KEY is configured.
// If STREAM_SECRET_KEY is empty or not set, requests pass through for prototype development.
func VerifyStreamRequest(r *http.Request, chatTarget string, messageID int) (bool, string) {
	secret := os.Getenv("STREAM_SECRET_KEY")
	if secret == "" {
		return true, "" // Security bypass during local development/benchmarks
	}

	sig := r.URL.Query().Get("sig")
	expStr := r.URL.Query().Get("exp")

	if sig == "" || expStr == "" {
		return false, "missing required signature or expiration parameter"
	}

	exp, err := strconv.ParseInt(expStr, 10, 64)
	if err != nil || time.Now().Unix() > exp {
		return false, "stream token has expired"
	}

	message := fmt.Sprintf("%s:%d:%d", chatTarget, messageID, exp)
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write([]byte(message))
	expectedSig := hex.EncodeToString(mac.Sum(nil))

	if !hmac.Equal([]byte(sig), []byte(expectedSig)) {
		return false, "invalid stream signature"
	}

	return true, ""
}
