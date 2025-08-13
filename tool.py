"""VNC screenshot sender.

This script reads a list of VNC targets, captures a screenshot from each
server and forwards the image to either a Telegram chat or a Discord
webhook.  It avoids using the `vncdotool` and `python-telegram-bot`
libraries and instead relies on a minimal implementation of the VNC
protocol together with the ubiquitous `requests` package for interacting
with the chosen notification service.

Only the "None" and "VNC" security types are supported.  The VNC
implementation is intentionally small and therefore may not handle all
edge cases of the protocol.
"""

from __future__ import annotations

import argparse
import socket
import struct
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import requests
from PIL import Image


# ---------------------------------------------------------------------------
# Utility functions


def _read_exact(sock: socket.socket, n: int) -> bytes:
    """Read exactly *n* bytes from *sock*.

    Raises ``RuntimeError`` if the connection is closed prematurely.
    """

    data = bytearray()
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise RuntimeError("Connection closed by remote host")
        data.extend(chunk)
    return bytes(data)


def _encrypt_vnc_password(password: str, challenge: bytes) -> bytes:
    """Return the DES encrypted challenge used by VNC authentication."""

    from Cryptodome.Cipher import DES

    key = password.encode("latin-1")[:8]
    key = key.ljust(8, b"\x00")
    # Reverse bits in each byte as required by the VNC spec
    key = bytes(int(f"{b:08b}"[::-1], 2) for b in key)
    cipher = DES.new(key, DES.MODE_ECB)
    return cipher.encrypt(challenge)


# ---------------------------------------------------------------------------
# VNC client


def capture_vnc_screen(
    host: str,
    port: int,
    password: str,
    timeout: float,
) -> Image.Image:
    """Capture a screenshot from the given VNC server.

    The returned :class:`~PIL.Image.Image` object contains the framebuffer
    captured using the "Raw" encoding.
    """

    sock = socket.create_connection((host, port), timeout=timeout)

    # Protocol handshake
    proto = _read_exact(sock, 12)
    sock.sendall(proto)  # agree on server's version

    version = proto[4:12]
    major = int(version[:3])
    minor = int(version[4:])

    if major == 3 and minor >= 7:
        num_types = _read_exact(sock, 1)[0]
        sec_types = _read_exact(sock, num_types)
        if 2 in sec_types and password:
            sock.sendall(b"\x02")
            challenge = _read_exact(sock, 16)
            sock.sendall(_encrypt_vnc_password(password, challenge))
        elif 1 in sec_types:
            sock.sendall(b"\x01")
        else:
            raise RuntimeError("Unsupported security types")
    else:  # protocol 3.3
        sec_type = struct.unpack("!I", _read_exact(sock, 4))[0]
        if sec_type == 2 and password:
            challenge = _read_exact(sock, 16)
            sock.sendall(_encrypt_vnc_password(password, challenge))
        elif sec_type != 1:
            raise RuntimeError("Unsupported security type")

    # Security result
    result = struct.unpack("!I", _read_exact(sock, 4))[0]
    if result != 0:
        raise RuntimeError("Authentication failed")

    sock.sendall(b"\x01")  # ClientInit, request to share the session

    # ServerInit
    init = _read_exact(sock, 24)
    width, height = struct.unpack("!HH", init[:4])
    name_length = struct.unpack("!I", _read_exact(sock, 4))[0]
    _read_exact(sock, name_length)  # skip desktop name

    # SetPixelFormat (request 24-bit RGB little endian)
    pixel_format = struct.pack(
        "!BBBBHHHBBBxxx",
        24,  # bits per pixel
        24,  # depth
        0,  # little endian
        1,  # true colour
        255,
        255,
        255,
        16,
        8,
        0,
    )
    sock.sendall(b"\x00\x00\x00\x00" + pixel_format)

    # SetEncodings (Raw)
    sock.sendall(b"\x02\x00\x00\x01\x00\x00\x00\x00")

    # FramebufferUpdateRequest for the entire screen
    sock.sendall(b"\x03\x00" + struct.pack("!HHHH", 0, 0, width, height))

    # FramebufferUpdate
    if _read_exact(sock, 1) != b"\x00":
        raise RuntimeError("Unexpected server message")
    _read_exact(sock, 1)  # padding
    num_rects = struct.unpack("!H", _read_exact(sock, 2))[0]

    image = Image.new("RGB", (width, height))
    for _ in range(num_rects):
        rx, ry, rw, rh = struct.unpack("!HHHH", _read_exact(sock, 8))
        encoding = struct.unpack("!i", _read_exact(sock, 4))[0]
        if encoding != 0:
            raise RuntimeError(f"Unsupported encoding: {encoding}")
        pixel_bytes = _read_exact(sock, rw * rh * 3)
        img = Image.frombytes("RGB", (rw, rh), pixel_bytes)
        image.paste(img, (rx, ry))

    sock.close()
    return image


# ---------------------------------------------------------------------------
# Notification helpers


def send_telegram_photo(image_path: Path, bot_token: str, chat_id: str) -> None:
    """Send ``image_path`` to the specified Telegram chat."""

    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    with image_path.open("rb") as img:
        response = requests.post(url, data={"chat_id": chat_id}, files={"photo": img})
    response.raise_for_status()


def send_discord_photo(image_path: Path, webhook_url: str) -> None:
    """Send ``image_path`` to a Discord webhook."""

    with image_path.open("rb") as img:
        response = requests.post(webhook_url, files={"file": (image_path.name, img, "image/png")})
    response.raise_for_status()


# ---------------------------------------------------------------------------
# CLI


def parse_targets(path: Path) -> Iterable[Tuple[str, int, str, str]]:
    """Yield ``(ip, port, password, name)`` tuples from ``path``."""

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            parts = line.split("-", 2)
            if len(parts) != 3 or ":" not in parts[0]:
                continue
            ip, port = parts[0].split(":", 1)
            password = parts[1]
            name = parts[2].strip("[]")
            yield ip, int(port), password, name


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Capture VNC screenshots")
    parser.add_argument("--input", default="results.txt", help="Path to targets file")
    parser.add_argument(
        "--service",
        choices=["telegram", "discord"],
        default="telegram",
        help="Notification service",
    )
    parser.add_argument("--bot-token", help="Telegram bot token")
    parser.add_argument("--chat-id", help="Telegram chat ID")
    parser.add_argument("--webhook-url", help="Discord webhook URL")
    parser.add_argument("--timeout", type=float, default=10.0, help="Socket timeout")
    args = parser.parse_args(argv)

    if args.service == "telegram":
        if not args.bot_token or not args.chat_id:
            parser.error("--bot-token and --chat-id required for Telegram")
    else:
        if not args.webhook_url:
            parser.error("--webhook-url required for Discord")

    targets = list(parse_targets(Path(args.input)))
    for ip, port, password, name in targets:
        try:
            image = capture_vnc_screen(ip, port, password, args.timeout)
            image_path = Path(f"{name}.png")
            image.save(image_path)
            if args.service == "telegram":
                send_telegram_photo(image_path, args.bot_token, args.chat_id)
            else:
                send_discord_photo(image_path, args.webhook_url)
        except Exception as exc:  # pragma: no cover - best effort
            print(f"Failed for {ip}:{port} - {exc}")
        finally:
            if "image_path" in locals() and image_path.exists():
                image_path.unlink()

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

