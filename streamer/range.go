package main

import (
	"fmt"
	"net/http"
	"regexp"
	"strconv"
	"strings"
)

var rangeRegex = regexp.MustCompile(`^bytes\s*=\s*(\d*)\s*-\s*(\d*)$`)

// ByteRange holds the parsed start and end offsets for RFC 7233 range requests.
type ByteRange struct {
	Start  int64
	End    int64
	Length int64
}

// ParseRange parses standard RFC 7233 Range headers (e.g. "bytes=0-1048575", "bytes=1000-", "bytes=-500000").
// If no Range header is provided, returns (nil, false, nil).
// If an invalid or unsatisfiable range is requested, returns an error suitable for HTTP 416.
func ParseRange(rangeHeader string, fileSize int64) (*ByteRange, bool, error) {
	trimmed := strings.TrimSpace(rangeHeader)
	if trimmed == "" {
		return nil, false, nil
	}

	matches := rangeRegex.FindStringSubmatch(trimmed)
	if len(matches) != 3 {
		return nil, false, fmt.Errorf("invalid range header syntax: %s", rangeHeader)
	}

	rawStart := matches[1]
	rawEnd := matches[2]

	if rawStart == "" && rawEnd == "" {
		return nil, false, fmt.Errorf("empty byte range")
	}

	var start, end int64

	if rawStart == "" {
		// Suffix range: bytes=-500000 (last 500,000 bytes)
		suffixLen, err := strconv.ParseInt(rawEnd, 10, 64)
		if err != nil || suffixLen <= 0 {
			return nil, false, fmt.Errorf("invalid suffix range length")
		}
		start = fileSize - suffixLen
		if start < 0 {
			start = 0
		}
		end = fileSize - 1
	} else if rawEnd == "" {
		// Prefix range: bytes=1000- (from 1000 to EOF)
		s, err := strconv.ParseInt(rawStart, 10, 64)
		if err != nil || s < 0 {
			return nil, false, fmt.Errorf("invalid start byte offset")
		}
		start = s
		end = fileSize - 1
	} else {
		// Explicit range: bytes=0-1048575
		s, err1 := strconv.ParseInt(rawStart, 10, 64)
		e, err2 := strconv.ParseInt(rawEnd, 10, 64)
		if err1 != nil || err2 != nil || s < 0 || e < s {
			return nil, false, fmt.Errorf("invalid start or end byte offsets")
		}
		start = s
		end = e
	}

	// Validate bounds against actual file size
	if start >= fileSize {
		return nil, false, fmt.Errorf("requested range start (%d) exceeds file size (%d)", start, fileSize)
	}

	if end >= fileSize {
		end = fileSize - 1
	}

	length := end - start + 1

	return &ByteRange{
		Start:  start,
		End:    end,
		Length: length,
	}, true, nil
}

// SetRangeResponseHeaders sets the required RFC 7233 headers for streaming video playback.
func SetRangeResponseHeaders(w http.ResponseWriter, r *ByteRange, fileSize int64, mimeType, fileName string) {
	w.Header().Set("Accept-Ranges", "bytes")
	w.Header().Set("Content-Type", mimeType)
	w.Header().Set("Cache-Control", "no-cache, no-store, must-revalidate")
	w.Header().Set("Pragma", "no-cache")
	w.Header().Set("Expires", "0")
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Expose-Headers", "Content-Range, Content-Length, Accept-Ranges, Content-Type")

	if fileName != "" {
		w.Header().Set("Content-Disposition", fmt.Sprintf(`inline; filename="%s"`, fileName))
	}

	if r != nil {
		w.Header().Set("Content-Range", fmt.Sprintf("bytes %d-%d/%d", r.Start, r.End, fileSize))
		w.Header().Set("Content-Length", strconv.FormatInt(r.Length, 10))
	} else {
		w.Header().Set("Content-Length", strconv.FormatInt(fileSize, 10))
	}
}
