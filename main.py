import pygame
import numpy as np
import random
import sys
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures

# Configuration Constants
CONFIG = {
    "screen_width": 1280,
    "screen_height": 720,
    "fps": 60,
    "gravity_constant": 6.674e-5,
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
    "max_orbit_radius_factor": 100,
    "planet_mass_factor": 0.01,
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
    "enemy_count_min": 3,
    "enemy_count_max": 8,
    "enemy_spawn_distance_min": 3000,
    "enemy_spawn_distance_max": 15000,
    "enemy_speed": 150,
    "enemy_health": 3,
    "enemy_color": (255, 50, 50),
    "bullet_speed": 600,
    "bullet_lifetime": 2.0,
    "bullet_color": (255, 255, 100),
    "rocket_fire_rate": 0.3,
    "map_size": 300,
    "map_position": (980, 20),
    "mission_types": ["collect", "destroy", "explore", "deliver"],
    "mission_reward_min": 100,
    "mission_reward_max": 500,
    "mission_time_min": 60,
    "mission_time_max": 180,
    "collectible_color": (0, 255, 100),
    "collectible_radius": 8
}

# --- Simple ML Model for Planet Properties ---
np.random.seed(42)
_distances = np.linspace(CONFIG["min_orbit_radius"], CONFIG["min_orbit_radius"] * 50, 100).reshape(-1, 1)
_mass_factors = (0.001 + 0.05 * (_distances / _distances.max())**0.5 + np.random.normal(0, 0.005, _distances.shape)).clip(0.0001, 0.1)
_radii = (CONFIG["planet_radius_min"] + (CONFIG["planet_radius_max"] - CONFIG["planet_radius_min"]) * (_distances / _distances.max())**0.3 + np.random.normal(0, 3, _distances.shape)).clip(CONFIG["planet_radius_min"], CONFIG["planet_radius_max"])
_density_factors = (0.1 + 0.9 * np.exp(-_distances / (CONFIG["min_orbit_radius"] * 20)) + np.random.normal(0, 0.1, _distances.shape)).clip(0.05, 1.0)

poly = PolynomialFeatures(degree=2, include_bias=False)
_distances_poly = poly.fit_transform(_distances)

mass_model = LinearRegression().fit(_distances_poly, _mass_factors)
radius_model = LinearRegression().fit(_distances_poly, _radii)
density_model = LinearRegression().fit(_distances_poly, _density_factors)

def generate_planet_properties(orbital_distance, star_mass):
    dist_poly = poly.transform(np.array([[orbital_distance]]))
    
    mass_factor = mass_model.predict(dist_poly)[0][0]
    mass = star_mass * np.clip(mass_factor + np.random.normal(0, 0.002), 0.0001, 0.1)
    
    radius = radius_model.predict(dist_poly)[0][0]
    radius = np.clip(radius + np.random.normal(0, 2), CONFIG["planet_radius_min"], CONFIG["planet_radius_max"])
    
    density_factor = density_model.predict(dist_poly)[0][0]
    density_factor = np.clip(density_factor + np.random.normal(0, 0.05), 0.05, 1.0)
    
    r = int(150 * (1 - density_factor) + 50 * (1 - min(1, orbital_distance / (CONFIG["min_orbit_radius"] * 30))))
    g = int(100 * density_factor + 50 * (1 - min(1, orbital_distance / (CONFIG["min_orbit_radius"] * 30))))
    b = int(200 * density_factor + 50 * min(1, orbital_distance / (CONFIG["min_orbit_radius"] * 50)))
    color = tuple(np.clip([r, g, b], 0, 255))
    
    return mass, radius, color, density_factor

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
        self.acceleration = np.zeros(2, dtype=float)
    
    def draw(self, surface, camera):
        screen_pos = camera.world_to_screen(self.position)
        screen_radius = int(self.radius * camera.zoom)
        
        if screen_radius < 1 and self.radius > 0.1:
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
        if distance_sq == 0:
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
        self.atmospheric_density = density
        self.discovered = False

class Asteroid(CelestialBody):
    def __init__(self, position, velocity, mass, radius, color=CONFIG["asteroid_color"], name="Asteroid"):
        super().__init__(position, velocity, mass, radius, color, name)

class Bullet:
    def __init__(self, position, velocity, color=CONFIG["bullet_color"]):
        self.position = np.array(position, dtype=float)
        self.velocity = np.array(velocity, dtype=float)
        self.radius = 2
        self.color = color
        self.lifetime = CONFIG["bullet_lifetime"]
    
    def update(self, dt):
        self.position += self.velocity * dt
        self.lifetime -= dt
        return self.lifetime > 0
    
    def draw(self, surface, camera):
        screen_pos = camera.world_to_screen(self.position)
        if 0 <= screen_pos[0] < camera.screen_width and 0 <= screen_pos[1] < camera.screen_height:
            pygame.draw.circle(surface, self.color, screen_pos.astype(int), int(self.radius * camera.zoom))
    
    def collision_check(self, obj):
        dist = np.linalg.norm(self.position - obj.position)
        return dist < (self.radius + obj.radius)

class Enemy:
    def __init__(self, position, target, color=CONFIG["enemy_color"]):
        self.position = np.array(position, dtype=float)
        self.velocity = np.zeros(2, dtype=float)
        self.target = target
        self.radius = 12
        self.color = color
        self.health = CONFIG["enemy_health"]
        self.speed = CONFIG["enemy_speed"]
        self.fire_cooldown = 0
        self.fire_rate = 1.5
    
    def update(self, dt):
        if self.target:
            direction = self.target.position - self.position
            distance = np.linalg.norm(direction)
            if distance > 0:
                direction = direction / distance
                desired_vel = direction * self.speed
                self.velocity = desired_vel
            
            if 300 < distance < 800:
                self.velocity *= 0.5  # Slow down to attack
            elif distance <= 300:
                self.velocity *= 0.2  # Almost stop when close
        
        self.position += self.velocity * dt
        
        if self.fire_cooldown > 0:
            self.fire_cooldown -= dt
        
        return self.health > 0
    
    def take_damage(self):
        self.health -= 1
        return self.health <= 0
    
    def can_fire(self):
        return self.fire_cooldown <= 0
    
    def fire(self, target_pos):
        self.fire_cooldown = self.fire_rate
        direction = target_pos - self.position
        distance = np.linalg.norm(direction)
        if distance > 0:
            direction = direction / distance
            bullet_velocity = direction * CONFIG["bullet_speed"]
            return Bullet(self.position.copy(), bullet_velocity, (255, 50, 50))
        return None
    
    def draw(self, surface, camera):
        screen_pos = camera.world_to_screen(self.position)
        screen_radius = int(self.radius * camera.zoom)
        
        if -screen_radius < screen_pos[0] < camera.screen_width + screen_radius and \
           -screen_radius < screen_pos[1] < camera.screen_height + screen_radius:
            pygame.draw.circle(surface, self.color, screen_pos.astype(int), screen_radius)
            
            # Draw health indicators
            health_radius = screen_radius + 2
            angle_step = 2 * np.pi / CONFIG["enemy_health"]
            for i in range(self.health):
                angle = i * angle_step
                health_pos = screen_pos + np.array([np.cos(angle), np.sin(angle)]) * health_radius
                pygame.draw.circle(surface, (0, 255, 0), health_pos.astype(int), max(2, int(3 * camera.zoom)))

class Collectible:
    def __init__(self, position, color=CONFIG["collectible_color"]):
        self.position = np.array(position, dtype=float)
        self.radius = CONFIG["collectible_radius"]
        self.color = color
        self.collected = False
        self.pulse_time = 0
    
    def update(self, dt):
        self.pulse_time = (self.pulse_time + dt) % 2.0
        return not self.collected
    
    def draw(self, surface, camera):
        if self.collected:
            return
            
        screen_pos = camera.world_to_screen(self.position)
        pulse_factor = 0.8 + 0.4 * np.sin(self.pulse_time * np.pi)
        screen_radius = int(self.radius * camera.zoom * pulse_factor)
        
        if -screen_radius < screen_pos[0] < camera.screen_width + screen_radius and \
           -screen_radius < screen_pos[1] < camera.screen_height + screen_radius:
            pygame.draw.circle(surface, self.color, screen_pos.astype(int), screen_radius)
            pygame.draw.circle(surface, (255, 255, 255), screen_pos.astype(int), screen_radius, 1)
    
    def check_collection(self, rocket):
        if not self.collected:
            dist = np.linalg.norm(self.position - rocket.position)
            if dist < (self.radius + rocket.radius):
                self.collected = True
                return True
        return False

class Mission:
    def __init__(self, mission_type, star_system):
        self.mission_type = mission_type
        self.completed = False
        self.active = True
        self.reward = random.randint(CONFIG["mission_reward_min"], CONFIG["mission_reward_max"])
        self.time_limit = random.randint(CONFIG["mission_time_min"], CONFIG["mission_time_max"])
        self.time_remaining = self.time_limit
        self.target_objects = []
        self.star_system = star_system
        self.target_count = 0
        self.completed_count = 0
        self.init_mission(mission_type)
    
    def init_mission(self, mission_type):
        if mission_type == "collect":
            self.target_count = random.randint(3, 6)
            for _ in range(self.target_count):
                position = self.generate_safe_position()
                self.target_objects.append(Collectible(position))
            self.description = f"Collect {self.target_count} resource packages"
            
        elif mission_type == "destroy":
            self.target_count = random.randint(2, 5)
            for _ in range(self.target_count):
                position = self.generate_safe_position(min_dist=4000, max_dist=10000)
                enemy = Enemy(position, self.star_system.rocket)
                enemy.mission_target = True
                self.star_system.enemies.append(enemy)
            self.description = f"Destroy {self.target_count} enemy ships"
            
        elif mission_type == "explore":
            planets = [body for body in self.star_system.bodies if isinstance(body, Planet)]
            self.target_count = min(random.randint(2, 4), len(planets))
            self.target_objects = random.sample(planets, self.target_count)
            self.description = f"Explore {self.target_count} undiscovered planets"
            
        elif mission_type == "deliver":
            position = self.generate_safe_position(min_dist=6000, max_dist=12000)
            self.target_objects.append(position)
            self.description = f"Deliver supplies to a remote station"
            self.target_count = 1
    
    def generate_safe_position(self, min_dist=3000, max_dist=8000):
        star = self.star_system.bodies[0]
        while True:
            angle = random.uniform(0, 2 * np.pi)
            distance = random.uniform(min_dist, max_dist)
            position = star.position + np.array([np.cos(angle), np.sin(angle)]) * distance
            
            # Check if position is safe (not too close to any planets)
            safe = True
            for body in self.star_system.bodies:
                if isinstance(body, Planet) and np.linalg.norm(position - body.position) < body.radius * 5:
                    safe = False
                    break
            
            if safe:
                return position
    
    def update(self, dt, rocket):
        if not self.active or self.completed:
            return
        
        self.time_remaining -= dt
        if self.time_remaining <= 0:
            self.active = False
            return
        
        if self.mission_type == "collect":
            for obj in self.target_objects:
                if not obj.collected and obj.check_collection(rocket):
                    self.completed_count += 1
            
            if self.completed_count >= self.target_count:
                self.completed = True
                
        elif self.mission_type == "destroy":
            mission_enemies = [e for e in self.star_system.enemies if getattr(e, "mission_target", False)]
            self.completed_count = self.target_count - len(mission_enemies)
            if self.completed_count >= self.target_count:
                self.completed = True
                
        elif self.mission_type == "explore":
            for planet in self.target_objects:
                if not planet.discovered and rocket.distance_to(planet) < planet.radius * 3:
                    planet.discovered = True
                    self.completed_count += 1
                    
            if self.completed_count >= self.target_count:
                self.completed = True
                
        elif self.mission_type == "deliver":
            target_pos = self.target_objects[0]
            if np.linalg.norm(rocket.position - target_pos) < rocket.radius * 2:
                self.completed = True
                self.completed_count = 1
    
    def draw(self, surface, camera):
        if not self.active:
            return
            
        if self.mission_type == "collect":
            for obj in self.target_objects:
                if not obj.collected:
                    obj.draw(surface, camera)
                    
        elif self.mission_type == "deliver":
            target_pos = self.target_objects[0]
            screen_pos = camera.world_to_screen(target_pos)
            screen_radius = int(20 * camera.zoom)
            
            if -screen_radius < screen_pos[0] < camera.screen_width + screen_radius and \
               -screen_radius < screen_pos[1] < camera.screen_height + screen_radius:
                pygame.draw.circle(surface, (100, 100, 255), screen_pos.astype(int), screen_radius)
                pygame.draw.circle(surface, (200, 200, 255), screen_pos.astype(int), screen_radius, 2)
                
                # Draw pulsing indicator
                pulse = (np.sin(pygame.time.get_ticks() / 200) + 1) / 2
                outer_radius = int(screen_radius * (1.2 + 0.3 * pulse))
                pygame.draw.circle(surface, (150, 150, 255, 100), screen_pos.astype(int), outer_radius, 1)
        
        elif self.mission_type == "explore":
            for planet in self.target_objects:
                if not planet.discovered:
                    screen_pos = camera.world_to_screen(planet.position)
                    screen_radius = int(planet.radius * camera.zoom * 1.5)
                    
                    if -screen_radius < screen_pos[0] < camera.screen_width + screen_radius and \
                       -screen_radius < screen_pos[1] < camera.screen_height + screen_radius:
                        pulse = (np.sin(pygame.time.get_ticks() / 300) + 1) / 2
                        pygame.draw.circle(surface, (0, 255, 255, 100), screen_pos.astype(int), 
                                         int(screen_radius * (1 + 0.2 * pulse)), 1)

class Rocket(CelestialBody):
    def __init__(self, position, velocity, mass=CONFIG["rocket_mass"], radius=5, color=CONFIG["rocket_color"], name="Rocket"):
        super().__init__(position, velocity, mass, radius, color, name)
        self.orientation = 0.0
        self.thrust_force = CONFIG["rocket_thrust"]
        self.rotation_speed = CONFIG["rocket_rotation_speed"]
        self.thrusting = False
        self.fuel = CONFIG["rocket_initial_fuel"]
        self.trajectory = []
        self.fire_cooldown = 0
        self.fire_rate = CONFIG["rocket_fire_rate"]
        self.credits = 200
        self.shields = 100
        self.max_shields = 100
        self.shield_recharge_rate = 2
        self.shield_recharge_cooldown = 0
    
    def rotate(self, direction):
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
            return True
        return False
    
    def update_position(self, dt):
        super().update_position(dt)
        self.trajectory.append(tuple(self.position))
        if len(self.trajectory) > CONFIG["trajectory_length"]:
            self.trajectory.pop(0)
            
        if self.fire_cooldown > 0:
            self.fire_cooldown -= dt
            
        if self.shield_recharge_cooldown > 0:
            self.shield_recharge_cooldown -= dt
        else:
            self.shields = min(self.max_shields, self.shields + self.shield_recharge_rate * dt)
    
    def can_fire(self):
        return self.fire_cooldown <= 0
    
    def fire(self):
        if not self.can_fire():
            return None
            
        self.fire_cooldown = self.fire_rate
        rad_angle = np.radians(self.orientation)
        direction = np.array([np.cos(rad_angle), np.sin(rad_angle)])
        bullet_pos = self.position + direction * (self.radius * 2)
        bullet_vel = self.velocity + direction * CONFIG["bullet_speed"]
        return Bullet(bullet_pos, bullet_vel)
    
    def take_damage(self, amount=10):
        if self.shields > 0:
            self.shields -= amount
            self.shield_recharge_cooldown = 3.0
            if self.shields < 0:
                self.shields = 0
            return False
        return True
    
    def draw(self, surface, camera):
        screen_pos = camera.world_to_screen(self.position)
        zoom = camera.zoom
        
        if len(self.trajectory) > 1:
            screen_points = [tuple(camera.world_to_screen(p).astype(int)) for p in self.trajectory]
            valid_points = []
            for p in screen_points:
                if -100 < p[0] < camera.screen_width + 100 and -100 < p[1] < camera.screen_height + 100:
                    valid_points.append(p)
            if len(valid_points) > 1:
                pygame.draw.lines(surface, CONFIG["trajectory_color"], False, valid_points, 1)
        
        rad_angle = np.radians(self.orientation)
        size = self.radius * zoom * 2
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
        
        # Draw shield if active
        if self.shields > 0:
            shield_alpha = int(255 * (self.shields / self.max_shields) * 0.5)
            shield_surface = pygame.Surface((int(size * 4), int(size * 4)), pygame.SRCALPHA)
            pygame.draw.circle(shield_surface, (100, 150, 255, shield_alpha), 
                              (int(size * 2), int(size * 2)), int(size * 1.5))
            shield_pos = screen_pos - np.array([size * 2, size * 2])
            surface.blit(shield_surface, shield_pos.astype(int))
        
        pygame.draw.polygon(surface, self.color, [p.astype(int) for p in rotated_points])
        
        if self.thrusting and self.fuel > 0:
            flame_length = size * 1.5
            flame_width = size * 0.6
            flame_points = [
                (-size / 2, -flame_width / 2),
                (-size / 2 - flame_length * (0.5 + random.random() * 0.5), 0),
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
        self.offset = np.array([0.0, 0.0])
        self.zoom = 1.0
        self.target = None
    
    def set_target(self, target_body):
        self.target = target_body
    
    def update(self, dt):
        if self.target:
            target_screen_center = np.array([self.screen_width / 2, self.screen_height / 2])
            self.offset = self.target.position - target_screen_center / self.zoom
    
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
        star_radius = np.cbrt(star_mass) * 0.05
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
            
            try:
                orbit_speed = np.sqrt(CONFIG["gravity_constant"] * star_mass / orbit_radius)
            except ValueError:
                orbit_speed = 0
            velocity_direction = np.array([-np.sin(angle), np.cos(angle)])
            velocity = velocity_direction * orbit_speed * random.uniform(0.95, 1.05)
            
            mass, radius, color, density = generate_planet_properties(orbit_radius, star_mass)
            
            planet = Planet(position, velocity, mass, radius, color, density, name=f"Planet-{i+1}")
            self.bodies.append(planet)
        
        # Generate Asteroid Fields
        for _ in range(CONFIG["asteroid_field_count"]):
            field_orbit_radius = random.uniform(CONFIG["min_orbit_radius"] * 1.2, last_orbit_radius * 1.2)
            field_width = field_orbit_radius * random.uniform(0.1, 0.3)
            
            for i in range(CONFIG["asteroids_per_field"]):
                orbit_radius = field_orbit_radius + random.uniform(-field_width/2, field_width/2)
                angle = random.uniform(0, 2 * np.pi)
                position = center + np.array([np.cos(angle), np.sin(angle)]) * orbit_radius
                
                # Calculate orbital velocity with some variance
                orbit_speed = np.sqrt(CONFIG["gravity_constant"] * star_mass / orbit_radius) * random.uniform(0.9, 1.1)
                velocity_direction = np.array([-np.sin(angle), np.cos(angle)])
                velocity = velocity_direction * orbit_speed
                
                # Generate asteroid properties
                asteroid_mass = random.uniform(CONFIG["asteroid_mass_min"], CONFIG["asteroid_mass_max"])
                asteroid_radius = random.uniform(CONFIG["asteroid_radius_min"], CONFIG["asteroid_radius_max"])
                asteroid_color = (
                    random.randint(80, 120),
                    random.randint(80, 120),
                    random.randint(80, 120)
                )
                
                asteroid = Asteroid(position, velocity, asteroid_mass, asteroid_radius, asteroid_color, name=f"Asteroid-{i}")
                self.bodies.append(asteroid)
        
        return self.bodies

class StarSystem:
    def __init__(self, seed=None):
        self.generator = SystemGenerator(seed)
        self.bodies = self.generator.generate_system()
        self.rocket = None
        self.bullets = []
        self.enemies = []
        self.missions = []
        self.active_mission = None
        self.collectibles = []
        self.time_since_enemy_spawn = 0
        
    def add_rocket(self, rocket):
        self.rocket = rocket
        
    def update(self, dt):
        # Apply gravitational forces between bodies
        for i, body1 in enumerate(self.bodies):
            for body2 in self.bodies[i+1:]:
                force = body1.gravitational_force_from(body2, CONFIG["gravity_constant"])
                body1.apply_force(force)
                body2.apply_force(-force)
            
            # Apply gravitational force on rocket
            if self.rocket:
                force = self.rocket.gravitational_force_from(body1, CONFIG["gravity_constant"])
                self.rocket.apply_force(force)
        
        # Update positions of all bodies
        for body in self.bodies:
            body.update_position(dt)
        
        if self.rocket:
            self.rocket.update_position(dt)
            
            # Check for collisions with planets
            for body in self.bodies:
                if not isinstance(body, Star) and self.rocket.distance_to(body) < (self.rocket.radius + body.radius):
                    # Handle collision - could be damage or landing mechanics
                    impact_velocity = np.linalg.norm(self.rocket.velocity - body.velocity)
                    if impact_velocity > 50:  # Hard landing
                        self.rocket.take_damage(impact_velocity / 10)
                    elif isinstance(body, Planet):
                        # Successfully landed
                        pass
        
        # Update bullets
        self.bullets = [bullet for bullet in self.bullets if bullet.update(dt)]
        
        # Check bullet collisions with enemies
        for bullet in self.bullets[:]:
            for enemy in self.enemies[:]:
                if np.linalg.norm(bullet.position - enemy.position) < (bullet.radius + enemy.radius):
                    if enemy.take_damage():
                        self.enemies.remove(enemy)
                    if bullet in self.bullets:
                        self.bullets.remove(bullet)
                    break
        
        # Update enemies
        self.time_since_enemy_spawn += dt
        if self.time_since_enemy_spawn > 30 and len(self.enemies) < 5 and random.random() < 0.01:
            self.spawn_enemy()
            self.time_since_enemy_spawn = 0
            
        for enemy in self.enemies[:]:
            if enemy.update(dt):
                # Enemy firing logic
                if enemy.can_fire() and np.linalg.norm(enemy.position - self.rocket.position) < 800:
                    bullet = enemy.fire(self.rocket.position)
                    if bullet:
                        self.bullets.append(bullet)
            else:
                self.enemies.remove(enemy)
        
        # Check enemy bullet collisions with rocket
        for bullet in self.bullets[:]:
            if bullet.color == (255, 50, 50) and self.rocket and bullet.collision_check(self.rocket):
                self.rocket.take_damage(10)
                if bullet in self.bullets:
                    self.bullets.remove(bullet)
        
        # Update collectibles
        for collectible in self.collectibles[:]:
            if not collectible.update(dt):
                self.collectibles.remove(collectible)
        
        # Update active mission
        if self.active_mission:
            self.active_mission.update(dt, self.rocket)
            if self.active_mission.completed:
                self.rocket.credits += self.active_mission.reward
                self.active_mission = None
    
    def spawn_enemy(self):
        if not self.rocket:
            return
            
        star = self.bodies[0]
        spawn_distance = random.uniform(CONFIG["enemy_spawn_distance_min"], CONFIG["enemy_spawn_distance_max"])
        angle = random.uniform(0, 2 * np.pi)
        position = star.position + np.array([np.cos(angle), np.sin(angle)]) * spawn_distance
        
        # Make sure enemy is not too close to rocket
        while np.linalg.norm(position - self.rocket.position) < 2000:
            angle = random.uniform(0, 2 * np.pi)
            position = star.position + np.array([np.cos(angle), np.sin(angle)]) * spawn_distance
        
        enemy = Enemy(position, self.rocket)
        self.enemies.append(enemy)
    
    def generate_mission(self):
        if not self.active_mission:
            mission_type = random.choice(CONFIG["mission_types"])
            self.active_mission = Mission(mission_type, self)
            
            # Add collectibles to the system if needed
            if mission_type == "collect":
                for obj in self.active_mission.target_objects:
                    self.collectibles.append(obj)
                    
            return self.active_mission
        return None
    
    def draw(self, surface, camera):
        # Draw all celestial bodies
        for body in self.bodies:
            body.draw(surface, camera)
        
        # Draw bullets
        for bullet in self.bullets:
            bullet.draw(surface, camera)
        
        # Draw enemies
        for enemy in self.enemies:
            enemy.draw(surface, camera)
        
        # Draw collectibles
        for collectible in self.collectibles:
            collectible.draw(surface, camera)
        
        # Draw active mission elements
        if self.active_mission:
            self.active_mission.draw(surface, camera)
        
        # Draw rocket
        if self.rocket:
            self.rocket.draw(surface, camera)

class MiniMap:
    def __init__(self, size=CONFIG["map_size"], position=CONFIG["map_position"]):
        self.size = size
        self.position = position
        self.surface = pygame.Surface((size, size))
        self.zoom_factor = 0.01  # Adjust to change mini-map scale
    
    def update(self, star_system, rocket_pos):
        self.surface.fill((20, 20, 40))
        
        # Draw border
        pygame.draw.rect(self.surface, (100, 100, 100), (0, 0, self.size, self.size), 1)
        
        center = np.array([self.size/2, self.size/2])
        
        # Draw all bodies
        for body in star_system.bodies:
            if isinstance(body, Star):
                color = (255, 255, 0)
                radius = 4
            elif isinstance(body, Planet):
                color = body.color
                radius = 2
            else:  # Asteroid or other
                continue  # Don't draw asteroids on minimap
                
            rel_pos = (body.position - rocket_pos) * self.zoom_factor + center
            if 0 <= rel_pos[0] < self.size and 0 <= rel_pos[1] < self.size:
                pygame.draw.circle(self.surface, color, rel_pos.astype(int), radius)
        
        # Draw enemies
        for enemy in star_system.enemies:
            rel_pos = (enemy.position - rocket_pos) * self.zoom_factor + center
            if 0 <= rel_pos[0] < self.size and 0 <= rel_pos[1] < self.size:
                pygame.draw.circle(self.surface, (255, 50, 50), rel_pos.astype(int), 2)
        
        # Draw rocket at center
        pygame.draw.circle(self.surface, (0, 255, 0), center.astype(int), 3)
    
    def draw(self, surface):
        surface.blit(self.surface, self.position)

class UI:
    def __init__(self):
        self.font = pygame.font.SysFont('Arial', CONFIG["ui_font_size"])
        self.large_font = pygame.font.SysFont('Arial', CONFIG["ui_font_size"] * 2)
        self.mission_font = pygame.font.SysFont('Arial', CONFIG["ui_font_size"] + 2)
    
    def draw(self, surface, rocket, star_system, camera):
        if rocket:
            # Draw fuel gauge
            fuel_pct = rocket.fuel / CONFIG["rocket_initial_fuel"]
            fuel_width = 150
            pygame.draw.rect(surface, (50, 50, 50), (20, 20, fuel_width, 15))
            pygame.draw.rect(surface, (0, 200, 0), (20, 20, int(fuel_width * fuel_pct), 15))
            fuel_text = self.font.render(f"Fuel: {int(rocket.fuel)}", True, CONFIG["ui_color"])
            surface.blit(fuel_text, (20, 40))
            
            # Draw shield gauge
            shield_pct = rocket.shields / rocket.max_shields
            shield_width = 150
            pygame.draw.rect(surface, (50, 50, 50), (20, 70, shield_width, 15))
            pygame.draw.rect(surface, (100, 100, 255), (20, 70, int(shield_width * shield_pct), 15))
            shield_text = self.font.render(f"Shields: {int(rocket.shields)}", True, CONFIG["ui_color"])
            surface.blit(shield_text, (20, 90))
            
            # Draw credits
            credits_text = self.font.render(f"Credits: {rocket.credits}", True, CONFIG["ui_color"])
            surface.blit(credits_text, (20, 120))
            
            # Draw velocity
            velocity = np.linalg.norm(rocket.velocity)
            velocity_text = self.font.render(f"Velocity: {int(velocity)}", True, CONFIG["ui_color"])
            surface.blit(velocity_text, (20, 150))
            
            # Draw zoom level
            zoom_text = self.font.render(f"Zoom: {camera.zoom:.2f}x", True, CONFIG["ui_color"])
            surface.blit(zoom_text, (20, 180))
        
        # Draw active mission info
        if star_system.active_mission:
            mission = star_system.active_mission
            pygame.draw.rect(surface, (0, 0, 0, 150), (CONFIG["screen_width"] - 300, 20, 280, 150))
            
            mission_title = self.mission_font.render("Active Mission", True, (255, 255, 100))
            surface.blit(mission_title, (CONFIG["screen_width"] - 290, 30))
            
            mission_desc = self.font.render(mission.description, True, CONFIG["ui_color"])
            surface.blit(mission_desc, (CONFIG["screen_width"] - 290, 60))
            
            progress_text = self.font.render(f"Progress: {mission.completed_count}/{mission.target_count}", True, CONFIG["ui_color"])
            surface.blit(progress_text, (CONFIG["screen_width"] - 290, 90))
            
            time_text = self.font.render(f"Time: {int(mission.time_remaining)}s", True, CONFIG["ui_color"])
            surface.blit(time_text, (CONFIG["screen_width"] - 290, 120))
            
            reward_text = self.font.render(f"Reward: {mission.reward} credits", True, CONFIG["ui_color"])
            surface.blit(reward_text, (CONFIG["screen_width"] - 290, 150))
        else:
            mission_text = self.font.render("No active mission - Press 'M' for new mission", True, CONFIG["ui_color"])
            surface.blit(mission_text, (CONFIG["screen_width"] // 2 - mission_text.get_width() // 2, 20))

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((CONFIG["screen_width"], CONFIG["screen_height"]))
        pygame.display.set_caption("Stellar Voyager")
        self.clock = pygame.time.Clock()
        self.running = True
        self.camera = Camera(CONFIG["screen_width"], CONFIG["screen_height"])
        self.star_system = StarSystem()
        self.ui = UI()
        self.mini_map = MiniMap()
        self.paused = False
        self.game_over = False
        
        # Create rocket near the first planet
        first_planet = next((body for body in self.star_system.bodies if isinstance(body, Planet)), None)
        if first_planet:
            start_pos = first_planet.position + np.array([first_planet.radius * 3, 0])
            orbit_speed = np.sqrt(CONFIG["gravity_constant"] * first_planet.mass / (first_planet.radius * 3))
            start_vel = np.array([0, orbit_speed * 0.9])
            self.rocket = Rocket(start_pos, start_vel)
            self.star_system.add_rocket(self.rocket)
            self.camera.set_target(self.rocket)
        else:
            # Fallback position at the star
            star = self.star_system.bodies[0]
            start_pos = star.position + np.array([3000, 0])
            start_vel = np.array([0, 30])
            self.rocket = Rocket(start_pos, start_vel)
            self.star_system.add_rocket(self.rocket)
            self.camera.set_target(self.rocket)
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.paused = not self.paused
                elif event.key == pygame.K_SPACE and not self.paused:
                    if self.rocket.can_fire():
                        bullet = self.rocket.fire()
                        if bullet:
                            self.star_system.bullets.append(bullet)
                elif event.key == pygame.K_m and not self.paused:
                    self.star_system.generate_mission()
                elif event.key == pygame.K_r and self.game_over:
                    self.__init__()  # Restart game
        
        if self.paused or self.game_over:
            return
        
        keys = pygame.key.get_pressed()
        
        # Rocket controls
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.rocket.thrusting = True
            self.rocket.apply_thrust(CONFIG["time_step"])
        else:
            self.rocket.thrusting = False
        
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.rocket.rotate(-1)
        
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.rocket.rotate(1)
        
        # Camera controls
        if keys[pygame.K_EQUALS] or keys[pygame.K_KP_PLUS]:
            self.camera.zoom_in()
        
        if keys[pygame.K_MINUS] or keys[pygame.K_KP_MINUS]:
            self.camera.zoom_out()
        
        # Camera movement when not locked to rocket
        if keys[pygame.K_c]:
            self.camera.set_target(None)
        
        if keys[pygame.K_v]:
            self.camera.set_target(self.rocket)
        
        if self.camera.target is None:
            move_speed = CONFIG["camera_speed"] / self.camera.zoom
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                self.camera.move(0, -move_speed)
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                self.camera.move(0, move_speed)
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.camera.move(-move_speed, 0)
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.camera.move(move_speed, 0)
    
    def update(self):
        if self.paused or self.game_over:
            return
            
        dt = CONFIG["time_step"]
        self.star_system.update(dt)
        self.camera.update(dt)
        
        # Check if rocket is out of fuel or destroyed
        if self.rocket:
            if self.rocket.shields <= 0:
                self.game_over = True
    
    def render(self):
        self.screen.fill(CONFIG["background_color"])
        
        # Draw star system
        self.star_system.draw(self.screen, self.camera)
        
        # Draw UI
        self.ui.draw(self.screen, self.rocket, self.star_system, self.camera)
        
        # Draw mini-map
        if self.rocket:
            self.mini_map.update(self.star_system, self.rocket.position)
            self.mini_map.draw(self.screen)
        
        # Draw pause overlay
        if self.paused:
            pause_overlay = pygame.Surface((CONFIG["screen_width"], CONFIG["screen_height"]), pygame.SRCALPHA)
            pause_overlay.fill((0, 0, 0, 128))
            self.screen.blit(pause_overlay, (0, 0))
            
            pause_text = self.ui.large_font.render("PAUSED", True, (255, 255, 255))
            text_pos = (CONFIG["screen_width"] // 2 - pause_text.get_width() // 2, 
                        CONFIG["screen_height"] // 2 - pause_text.get_height() // 2)
            self.screen.blit(pause_text, text_pos)
            
            help_text = self.ui.font.render("Press ESC to resume", True, (255, 255, 255))
            help_pos = (CONFIG["screen_width"] // 2 - help_text.get_width() // 2, 
                        CONFIG["screen_height"] // 2 + pause_text.get_height())
            self.screen.blit(help_text, help_pos)
        
        # Draw game over screen
        if self.game_over:
            game_over_overlay = pygame.Surface((CONFIG["screen_width"], CONFIG["screen_height"]), pygame.SRCALPHA)
            game_over_overlay.fill((0, 0, 0, 192))
            self.screen.blit(game_over_overlay, (0, 0))
            
            game_over_text = self.ui.large_font.render("GAME OVER", True, (255, 50, 50))
            text_pos = (CONFIG["screen_width"] // 2 - game_over_text.get_width() // 2, 
                        CONFIG["screen_height"] // 2 - game_over_text.get_height() // 2)
            self.screen.blit(game_over_text, text_pos)
            
            restart_text = self.ui.font.render("Press R to restart", True, (255, 255, 255))
            restart_pos = (CONFIG["screen_width"] // 2 - restart_text.get_width() // 2, 
                           CONFIG["screen_height"] // 2 + game_over_text.get_height())
            self.screen.blit(restart_text, restart_pos)
        
        pygame.display.flip()
    
    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.render()
            self.clock.tick(CONFIG["fps"])
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = Game()
    game.run()
