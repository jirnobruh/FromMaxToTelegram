import requests
import logging
import json
from config import TG_BOT_TOKEN, TG_CHAT_ID, TG_TOPIC_ID

logger = logging.getLogger(__name__)

def _send_request(method, data, files=None):
    """Вспомогательная функция для отправки запросов к Telegram API."""
    api_url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/{method}"
    
    if TG_TOPIC_ID:
        data["message_thread_id"] = TG_TOPIC_ID
        
    try:
        response = requests.post(api_url, data=data, files=files)
        response.raise_for_status()
        logger.info(f"Успешно отправлено в Telegram через метод {method}.")
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при отправке в Telegram через метод {method}: {e}")
        if e.response is not None:
            logger.error(f"Ответ сервера Telegram: {e.response.text}")
    return None

def send_text_to_telegram(text):
    """Отправляет текстовое сообщение в Telegram."""
    payload = {"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "HTML"}
    _send_request("sendMessage", payload)

def send_photo_to_telegram(photo_url, caption):
    """Отправляет одно фото в Telegram."""
    payload = {"chat_id": TG_CHAT_ID, "photo": photo_url, "caption": caption, "parse_mode": "HTML"}
    _send_request("sendPhoto", payload)

def send_media_group_to_telegram(photos_urls, caption):
    """Отправляет группу фотографий (альбом) в Telegram."""
    if not photos_urls:
        return

    media = []
    for i, url in enumerate(photos_urls):
        item = {"type": "photo", "media": url}
        if i == 0:
            item["caption"] = caption
            item["parse_mode"] = "HTML"
        media.append(item)

    for i in range(0, len(media), 10):
        chunk = media[i:i+10]
        payload = {"chat_id": TG_CHAT_ID, "media": json.dumps(chunk)}
        _send_request("sendMediaGroup", payload)

def send_document_to_telegram(document_url, caption, file_name):
    """Скачивает файл и отправляет его как документ в Telegram."""
    logger.info(f"Начинаю скачивание файла: {file_name} ({document_url})")
    try:
        # --- ИСПРАВЛЕНИЕ: Добавляем verify=False, чтобы обойти ошибку SSL ---
        # Также добавляем заголовок, имитирующий браузер, на всякий случай
        headers = {'User-Agent': 'Mozilla/5.0'}
        logger.warning("Отключаю проверку SSL-сертификата для скачивания файла.")
        file_response = requests.get(document_url, stream=True, timeout=60, verify=False, headers=headers)
        file_response.raise_for_status()
        
        logger.info(f"Файл '{file_name}' успешно скачан, отправляю в Telegram...")
        
        files = {'document': (file_name, file_response.content)}
        payload = {'chat_id': TG_CHAT_ID, 'caption': caption, 'parse_mode': 'HTML'}
        _send_request("sendDocument", payload, files=files)

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при скачивании или отправке документа '{file_name}': {e}")
