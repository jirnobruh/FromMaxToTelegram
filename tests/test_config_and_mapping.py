"""
Tests for BotConfig parsing and chat/topic destination mapping.
"""
import json
from src.config import BotConfig, ChatTargetConfig


def test_config_parsing_defaults():
    cfg = BotConfig(
        MAX_TOKEN="max_secret_123",
        MAX_CHAT_IDS="100, 200, 300",
        TG_BOT_TOKEN="12345:ABCDEF",
        TG_CHAT_ID=-1001234567890,
        TG_TOPIC_ID=42,
    )
    assert cfg.MAX_TOKEN == "max_secret_123"
    assert cfg.MAX_CHAT_IDS == ["100", "200", "300"]
    assert cfg.TG_CHAT_ID == -1001234567890
    assert cfg.TG_TOPIC_ID == 42


def test_config_destination_fallback():
    cfg = BotConfig(
        MAX_TOKEN="token",
        TG_BOT_TOKEN="tg_token",
        TG_CHAT_ID=-100111,
        TG_TOPIC_ID=10,
    )
    chat_id, topic_id = cfg.get_destination("99999")
    assert chat_id == -100111
    assert topic_id == 10


def test_config_destination_with_mapping():
    mapping = {
        "100": {"tg_chat_id": -100222, "tg_topic_id": 5},
        "200": {"tg_chat_id": -100333, "tg_topic_id": None},
    }
    cfg = BotConfig(
        MAX_TOKEN="token",
        TG_BOT_TOKEN="tg_token",
        TG_CHAT_ID=-100111,
        TG_TOPIC_ID=10,
        CHAT_MAPPING=mapping,
    )

    # Specific mapping with topic
    c1, t1 = cfg.get_destination("100")
    assert c1 == -100222
    assert t1 == 5

    # Specific mapping without topic
    c2, t2 = cfg.get_destination(200)
    assert c2 == -100333
    assert t2 is None

    # Unmapped fallback
    c3, t3 = cfg.get_destination("300")
    assert c3 == -100111
    assert t3 == 10
