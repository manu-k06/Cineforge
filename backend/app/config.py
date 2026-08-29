import json
from typing import List, Optional, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Cineforge API"
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS configuration
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Telegram MTProto User Session Settings
    TELEGRAM_API_ID: Optional[int] = None
    TELEGRAM_API_HASH: str = ""
    TELEGRAM_SESSION_NAME: str = "cineforge_session"

    # Telegram Bot Interaction Settings (Third-party Bot)
    TELEGRAM_BOT_USERNAME: str = ""
    TELEGRAM_BOT_RESPONSE_TIMEOUT: float = 15.0

    # Media Access & Streaming Performance Configuration
    # 512 KB (524,288 bytes) is the MTProto standard maximum request chunk size for high throughput
    TELEGRAM_CHUNK_SIZE: int = 524288
    # Number of chunks to prefetch ahead in memory (4 * 512KB = 2MB per stream)
    MEDIA_PREFETCH_CHUNKS: int = 4
    # Strict upper bound on memory buffer per reader/stream instance (8 MB)
    MAX_MEDIA_BUFFER_SIZE: int = 8388608
    # Max bytes allowable for a single test/benchmark range request (64 MB)
    MAX_BENCHMARK_BYTES: int = 67108864

    # Milestone B6: Session & Adaptive Bounded Cache Configuration
    # Max cache capacity in Megabytes per active streaming session (16 MB = 32 x 512KB chunks)
    MEDIA_MAX_BUFFER_MB: int = 16
    # Session idle expiration timeout in seconds (10 minutes)
    MEDIA_SESSION_TIMEOUT: int = 600
    # Number of sequential chunks to adaptively prefetch ahead of playhead (2 x 512KB = 1 MB)
    MEDIA_PREFETCH_CHUNKS_AHEAD: int = 2

    # Milestone B7: Media Probing, Compatibility & Playback Sustainability
    # Path to ffprobe executable (or command name on PATH)
    FFPROBE_PATH: Optional[str] = "ffprobe"
    # Safety margin multiplier for playback sustainability assessment (e.g. 1.15x)
    MEDIA_SUSTAINABILITY_MARGIN: float = 1.15
    # Default baseline measured source throughput in bps from B5/B5.2 benchmarks (~1.05 Mbps / 0.13 MB/s)
    MEASURED_SOURCE_THROUGHPUT_BPS: int = 1050000
    # Initial byte span to fetch from Telegram for ffprobe inspection (2 MB)
    PROBE_INITIAL_BYTES: int = 2097152

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("TELEGRAM_API_ID", mode="before")
    @classmethod
    def parse_api_id(cls, v: Union[int, str, None]) -> Optional[int]:
        if v is None or v == "":
            return None
        if isinstance(v, str):
            v_trimmed = v.strip()
            if not v_trimmed:
                return None
            return int(v_trimmed)
        return int(v)

    @field_validator("TELEGRAM_BOT_USERNAME", mode="before")
    @classmethod
    def parse_bot_username(cls, v: Union[str, None]) -> str:
        if v is None:
            return ""
        return v.strip().lstrip("@")

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            v_trimmed = v.strip()
            if v_trimmed.startswith("[") and v_trimmed.endswith("]"):
                return json.loads(v_trimmed)
            return [origin.strip() for origin in v_trimmed.split(",") if origin.strip()]
        return v


settings = Settings()
