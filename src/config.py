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


class BotConfig(BaseSettings):
    """Application settings loaded from environment and .env file."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # MAX settings
    MAX_TOKEN: str = Field(description="MAX messenger auth token")
    MAX_CHAT_IDS: list[str] = Field(default_factory=list, description="List of monitored MAX chat IDs")

    # Telegram settings
    TG_BOT_TOKEN: str = Field(description="Telegram Bot API Token")
    TG_CHAT_ID: Union[int, str] = Field(description="Default Telegram destination chat ID")
    TG_TOPIC_ID: int | None = Field(default=None, description="Default Telegram message_thread_id / topic ID")
    MONITOR_ID: Union[int, str, None] = Field(default=None, description="Chat ID for system monitoring and alerts")

    # Advanced chat mapping: {"max_chat_id": {"tg_chat_id": ..., "tg_topic_id": ...}}
    CHAT_MAPPING: dict[str, ChatTargetConfig] = Field(default_factory=dict)

    # General app settings
    LOG_LEVEL: str = Field(default="INFO")
    USER_CACHE_TTL: int = Field(default=3600, description="Cache TTL in seconds for user profile names")
    MAX_WORKERS: int = Field(default=4, description="Worker count for processing message push events")

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
