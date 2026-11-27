"""Lightweight Room-Code Relay Server & Host/Client adapters for cross-network co-op.

Run standalone on any VPS / cloud host with:
    python -m stellar_forge.net.relay --port 50557
"""
from __future__ import annotations

import argparse
import queue
import random
import socket
import threading

from .protocol import PLAYER_COLORS, recv_msg, send_msg

RELAY_PORT = 50557
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _gen_code(existing: set[str]) -> str:
    for _ in range(100):
        code = "".join(random.choice(_ALPHABET) for _ in range(6))
        if code not in existing:
            return code
    raise RuntimeError("No room codes available")


class _Room:
    def __init__(self, code: str, host_sock: socket.socket):
        self.code = code
        self.host_sock = host_sock
        self.clients: dict[int, socket.socket] = {}
        self.next_cid = 1
        self.lock = threading.Lock()


class RelayServer:
    """Stateless-packet Room-Code relay forwarding frames between a Host and Clients."""

    def __init__(self, bind_host: str = "0.0.0.0", port: int = RELAY_PORT, max_players: int = 4):
        self.bind_host = bind_host
        self.port = port
        self.max_players = max_players
        self._lock = threading.Lock()
        self._rooms: dict[str, _Room] = {}
        self._srv: socket.socket | None = None
        self.running = False

    def start(self) -> int:
        self._srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._srv.bind((self.bind_host, self.port))
        self._srv.listen(32)
        self._srv.settimeout(0.25)
        self.port = self._srv.getsockname()[1]
        self.running = True
        threading.Thread(target=self._accept_loop, daemon=True).start()
        return self.port

    def stop(self) -> None:
        self.running = False
        if self._srv is not None:
            try:
                self._srv.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self._srv.close()
            except OSError:
                pass
            self._srv = None
        with self._lock:
            rooms = list(self._rooms.values())
            self._rooms.clear()
        for r in rooms:
            self._close_room(r)

    def _accept_loop(self) -> None:
        while self.running and self._srv is not None:
            try:
                csock, _ = self._srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            csock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            threading.Thread(target=self._handle_conn, args=(csock,), daemon=True).start()

    def _handle_conn(self, sock: socket.socket) -> None:
        try:
            sock.settimeout(5.0)
            first = recv_msg(sock)
            if not first:
                sock.close()
                return
            sock.settimeout(0.5)
            t = first.get("t")
            if t == "relay_create":
                self._run_host(sock)
            elif t == "relay_join":
                self._run_client(sock, str(first.get("code", "")).upper().strip())
            else:
                sock.close()
        except Exception:
            try:
                sock.close()
            except OSError:
                pass

    def _run_host(self, sock: socket.socket) -> None:
        with self._lock:
            code = _gen_code(set(self._rooms))
            room = _Room(code, sock)
            self._rooms[code] = room
        send_msg(sock, {"t": "relay_created", "code": code})
        try:
            while self.running:
                try:
                    msg = recv_msg(sock)
                except socket.timeout:
                    continue
                if msg is None:
                    break
                if msg.get("t") == "relay_to":
                    cid = msg.get("cid")
                    inner = msg.get("msg")
                    if inner is None:
                        continue
                    with room.lock:
                        targets = [room.clients[cid]] if cid in room.clients else (
                            list(room.clients.values()) if cid is None else []
                        )
                    for cs in targets:
                        try:
                            send_msg(cs, inner)
                        except OSError:
                            pass
        except (OSError, ValueError):
            pass
        finally:
            with self._lock:
                self._rooms.pop(room.code, None)
            self._close_room(room)

    def _run_client(self, sock: socket.socket, code: str) -> None:
        with self._lock:
            room = self._rooms.get(code)
        if room is None:
            send_msg(sock, {"t": "reject", "reason": f"Room {code} not found"})
            sock.close()
            return
        with room.lock:
            if 1 + len(room.clients) >= self.max_players:
                send_msg(sock, {"t": "reject", "reason": "Room is full"})
                sock.close()
                return
            cid = room.next_cid
            room.next_cid += 1
            room.clients[cid] = sock
        try:
            send_msg(room.host_sock, {"t": "relay_peer_join", "cid": cid})
        except OSError:
            sock.close()
            return
        try:
            while self.running:
                try:
                    msg = recv_msg(sock)
                except socket.timeout:
                    continue
                if msg is None:
                    break
                try:
                    send_msg(room.host_sock, {"t": "relay_from", "cid": cid, "msg": msg})
                except OSError:
                    break
        except (OSError, ValueError):
            pass
        finally:
            with room.lock:
                room.clients.pop(cid, None)
            try:
                send_msg(room.host_sock, {"t": "relay_peer_left", "cid": cid})
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass

    @staticmethod
    def _close_room(room: _Room) -> None:
        with room.lock:
            socks = [room.host_sock, *room.clients.values()]
            room.clients.clear()
        for s in socks:
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                s.close()
            except OSError:
                pass


class RelayHost:
    """Drop-in NetHost replacement that hosts a Room Code on a RelayServer."""

    is_host = True

    def __init__(self, relay_host: str, relay_port: int = RELAY_PORT, host_name: str = "Voyager-1"):
        self.pid = 0
        self.name = host_name
        self.relay_host = relay_host
        self.relay_port = relay_port
        self.room_code = ""
        self.welcome_fn = None
        self._lock = threading.Lock()
        self._peers: dict[int, dict] = {}
        self.inbox: queue.Queue[tuple[int, dict]] = queue.Queue(maxsize=512)
        self._send_q: queue.Queue[dict] = queue.Queue(maxsize=256)
        self._sock: socket.socket | None = None
        self.running = False

    def start(self, timeout: float = 4.0) -> str:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((self.relay_host, self.relay_port))
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        send_msg(sock, {"t": "relay_create"})
        resp = recv_msg(sock)
        if not resp or resp.get("t") != "relay_created":
            sock.close()
            raise ConnectionError("Relay did not create room")
        sock.settimeout(0.5)
        self._sock = sock
        self.room_code = resp["code"]
        self.running = True
        threading.Thread(target=self._recv_loop, daemon=True).start()
        threading.Thread(target=self._send_loop, daemon=True).start()
        return self.room_code

    def player_list(self) -> list[dict]:
        with self._lock:
            out = [{"pid": 0, "name": self.name, "color": PLAYER_COLORS[0]}]
            for pid, p in self._peers.items():
                if p.get("welcomed"):
                    out.append({"pid": pid, "name": p["name"], "color": p["color"]})
            return out

    def broadcast(self, msg: dict, exclude_pid: int | None = None) -> None:
        if not self.running:
            return
        if exclude_pid is None:
            self._enqueue({"t": "relay_to", "cid": None, "msg": msg})
            return
        with self._lock:
            pids = [pid for pid in self._peers if pid != exclude_pid]
        for pid in pids:
            self._enqueue({"t": "relay_to", "cid": pid, "msg": msg})

    def stop(self) -> None:
        self.running = False
        if self._sock is not None:
            try:
                self._sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        with self._lock:
            self._peers.clear()

    def _enqueue(self, frame: dict) -> None:
        try:
            self._send_q.put_nowait(frame)
        except queue.Full:
            pass

    def _recv_loop(self) -> None:
        try:
            while self.running and self._sock is not None:
                try:
                    frame = recv_msg(self._sock)
                except socket.timeout:
                    continue
                if frame is None:
                    break
                ft = frame.get("t")
                if ft == "relay_peer_join":
                    cid = int(frame["cid"])
                    with self._lock:
                        self._peers[cid] = {
                            "name": f"Voyager-{cid + 1}",
                            "color": PLAYER_COLORS[cid % len(PLAYER_COLORS)],
                            "welcomed": False,
                        }
                elif ft == "relay_peer_left":
                    cid = int(frame["cid"])
                    with self._lock:
                        p = self._peers.pop(cid, None)
                    if p and p.get("welcomed"):
                        self._push_inbox(cid, {"t": "left", "pid": cid, "name": p["name"]})
                elif ft == "relay_from":
                    cid = int(frame["cid"])
                    msg = frame.get("msg") or {}
                    if msg.get("t") == "hello":
                        name = str(msg.get("name") or f"Voyager-{cid + 1}")[:18]
                        col = PLAYER_COLORS[cid % len(PLAYER_COLORS)]
                        with self._lock:
                            self._peers[cid] = {"name": name, "color": col, "welcomed": True}
                        welcome = self.welcome_fn() if self.welcome_fn else {}
                        welcome.update({"t": "welcome", "pid": cid, "name": name, "color": list(col)})
                        self._enqueue({"t": "relay_to", "cid": cid, "msg": welcome})
                        self._push_inbox(cid, {"t": "joined", "pid": cid, "name": name})
                    else:
                        self._push_inbox(cid, msg)
        except (OSError, ValueError):
            pass
        finally:
            self.running = False

    def _send_loop(self) -> None:
        try:
            while self.running and self._sock is not None:
                try:
                    frame = self._send_q.get(timeout=0.25)
                except queue.Empty:
                    continue
                send_msg(self._sock, frame)
        except OSError:
            self.running = False

    def _push_inbox(self, pid: int, msg: dict) -> None:
        try:
            self.inbox.put_nowait((pid, msg))
        except queue.Full:
            pass


class RelayClient:
    """Drop-in NetClient replacement that joins a Room Code on a RelayServer."""

    is_host = False

    def __init__(self, relay_host: str, relay_port: int = RELAY_PORT, code: str = "", name: str = "Voyager"):
        self.host = relay_host
        self.port = relay_port
        self.code = code.upper().strip()
        self.name = name
        self.pid = -1
        self.color = list(PLAYER_COLORS[1])
        self.welcome: dict = {}
        self.inbox: queue.Queue[dict] = queue.Queue(maxsize=512)
        self._send_q: queue.Queue[dict] = queue.Queue(maxsize=128)
        self._sock: socket.socket | None = None
        self.running = False

    def connect(self, timeout: float = 4.0) -> dict:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((self.host, self.port))
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        send_msg(sock, {"t": "relay_join", "code": self.code})
        send_msg(sock, {"t": "hello", "name": self.name})
        resp = recv_msg(sock)
        if not resp or resp.get("t") == "reject":
            reason = (resp or {}).get("reason", "Connection rejected")
            sock.close()
            raise ConnectionError(reason)
        if resp.get("t") != "welcome":
            sock.close()
            raise ConnectionError("Unexpected handshake response")
        sock.settimeout(0.5)
        self._sock = sock
        self.pid = int(resp["pid"])
        self.name = resp.get("name", self.name)
        self.color = resp.get("color", self.color)
        self.welcome = resp
        self.running = True
        threading.Thread(target=self._recv_loop, daemon=True).start()
        threading.Thread(target=self._send_loop, daemon=True).start()
        return resp

    def send(self, msg: dict) -> None:
        if not self.running:
            return
        try:
            self._send_q.put_nowait(msg)
        except queue.Full:
            pass

    def stop(self) -> None:
        self.running = False
        if self._sock is not None:
            try:
                self._sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    def _recv_loop(self) -> None:
        try:
            while self.running and self._sock is not None:
                try:
                    msg = recv_msg(self._sock)
                except socket.timeout:
                    continue
                if msg is None:
                    break
                try:
                    self.inbox.put_nowait(msg)
                except queue.Full:
                    pass
        except (OSError, ValueError):
            pass
        finally:
            self.running = False
            try:
                self.inbox.put_nowait({"t": "disconnected"})
            except queue.Full:
                pass

    def _send_loop(self) -> None:
        try:
            while self.running and self._sock is not None:
                try:
                    msg = self._send_q.get(timeout=0.25)
                except queue.Empty:
                    continue
                send_msg(self._sock, msg)
        except OSError:
            self.running = False


def main() -> None:
    parser = argparse.ArgumentParser(description="Stellar Forge Co-op Relay Server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=RELAY_PORT)
    args = parser.parse_args()
    srv = RelayServer(args.host, args.port)
    port = srv.start()
    print(f"Stellar Forge Relay listening on {args.host}:{port}")
    try:
        while srv.running:
            threading.Event().wait(1.0)
    except KeyboardInterrupt:
        srv.stop()


if __name__ == "__main__":
    main()
