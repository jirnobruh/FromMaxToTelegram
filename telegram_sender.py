import requests
import logging
from config import TG_BOT_TOKEN, TG_CHAT_ID, TG_TOPIC_ID

logger = logging.getLogger(__name__)

def send_text_to_telegram(text):
    """Отправляет текстовое сообщение в Telegram."""
    api_url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    if TG_TOPIC_ID:
        payload["message_thread_id"] = TG_TOPIC_ID
    
    try:
        response = requests.post(api_url, data=payload)
        response.raise_for_status()
        logger.info("Текстовое сообщение успешно отправлено в Telegram.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при отправке текстового сообщения в Telegram: {e}")

def send_photo_to_telegram(photo_url, caption):
    """Отправляет фото в Telegram."""
    api_url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendPhoto"
    payload = {
        "chat_id": TG_CHAT_ID,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "HTML"
    }
    if TG_TOPIC_ID:
        payload["message_thread_id"] = TG_TOPIC_ID

    try:
        response = requests.post(api_url, data=payload)
        response.raise_for_status()
        logger.info("Фото успешно отправлено в Telegram.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при отправке фото в Telegram: {e}")

def send_document_to_telegram(document_url, caption, file_name):
    """Скачивает файл и отправляет его как документ в Telegram."""
    try:
        # Скачиваем файл
        file_response = requests.get(document_url, stream=True)
        file_response.raise_for_status()
        
        # Отправляем файл
        api_url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendDocument"
        files = {'document': (file_name, file_response.content)}
        payload = {
            'chat_id': TG_CHAT_ID,
            'caption': caption,
            'parse_mode': 'HTML'
        }
        if TG_TOPIC_ID:
            payload['message_thread_id'] = TG_TOPIC_ID
            
        response = requests.post(api_url, data=payload, files=files)
        response.raise_for_status()
        logger.info(f"Документ '{file_name}' успешно отправлен в Telegram.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при отправке документа в Telegram: {e}")
