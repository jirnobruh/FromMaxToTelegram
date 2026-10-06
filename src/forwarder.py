"""
Message forwarder service coordinating MAX messages into Telegram.
"""
import asyncio
import logging
from typing import Optional, Union

import aiohttp
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter, TelegramAPIError
from aiogram.types import BufferedInputFile, InputMediaPhoto, URLInputFile

from max_client import MaxClient
from max_client.models import Attachment, Message
from src.cache import UserCache
from src.config import BotConfig
from src.formatter import (
    escape_html,
    format_author_header,
    format_message_text,
    split_into_media_batches,
    truncate_caption,
    truncate_message,
)

logger = logging.getLogger("max-to-tg-bot.forwarder")


class MessageForwarder:
    """Handles parsing and delivering MAX messages to target Telegram chats/topics."""

    def __init__(self, bot: Bot, config: BotConfig, user_cache: Optional[UserCache] = None):
        self.bot = bot
        self.config = config
        self.user_cache = user_cache or UserCache(ttl=config.USER_CACHE_TTL)

    async def get_user_display_name(self, client: MaxClient, user_id: Union[int, str, None]) -> str:
        """Resolves user display name with caching to minimize WebSocket lookups."""
        if not user_id:
            return "Аноним"

        cached = await self.user_cache.get(user_id)
        if cached:
            return cached

        try:
            user = await client.get_user(id=user_id)
            name = user.display_name
            await self.user_cache.set(user_id, name)
            return name
        except Exception as e:
            logger.warning(f"Failed to fetch user profile for id {user_id}: {e}")
            fallback = f"User {user_id}"
            await self.user_cache.set(user_id, fallback)
            return fallback

    async def forward_max_message(self, client: MaxClient, message: Message) -> None:
        """Main pipeline to process and send a MAX message into Telegram."""
        # 1. Determine destination Telegram chat & topic
        tg_chat_id, tg_topic_id = self.config.get_destination(message.chat_id)
        logger.info(f"Forwarding MAX message {message.id} from chat {message.chat_id} -> TG {tg_chat_id} (topic {tg_topic_id})")

        # 2. Extract author name
        author_name = await self.get_user_display_name(client, message.sender)

        # 3. Handle forwarded/replied message content
        forward_author_name: Optional[str] = None
        main_text = message.text or ""
        attaches = list(message.attaches or [])

        if message.is_forward and message.link and message.link.message:
            fwd_msg = message.link.message
            fwd_sender_id = message.link.sender or fwd_msg.sender
            forward_author_name = await self.get_user_display_name(client, fwd_sender_id)
            if fwd_msg.text and not main_text:
                main_text = fwd_msg.text
            if fwd_msg.attaches and not attaches:
                attaches = list(fwd_msg.attaches)

        # 4. Separate attachments: Photos vs Files
        photos: list[Attachment] = []
        files_to_process: list[Attachment] = []
        unhandled_files: list[str] = []

        for a in attaches:
            if a.is_photo or (a.mime_type and a.mime_type.startswith("image/")):
                if a.url:
                    photos.append(a)
                else:
                    files_to_process.append(a)
            elif a.is_file or a.file_id or a.name or a.url:
                files_to_process.append(a)
            else:
                unhandled_files.append(a.name or a.type or "файл")

        # 5. Try downloading files
        downloaded_documents: list[tuple[BufferedInputFile, str]] = []
        for a in files_to_process:
            filename = a.name or (f"file_{a.file_id}" if a.file_id else "file")
            try:
                download_url = await a.get_download_url(message)
                if download_url:
                    doc = await self._download_file_bytes(download_url, filename)
                    if doc:
                        downloaded_documents.append((doc, filename))
                        continue
            except Exception as e:
                logger.warning(f"Failed to download attachment {filename}: {e}")

            # If download was impossible or failed
            unhandled_files.append(filename)

        # 6. Format formatted text body
        formatted_text = format_message_text(
            author_name=author_name,
            text=main_text,
            forward_author_name=forward_author_name,
            unhandled_files=unhandled_files,
        )

        # 7. Deliver to Telegram
        caption_used = False

        if photos:
            await self._send_photo_batches(
                tg_chat_id=tg_chat_id,
                tg_topic_id=tg_topic_id,
                photos=photos,
                formatted_text=formatted_text,
            )
            caption_used = True

        if downloaded_documents:
            for idx, (doc, filename) in enumerate(downloaded_documents):
                doc_caption = None
                parse_mode = None
                if not caption_used and idx == 0:
                    doc_caption = truncate_caption(formatted_text)
                    parse_mode = ParseMode.HTML
                    caption_used = True

                await self._safe_telegram_call(
                    self.bot.send_document(
                        chat_id=tg_chat_id,
                        message_thread_id=tg_topic_id,
                        document=doc,
                        caption=doc_caption,
                        parse_mode=parse_mode,
                    )
                )

        if not caption_used:
            await self._send_text_message(
                tg_chat_id=tg_chat_id,
                tg_topic_id=tg_topic_id,
                formatted_text=formatted_text,
            )

    async def _download_file_bytes(self, url: str, filename: str) -> Optional[BufferedInputFile]:
        """Downloads file bytes via HTTP with a 50MB safety limit."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        content_length = resp.headers.get("Content-Length")
                        if content_length and int(content_length) > 50 * 1024 * 1024:
                            logger.warning(f"File {filename} exceeds 50MB: {content_length} bytes")
                            return None
                        data = await resp.read()
                        if len(data) > 50 * 1024 * 1024:
                            logger.warning(f"File {filename} exceeds 50MB after download")
                            return None
                        return BufferedInputFile(data, filename=filename)
                    else:
                        logger.warning(f"HTTP download failed with status {resp.status} for {url}")
                        return None
        except Exception as e:
            logger.warning(f"Error downloading file {filename} from {url}: {e}")
            return None

    async def _send_text_message(
        self,
        tg_chat_id: Union[int, str],
        tg_topic_id: int | None,
        formatted_text: str,
    ) -> None:
        """Sends a text-only message to Telegram with retry support."""
        safe_text = truncate_message(formatted_text)
        await self._safe_telegram_call(
            self.bot.send_message(
                chat_id=tg_chat_id,
                message_thread_id=tg_topic_id,
                text=safe_text,
            )
        )

    async def _send_photo_batches(
        self,
        tg_chat_id: Union[int, str],
        tg_topic_id: int | None,
        photos: list[Attachment],
        formatted_text: str,
    ) -> None:
        """Sends photo media groups in batches of at most 10 items."""
        batches = split_into_media_batches(photos, batch_size=10)

        for batch_index, batch in enumerate(batches):
            media_group: list[InputMediaPhoto] = []
            for photo_index, photo in enumerate(batch):
                caption = None
                parse_mode = None
                # Attach caption to the first photo of the first batch
                if batch_index == 0 and photo_index == 0 and formatted_text:
                    caption = truncate_caption(formatted_text)
                    parse_mode = ParseMode.HTML

                media_item = InputMediaPhoto(
                    media=photo.url,
                    caption=caption,
                    parse_mode=parse_mode,
                )
                media_group.append(media_item)

            if len(media_group) == 1:
                # Single photo: sendPhoto is simpler and more reliable
                single = media_group[0]
                await self._safe_telegram_call(
                    self.bot.send_photo(
                        chat_id=tg_chat_id,
                        message_thread_id=tg_topic_id,
                        photo=single.media,
                        caption=single.caption,
                        parse_mode=single.parse_mode,
                    )
                )
            else:
                await self._safe_telegram_call(
                    self.bot.send_media_group(
                        chat_id=tg_chat_id,
                        message_thread_id=tg_topic_id,
                        media=media_group,
                    )
                )

    async def _safe_telegram_call(self, coro, max_retries: int = 3) -> None:
        """Executes a Telegram Bot API call with handling for rate limits and retries."""
        for attempt in range(1, max_retries + 1):
            try:
                await coro
                return
            except TelegramRetryAfter as e:
                logger.warning(f"Telegram Rate Limit: Retry after {e.retry_after}s (attempt {attempt}/{max_retries})")
                await asyncio.sleep(e.retry_after + 0.5)
            except TelegramNetworkError as e:
                logger.warning(f"Telegram Network Error: {e} (attempt {attempt}/{max_retries})")
                await asyncio.sleep(1.0 * attempt)
            except TelegramAPIError as e:
                logger.error(f"Telegram API Error: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error while sending to Telegram: {e}", exc_info=True)
                raise
