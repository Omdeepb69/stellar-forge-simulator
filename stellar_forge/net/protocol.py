"""Length-prefixed JSON framing over TCP + LAN UDP discovery constants."""
from __future__ import annotations

import json
import socket
import struct

GAME_PORT = 50556
DISCOVERY_PORT = 50555
DISCOVERY_MAGIC = b"SF_DISCOVER_V1"
DISCOVERY_REPLY = "SF_HERE"
MAX_FRAME = 1024 * 512  # 512 KiB safety cap

PLAYER_COLORS = [
    (110, 225, 255),  # Host: Voyager Cyan
    (255, 210, 95),   # P2: Solar Gold
    (120, 255, 165),  # P3: Verdant Emerald
    (205, 145, 255),  # P4: Astral Violet
]


def send_msg(sock: socket.socket, msg: dict) -> None:
    """Serialize *msg* as length-prefixed UTF-8 JSON and send all bytes."""
    payload = json.dumps(msg, separators=(",", ":")).encode("utf-8")
    frame = struct.pack("!I", len(payload)) + payload
    sock.sendall(frame)


def recv_exact(sock: socket.socket, n: int) -> bytes | None:
    """Read exactly *n* bytes from *sock*, or return None on clean EOF."""
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf.extend(chunk)
    return bytes(buf)


def recv_msg(sock: socket.socket) -> dict | None:
    """Read one length-prefixed JSON message, or None on disconnect."""
    hdr = recv_exact(sock, 4)
    if hdr is None:
        return None
    (size,) = struct.unpack("!I", hdr)
    if size <= 0 or size > MAX_FRAME:
        raise ValueError(f"Invalid frame size: {size}")
    body = recv_exact(sock, size)
    if body is None:
        return None
    return json.loads(body.decode("utf-8"))

