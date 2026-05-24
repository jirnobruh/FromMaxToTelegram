import logging
from maxlib import MaxClient, Message
from config import MAX_TOKEN, MAX_CHAT_IDS
from telegram_sender import send_text_to_telegram, send_photo_to_telegram, send_document_to_telegram

logger = logging.getLogger(__name__)

def main():
    """Основная функция запуска бота."""
    logger.info("Запуск бота...")
    client = MaxClient(MAX_TOKEN)

    @client.on_connect
    def on_connect():
        if client.me:
            logger.info(f"Успешное подключение к MAX: {client.me.contact.names[0].name} ({client.me.contact.phone})")
        else:
            logger.error("Не удалось получить информацию о пользователе MAX.")

    @client.on_message
    def on_message(message: Message):
        if message.chat.id not in MAX_CHAT_IDS or message.status == "REMOVED":
            return

        logger.info(f"Получено новое сообщение в чате MAX (ID: {message.chat.id})")

        author_name = message.user.contact.names[0].name
        message_text = message.text or ""
        
        # Обработка пересланных сообщений
        if "link" in message.kwargs.keys() and message.kwargs["link"]["type"] == "FORWARD":
            forwarded_from = client.get_user(id=message.kwargs["link"]["message"]["sender"]).contact.names[0].name
            author_name = f"{author_name} (переслано от {forwarded_from})"
            message_text = message.kwargs["link"]["message"]["text"] or ""
            message.attaches = message.kwargs["link"]["message"]["attaches"]

        # Обработка ответов
        if "link" in message.kwargs.keys() and message.kwargs["link"]["type"] == "REPLY":
            # В MaxLib нет прямого доступа к тексту ответа, это нужно будет доработать
            # или найти обходной путь, если это возможно.
            # Пока просто добавим информацию об ответе.
            message_text = f"<i>В ответ на другое сообщение</i>\n\n{message_text}"

        full_caption = f"<b>{author_name}</b>\n{message_text}"

        # Обработка вложений
        if not message.attaches:
            if message_text:
                send_text_to_telegram(full_caption)
        else:
            for attach in message.attaches:
                if attach["_type"] == "PHOTO":
                    send_photo_to_telegram(attach["baseUrl"], full_caption)
                elif attach["_type"] == "FILE":
                    send_document_to_telegram(attach["baseUrl"], full_caption, attach["name"])
                # Можно добавить обработку других типов вложений (видео, аудио и т.д.)
                else:
                    unsupported_message = f"{full_caption}\n\n<i>[Неподдерживаемое вложение: {attach['_type']}]</i>"
                    send_text_to_telegram(unsupported_message)

    try:
        client.run()
    except Exception as e:
        logger.critical(f"Критическая ошибка в работе клиента MAX: {e}", exc_info=True)

if __name__ == "__main__":
    main()
