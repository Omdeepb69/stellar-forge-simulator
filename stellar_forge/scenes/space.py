"""Space flight: the infinite universe, combat, landing and docking."""
from __future__ import annotations

import math
import random

import pygame
from pygame.math import Vector2

from .. import config
from ..core.camera import SpaceCamera
from ..core.scene import Scene
from ..entities.bodies import ForgeGate
from ..entities.enemies import Dreadnought, Raider, Torpedo
from ..entities.projectiles import Missile, Pickup
from ..entities.ship import Controls, PlayerShip
from ..systems import gravity
from ..systems.particles import ParticleSystem
from ..ui import hud
from ..ui.starfield import Starfield
from ..ui.text import panel, text
from ..systems import lore
from ..systems.achievements import distance_sectors
from ..systems.corps import CorpsWing
from ..systems.saga_space import SagaSpace
from ..systems.space_events import CargoPod, EventDirector
from ..ui.floaters import Floaters
from ..ui.palette import col as pcol
from ..world.universe import Universe

HOME_STATION = "0,0:st"
# the three space camera distances ([V] / mouse wheel / +-)
CAMERAS = [("Close", 1.0), ("Medium", 0.55), ("Far", 0.24)]


class SpaceScene(Scene):
    advances_time = True

    def __init__(self, game):
        super().__init__(game)
        self.camera = SpaceCamera()
        self.cam_mode = max(0, min(2, getattr(game.settings, "camera", 1)))
        self.user_zoom = CAMERAS[self.cam_mode][1]
        self.particles = ParticleSystem()
        self.starfield = Starfield(game.state.seed)
        self.ship = PlayerShip(game, Vector2())
        self.bullets = []
        self.enemies: list[Raider] = []
        self.corps = CorpsWing(self)
        self.saga = SagaSpace(self)
        self.saga_prompt = None
        self.pickups: list[Pickup] = []
        self.clock = 0.0
        self.sectors = []
        self._sector_key = None
        self.system = None
        self.sources = []
        self.trajectory = []
        self._traj_timer = 0
        self.land_target = None
        self.dock_target = None
        self.near_wormhole = None
        self.in_nebula = False
        self.dominant = None
        self.target = None       # TAB-selected body
        self.dead_timer = -1.0
        self.land_grace = 0.0
        self.death_reason = ""
        self.spawn_timer = 3.0
        self.warnings: list[str] = []
        self._fuel_warned = False
        self.near_forge = None
        self.flagship_cd = 90.0
        self.director = EventDirector(self)
        self.comets = []
        self.floaters = Floaters()
        self.towing: CargoPod | None = None
        self.autopilot = None          # (label, pos_fn, vel_fn, arrive_radius)
        self.near_derelict = None
        self.event_prompt = None

    def sector_danger(self) -> float:
        return self.game.universe.sector(*Universe.sector_coords(self.ship.pos)).danger

    @property
    def music(self) -> str:
        return "boss" if any(getattr(e, "is_boss", False) and e.aggro for e in self.enemies) else "space"

    @property
    def boss(self):
        return next((e for e in self.enemies if getattr(e, "is_boss", False) and e.aggro), None)

    # ------------------------------------------------------------------
    @property
    def t(self) -> float:
        return self.game.state.world_time

    def place_ship(self, pos: Vector2, vel: Vector2 | None = None, angle: float = 0.0) -> None:
        self.ship.pos = Vector2(pos)
        self.ship.vel = Vector2(vel or (0, 0))
        self.ship.angle = angle
        self.camera.snap(self.ship.pos)
        self._refresh_sectors(force=True)

    def launch_from(self, body, quiet: bool = False) -> None:
        t = self.t
        center = body.pos(t)
        out = Vector2(0, -1).rotate(random.uniform(-40, 40))
        pos = center + out * (body.radius + 90)
        vel = body.vel(t) + out * 260
        self.land_grace = 4.0
        angle = math.degrees(math.atan2(out.x, -out.y))
        self.place_ship(pos, vel, angle)
        self.ship.invuln = 2.5
        self.bullets.clear()
        self.enemies = [e for e in self.enemies if e.pos.distance_to(pos) > 2500]
        if not quiet:
            for _ in range(30):
                v = out.rotate(random.uniform(-70, 70)) * random.uniform(40, 160)
                self.particles.emit(pos.x - out.x * 60, pos.y - out.y * 60, v.x, v.y,
                                    random.uniform(0.5, 1.2), random.uniform(4, 9), (200, 190, 170), drag=1.5)
            self.game.audio.play("land", 0.8)

    def save_location(self) -> None:
        near = None
        best = 6000.0
        for sec in self.sectors:
            for b in sec.planets + sec.stations:
                d = b.pos(self.t).distance_to(self.ship.pos)
                if d < best:
                    best, near = d, b
        if near is not None:
            self.game.state.location = {"kind": "space", "near": near.id}
        else:
            self.game.state.location = {"kind": "space", "x": self.ship.pos.x, "y": self.ship.pos.y}

    def on_enter(self) -> None:
        self._refresh_sectors(force=True)

    def on_exit(self) -> None:
        self.game.audio.loop("thrust", False)

    on_pause = on_exit

    # ------------------------------------------------------------------
    def _refresh_sectors(self, force=False) -> None:
        key = Universe.sector_coords(self.ship.pos)
        if force or key != self._sector_key:
            self._sector_key = key
            self.sectors = self.game.universe.active_sectors(self.ship.pos)
        sys_ = self.game.universe.current_system(self.ship.pos)
        if sys_ is not self.system:
            self.system = sys_
            if sys_ is not None:
                self._discover(sys_)
        srcs = list(sys_.gravity_sources()) if sys_ else []
        for sec in self.sectors:
            for hz in sec.hazards:
                if hz not in srcs and hz.pos(self.t).distance_to(self.ship.pos) < 30000:
                    srcs.append(hz)
        self.sources = srcs

    def _discover(self, sec) -> None:
        st = self.game.state
        if sec.key in st.discovered_systems:
            return
        st.discovered_systems.append(sec.key)
        if sec.key != "0,0":
            st.earn(config.DISCOVERY_REWARD)
            st.scan_data += len(sec.planets)
            self.game.banner.show(f"Discovered: {sec.name} system",
                                  f"{len(sec.planets)} worlds  ·  {sec.star.spectral}-class star  ·  +{config.DISCOVERY_REWARD} cr")
            self.game.audio.play("discover")
            self.game.events.emit("system_discovered", key=sec.key)

    # ------------------------------------------------------------------
    def handle_event(self, e) -> None:
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                from .menus import PauseScene
                self.game.scenes.push(PauseScene(self.game))
            elif e.key == pygame.K_l:
                self.try_land()
            elif e.key == pygame.K_e:
                self.try_dock()
            elif e.key == pygame.K_m:
                from .map import MapScene
                self.game.scenes.push(MapScene(self.game, self))
            elif e.key == pygame.K_TAB:
                self.cycle_target()
            elif e.key == pygame.K_b:
                from .logbook import LogbookScene
                self.game.scenes.push(LogbookScene(self.game))
            elif e.key == pygame.K_q:
                if len(self.game.state.weapons) > 1:
                    name = self.ship.cycle_weapon()
                    self.game.toasts.add(f"Weapon: {name}", (200, 220, 255), 1.5)
                    self.game.audio.play("ui", 0.6)
            elif e.key == pygame.K_p:
                self.toggle_autopilot()
            elif e.key == pygame.K_c:
                self.corps.hail()
            elif e.key == pygame.K_v:
                self.set_camera((self.cam_mode + 1) % len(CAMERAS))
            elif e.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                self.set_camera(self.cam_mode - 1)
            elif e.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                self.set_camera(self.cam_mode + 1)
        elif e.type == pygame.MOUSEWHEEL and e.y:
            self.set_camera(self.cam_mode - (1 if e.y > 0 else -1))

    def set_camera(self, mode: int) -> None:
        """Switch between the three camera distances (remembered in the settings)."""
        mode = max(0, min(len(CAMERAS) - 1, mode))
        if mode == self.cam_mode:
            return
        self.cam_mode = mode
        self.user_zoom = CAMERAS[mode][1]
        self.game.settings.camera = mode
        self.game.toasts.add(f"Camera: {CAMERAS[mode][0]}", (200, 220, 255), 1.2)
        self.game.audio.play("ui", 0.4)

    def controls(self) -> Controls:
        k = self.game.input.pressed()
        c = Controls()
        if self.dead_timer >= 0:
            return c
        c.thrust = k[pygame.K_w] or k[pygame.K_UP]
        c.turn = (k[pygame.K_d] or k[pygame.K_RIGHT]) - (k[pygame.K_a] or k[pygame.K_LEFT])
        c.boost = k[pygame.K_LSHIFT] or k[pygame.K_RSHIFT]
        c.match = k[pygame.K_s] or k[pygame.K_DOWN]
        c.fire = k[pygame.K_SPACE] or pygame.mouse.get_pressed()[0]
        if self.autopilot is not None:
            if c.thrust or c.turn or c.match:
                self.autopilot = None
                self.game.toasts.add("Autopilot disengaged", (200, 220, 255), 1.5)
            else:
                self._autopilot(c)
        return c

    # ------------------------------------------------------------------
    # autopilot & waypoints
    def _autopilot_target(self):
        st = self.game.state
        if st.waypoint:
            wp = Vector2(st.waypoint[0], st.waypoint[1])
            return (st.waypoint[2] if len(st.waypoint) > 2 else "Waypoint", lambda: wp, lambda: Vector2(), 500)
        body = self.target
        if body is None:
            q = self.game.quests.target()
            body = q[1] if q else None
        if body is None and st.boss_defeated and self.game.quests.cid == "shards":
            body = self.game.quests.shard_target(self.ship.pos)
        if body is None:
            return None
        arrive = body.radius * 2.2 + 260 if body.kind == "planet" else 300
        return (body.name, lambda b=body: b.pos(self.t), lambda b=body: b.vel(self.t), arrive)

    def toggle_autopilot(self) -> None:
        if self.autopilot is not None:
            self.autopilot = None
            self.game.toasts.add("Autopilot off", (200, 220, 255), 1.5)
            return
        tgt = self._autopilot_target()
        if tgt is None:
            self.game.toasts.add("Autopilot needs a target: TAB-select a body or set a waypoint on the map [M]",
                                 config.UI_WARN, 3)
            self.game.audio.play("deny")
            return
        self.autopilot = tgt
        self.game.toasts.add(f"Autopilot engaged: {tgt[0]}", (140, 230, 255), 2)
        self.game.audio.play("discover", 0.4)

    def _autopilot(self, c) -> None:
        label, pos_fn, vel_fn, arrive = self.autopilot
        ship, st = self.ship, self.game.state
        tpos, tvel = pos_fn(), vel_fn()
        rel = tpos - ship.pos
        dist = rel.length()
        if dist < arrive:
            c.match = True
            if (ship.vel - tvel).length() < 60:
                self.autopilot = None
                self.game.toasts.add(f"Autopilot: arrived at {label}", config.UI_GOOD, 2.5)
                self.game.audio.play("relic", 0.4)
                if st.waypoint and label == (st.waypoint[2] if len(st.waypoint) > 2 else "Waypoint"):
                    st.waypoint = None
            return
        n = rel / dist
        # steer around stars and black holes in the way
        for sec in self.sectors:
            for b in ([sec.star] if sec.star else []) + sec.hazards:
                bp = b.pos(self.t) - ship.pos
                along = bp.dot(n)
                if 0 < along < dist:
                    side = bp - n * along
                    clear = b.radius * (4 if b.kind == "blackhole" else 2.6)
                    if side.length() < clear:
                        perp = Vector2(-n.y, n.x)
                        if perp.dot(side) > 0:
                            perp = -perp
                        n = (n + perp * 1.2).normalize()
        accel = st.thrust * 0.55
        cruise = min(config.SHIP_MAX_SPEED * 0.85, math.sqrt(2 * accel * max(0.0, dist - arrive * 0.8)))
        desired = tvel + n * cruise
        dv = desired - ship.vel
        if dv.length() < 15:
            return
        want = math.degrees(math.atan2(dv.x, -dv.y))
        diff = (want - ship.angle + 180) % 360 - 180
        c.turn = max(-1.0, min(1.0, diff / 25))
        c.thrust = abs(diff) < 22 and dv.length() > 25
        c.boost = c.thrust and dist > 30000 and st.fuel > st.max_fuel * 0.4

    def cycle_target(self) -> None:
        cands = []
        for sec in self.sectors:
            for b in sec.planets + sec.stations + sec.hazards + sec.wormholes:
                d = b.pos(self.t).distance_to(self.ship.pos)
                if d < self.game.state.scanner_range * 2:
                    cands.append((d, b))
        cands.sort(key=lambda x: x[0])
        if not cands:
            self.target = None
            return
        bodies = [b for _, b in cands[:8]]
        if self.target in bodies:
            self.target = bodies[(bodies.index(self.target) + 1) % len(bodies)]
        else:
            self.target = bodies[0]
        self.game.audio.play("ui", 0.5)

    # ------------------------------------------------------------------
    def try_land(self) -> None:
        p = self.land_target
        if p is None:
            self.game.toasts.add("No landable world in range", config.UI_WARN, 1.5)
            self.game.audio.play("deny")
            return
        if self.game.quests.warden_alive(p):
            self._warden_blocks(p)
            return
        rel = (self.ship.vel - p.vel(self.t)).length()
        if rel > 650:
            self.game.toasts.add("Too fast for the landing computer - hold [S] to match speed", config.UI_WARN)
            self.game.audio.play("deny")
            return
        self.game.state.fuel = max(0.0, self.game.state.fuel - 8)
        self.game.audio.play("land")
        self.game.land(p)

    def _warden_blocks(self, planet) -> None:
        self.game.toasts.add(f"The Warden's interdiction field shields {planet.name} - destroy it first!",
                             config.UI_DANGER, 3)
        self.game.audio.play("deny")

    def try_dock(self) -> None:
        if self.saga.interact():
            return
        if self.near_forge is not None:
            self.use_forge()
            return
        if self.event_prompt is not None:
            self.event_prompt[1].interact()
            return
        if self.near_derelict is not None:
            d = self.near_derelict
            if d.id in self.game.state.derelicts_looted:
                self.game.toasts.add("Already stripped. Only echoes left.", (180, 180, 190))
            from .derelict import DerelictScene
            self.ship.vel = Vector2()
            self.game.audio.play("land", 0.6)
            self.game.scenes.push(DerelictScene(self.game, d), fade=True)
            return
        if self.near_wormhole is not None:
            self.warp(self.near_wormhole)
            return
        st = self.dock_target
        if st is None:
            return
        from .station import StationScene
        if self.towing is not None and self.towing.alive:
            self.towing.deliver()
        self.ship.vel = Vector2(st.vel(self.t))
        self.game.state.location = {"kind": "space", "near": st.id}
        self.game.audio.play("land", 0.6)
        self.game.scenes.push(StationScene(self.game, st))
        self.game.events.emit("docked", station_id=st.id)
        self.game.save()

    def use_forge(self) -> None:
        st, q = self.game.state, self.game.quests
        if st.ending == "destroy":
            self.game.toasts.add("Only cooling wreckage remains. Good riddance.", (200, 200, 210))
        elif st.forge_restored:
            self.game.toasts.add("The Forge burns steady. Earth-Prime turns in its light.", (140, 230, 255))
        elif q.cid == "forge" and st.has_all_shards():
            from ..systems.quests import FORGE_CHOICE
            from .choice import ChoiceScene
            self.game.audio.loop("thrust", False)
            self.game.scenes.push(ChoiceScene(self.game, "vey", FORGE_CHOICE[0], FORGE_CHOICE[1], [
                ("Reignite the Forge: rebuild Earth-Prime", lambda: self.game.start_ending("rebuild"),
                 "Give humanity its home back"),
                ("Shatter the Forge forever", lambda: self.game.start_ending("destroy"),
                 "No one will ever wield it again"),
                ("Not yet", lambda: None, "")]))
        elif st.boss_defeated:
            self.game.toasts.add(f"The Forge is dormant. Shards slotted: {len(st.shards)}/5", config.UI_VIOLET)
            self.game.audio.play("deny")
        else:
            self.game.toasts.add("A vast, broken ring of unknown origin. It feels... asleep.", (200, 200, 220))

    def warp(self, wh) -> None:
        ex, ey = wh.exit_sector
        sec = self.game.universe.sector(ex, ey)
        dest = sec.origin + Vector2(config.SECTOR_SIZE * 0.5, config.SECTOR_SIZE * 0.5)
        if sec.has_system:
            dest = sec.system_center + Vector2(sec.system_radius + 1500, 0).rotate(random.uniform(0, 360))
        self.game.audio.play("warp")
        self.game.banner.show("Wormhole transit", f"Emerged in sector {ex},{ey}")
        self.particles.clear()
        self.enemies.clear()
        self.bullets.clear()
        self.place_ship(dest, Vector2(), self.ship.angle)
        self.ship.invuln = 2.0
        self.game.shake(20)

    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        self.clock += dt
        st = self.game.state
        t = self.t
        ship = self.ship
        self._refresh_sectors()

        if self.dead_timer >= 0:
            self.dead_timer += dt
            self.particles.update(dt)
            if self.dead_timer > 1.6:
                self.game.game_over(self.death_reason)
            return

        ctl = self.controls()
        self.land_grace = max(0.0, self.land_grace - dt)
        self.flagship_cd -= dt
        ForgeGate.lit = len(st.shards)
        ForgeGate.restored = st.forge_restored and st.ending != "destroy"
        ForgeGate.destroyed = st.ending == "destroy"
        if st.ending and not st.signal_found:
            from ..systems.quests import signal_position
            if signal_position(self.game.universe).distance_to(ship.pos) < 700:
                st.signal_found = True
                from .act_two import BellScene
                self.game.audio.loop("thrust", False)
                self.game.scenes.push(BellScene(self.game), fade=True, force=True)
        d = distance_sectors(ship.pos, config.SECTOR_SIZE)
        if d > st.stats.get("max_distance", 0):
            st.stats["max_distance"] = d
        self.dominant = gravity.dominant_body(ship.pos, t, self.sources) if self.sources else None
        match_body = self.dock_target or self.land_target or self.dominant
        match_vel = match_body.vel(t) if match_body is not None else Vector2()
        acc = gravity.acceleration(ship.pos, t, self.sources)

        # nebulae: drag + stealth
        self.in_nebula = any(n.contains(ship.pos) for sec in self.sectors for n in sec.nebulae)
        if self.in_nebula:
            ship.vel *= max(0.0, 1 - 0.35 * dt)

        new_bullets = ship.update(dt, ctl, acc, match_vel, self.particles)
        self.bullets.extend(new_bullets)
        self.director.update(dt)
        self._update_extras(dt)
        self._space_hints()
        self.game.audio.loop("thrust", ship.thrusting, 0.35 if ship.boosting else 0.22)

        self._solar_recharge(dt)
        self._collisions(dt)
        self._update_combat(dt)
        self._spawn(dt)
        self._update_prompts()

        self.particles.update(dt)
        speed = ship.vel.length()
        self.camera.target_zoom = self.user_zoom / (1 + speed / 4200)
        self.camera.follow(ship.pos, ship.vel, dt)

        self._traj_timer -= 1
        if self._traj_timer <= 0:
            self._traj_timer = 4
            self.trajectory = gravity.predict(ship.pos, ship.vel, t, self.sources) if self.sources else []

        if st.hull <= 0 and self.dead_timer < 0:
            self._die("Your rocket broke apart.")

    def _update_extras(self, dt) -> None:
        """Comets, missiles and floating numbers."""
        ship = self.ship
        self.floaters.update(dt)
        for c in self.comets:
            c.update(dt, self.particles)
            if c.pos.distance_squared_to(ship.pos) < (c.radius + ship.RADIUS) ** 2:
                ship.damage(15)
                c.alive = False
                self.particles.burst(c.pos.x, c.pos.y, 30, 200, [(200, 230, 255), (255, 255, 255)])
        for b in self.bullets:
            if b.owner != "player" or not b.alive:
                continue
            if isinstance(b, Missile):
                b.steer(self.enemies, dt, self.particles)
            for c in self.comets:
                if c.alive and b.pos.distance_squared_to(c.pos) < c.radius ** 2:
                    b.alive = False
                    c.hp -= b.damage
                    self.particles.burst(b.pos.x, b.pos.y, 6, 120, [(200, 230, 255)], life=(0.1, 0.4))
                    if c.hp <= 0:
                        self._comet_destroyed(c)
                    break
        self.comets = [c for c in self.comets if c.alive]

    def _comet_destroyed(self, c) -> None:
        c.alive = False
        self.particles.burst(c.pos.x, c.pos.y, 40, 260, [(200, 230, 255), (255, 255, 255), (150, 190, 230)],
                             life=(0.4, 1.2))
        self.game.audio.play("explosion", 0.5)
        self.director.drop_comet_loot(c)

    def _space_hints(self) -> None:
        g, ship, t = self.game, self.ship, self.t
        if self.corps.battle is not None:
            g.hint("corps_battle", "A Survey Corps wing is fighting raiders! Help them out - every raider you "
                                   "down there earns Corps Merit, and they pay well if they survive.")
        from ..systems.corps import has_contact
        if has_contact(g.state):
            g.hint("corps_hail", "We have a Survey Corps contact now. Press [C] any time in space to hail them: "
                                 "fuel, repairs, a rescue tow or an escort - for Merit or credits.")
        for sec in self.sectors:
            for h in sec.hazards:
                d = h.pos(t).distance_to(ship.pos)
                if h.kind == "blackhole" and d < 9000:
                    g.hint("blackhole", "Black hole ahead. Its pull grows fast near the centre - don't cross the "
                                        "event horizon. The dashed line shows where we'll drift.")
                elif h.kind == "pulsar" and d < 9000:
                    g.hint("pulsar", "A pulsar: its sweeping beams cook hulls. Time your crossing between sweeps.")
            for w in sec.wormholes:
                if w.pos(t).distance_to(ship.pos) < 6000:
                    g.hint("wormhole", "A wormhole. Fly in and press [E] to jump 4-12 sectors away. One-way trip!")
            for d in sec.derelicts:
                if d.pos(t).distance_to(ship.pos) < 5000:
                    g.hint("derelict_near", "A derelict ship. Get close and press [E] to board it. Expect company.")
        if self.in_nebula:
            g.hint("nebula", "Nebula: raiders can't see us in here, but neither can our radar.")
        if self.dominant is not None and getattr(self.dominant, "biome_id", "") == "gas" and \
                self.dominant.pos(t).distance_to(ship.pos) < self.dominant.radius * 4:
            g.hint("gas", "Gas giants can't be landed on, but their gravity makes a great slingshot.")
        if self.enemies and g.quests.cid != "raiders":
            g.hint("combat", f"Hostiles! [{g.input.key_name('weapon')}] switches weapons once you own more. "
                             "Hold S to match speed and dodge.")
        if g.state.chapter >= 3:
            g.hint("autopilot", f"Long trip? TAB-select a target or click the galaxy map [M] for a waypoint, then "
                                f"press [{g.input.key_name('autopilot')}] for autopilot.")

    def _die(self, reason: str) -> None:
        self.death_reason = reason
        self.dead_timer = 0.0
        self.particles.explosion(self.ship.pos.x, self.ship.pos.y, 2.5)
        self.game.audio.play("explosion")
        self.game.audio.loop("thrust", False)
        self.game.shake(25)

    def _solar_recharge(self, dt) -> None:
        st = self.game.state
        star = self.system.star if self.system else None
        if star and st.fuel < config.EMERGENCY_FUEL:
            d = star.pos(self.t).distance_to(self.ship.pos)
            if d < star.radius * 10:
                st.fuel = min(config.EMERGENCY_FUEL, st.fuel + 6 * dt)
        if st.fuel < 1 and not self._fuel_warned:
            self._fuel_warned = True
            self.game.dialogue.say([("ai", "Fuel depleted. Drift close to a star - the solar sails will "
                                           "trickle-charge us. Or shoot asteroids for fuel cells.")])
        elif st.fuel > 30:
            self._fuel_warned = False

    def _collisions(self, dt) -> None:
        ship, t, st = self.ship, self.t, self.game.state
        self.warnings = []
        for sec in self.sectors:
            for b in sec.bodies:
                bp = b.pos(t)
                d_vec = ship.pos - bp
                dist = d_vec.length()
                reach = b.radius + ship.RADIUS
                if b.kind == "star":
                    if dist < b.radius * 2.2:
                        heat = (1 - (dist - b.radius) / (b.radius * 1.2))
                        ship.damage(max(0.0, heat) * 30 * dt, shake=False)
                        self.warnings.append("HULL OVERHEATING")
                elif b.kind == "blackhole":
                    if dist < b.radius * 4:
                        self.warnings.append("EVENT HORIZON PROXIMITY")
                    if dist < b.radius:
                        self._die("Spaghettified by a black hole.")
                        return
                    continue
                elif b.kind == "pulsar":
                    if b.in_beam(ship.pos, t, self.clock):
                        ship.damage(35 * dt, shake=False)
                        self.warnings.append("RADIATION BEAM")
                elif b.kind in ("wormhole", "forge"):
                    continue
                if dist >= reach or dist < 1e-3:
                    continue
                n = d_vec / dist
                bv = b.vel(t)
                rel = ship.vel - bv
                closing = -rel.dot(n)
                if b.kind == "planet" and b.landable and self.land_grace <= 0 and closing < config.SAFE_LANDING_SPEED and rel.length() < 260:
                    if not self.game.quests.warden_alive(b):
                        self.game.land(b)
                        return
                # bounce
                ship.pos = bp + n * (reach + 1)
                if closing > 0:
                    ship.vel = bv + (rel + n * closing * 1.5)
                    impact = closing
                    if b.kind == "asteroid":
                        impact *= 0.6
                    if impact > 60:
                        ship.damage(impact * 0.09)
                        self.particles.burst(ship.pos.x - n.x * 20, ship.pos.y - n.y * 20, 12, 120,
                                             [(255, 200, 120), (180, 180, 180)], life=(0.2, 0.5))
        if st.fuel < st.max_fuel * 0.15:
            self.warnings.append("LOW FUEL")

    def _update_combat(self, dt) -> None:
        ship = self.ship
        t = self.t
        torpedoes = [b for b in self.bullets if isinstance(b, Torpedo) and b.alive]
        for tp in torpedoes:
            tp.steer(ship.pos, dt)
        asteroids = [a for sec in self.sectors for a in sec.asteroids
                     if a.pos(t).distance_squared_to(ship.pos) < 3000 ** 2]
        for b in self.bullets:
            b.update(dt)
            if not b.alive:
                continue
            if b.owner == "ally":
                for e in self.enemies:
                    if e.alive and b.pos.distance_squared_to(e.pos) < e.radius ** 2:
                        b.alive = False
                        self.particles.burst(b.pos.x, b.pos.y, 5, 110, [(255, 200, 120)], life=(0.1, 0.3))
                        if e.hurt(b.damage):
                            self._ally_killed(e)
                        break
                continue
            if b.owner == "player":
                for e in self.enemies:
                    if e.alive and b.pos.distance_squared_to(e.pos) < e.radius ** 2:
                        b.alive = False
                        self.particles.burst(b.pos.x, b.pos.y, 6, 120, [(160, 255, 200)], life=(0.1, 0.3))
                        self.floaters.damage(e.pos.x, e.pos.y - e.radius, b.damage, crit=isinstance(b, Missile))
                        if e.hurt(b.damage):
                            self._enemy_killed(e)
                        else:
                            self.game.audio.play("hit", 0.3)
                        break
                else:
                    for tp in torpedoes:
                        if tp.alive and b.pos.distance_squared_to(tp.pos) < 26 ** 2:
                            b.alive = tp.alive = False
                            self.particles.burst(tp.pos.x, tp.pos.y, 14, 160, [(255, 160, 60), (255, 240, 180)])
                            self.game.audio.play("hit", 0.4)
                            break
                    else:
                        for a in asteroids:
                            ap = a.pos(t)
                            if b.pos.distance_squared_to(ap) < a.radius ** 2:
                                b.alive = False
                                a.hp -= b.damage
                                self.particles.burst(b.pos.x, b.pos.y, 4, 90, [(170, 160, 150)], life=(0.1, 0.4))
                                if a.hp <= 0:
                                    self._asteroid_destroyed(a, ap)
                                break
            else:
                if ship.pos.distance_squared_to(b.pos) < (ship.RADIUS + 4) ** 2:
                    b.alive = False
                    ship.damage(b.damage)
                    self.particles.burst(b.pos.x, b.pos.y, 10, 150, [(130, 255, 120), (255, 255, 255)])
                elif self.corps.ships and self.corps.hit(b):
                    b.alive = False
        self.bullets = [b for b in self.bullets if b.alive]

        self.bullets.extend(self.corps.update(dt))
        self.saga.update(dt)
        for e in list(self.enemies):
            foe = self.corps.target_for(e, ship) if isinstance(e, Raider) and self.corps.ships else ship
            shots = e.update(dt, foe, self.in_nebula and foe is ship, self.particles)
            self.bullets.extend(shots)
            queue = getattr(e, "spawn_queue", None)
            if queue:
                self.enemies.extend(queue)
                queue.clear()
            if e.pos.distance_squared_to(ship.pos) < (e.radius + ship.RADIUS) ** 2:
                ship.damage(30 if getattr(e, "is_boss", False) else 12)
                if not getattr(e, "is_boss", False):
                    e.hurt(2)
                e.vel = (e.pos - ship.pos).normalize() * 300 if e.pos != ship.pos else e.vel
                if not e.alive:
                    self._enemy_killed(e)
        self.enemies = [e for e in self.enemies if e.alive and
                        e.pos.distance_to(ship.pos) < (30000 if getattr(e, "is_boss", False) else 5500)]

        for p in self.pickups:
            p.update(dt, ship.pos)
            if p.pos.distance_squared_to(ship.pos) < 45 ** 2:
                p.alive = False
                self._collect(p)
        self.pickups = [p for p in self.pickups if p.alive]

    def _collect(self, p: Pickup) -> None:
        st = self.game.state
        if p.kind == "fuel":
            st.fuel = min(st.max_fuel, st.fuel + p.amount)
            msg = f"+{p.amount:.0f} fuel"
        elif p.kind == "repair":
            st.hull = min(st.max_hull, st.hull + p.amount)
            msg = f"+{p.amount:.0f} hull"
        elif p.kind == "credits":
            st.earn(int(p.amount))
            msg = f"+{p.amount:.0f} cr"
        elif p.kind == "ore":
            st.ore += int(p.amount)
            self.game.events.emit("ore_collected", amount=int(p.amount))
            msg = f"+{p.amount:.0f} ore"
        else:
            st.scan_data += int(p.amount)
            msg = f"+{p.amount:.0f} data"
        self.game.toasts.add(msg, (200, 255, 200), 1.4)
        self.game.audio.play("pickup", 0.6)

    def _ally_killed(self, e) -> None:
        """A Corps ship got the kill: a blast, a little loot, no bounty for you."""
        self.particles.explosion(e.pos.x, e.pos.y, 1.0, base_v=(e.vel.x * 0.3, e.vel.y * 0.3))
        self.game.audio.play("explosion", 0.5)
        self.corps.on_kill(e, by_player=False)
        self.saga.on_kill(e)
        if random.random() < 0.4:
            self.pickups.append(Pickup(e.pos, random.choice(["fuel", "repair"]), random.randint(20, 50)))

    def _enemy_killed(self, e) -> None:
        self.corps.on_kill(e, by_player=True)
        self.saga.on_kill(e)
        st = self.game.state
        if getattr(e, "is_boss", False):
            self.game.freeze(0.1)
            self.game.slowmo(1.4)
            st.add_rep("haven", 5)
            st.add_rep("remnant", -4)
            lore.announce(self.game, lore.next_log(st, "remnant"))
            import random as _r
            from ..systems.items import roll_mod
            mod = roll_mod(_r.Random(), min_rarity=1, luck=0.1)
            st.mods.append(mod)
            self.game.toasts.add(f"Salvaged: {mod['name']}", (200, 160, 255), 4)
            for k in range(6):
                off = Vector2(random.uniform(-90, 90), random.uniform(-90, 90))
                self.particles.explosion(e.pos.x + off.x, e.pos.y + off.y, 2.2)
            self.game.audio.play("explosion", 1.0)
            self.game.shake(30)
            for k in range(5):
                v = Vector2(1, 0).rotate(k * 72)
                self.pickups.append(Pickup(e.pos + v * 40, "credits", e.bounty // 5))
            self.pickups.append(Pickup(e.pos, "repair", 60))
            self.pickups.append(Pickup(e.pos + Vector2(30, 0), "fuel", 200))
            self.pickups.append(Pickup(e.pos - Vector2(30, 0), "data", 12))
            self.bullets = [b for b in self.bullets if b.owner == "player"]
            self.game.events.emit("enemy_destroyed", quest=False, elite=True, warden=e.warden,
                                  flagship=e.warden is None)
            if e.warden is None:
                self.game.banner.show(f"{e.name} destroyed", f"+{e.bounty} cr bounty scattered in the wreck")
            return
        self.particles.explosion(e.pos.x, e.pos.y, 1.4 if e.elite else 1.0, base_v=(e.vel.x * 0.3, e.vel.y * 0.3))
        self.game.audio.play("explosion", 0.7)
        self.game.shake(8)
        self.game.freeze(0.035)
        st.add_rep("haven", 1)
        self.pickups.append(Pickup(e.pos, "credits", e.bounty))
        roll = random.random()
        if roll < 0.35:
            self.pickups.append(Pickup(e.pos, "fuel", random.randint(40, 90)))
        elif roll < 0.6:
            self.pickups.append(Pickup(e.pos, "repair", random.randint(10, 25)))
        self.game.events.emit("enemy_destroyed", quest=e.quest, elite=e.elite)

    def _asteroid_destroyed(self, a, ap) -> None:
        self.game.universe.mark_destroyed(a.id)
        for sec in self.sectors:
            if a in sec.asteroids:
                sec.asteroids.remove(a)
                sec.bodies.remove(a)
        self.particles.burst(ap.x, ap.y, int(10 + a.radius / 2), 140, [(150, 140, 130), (110, 100, 90)],
                             life=(0.4, 1.2), size=(2, 6), drag=1.0)
        self.game.audio.play("hit", 0.5)
        if a.ore or random.random() < 0.3:
            self.pickups.append(Pickup(ap, "ore", random.randint(2, 5) if a.ore else 1))
        if random.random() < 0.45:
            self.pickups.append(Pickup(ap, "fuel", random.randint(25, 60)))

    def _spawn(self, dt) -> None:
        q = self.game.quests
        ship = self.ship
        self.spawn_timer -= dt
        if self.spawn_timer > 0:
            return
        self.spawn_timer = random.uniform(2.0, 5.0)
        if q.cid == "raiders":
            home = self.game.universe.find_body(HOME_STATION)
            hp = home.pos(self.t)
            quest_alive = sum(1 for e in self.enemies if e.quest)
            left = q.chapter["count"] - self.game.state.chapter_progress
            if quest_alive < min(3, left) and ship.pos.distance_to(hp) < 9000:
                pos = hp + Vector2(1, 0).rotate(random.uniform(0, 360)) * random.uniform(1800, 2600)
                r = Raider(self.game, pos, 1.0, quest=True)
                r.aggro = True
                self.enemies.append(r)
            return
        if q.cid in ("awaken", "signal", "boss"):
            return
        self._spawn_bosses()
        sec = self.game.universe.sector(*Universe.sector_coords(ship.pos))
        danger = sec.danger
        cap = min(7, int(1 + danger))
        if (sec.sx, sec.sy) == (0, 0):
            cap = 2
        if self.in_nebula or len(self.enemies) >= cap:
            return
        if random.random() < 0.25 + danger * 0.05:
            n = 1 if danger < 2 else random.randint(1, min(3, int(danger)))
            if ship.vel.length_squared() > 10000:
                ang = ship.vel.angle_to(Vector2(1, 0))
                dir_v = Vector2(1, 0).rotate(-ang + random.uniform(-65, 65))
            else:
                dir_v = Vector2(1, 0).rotate(random.uniform(0, 360))
            base = ship.pos + dir_v * random.uniform(1600, 2300)
            for i in range(n):
                elite = danger > 2.5 and random.random() < 0.15 + danger * 0.03
                r = Raider(self.game, base + Vector2(i * 90, 0), danger, elite=elite)
                r.aggro = True
                self.enemies.append(r)
            if n > 1:
                self.game.toasts.add("Raider squadron inbound!", config.UI_DANGER)
                self.game.audio.play("alarm", 0.5)

    def _spawn_bosses(self) -> None:
        st, ship, t = self.game.state, self.ship, self.t
        if not st.boss_defeated:
            return
        # each Shard world is blockaded by a Warden until it is destroyed
        for sec in self.sectors:
            pl = sec.shard_planet
            if pl is None or not self.game.quests.warden_alive(pl):
                continue
            if any(getattr(e, "warden", None) == sec.key for e in self.enemies):
                continue
            pp = pl.pos(t)
            if pp.distance_to(ship.pos) < 9000:
                pos = pp + (ship.pos - pp).normalize() * (pl.radius + 900) if ship.pos != pp else pp
                self.enemies.append(Dreadnought(self.game, pos, sec.danger + 1.0, warden=sec.key,
                                                name=f"Warden of {pl.name}"))
                self.game.toasts.add(f"A Remnant Warden guards {pl.name}!", config.UI_DANGER, 4)
                self.game.audio.play("alarm", 0.8)
        # roaming flagships in the deep sectors
        sec = self.game.universe.sector(*Universe.sector_coords(ship.pos))
        if self.flagship_cd > 0 or sec.danger < 2.2 or any(getattr(e, "is_boss", False) for e in self.enemies):
            return
        if random.random() < 0.12:
            self.flagship_cd = random.uniform(150, 260)
            pos = ship.pos + Vector2(1, 0).rotate(random.uniform(0, 360)) * 3300
            self.enemies.append(Dreadnought(self.game, pos, sec.danger))
            self.game.toasts.add("Remnant flagship detected on long-range scanners!", config.UI_DANGER, 4)
            self.game.audio.play("alarm", 0.6)

    def _update_prompts(self) -> None:
        ship, t = self.ship, self.t
        self.land_target = self.dock_target = self.near_wormhole = self.near_forge = None
        self.near_derelict = None
        self.event_prompt = self.director.nearest_prompt()
        self.saga_prompt = self.saga.prompt()
        best_l = best_d = float("inf")
        for sec in self.sectors:
            for p in sec.planets:
                if not p.landable:
                    continue
                d = p.pos(t).distance_to(ship.pos) - p.radius
                if d < p.radius * (config.LANDING_ASSIST_RANGE - 1) + 250 and d < best_l:
                    best_l, self.land_target = d, p
            for s in sec.stations:
                d = s.pos(t).distance_to(ship.pos)
                if d < 420 and d < best_d:
                    best_d, self.dock_target = d, s
            for w in sec.wormholes:
                if w.pos(t).distance_to(ship.pos) < w.radius * 1.4:
                    self.near_wormhole = w
            if sec.forge is not None and sec.forge.pos(t).distance_to(ship.pos) < sec.forge.radius * 2.2:
                self.near_forge = sec.forge
            for d in sec.derelicts:
                if d.pos(t).distance_to(ship.pos) < d.radius * 2.0:
                    self.near_derelict = d

    # ------------------------------------------------------------------
    def draw(self, surf: pygame.Surface) -> None:
        cam, t = self.camera, self.t
        surf.fill(config.SPACE_BG)
        self.starfield.draw(surf, cam.pos.x, cam.pos.y)
        for sec in self.sectors:
            for n in sec.nebulae:
                n.draw(surf, cam, self.clock)
        # orbits of the current system
        if self.system and cam.zoom < 0.35:
            sc = cam.to_screen(self.system.star.pos(t))
            for p in self.system.planets:
                if not p.is_moon:
                    r = p.orbit_r * cam.zoom
                    if r < 4000:
                        pygame.draw.circle(surf, (30, 40, 70), sc, r, 1)
        for sec in self.sectors:
            for b in sec.bodies:
                if cam.visible(b.pos(t), b.radius * (3 if b.kind in ("star", "blackhole") else 1.6)):
                    b.draw(surf, cam, t, self.clock)
                elif b.kind == "pulsar" and b.pos(t).distance_to(cam.pos) < b.beam_len:
                    b.draw(surf, cam, t, self.clock)
        if len(self.trajectory) > 1:
            pts = [cam.to_screen(p) for p in self.trajectory[::2]]
            for i in range(len(pts) - 1):
                if i % 2 == 0:
                    c = max(40, 200 - i * 3)
                    pygame.draw.line(surf, (c // 3, c // 2, c), pts[i], pts[i + 1], 2)
        for p in self.pickups:
            p.draw(surf, cam, self.clock)
        self.director.draw(surf, cam, self.clock)
        if self.game.state.ending:
            self._draw_bell(surf, cam)
        for c in self.comets:
            c.draw(surf, cam, self.clock)
        self.saga.draw(surf, cam)
        self.corps.draw(surf, cam)
        for e in self.enemies:
            e.draw(surf, cam)
        for b in self.bullets:
            b.draw(surf, cam)
        if self.dead_timer < 0:
            self.ship.draw(surf, cam, self.clock)
        self.particles.draw(surf, cam.to_screen, max(0.5, cam.zoom))
        self.floaters.draw(surf, cam.to_screen)
        self.director.overlay(surf)
        self._draw_hud(surf)

    def _draw_hud(self, surf) -> None:
        g, st, cam, t = self.game, self.game.state, self.camera, self.t
        hud.ship_status(surf, g, self.clock)
        hud.relic_slots(surf, g)
        ref = self.dock_target or self.land_target or self.dominant
        rel = (self.ship.vel - ref.vel(t)).length() if ref else self.ship.vel.length()
        loc = self.system.name if self.system else f"Deep space {self._sector_key[0]},{self._sector_key[1]}"
        info = f"speed {self.ship.vel.length():.0f}" + (f"  ·  vs {ref.name[:12]} {rel:.0f}" if ref else "")
        hud.location(surf, loc, info)
        hud.objective(surf, g)

        # compass arrows
        target = g.quests.target()
        if target and target[1] is not None:
            pos = target[1].pos(t)
            hud.edge_arrow(surf, cam.to_screen(pos), (255, 210, 90), target[0], pos.distance_to(self.ship.pos))
        if g.quests.cid == "keys":
            missing = g.quests.missing_relics()
            pl = g.universe.nearest_stronghold(self.ship.pos, missing, st.looted_strongholds,
                                               max_radius=2 + st.lvl("scanner"))
            if pl is not None:
                pos = pl.pos(t)
                hud.edge_arrow(surf, cam.to_screen(pos), (255, 210, 90),
                               f"Ancient signal: {pl.name} ({pl.biome.name})", pos.distance_to(self.ship.pos))
        if st.boss_defeated and g.quests.cid == "shards":
            pl = g.quests.shard_target(self.ship.pos)
            if pl is not None:
                pos = pl.pos(t)
                hud.edge_arrow(surf, cam.to_screen(pos), config.UI_VIOLET,
                               f"Shard vault: {pl.name} ({pl.biome.name})", pos.distance_to(self.ship.pos))
        if self.target is not None:
            pos = self.target.pos(t)
            hud.edge_arrow(surf, cam.to_screen(pos), pcol("target"), self.target.name, pos.distance_to(self.ship.pos))
        if st.waypoint:
            pos = Vector2(st.waypoint[0], st.waypoint[1])
            hud.edge_arrow(surf, cam.to_screen(pos), pcol("waypoint"),
                           st.waypoint[2] if len(st.waypoint) > 2 else "Waypoint", pos.distance_to(self.ship.pos))
        if st.ending and not st.signal_found:
            from ..systems.quests import signal_position
            pos = signal_position(g.universe)
            hud.edge_arrow(surf, cam.to_screen(pos), pcol("signal"), "??? The Bell", pos.distance_to(self.ship.pos))
        for e in self.enemies:
            if e.aggro and not cam.visible(e.pos, 40, 0):
                hud.edge_arrow(surf, cam.to_screen(e.pos), pcol("enemy"), "", None)
        self.saga.arrows(surf, cam)
        cap = self.corps.captain()
        if cap is not None and cam.visible(cap.pos, 40, 0):
            cx, cy = cam.to_screen(cap.pos)
            text(surf, cap.name, (cx, cy - 70), 15, (255, 140, 100), anchor="midbottom", outline=True)
        elif cap is not None:
            hud.edge_arrow(surf, cam.to_screen(cap.pos), (255, 120, 90), cap.name, cap.pos.distance_to(self.ship.pos))
        bt = self.corps.battle
        if bt is not None and not cam.visible(bt["pos"], 60, 0):
            hud.edge_arrow(surf, cam.to_screen(bt["pos"]), (255, 190, 90), "Corps battle",
                           bt["pos"].distance_to(self.ship.pos))
        for ev in self.director.events:
            if ev.label and not cam.visible(ev.pos, 40, 0) and ev.pos.distance_to(self.ship.pos) < 4000:
                hud.edge_arrow(surf, cam.to_screen(ev.pos), (255, 200, 120), ev.label, ev.pos.distance_to(self.ship.pos))

        self._draw_radar(surf)

        boss = self.boss
        if boss is not None:
            hud.boss_bar(surf, boss.name, boss.hp / boss.max_hp, enraged=boss.enraged)
        # prompts (hidden while someone is talking: the dialogue box owns the bottom)
        talking = g.dialogue.active
        if self.autopilot is not None and not talking:
            tp = self.autopilot[1]()
            hud.prompt(surf, f"AUTOPILOT  ->  {self.autopilot[0]}   {tp.distance_to(self.ship.pos) / 100:.0f} km   "
                             f"([{g.input.key_name('autopilot')}] or steer to cancel)", (140, 230, 255),
                       y=hud.PROMPT_Y - 48)
        self._draw_weapon(surf)
        if talking:
            pass
        elif self.saga_prompt is not None:
            hud.prompt(surf, *self.saga_prompt)
        elif self.near_forge is not None:
            hud.prompt(surf, "[E] The Stellar Forge", (255, 200, 110))
        elif self.event_prompt is not None:
            hud.prompt(surf, self.event_prompt[0], (255, 200, 120))
        elif self.near_derelict is not None:
            looted = self.near_derelict.id in st.derelicts_looted
            hud.prompt(surf, f"[E] Board the {self.near_derelict.name.replace('Wreck of the ', '')}"
                       + (" (searched)" if looted else ""), (200, 210, 230))
        elif self.near_wormhole is not None:
            hud.prompt(surf, "[E] Enter the wormhole", (210, 160, 255))
        elif self.dock_target is not None:
            hud.prompt(surf, f"[E] Dock at {self.dock_target.name}", (140, 230, 255))
        elif self.land_target is not None:
            p = self.land_target
            relv = (self.ship.vel - p.vel(t)).length()
            ok = relv < 650
            col = (150, 255, 150) if ok else config.UI_WARN
            extra = "" if ok else "  - too fast, hold [S]"
            if g.quests.warden_alive(p):
                col, extra = config.UI_DANGER, "  - blocked by the Warden"
            hud.prompt(surf, f"[L] Land on {p.name} ({p.biome.name}){extra}", col)
            if p.stronghold and p.id not in st.looted_strongholds:
                text(surf, "Ancient signal detected on surface", (config.SCREEN_W // 2, hud.PROMPT_Y + 30),
                     14, (255, 210, 90), anchor="center", outline=True)
        for i, w in enumerate(dict.fromkeys(self.warnings)):
            hud.warning(surf, w, self.clock, i)
        if self.in_nebula:
            text(surf, "In nebula: hidden from raiders, sensors scrambled", (config.SCREEN_W // 2, 40), 14,
                 (200, 160, 255), anchor="center")
        if g.settings.show_hints and not talking:
            k = g.input.key_name
            text(surf, hud.fit(f"W thrust  A/D turn  S brake  SPACE fire  L land  E dock  M map  "
                               f"{k('camera')} camera  {k('corps')} Corps  {k('autopilot')} autopilot",
                               config.SCREEN_W - 2 * 250),
                 (config.SCREEN_W // 2, config.SCREEN_H - 6), 12, (120, 130, 160), anchor="midbottom")

    def _draw_bell(self, surf, cam) -> None:
        from ..core.assets import glow
        from ..systems.quests import signal_position
        pos = signal_position(self.game.universe)
        if not cam.visible(pos, 900):
            return
        sx, sy = cam.to_screen(pos)
        z = cam.zoom
        g = glow(int(max(10, 500 * z)) // 8 * 8 + 8, (90, 240, 220), 0.6)
        surf.blit(g, g.get_rect(center=(sx, sy)), special_flags=pygame.BLEND_ADD)
        w, h = 260 * z, 320 * z
        pts = [(sx - w * 0.2, sy - h * 0.5), (sx + w * 0.2, sy - h * 0.5), (sx + w * 0.35, sy + h * 0.1),
               (sx + w * 0.5, sy + h * 0.45), (sx - w * 0.5, sy + h * 0.45), (sx - w * 0.35, sy + h * 0.1)]
        pygame.draw.polygon(surf, (30, 70, 80), pts)
        pygame.draw.polygon(surf, (120, 255, 230), pts, max(1, int(4 * z)))
        r = (self.clock * 120 * z) % (400 * z)
        pygame.draw.circle(surf, (120, 255, 230), (sx, sy), max(2, r), 1)

    def _draw_weapon(self, surf) -> None:
        st = self.game.state
        if len(st.weapons) < 2:
            return
        from ..systems.items import WEAPONS
        x, y = 22, config.SCREEN_H - 64
        panel(surf, (x - 10, y - 10, 66 * len(st.weapons) + 10, 56))
        for i, w in enumerate([w for w in WEAPONS if w in st.weapons]):
            r = pygame.Rect(x + i * 66, y, 56, 36)
            sel = w == st.weapon
            pygame.draw.rect(surf, (30, 50, 80) if sel else (14, 22, 38), r, border_radius=6)
            pygame.draw.rect(surf, config.UI_GOLD if sel else (60, 80, 110), r, 2, border_radius=6)
            surf.blit(hud.icon(self.game, WEAPONS[w]["icon"], 28), (r.x + 14, r.y + 4))
        text(surf, f"[{self.game.input.key_name('weapon')}]", (x + 66 * len(st.weapons) - 8, y - 6), 11,
             (150, 160, 190), anchor="topright")

    def _draw_radar(self, surf) -> None:
        """Radar inside a riveted porthole (Console style)."""
        from ..ui.text import theme
        th = theme()
        ring = th.parts["porthole"].img
        big = pygame.transform.scale(ring, (ring.get_width() * 2, ring.get_height() * 2))
        rc = big.get_rect(bottomright=(config.SCREEN_W - 12, config.SCREEN_H - 28))
        cx, cy = rc.center
        R = rc.w // 2 - 18
        pygame.draw.circle(surf, th.c["glass"], (cx, cy), R + 4)
        pygame.draw.circle(surf, th.c["glass_line"], (cx, cy), R // 2, 2)
        rng = self.game.state.scanner_range
        t = self.t
        if self.in_nebula and int(self.clock * 10) % 3:
            for _ in range(30):
                a, d = random.uniform(0, math.tau), random.uniform(0, R)
                surf.fill((90, 90, 120), (int(cx + math.cos(a) * d) // 2 * 2, int(cy + math.sin(a) * d) // 2 * 2, 2, 2))
        else:
            def plot(world, color, size):
                d = world - self.ship.pos
                if d.length() > rng:
                    return
                q = d / rng * (R - 4)
                n = size * 2
                surf.fill(color, (int(cx + q.x) // 2 * 2 - n // 2, int(cy + q.y) // 2 * 2 - n // 2, n, n))
            for sec in self.sectors:
                for b in sec.bodies:
                    if b.kind != "asteroid":
                        plot(b.pos(t), b.map_color(), 3 if b.kind in ("star", "blackhole") else 2)
            for e in self.enemies:
                plot(e.pos, pcol("enemy"), 3 if getattr(e, "is_boss", False) else 1)
            for a in self.corps.ships:
                plot(a.pos, (255, 190, 90), 2)
            for ev in self.director.events:
                plot(ev.pos, (255, 200, 120), 2)
            for p in self.pickups:
                plot(p.pos, (255, 230, 120), 1)
        fwd = self.ship.forward
        for k in range(5):
            surf.fill((255, 255, 255), (int(cx + fwd.x * k * 3) // 2 * 2, int(cy + fwd.y * k * 3) // 2 * 2, 4, 4))
        surf.blit(big, rc)
        text(surf, f"radar {rng / 1000:.0f}k", (cx, rc.bottom + 2), 13, th.c["dim"], anchor="midtop", outline=True)
