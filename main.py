"""Launcher kept for convenience: `python main.py` == `python -m stellar_forge`."""
import os
import sys
import traceback


def _android_fatal(tb: str) -> None:
    """Last-resort error screen on Android if import or startup crashes."""
    print(tb)
    priv = os.environ.get("ANDROID_PRIVATE", ".")
    try:
        os.makedirs(priv, exist_ok=True)
        with open(os.path.join(priv, "crash.log"), "a", encoding="utf-8") as f:
            f.write("\n--- MAIN FATAL ---\n" + tb)
    except Exception:
        pass
    if not (os.environ.get("ANDROID_ARGUMENT") or os.environ.get("P4A_BOOTSTRAP")):
        return
    try:
        try:
            from android.loadingscreen import hide_loading_screen
            hide_loading_screen()
        except Exception:
            pass
        import pygame
        pygame.init()
        surf = pygame.display.get_surface() or pygame.display.set_mode((0, 0))
        font = pygame.font.Font(None, 28)
        lines = ["STELLAR FORGE ERROR (tap to exit):"] + tb.splitlines()[-22:]
        for _ in range(300):
            for ev in pygame.event.get():
                if ev.type in (pygame.QUIT, pygame.FINGERDOWN, pygame.MOUSEBUTTONDOWN):
                    return
            surf.fill((24, 6, 10))
            y = 20
            for ln in lines:
                surf.blit(font.render(ln[:90], True, (255, 220, 220)), (20, y))
                y += 28
            pygame.display.flip()
            pygame.time.wait(100)
    except Exception:
        pass


if __name__ == "__main__":
    try:
        from stellar_forge.core.game import main
        main()
    except KeyboardInterrupt:
        pass
    except BaseException:
        _android_fatal(traceback.format_exc())
        sys.exit(1)
