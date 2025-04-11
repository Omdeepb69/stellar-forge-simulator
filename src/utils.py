import pygame
import json
import joblib
import os
import random
import math
from typing import Dict, Any, Tuple, List, Optional, Union

# Constants
# Colors (RGB)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)
GRAY = (128, 128, 128)
LIGHT_GRAY = (200, 200, 200)
DARK_GRAY = (50, 50, 50)

# Physics Constants (adjust as needed for simulation scale)
G = 6.67430e-5 # Adjusted Gravitational constant for 2D simulation stability/visuals
PI = math.pi
TWO_PI = 2 * PI

# Default Configuration
DEFAULT_CONFIG = {
    "screen_width": 1280,
    "screen_height": 720,
    "fps": 60,
    "time_scale": 1.0,
    "gravity_constant": G,
    "star_min_mass": 1e6,
    "star_max_mass": 5e7,
    "planet_min_mass": 1e3,
    "planet_max_mass": 1e5,
    "planet_min_radius": 5,
    "planet_max_radius": 20,
    "min_planets": 2,
    "max_planets": 8,
    "min_orbit_radius": 100,
    "max_orbit_radius": 500,
    "orbit_spacing_factor": 1.5,
    "asteroid_field_count": 1,
    "asteroids_per_field": 100,
    "asteroid_min_radius": 0.5,
    "asteroid_max_radius": 2.0,
    "asteroid_field_radius_factor": 1.2,
    "rocket_mass": 100.0,
    "rocket_thrust": 5000.0,
    "rocket_fuel": 1000.0,
    "fuel_consumption_rate": 1.0,
    "ml_model_path": "models/planet_model.joblib",
    "save_game_path": "saves/savegame.json",
    "log_level": "INFO",
    "seed": None # Use None for random seed, or an integer for deterministic generation
}

# --- Configuration Management ---

def load_config(config_path: str = "config.json") -> Dict[str, Any]:
    """Loads configuration from a JSON file, using defaults if file not found."""
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                user_config = json.load(f)
            # Merge user config with defaults, overriding defaults
            config = DEFAULT_CONFIG.copy()
            config.update(user_config)
            return config
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in {config_path}. Using default configuration.")
            return DEFAULT_CONFIG.copy()
        except Exception as e:
            print(f"Error loading config file {config_path}: {e}. Using default configuration.")
            return DEFAULT_CONFIG.copy()
    else:
        print(f"Warning: Config file {config_path} not found. Using default configuration.")
        return DEFAULT_CONFIG.copy()

def save_config(config: Dict[str, Any], config_path: str = "config.json") -> None:
    """Saves the current configuration to a JSON file."""
    try:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Error saving config file {config_path}: {e}")

# --- File Operations ---

def save_json(data: Any, file_path: str) -> bool:
    """Saves data to a JSON file."""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
        return True
    except TypeError as e:
        print(f"Error: Data not JSON serializable when saving to {file_path}: {e}")
        return False
    except Exception as e:
        print(f"Error saving JSON file {file_path}: {e}")
        return False

def load_json(file_path: str) -> Optional[Any]:
    """Loads data from a JSON file."""
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return None
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {file_path}.")
        return None
    except Exception as e:
        print(f"Error loading JSON file {file_path}: {e}")
        return None

def save_model(model: Any, file_path: str) -> bool:
    """Saves a machine learning model using joblib."""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        joblib.dump(model, file_path)
        return True
    except Exception as e:
        print(f"Error saving model to {file_path}: {e}")
        return False

def load_model(file_path: str) -> Optional[Any]:
    """Loads a machine learning model using joblib."""
    if not os.path.exists(file_path):
        print(f"Error: Model file not found: {file_path}")
        return None
    try:
        model = joblib.load(file_path)
        return model
    except Exception as e:
        print(f"Error loading model from {file_path}: {e}")
        return None

# --- Math & Physics Helpers ---

Vector2 = pygame.math.Vector2

def distance_sq(p1: Vector2, p2: Vector2) -> float:
    """Calculates the squared distance between two points."""
    return (p1.x - p2.x)**2 + (p1.y - p2.y)**2

def distance(p1: Vector2, p2: Vector2) -> float:
    """Calculates the distance between two points."""
    return math.sqrt(distance_sq(p1, p2))

def normalize(v: Vector2) -> Vector2:
    """Returns the normalized vector."""
    mag = v.length()
    if mag == 0:
        return Vector2(0, 0)
    return v / mag

def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamps a value between min_val and max_val."""
    return max(min_val, min(value, max_val))

def random_color() -> Tuple[int, int, int]:
    """Generates a random RGB color."""
    return (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))

def world_to_screen(world_pos: Vector2, camera_offset: Vector2, zoom: float, screen_center: Vector2) -> Tuple[int, int]:
    """Converts world coordinates to screen coordinates."""
    screen_pos = (world_pos - camera_offset) * zoom + screen_center
    return int(screen_pos.x), int(screen_pos.y)

def screen_to_world(screen_pos: Tuple[int, int], camera_offset: Vector2, zoom: float, screen_center: Vector2) -> Vector2:
    """Converts screen coordinates to world coordinates."""
    world_pos = (Vector2(screen_pos) - screen_center) / zoom + camera_offset
    return world_pos

# --- Data Visualization (Pygame specific) ---

def draw_text(surface: pygame.Surface, text: str, pos: Tuple[int, int], font: pygame.font.Font, color: Tuple[int, int, int] = WHITE, align: str = "topleft") -> None:
    """Draws text on a Pygame surface."""
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect()
    if align == "center":
        text_rect.center = pos
    elif align == "topright":
        text_rect.topright = pos
    elif align == "bottomleft":
        text_rect.bottomleft = pos
    elif align == "bottomright":
        text_rect.bottomright = pos
    else: # Default to topleft
        text_rect.topleft = pos
    surface.blit(text_surface, text_rect)

def draw_circle_scaled(surface: pygame.Surface, color: Tuple[int, int, int], world_pos: Vector2, radius: float, camera_offset: Vector2, zoom: float, screen_center: Vector2, width: int = 0) -> None:
    """Draws a circle adjusted for camera view."""
    screen_pos = world_to_screen(world_pos, camera_offset, zoom, screen_center)
    scaled_radius = max(1, int(radius * zoom)) # Ensure radius is at least 1 pixel
    pygame.draw.circle(surface, color, screen_pos, scaled_radius, width)

def draw_line_scaled(surface: pygame.Surface, color: Tuple[int, int, int], world_start: Vector2, world_end: Vector2, camera_offset: Vector2, zoom: float, screen_center: Vector2, width: int = 1) -> None:
    """Draws a line adjusted for camera view."""
    screen_start = world_to_screen(world_start, camera_offset, zoom, screen_center)
    screen_end = world_to_screen(world_end, camera_offset, zoom, screen_center)
    pygame.draw.line(surface, color, screen_start, screen_end, max(1, int(width))) # Ensure width is at least 1

def draw_polygon_scaled(surface: pygame.Surface, color: Tuple[int, int, int], world_points: List[Vector2], camera_offset: Vector2, zoom: float, screen_center: Vector2, width: int = 0) -> None:
    """Draws a polygon adjusted for camera view."""
    screen_points = [world_to_screen(p, camera_offset, zoom, screen_center) for p in world_points]
    if len(screen_points) > 2: # Need at least 3 points for a polygon
        pygame.draw.polygon(surface, color, screen_points, width)

def draw_trajectory(surface: pygame.Surface, points: List[Vector2], color: Tuple[int, int, int], camera_offset: Vector2, zoom: float, screen_center: Vector2, width: int = 1) -> None:
    """Draws a trajectory path adjusted for camera view."""
    if len(points) < 2:
        return
    screen_points = [world_to_screen(p, camera_offset, zoom, screen_center) for p in points]
    pygame.draw.lines(surface, color, False, screen_points, max(1, int(width)))

# --- Metrics Calculation ---

class FpsCalculator:
    """Calculates and stores Frames Per Second."""
    def __init__(self) -> None:
        self.clock = pygame.time.Clock()
        self.fps = 0.0

    def tick(self, target_fps: int) -> float:
        """Ticks the clock and updates FPS."""
        self.clock.tick(target_fps)
        self.fps = self.clock.get_fps()
        return self.fps

    def get_fps(self) -> float:
        """Returns the current calculated FPS."""
        return self.fps

# --- ML Model Interaction ---

_ml_model_cache: Dict[str, Any] = {}

def get_ml_model(model_path: str) -> Optional[Any]:
    """Loads an ML model, using a cache to avoid redundant loads."""
    if model_path in _ml_model_cache:
        return _ml_model_cache[model_path]

    model = load_model(model_path)
    if model:
        _ml_model_cache[model_path] = model
    return model

def predict_planet_properties(model: Any, input_features: List[List[float]]) -> Optional[Any]:
    """
    Uses a loaded ML model to predict planet properties.
    Assumes the model has a 'predict' method compatible with scikit-learn.
    Input features format depends on how the model was trained (e.g., [[orbital_distance, star_mass], ...]).
    Returns the prediction result, format depends on the model.
    """
    if not hasattr(model, 'predict'):
        print("Error: Loaded model does not have a 'predict' method.")
        return None
    try:
        predictions = model.predict(input_features)
        return predictions
    except Exception as e:
        print(f"Error during model prediction: {e}")
        return None

# --- Other Utilities ---

def setup_random_seed(seed: Optional[int] = None) -> None:
    """Initializes the random number generator with a specific seed."""
    if seed is not None:
        random.seed(seed)
        # Note: If using numpy or other libraries with their own RNG, seed them here too.
        # import numpy as np
        # np.random.seed(seed)
        print(f"Random seed set to: {seed}")
    else:
        print("Using random seed.")

def generate_unique_id() -> str:
    """Generates a simple unique ID (useful for objects)."""
    return f"obj_{random.randint(10000, 99999)}_{int(pygame.time.get_ticks())}"

def format_time(seconds: float) -> str:
    """Formats a duration in seconds into H:M:S or M:S format."""
    total_seconds = int(seconds)
    secs = total_seconds % 60
    total_minutes = total_seconds // 60
    mins = total_minutes % 60
    hours = total_minutes // 60

    if hours > 0:
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    else:
        return f"{mins:02d}:{secs:02d}"

def scale_value(value: float, min1: float, max1: float, min2: float, max2: float) -> float:
    """Scales a value from one range to another."""
    if max1 - min1 == 0: return min2 # Avoid division by zero
    return min2 + (value - min1) * (max2 - min2) / (max1 - min1)

# Example usage within the project might look like:
# config = load_config()
# screen = pygame.display.set_mode((config['screen_width'], config['screen_height']))
# font = pygame.font.SysFont(None, 24)
# fps_calc = FpsCalculator()
#
# # In game loop:
# dt = clock.tick(config['fps']) / 1000.0 * config['time_scale']
# current_fps = fps_calc.get_fps()
# draw_text(screen, f"FPS: {current_fps:.1f}", (10, 10), font)
# draw_circle_scaled(screen, BLUE, planet.position, planet.radius, camera.offset, camera.zoom, screen_center)