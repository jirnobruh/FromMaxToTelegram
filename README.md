# FromMaxToTelegram

<p align="center">
  <b>Асинхронный шлюз-бот для надежной пересылки сообщений, фотографий и документов из мессенджера MAX в Telegram</b><br>
  <i>(Каналы, группы и топики/темы форумов)</i>
</p>

<p align="center">
  <a href="https://github.com/jirnobruh/FromMaxToTelegram"><img src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg" alt="Python 3.10+"></a>
  <a href="https://github.com/aiogram/aiogram"><img src="https://img.shields.io/badge/aiogram-3.x-2CA5E0.svg" alt="aiogram 3.x"></a>
  <a href="https://pypi.org/project/max-library/"><img src="https://img.shields.io/badge/powered%20by-max--library-007ACC.svg" alt="max-library"></a>
  <a href="https://github.com/jirnobruh/FromMaxToTelegram/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License MIT"></a>
</p>

---

## 📌 О проекте

**FromMaxToTelegram** — это высоконадежный production-бот для организации моста между корпоративным мессенджером **MAX** (`web.oneme.ru`) и **Telegram**.

Бот работает на базе асинхронной библиотеки [max-library](https://github.com/jirnobruh/max-library) и фреймворка [aiogram 3.x](https://github.com/aiogram/aiogram). Он решает проблему нестабильности старых синхронных клиентов, работая неделями без зависаний и утечек ресурсов благодаря правильному управлению жизненным циклом WebSocket-соединения.

---

## ✨ Возможности

- 🚀 **Высокая стабильность и отказоустойчивость:** Асинхронный неблокирующий WebSocket-клиент с фоновым heartbeat и автоматическим восстановлением соединения при обрывах сети.
- 💬 **Форматирование сообщений:**
  - Преобразование форматирования с безопасным экранированием HTML.
  - Подстановка автора (имя, телефон, никнейм).
  - Красивое оформление ответов (`REPLY`) и пересланных сообщений (`FORWARD`).
- 🖼️ **Медиа и альбомы:**
  - Одиночные изображения.
  - Автоматическая группировка пачек фотографий в нативные Telegram Media Groups (до 10 изображений в одном сообщении).
- 📎 **Загрузка и отправка файлов:**
  - Прямое разрешение URL скачивания через RPC протокол MAX (Opcode 88).
  - Потоковое асинхронное скачивание файлов и отправка в Telegram как нативных документов (`send_document`).
  - Fallback-режим: если файл превышает лимит Telegram или недоступен, к сообщению аккуратно прикрепляется список файлов `Необработанные файлы: {file.pdf, doc.docx}`.
- 🧠 **Кэш профилей пользователей:** Встроенный TTL/LRU-кэш информации об отправителях снижает нагрузку на сеть и ускоряет доставку сообщений.
- 🗄️ **Умное логирование:**
  - Отдельный файл лога на каждый запуск терминала (`session_YYYY-MM-DD_HH-MM-SS.log`).
  - Ограничение суммарного размера директории логов (по умолчанию 1024 МБ) с автоудалением старых файлов.
  - Автоматическая нарезка файлов по 100 МБ для предотвращения создания огромных нечитаемых файлов.
  - Перехват неотловленных исключений (`sys.excepthook`) и зеркалирование вывода в консоль.
- 🔀 **Гибкая маршрутизация (`CHAT_MAPPING`):**
  - Поддержка одиночных чатов и топиков форумов Telegram (`TG_TOPIC_ID`).
  - Возможность маршрутизировать разные чаты MAX в разные Telegram-чаты и темы через JSON-конфигурацию.

---

## 🛠️ Установка и запуск

### 1. Клонирование репозитория

```bash
git clone https://github.com/jirnobruh/FromMaxToTelegram.git
cd FromMaxToTelegram
```

### 2. Создание виртуального окружения

```bash
python -m venv .venv

# Для Windows:
.venv\Scripts\activate

# Для Linux/macOS:
source .venv/bin/activate
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

> **Примечание:** Бот использует официальный SDK [max-library](https://pypi.org/project/max-library/):
> ```bash
> pip install max-library
> ```

---

## ⚙️ Конфигурация (.env)

Создайте файл `.env` в корне проекта бота (или скопируйте `.env.example`):

```ini
# Авторизационный токен мессенджера MAX
MAX_TOKEN=your_max_token_here

# Список отслеживаемых чатов MAX (ID через запятую или JSON-массив)
MAX_CHAT_IDS=123456789,987654321

# Данные Telegram бота
TG_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TG_CHAT_ID=-1001234567890

# Опционально: ID темы/топика в супергруппе Telegram (форуме)
TG_TOPIC_ID=

# Опционально: ID администратора для уведомлений о запуске/ошибках
MONITOR_ID=

# Опционально: расширенный маппинг чатов (JSON)
# CHAT_MAPPING={"123456789": {"chat_id": -1001234567890, "topic_id": 42}}

# Параметры логирования
LOGS_DIR=logs
MAX_LOGS_DIR_SIZE_MB=1024
MAX_LOG_FILE_SIZE_MB=100
LOG_LEVEL=INFO
```

---

## 🚀 Запуск бота

### Windows (через скрипт):
Просто запустите файл:
```bat
start_bot.bat
```

### Вручную из терминала:
```bash
python -m src.main
```

---

## 🧪 Запуск тестов

Проект полностью покрыт модульными и интеграционными тестами (`pytest`):

```bash
pytest tests
```

---

## 📂 Структура проекта

```text
FromMaxToTelegram/
├── src/
│   ├── config.py       # Валидация настроек и .env (Pydantic Settings)
│   ├── forwarder.py    # Логика загрузки файлов, альбомов и отправки в Telegram
│   ├── formatter.py    # Форматирование текста, авторов и цитат в HTML
│   ├── cache.py        # Кэш профилей пользователей
│   ├── logger.py       # Сессионный логгер с ротацией и квотой 1024 МБ
│   └── main.py         # Точка входа, инициализация клиентов и хэндлеров
├── tests/              # Набор тестов (pytest-asyncio)
├── requirements.txt    # Зависимости проекта
├── start_bot.bat       # Скрипт быстрого запуска для Windows
└── README.md
```

---

## 📄 Лицензия

Проект распространяется под лицензией [MIT](LICENSE).
Автор: **[jirnobruh](https://github.com/jirnobruh)**.
Библиотека протокола: **[max-library](https://github.com/jirnobruh/max-library)**.
