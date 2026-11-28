"""The Game object: owns the window, services and the scene stack."""
from __future__ import annotations

import sys
import traceback

import pygame

from .. import config
from ..systems.achievements import AchievementTracker
from ..systems.quests import QuestManager
from ..ui.overlay import Banner, Dialogue, Toasts
from ..world.universe import Universe
from .assets import AssetManager
from .audio import Audio
from .events import EventBus
from .game_state import GameState
from .input import Input
from .music import Music
from .scene import SceneManager
from .settings import Settings


class Game:
    def __init__(self, headless: bool = False):
        # Pre-init the mixer BEFORE pygame.init() so SDL picks the right sample
        # rate and buffer size on all platforms (especially Linux PyInstaller builds
        # where the default buffer can be misdetected as 0).
        if not headless:
            pygame.mixer.pre_init(22050, -16, 2, 512)
        pygame.init()
        pygame.display.set_caption(config.TITLE)
        self.headless = headless
        self.settings = Settings.load()
        flags = pygame.SCALED | pygame.RESIZABLE if not headless else 0
        if self.settings.fullscreen and not headless:
            flags |= pygame.FULLSCREEN
        try:
            self.screen = pygame.display.set_mode((config.SCREEN_W, config.SCREEN_H), flags, vsync=1)
        except pygame.error:
            self.screen = pygame.display.set_mode((config.SCREEN_W, config.SCREEN_H), flags)
        self.clock = pygame.time.Clock()
        self.assets = AssetManager()
        self._set_icon()
        self.audio = Audio()
        self.music = Music(self.audio)
        self.events = EventBus()
        self.scenes = SceneManager(self)
        self.dialogue = Dialogue(self)
        self.toasts = Toasts(self.assets)
        self.banner = Banner()
        self.achievements = AchievementTracker(self)
        self.input = Input(self)
        from ..ui.touch import TouchOverlay
        self.touch = TouchOverlay(self)
        self.state: GameState | None = None
        self.universe: Universe | None = None
        self.quests: QuestManager | None = None
        self._space_scene = None
        self.net = None
        self._embedded_relay = None
        self.running = True
        self.hitstop = 0.0
        self.slow_t = 0.0
        self.apply_settings()
        self.music.prewarm(["title", "surface", "space"])

    def _set_icon(self) -> None:
        try:
            path = "generated/ui/icon.png" if self.assets.exists("generated/ui/icon.png") else \
                "generated/items/shard_crystal.png"
            # Load the 256px icon and let the OS / pygame pick the best size
            img = self.assets.image(path)
            pygame.display.set_icon(img)
        except pygame.error:
            pass

    # ------------------------------------------------------------------
    # settings
    @property
    def show_fps(self) -> bool:
        return self.settings.show_fps

    def apply_settings(self) -> None:
        s = self.settings
        self.audio.volume = s.master * s.sfx * 0.7
        self.music.volume = s.master * s.music * 0.8
        from ..ui import palette
        palette.set_colorblind(s.colorblind)
        if hasattr(self, "input"):
            self.input.rebuild_bindings()
        if hasattr(self, "touch"):
            self.touch.enabled = getattr(s, "touch_controls", False) or config.IS_ANDROID

    # ------------------------------------------------------------------
    # game feel
    def freeze(self, seconds: float) -> None:
        """Hit-stop: a tiny pause that sells big impacts."""
        self.hitstop = max(self.hitstop, seconds)

    def slowmo(self, seconds: float) -> None:
        self.slow_t = max(self.slow_t, seconds)

    def hint(self, hint_id: str, lines) -> bool:
        """Show a one-time contextual hint from the ship AI."""
        st = self.state
        if st is None or hint_id in st.hints_seen or not self.settings.show_hints:
            return False
        st.hints_seen.append(hint_id)
        if isinstance(lines, str):
            lines = [("ai", lines)]
        self.dialogue.say(lines)
        return True

    def toggle_fullscreen(self) -> None:
        if self.headless:
            return
        try:
            pygame.display.toggle_fullscreen()
            self.settings.fullscreen = not self.settings.fullscreen
            self.settings.save()
        except pygame.error:
            self.toasts.add("Fullscreen is not supported here", config.UI_WARN)

    # ------------------------------------------------------------------
    # campaign lifecycle
    def select_save(self, path) -> None:
        """Point saving/loading at a slot file."""
        config.SAVE_FILE = path

    def new_game(self, seed: int | None = None, difficulty: str = "normal", switch_scene: bool = True) -> None:
        state = GameState() if seed is None else GameState(seed=seed)
        state.difficulty = difficulty
        self._begin(state, switch_scene=switch_scene)
        self.quests.start()
        self.save()

    def new_game_plus(self) -> bool:
        old = GameState.load()
        if old is None or not old.forge_restored:
            return False
        self._begin(old.new_game_plus())
        self.quests.start()
        self.banner.show(f"NEW GAME+ {self.state.ng_plus}", "A new galaxy. Stronger foes. Your gear came with you.", 4.5)
        return True

    def continue_game(self) -> bool:
        state = GameState.load()
        if state is None:
            return False
        self._begin(state)
        self.toasts.add("Game loaded", config.UI_GOOD)
        return True

    def _begin(self, state: GameState, switch_scene: bool = True) -> None:
        from ..scenes.space import SpaceScene
        from ..scenes.surface import SurfaceScene
        self.events = EventBus()
        self.state = state
        bonus = state.ng_plus * config.NG_PLUS_DANGER - (0.5 if state.ending == "destroy" else 0.0)
        self.universe = Universe(state.seed, state.destroyed, bonus, earth=state.ending == "rebuild")
        self.quests = QuestManager(self)
        from ..systems import corps_career, saga
        corps_career.install(self)
        self.dialogue.queue.clear()
        self._space_scene = SpaceScene(self)
        saga.install(self)
        if self.quests.cid == "boss" and state.boss_defeated:
            self.quests._on_boss()          # saved during the Act II intro: resume in Act II
        if self.quests.cid == "boss" and not state.boss_defeated:
            from ..scenes.boss import BossScene
            if switch_scene:
                self.scenes.switch(BossScene(self))
            return
        loc = state.location
        if loc.get("kind") == "surface":
            planet = self.universe.find_body(loc.get("planet", "0,0:0")) or self.universe.find_body("0,0:0")
            if switch_scene:
                self.scenes.switch(SurfaceScene(self, planet))
        else:
            body = self.universe.find_body(loc.get("near", "")) if loc.get("near") else None
            if body is not None:
                self._space_scene.launch_from(body, quiet=True)
            else:
                self._space_scene.place_ship(pygame.Vector2(loc.get("x", 0), loc.get("y", 0)))
            if switch_scene:
                self.scenes.switch(self._space_scene)

    @property
    def space(self):
        return self._space_scene

    def _welcome_payload(self) -> dict:
        return {
            "seed": self.state.seed,
            "chapter": self.state.chapter,
            "keys": sorted(self.state.relics),
            "shards": sorted(self.state.shards),
            "boss_defeated": self.state.boss_defeated,
            "destroyed": list(self.state.destroyed),
            "ending": self.state.ending,
            "ng_plus": self.state.ng_plus,
        }

    def _enter_remote_galaxy(self, client, label: str) -> None:
        from ..net import NetSync
        w = client.welcome
        ch = max(2, int(w.get("chapter", 2)))  # join in space ready to fly with host
        st = GameState(
            seed=int(w["seed"]),
            chapter=ch,
            relics=list(w.get("keys", ())),
            shards=list(w.get("shards", ())),
            boss_defeated=bool(w.get("boss_defeated", False)),
            destroyed=list(w.get("destroyed", ())),
            ending=str(w.get("ending", "")),
            ng_plus=int(w.get("ng_plus", 0)),
            location={"kind": "space", "near": "0,0:st"},
        )
        self._begin(st)
        self.net = NetSync(self, client)
        self.toasts.add(f"Connected to {label}", config.UI_GOOD, 3.0)

    def host_multiplayer(self, port: int = 50556, name: str = "Voyager-1") -> int:
        """Open the current (or a fresh) galaxy as a LAN/Direct-IP co-op host."""
        from ..net import NetHost, NetSync
        self.stop_multiplayer()
        if self.state is None:
            self.new_game(switch_scene=False)
        host = NetHost(host_name=name, port=port)
        host.welcome_fn = self._welcome_payload
        bound = host.start()
        self.net = NetSync(self, host)
        return bound

    def host_relay(self, relay_host: str, relay_port: int = 50557, name: str = "Voyager-1") -> str:
        """Host the current (or a fresh) galaxy through a Room-Code relay server.

        If ``relay_host`` is localhost and no external relay is running, starts
        an embedded relay server automatically so Room Codes work out of the box.
        """
        from ..net import NetSync, RelayHost, RelayServer
        self.stop_multiplayer()
        if self.state is None:
            self.new_game(switch_scene=False)
        host = RelayHost(relay_host, relay_port, host_name=name)
        host.welcome_fn = self._welcome_payload
        try:
            code = host.start()
        except OSError:
            if relay_host not in ("127.0.0.1", "localhost", "0.0.0.0"):
                raise
            srv = RelayServer("0.0.0.0", port=relay_port)
            srv.start()
            self._embedded_relay = srv
            host = RelayHost("127.0.0.1", srv.port, host_name=name)
            host.welcome_fn = self._welcome_payload
            code = host.start()
        self.net = NetSync(self, host)
        return code

    def join_multiplayer(self, host_ip: str, port: int = 50556, name: str = "Voyager") -> None:
        """Connect to a co-op host via IP:port and enter their seeded galaxy."""
        from ..net import NetClient
        self.stop_multiplayer()
        client = NetClient(host_ip, port=port, name=name)
        client.connect()
        self._enter_remote_galaxy(client, f"{host_ip}:{port}")

    def join_relay(self, relay_host: str, relay_port: int = 50557, code: str = "", name: str = "Voyager") -> None:
        """Connect to a co-op host via a 6-character Room Code on a relay server."""
        from ..net import RelayClient
        self.stop_multiplayer()
        client = RelayClient(relay_host, relay_port, code=code, name=name)
        client.connect()
        self._enter_remote_galaxy(client, f"Room {client.code}")

    def stop_multiplayer(self) -> None:
        if self.net is not None:
            self.net.stop()
            self.net = None
        if self._embedded_relay is not None:
            self._embedded_relay.stop()
            self._embedded_relay = None

    def land(self, planet) -> None:
        from ..scenes.surface import SurfaceScene
        self.state.location = {"kind": "surface", "planet": planet.id}
        new = planet.id not in self.state.landed_planets
        self.state.mark("landed_planets", planet.id)
        self.state.mark("biomes_visited", planet.biome_id)
        self.events.emit("planet_landed", planet_id=planet.id, new=new)
        self.save()
        self.scenes.switch(SurfaceScene(self, planet))

    def launch(self, planet) -> None:
        self.state.location = {"kind": "space", "near": planet.id}
        self._space_scene.launch_from(planet)
        self.scenes.switch(self._space_scene)
        self.events.emit("launched", planet_id=planet.id)

    def start_boss_sequence(self) -> None:
        from ..scenes.boss import BossScene
        from ..scenes.cutscene import CutsceneScene
        self.save()
        self.scenes.switch(CutsceneScene(self, next_scene=lambda: BossScene(self)), force=True)

    def return_to_space_after_boss(self) -> None:
        from ..scenes.act_two import ActTwoScene
        self.state.boss_defeated = True     # quitting mid-cutscene must not mean a rematch
        self.state.location = {"kind": "space", "near": "0,0:st"}
        self.save()
        self.scenes.switch(ActTwoScene(self, on_done=self._after_boss), force=True)

    def _after_boss(self) -> None:
        home = self.universe.find_body("0,0:st")
        self._space_scene.launch_from(home, quiet=True)
        self.scenes.switch(self._space_scene, force=True)
        self.events.emit("boss_defeated")
        self.save()

    def start_ending(self, ending: str = "rebuild") -> None:
        from ..scenes.ending import EndingScene
        self.save()
        self.scenes.switch(EndingScene(self, ending), force=True)

    def finish_ending(self, ending: str = "rebuild") -> None:
        """Called when the ending's credits finish: back to Haven, free roam."""
        self.events.emit("forge_restored", ending=ending)
        if ending == "rebuild":
            self.universe.earth = True
            self.universe.rebuild_home()
        else:
            self.universe.danger_bonus -= 0.5
            self.universe._cache.clear()
        self._space_scene._refresh_sectors(force=True)
        home = self.universe.find_body("0,0:forge") or self.universe.find_body("0,0:st")
        self._space_scene.launch_from(home, quiet=True)
        self.scenes.switch(self._space_scene, force=True)
        self.save()

    def game_over(self, reason: str) -> None:
        from ..scenes.menus import GameOverScene
        self.audio.loop("thrust", False)
        self.scenes.switch(GameOverScene(self, reason), force=True)

    def save(self) -> None:
        if not self.state:
            return
        for scene in self.scenes.stack:
            if hasattr(scene, "save_location"):
                scene.save_location()
        self.state.destroyed = sorted(self.universe.destroyed)[-4000:]
        try:
            self.state.save()
        except OSError as exc:
            self.toasts.add(f"Save failed: {exc}", config.UI_DANGER)

    def shake(self, amount: float) -> None:
        amount *= self.settings.shake
        top = self.scenes.top
        cam = getattr(top, "camera", None)
        if cam is not None and amount > 0:
            cam.shake = max(cam.shake, amount)

    def _music_for_stack(self) -> str | None:
        for scene in reversed(self.scenes.stack):
            m = getattr(scene, "music", None)
            if m is not None:
                return None if m == "silence" else m
        return None

    # ------------------------------------------------------------------
    def run(self) -> None:
        from ..scenes.menus import TitleScene
        self.scenes.switch(TitleScene(self), fade=False)
        errors = 0
        while self.running:
            dt = min(self.clock.tick(config.FPS) / 1000.0, config.MAX_DT)
            try:
                self.step(dt)
                errors = max(0, errors - 1)
            except Exception:              # last line of defence: log it, recover, keep playing
                errors += 5
                self._recover(errors)
        self.settings.save()
        self.stop_multiplayer()
        self.audio.stop_all()
        pygame.quit()

    def _recover(self, errors: int) -> None:
        """Write the traceback to saves/crash.log and get the player back to something playable."""
        import traceback
        from datetime import datetime
        try:
            log = config.SAVE_FILE.parent / "crash.log"
            log.parent.mkdir(parents=True, exist_ok=True)
            with open(log, "a", encoding="utf-8") as f:
                f.write(f"\n--- {datetime.now():%Y-%m-%d %H:%M:%S}  scene={type(self.scenes.top).__name__}\n")
                f.write(traceback.format_exc())
        except Exception:
            pass
        try:
            if errors < 40:
                if errors <= 5:
                    self.toasts.add("Recovered from an error (details in saves/crash.log)", (255, 160, 120), 3)
                return
            # the same error every frame: leave that scene for a safe one
            if self.state is not None and self.scenes.top is not self.space:
                self.scenes.switch(self.space, fade=False, force=True)
                self.toasts.add("Something broke there - you're back in your ship", (255, 160, 120), 4)
            else:
                from ..scenes.menus import TitleScene
                self.scenes.switch(TitleScene(self), fade=False, force=True)
        except Exception:
            pass

    def _expand(self, events):
        for event in events:
            # Touch events are consumed by the overlay and turned into KEYDOWN/UP
            if event.type in (pygame.FINGERDOWN, pygame.FINGERUP, pygame.FINGERMOTION):
                self.touch.handle_event(event)
                continue
            if pygame.JOYAXISMOTION <= event.type <= pygame.JOYDEVICEREMOVED:
                yield from self.input.translate(event)
            else:
                ev = self.input.remap(event)
                if ev is not None:
                    yield ev

    def step(self, dt: float, events=None) -> None:
        for event in self._expand(pygame.event.get() if events is None else events):
            if event.type == pygame.QUIT:
                if self.state and self.state.hull > 0 and self.state.pilot_hp > 0:
                    self.save()
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN and self.dialogue.active:
                self.dialogue.advance()
                continue
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F3:
                self.settings.show_fps = not self.settings.show_fps
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                self.toggle_fullscreen()
                continue
            self.scenes.handle_event(event)
        real_dt = dt
        if self.hitstop > 0:
            self.hitstop -= dt
            dt = 0.0
        elif self.slow_t > 0:
            self.slow_t -= dt
            dt *= 0.3
        top = self.scenes.top
        if self.state and getattr(top, "advances_time", False) and not self.scenes.transitioning:
            self.state.world_time += dt
        if self.state and top is not None and not getattr(top, "menu", False):
            self.state.play_time += real_dt
            self.achievements.update(real_dt)
        self.scenes.update(dt)
        if self.net is not None:
            self.net.update(real_dt)
        self.music.play(self._music_for_stack())
        self.music.update(real_dt)
        self.dialogue.update(real_dt)
        self.toasts.update(real_dt)
        self.banner.update(real_dt)
        self.scenes.draw(self.screen)
        in_menu = bool(getattr(self.scenes.top, "menu", False))
        if not in_menu:                     # title cards never cover a menu
            self.banner.draw(self.screen)
        self.toasts.draw(self.screen, in_menu)
        self.dialogue.draw(self.screen)
        # Touch overlay drawn on top of everything except the FPS counter
        self.touch.draw(self.screen)
        if self.show_fps:
            from ..ui.text import text
            text(self.screen, f"{self.clock.get_fps():.0f} fps", (config.SCREEN_W - 8, config.SCREEN_H - 8),
                 14, anchor="bottomright")
        pygame.display.flip()


def main() -> None:
    try:
        Game().run()
    except KeyboardInterrupt:
        pass
    except Exception:
        traceback.print_exc()
        sys.exit(1)
