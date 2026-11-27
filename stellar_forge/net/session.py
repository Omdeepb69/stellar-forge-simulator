"""Threaded TCP Host/Client and UDP LAN discovery for Co-op Multiplayer."""
from __future__ import annotations

import queue
import socket
import threading
import time

from .protocol import (
    DISCOVERY_MAGIC,
    DISCOVERY_PORT,
    DISCOVERY_REPLY,
    GAME_PORT,
    PLAYER_COLORS,
    recv_msg,
    send_msg,
)


def local_ip() -> str:
    """Best-effort local LAN IPv4 address (falls back to 127.0.0.1)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def discover_lan(timeout: float = 0.5, port: int = DISCOVERY_PORT) -> list[dict]:
    """Broadcast a LAN probe and return [{ip, port, name, players, max_players}]."""
    found: dict[tuple[str, int], dict] = {}
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(0.12)
        sock.sendto(DISCOVERY_MAGIC, ("255.255.255.255", port))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                data, (addr, _) = sock.recvfrom(512)
            except socket.timeout:
                continue
            except OSError:
                break
            text = data.decode("utf-8", errors="ignore")
            parts = text.split("|")
            if len(parts) >= 5 and parts[0] == DISCOVERY_REPLY:
                try:
                    gport = int(parts[1])
                    cur, mx = int(parts[3]), int(parts[4])
                except ValueError:
                    continue
                found[(addr, gport)] = {
                    "ip": addr,
                    "port": gport,
                    "name": parts[2],
                    "players": cur,
                    "max_players": mx,
                }
    except OSError:
        pass
    finally:
        sock.close()
    return list(found.values())


class _PeerConn:
    __slots__ = ("pid", "name", "color", "sock", "send_q", "alive")

    def __init__(self, pid: int, name: str, sock: socket.socket):
        self.pid = pid
        self.name = name
        self.color = PLAYER_COLORS[pid % len(PLAYER_COLORS)]
        self.sock = sock
        self.send_q: queue.Queue[dict] = queue.Queue(maxsize=64)
        self.alive = True


class NetHost:
    """Authoritative co-op host accepting up to 3 remote clients (4 players total)."""

    is_host = True

    def __init__(self, host_name: str = "Voyager-1", port: int = GAME_PORT,
                 discovery_port: int = DISCOVERY_PORT, max_players: int = 4):
        self.pid = 0
        self.name = host_name
        self.port = port
        self.discovery_port = discovery_port
        self.max_players = max_players
        self.welcome_fn = None  # () -> dict with seed & campaign snapshot
        self._lock = threading.Lock()
        self._peers: dict[int, _PeerConn] = {}
        self._next_pid = 1
        self.inbox: queue.Queue[tuple[int, dict]] = queue.Queue(maxsize=512)
        self.running = False
        self._srv: socket.socket | None = None
        self._disc: socket.socket | None = None

    def start(self) -> int:
        """Bind TCP + UDP discovery sockets and start background threads. Returns bound TCP port."""
        self._srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._srv.bind(("0.0.0.0", self.port))
        self._srv.listen(8)
        self._srv.settimeout(0.25)
        self.port = self._srv.getsockname()[1]
        self.running = True
        threading.Thread(target=self._accept_loop, daemon=True).start()
        if self.discovery_port:
            try:
                self._disc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self._disc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self._disc.bind(("0.0.0.0", self.discovery_port))
                self._disc.settimeout(0.25)
                threading.Thread(target=self._discovery_loop, daemon=True).start()
            except OSError:
                self._disc = None
        return self.port

    def player_list(self) -> list[dict]:
        with self._lock:
            out = [{"pid": 0, "name": self.name, "color": PLAYER_COLORS[0]}]
            for p in self._peers.values():
                out.append({"pid": p.pid, "name": p.name, "color": p.color})
            return out

    def broadcast(self, msg: dict, exclude_pid: int | None = None) -> None:
        with self._lock:
            peers = list(self._peers.values())
        for p in peers:
            if not p.alive or p.pid == exclude_pid:
                continue
            try:
                p.send_q.put_nowait(msg)
            except queue.Full:
                pass

    def stop(self) -> None:
        self.running = False
        for s in (self._srv, self._disc):
            if s is not None:
                try:
                    s.close()
                except OSError:
                    pass
        with self._lock:
            peers = list(self._peers.values())
            self._peers.clear()
        for p in peers:
            p.alive = False
            try:
                p.sock.close()
            except OSError:
                pass

    # ------------------------------------------------------------------
    def _discovery_loop(self) -> None:
        while self.running and self._disc is not None:
            try:
                data, addr = self._disc.recvfrom(256)
            except socket.timeout:
                continue
            except OSError:
                break
            if data == DISCOVERY_MAGIC:
                with self._lock:
                    count = 1 + len(self._peers)
                reply = f"{DISCOVERY_REPLY}|{self.port}|{self.name}|{count}|{self.max_players}"
                try:
                    self._disc.sendto(reply.encode("utf-8"), addr)
                except OSError:
                    pass

    def _accept_loop(self) -> None:
        while self.running and self._srv is not None:
            try:
                csock, _ = self._srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                csock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                csock.settimeout(5.0)
                hello = recv_msg(csock)
                if not hello or hello.get("t") != "hello":
                    csock.close()
                    continue
                with self._lock:
                    if 1 + len(self._peers) >= self.max_players:
                        send_msg(csock, {"t": "reject", "reason": "Server is full"})
                        csock.close()
                        continue
                    pid = self._next_pid
                    self._next_pid += 1
                    name = str(hello.get("name") or f"Voyager-{pid + 1}")[:18]
                    peer = _PeerConn(pid, name, csock)
                    self._peers[pid] = peer
                welcome = self.welcome_fn() if self.welcome_fn else {}
                welcome.update({"t": "welcome", "pid": pid, "name": name, "color": list(peer.color)})
                send_msg(csock, welcome)
                csock.settimeout(None)
                threading.Thread(target=self._peer_recv, args=(peer,), daemon=True).start()
                threading.Thread(target=self._peer_send, args=(peer,), daemon=True).start()
                self._push_inbox(pid, {"t": "joined", "pid": pid, "name": name})
            except Exception:
                try:
                    csock.close()
                except OSError:
                    pass

    def _peer_recv(self, peer: _PeerConn) -> None:
        try:
            peer.sock.settimeout(0.5)
            while self.running and peer.alive:
                try:
                    msg = recv_msg(peer.sock)
                except socket.timeout:
                    continue
                if msg is None:
                    break
                self._push_inbox(peer.pid, msg)
        except (OSError, ValueError):
            pass
        finally:
            self._drop_peer(peer)

    def _peer_send(self, peer: _PeerConn) -> None:
        try:
            while self.running and peer.alive:
                try:
                    msg = peer.send_q.get(timeout=0.25)
                except queue.Empty:
                    continue
                send_msg(peer.sock, msg)
        except OSError:
            self._drop_peer(peer)

    def _drop_peer(self, peer: _PeerConn) -> None:
        if not peer.alive:
            return
        peer.alive = False
        with self._lock:
            self._peers.pop(peer.pid, None)
        try:
            peer.sock.close()
        except OSError:
            pass
        self._push_inbox(peer.pid, {"t": "left", "pid": peer.pid, "name": peer.name})

    def _push_inbox(self, pid: int, msg: dict) -> None:
        try:
            self.inbox.put_nowait((pid, msg))
        except queue.Full:
            pass


class NetClient:
    """Co-op client connecting to a NetHost via IP:port."""

    is_host = False

    def __init__(self, host: str, port: int = GAME_PORT, name: str = "Voyager"):
        self.host = host
        self.port = port
        self.name = name
        self.pid = -1
        self.color = list(PLAYER_COLORS[1])
        self.welcome: dict = {}
        self.inbox: queue.Queue[dict] = queue.Queue(maxsize=512)
        self._send_q: queue.Queue[dict] = queue.Queue(maxsize=128)
        self._sock: socket.socket | None = None
        self.running = False

    def connect(self, timeout: float = 4.0) -> dict:
        """Connect, perform hello/welcome handshake, and start IO threads."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((self.host, self.port))
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        send_msg(sock, {"t": "hello", "name": self.name})
        resp = recv_msg(sock)
        if not resp or resp.get("t") == "reject":
            reason = (resp or {}).get("reason", "Connection rejected")
            sock.close()
            raise ConnectionError(reason)
        if resp.get("t") != "welcome":
            sock.close()
            raise ConnectionError("Unexpected handshake response")
        sock.settimeout(None)
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
                msg = recv_msg(self._sock)
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

