"""
Configuration management using pydantic-settings.
"""
import json
from typing import Any, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ChatTargetConfig(BaseSettings):
    """Target Telegram destination for a specific MAX chat."""
    tg_chat_id: Union[int, str]
    tg_topic_id: int | None = None
    chat_name: str | None = None


class BotConfig(BaseSettings):
    """Application settings loaded from environment and .env file."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # MAX settings
    MAX_TOKEN: str = Field(description="MAX messenger auth token")
    MAX_CHAT_IDS: Union[list[str], str] = Field(default_factory=list, description="List of monitored MAX chat IDs")

    # Telegram settings
    TG_BOT_TOKEN: str = Field(description="Telegram Bot API Token")
    TG_CHAT_ID: Union[int, str] = Field(description="Default Telegram destination chat ID")
    TG_TOPIC_ID: int | None = Field(default=None, description="Default Telegram message_thread_id / topic ID")
    MONITOR_ID: Union[int, str, None] = Field(default=None, description="Chat ID for system monitoring and alerts")

    # Advanced chat mapping: {"max_chat_id": {"tg_chat_id": ..., "tg_topic_id": ..., "chat_name": ...}}
    CHAT_MAPPING: dict[str, ChatTargetConfig] = Field(default_factory=dict)
    CHAT_NAMES: dict[str, str] = Field(default_factory=dict, description="Manual override mapping of MAX chat_id to custom display title")

    # General app settings
    LOG_LEVEL: str = Field(default="INFO")
    USER_CACHE_TTL: int = Field(default=3600, description="Cache TTL in seconds for user profile names")
    CHAT_CACHE_TTL: int = Field(default=86400, description="Cache TTL in seconds for chat titles")
    MAX_WORKERS: int = Field(default=4, description="Worker count for processing message push events")
    MAX_HEARTBEAT_INTERVAL: float = Field(default=45.0, description="Interval in seconds for client-initiated MAX heartbeats")
    MAX_HEARTBEAT_TIMEOUT: float = Field(default=120.0, description="Max seconds of inactivity before declaring connection dead")
    HEALTH_CHECK_FILE: str = Field(default="health.json", description="Path to health status file updated periodically")

    # Logging settings
    LOGS_DIR: str = Field(default="logs", description="Directory to store session log files")
    MAX_LOGS_DIR_SIZE_MB: int = Field(default=1024, description="Max total size of logs directory in MB (1GB)")
    MAX_LOG_FILE_SIZE_MB: int = Field(default=100, description="Max size of a single log chunk file in MB before rotation")

    @field_validator("MAX_CHAT_IDS", mode="before")
    @classmethod
    def _parse_max_chat_ids(cls, v: Any) -> list[str]:
        if isinstance(v, list):
            return [str(item).strip() for item in v if str(item).strip()]
        if isinstance(v, (int, str)):
            v_str = str(v).strip()
            if not v_str:
                return []
            if v_str.startswith("[") and v_str.endswith("]"):
                try:
                    parsed = json.loads(v_str)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except Exception:
                    pass
            # Comma separated
            return [item.strip() for item in v_str.split(",") if item.strip()]
        return []

    @field_validator("CHAT_MAPPING", mode="before")
    @classmethod
    def _parse_chat_mapping(cls, v: Any) -> dict[str, Any]:
        if isinstance(v, str):
            v_str = v.strip()
            if not v_str:
                return {}
            try:
                parsed = json.loads(v_str)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                return {}
        if isinstance(v, dict):
            return v
        return {}

    @field_validator("CHAT_NAMES", mode="before")
    @classmethod
    def _parse_chat_names(cls, v: Any) -> dict[str, str]:
        if isinstance(v, str):
            v_str = v.strip()
            if not v_str:
                return {}
            try:
                parsed = json.loads(v_str)
                if isinstance(parsed, dict):
                    return {str(k).strip(): str(val).strip() for k, val in parsed.items()}
            except Exception:
                return {}
        if isinstance(v, dict):
            return {str(k).strip(): str(val).strip() for k, val in v.items()}
        return {}

    def get_destination(self, max_chat_id: int | str) -> tuple[Union[int, str], int | None]:
        """
        Returns (tg_chat_id, tg_topic_id) for a given MAX chat.
        Uses CHAT_MAPPING if specified, otherwise falls back to (TG_CHAT_ID, TG_TOPIC_ID).
        """
        key = str(max_chat_id).strip()
        if key in self.CHAT_MAPPING:
            target = self.CHAT_MAPPING[key]
            return target.tg_chat_id, target.tg_topic_id
        return self.TG_CHAT_ID, self.TG_TOPIC_ID

    def get_chat_override_title(self, max_chat_id: int | str) -> Optional[str]:
        """
        Returns manual override chat title if configured in CHAT_MAPPING or CHAT_NAMES.
        """
        key = str(max_chat_id).strip()
        if key in self.CHAT_MAPPING and self.CHAT_MAPPING[key].chat_name:
            return self.CHAT_MAPPING[key].chat_name
        return self.CHAT_NAMES.get(key)

