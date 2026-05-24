import logging
import threading
from max_client_fix import PatchedMaxClient
from config import MAX_TOKEN, MAX_CHAT_IDS
from telegram_sender import (
    send_text_to_telegram,
    send_photo_to_telegram,
    send_media_group_to_telegram
)
import urllib3
from maxlib.classes import User


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)

def process_raw_message(client, payload):
    try:
        chat_id = payload.get('chatId')
        message_data = payload.get('message', {})

        if not chat_id or not message_data or chat_id not in MAX_CHAT_IDS:
            return

        logger.info(f"Получено новое сообщение в чате MAX (ID: {chat_id}).")

        # 1. Определяем отправителя
        sender_id = message_data.get("sender")
        author_name = "Неизвестный отправитель"

        if sender_id:
            try:
                user = client.contacts.get(sender_id)
                if user and user.contact and user.contact.names:
                    author_name = user.contact.names[0].name
            except Exception as e:
                logger.error(f"Ошибка получения имени отправителя {sender_id}: {e}")

        # 2. Основной текст и вложения
        message_text = message_data.get('text', '') or ""
        attaches = message_data.get('attaches', [])

        # 3. Пересланное сообщение
        link = message_data.get('link')
        if link and link.get('type') == 'FORWARD':
            forwarded_message = link.get('message', {})

            fwd_sender = forwarded_message.get("sender")
            if fwd_sender:
                try:
                    fwd_user = client.contacts.get(fwd_sender)
                    if fwd_user and fwd_user.contact and fwd_user.contact.names:
                        fwd_name = fwd_user.contact.names[0].name
                        author_name = f"{author_name} (переслано от {fwd_name})"
                except Exception as e:
                    logger.error(f"Ошибка получения имени пересланного отправителя {fwd_sender}: {e}")

            message_text = forwarded_message.get("text", "") or ""
            attaches = forwarded_message.get("attaches", [])

        # 4. Формируем подпись
        full_caption = f"<b>{author_name}</b>\n{message_text}"

        photos = []
        unsupported_files = []

        for attach in attaches:
            if attach.get("_type") == "PHOTO" and attach.get("baseUrl"):
                photos.append(attach["baseUrl"])
            elif attach.get("name"):
                unsupported_files.append(attach["name"])

        # 5. Отправка в Telegram
        text_sent = False

        if photos:
            if len(photos) > 1:
                send_media_group_to_telegram(photos, full_caption)
            else:
                send_photo_to_telegram(photos[0], full_caption)
            text_sent = True

        if unsupported_files and not photos:
            full_caption += "\n\n<i>[Прикреплен файл: " + ", ".join(unsupported_files) + "]</i>"
            send_text_to_telegram(full_caption)
            text_sent = True

        elif unsupported_files and photos:
            send_text_to_telegram(f"<b>{author_name}</b>\n<i>[Прикреплен файл: {', '.join(unsupported_files)}]</i>")

        if not text_sent and message_text.strip():
            send_text_to_telegram(full_caption)

    except Exception as e:
        logger.error(f"Критическая ошибка при обработке сообщения: {e}", exc_info=True)


def main():
    logger.info("Запуск бота...")
    client = PatchedMaxClient(MAX_TOKEN)

    @client.on_connect
    def on_connect():
        if client.me:
            logger.info(f"Успешное подключение к MAX: {client.me.contact.names[0].name} ({client.me.contact.phone})")
        else:
            logger.error("Не удалось получить информацию о пользователе MAX.")

    @client.on_raw_message
    def on_raw_message_handler(client, payload):
        # Запускаем обработку в потоке, чтобы не блокировать слушатель
        thread = threading.Thread(target=process_raw_message, args=(client, payload))
        thread.daemon = True
        thread.start()

    try:
        client.run()
        while True:
            threading.Event().wait(timeout=60)
    except KeyboardInterrupt:
        logger.info("Бот останавливается...")
    except Exception as e:
        logger.critical(f"Критическая ошибка в работе клиента MAX: {e}", exc_info=True)

if __name__ == "__main__":
    main()