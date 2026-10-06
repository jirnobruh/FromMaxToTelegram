"""
Main entrypoint and lifecycle coordinator for MAX to Telegram Bot.
"""
import asyncio
import html
import logging
import signal
import sys
from typing import Optional

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from max_library import MaxClient, filters
from max_library.models import Message
from src.config import BotConfig
from src.forwarder import MessageForwarder
from src.logger import setup_logging

logger = logging.getLogger("max-to-tg-bot")


class BotApp:
    """Manages the full lifecycle of MaxClient and Telegram Bot."""

    def __init__(self, config: Optional[BotConfig] = None):
        self.config = config or BotConfig()
        self.session_log_path = setup_logging(
            logs_dir=self.config.LOGS_DIR,
            log_level=self.config.LOG_LEVEL,
            max_dir_size_mb=self.config.MAX_LOGS_DIR_SIZE_MB,
            max_file_size_mb=self.config.MAX_LOG_FILE_SIZE_MB,
        )

        self.bot = Bot(
            token=self.config.TG_BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        self.forwarder = MessageForwarder(bot=self.bot, config=self.config)
        self.max_library = MaxClient(
            token=self.config.MAX_TOKEN,
            num_workers=self.config.MAX_WORKERS,
            auto_reconnect=True,
        )
        self._stop_event = asyncio.Event()

    def setup_handlers(self) -> None:
        """Registers MAX event filters and callbacks."""

        # 1. On Connect / Reconnect
        @self.max_library.on_connect
        async def on_connect(client: MaxClient):
            user_info = "Unknown"
            if client.me:
                user_info = f"{client.me.display_name} (ID: {client.me.id})"
            logger.info(f"Connected to MAX as: {user_info}")

            # Notify monitor chat if configured
            if self.config.MONITOR_ID:
                try:
                    await self.bot.send_message(
                        chat_id=self.config.MONITOR_ID,
                        text=f"🟢 <b>MAX Forwarder Bot connected</b>\n👤 Пользователь: <code>{html.escape(user_info)}</code>",
                    )
                except Exception as e:
                    logger.warning(f"Failed to send monitor startup notification: {e}")

        # 2. On Incoming Message
        if self.config.MAX_CHAT_IDS:
            msg_filter = filters.chat_id(*self.config.MAX_CHAT_IDS) & filters.is_not_removed()
        else:
            msg_filter = filters.is_not_removed()

        @self.max_library.on_message(msg_filter)
        async def handle_message(client: MaxClient, message: Message):
            try:
                await self.forwarder.forward_max_message(client, message)
            except Exception as e:
                logger.error(f"Error while forwarding message {message.id}: {e}", exc_info=True)

    async def start(self) -> None:
        """Starts the MAX client and waits for shutdown signal."""
        self.setup_handlers()
        logger.info("Starting MAX Forwarder Bot...")

        try:
            await self.max_library.start()
            logger.info("MAX Forwarder Bot is running. Press Ctrl+C to stop.")
            await self._stop_event.wait()
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Gracefully terminates client and closes bot session."""
        logger.info("Stopping MAX Forwarder Bot...")
        self._stop_event.set()

        try:
            await self.max_library.close()
        except Exception as e:
            logger.warning(f"Error closing max client: {e}")

        try:
            await self.bot.session.close()
        except Exception as e:
            logger.warning(f"Error closing bot session: {e}")

        logger.info("MAX Forwarder Bot stopped.")


async def main() -> None:
    try:
        config = BotConfig()
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please ensure .env file is configured properly according to .env.example")
        sys.exit(1)

    app = BotApp(config)

    # Register OS signal handlers for graceful stop
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(app.stop()))
        except NotImplementedError:
            # Signal handlers not implemented on Windows event loop for add_signal_handler
            pass

    try:
        await app.start()
    except (KeyboardInterrupt, SystemExit):
        await app.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
