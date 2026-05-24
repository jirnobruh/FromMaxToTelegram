import os
import logging
from dotenv import load_dotenv

# Настраиваем базовое логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%d-%m-%Y %H:%M:%S',
    handlers=[
        logging.FileHandler("bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Загружаем переменные окружения из .env файла
load_dotenv()

# --- Настройки MAX ---
MAX_TOKEN = os.getenv("MAX_TOKEN")
MAX_CHAT_IDS_STR = os.getenv("MAX_CHAT_IDS")

# --- Настройки Telegram ---
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
TG_TOPIC_ID = os.getenv("TG_TOPIC_ID")  # Необязательный параметр

# --- Проверка обязательных переменных ---
if not all([MAX_TOKEN, MAX_CHAT_IDS_STR, TG_BOT_TOKEN, TG_CHAT_ID]):
    logging.error("Критическая ошибка: Не все переменные окружения (MAX_TOKEN, MAX_CHAT_IDS, TG_BOT_TOKEN, TG_CHAT_ID) заданы в .env файле.")
    exit()

# --- Обработка и валидация переменных ---
try:
    MAX_CHAT_IDS = [int(chat_id.strip()) for chat_id in MAX_CHAT_IDS_STR.split(",")]
except (ValueError, AttributeError):
    logging.error("Критическая ошибка: Переменная MAX_CHAT_IDS в .env файле должна быть списком ID чатов, разделенных запятыми.")
    exit()

if TG_TOPIC_ID:
    try:
        TG_TOPIC_ID = int(TG_TOPIC_ID)
    except ValueError:
        logging.warning("Неверный формат TG_TOPIC_ID. Он будет проигнорирован.")
        TG_TOPIC_ID = None
else:
    TG_TOPIC_ID = None

logging.info("Конфигурация успешно загружена.")
