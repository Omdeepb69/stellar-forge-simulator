import pygame
import numpy as np
import random
import math
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures

# Configuration Constants
CONFIG = {
    "screen_width": 1280,
    "screen_height": 720,
    "fps": 60,
    "gravity_constant": 9.674e-5,
    "time_step": 0.1,
    "camera_speed": 5,
    "zoom_speed": 1.1,
    "min_zoom": 0.1,
    "max_zoom": 5.0,
    "star_mass_min": 5e6,
    "star_mass_max": 5e7,
    "planet_count": 5,
    "min_orbit_radius": 1500,
    "max_orbit_radius": 10000,
    "planet_mass_factor": 0.01,
    "planet_radius_min": 20,
    "planet_radius_max": 50,
    "rocket_mass": 100,
    "rocket_thrust": 500,
    "rocket_rotation_speed": 3,
    "rocket_initial_fuel": 1000,
    "fuel_consumption_rate": 0.5,
    "background_color": (5, 5, 15),
    "star_color": (255, 255, 150),
    "rocket_color": (200, 200, 255),
    "trajectory_color": (0, 100, 255),
    "trajectory_length": 200,
    "show_trajectory": True,
    "ui_font_size": 24,
    "max_enemies": 5,
    "enemy_spawn_rate": 0.01
}

class CelestialBody:
    def __init__(self, position, velocity, mass, radius, color, name="Body"):
        self.position = np.array(position, dtype=float)
        self.velocity = np.array(velocity, dtype=float)
        self.mass = float(mass)
        self.radius = float(radius)
        self.color = color
        self.name = name
        self.acceleration = np.zeros(2, dtype=float)
        self.rotation = 0.0
        self.rotation_speed = random.uniform(-0.5, 0.5)

    def apply_force(self, force):
        if self.mass > 0:
            self.acceleration += force / self.mass

    def update(self, dt):
        self.velocity += self.acceleration * dt
        self.position += self.velocity * dt
        self.acceleration = np.zeros(2, dtype=float)
        self.rotation = (self.rotation + self.rotation_speed * dt) % 360

    def draw(self, surface, camera):
        screen_pos = camera.world_to_screen(self.position)
        screen_radius = int(self.radius * camera.zoom)
        
        if screen_radius < 1:
            if 0 <= screen_pos[0] < camera.screen_width and 0 <= screen_pos[1] < camera.screen_height:
                pygame.draw.circle(surface, self.color, screen_pos.astype(int), 1)
        elif screen_radius >= 1:
            if (-screen_radius < screen_pos[0] < camera.screen_width + screen_radius and
                -screen_radius < screen_pos[1] < camera.screen_height + screen_radius):
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

    def visible(self, camera):
        screen_pos = camera.world_to_screen(self.position)
        screen_radius = int(self.radius * camera.zoom)
        return (-screen_radius < screen_pos[0] < camera.screen_width + screen_radius and
                -screen_radius < screen_pos[1] < camera.screen_height + screen_radius)

class Star(CelestialBody):
    def __init__(self, position, mass, radius, color=CONFIG["star_color"], name="Star"):
        super().__init__(position, [0, 0], mass, radius, color, name)
        self.flare_timer = 0
        self.flare_interval = random.uniform(10.0, 30.0)

    def draw(self, surface, camera):
        screen_pos = camera.world_to_screen(self.position)
        screen_radius = int(self.radius * camera.zoom)
        
        if screen_radius >= 1:
            # Draw glow effect
            glow_surface = pygame.Surface((screen_radius * 4, screen_radius * 4), pygame.SRCALPHA)
            for i in range(3):
                glow_radius = screen_radius * (1.5 - i * 0.2)
                alpha = 100 - i * 30
                pygame.draw.circle(glow_surface, (*self.color[:3], alpha), 
                                  (screen_radius * 2, screen_radius * 2), glow_radius)
            
            # Main star
            pygame.draw.circle(glow_surface, self.color, 
                              (screen_radius * 2, screen_radius * 2), screen_radius)
            
            surface.blit(glow_surface, 
                        (screen_pos[0] - screen_radius * 2, screen_pos[1] - screen_radius * 2))

class Planet(CelestialBody):
    def __init__(self, position, velocity, mass, radius, color, name="Planet"):
        super().__init__(position, velocity, mass, radius, color, name)
        self.has_atmosphere = random.random() < 0.7
        self.atmosphere_color = (
            min(color[0] + 30, 255),
            min(color[1] + 30, 255),
            min(color[2] + 30, 255)
        )

    def draw(self, surface, camera):
        screen_pos = camera.world_to_screen(self.position)
        screen_radius = int(self.radius * camera.zoom)
        
        if screen_radius >= 1:
            # Atmosphere glow
            if self.has_atmosphere:
                atmo_radius = int(screen_radius * 1.2)
                atmo_surface = pygame.Surface((atmo_radius * 2, atmo_radius * 2), pygame.SRCALPHA)
                atmo_color = (*self.atmosphere_color, 80)
                pygame.draw.circle(atmo_surface, atmo_color, 
                                  (atmo_radius, atmo_radius), atmo_radius)
                surface.blit(atmo_surface, 
                            (screen_pos[0] - atmo_radius, screen_pos[1] - atmo_radius))
            
            # Planet body
            pygame.draw.circle(surface, self.color, screen_pos.astype(int), screen_radius)
            
            # Surface details
            if screen_radius > 8:
                detail_color = (
                    max(0, self.color[0] - 40),
                    max(0, self.color[1] - 40),
                    max(0, self.color[2] - 40)
                )
                for _ in range(3):
                    angle = random.uniform(0, 2 * math.pi)
                    distance = random.uniform(0.3, 0.7) * screen_radius
                    size = random.uniform(0.1, 0.3) * screen_radius
                    detail_pos = (
                        screen_pos[0] + math.cos(angle) * distance,
                        screen_pos[1] + math.sin(angle) * distance
                    )
                    pygame.draw.circle(surface, detail_color, detail_pos, int(size))

class Rocket(CelestialBody):
    def __init__(self, position, velocity=[0, 0]):
        super().__init__(position, velocity, CONFIG["rocket_mass"], 10, CONFIG["rocket_color"], "Player")
        self.thrust = CONFIG["rocket_thrust"]
        self.rotation_speed = CONFIG["rocket_rotation_speed"]
        self.angle = 0
        self.thrusting = False
        self.turning_left = False
        self.turning_right = False
        self.fuel = CONFIG["rocket_initial_fuel"]
        self.max_fuel = CONFIG["rocket_initial_fuel"]
        self.health = 100
        self.max_health = 100
        self.trajectory_points = []
        self.fire_rate_timer = 0
        self.damage_flash_timer = 0

    def apply_thrust(self):
        if self.fuel <= 0:
            self.thrusting = False
            return
            
        thrust_vector = np.array([math.cos(self.angle), math.sin(self.angle)]) * self.thrust
        self.apply_force(thrust_vector)
        
        if self.thrusting:
            self.fuel -= CONFIG["fuel_consumption_rate"]
            self.fuel = max(0, self.fuel)

    def update_rotation(self, dt):
        if self.turning_left:
            self.angle -= self.rotation_speed * dt
        if self.turning_right:
            self.angle += self.rotation_speed * dt

    def update_trajectory(self, celestial_bodies, dt):
        self.trajectory_points = []
        pred_pos = self.position.copy()
        pred_vel = self.velocity.copy()
        
        for _ in range(CONFIG["trajectory_length"]):
            total_force = np.zeros(2, dtype=float)
            for body in celestial_bodies:
                if isinstance(body, CelestialBody) and body != self:
                    delta = body.position - pred_pos
                    distance_sq = np.dot(delta, delta)
                    if distance_sq > 0:
                        distance = np.sqrt(distance_sq)
                        force_magnitude = CONFIG["gravity_constant"] * self.mass * body.mass / distance_sq
                        force = force_magnitude * (delta / distance)
                        total_force += force
            
            pred_acc = total_force / self.mass
            pred_vel += pred_acc * CONFIG["time_step"] * 2
            pred_pos += pred_vel * CONFIG["time_step"] * 2
            self.trajectory_points.append(pred_pos.copy())

    def draw_trajectory(self, surface, camera):
        if len(self.trajectory_points) < 2 or not CONFIG["show_trajectory"]:
            return
            
        screen_points = [camera.world_to_screen(p).astype(int) for p in self.trajectory_points]
        
        for i in range(len(screen_points) - 1):
            alpha = 255 - int(200 * i / len(screen_points))
            color = CONFIG["trajectory_color"][:3] + (alpha,)
            pygame.draw.line(surface, color, screen_points[i], screen_points[i + 1], 2)

    def draw(self, surface, camera):
        screen_pos = camera.world_to_screen(self.position)
        screen_radius = max(3, int(self.radius * camera.zoom))
        
        # Flash effect when damaged
        color = self.color
        if self.damage_flash_timer > 0:
            flash_intensity = min(255, int(255 * self.damage_flash_timer / 0.5))
            color = (255, flash_intensity, flash_intensity)
        
        direction = np.array([math.cos(self.angle), math.sin(self.angle)])
        right = np.array([-direction[1], direction[0]])
        
        rocket_length = screen_radius * 3
        nose = screen_pos + direction * rocket_length
        left_wing = screen_pos - direction * rocket_length/2 + right * screen_radius
        right_wing = screen_pos - direction * rocket_length/2 - right * screen_radius
        tail = screen_pos - direction * rocket_length/2
        
        pygame.draw.polygon(surface, color, [nose, left_wing, right_wing])
        
        if self.thrusting and self.fuel > 0:
            flame_length = rocket_length * random.uniform(0.7, 1.0)
            flame_points = [
                tail,
                tail - direction * flame_length + right * screen_radius/2,
                tail - direction * flame_length * 1.2,
                tail - direction * flame_length - right * screen_radius/2
            ]
            flame_color = (255, random.randint(100, 200), 0)
            pygame.draw.polygon(surface, flame_color, flame_points)

    def take_damage(self, amount):
        self.health -= amount
        self.damage_flash_timer = 0.5
        return self.health <= 0

class Enemy(CelestialBody):
    def __init__(self, position, velocity=None, health=3):
        velocity = velocity if velocity is not None else [0, 0]
        super().__init__(position, velocity, 50, 15, (255, 50, 50), "Enemy")
        self.health = health
        self.max_health = health
        self.speed = 150
        self.damage = 10
        self.fire_timer = random.uniform(1, 3)
        self.target = None
        self.active = True
        self.damaged_timer = 0

    def set_target(self, target):
        self.target = target

    def update(self, dt, bullets):
        if not self.active or not self.target:
            return
            
        if self.damaged_timer > 0:
            self.damaged_timer -= dt
        
        # Move toward target
        direction = self.target.position - self.position
        distance = np.linalg.norm(direction)
        
        if distance > 0:
            direction = direction / distance
            self.velocity = direction * self.speed
            self.position += self.velocity * dt
            
            # Face target
            self.angle = math.atan2(direction[1], direction[0])
            
            # Fire at target
            if distance < 800:
                self.fire_timer -= dt
                if self.fire_timer <= 0:
                    self.fire(bullets)
                    self.fire_timer = random.uniform(1.5, 3.0)

    def fire(self, bullets):
        direction = np.array([math.cos(self.angle), math.sin(self.angle)])
        bullet_pos = self.position + direction * self.radius
        bullet_vel = self.velocity + direction * 600
        bullet = CelestialBody(bullet_pos, bullet_vel, 1, 3, (255, 100, 100))
        bullets.append(bullet)

    def take_damage(self, amount):
        self.health -= amount
        self.damaged_timer = 0.3
        if self.health <= 0:
            self.active = False
            return True
        return False

    def draw(self, surface, camera):
        if not self.active:
            return
            
        screen_pos = camera.world_to_screen(self.position)
        screen_radius = int(self.radius * camera.zoom)
        
        color = self.color
        if self.damaged_timer > 0:
            color = (255, 100, 100)
        
        direction = np.array([math.cos(self.angle), math.sin(self.angle)])
        right = np.array([-direction[1], direction[0]])
        
        ship_length = screen_radius * 2
        nose = screen_pos + direction * ship_length/2
        left_wing = screen_pos - direction * ship_length/2 + right * screen_radius
        right_wing = screen_pos - direction * ship_length/2 - right * screen_radius
        
        pygame.draw.polygon(surface, color, [nose, left_wing, right_wing])
        
        # Health bar
        if self.health < self.max_health:
            bar_width = screen_radius * 2
            bar_height = 4
            health_width = int(bar_width * (self.health / self.max_health))
            pygame.draw.rect(surface, (255, 0, 0), 
                           (screen_pos[0] - bar_width/2, screen_pos[1] - ship_length, 
                            bar_width, bar_height))
            pygame.draw.rect(surface, (0, 255, 0), 
                           (screen_pos[0] - bar_width/2, screen_pos[1] - ship_length, 
                            health_width, bar_height))

class Camera:
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.position = np.array([0, 0], dtype=float)
        self.zoom = 1.0
        self.target = None
    
    def world_to_screen(self, world_pos):
        relative_pos = (world_pos - self.position) * self.zoom
        return np.array([
            self.screen_width / 2 + relative_pos[0],
            self.screen_height / 2 + relative_pos[1]
        ])
    
    def screen_to_world(self, screen_pos):
        relative_pos = np.array([
            screen_pos[0] - self.screen_width / 2,
            screen_pos[1] - self.screen_height / 2
        ])
        return self.position + relative_pos / self.zoom
    
    def set_target(self, target):
        self.target = target
    
    def update(self, dt):
        if self.target:
            # Smooth follow
            follow_speed = 5.0 * dt
            self.position += (self.target.position - self.position) * follow_speed
    
    def zoom_in(self):
        self.zoom = min(CONFIG["max_zoom"], self.zoom * CONFIG["zoom_speed"])
    
    def zoom_out(self):
        self.zoom = max(CONFIG["min_zoom"], self.zoom / CONFIG["zoom_speed"])

class Background:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.stars = []
        
        for _ in range(1000):
            self.stars.append({
                'x': random.randint(0, width),
                'y': random.randint(0, height),
                'size': random.uniform(0.5, 2.0),
                'brightness': random.randint(50, 255)
            })
    
    def draw(self, surface, camera):
        for star in self.stars:
            screen_x = (star['x'] - camera.position[0]) * camera.zoom + camera.screen_width/2
            screen_y = (star['y'] - camera.position[1]) * camera.zoom + camera.screen_height/2
            brightness = star['brightness']
            size = max(1, int(star['size'] * camera.zoom * 0.5))
            pygame.draw.circle(surface, (brightness, brightness, brightness), 
                              (int(screen_x), int(screen_y)), size)

class UI:
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.font = pygame.font.SysFont(None, CONFIG["ui_font_size"])
        self.small_font = pygame.font.SysFont(None, CONFIG["ui_font_size"] - 4)
        self.showing_map = False
    
    def draw_hud(self, surface, rocket):
        # Fuel gauge
        fuel_width = 200
        fuel_height = 20
        fuel_x = 20
        fuel_y = 20
        
        pygame.draw.rect(surface, (50, 50, 50), (fuel_x, fuel_y, fuel_width, fuel_height))
        pygame.draw.rect(surface, (0, 200, 0), 
                         (fuel_x, fuel_y, int(fuel_width * (rocket.fuel / rocket.max_fuel)), fuel_height))
        pygame.draw.rect(surface, (200, 200, 200), (fuel_x, fuel_y, fuel_width, fuel_height), 2)
        
        fuel_text = self.font.render(f"Fuel: {int(rocket.fuel)}/{rocket.max_fuel}", True, (255, 255, 255))
        surface.blit(fuel_text, (fuel_x + 10, fuel_y + 2))
        
        # Health gauge
        health_x = 20
        health_y = 50
        
        pygame.draw.rect(surface, (50, 50, 50), (health_x, health_y, fuel_width, fuel_height))
        health_percent = rocket.health / rocket.max_health
        health_color = (0, 255, 0) if health_percent > 0.6 else (255, 255, 0) if health_percent > 0.3 else (255, 0, 0)
        pygame.draw.rect(surface, health_color, 
                         (health_x, health_y, int(fuel_width * health_percent), fuel_height))
        pygame.draw.rect(surface, (200, 200, 200), (health_x, health_y, fuel_width, fuel_height), 2)
        
        health_text = self.font.render(f"Health: {int(rocket.health)}/{rocket.max_health}", True, (255, 255, 255))
        surface.blit(health_text, (health_x + 10, health_y + 2))
        
        # Speed indicator
        speed = np.linalg.norm(rocket.velocity)
        speed_text = self.font.render(f"Speed: {int(speed)}", True, (255, 255, 255))
        surface.blit(speed_text, (20, 80))
        
        # Coordinates
        coord_text = self.small_font.render(f"Position: ({int(rocket.position[0])}, {int(rocket.position[1])})", 
                                           True, (200, 200, 200))
        surface.blit(coord_text, (20, 110))
    
    def draw_map(self, surface, rocket, celestial_bodies, camera):
        if not self.showing_map:
            return
            
        # Create overlay
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        surface.blit(overlay, (0, 0))
        
        # Draw grid
        grid_size = 2000
        grid_color = (50, 50, 50, 150)
        
        for i in range(-5, 6):
            # Horizontal lines
            start_pos = camera.world_to_screen(np.array([-5 * grid_size, i * grid_size]) + rocket.position)
            end_pos = camera.world_to_screen(np.array([5 * grid_size, i * grid_size]) + rocket.position)
            pygame.draw.line(surface, grid_color, start_pos, end_pos, 1)
            
            # Vertical lines
            start_pos = camera.world_to_screen(np.array([i * grid_size, -5 * grid_size]) + rocket.position)
            end_pos = camera.world_to_screen(np.array([i * grid_size, 5 * grid_size]) + rocket.position)
            pygame.draw.line(surface, grid_color, start_pos, end_pos, 1)
        
        # Draw celestial bodies
        for body in celestial_bodies:
            if isinstance(body, CelestialBody):
                map_pos = camera.world_to_screen(body.position)
                size = max(2, int(body.radius * 0.01))
                
                if isinstance(body, Star):
                    color = (255, 255, 0)
                    size = max(3, size)
                elif isinstance(body, Planet):
                    color = body.color
                elif isinstance(body, Rocket):
                    color = (0, 255, 0)
                elif isinstance(body, Enemy):
                    color = (255, 0, 0) if body.active else (100, 0, 0)
                else:
                    color = (200, 200, 200)
                
                pygame.draw.circle(surface, color, map_pos.astype(int), size)
        
        # Draw title
        title = self.font.render("STAR MAP (M to close)", True, (255, 255, 255))
        surface.blit(title, (self.screen_width/2 - title.get_width()/2, 20))

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((CONFIG["screen_width"], CONFIG["screen_height"]))
        pygame.display.set_caption("Space Gravity Simulator")
        
        self.clock = pygame.time.Clock()
        self.running = True
        self.paused = False
        self.game_over = False
        
        self.camera = Camera(CONFIG["screen_width"], CONFIG["screen_height"])
        self.background = Background(20000, 20000)
        self.ui = UI(CONFIG["screen_width"], CONFIG["screen_height"])
        
        self.celestial_bodies = []
        self.bullets = []
        self.enemies = []
        
        self.generate_universe()
        
        self.camera.set_target(self.rocket)
    
    def generate_universe(self):
        # Create central star
        star_mass = (CONFIG["star_mass_min"] + CONFIG["star_mass_max"]) / 2
        self.star = Star([0, 0], star_mass, 100)
        self.celestial_bodies.append(self.star)
        
        # Create planets
        for i in range(CONFIG["planet_count"]):
            distance = random.uniform(CONFIG["min_orbit_radius"], CONFIG["max_orbit_radius"])
            angle = random.uniform(0, 2 * math.pi)
            position = np.array([math.cos(angle), math.sin(angle)]) * distance
            
            # Calculate orbital velocity
            orbit_speed = math.sqrt(CONFIG["gravity_constant"] * self.star.mass / distance)
            velocity = np.array([-math.sin(angle), math.cos(angle)]) * orbit_speed * random.uniform(0.9, 1.1)
            
            mass = random.uniform(5e4, 2e5)
            radius = random.uniform(CONFIG["planet_radius_min"], CONFIG["planet_radius_max"])
            color = (
                random.randint(50, 200),
                random.randint(50, 200),
                random.randint(50, 200)
            )
            
            planet = Planet(position, velocity, mass, radius, color, f"Planet {i+1}")
            self.celestial_bodies.append(planet)
        
        # Create player rocket near first planet
        spawn_angle = random.uniform(0, 2 * math.pi)
        spawn_distance = CONFIG["min_orbit_radius"] * 0.8
        self.rocket = Rocket([
            math.cos(spawn_angle) * spawn_distance,
            math.sin(spawn_angle) * spawn_distance
        ])
        self.celestial_bodies.append(self.rocket)
        
        # Create initial enemies
        for _ in range(3):
            self.spawn_enemy()
    
    def spawn_enemy(self):
        angle = random.uniform(0, 2 * math.pi)
        distance = random.uniform(2000, 5000)
        position = self.rocket.position + np.array([math.cos(angle), math.sin(angle)]) * distance
        
        enemy = Enemy(position)
        enemy.set_target(self.rocket)
        self.enemies.append(enemy)
        self.celestial_bodies.append(enemy)
    
    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.paused = not self.paused
                elif event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                    self.camera.zoom_in()
                elif event.key == pygame.K_MINUS:
                    self.camera.zoom_out()
                elif event.key == pygame.K_m:
                    self.ui.showing_map = not self.ui.showing_map
                elif event.key == pygame.K_SPACE:
                    self.rocket.fire_weapon(self.bullets)
        
        keys = pygame.key.get_pressed()
        self.rocket.thrusting = keys[pygame.K_w] or keys[pygame.K_UP]
        self.rocket.turning_left = keys[pygame.K_a] or keys[pygame.K_LEFT]
        self.rocket.turning_right = keys[pygame.K_d] or keys[pygame.K_RIGHT]
        
        # Debug controls
        if keys[pygame.K_0] and keys[pygame.K_LCTRL]:
            self.rocket.fuel = self.rocket.max_fuel
            self.rocket.health = self.rocket.max_health
    
    def update_physics(self, dt):
        # Update rocket controls
        self.rocket.update_rotation(dt)
        self.rocket.apply_thrust()
        
        # Calculate gravity between all bodies
        for i, body1 in enumerate(self.celestial_bodies):
            for body2 in self.celestial_bodies[i+1:]:
                if isinstance(body1, CelestialBody) and isinstance(body2, CelestialBody):
                    force = body1.gravitational_force_from(body2, CONFIG["gravity_constant"])
                    body1.apply_force(force)
                    body2.apply_force(-force)
        
        # Update positions and check collisions
        for body in self.celestial_bodies[:]:
            if isinstance(body, CelestialBody):
                body.update(dt)
                
                # Check for collisions with rocket
                if body != self.rocket:
                    distance = self.rocket.distance_to(body)
                    if distance < body.radius + self.rocket.radius:
                        # Calculate damage based on impact velocity
                        relative_vel = np.linalg.norm(self.rocket.velocity - body.velocity)
                        damage = int(relative_vel * 0.5)
                        if damage > 0:
                            if self.rocket.take_damage(damage):
                                self.game_over = True
                        
                        # Bounce off
                        normal = (self.rocket.position - body.position) / distance
                        self.rocket.velocity = np.dot(self.rocket.velocity, normal) * normal * 0.5
        
        # Update bullets
        for bullet in self.bullets[:]:
            bullet.update(dt)
            
            # Remove bullets that are too old or out of bounds
            screen_pos = self.camera.world_to_screen(bullet.position)
            if (bullet.lifetime <= 0 or 
                not (0 <= screen_pos[0] < CONFIG["screen_width"] and 
                     0 <= screen_pos[1] < CONFIG["screen_height"])):
                self.bullets.remove(bullet)
                if bullet in self.celestial_bodies:
                    self.celestial_bodies.remove(bullet)
        
        # Update enemies
        for enemy in self.enemies[:]:
            if isinstance(enemy, Enemy):
                enemy.update(dt, self.bullets)
                
                # Remove inactive enemies
                if not enemy.active:
                    self.enemies.remove(enemy)
                    if enemy in self.celestial_bodies:
                        self.celestial_bodies.remove(enemy)
        
        # Spawn new enemies occasionally
        if (len(self.enemies) < CONFIG["max_enemies"] and 
            random.random() < CONFIG["enemy_spawn_rate"]):
            self.spawn_enemy()
        
        # Update trajectory prediction
        self.rocket.update_trajectory(self.celestial_bodies, dt)
        
        # Update camera
        self.camera.update(dt)
    
    def draw(self):
        self.screen.fill(CONFIG["background_color"])
        
        # Draw background
        self.background.draw(self.screen, self.camera)
        
        # Draw celestial bodies (sorted by size for proper overlap)
        for body in sorted([b for b in self.celestial_bodies if isinstance(b, CelestialBody)], 
                          key=lambda b: b.radius):
            if body.visible(self.camera):
                body.draw(self.screen, self.camera)
        
        # Draw trajectory
        self.rocket.draw_trajectory(self.screen, self.camera)
        
        # Draw UI
        self.ui.draw_hud(self.screen, self.rocket)
        self.ui.draw_map(self.screen, self.rocket, self.celestial_bodies, self.camera)
        
        # Draw pause/game over screens
        if self.paused:
            overlay = pygame.Surface((CONFIG["screen_width"], CONFIG["screen_height"]), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 128))
            self.screen.blit(overlay, (0, 0))
            
            font = pygame.font.SysFont(None, 72)
            text = font.render("PAUSED", True, (255, 255, 255))
            self.screen.blit(text, (CONFIG["screen_width"]/2 - text.get_width()/2, 
                              CONFIG["screen_height"]/2 - text.get_height()/2))
        
        if self.game_over:
            overlay = pygame.Surface((CONFIG["screen_width"], CONFIG["screen_height"]), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 200))
            self.screen.blit(overlay, (0, 0))
            
            font = pygame.font.SysFont(None, 72)
            text = font.render("GAME OVER", True, (255, 50, 50))
            self.screen.blit(text, (CONFIG["screen_width"]/2 - text.get_width()/2, 
                              CONFIG["screen_height"]/2 - text.get_height()/2))
            
            font = pygame.font.SysFont(None, 36)
            text = font.render("Press ESC to exit", True, (200, 200, 200))
            self.screen.blit(text, (CONFIG["screen_width"]/2 - text.get_width()/2, 
                              CONFIG["screen_height"]/2 + 50))
        
        pygame.display.flip()
    
    def run(self):
        last_time = pygame.time.get_ticks()
        
        while self.running:
            current_time = pygame.time.get_ticks()
            dt = (current_time - last_time) / 1000.0
            last_time = current_time
            
            self.handle_input()
            
            if not self.paused and not self.game_over:
                self.update_physics(min(dt, 0.1))  # Cap dt to prevent physics issues
            
            self.draw()
            self.clock.tick(CONFIG["fps"])
        
        pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()