# Tool Check VNC

This repository contains a simple Python script that reads a list of VNC
servers from `results.txt`, connects to each server using `vncdotool`, grabs a
screenshot and sends the image to a Telegram chat.

## Requirements

- Python 3.8+
- [`vncdotool`](https://github.com/sibson/vncdotool)
- [`python-telegram-bot`](https://github.com/python-telegram-bot/python-telegram-bot)

Install the dependencies using pip:

```bash
pip install vncdotool python-telegram-bot
```

## Preparing `results.txt`

Each line in `results.txt` must follow the format:

```
<ip>:<port>-<password>-<name>
```

Example:

```
192.168.0.10:5900-null-[My Server]
```

Only the first two dashes are treated as separators, so dashes in `<name>` are
allowed.

## Telegram configuration

Set the following environment variables before running the script:

- `TELEGRAM_BOT_TOKEN`: token of your Telegram bot
- `TELEGRAM_CHAT_ID`: target chat ID

## Running the script

After configuring the environment variables and preparing `results.txt`, run:

```bash
python tool.py
```

The script will attempt to connect to each VNC server, capture a screenshot and
send it to the configured Telegram chat.

