```python
import pygame
import numpy as np
import random
import argparse
import sys
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures

# Configuration Constants
CONFIG = {
    "screen_width": 1280,
    "screen_height": 720,
    "fps": 60,
    "gravity_constant": 6.674e-5, # Adjusted for simulation scale
    "time_step": 0.1,
    "camera_speed": 5,
    "zoom_speed": 1.1,
    "min_zoom": 0.1,
    "max_zoom": 5.0,
    "star_mass_min": 5e6,
    "star_mass_max": 5e7,
    "planet_count_min": 3,
    "planet_count_max": 8,
    "min_orbit_radius": 1500,
    "max_orbit_radius_factor": 100, # Relative to min_orbit_radius
    "planet_mass_factor": 0.01, # Relative to star mass
    "planet_radius_min": 5,
    "planet_radius_max": 50,
    "asteroid_field_count": 1,
    "asteroids_per_field": 100,
    "asteroid_mass_min": 1e1,
    "asteroid_mass_max": 1e2,
    "asteroid_radius_min": 1,
    "asteroid_radius_max": 4,
    "rocket_mass": 100,
    "rocket_thrust": 500,
    "rocket_rotation_speed": 3,
    "rocket_initial_fuel": 1000,
    "fuel_consumption_rate": 0.5,
    "background_color": (0, 0, 10),
    "star_color": (255, 255, 0),
    "asteroid_color": (100, 100, 100),
    "rocket_color": (200, 200, 255),
    "trajectory_color": (0, 100, 255),
    "trajectory_length": 200,
    "ui_font_size": 18,
    "ui_color": (255, 255, 255),
}

# --- Simple ML Model for Planet Properties ---
# Generate some synthetic data based on orbital distance
# Features: orbital_distance
# Targets: mass_factor, radius, density_factor (influences color/atmosphere)
np.random.seed(42) # for reproducibility
_distances = np.linspace(CONFIG["min_orbit_radius"], CONFIG["min_orbit_radius"] * 50, 100).reshape(-1, 1)
# Simple relationships + noise
_mass_factors = (0.001 + 0.05 * (_distances / _distances.max())**0.5 + np.random.normal(0, 0.005, _distances.shape)).clip(0.0001, 0.1)
_radii = (CONFIG["planet_radius_min"] + (CONFIG["planet_radius_max"] - CONFIG["planet_radius_min"]) * (_distances / _distances.max())**0.3 + np.random.normal(0, 3, _distances.shape)).clip(CONFIG["planet_radius_min"], CONFIG["planet_radius_max"])
_density_factors = (0.1 + 0.9 * np.exp(-_distances / (CONFIG["min_orbit_radius"] * 20)) + np.random.normal(0, 0.1, _distances.shape)).clip(0.05, 1.0)

# Train simple models
poly = PolynomialFeatures(degree=2, include_bias=False)
_distances_poly = poly.fit_transform(_distances)

mass_model = LinearRegression().fit(_distances_poly, _mass_factors)
radius_model = LinearRegression().fit(_distances_poly, _radii)
density_model = LinearRegression().fit(_distances_poly, _density_factors)

def generate_planet_properties(orbital_distance, star_mass):
    """Generates planet properties using simple trained models."""
    dist_poly = poly.transform(np.array([[orbital_distance]]))

    mass_factor = mass_model.predict(dist_poly)[0][0]
    mass = star_mass * np.clip(mass_factor + np.random.normal(0, 0.002), 0.0001, 0.1)

    radius = radius_model.predict(dist_poly)[0][0]
    radius = np.clip(radius + np.random.normal(0, 2), CONFIG["planet_radius_min"], CONFIG["planet_radius_max"])

    density_factor = density_model.predict(dist_poly)[0][0]
    density_factor = np.clip(density_factor + np.random.normal(0, 0.05), 0.05, 1.0)

    # Determine color based on density/distance (e.g., denser/closer = reddish/brown, less dense/farther = bluish/grey)
    r = int(150 * (1 - density_factor) + 50 * (1 - min(1, orbital_distance / (CONFIG["min_orbit_radius"] * 30))))
    g = int(100 * density_factor + 50 * (1 - min(1, orbital_distance / (CONFIG["min_orbit_radius"] * 30))))
    b = int(200 * density_factor + 50 * min(1, orbital_distance / (CONFIG["min_orbit_radius"] * 50)))
    color = tuple(np.clip([r, g, b], 0, 255))

    return mass, radius, color, density_factor

# --- Core Classes ---

class CelestialBody:
    def __init__(self, position, velocity, mass, radius, color, name="Body"):
        self.position = np.array(position, dtype=float)
        self.velocity = np.array(velocity, dtype=float)
        self.mass = float(mass)
        self.radius = float(radius)
        self.color = color
        self.name = name
        self.acceleration = np.zeros(2, dtype=float)

    def apply_force(self, force):
        if self.mass > 0:
            self.acceleration += force / self.mass

    def update_position(self, dt):
        self.velocity += self.acceleration * dt
        self.position += self.velocity * dt
        self.acceleration = np.zeros(2, dtype=float) # Reset acceleration

    def draw(self, surface, camera):
        screen_pos = camera.world_to_screen(self.position)
        screen_radius = int(self.radius * camera.zoom)

        # Culling: Only draw if visible on screen (with some margin)
        if screen_radius < 1 and self.radius > 0.1: # Draw tiny bodies as single pixels if zoom is low
             if -10 < screen_pos[0] < camera.screen_width + 10 and -10 < screen_pos[1] < camera.screen_height + 10:
                 pygame.draw.circle(surface, self.color, screen_pos.astype(int), 1)
        elif screen_radius >= 1:
            if -screen_radius < screen_pos[0] < camera.screen_width + screen_radius and \
               -screen_radius < screen_pos[1] < camera.screen_height + screen_radius:
                pygame.draw.circle(surface, self.color, screen_pos.astype(int), screen_radius)

    def distance_to(self, other_body):
        return np.linalg.norm(self.position - other_body.position)

    def gravitational_force_from(self, other_body, G):
        vector = other_body.position - self.position
        distance_sq = np.dot(vector, vector)
        if distance_sq == 0: # Avoid division by zero
            return np.zeros(2)
        distance = np.sqrt(distance_sq)
        force_magnitude = G * self.mass * other_body.mass / distance_sq
        force_vector = force_magnitude * (vector / distance)
        return force_vector

class Star(CelestialBody):
    def __init__(self, position, mass, radius, color=CONFIG["star_color"], name="Star"):
        super().__init__(position, [0, 0], mass, radius, color, name)

class Planet(CelestialBody):
    def __init__(self, position, velocity, mass, radius, color, density, name="Planet"):
        super().__init__(position, velocity, mass, radius, color, name)
        self.atmospheric_density = density # Simple factor

class Asteroid(CelestialBody):
    def __init__(self, position, velocity, mass, radius, color=CONFIG["asteroid_color"], name="Asteroid"):
        super().__init__(position, velocity, mass, radius, color, name)

class Rocket(CelestialBody):
    def __init__(self, position, velocity, mass=CONFIG["rocket_mass"], radius=5, color=CONFIG["rocket_color"], name="Rocket"):
        super().__init__(position, velocity, mass, radius, color, name)
        self.orientation = 0.0 # Angle in degrees, 0 = right
        self.thrust_force = CONFIG["rocket_thrust"]
        self.rotation_speed = CONFIG["rocket_rotation_speed"]
        self.thrusting = False
        self.fuel = CONFIG["rocket_initial_fuel"]
        self.trajectory = []

    def rotate(self, direction): # direction: 1 for counter-clockwise, -1 for clockwise
        self.orientation = (self.orientation + direction * self.rotation_speed) % 360

    def apply_thrust(self, dt):
        if self.thrusting and self.fuel > 0:
            rad_angle = np.radians(self.orientation)
            force_direction = np.array([np.cos(rad_angle), np.sin(rad_angle)])
            force = force_direction * self.thrust_force
            self.apply_force(force)
            self.fuel -= CONFIG["fuel_consumption_rate"] * dt
            if self.fuel < 0:
                self.fuel = 0
            return True # Indicates thrust was applied
        return False

    def update_position(self, dt):
        super().update_position(dt)
        # Record trajectory
        self.trajectory.append(tuple(self.position))
        if len(self.trajectory) > CONFIG["trajectory_length"]:
            self.trajectory.pop(0)

    def draw(self, surface, camera):
        screen_pos = camera.world_to_screen(self.position)
        zoom = camera.zoom

        # Draw trajectory first
        if len(self.trajectory) > 1:
            screen_points = [tuple(camera.world_to_screen(p).astype(int)) for p in self.trajectory]
            valid_points = []
            for p in screen_points:
                 if -100 < p[0] < camera.screen_width + 100 and -100 < p[1] < camera.screen_height + 100:
                     valid_points.append(p)
            if len(valid_points) > 1:
                 pygame.draw.lines(surface, CONFIG["trajectory_color"], False, valid_points, 1)


        # Draw rocket body (triangle)
        rad_angle = np.radians(self.orientation)
        size = self.radius * zoom * 2 # Make rocket visually larger
        points = [
            (size, 0),
            (-size / 2, -size / 2),
            (-size / 2, size / 2)
        ]
        rotated_points = []
        for x, y in points:
            new_x = x * np.cos(rad_angle) - y * np.sin(rad_angle)
            new_y = x * np.sin(rad_angle) + y * np.cos(rad_angle)
            rotated_points.append(screen_pos + np.array([new_x, new_y]))

        pygame.draw.polygon(surface, self.color, [p.astype(int) for p in rotated_points])

        # Draw thrust flame if thrusting
        if self.thrusting and self.fuel > 0:
            flame_length = size * 1.5
            flame_width = size * 0.6
            flame_points = [
                (-size / 2, -flame_width / 2),
                (-size / 2 - flame_length * (0.5 + random.random() * 0.5) , 0), # Flicker effect
                (-size / 2, flame_width / 2)
            ]
            rotated_flame_points = []
            for x, y in flame_points:
                new_x = x * np.cos(rad_angle) - y * np.sin(rad_angle)
                new_y = x * np.sin(rad_angle) + y * np.cos(rad_angle)
                rotated_flame_points.append(screen_pos + np.array([new_x, new_y]))
            pygame.draw.polygon(surface, (255, 150, 0), [p.astype(int) for p in rotated_flame_points])


class Camera:
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.offset = np.array([0.0, 0.0]) # World position of the top-left corner
        self.zoom = 1.0
        self.target = None # Optional target to follow (e.g., the rocket)

    def set_target(self, target_body):
        self.target = target_body

    def update(self, dt):
        if self.target:
            # Center the view on the target
            target_screen_center = np.array([self.screen_width / 2, self.screen_height / 2])
            self.offset = self.target.position - target_screen_center / self.zoom
        # Add panning logic if needed (e.g., with arrow keys when no target)

    def world_to_screen(self, world_pos):
        return (np.array(world_pos) - self.offset) * self.zoom

    def screen_to_world(self, screen_pos):
        return np.array(screen_pos) / self.zoom + self.offset

    def zoom_in(self):
        old_mouse_world = self.screen_to_world(pygame.mouse.get_pos())
        self.zoom *= CONFIG["zoom_speed"]
        self.zoom = min(self.zoom, CONFIG["max_zoom"])
        new_mouse_world = self.screen_to_world(pygame.mouse.get_pos())
        self.offset += old_mouse_world - new_mouse_world


    def zoom_out(self):
        old_mouse_world = self.screen_to_world(pygame.mouse.get_pos())
        self.zoom /= CONFIG["zoom_speed"]
        self.zoom = max(self.zoom, CONFIG["min_zoom"])
        new_mouse_world = self.screen_to_world(pygame.mouse.get_pos())
        self.offset += old_mouse_world - new_mouse_world

    def move(self, dx, dy):
         # Prevent moving if following a target
        if self.target is None:
            self.offset += np.array([dx, dy]) / self.zoom


class SystemGenerator:
    def __init__(self, seed=None):
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
        self.bodies = []

    def generate_system(self):
        self.bodies = []
        center = np.array([0.0, 0.0])

        # Generate Star
        star_mass = random.uniform(CONFIG["star_mass_min"], CONFIG["star_mass_max"])
        star_radius = np.cbrt(star_mass) * 0.05 # Radius roughly scales with cbrt(mass)
        star = Star(center, star_mass, star_radius)
        self.bodies.append(star)

        # Generate Planets
        num_planets = random.randint(CONFIG["planet_count_min"], CONFIG["planet_count_max"])
        last_orbit_radius = 0
        for i in range(num_planets):
            orbit_radius = random.uniform(
                max(CONFIG["min_orbit_radius"], last_orbit_radius * 1.5),
                max(CONFIG["min_orbit_radius"] * 1.5, last_orbit_radius * 2.0) + CONFIG["min_orbit_radius"] * (i + 1) * 2
            )
            last_orbit_radius = orbit_radius

            angle = random.uniform(0, 2 * np.pi)
            position = center + np.array([np.cos(angle), np.sin(angle)]) * orbit_radius

            # Calculate stable-ish orbital velocity (tangential)
            try:
                orbit_speed = np.sqrt(CONFIG["gravity_constant"] * star_mass / orbit_radius)
            except ValueError:
                 orbit_speed = 0 # Avoid sqrt of negative if something weird happens
            velocity_direction = np.array([-np.sin(angle), np.cos(angle)]) # Perpendicular to position vector
            velocity = velocity_direction * orbit_speed * random.uniform(0.95, 1.05) # Add slight variation

            mass, radius, color, density = generate_planet_properties(orbit_radius, star_mass)

            planet = Planet(position, velocity, mass, radius, color, density, name=f"Planet-{i+1}")
            self.bodies.append(planet)

        # Generate Asteroid Fields
        for _ in range(CONFIG["asteroid_field_count"]):
            field_orbit_radius = random.uniform(CONFIG["min_orbit_radius"] * 1.2, last_orbit_radius * 1.2)
            field_width = field_orbit_radius * random.uniform(0.1, 0.3)

            for i in range(CONFIG["asteroids_per_field"]):
                a_orbit_radius = random.uniform(field_orbit_radius - field_width / 2, field_orbit_radius + field_width / 2)
                if a_orbit_radius <= 0: continue # Ensure positive radius

                a_angle = random.uniform(0, 2 * np.pi)
                a_position = center + np.array([np.cos(a_angle), np.sin(a_angle)]) * a_orbit_radius

                try:
                    a_orbit_speed = np.sqrt(CONFIG["gravity_constant"] * star_mass / a_orbit_radius)
                except ValueError:
                    a_orbit_speed = 0
                a_velocity_direction = np.array([-np.sin(a_angle), np.cos(a_angle)])
                a_velocity = a_velocity_direction * a_orbit_speed * random.uniform(0.8, 1.2) # More variation for asteroids

                a_mass = random.uniform(CONFIG["asteroid_mass_min"], CONFIG["asteroid_mass_max"])
                a_radius = random.uniform(CONFIG["asteroid_radius_min"], CONFIG["asteroid_radius_max"])

                asteroid = Asteroid(a_position, a_velocity, a_mass, a_radius, name=f"Asteroid-{i+1}")
                self.bodies.append(asteroid)

        return self.bodies


class PhysicsEngine:
    def __init__(self, bodies, G):
        self.bodies = bodies
        self.G = G

    def update(self, dt):
        # Calculate forces (Simplified: only star and massive planets affect others significantly)
        star = self.bodies[0] # Assuming star is always the first body
        massive_bodies = [b for b in self.bodies if b.mass > CONFIG["star_mass_min"] * 0.001 or isinstance(b, Star)]
        rocket = next((b for b in self.bodies if isinstance(b, Rocket)), None)

        for i, body1 in enumerate(self.bodies):
            if isinstance(body1, Star): continue # Assume star doesn't move

            # Force from Star
            force = body1.gravitational_force_from(star, self.G)
            body1.apply_force(force)

            # For rocket, consider forces from nearby massive planets
            if body1 == rocket:
                for body2 in massive_bodies:
                    if body1 == body2 or body2 == star: continue # Skip self and star (already calculated)
                    dist = body1.distance_to(body2)
                    # Only consider planets within a certain range to save computation
                    if dist < CONFIG["min_orbit_radius"] * 5: # Arbitrary range
                         force = body1.gravitational_force_from(body2, self.G)
                         body1.apply_force(force)
            # For planets, only consider star's gravity (as per simplified requirement)
            # (Could add planet-planet interaction here if needed)


        # Update positions
        for body in self.bodies:
            if isinstance(body, Rocket):
                body.apply_thrust(dt) # Apply thrust force before updating position
            if not isinstance(body, Star): # Keep star stationary
                body.update_position(dt)


class Game:
    def __init__(self, screen_width, screen_height, seed=None):
        pygame.init()
        pygame.font.init()
        try:
            self.screen = pygame.display.set_mode((screen_width, screen_height))
            pygame.display.set_caption("Stellar Forge Simulator")
            self.clock = pygame.time.Clock()
            self.font = pygame.font.SysFont(None, CONFIG["ui_font_size"])
        except pygame.error as e:
            print(f"Error initializing Pygame: {e}", file=sys.stderr)
            sys.exit(1)

        self.running = True
        self.camera = Camera(screen_width, screen_height)
        self.seed = seed

        print("Generating system...")
        generator = SystemGenerator(self.seed)
        self.bodies = generator.generate_system()

        # Add Rocket
        star = self.bodies[0]
        rocket_start_pos = star.position + np.array([star.radius + 1000, 0]) # Start near the star
        rocket_start_vel = np.array([0.0, np.sqrt(CONFIG["gravity_constant"] * star.mass / (star.radius + 1000)) * 0.8]) # Initial orbital vel
        self.rocket = Rocket(rocket_start_pos, rocket_start_vel)
        self.bodies.append(self.rocket)
        self.camera.set_target(self.rocket) # Make camera follow rocket

        self.physics_engine = PhysicsEngine(self.bodies, CONFIG["gravity_constant"])
        print("System generated. Starting simulation.")


    def run(self):
        while self.running:
            dt = self.clock.tick(CONFIG["fps"]) / 1000.0 * CONFIG["time_step"] # Scaled delta time
            if dt == 0: continue # Avoid issues if frame rate is too high or game paused

            self.handle_input()
            self.update(dt)
            self.render()

        pygame.quit()

    def handle_input(self):
        keys = pygame.key.get_pressed()

        # Rocket controls
        self.rocket.thrusting = keys[pygame.K_UP] or keys[pygame.K_w]
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.rocket.rotate(1) # Counter-clockwise
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.rocket.rotate(-1) # Clockwise

        # Camera controls (Manual pan disabled when following target)
        if self.camera.target is None:
            cam_speed = CONFIG["camera_speed"] / self.camera.zoom
            if keys[pygame.K_LEFT]:
                self.camera.move(-cam_speed, 0)
            if keys[pygame.K_RIGHT]:
                self.camera.move(cam_speed, 0)
            if keys[pygame.K_UP]:
                self.camera.move(0, -cam_speed)
            if keys[pygame.K_DOWN]:
                self.camera.move(0, cam_speed)

        # Toggle camera follow
        if keys[pygame.K_f]:
             if self.camera.target == self.rocket:
                 self.camera.set_target(None)
             else:
                 self.camera.set_target(self.rocket)


        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                 if event.key == pygame.K_ESCAPE:
                     self.running = False
                 elif event.key == pygame.K_PAGEUP: # Zoom in
                     self.camera.zoom_in()
                 elif event.key == pygame.K_PAGEDOWN: # Zoom out
                     self.camera.zoom_out()
            elif event.type == pygame.MOUSEWHEEL:
                 if event.y > 0: # Scroll up
                     self.camera.zoom_in()
                 elif event.y < 0: # Scroll down
                     self.camera.zoom_out()


    def update(self, dt):
        self.physics_engine.update(dt)
        self.camera.update(dt)

    def render(self):
        self.screen.fill(CONFIG["background_color"])

        # Draw all celestial bodies
        for body in self.bodies:
            body.draw(self.screen, self.camera)

        # Draw UI Text
        self.draw_ui()

        pygame.display.flip()

    def draw_ui(self):
        # Rocket Info
        rocket_vel = np.linalg.norm(self.rocket.velocity)
        rocket_alt = self.rocket.distance_to(self.bodies[0]) - self.bodies[0].radius - self.rocket.radius # Altitude above star surface
        fuel_text = f"Fuel: {self.rocket.fuel:.1f}"
        vel_text = f"Velocity: {rocket_vel:.2f} units/s"
        alt_text = f"Altitude (Star): {rocket_alt:.2f} units"
        zoom_text = f"Zoom: {self.camera.zoom:.2f}x"
        follow_text = f"Camera Follow: {'ON'