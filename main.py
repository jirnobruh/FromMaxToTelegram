import logging
import threading
from max_client_fix import PatchedMaxClient
from maxlib import Message
from config import MAX_TOKEN, MAX_CHAT_IDS
from telegram_sender import send_text_to_telegram, send_photo_to_telegram, send_document_to_telegram
from filters import AnyFilter

logger = logging.getLogger(__name__)

def main():
    """Основная функция запуска бота."""
    logger.info("Запуск бота...")
    
    client = PatchedMaxClient(MAX_TOKEN)

    @client.on_connect
    def on_connect():
        if client.me:
            logger.info(f"Успешное подключение к MAX: {client.me.contact.names[0].name} ({client.me.contact.phone})")
        else:
            logger.error("Не удалось получить информацию о пользователе MAX.")

    @client.on_message(AnyFilter())
    def on_message(client, message: Message):
        status = getattr(message, 'status', None)
        try:
            chat_id = message.chat.id
        except AttributeError:
            return

        if chat_id not in MAX_CHAT_IDS or status == "REMOVED":
            return

        logger.info(f"Получено новое сообщение в чате MAX (ID: {chat_id})")

        # 1. Инициализируем переменные из основного сообщения
        try:
            author_name = message.user.contact.names[0].name
        except (AttributeError, IndexError):
            author_name = "Неизвестный отправитель"
        
        message_text = getattr(message, 'text', '') or ""
        attaches = getattr(message, 'attaches', [])

        # 2. Безопасно проверяем, есть ли пересланное или ответное сообщение
        kwargs = getattr(message, 'kwargs', {})
        link = kwargs.get('link')

        if link:
            # 3. Обработка пересланных сообщений
            if link.get('type') == 'FORWARD':
                forwarded_message = link.get('message', {})
                try:
                    forwarded_from_id = forwarded_message.get('sender')
                    if forwarded_from_id:
                        forwarded_from_user = client.get_user(id=forwarded_from_id)
                        forwarded_from_name = forwarded_from_user.contact.names[0].name
                        author_name = f"{author_name} (переслано от {forwarded_from_name})"
                    else:
                        author_name = f"{author_name} (пересланное сообщение)"
                except Exception as e:
                    logger.warning(f"Не удалось получить имя автора пересланного сообщения: {e}")
                    author_name = f"{author_name} (пересланное сообщение)"
                
                # Перезаписываем текст и вложения данными из пересланного сообщения
                message_text = forwarded_message.get("text", "") or ""
                attaches = forwarded_message.get("attaches", [])

            # 4. Обработка ответов
            elif link.get('type') == 'REPLY':
                message_text = f"<i>В ответ на другое сообщение</i>\n\n{message_text}"

        # 5. Готовим и отправляем сообщение в Telegram
        full_caption = f"<b>{author_name}</b>\n{message_text}"
        
        if not attaches:
            # Отправляем, только если есть что отправлять (непустой текст)
            if message_text.strip():
                send_text_to_telegram(full_caption)
        else:
            for attach in attaches:
                attach_type = attach.get("_type") if isinstance(attach, dict) else getattr(attach, "type", "UNKNOWN")
                base_url = attach.get("baseUrl") if isinstance(attach, dict) else getattr(attach, "base_url", None)
                file_name = attach.get("name") if isinstance(attach, dict) else getattr(attach, "name", "file")

                if not base_url:
                    continue

                if attach_type == "PHOTO":
                    send_photo_to_telegram(base_url, full_caption)
                elif attach_type == "FILE":
                    send_document_to_telegram(base_url, full_caption, file_name)
                else:
                    unsupported_message = f"{full_caption}\n\n<i>[Неподдерживаемое вложение: {attach_type}]</i>"
                    send_text_to_telegram(unsupported_message)

    try:
        client.run()
        threading.Event().wait()
    except Exception as e:
        logger.critical(f"Критическая ошибка в работе клиента MAX: {e}", exc_info=True)

if __name__ == "__main__":
    main()
