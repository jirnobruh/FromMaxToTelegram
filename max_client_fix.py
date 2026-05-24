import json
import logging
import threading
import requests
from websockets.sync.client import connect
from websockets.exceptions import ConnectionClosedError
from maxlib import MaxClient
from maxlib.classes import User, Contact
import maxlib.classes
import time

logger = logging.getLogger(__name__)
original_contact_init = Contact.__init__


def patched_contact_init(self, client, **kwargs):
    kwargs.pop('registrationTime', None)
    original_contact_init(self, client, **kwargs)
maxlib.classes.Contact.__init__ = patched_contact_init

class PatchedMaxClient(MaxClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._raw_message_handler = None
        self.contacts = {}

    def on_raw_message(self, func):
        """Новый декоратор для регистрации обработчика сырых данных."""
        self._raw_message_handler = func
        return func

    def api_call(self, cmd, payload):
        """
        Правильный вызов REST API MAX.
        """
        url = "https://api.oneme.ru/api"
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }

        body = {
            "cmd": cmd,
            "payload": payload
        }

        response = requests.post(url, headers=headers, json=body, timeout=10)
        response.raise_for_status()

        data = response.json()
        return data.get("payload")

    def _listener(self):
        """
        Полностью переопределенный слушатель.
        Он перехватывает сырые данные и передает их нашему обработчику,
        в обход сломанного парсера maxlib.
        """
        logger.info("Запущен кастомный слушатель сообщений.")
        while not getattr(self, '_t_stop', False):
            try:
                raw_recv = self.websocket.recv()
                recv = json.loads(raw_recv)

                opcode = recv.get("opcode")
                payload = recv.get("payload")

                # Если это новое сообщение и у нас есть обработчик
                if opcode == 128 and self._raw_message_handler:
                    # Передаем payload напрямую в наш обработчик в main.py
                    self._raw_message_handler(self, payload)

                if opcode == 130:  # полный список контактов
                    contacts = payload.get("contacts", [])
                    for c in contacts:
                        try:
                            user = User(self, c)
                            self.contacts[user.id] = user
                        except Exception as e:
                            logger.error(f"Ошибка обработки контакта: {e}")

                if opcode == 131:  # обновление контакта
                    c = payload.get("contact")
                    if c:
                        try:
                            user = User(self, c)
                            self.contacts[user.id] = user
                        except Exception as e:
                            logger.error(f"Ошибка обновления контакта: {e}")

            except ConnectionClosedError:
                logger.warning("Соединение WebSocket было закрыто. Попытка переподключения...")
                self._connected = False
                time.sleep(5)
                if not getattr(self, '_t_stop', False):
                    try:
                        self.connect()
                    except Exception as e:
                        logger.error(f"Не удалось переподключиться: {e}")
            except Exception as e:
                logger.error(f"Критическая ошибка в кастомном слушателе: {e}", exc_info=True)

    def connect(self, _f=None):
        if self._connected:
            return

        headers = [
            ("Origin", "https://web.oneme.ru"),
            ("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36")
        ]

        self.websocket = connect(
            "wss://ws-api.oneme.ru/websocket",
            additional_headers=headers,
            ping_interval=25,
            ping_timeout=10
        )

        self.websocket.send(self.user_agent)
        self.websocket.recv()

        if _f:
            return

        self.websocket.send(json.dumps({
            "ver": 11, "cmd": 0, "seq": self.seq, "opcode": 19,
            "payload": {
                "interactive": True,
                "token": self.auth_token,
                "chatsSync": 0,
                "contactsSync": 1,
                "presenceSync": 0,
                "draftsSync": 0,
                "chatsCount": 40
            }
        }))

        response = json.loads(self.websocket.recv())
        if 'payload' in response and 'profile' in response['payload']:
            usr = User(self, response['payload']['profile'])
            self.me = usr

        self._connected = True

        if self._on_connect:
            self._on_connect()
