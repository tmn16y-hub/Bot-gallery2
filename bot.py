import os
import base64
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime

import requests


# =========================
# НАСТРОЙКИ
# =========================

TOKEN = os.environ["BOT_TOKEN"]
WEBAPP_URL = os.environ["WEBAPP_URL"].rstrip("/")
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]

REPO = "tmn16y-hub/Bot-gallery2"
BRANCH = "main"

TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"
GITHUB_API = f"https://api.github.com/repos/{REPO}"

GITHUB_HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}


# =========================
# PORT ДЛЯ RENDER
# =========================

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

    def log_message(self, format, *args):
        pass


def start_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"Web server started on port {port}")
    server.serve_forever()


# =========================
# TELEGRAM
# =========================

def telegram(method, data):
    r = requests.post(
        f"{TELEGRAM_API}/{method}",
        json=data,
        timeout=60
    )
    r.raise_for_status()
    return r.json()


def send_message(chat_id, text):
    telegram("sendMessage", {
        "chat_id": chat_id,
        "text": text
    })


def send_start(chat_id):
    keyboard = {
        "keyboard": [[
            {
                "text": "Перейти",
                "web_app": {
                    "url": WEBAPP_URL
                }
            }
        ]],
        "resize_keyboard": True,
        "is_persistent": True
    }

    telegram("sendMessage", {
        "chat_id": chat_id,
        "text": "Привет, переходи в галерею.",
        "reply_markup": keyboard
    })


# =========================
# GITHUB
# =========================

def github_get(path):
    r = requests.get(
        f"{GITHUB_API}/contents/{path}",
        headers=GITHUB_HEADERS,
        params={"ref": BRANCH},
        timeout=60
    )

    if r.status_code == 404:
        return None

    r.raise_for_status()
    return r.json()


def github_upload(path, content, message):
    existing = github_get(path)

    data = {
        "message": message,
        "content": base64.b64encode(content).decode(),
        "branch": BRANCH
    }

    if existing:
        data["sha"] = existing["sha"]

    r = requests.put(
        f"{GITHUB_API}/contents/{path}",
        headers=GITHUB_HEADERS,
        json=data,
        timeout=60
    )

    r.raise_for_status()


def get_script():
    data = github_get("script.js")

    if not data:
        raise Exception("script.js не найден в GitHub")

    content = base64.b64decode(
        data["content"]
    ).decode("utf-8")

    return content, data["sha"]


def update_script(photo_path, username, time_text):
    script, sha = get_script()

    new_line = (
        f'  {{src:"{photo_path}", '
        f'user:"{username}", '
        f'time:"{time_text}"}},\n'
    )

    marker = "const photos = ["

    if marker not in script:
        raise Exception(
            "В script.js не найдено 'const photos = ['"
        )

    script = script.replace(
        marker,
        marker + "\n" + new_line,
        1
    )

    data = {
        "message": f"Add photo {photo_path}",
        "content": base64.b64encode(
            script.encode("utf-8")
        ).decode(),
        "branch": BRANCH,
        "sha": sha
    }

    r = requests.put(
        f"{GITHUB_API}/contents/script.js",
        headers=GITHUB_HEADERS,
        json=data,
        timeout=60
    )

    r.raise_for_status()


# =========================
# ОБРАБОТКА ФОТО
# =========================

def process_photo(message):
    chat_id = message["chat"]["id"]

    photos = message.get("photo")

    if not photos:
        return

    # Берём фотографию максимального качества
    photo = photos[-1]
    file_id = photo["file_id"]

    # Username
    user = message.get("from", {})

    if user.get("username"):
        username = "@" + user["username"]
    else:
        username = user.get("first_name", "Пользователь")

    # Время сообщения
    message_date = message.get("date")

    if message_date:
        dt = datetime.fromtimestamp(message_date)
        time_text = dt.strftime("%d.%m %H:%M")
    else:
        time_text = datetime.now().strftime("%d.%m %H:%M")

    print(
        f"Получено фото от {username}, "
        f"время {time_text}"
    )

    # Получаем информацию о файле Telegram
    file_info = telegram("getFile", {
        "file_id": file_id
    })

    file_path = file_info["result"]["file_path"]

    # Скачиваем фотографию
    file_url = (
        f"https://api.telegram.org/file/bot"
        f"{TOKEN}/{file_path}"
    )

    response = requests.get(
        file_url,
        timeout=60
    )

    response.raise_for_status()

    # Имя файла
    filename = (
        datetime.now().strftime("%Y%m%d_%H%M%S")
        + ".jpg"
    )

    github_photo_path = f"photos/{filename}"

    # Загружаем фотографию в GitHub
    github_upload(
        github_photo_path,
        response.content,
        f"Add photo {filename}"
    )

    # Добавляем её в script.js
    update_script(
        github_photo_path,
        username,
        time_text
    )

    send_message(
        chat_id,
        "Фото добавлено в галерею ✅\n\n"
        f"{username} · {time_text}"
    )

    print("Фото успешно добавлено")


# =========================
# ОСНОВНОЙ ЦИКЛ
# =========================

def main():
    print("Telegram bot started")

    offset = 0

    while True:
        updates = telegram("getUpdates", {
            "timeout": 50,
            "offset": offset
        }).get("result", [])

        for update in updates:
            offset = update["update_id"] + 1

            message = update.get("message", {})

            try:
                # Фотография
                if "photo" in message:
                    process_photo(message)
                    continue

                # Текстовые команды
                text = message.get("text", "")
                chat_id = message.get(
                    "chat", {}
                ).get("id")

                if chat_id and text in (
                    "/start",
                    "/gallery",
                    "Перейти"
                ):
                    send_start(chat_id)

            except Exception as e:
                print("ОШИБКА:", repr(e))

                if message.get("chat", {}).get("id"):
                    send_message(
                        message["chat"]["id"],
                        "Произошла ошибка при добавлении фото ❌"
                    )


# =========================
# ЗАПУСК
# =========================

if __name__ == "__main__":

    # Запускаем HTTP-сервер отдельно
    server_thread = threading.Thread(
        target=start_server,
        daemon=True
    )

    server_thread.start()

    # Запускаем Telegram
    main()
