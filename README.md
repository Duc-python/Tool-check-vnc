# Tool Check VNC

This project provides a small script that iterates over a list of VNC
servers, captures a screenshot from each and forwards the image to either
a Telegram chat or a Discord webhook.  The previous implementation
depended on the heavy `vncdotool` and `python-telegram-bot` packages; the
script now uses a light‑weight VNC client written with the Python
standard library and the ubiquitous
[`requests`](https://pypi.org/project/requests/) package to communicate
with the selected notification service.

The implementation supports the "None" and "VNC" authentication methods
of the RFB protocol and is intended for quick checking tasks rather than
as a full featured VNC client.

## Requirements

- Python 3.8+
- [`requests`](https://pypi.org/project/requests/)
- [`Pillow`](https://pypi.org/project/Pillow/)
- [`pycryptodomex`](https://pypi.org/project/pycryptodomex/)

Install the dependencies using pip:

```bash
pip install requests Pillow pycryptodomex
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

Only the first two dashes are treated as separators, so dashes in
`<name>` are allowed.

## Running the script

Execute the script with the desired options:

```bash
python tool.py --input results.txt --service telegram --bot-token <TOKEN> --chat-id <CHAT_ID>
```

To send results to Discord instead:

```bash
python tool.py --input results.txt --service discord --webhook-url <URL>
```

`--input` defaults to `results.txt` if not specified.  The script will
attempt to connect to each VNC server, grab a screenshot and send it to
the configured chat or webhook.

