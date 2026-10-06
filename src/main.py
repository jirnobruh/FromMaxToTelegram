import asyncio
import logging
from max_client import __version__ as max_client_version

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("max-to-tg-bot")

async def main() -> None:
    logger.info("Starting MAX to Telegram Forwarder Bot...")
    logger.info(f"Loaded max-client SDK version: {max_client_version}")
    # TODO: Initialize MaxClient, Bot, and message forwarder pipeline
    logger.info("Bot initialized successfully.")

if __name__ == "__main__":
    asyncio.run(main())
