```python
import pygame
import math
import random
import numpy as np
import sys

# Constants
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
GRAY = (128, 128, 128)
ORANGE = (255, 165, 0)

DEFAULT_ZOOM = 0.01
MIN_ZOOM = 0.0001
MAX_ZOOM = 1.0
ZOOM_FACTOR = 1.1
PAN_SPEED = 10 # Screen pixels per frame

# Helper function for drawing text
def draw_text(surface, text, position, font, color=WHITE):
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect(topleft=position)
    surface.blit(text_surface, text_rect)

class Camera:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.zoom = DEFAULT_ZOOM
        # World coordinates of the center of the screen
        self.center_offset = np.array([0.0, 0.0])
        self.target_object = None # Optional object to follow

    def set_target(self, target):
        self.target_object = target

    def update(self, dt):
        if self.target_object:
            # Smoothly follow the target
            # target_pos = np.array(self.target_object.position)
            # current_center = self.center_offset
            # self.center_offset += (target_pos - current_center) * 0.1 # Simple lerp
            # For now, just snap to target
             self.center_offset = np.array(self.target_object.position)


    def apply_transform(self, world_pos):
        # 1. Translate world coordinates relative to camera center
        relative_pos = np.array(world_pos) - self.center_offset
        # 2. Scale by zoom level
        scaled_pos = relative_pos * self.zoom
        # 3. Translate to screen coordinates (origin top-left)
        screen_x = scaled_pos[0] + self.width / 2
        screen_y = scaled_pos[1] + self.height / 2
        return int(screen_x), int(screen_y)

    def apply_zoom_to_radius(self, world_radius):
        # Scale radius, ensuring minimum pixel size for visibility
        scaled_radius = max(1, int(world_radius * self.zoom))
        return scaled_radius

    def screen_to_world(self, screen_pos):
        screen_x, screen_y = screen_pos
        # 1. Translate screen coordinates relative to screen center
        relative_screen_x = screen_x - self.width / 2
        relative_screen_y = screen_y - self.height / 2
        # 2. Scale by inverse zoom level
        scaled_pos_x = relative_screen_x / self.zoom
        scaled_pos_y = relative_screen_y / self.zoom
        # 3. Add camera center offset
        world_x = scaled_pos_x + self.center_offset[0]
        world_y = scaled_pos_y + self.center_offset[1]
        return np.array([world_x, world_y])

    def zoom_in(self):
        self.zoom *= ZOOM_FACTOR
        self.zoom = min(self.zoom, MAX_ZOOM)

    def zoom_out(self):
        self.zoom /= ZOOM_FACTOR
        self.zoom = max(self.zoom, MIN_ZOOM)

    def pan(self, dx, dy):
        # Pan amount needs to be scaled by inverse zoom to move correctly in world space
        self.center_offset += np.array([dx / self.zoom, dy / self.zoom])
        self.target_object = None # Stop following target when panning manually


class Visualization:
    def __init__(self, width=SCREEN_WIDTH, height=SCREEN_HEIGHT):
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Stellar Forge Simulator")
        self.clock = pygame.time.Clock()
        self.font_small = pygame.font.SysFont(None, 24)
        self.font_medium = pygame.font.SysFont(None, 36)
        self.font_large = pygame.font.SysFont(None, 48)
        self.camera = Camera(self.width, self.height)
        self.show_debug_info = False
        self.show_trajectory = True
        self.num_bg_stars = 200
        self.bg_stars = [(random.randint(0, self.width), random.randint(0, self.height), random.randint(1, 2))
                         for _ in range(self.num_bg_stars)] # (x, y, size)

    def _world_to_screen(self, world_pos):
        return self.camera.apply_transform(world_pos)

    def _scale_radius(self, world_radius):
        return self.camera.apply_zoom_to_radius(world_radius)

    def _draw_background(self):
        self.screen.fill(BLACK)
        for x, y, size in self.bg_stars:
            pygame.draw.circle(self.screen, GRAY, (x, y), size)

    def _draw_star(self, star):
        screen_pos = self._world_to_screen(star.position)
        screen_radius = self._scale_radius(star.radius)
        # Draw corona effect
        corona_radius = int(screen_radius * 1.5)
        if corona_radius > screen_radius:
             # Create a surface for the corona effect
            corona_surface = pygame.Surface((corona_radius * 2, corona_radius * 2), pygame.SRCALPHA)
            alpha = 50 # Adjust alpha for desired intensity
            color_with_alpha = star.color + (alpha,)
            pygame.draw.circle(corona_surface, color_with_alpha, (corona_radius, corona_radius), corona_radius)
            self.screen.blit(corona_surface, (screen_pos[0] - corona_radius, screen_pos[1] - corona_radius))

        pygame.draw.circle(self.screen, star.color, screen_pos, screen_radius)


    def _draw_planet(self, planet):
        screen_pos = self._world_to_screen(planet.position)
        screen_radius = self._scale_radius(planet.radius)

        # Draw atmosphere if dense enough
        if hasattr(planet, 'atmosphere_density') and planet.atmosphere_density > 0.1 and screen_radius > 1:
            atmosphere_radius = int(screen_radius * (1 + planet.atmosphere_density * 0.2)) # Scale atmosphere size
            if atmosphere_radius > screen_radius:
                atmosphere_surface = pygame.Surface((atmosphere_radius * 2, atmosphere_radius * 2), pygame.SRCALPHA)
                # Use planet color with low alpha for atmosphere
                atmosphere_color = planet.color + (30,) # Low alpha
                pygame.draw.circle(atmosphere_surface, atmosphere_color, (atmosphere_radius, atmosphere_radius), atmosphere_radius)
                self.screen.blit(atmosphere_surface, (screen_pos[0] - atmosphere_radius, screen_pos[1] - atmosphere_radius))

        pygame.draw.circle(self.screen, planet.color, screen_pos, screen_radius)

        # Draw label if zoomed in enough
        if self.camera.zoom > 0.05:
             draw_text(self.screen, planet.name, (screen_pos[0] + screen_radius + 5, screen_pos[1]), self.font_small, WHITE)


    def _draw_asteroid(self, asteroid_pos, asteroid_radius):
         screen_pos = self._world_to_screen(asteroid_pos)
         # Simple polygon for asteroid shape
         points = []
         num_points = random.randint(5, 8)
         base_radius = self._scale_radius(asteroid_radius)
         if base_radius < 1:
             base_radius = 1 # Ensure visibility

         for i in range(num_points):
             angle = 2 * math.pi * i / num_points
             dist = base_radius * random.uniform(0.7, 1.3)
             x = screen_pos[0] + dist * math.cos(angle)
             y = screen_pos[1] + dist * math.sin(angle)
             points.append((int(x), int(y)))

         if len(points) > 2:
             pygame.draw.polygon(self.screen, GRAY, points)


    def _draw_asteroid_field(self, field):
        # Only draw a subset for performance, especially when zoomed out
        max_asteroids_to_draw = 100
        asteroids_to_draw = field.asteroids[:max_asteroids_to_draw]

        for asteroid in asteroids_to_draw:
            # Assuming asteroid is a dict or object with 'position' and 'radius'
            self._draw_asteroid(asteroid['position'], asteroid['radius'])


    def _draw_rocket(self, rocket):
        screen_pos = self._world_to_screen(rocket.position)
        size = 15 # Rocket size in pixels (could be scaled slightly with zoom?)

        # Simple triangle shape for rocket
        angle_rad = math.radians(rocket.angle) # Assuming angle is in degrees
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

        # Nose
        p1 = (screen_pos[0] + size * cos_a,
              screen_pos[1] + size * sin_a)
        # Base corners
        base_angle_offset = math.pi * 0.8 # Angle for base corners relative to back
        base_dist = size * 0.6
        p2 = (screen_pos[0] - base_dist * math.cos(angle_rad + base_angle_offset),
              screen_pos[1] - base_dist * math.sin(angle_rad + base_angle_offset))
        p3 = (screen_pos[0] - base_dist * math.cos(angle_rad - base_angle_offset),
              screen_pos[1] - base_dist * math.sin(angle_rad - base_angle_offset))

        pygame.draw.polygon(self.screen, WHITE, [p1, p2, p3])

        # Draw thrust flame if thrusting
        if rocket.is_thrusting:
            flame_length = size * 1.5
            flame_width = size * 0.5
            # Flame base center (opposite direction of nose)
            flame_base_x = screen_pos[0] - (size * 0.5) * cos_a
            flame_base_y = screen_pos[1] - (size * 0.5) * sin_a
            # Flame tip
            flame_tip_x = flame_base_x - flame_length * cos_a
            flame_tip_y = flame_base_y - flame_length * sin_a
            # Flame base corners (perpendicular to direction)
            perp_dx = -sin_a * flame_width / 2
            perp_dy = cos_a * flame_width / 2
            flame_p1 = (flame_base_x + perp_dx, flame_base_y + perp_dy)
            flame_p2 = (flame_base_x - perp_dx, flame_base_y - perp_dy)
            flame_p3 = (flame_tip_x, flame_tip_y)

            flame_color = random.choice([ORANGE, YELLOW, RED])
            pygame.draw.polygon(self.screen, flame_color, [flame_p1, flame_p2, flame_p3])


    def _draw_trajectory(self, trajectory_points):
        if len(trajectory_points) > 1:
            screen_points = [self._world_to_screen(p) for p in trajectory_points]
            pygame.draw.lines(self.screen, BLUE, False, screen_points, 1)


    def _draw_ui(self, rocket, time_scale):
        # Rocket Info
        vel_magnitude = np.linalg.norm(rocket.velocity)
        draw_text(self.screen, f"Velocity: {vel_magnitude:.2f} m/s", (10, 10), self.font_small)
        draw_text(self.screen, f"Position: ({rocket.position[0]:.1f}, {rocket.position[1]:.1f})", (10, 30), self.font_small)
        draw_text(self.screen, f"Fuel: {rocket.fuel:.1f}", (10, 50), self.font_small, GREEN if rocket.fuel > 0 else RED)
        draw_text(self.screen, f"Angle: {rocket.angle:.1f} deg", (10, 70), self.font_small)

        # Time Scale
        draw_text(self.screen, f"Time Scale: {time_scale:.1f}x", (self.width - 150, 10), self.font_small)

        # Camera Info
        draw_text(self.screen, f"Zoom: {self.camera.zoom:.4f}", (self.width - 150, 30), self.font_small)
        draw_text(self.screen, f"Cam Center: ({self.camera.center_offset[0]:.1f}, {self.camera.center_offset[1]:.1f})", (self.width - 300, 50), self.font_small)

        # Controls Help Text
        help_texts = [
            "Controls:",
            " W/S: Thrust +/-",
            " A/D: Rotate",
            " LSHIFT: Max Thrust",
            " LCTRL: Cut Thrust",
            " +/-: Time Warp",
            " Scroll: Zoom",
            " MMB Drag: Pan",
            " T: Toggle Trajectory",
            " F: Follow Rocket",
            " I: Toggle Debug Info"
        ]
        for i, text in enumerate(help_texts):
             draw_text(self.screen, text, (10, self.height - 20 * (len(help_texts) - i)), self.font_small, GRAY)


    def _draw_debug_overlay(self, star_system, rocket, model_info=None):
        # Placeholder for data analysis / model performance visualization
        # Displaying basic counts and properties as text for now

        y_offset = 100
        draw_text(self.screen, "-- Debug Info --", (10, y_offset), self.font_medium, YELLOW)
        y_offset += 30

        if star_system:
            draw_text(self.screen, f"Stars: {len(star_system.stars)}", (10, y_offset), self.font_small, YELLOW)
            y_offset += 20
            draw_text(self.screen, f"Planets: {len(star_system.planets)}", (10, y_offset), self.font_small, YELLOW)
            y_offset += 20
            # Example: Show properties of the first planet if it exists
            if star_system.planets:
                p = star_system.planets[0]
                draw_text(self.screen, f" P1 Mass: {p.mass:.2e} kg", (10, y_offset), self.font_small, YELLOW)
                y_offset += 20
                draw_text(self.screen, f" P1 Radius: {p.radius:.0f} m", (10, y_offset), self.font_small, YELLOW)
                y_offset += 20
                draw_text(self.screen, f" P1 Orbit Dist: {np.linalg.norm(p.position):.2e} m", (10, y_offset), self.font_small, YELLOW)
                y_offset += 20
                if hasattr(p, 'atmosphere_density'):
                     draw_text(self.screen, f" P1 Atm Density: {p.atmosphere_density:.2f}", (10, y_offset), self.font_small, YELLOW)
                     y_offset += 20


        if rocket:
             draw_text(self.screen, f"Rocket Vel: ({rocket.velocity[0]:.2f}, {rocket.velocity[1]:.2f})", (10, y_offset), self.font_small, YELLOW)
             y_offset += 20

        # Placeholder for Model Performance Info
        if model_info: # Assuming model_info is a dict passed in
            draw_text(self.screen, "ML Model Info:", (10, y_offset), self.font_small, YELLOW)
            y_offset += 20
            for key, value in model_info.items():
                 draw_text(self.screen, f"  {key}: {value}", (10, y_offset), self.font_small, YELLOW)
                 y_offset += 20


    def handle_input(self, events):
        # Returns True if quit event is detected
        quit_game = False
        pan_delta = np.array([0.0, 0.0])
        mouse_wheel_delta = 0

        # Check for mouse button state for panning
        middle_mouse_pressed = pygame.mouse.get_pressed()[1] # Index 1 is middle button
        mouse_rel = pygame.mouse.get_rel()

        for event in events:
            if event.type == pygame.QUIT:
                quit_game = True
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    quit_game = True
                if event.key == pygame.K_i:
                    self.show_debug_info = not self.show_debug_info
                if event.key == pygame.K_t:
                    self.show_trajectory = not self.show_trajectory
                # Add other keybinds if needed for visualization control (e.g., centering view)

            if event.type == pygame.MOUSEWHEEL:
                mouse_wheel_delta = event.y # Positive for scroll up/zoom in, negative for scroll down/zoom out

        # Handle continuous panning with middle mouse button
        if middle_mouse_pressed:
            # Panning is inverted: moving mouse right moves camera left (world moves right)
            pan_delta = np.array([-mouse_rel[0], -mouse_rel[1]], dtype=float)


        # Apply zoom from mouse wheel
        if mouse_wheel_delta > 0:
            self.camera.zoom_in()
        elif mouse_wheel_delta < 0:
            self.camera.zoom_out()

        # Apply panning
        if np.any(pan_delta): # Check if pan_delta is not zero
             self.camera.pan(pan_delta[0], pan_delta[1])

        return quit_game


    def render(self, star_system, rocket, trajectory_points, time_scale, model_info=None):
        # Update camera (e.g., follow rocket if target is set)
        self.camera.update(self.clock.get_time() / 1000.0) # Pass dt in seconds

        # Drawing
        self._draw_background()

        if star_system:
            for star in star_system.stars:
                self._draw_star(star)
            for planet in star_system.planets:
                self._draw_planet(planet)
            for field in star_system.asteroid_fields:
                 self._draw_asteroid_field(field) # Assuming field has 'asteroids' list

        if rocket:
            if self.show_trajectory and trajectory_points:
                self._draw_trajectory(trajectory_points)
            self._draw_rocket(rocket)

        # UI and Overlays
        if rocket:
            self._draw_ui(rocket, time_scale)

        if self.show_debug_info:
            self._draw_debug_overlay(star_system, rocket, model_info)

        # Update display
        pygame.display.flip()

        # Cap framerate
        self.clock.tick(60) # Limit to 60 FPS

    def shutdown(self):
        pygame.quit()


# Example Usage (requires dummy classes for game objects)
if __name__ == '__main__':

    # --- Dummy Game Object Classes (Replace with actual game objects) ---
    class MockStar:
        def __init__(self, name="Sol", position=(0, 0), radius=696340e3, color=YELLOW, mass=1.989e30):
            self.name = name
            self.position = np.array(position, dtype=float)
            self.radius = radius # meters
            self.color = color
            self.mass = mass

    class MockPlanet:
        def __init__(self, name, position, radius, color, mass, atmosphere_density=0.0):
            self.name = name
            self.position = np.array(position, dtype=float)
            self.radius = radius # meters
            self.color = color
            self.mass = mass
            self.atmosphere_density = atmosphere_density # 0 to 1

    class MockAsteroidField:
         def __init__(self, center_pos, num_asteroids, field_radius):
             self.asteroids = []
             for _ in range(num_asteroids):
                 angle = random.uniform(0, 2 * math.pi)
                 dist = random.uniform(field_radius * 0.8, field_radius * 1.2)
                 pos = center_pos + np.array([dist * math.cos(angle), dist * math.sin(angle)])
                 radius = random.uniform(50e3, 200e3) # 50km to 200km radius
                 self.asteroids.append({'position': pos, 'radius': radius})


    class MockRocket:
        def __init__(self, position=(150e6, 0), velocity=(0, 29780.0), angle=0.0, fuel=100.0):
            self.position = np.array(position, dtype=float) # Start near Earth orbit
            self.velocity = np.array(velocity, dtype=float) # Earth orbital velocity
            self.angle = angle # degrees, 0 = right
            self.fuel = fuel
            self.is_thrusting = False # Controlled by input

    class MockStarSystem:
        def __init__(self):
            self.stars = [MockStar()]
            AU = 149.6e9 # Astronomical Unit in meters
            self.planets = [
                MockPlanet("Mercury", (0.39 * AU, 0), 2440e3, GRAY, 0.33e24),
                MockPlanet("Venus", (0.72 * AU, 0), 6052e3, (210, 190, 150), 4.87e24, 0.9), # Yellowish white
                MockPlanet("Earth", (1.00 * AU, 0), 6371e3, BLUE, 5.97e24, 0.5),
                MockPlanet("Mars", (1.52 * AU, 0), 3390e3, RED, 0.64e24, 0.1),
            ]
            self.asteroid_fields = [
                 MockAsteroidField(np.array([2.8 * AU, 0]), 50, 0.5 * AU)
            ]
    # --- End Dummy Classes ---

    # --- Simulation Setup ---
    viz = Visualization()
    system = MockStarSystem()
    # Place rocket near Earth initially
    earth_pos = system.planets[2].position
    rocket_start_pos = earth_pos + np.array([system.planets[2].radius * 10, 0]) # Start 10 radii away
    rocket_start_vel = np.array([0, 35000.0]) # Some orbital velocity around Earth (adjust!)
    rocket = MockRocket(position=rocket_start_pos, velocity=rocket_start_vel, angle=-90.0) # Pointing "up"

    viz.camera.set_target(rocket) # Make camera follow the rocket
    viz.camera.zoom = 0.0000001 # Zoom out significantly initially to see planets

    trajectory = []
    max_trajectory_points = 500
    time_scale = 1.0 # Real time initially
    running = True
    paused = False
    pan_speed_multiplier = 1.0 # Adjusts how fast panning keys move the view

    # --- Main Loop ---
    while running:
        # --- Event Handling ---
        events = pygame.event.get()
        if viz.handle_input(events): # Handles quit, zoom, pan, debug toggle
            running = False

        keys = pygame.key.get_pressed()

        # Rocket Controls (Simplified for example)
        rocket.is_thrusting = False
        thrust_force = 100000.0 # Newtons (example value)
        rotation_speed = 90.0 # degrees per second
        dt = viz.clock.get_time() / 1000.0 * time_scale # Scaled delta time

        if not paused:
            if keys[pygame.K_w] or keys[pygame.K_LSHIFT]:
                rocket.is_thrusting = True
                # Simplified physics: Apply thrust directly to velocity
                thrust_direction = np.array([math.cos(math.radians(rocket.angle)), math.sin(math.radians(rocket.angle))])
                # Assuming constant mass for simplicity
                acceleration = thrust_direction * thrust_force / 1000.0 # F=ma, assume mass=1000kg
                rocket.velocity += acceleration * dt
                rocket.fuel -= 0.1 * dt # Consume fuel
                if rocket.fuel < 0: rocket.fuel = 0