import os
import base64
import requests
from datetime import datetime

TOKEN = os.environ["BOT_TOKEN"]
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]

REPO = "tmn16y-hub/melon-gallery"
BRANCH = "main"

API = f"https://api.telegram.org/bot{TOKEN}/"
GITHUB_API = f"https://api.github.com/repos/{REPO}"

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}


def api(method, data):
    r = requests.post(API + method, json=data, timeout=60)
    r.raise_for_status()
    return r.json()


def github_get(path):
    r = requests.get(
        f"{GITHUB_API}/contents/{path}",
        headers=HEADERS,
        params={"ref": BRANCH},
        timeout=60
    )
    r.raise_for_status()
    return r.json()


def github_upload(path, content, message):
    url = f"{GITHUB_API}/contents/{path}"

    try:
        old = github_get(path)
        sha = old["sha"]
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            sha = None
        else:
            raise

    data = {
        "message": message,
        "content": base64.b64encode(content).decode(),
        "branch": BRANCH
    }

    if sha:
        data["sha"] = sha

    r = requests.put(
        url,
        headers=HEADERS,
        json=data,
        timeout=60
    )
    r.raise_for_status()


def get_file(path):
    data = github_get(path)
    content = base64.b64decode(data["content"]).decode("utf-8")
    return content, data["sha"]


def update_script(photo_name, username, time_text):
    path = "script.js"

    script, sha = get_file(path)

    new_photo = (
        f'  {{src:"{photo_name}", '
        f'user:"{username}", '
        f'time:"{time_text}"}},\n'
    )

    marker = "const photos = [\n"

    if marker not in script:
        raise Exception("Не найден массив photos в script.js")

    script = script.replace(
        marker,
        marker + new_photo,
        1
    )

    data = {
        "message": f"Add photo {photo_name}",
        "content": base64.b64encode(
            script.encode("utf-8")
        ).decode(),
        "branch": BRANCH,
        "sha": sha
    }

    r = requests.put(
        f"{GITHUB_API}/contents/{path}",
        headers=HEADERS,
        json=data,
        timeout=60
    )
    r.raise_for_status()


def send_start(chat_id):
    keyboard = {
        "keyboard": [[
            {
                "text": "Перейти",
                "web_app": {
                    "url": os.environ["WEBAPP_URL"].rstrip("/")
                }
            }
        ]],
        "resize_keyboard": True,
        "is_persistent": True
    }

    api("sendMessage", {
        "chat_id": chat_id,
        "text": "Привет, переходи в галерею.",
        "reply_markup": keyboard
    })


def send_message(chat_id, text):
    api("sendMessage", {
        "chat_id": chat_id,
        "text": text
    })


def process_photo(msg):
    chat_id = msg["chat"]["id"]

    photos = msg.get("photo", [])

    if not photos:
        return

    photo = photos[-1]
    file_id = photo["file_id"]

    username = msg.get("from", {}).get("username")

    if username:
        username = "@" + username
    else:
        username = msg.get("from", {}).get("first_name", "Пользователь")

    message_date = msg.get("date")

    if message_date:
        dt = datetime.fromtimestamp(message_date)
        time_text = dt.strftime("%d.%m %H:%M")
    else:
        time_text = ""

    file_info = api("getFile", {
        "file_id": file_id
    })

    file_path = file_info["result"]["file_path"]

    file_url = (
        f"https://api.telegram.org/file/bot"
        f"{TOKEN}/{file_path}"
    )

    r = requests.get(file_url, timeout=60)
    r.raise_for_status()

    extension = os.path.splitext(file_path)[1]

    if not extension:
        extension = ".jpg"

    filename = (
        datetime.now().strftime("%Y%m%d_%H%M%S")
        + extension
    )

    github_path = f"photos/{filename}"

    github_upload(
        github_path,
        r.content,
        f"Add photo {filename}"
    )

    update_script(
        f"photos/{filename}",
        username,
        time_text
    )

    send_message(
        chat_id,
        f"Фото добавлено в галерею ✅\n"
        f"{username} · {time_text}"
    )


def main():
    offset = 0

    while True:
        updates = api("getUpdates", {
            "timeout": 50,
            "offset": offset
        }).get("result", [])

        for update in updates:
            offset = update["update_id"] + 1

            msg = update.get("message", {})

            if "photo" in msg:
                try:
                    process_photo(msg)
                except Exception as e:
                    print("Ошибка:", e)
                    send_message(
                        msg["chat"]["id"],
                        "Не удалось добавить фото ❌"
                    )

            text = msg.get("text", "")
            chat_id = msg.get("chat", {}).get("id")

            if chat_id and text in (
                "/start",
                "/gallery",
                "Перейти"
            ):
                send_start(chat_id)


if __name__ == "__main__":
    main()