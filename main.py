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

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)

def process_raw_message(client, payload):
    """
    Обрабатывает 'сырой' payload сообщения, полученный в обход maxlib.
    """
    try:
        chat_id = payload.get('chatId')
        message_data = payload.get('message', {})
        
        if not chat_id or not message_data or chat_id not in MAX_CHAT_IDS:
            return

        logger.info(f"Получено новое сообщение в чате MAX (ID: {chat_id}). Начинаю ручную обработку.")

        # 1. Получаем автора изначального сообщения
        sender_id = message_data.get('sender')
        try:
            author_user = client.get_user(id=sender_id)
            author_name = author_user.contact.names[0].name
        except Exception:
            author_name = "Неизвестный отправитель"

        # 2. Инициализируем переменные из основного сообщения
        message_text = message_data.get('text', '') or ""
        attaches = message_data.get('attaches', [])

        # 3. Ищем и обрабатываем пересланное сообщение
        link = message_data.get('link')
        if link and link.get('type') == 'FORWARD':
            forwarded_message = link.get('message', {})
            try:
                forwarded_from_id = forwarded_message.get('sender')
                if forwarded_from_id:
                    forwarded_from_user = client.get_user(id=forwarded_from_id)
                    author_name = f"{author_name} (переслано от {forwarded_from_user.contact.names[0].name})"
            except Exception:
                author_name = f"{author_name} (пересланное сообщение)"
            
            # Перезаписываем текст и вложения данными из пересланного сообщения
            message_text = forwarded_message.get("text", "") or ""
            attaches = forwarded_message.get("attaches", [])
            logger.info("Сообщение определено как пересылка. Используются данные вложенного сообщения.")

        # 4. Формируем подпись и обрабатываем вложения
        full_caption = f"<b>{author_name}</b>\n{message_text}"
        
        photos = []
        unsupported_files = []

        for attach in attaches:
            attach_type = attach.get("_type")
            # Фотографии (имеют baseUrl)
            if attach_type == "PHOTO" and attach.get("baseUrl"):
                photos.append(attach["baseUrl"])
            # Файлы (не имеют baseUrl, но имеют имя)
            elif attach.get("name"):
                unsupported_files.append(attach["name"])
        
        logger.info(f"Найдено {len(photos)} фото и {len(unsupported_files)} файлов/неподдерживаемых вложений.")

        # 5. Логика отправки
        text_sent = False
        
        if photos:
            if len(photos) > 1:
                send_media_group_to_telegram(photos, full_caption)
            else:
                send_photo_to_telegram(photos[0], full_caption)
            text_sent = True

        if unsupported_files:
            unsupported_text = "\n\n<i>[Прикреплен файл: " + ", ".join(unsupported_files) + "]</i>"
            if not text_sent:
                full_caption += unsupported_text
            else: # Если текст уже ушел с фото, отправляем уведомление о файлах отдельно
                send_text_to_telegram(f"<b>{author_name}</b>{unsupported_text}")
            text_sent = True

        # Отправляем текст, если он есть и еще не был отправлен
        if not text_sent and message_text.strip():
            send_text_to_telegram(full_caption)
            
        logger.info(f"Обработка сообщения в чате MAX (ID: {chat_id}) завершена.")
        
    except Exception as e:
        logger.error(f"Критическая ошибка при ручной обработке сообщения: {e}", exc_info=True)


def main():
    logger.info("Запуск бота...")
    client = PatchedMaxClient(MAX_TOKEN)

    @client.on_connect
    def on_connect():
        if client.me:
            logger.info(f"Успешное подключение к MAX: {client.me.contact.names[0].name} ({client.me.contact.phone})")
        else:
            logger.error("Не удалось получить информацию о пользователе MAX.")

    # --- ГЛАВНОЕ ИЗМЕНЕНИЕ ---
    # Регистрируем наш новый обработчик сырых данных
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
