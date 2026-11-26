"""The on-foot pilot used by planet surfaces and the boss arena."""
from __future__ import annotations

import math

import pygame

from .. import config

SWING_TIME = 0.3
SPEAR_TIME = 0.42
BLASTER_COOLDOWN = 0.32
CHARGE_TIME = 0.7
HOOK_RANGE = 640


def base_gravity(p) -> float:
    return config.SURFACE_GRAVITY if p.k > 1 else 1500.0


class Pilot:
    _anim_cache: dict = {}

    W, H = 44, 84

    def __init__(self, game, x: float, ground_fn, gravity_mult: float = 1.0,
                 friction: float = 1.0, liquid=None, big: bool = True):
        """``big``: the 2x art-scale world (planets, caves, derelicts). The Warlord's
        arena still uses the original, smaller pilot."""
        self.game = game
        self.k = 1.75 if big else 1.0
        self.W, self.H = int(44 * self.k), int(84 * self.k)
        if big:
            self.speed, self.jump_v, self.jet_force = config.PLAYER_SPEED, config.PLAYER_JUMP, config.JETPACK_FORCE
            base_g = config.SURFACE_GRAVITY
        else:
            self.speed, self.jump_v, self.jet_force, base_g = 300.0, 640.0, 2300.0, 1500.0
        self.state = game.state
        self.ground = ground_fn
        self.x = x
        self.y = ground_fn(x)
        self.vx = self.vy = 0.0
        self.gravity = base_g * gravity_mult
        self.friction = friction
        self.liquid = liquid           # (kind, y, props) or None
        self.on_ground = True
        self.facing = 1
        self.air_time = 0.0
        self.jet = self.state.jetpack_capacity
        self.jetting = False
        self.peak_y = self.y            # highest point since you last stood, thrusted, swam or swung
        self.swing_t = 0.0
        self.swing_hit = set()
        self.blaster_t = 0.0
        self.invuln = 0.0
        self.hurt_flash = 0.0
        self.heal_t = 0.0
        self.submerged = False
        self.regen_delay = 0.0
        self.walk_anim = 0.0
        a = game.assets
        swing = [f"player/swing/swordSwing{i}.png" for i in range(1, 5)]
        if big:   # the original 80x80 art at the fixed art scale: crisp, uncropped frames
            sz = (80 * config.ART_SCALE, 80 * config.ART_SCALE)
        else:
            sz = (96, 96)
        self.idle = a.image("player/mainCharStill.png", size=sz)
        self.idle_l = a.image("player/mainCharStill.png", size=sz, flip_x=True)
        self.swing_r = [a.image(p, size=sz) for p in swing]
        self.swing_l = [a.image(p, size=sz, flip_x=True) for p in swing]
        self._jump_held = False
        # caves and derelicts have a ceiling
        self.ceiling = None
        self.anchor_fn = None
        self.charge = 0.0
        self._shoot_held = False

    # ------------------------------------------------------------------
    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(self.x - self.W / 2, self.y - self.H, self.W, self.H)

    @property
    def swinging(self) -> bool:
        return self.swing_t > 0

    @property
    def spear(self) -> bool:
        return self.state.foot_weapon == "spear"

    @property
    def swing_time(self) -> float:
        return SPEAR_TIME if self.spear else SWING_TIME

    def sword_rect(self) -> pygame.Rect | None:
        if not self.swinging or self.swing_t < self.swing_time * 0.15:
            return None
        if self.spear:   # long, narrow thrust
            w = 124 * self.k
            x = self.x + (6 if self.facing > 0 else -6 - w)
            return pygame.Rect(x, self.y - self.H * 0.75, w, 34 * self.k)
        w = 78 * self.k
        x = self.x + (10 * self.k if self.facing > 0 else -10 * self.k - w)
        return pygame.Rect(x, self.y - self.H - 10, w, self.H + 10)

    @property
    def melee_damage(self) -> float:
        return self.state.melee_damage * (1.6 if self.spear else 1.0)

    @property
    def hand(self):
        return self.x + self.facing * 10 * self.k, self.y - self.H * 0.6

    def update(self, dt: float, keys, enabled: bool = True) -> list:
        """Returns a list of spawned projectiles: (x, y, vx)."""
        shots = []
        left = keys[pygame.K_LEFT] or keys[pygame.K_a]
        right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
        jump = keys[pygame.K_UP] or keys[pygame.K_w]
        attack = keys[pygame.K_SPACE] or keys[pygame.K_j]
        shoot = keys[pygame.K_f] or keys[pygame.K_k]
        if not enabled:
            left = right = jump = attack = shoot = False

        target = (right - left) * self.speed
        if left != right:
            self.facing = 1 if right else -1
        ctrl = 12 * self.friction if self.on_ground else 4.0
        self.vx += (target - self.vx) * min(1.0, dt * ctrl)

        # liquid
        self.submerged = bool(self.liquid) and self.y - self.H * 0.4 > self.liquid[1]
        grav = self.gravity * (0.25 if self.submerged else 1.0)
        if self.submerged and "ocean" in self.state.trophies:
            self.vx += (target - self.vx) * min(1.0, dt * 6)   # Abyssal Pearl: swim like a fish

        if jump and not self._jump_held and (self.on_ground or self.submerged):
            self.vy = -self.jump_v * (0.65 if self.submerged else 1.0) * (0.85 + 0.15 / max(0.4, self.gravity / base_gravity(self)))
            self.on_ground = False
            self.air_time = 0
            self.game.audio.play("jump", 0.6)
        self.jetting = False
        if jump and not self.on_ground and self.air_time > 0.22 and self.jet > 0:
            self.vy -= self.jet_force * dt * (2 if self.submerged and "ocean" in self.state.trophies else 1)
            self.vy = max(self.vy, -560 * self.k ** 0.75)
            self.jet = max(0.0, self.jet - dt)
            self.jetting = True
        self._jump_held = jump

        self.vy += grav * dt
        if self.submerged:
            self.vx *= max(0.0, 1 - 2.0 * dt)
            self.vy *= max(0.0, 1 - 3.0 * dt)
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.ceiling is not None:
            top = self.ceiling(self.x) + self.H
            if self.y < top:
                self.y = top
                self.vy = max(self.vy, 0.0)
        gy = self.ground(self.x)
        if self.y >= gy:
            if not self.on_ground and self.vy > 250:
                self.land_squash = min(1.0, self.vy / 1100)   # visual squash on touchdown
                self.dust = True
            # hard landings hurt only after a real drop - never from a jump or a jetpack hop
            drop = gy - self.peak_y
            safe = config.SAFE_FALL * self.k / 1.75
            if not self.on_ground and drop > safe:
                self.hurt((drop - safe) * 0.04 * min(1.5, self.gravity / base_gravity(self)), 0)
            self.y = gy
            self.vy = 0
            self.on_ground = True
            self.air_time = 0
        else:
            self.on_ground = self.y >= gy - 2 and self.vy >= 0
            self.air_time += dt
        if self.on_ground or self.jetting or self.submerged:
            self.peak_y = self.y
        else:
            self.peak_y = min(self.peak_y, self.y)
        if self.on_ground:
            self.jet = min(self.state.jetpack_capacity, self.jet + dt * config.JETPACK_REGEN)
        elif not self.jetting and self.air_time > 0.5:
            self.jet = min(self.state.jetpack_capacity, self.jet + dt * 0.25)   # a trickle while gliding

        # combat
        self.swing_t = max(0.0, self.swing_t - dt)
        self.blaster_t = max(0.0, self.blaster_t - dt)
        if attack and self.swing_t <= 0:
            self.swing_t = self.swing_time
            self.swing_hit = set()
            self.game.audio.play("swing", 0.7)
        # blaster: tap to fire, hold to charge a piercing shot
        if shoot:
            if not self._shoot_held and self.blaster_t <= 0:
                self.blaster_t = BLASTER_COOLDOWN
                shots.append((self.x + self.facing * 30 * self.k, self.y - self.H * 0.55, self.facing * 900 * self.k,
                              1.0))
                self.game.audio.play("laser", 0.4)
                self.charge = 0.0
            else:
                self.charge += dt
        elif self._shoot_held:
            if self.charge >= CHARGE_TIME:
                shots.append((self.x + self.facing * 30 * self.k, self.y - self.H * 0.55, self.facing * 1300 * self.k,
                              4.0))
                self.game.audio.play("warp", 0.35)
                self.game.shake(5)
            self.charge = 0.0
        self._shoot_held = shoot

        self.invuln = max(0.0, self.invuln - dt)
        self.hurt_flash = max(0.0, self.hurt_flash - dt)
        self.heal_t = max(0.0, self.heal_t - dt)
        self.regen_delay = max(0.0, self.regen_delay - dt)
        if self.regen_delay <= 0:
            self.state.pilot_hp = min(self.state.max_pilot_hp, self.state.pilot_hp + 2.5 * dt)
        self.walk_anim += abs(self.vx) * dt * 0.05
        return shots

    # ------------------------------------------------------------------
    def _draw_charge(self, surf, ox, oy) -> None:
        if self.charge > 0.15:
            k = min(1.0, self.charge / CHARGE_TIME)
            c = (140, 230, 255) if k < 1 else (255, 255, 255)
            pygame.draw.circle(surf, c, (self.x + self.facing * 30 - ox, self.y - self.H * 0.55 - oy), 3 + 7 * k, 2)

    def hurt(self, amount: float, knock_dir: float = 0.0) -> bool:
        if self.invuln > 0 or amount <= 0:
            return False
        amount *= self.state.damage_taken
        self.state.pilot_hp = max(0.0, self.state.pilot_hp - amount)
        self.invuln = 0.7
        self.hurt_flash = 0.3
        self.regen_delay = 5.0
        if knock_dir:
            self.vx = knock_dir * 420 * self.k
            self.vy = -320 * self.k
            self.on_ground = False
        self.game.audio.play("hit", 0.6)
        self.game.shake(6)
        return True

    def hazard(self, dps: float, dt: float) -> None:
        """Continuous damage that ignores i-frames (lava, acid, spines)."""
        dps *= self.state.damage_taken
        self.state.pilot_hp = max(0.0, self.state.pilot_hp - dps * dt)
        self.regen_delay = 5.0
        self.hurt_flash = 0.1

    def apply_heal(self, particles=None, floaters=None) -> float:
        """Restore pilot HP with an emerald pulse and rising bio-gel particles."""
        import random
        st = self.state
        amount = max(config.MEDKIT_HEAL, st.max_pilot_hp * 0.45)
        healed = min(st.max_pilot_hp - st.pilot_hp, amount)
        st.pilot_hp = min(st.max_pilot_hp, st.pilot_hp + amount)
        self.heal_t = 0.85
        self.regen_delay = 0.0
        self.game.audio.play("pickup", 0.8)
        if particles is not None:
            cols = [(110, 255, 160), (180, 255, 220), (110, 230, 255)]
            for i in range(24):
                ang = i / 24 * math.tau
                vx = math.cos(ang) * random.uniform(40, 120)
                vy = -random.uniform(70, 210)
                particles.emit(self.x + math.cos(ang) * 16 * self.k,
                               self.y - random.uniform(10, self.H * 0.8),
                               vx, vy, random.uniform(0.4, 0.9), random.uniform(2, 5),
                               random.choice(cols), drag=1.8, glow=True)
        if floaters is not None and healed >= 1:
            floaters.add(self.x, self.y - self.H - 14, f"+{healed:.0f} HP", (120, 255, 160), 18, 1.3)
        return healed

    def use_medkit(self, particles=None, floaters=None) -> bool:
        """Spend one Nano-Medkit from inventory to heal the pilot."""
        st = self.state
        if st.medkits <= 0:
            self.game.toasts.add("No medkits left", config.UI_WARN, 1.4)
            self.game.audio.play("deny", 0.5)
            return False
        if st.pilot_hp >= st.max_pilot_hp - 0.5:
            self.game.toasts.add("Health is already full", (180, 220, 200), 1.3)
            self.game.audio.play("deny", 0.4)
            return False
        st.medkits -= 1
        self.apply_heal(particles, floaters)
        return True

    # ------------------------------------------------------------------
    def _animate(self, img):
        """Squash-and-stretch on top of the single hand-drawn frame:
        a bouncy lean while walking, stretch when rising, squash on landing."""
        import math
        sx = sy = 1.0
        angle = 0.0
        bob = 0.0
        squash = getattr(self, "land_squash", 0.0)
        if squash > 0:
            sx, sy = 1 + 0.22 * squash, 1 - 0.2 * squash
            self.land_squash = max(0.0, squash - 0.12)
        elif not self.on_ground and not self.submerged:
            k = max(-1.0, min(1.0, -self.vy / 700))
            sx, sy = 1 - 0.08 * k, 1 + 0.1 * k
            angle = -self.facing * max(-8, min(8, self.vx / 40))
        elif self.on_ground and abs(self.vx) > 30:
            ph = self.walk_anim
            bob = -abs(math.sin(ph)) * 6
            sy = 1 + 0.06 * math.sin(ph * 2)
            sx = 1 - 0.04 * math.sin(ph * 2)
            angle = -self.facing * (4 + 3 * math.sin(ph))
        else:  # idle breathing
            t = pygame.time.get_ticks() / 1000
            sy = 1 + 0.025 * math.sin(t * 2.4)
        if abs(sx - 1) < 0.01 and abs(sy - 1) < 0.01 and abs(angle) < 0.5:
            return img, bob
        key = (id(img), round(sx, 2), round(sy, 2), int(angle))
        cache = Pilot._anim_cache
        out = cache.get(key)
        if out is None:
            if len(cache) > 400:
                cache.clear()
            w, h = img.get_size()
            out = pygame.transform.scale(img, (max(1, int(w * sx)), max(1, int(h * sy))))
            if int(angle):
                out = pygame.transform.rotate(out, int(angle))
            cache[key] = out
        return out, bob

    def draw(self, surf, ox: float, oy: float) -> None:
        self._draw_charge(surf, ox, oy)
        if self.invuln > 0 and int(self.invuln * 20) % 2:
            return
        if self.swinging and self.spear:
            img = self.idle if self.facing > 0 else self.idle_l
            k = 1 - self.swing_t / SPEAR_TIME
            reach = (40 + 96 * math.sin(min(1.0, k * 1.6) * math.pi / 2)) * self.k
            u = max(2, int(round(self.k)))
            y0 = int(self.y - oy - self.H * 0.55) // 2 * 2
            x0 = int(self.x - ox + self.facing * 6 * self.k) // 2 * 2
            f = self.facing
            butt = int(x0 - f * 26 * self.k) // 2 * 2
            tip = int(x0 + f * reach) // 2 * 2
            sx0, sx1 = min(butt, tip), max(butt, tip)
            # Titanium alloy shaft with dark outline & top specular edge (matches Voyager suit)
            pygame.draw.rect(surf, (22, 30, 46), (sx0, y0 - 2 * u, sx1 - sx0, 4 * u))
            pygame.draw.rect(surf, (84, 110, 146), (sx0, y0 - u, sx1 - sx0, 2 * u))
            pygame.draw.rect(surf, (165, 195, 230), (sx0, y0 - u, sx1 - sx0, u))
            # Gold counterweight pommel at the rear
            pygame.draw.rect(surf, (225, 175, 70), (butt - (3 * u if f > 0 else 0), y0 - 2 * u, 3 * u, 4 * u))
            # Gold/cyan ion emitter collar behind the blade
            cx = tip - f * 4 * u
            pygame.draw.rect(surf, (255, 205, 90), (cx - 2 * u, y0 - 3 * u, 4 * u, 6 * u))
            pygame.draw.rect(surf, (100, 235, 255), (cx - u, y0 - 2 * u, 2 * u, 4 * u))
            # Stepped pixel-art Ion Blade + white-hot core
            blade_len = 16 * u
            pygame.draw.polygon(surf, (45, 175, 240),
                                [(tip, y0 - 4 * u), (tip + f * blade_len, y0), (tip, y0 + 4 * u)])
            pygame.draw.polygon(surf, (125, 238, 255),
                                [(tip, y0 - 2 * u), (tip + f * (blade_len - 3 * u), y0), (tip, y0 + 2 * u)])
            pygame.draw.polygon(surf, (235, 252, 255),
                                [(tip, y0 - u), (tip + f * (blade_len - 6 * u), y0), (tip, y0 + u)])
            if k < 0.75:
                pulse_x = tip - f * int(6 * u * k)
                pygame.draw.line(surf, (140, 240, 255), (pulse_x, y0 - 5 * u), (pulse_x, y0 + 5 * u), max(2, u))
        elif self.swinging:
            idx = min(3, int((1 - self.swing_t / SWING_TIME) * 4))
            img = (self.swing_r if self.facing > 0 else self.swing_l)[idx]
        else:
            img = self.idle if self.facing > 0 else self.idle_l
        img, bob = self._animate(img)
        rect = img.get_rect(midbottom=(self.x - ox, self.y - oy + 6 + bob))
        surf.blit(img, rect)
        if self.hurt_flash > 0:
            flash = img.copy()
            flash.fill((255, 60, 60, 0), special_flags=pygame.BLEND_RGB_ADD)
            surf.blit(flash, rect)
        if self.heal_t > 0:
            k = 1.0 - self.heal_t / 0.85
            pulse = math.sin(k * math.pi)
            glow = img.copy()
            glow.fill((int(40 * pulse), int(160 * pulse), int(90 * pulse), 0), special_flags=pygame.BLEND_RGB_ADD)
            surf.blit(glow, rect)
            cx, cy = int(self.x - ox), int(self.y - oy - self.H * 0.5)
            for delay, col in ((0.0, (110, 255, 160)), (0.2, (130, 235, 255))):
                rk = (k - delay) / max(0.01, 1.0 - delay)
                if 0 < rk < 1:
                    rad = max(8, int((18 + 68 * rk) * self.k))
                    ring = pygame.Surface((rad * 2 + 4, rad * 2 + 4), pygame.SRCALPHA)
                    pygame.draw.circle(ring, (*col, int(190 * (1 - rk))), (rad + 2, rad + 2), rad, 3)
                    surf.blit(ring, (cx - rad - 2, cy - rad - 2))
            # rising pixel-art '+' crosses around the pilot
            for i, dx in enumerate((-18, 0, 18)):
                ck = (k * 1.4 - i * 0.18) % 1.0
                if 0 < k * 1.4 - i * 0.18 < 1.0:
                    px = int(cx + dx * self.k)
                    py = int(cy - ck * 54 * self.k + 14)
                    a = int(240 * (1 - ck))
                    cross = pygame.Surface((12, 12), pygame.SRCALPHA)
                    pygame.draw.rect(cross, (130, 255, 170, a), (4, 1, 4, 10))
                    pygame.draw.rect(cross, (130, 255, 170, a), (1, 4, 10, 4))
                    surf.blit(cross, (px - 6, py - 6))
        if self.jetting:
            import random
            fx = self.x - ox - self.facing * 16
            fy = self.y - oy - 20
            for _ in range(3):
                pygame.draw.circle(surf, random.choice([(255, 200, 80), (255, 120, 40)]),
                                   (fx + random.uniform(-5, 5), fy + random.uniform(0, 18)), random.uniform(3, 6))
