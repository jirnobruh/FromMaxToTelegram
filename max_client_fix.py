import json
from websockets.sync.client import connect
from maxlib import MaxClient
from maxlib.classes import User, Contact
import maxlib.classes

# --- МОНКИ-ПАТЧ (Monkey Patch) ДЛЯ КЛАССА Contact ---
# Сервер MAX начал отдавать новые поля (например, registrationTime),
# о которых старая библиотека не знает. Чтобы не переписывать каждый метод
# библиотеки (get_user, connect и т.д.), мы один раз патчим сам конструктор Contact,
# чтобы он просто игнорировал это поле.

original_contact_init = Contact.__init__

def patched_contact_init(self, client, **kwargs):
    kwargs.pop('registrationTime', None)  # Безопасно удаляем новое поле
    # Если в будущем появятся другие неизвестные поля, их тоже можно будет удалять здесь
    original_contact_init(self, client, **kwargs)

# Заменяем оригинальный конструктор на наш исправленный
maxlib.classes.Contact.__init__ = patched_contact_init


class PatchedMaxClient(MaxClient):
    def connect(self, _f=None):
        """
        Переопределенный метод подключения, который добавляет необходимые заголовки
        для предотвращения ошибки 'HTTP 403 Forbidden'.
        """
        if self._connected:
            return
        
        headers = [
            ("Origin", "https://web.oneme.ru"),
            ("Pragma", "no-cache"),
            ("Cache-Control", "no-cache"),
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
            "ver": 11,
            "cmd": 0,
            "seq": self.seq,
            "opcode": 19, 
            "payload": {
                "interactive": True,
                "token": self.auth_token,
                "chatsSync": 0,
                "contactsSync": 0,
                "presenceSync": 0,
                "draftsSync": 0,
                "chatsCount": 40
            }
        }))

        response = json.loads(self.websocket.recv())
        if 'payload' in response and 'profile' in response['payload']:
            # Теперь нам не нужно удалять registrationTime здесь,
            # так как наш патч (выше) обработает это автоматически для всех пользователей
            usr = User(self, response['payload']['profile'])
            self.me = usr
        
        self._connected = True

        if self._on_connect:
            self._on_connect()
