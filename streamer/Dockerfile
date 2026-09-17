# Multi-stage Dockerfile for Cineforge Go Streamer
# -------------------------------------------------------------------
# Stage 1: Build binary
# -------------------------------------------------------------------
FROM golang:1.24-alpine AS builder

# Install build dependencies
RUN apk add --no-cache git ca-certificates tzdata

WORKDIR /app

# Cache dependency layer
COPY go.mod go.sum ./
RUN go mod download

# Copy production streamer sources
COPY auth.go main.go pipe.go pool.go range.go telegram.go ./

# Compile statically linked binary with stripped debug info for minimal footprint
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o streamer main.go telegram.go pool.go pipe.go range.go auth.go

# -------------------------------------------------------------------
# Stage 2: Minimal runtime image
# -------------------------------------------------------------------
FROM alpine:3.21

# Install CA certificates for MTProto TLS connections
RUN apk add --no-cache ca-certificates tzdata

# Create non-root user for container security
RUN addgroup -S cineforge && adduser -S cineforge -G cineforge

WORKDIR /app

# Copy binary from builder stage
COPY --from=builder /app/streamer /app/streamer

# Set runtime ownership
RUN chown -R cineforge:cineforge /app

USER cineforge

# Default environment variables (overridden by Render runtime)
ENV HOST=0.0.0.0
ENV PORT=8088

EXPOSE 8088

# Health check (Render also performs native HTTP health checks via dashboard/render.yaml)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:${PORT:-8088}/health || exit 1

ENTRYPOINT ["/app/streamer"]
