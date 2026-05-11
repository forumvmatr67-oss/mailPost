import json
import hashlib
import os
from datetime import datetime

# Импортируем colorama для поддержки цвета в Windows
try:
    from colorama import init, Fore, Style
    init(autoreset=True)  # автоматический сброс цвета после каждого print
    GREEN = Fore.GREEN
    YELLOW = Fore.YELLOW
    RED = Fore.RED
    BLUE = Fore.BLUE
    RESET = Style.RESET_ALL
except ImportError:
    # Если colorama не установлен, используем обычный вывод без цветов
    GREEN = YELLOW = RED = BLUE = RESET = ''
    print("[Внимание] Для цветов установите: pip install colorama")

class MinecraftMail:
    def __init__(self, config_file='config.json'):
        self.config_file = config_file
        self._ensure_config()
        with open(config_file, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        self.users_file = self.config['users_file']
        self.messages_file = self.config['messages_file']
        self.counter_file = self.config['message_id_counter_file']
        self.current_user = None
        self._init_files()

    def _ensure_config(self):
        if not os.path.exists(self.config_file):
            default_config = {
                "users_file": "users.json",
                "messages_file": "messages.json",
                "message_id_counter_file": "msg_counter.json"
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)

    def _init_files(self):
        for file, default in [(self.users_file, []), (self.messages_file, []), (self.counter_file, {"next_id": 1})]:
            if not os.path.exists(file):
                with open(file, 'w', encoding='utf-8') as f:
                    json.dump(default, f, indent=4, ensure_ascii=False)

    def _hash(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def _load_users(self):
        with open(self.users_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_users(self, users):
        with open(self.users_file, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=4, ensure_ascii=False)

    def _load_messages(self):
        with open(self.messages_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_messages(self, messages):
        with open(self.messages_file, 'w', encoding='utf-8') as f:
            json.dump(messages, f, indent=4, ensure_ascii=False)

    def _next_id(self):
        with open(self.counter_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        nid = data['next_id']
        data['next_id'] += 1
        with open(self.counter_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        return nid

    def _color_print(self, color, text):
        print(f"{color}{text}{RESET}")

    # Команды
    def cmd_register(self, args):
        if len(args) != 2:
            self._color_print(YELLOW, "Использование: /register <ник> <пароль>")
            return
        username, password = args[0], args[1]
        users = self._load_users()
        if any(u['username'] == username for u in users):
            self._color_print(RED, f"[Ошибка] Игрок {username} уже зарегистрирован!")
            return
        users.append({'username': username, 'password': self._hash(password)})
        self._save_users(users)
        self._color_print(GREEN, f"[Успех] Игрок {username} зарегистрирован! Добро пожаловать на сервер!")

    def cmd_login(self, args):
        if len(args) != 2:
            self._color_print(YELLOW, "Использование: /login <ник> <пароль>")
            return
        username, password = args[0], args[1]
        users = self._load_users()
        hashed = self._hash(password)
        for u in users:
            if u['username'] == username and u['password'] == hashed:
                self.current_user = username
                self._color_print(GREEN, f"[Успех] Вы вошли как {username}")
                return
        self._color_print(RED, "[Ошибка] Неверный ник или пароль!")

    def cmd_logout(self, args):
        if self.current_user is None:
            self._color_print(YELLOW, "Вы не авторизованы.")
            return
        self._color_print(BLUE, f"Игрок {self.current_user} вышел из почтовой системы.")
        self.current_user = None

    def cmd_send(self, args):
        if self.current_user is None:
            self._color_print(RED, "Сначала войдите: /login <ник> <пароль>")
            return
        if len(args) < 3:
            self._color_print(YELLOW, "Использование: /send <получатель> <тема> <текст> (текст может быть с пробелами)")
            return
        to_user = args[0]
        subject = args[1]
        body = ' '.join(args[2:])
        users = self._load_users()
        if not any(u['username'] == to_user for u in users):
            self._color_print(RED, f"Игрок {to_user} не найден!")
            return
        msg_id = self._next_id()
        message = {
            'id': msg_id,
            'from': self.current_user,
            'to': to_user,
            'subject': subject,
            'body': body,
            'timestamp': datetime.now().isoformat(),
            'is_read': False
        }
        msgs = self._load_messages()
        msgs.append(message)
        self._save_messages(msgs)
        self._color_print(GREEN, f"[Почта] Письмо отправлено игроку {to_user} (ID: {msg_id})")

    def cmd_inbox(self, args):
        if self.current_user is None:
            self._color_print(RED, "Сначала войдите.")
            return
        msgs = self._load_messages()
        inbox = [m for m in msgs if m['to'] == self.current_user]
        if not inbox:
            self._color_print(BLUE, "Входящих писем нет. Отдыхайте!")
            return
        self._color_print(BLUE, f"========== Входящие ({self.current_user}) ==========")
        for m in inbox:
            status = "✔" if m['is_read'] else "✘"
            self._color_print(YELLOW, f"[{status}] ID:{m['id']} | От: {m['from']} | Тема: {m['subject']} | {m['timestamp'][:19]}")
        print("Для прочтения письма: /read <ID>")

    def cmd_read(self, args):
        if self.current_user is None:
            self._color_print(RED, "Сначала войдите.")
            return
        if len(args) != 1 or not args[0].isdigit():
            self._color_print(YELLOW, "Использование: /read <ID письма>")
            return
        msg_id = int(args[0])
        msgs = self._load_messages()
        for m in msgs:
            if m['id'] == msg_id and m['to'] == self.current_user:
                m['is_read'] = True
                self._save_messages(msgs)
                self._color_print(BLUE, f"От: {m['from']}\nТема: {m['subject']}\nДата: {m['timestamp']}\nТекст:\n{m['body']}")
                return
        self._color_print(RED, "Письмо не найдено или у вас нет доступа.")

    def cmd_outbox(self, args):
        if self.current_user is None:
            self._color_print(RED, "Сначала войдите.")
            return
        msgs = self._load_messages()
        outbox = [m for m in msgs if m['from'] == self.current_user]
        if not outbox:
            self._color_print(BLUE, "Исходящих писем нет.")
            return
        self._color_print(BLUE, "========== Исходящие ==========")
        for m in outbox:
            self._color_print(YELLOW, f"ID:{m['id']} | Кому: {m['to']} | Тема: {m['subject']} | {m['timestamp'][:19]}")

    def cmd_delete(self, args):
        if self.current_user is None:
            self._color_print(RED, "Сначала войдите.")
            return
        if len(args) != 1 or not args[0].isdigit():
            self._color_print(YELLOW, "Использование: /delete <ID письма>")
            return
        msg_id = int(args[0])
        msgs = self._load_messages()
        original_len = len(msgs)
        msgs = [m for m in msgs if not (m['id'] == msg_id and (m['from'] == self.current_user or m['to'] == self.current_user))]
        if len(msgs) < original_len:
            self._save_messages(msgs)
            self._color_print(GREEN, f"Письмо ID:{msg_id} удалено.")
        else:
            self._color_print(RED, "Не удалось удалить письмо (нет прав или не существует).")

    def cmd_help(self, args):
        self._color_print(BLUE, "=== Minecraft Почта Команды ===")
        commands = [
            "/register <ник> <пароль> - регистрация",
            "/login <ник> <пароль> - вход",
            "/logout - выход из аккаунта",
            "/send <получатель> <тема> <текст> - отправить письмо",
            "/inbox - показать входящие",
            "/read <ID> - прочитать письмо",
            "/outbox - показать отправленные",
            "/delete <ID> - удалить письмо",
            "/help - эта справка",
            "/exit - выйти из программы"
        ]
        for cmd in commands:
            self._color_print(GREEN, cmd)

    def run(self):
        self._color_print(GREEN, r"""
   __  _          _         _        _       _   
  / _\| | ___  __| |_ __   | |   ___| | __ _| |_ 
 / /  | |/ _ \/ _` | '_ \  | |  / _ \ |/ _` | __|
/ /___| |  __/ (_| | | | | | |_|  __/ | (_| | |_ 
\____/|_|\___|\__,_|_| |_| |____\___|_|\__,_|\__|
        Minecraft Mail System v1.0
        """)
        self._color_print(BLUE, "Введите /help для списка команд.\n")
        while True:
            try:
                prompt = f"{GREEN}[{self.current_user or 'Гость'}@MinecraftMail]{RESET} "
                cmd_line = input(prompt).strip()
                if not cmd_line:
                    continue
                if cmd_line.startswith('/'):
                    parts = cmd_line[1:].split()
                    cmd = parts[0].lower()
                    args = parts[1:]
                    if cmd == 'exit':
                        self._color_print(BLUE, "Выход из почтовой системы. До встречи на сервере!")
                        break
                    elif cmd == 'register':
                        self.cmd_register(args)
                    elif cmd == 'login':
                        self.cmd_login(args)
                    elif cmd == 'logout':
                        self.cmd_logout(args)
                    elif cmd == 'send':
                        self.cmd_send(args)
                    elif cmd == 'inbox':
                        self.cmd_inbox(args)
                    elif cmd == 'read':
                        self.cmd_read(args)
                    elif cmd == 'outbox':
                        self.cmd_outbox(args)
                    elif cmd == 'delete':
                        self.cmd_delete(args)
                    elif cmd == 'help':
                        self.cmd_help(args)
                    else:
                        self._color_print(RED, f"Неизвестная команда: {cmd}. Введите /help.")
                else:
                    self._color_print(RED, "Команды должны начинаться с /. Введите /help.")
            except KeyboardInterrupt:
                print()
                self._color_print(BLUE, "До свидания!")
                break
            except Exception as e:
                self._color_print(RED, f"Ошибка: {e}")

if __name__ == "__main__":
    app = MinecraftMail()
    app.run()
