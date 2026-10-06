"""
Unit tests for MessageForwarder orchestration logic.
"""
from unittest.mock import AsyncMock, MagicMock
import pytest
from max_client import MaxClient
from max_client.models import Attachment, Message, MessageLink, User
from src.cache import UserCache
from src.config import BotConfig
from src.forwarder import MessageForwarder


@pytest.fixture
def forwarder():
    bot = MagicMock()
    bot.send_message = AsyncMock()
    bot.send_photo = AsyncMock()
    bot.send_media_group = AsyncMock()
    bot.send_document = AsyncMock()
    config = BotConfig(
        MAX_TOKEN="dummy",
        TG_BOT_TOKEN="dummy",
        TG_CHAT_ID=-100111,
        TG_TOPIC_ID=15,
    )
    cache = UserCache(ttl=60)
    return MessageForwarder(bot=bot, config=config, user_cache=cache)


@pytest.fixture
def mock_client():
    client = MagicMock(spec=MaxClient)
    client.get_user = AsyncMock(
        return_value=User.model_validate({"id": 1234, "names": [{"name": "Анна"}]})
    )
    return client


@pytest.mark.asyncio
async def test_forward_plain_text(forwarder, mock_client):
    msg = Message(
        id="m1",
        chatId=500,
        sender=1234,
        text="Привет всем!",
    )

    await forwarder.forward_max_message(mock_client, msg)

    forwarder.bot.send_message.assert_called_once()
    call_args = forwarder.bot.send_message.call_args[1]
    assert call_args["chat_id"] == -100111
    assert call_args["message_thread_id"] == 15
    assert "<b>Анна</b>" in call_args["text"]
    assert "Привет всем!" in call_args["text"]


@pytest.mark.asyncio
async def test_forward_with_single_photo(forwarder, mock_client):
    msg = Message(
        id="m2",
        chatId=500,
        sender=1234,
        text="Смотрите фото",
        attaches=[
            Attachment(_type="PHOTO", baseUrl="https://example.com/p1.jpg")
        ],
    )

    await forwarder.forward_max_message(mock_client, msg)

    forwarder.bot.send_photo.assert_called_once()
    call_args = forwarder.bot.send_photo.call_args[1]
    assert call_args["chat_id"] == -100111
    assert call_args["message_thread_id"] == 15
    assert call_args["photo"] == "https://example.com/p1.jpg"
    assert "<b>Анна</b>" in call_args["caption"]


@pytest.mark.asyncio
async def test_forward_with_multiple_photos(forwarder, mock_client):
    attaches = [
        Attachment(_type="PHOTO", baseUrl=f"https://example.com/p{i}.jpg")
        for i in range(12)
    ]
    msg = Message(
        id="m3",
        chatId=500,
        sender=1234,
        text="Альбом",
        attaches=attaches,
    )

    await forwarder.forward_max_message(mock_client, msg)

    # 12 photos should be split into 2 batches (10 and 2)
    assert forwarder.bot.send_media_group.call_count == 2
    first_call_media = forwarder.bot.send_media_group.call_args_list[0][1]["media"]
    second_call_media = forwarder.bot.send_media_group.call_args_list[1][1]["media"]
    assert len(first_call_media) == 10
    assert len(second_call_media) == 2
    # Caption attached to first item in first batch
    assert "<b>Анна</b>" in first_call_media[0].caption
    assert second_call_media[0].caption is None


@pytest.mark.asyncio
async def test_forward_nested_forward_message(forwarder, mock_client):
    mock_client.get_user.side_effect = [
        User.model_validate({"id": 1234, "names": [{"name": "Анна"}]}),
        User.model_validate({"id": 5678, "names": [{"name": "Борис"}]}),
    ]
    fwd_payload = {
        "id": "m4",
        "chatId": 500,
        "sender": 1234,
        "text": "",
        "link": {
            "type": "FORWARD",
            "chatId": 600,
            "message": {
                "id": "m4_orig",
                "sender": 5678,
                "text": "Оригинальный текст",
            },
        },
    }
    msg = Message.model_validate(fwd_payload).bind_client(mock_client)
    await forwarder.forward_max_message(mock_client, msg)

    forwarder.bot.send_message.assert_called_once()
    text = forwarder.bot.send_message.call_args[1]["text"]
    assert "<b>Анна</b>" in text
    assert "Переслано от: Борис" in text
    assert "Оригинальный текст" in text


@pytest.mark.asyncio
async def test_forward_unhandled_file_attachment(forwarder, mock_client):
    file_payload = {
        "id": "m5",
        "chatId": 500,
        "sender": 1234,
        "text": "",
        "attaches": [
            {
                "_type": "FILE",
                "name": "README.md",
                "size": 1360,
                "fileId": 3616615111,
            }
        ],
    }
    msg = Message.model_validate(file_payload).bind_client(mock_client)
    mock_client.get_file_download_url = AsyncMock(return_value=None)

    await forwarder.forward_max_message(mock_client, msg)

    forwarder.bot.send_message.assert_called_once()
    text = forwarder.bot.send_message.call_args[1]["text"]
    assert "<b>Анна</b>" in text
    assert "Необработанные файлы:" in text
    assert "README.md" in text
