"""Multiplayer world synchronization and remote player rendering."""
from __future__ import annotations

import math
import queue
import time

import pygame
from pygame.math import Vector2

from .. import config
from ..core.assets import rot as _rot
from ..systems.items import SHIPS
from ..ui import hud
from ..ui.text import text
from .protocol import PLAYER_COLORS
from .session import NetClient, NetHost

SYNC_INTERVAL = 0.05  # 20 Hz state snapshots


class RemotePeer:
    """Interpolated state of one remote player."""

    def __init__(self, pid: int, name: str, color: tuple[int, int, int]):
        self.pid = pid
        self.name = name
        self.color = tuple(color)
        self.loc = "space"
        self.x = 0.0
        self.y = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.angle = 0.0
        self.facing = 1
        self.ship = "scout"
        self.thrusting = False
        self.boosting = False
        self.swinging = False
        self.boomerang = False
        self.boom_active = False
        self.boom_x = 0.0
        self.boom_y = 0.0
        self.boom_angle = 0.0
        self.rx = 0.0
        self.ry = 0.0
        self.rangle = 0.0
        self._has_pos = False
        self.last_seen = time.monotonic()

    def apply(self, d: dict) -> None:
        self.loc = d.get("loc", "space")
        self.x = float(d.get("x", self.x))
        self.y = float(d.get("y", self.y))
        self.vx = float(d.get("vx", 0.0))
        self.vy = float(d.get("vy", 0.0))
        self.angle = float(d.get("angle", 0.0))
        self.facing = int(d.get("facing", 1))
        self.ship = d.get("ship", self.ship)
        self.thrusting = bool(d.get("thrusting", False))
        self.boosting = bool(d.get("boosting", False))
        self.swinging = bool(d.get("swinging", False))
        self.boomerang = bool(d.get("boomerang", False))
        self.boom_active = bool(d.get("boom_active", False))
        self.boom_x = float(d.get("boom_x", 0.0))
        self.boom_y = float(d.get("boom_y", 0.0))
        self.boom_angle = float(d.get("boom_angle", 0.0))
        if not self._has_pos:
            self.rx, self.ry, self.rangle = self.x, self.y, self.angle
            self._has_pos = True
        self.last_seen = time.monotonic()

    def step(self, dt: float) -> None:
        if not self._has_pos:
            return
        k = min(1.0, dt * 14.0)
        self.rx += (self.x + self.vx * dt * 0.5 - self.rx) * k
        self.ry += (self.y + self.vy * dt * 0.5 - self.ry) * k
        diff = (self.angle - self.rangle + 180.0) % 360.0 - 180.0
        self.rangle = (self.rangle + diff * k) % 360.0


class NetSync:
    """Bridges NetHost / NetClient with Game, SpaceScene, SurfaceScene and MapScene."""

    def __init__(self, game, transport: NetHost | NetClient):
        self.game = game
        self.transport = transport
        self.is_host = transport.is_host
        self.peers: dict[int, RemotePeer] = {}
        self._send_t = 0.0
        self._ship_sprites: dict[str, pygame.Surface] = {}
        self._pilot_cache: dict[str, object] = {}

    @property
    def pid(self) -> int:
        return self.transport.pid

    def peer_count(self) -> int:
        return 1 + len(self.peers)

    def stop(self) -> None:
        self.transport.stop()
        self.peers.clear()

    # ------------------------------------------------------------------
    # Outgoing events
    def send_shot(self, kind: str, x: float, y: float, vx: float, vy: float, dmg: float,
                  color: tuple[int, int, int] = (140, 230, 255)) -> None:
        msg = {
            "t": "shot",
            "pid": self.pid,
            "loc": self._local_loc(),
            "kind": kind,
            "x": round(x, 1),
            "y": round(y, 1),
            "vx": round(vx, 1),
            "vy": round(vy, 1),
            "dmg": round(dmg, 2),
            "col": list(color),
        }
        if self.is_host:
            self.transport.broadcast(msg)
        else:
            self.transport.send(msg)

    def send_enemy_hit(self, eid: int, dmg: float) -> None:
        if not self.is_host and eid:
            self.transport.send({"t": "hit_enemy", "eid": eid, "dmg": round(dmg, 2)})

    # ------------------------------------------------------------------
    # Per-frame update
    def update(self, dt: float) -> None:
        if self.is_host:
            self._host_pump()
        else:
            self._client_pump()
        for peer in self.peers.values():
            peer.step(dt)
        self._send_t += dt
        if self._send_t >= SYNC_INTERVAL:
            self._send_t = 0.0
            if self.is_host:
                self._host_broadcast()
            else:
                self._client_send_state()

    def _local_loc(self) -> str:
        top = self.game.scenes.top
        tname = type(top).__name__
        if tname == "SpaceScene":
            return "space"
        if tname == "SurfaceScene" and getattr(top, "planet", None) is not None:
            return f"surface:{top.planet.id}"
        return "other"

    def _capture_local_state(self) -> dict:
        g = self.game
        st = g.state
        top = g.scenes.top
        loc = self._local_loc()
        d = {
            "pid": self.pid,
            "name": self.transport.name,
            "color": list(PLAYER_COLORS[self.pid % len(PLAYER_COLORS)]),
            "loc": loc,
            "ship": st.ship if st else "scout",
        }
        if loc == "space" and hasattr(top, "ship"):
            s = top.ship
            d.update(x=round(s.pos.x, 1), y=round(s.pos.y, 1),
                     vx=round(s.vel.x, 1), vy=round(s.vel.y, 1),
                     angle=round(s.angle, 1), thrusting=s.thrusting, boosting=s.boosting)
        elif loc.startswith("surface:") and hasattr(top, "pilot"):
            p = top.pilot
            d.update(x=round(p.x, 1), y=round(p.y, 1),
                     vx=round(p.vx, 1), vy=round(p.vy, 1),
                     facing=p.facing, swinging=p.swinging, boomerang=p.boomerang,
                     boom_active=p.boom_active, boom_x=round(p.boom_x, 1),
                     boom_y=round(p.boom_y, 1), boom_angle=round(p.boom_angle, 1))
        elif g.space is not None and hasattr(g.space, "ship"):
            s = g.space.ship
            d.update(x=round(s.pos.x, 1), y=round(s.pos.y, 1))
        return d

    # ------------------------------------------------------------------
    def _host_pump(self) -> None:
        host: NetHost = self.transport  # type: ignore[assignment]
        while True:
            try:
                pid, msg = host.inbox.get_nowait()
            except queue.Empty:
                break
            t = msg.get("t")
            if t == "joined":
                col = PLAYER_COLORS[pid % len(PLAYER_COLORS)]
                name = msg.get("name", f"Voyager-{pid + 1}")
                self.peers[pid] = RemotePeer(pid, name, col)
                self.game.toasts.add(f"{name} joined the galaxy", config.UI_GOOD, 2.5)
            elif t == "left":
                peer = self.peers.pop(pid, None)
                name = peer.name if peer else msg.get("name", "Player")
                self.game.toasts.add(f"{name} disconnected", config.UI_WARN, 2.5)
            elif t == "state":
                peer = self.peers.get(pid)
                if peer is not None:
                    peer.apply(msg)
            elif t == "shot":
                msg["pid"] = pid
                self._spawn_remote_shot(msg)
                host.broadcast(msg, exclude_pid=pid)
            elif t == "hit_enemy":
                self._host_apply_enemy_hit(int(msg.get("eid", 0)), float(msg.get("dmg", 0.0)))

    def _host_apply_enemy_hit(self, eid: int, dmg: float) -> None:
        sp = self.game.space
        if sp is None or dmg <= 0:
            return
        for e in list(sp.enemies):
            if id(e) == eid and e.alive:
                if e.hurt(dmg):
                    sp._enemy_killed(e)
                break

    def _host_broadcast(self) -> None:
        host: NetHost = self.transport  # type: ignore[assignment]
        st = self.game.state
        players = [self._capture_local_state()]
        for p in self.peers.values():
            players.append({
                "pid": p.pid, "name": p.name, "color": list(p.color), "loc": p.loc,
                "x": round(p.x, 1), "y": round(p.y, 1), "vx": round(p.vx, 1), "vy": round(p.vy, 1),
                "angle": round(p.angle, 1), "facing": p.facing, "ship": p.ship,
                "thrusting": p.thrusting, "boosting": p.boosting,
                "swinging": p.swinging, "boomerang": p.boomerang,
                "boom_active": p.boom_active, "boom_x": round(p.boom_x, 1),
                "boom_y": round(p.boom_y, 1), "boom_angle": round(p.boom_angle, 1),
            })
        enemies = []
        sp = self.game.space
        if sp is not None:
            for e in sp.enemies[:24]:
                if not e.alive:
                    continue
                enemies.append([
                    id(e), 1 if getattr(e, "is_boss", False) else 0,
                    1 if getattr(e, "elite", False) else 0,
                    round(e.pos.x, 1), round(e.pos.y, 1),
                    round(e.vel.x, 1), round(e.vel.y, 1),
                    round(e.angle, 1), round(e.hp, 1), round(e.max_hp, 1),
                    getattr(e, "warden", None), getattr(e, "name", None),
                ])
        camp = None
        if st is not None:
            camp = {
                "chapter": st.chapter,
                "keys": sorted(st.keys),
                "shards": sorted(st.shards),
                "boss_defeated": st.boss_defeated,
            }
        host.broadcast({"t": "world", "players": players, "enemies": enemies, "camp": camp})

    # ------------------------------------------------------------------
    def _client_send_state(self) -> None:
        client: NetClient = self.transport  # type: ignore[assignment]
        d = self._capture_local_state()
        d["t"] = "state"
        client.send(d)

    def _client_pump(self) -> None:
        client: NetClient = self.transport  # type: ignore[assignment]
        while True:
            try:
                msg = client.inbox.get_nowait()
            except queue.Empty:
                break
            t = msg.get("t")
            if t == "disconnected":
                self.game.toasts.add("Disconnected from host", config.UI_DANGER, 3.0)
                self.game.net = None
                return
            elif t == "world":
                self._apply_world_snapshot(msg)
            elif t == "shot":
                if msg.get("pid") != self.pid:
                    self._spawn_remote_shot(msg)

    def _apply_world_snapshot(self, msg: dict) -> None:
        seen = set()
        for pd in msg.get("players", ()):
            pid = int(pd.get("pid", -1))
            if pid == self.pid or pid < 0:
                continue
            seen.add(pid)
            peer = self.peers.get(pid)
            if peer is None:
                col = tuple(pd.get("color") or PLAYER_COLORS[pid % len(PLAYER_COLORS)])
                peer = RemotePeer(pid, pd.get("name", f"Voyager-{pid + 1}"), col)
                self.peers[pid] = peer
                self.game.toasts.add(f"{peer.name} joined", config.UI_GOOD, 2.0)
            peer.apply(pd)
        for dead_pid in list(self.peers):
            if dead_pid not in seen:
                left = self.peers.pop(dead_pid)
                self.game.toasts.add(f"{left.name} left", config.UI_WARN, 2.0)
        self._sync_client_enemies(msg.get("enemies", ()))
        camp = msg.get("camp")
        if camp and self.game.state is not None:
            st = self.game.state
            if int(camp.get("chapter", st.chapter)) > st.chapter:
                st.chapter = int(camp["chapter"])
            for k in camp.get("keys", ()):
                st.keys.add(k)
            for s in camp.get("shards", ()):
                st.shards.add(s)
            if camp.get("boss_defeated"):
                st.boss_defeated = True

    def _sync_client_enemies(self, items: list) -> None:
        sp = self.game.space
        if sp is None:
            return
        from ..entities.enemies import Dreadnought, Raider
        existing = {getattr(e, "_net_eid", None): e for e in sp.enemies}
        synced = []
        for row in items:
            eid, is_boss, elite, x, y, vx, vy, angle, hp, max_hp, warden, name = row
            e = existing.get(eid)
            if e is None:
                if is_boss:
                    e = Dreadnought(self.game, Vector2(x, y), 2.5, warden=warden, name=name)
                else:
                    e = Raider(self.game, Vector2(x, y), 1.5, elite=bool(elite))
                e._net_eid = eid
            e.pos.update(x, y)
            e.vel.update(vx, vy)
            e.angle = angle
            e.hp = hp
            e.max_hp = max_hp
            e.aggro = True
            e.alive = hp > 0
            synced.append(e)
        sp.enemies = synced

    def _spawn_remote_shot(self, msg: dict) -> None:
        loc = msg.get("loc")
        if loc != self._local_loc():
            return
        top = self.game.scenes.top
        if loc == "space" and hasattr(top, "bullets"):
            from ..entities.projectiles import Bullet
            col = tuple(msg.get("col") or (140, 230, 255))
            top.bullets.append(Bullet(
                Vector2(msg["x"], msg["y"]),
                Vector2(msg["vx"], msg["vy"]),
                0.0,  # visual proxy; owner's client/host handles damage
                "remote",
                col,
                life=1.2,
            ))
        elif loc.startswith("surface:") and hasattr(top, "bolts"):
            top.bolts.append([msg["x"], msg["y"], msg["vx"], 0.9, 1.0, set()])

    # ------------------------------------------------------------------
    # Rendering helpers
    def _ship_sprite(self, ship_id: str) -> pygame.Surface:
        img = self._ship_sprites.get(ship_id)
        if img is None:
            info = SHIPS.get(ship_id, SHIPS["scout"])
            img = self.game.assets.image(info["sprite"], crop=True)
            self._ship_sprites[ship_id] = img
        return img

    def draw_space(self, surf: pygame.Surface, cam) -> None:
        for peer in self.peers.values():
            if peer.loc != "space":
                continue
            pos = Vector2(peer.rx, peer.ry)
            if cam.visible(pos, 80, 0):
                sx, sy = cam.to_screen(pos)
                info = SHIPS.get(peer.ship, SHIPS["scout"])
                scale = (1.3 if cam.zoom > 0.45 else 1.0) * info.get("scale", 1.0)
                if peer.thrusting:
                    fwd = Vector2(math.sin(math.radians(peer.rangle)), -math.cos(math.radians(peer.rangle)))
                    tail = pos - fwd * (22 * info.get("scale", 1.0))
                    tx, ty = cam.to_screen(tail)
                    r = max(3, int((8 if peer.boosting else 5) * max(0.6, cam.zoom)))
                    pygame.draw.circle(surf, peer.color, (int(tx), int(ty)), r)
                img = _rot(self._ship_sprite(peer.ship), -peer.rangle, scale)
                surf.blit(img, img.get_rect(center=(sx, sy)))
                text(surf, peer.name, (sx, sy - 34 * scale), 14, peer.color, bold=True,
                     anchor="midbottom", outline=True)
            else:
                ship = getattr(self.game.space, "ship", None)
                dist = pos.distance_to(ship.pos) if ship else None
                hud.edge_arrow(surf, cam.to_screen(pos), peer.color, peer.name, dist)

    def _ensure_pilot_art(self) -> None:
        if self._pilot_cache:
            return
        a = self.game.assets
        sz = (80 * config.ART_SCALE, 80 * config.ART_SCALE)
        swing = [f"player/swing/swordSwing{i}.png" for i in range(1, 5)]
        self._pilot_cache = {
            "idle_r": a.image("player/mainCharStill.png", size=sz),
            "idle_l": a.image("player/mainCharStill.png", size=sz, flip_x=True),
            "swing_r": a.image(swing[1], size=sz),
            "swing_l": a.image(swing[1], size=sz, flip_x=True),
            "boom": a.image("player/boomerang.png", size=(38, 38)),
        }

    def draw_surface(self, surf: pygame.Surface, ox: float, oy: float, planet_id: str) -> None:
        target_loc = f"surface:{planet_id}"
        peers = [p for p in self.peers.values() if p.loc == target_loc]
        if not peers:
            return
        self._ensure_pilot_art()
        for peer in peers:
            if peer.boom_active:
                rot = pygame.transform.rotate(self._pilot_cache["boom"], -peer.boom_angle)
                surf.blit(rot, rot.get_rect(center=(int(peer.boom_x - ox), int(peer.boom_y - oy))))
            if peer.swinging and not peer.boomerang:
                img = self._pilot_cache["swing_r" if peer.facing > 0 else "swing_l"]
            else:
                img = self._pilot_cache["idle_r" if peer.facing > 0 else "idle_l"]
            rect = img.get_rect(midbottom=(peer.rx - ox, peer.ry - oy + 6))
            surf.blit(img, rect)
            text(surf, peer.name, (int(peer.rx - ox), rect.top - 4), 14, peer.color, bold=True,
                 anchor="midbottom", outline=True)

