"""In-game video cutscene (OpenCV if available) with a text fallback."""
from __future__ import annotations

import pygame

from .. import config
from ..core.scene import Scene
from ..ui.text import text

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None

CAPTIONS = [
    (0.0, "The Forge gate tears open above Haven..."),
    (2.5, "...and the Warlord drags you through."),
]


class CutsceneScene(Scene):
    music = "silence"

    def __init__(self, game, next_scene, video: str = "cutscene/colfin.mp4"):
        super().__init__(game)
        self.next_scene = next_scene
        self.t = 0.0
        self.done = False
        self.frame: pygame.Surface | None = None
        self.cap = None
        self.fps = 30.0
        self.frame_t = 0.0
        path = game.assets.resolve(video)
        if cv2 is not None and path is not None:
            cap = cv2.VideoCapture(str(path))
            if cap.isOpened():
                self.cap = cap
                self.fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.duration = 7.0 if self.cap is None else 60.0

    def on_enter(self) -> None:
        self.game.audio.play("warp")

    def _read(self) -> bool:
        ok, img = self.cap.read()
        if not ok:
            return False
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w = img.shape[:2]
        surf = pygame.image.frombuffer(img.tobytes(), (w, h), "RGB")
        scale = min(config.SCREEN_W / w, config.SCREEN_H / h)
        self.frame = pygame.transform.smoothscale(surf, (int(w * scale), int(h * scale)))
        return True

    def handle_event(self, e) -> None:
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_RETURN):
            self.finish()

    def finish(self) -> None:
        if self.done:
            return
        self.done = True
        if self.cap is not None:
            self.cap.release()
        self.game.scenes.switch(self.next_scene())

    def update(self, dt) -> None:
        self.t += dt
        if self.cap is not None:
            self.frame_t += dt
            while self.frame_t >= 1 / self.fps:
                self.frame_t -= 1 / self.fps
                if not self._read():
                    self.cap.release()
                    self.cap = None
                    self.duration = self.t + 1.5
                    break
        if self.t > self.duration:
            self.finish()

    def draw(self, surf) -> None:
        surf.fill((0, 0, 0))
        if self.frame is not None:
            surf.blit(self.frame, self.frame.get_rect(center=(config.SCREEN_W // 2, config.SCREEN_H // 2)))
        caption = ""
        for start, msg in CAPTIONS:
            if self.t >= start:
                caption = msg
        text(surf, caption, (config.SCREEN_W // 2, config.SCREEN_H - 60), 22, (255, 230, 200), anchor="center")
        text(surf, "[Space] skip", (config.SCREEN_W - 16, config.SCREEN_H - 12), 12, (150, 150, 150),
             anchor="bottomright")
