import pygame
import numpy as np
import random
import sys
import math
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
import pygame.freetype
import hashlib
import os

# Configuration Constants
CONFIG = {
    "screen_width": 1280,
    "screen_height": 720,
    "fps": 60,
    "gravity_constant": 9.674e-5,  # Increased for stronger gravitational pull
    "time_step": 0.1,
    "camera_speed": 5,
    "zoom_speed": 1.1,
    "min_zoom": 0.1,
    "max_zoom": 5.0,
    "star_mass_min": 5e6,
    "star_mass_max": 5e7,
    "planet_count_min": 4,
    "planet_count_max": 10,  # More planets
    "min_orbit_radius": 1500,
    "max_orbit_radius_factor": 100,
    "planet_mass_factor": 0.01,
    "planet_radius_min": 5,
    "planet_radius_max": 50,
    "asteroid_field_count": 3,  # More asteroid fields
    "asteroids_per_field": 150,  # More asteroids per field
    "asteroid_mass_min": 1e1,
    "asteroid_mass_max": 1e2,
    "asteroid_radius_min": 1,
    "asteroid_radius_max": 4,
    "rocket_mass": 70,  # Reduced mass for faster acceleration
    "rocket_thrust": 1000,  # Increased thrust for more responsive control
    "rocket_rotation_speed": 3,
    "rocket_initial_fuel": 1000,
    "fuel_consumption_rate": 0.5,
    "background_color": (5, 5, 15),  # Slightly darker background
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
    "mission_types": ["collect", "destroy", "explore", "deliver", "rescue", "defend", "research"],  # New mission types
    "mission_reward_min": 100,
    "mission_reward_max": 500,
    "mission_time_min": 60,
    "mission_time_max": 180,
    "collectible_color": (0, 255, 100),
    "collectible_radius": 8,
    "black_hole_spawn_chance": 0.25,  # 25% chance to have a black hole
    "wormhole_spawn_chance": 0.3,  # 30% chance to have wormholes
    "pulsar_spawn_chance": 0.2,  # 20% chance to have a pulsar
    "nebula_spawn_chance": 0.4,  # 40% chance to have a nebula
    "item_types": ["fuel", "shield", "weapon", "engine", "scanner", "repair"],
    "upgrade_cost_base": 100,
    "planet_biome_types": ["desert", "ice", "ocean", "forest", "volcanic", "gas", "rocky", "toxic"],
    "damage_visual_time": 0.5,  # Time to show damage visual effect
    "star_glow_effect": True,
    "message_display_time": 5.0,  # Time to display mission messages
    "boss_spawn_chance": 0.1,  # 10% chance for boss enemies in later missions
    "space_station_count": 2,  # Number of space stations in the system
    "debris_count": 3,  # Number of debris fields
    "debris_pieces_per_field": 20,
    "quest_line_length": 5,  # Number of sequential storyline missions,
}

# Story/Quest line for the game
STORY = {
    "title": "The Last Voyager",
    "intro": "As the last surviving pilot of the Stellar Fleet, you must discover what happened to your home planet while fending off mysterious attackers.",
    "quests": [
        {
            "id": 0,
            "title": "Distress Signal",
            "description": "Investigate a distress signal coming from a nearby outpost.",
            "mission_type": "explore",
            "target_count": 1,
            "reward": 200,
            "next_message": "The outpost has been attacked. Survivors mentioned raiders taking resources to the asteroid belt."
        },
        {
            "id": 1,
            "title": "Resource Recovery",
            "description": "Recover stolen supplies from the asteroid belt.",
            "mission_type": "collect",
            "target_count": 4,
            "reward": 300,
            "next_message": "You've recovered the supplies but detected enemy ships approaching."
        },
        {
            "id": 2,
            "title": "Defensive Maneuvers",
            "description": "Destroy the incoming enemy raiders.",
            "mission_type": "destroy",
            "target_count": 5,
            "reward": 400,
            "next_message": "One of the enemy ships was carrying coordinates to their base on a distant planet."
        },
        {
            "id": 3,
            "title": "Reconnaissance",
            "description": "Explore the enemy base on the distant planet.",
            "mission_type": "explore",
            "target_count": 1,
            "reward": 450,
            "next_message": "The base contained information about a scientific research station that may know what happened to your home planet."
        },
        {
            "id": 4,
            "title": "Final Discovery",
            "description": "Reach the research station and discover the truth.",
            "mission_type": "deliver",
            "target_count": 1,
            "reward": 750,
            "next_message": "The truth is revealed: a cosmic event destroyed your home world, but survivors established a colony beyond the nebula. You are not alone after all."
        }
    ],
    "epilogue": "With the coordinates of the survivor colony in hand, you set course for your new home, carrying hope for humanity's future among the stars."
}

# --- Enhanced ML Model for Planet Properties ---
np.random.seed(42)
_distances = np.linspace(CONFIG["min_orbit_radius"], CONFIG["min_orbit_radius"] * 50, 100).reshape(-1, 1)
_mass_factors = (0.001 + 0.05 * (_distances / _distances.max())**0.5 + np.random.normal(0, 0.01, _distances.shape)).clip(0.0001, 0.2)  # Higher mass variance
_radii = (CONFIG["planet_radius_min"] + (CONFIG["planet_radius_max"] - CONFIG["planet_radius_min"]) * (_distances / _distances.max())**0.3 + np.random.normal(0, 5, _distances.shape)).clip(CONFIG["planet_radius_min"], CONFIG["planet_radius_max"])  # Higher size variance
_density_factors = (0.1 + 0.9 * np.exp(-_distances / (CONFIG["min_orbit_radius"] * 20)) + np.random.normal(0, 0.2, _distances.shape)).clip(0.05, 1.0)  # Higher density variance

poly = PolynomialFeatures(degree=2, include_bias=False)
_distances_poly = poly.fit_transform(_distances)

mass_model = LinearRegression().fit(_distances_poly, _mass_factors)
radius_model = LinearRegression().fit(_distances_poly, _radii)
density_model = LinearRegression().fit(_distances_poly, _density_factors)

def generate_planet_properties(orbital_distance, star_mass):
    """Generate realistic planet properties based on distance from star and assign biome."""
    dist_poly = poly.transform(np.array([[orbital_distance]]))
    mass_factor = mass_model.predict(dist_poly)[0][0]
    mass = star_mass * np.clip(mass_factor + np.random.normal(0, 0.005), 0.0001, 0.2)
    radius = radius_model.predict(dist_poly)[0][0]
    radius = np.clip(radius + np.random.normal(0, 4), CONFIG["planet_radius_min"], CONFIG["planet_radius_max"])
    density_factor = density_model.predict(dist_poly)[0][0]
    density_factor = np.clip(density_factor + np.random.normal(0, 0.1), 0.05, 1.0)
    # --- Biome assignment ---
    biomes = ["desert", "ice", "forest", "ocean", "volcanic", "gas", "rocky", "toxic"]
    biome_type = random.choices(["desert", "ice", "forest"], weights=[0.3, 0.3, 0.4])[0]
    # --- Biome-specific properties ---
    if biome_type == "desert":
        color = (random.randint(200, 255), random.randint(120, 180), random.randint(60, 100))
        density_factor = 0.3 + np.random.uniform(0, 0.2)
        gravity_mult = 0.7
        takeoff_cost = 0.7
    elif biome_type == "ice":
        color = (random.randint(180, 240), random.randint(200, 255), random.randint(220, 255))
        density_factor = 0.2 + np.random.uniform(0, 0.2)
        gravity_mult = 0.5
        takeoff_cost = 1.2
    elif biome_type == "forest":
        color = (random.randint(60, 120), random.randint(180, 255), random.randint(60, 120))
        density_factor = 0.7 + np.random.uniform(0, 0.2)
        gravity_mult = 1.1
        takeoff_cost = 1.0
    else:
        # fallback for other types
        color = (random.randint(100, 200), random.randint(100, 200), random.randint(100, 200))
        gravity_mult = 1.0
        takeoff_cost = 1.0
    mass *= gravity_mult
    # Add more variety to planet colors
    variation = random.randint(-30, 30)
    color = tuple(np.clip([c + variation for c in color], 20, 255))
    has_rings = random.random() < 0.2
    has_moons = random.randint(0, 3)
    return mass, radius, color, density_factor, biome_type, has_rings, has_moons, takeoff_cost

class ParticleSystem:
    """System for managing visual particles."""
    def __init__(self):
        self.particles = []
    def add_particle(self, particle):
        self.particles.append(particle)
    def update(self, dt):
        self.particles = [p for p in self.particles if p.update(dt)]
    def draw(self, surface, camera):
        # Performance optimization: limit particles drawn
        max_particles = 100
        for i, particle in enumerate(self.particles):
            if i >= max_particles:
                break
            particle.draw(surface, camera)
    def add_star_glow(self, position, radius):
        """Add star glow particles."""
        for _ in range(3):
            angle = random.uniform(0, 2 * np.pi)
            distance = radius * random.uniform(0.8, 1.2)
            pos = position + np.array([math.cos(angle), math.sin(angle)]) * distance
            vel = np.array([random.uniform(-5, 5), random.uniform(-5, 5)])
            color = (255, 255, 200, 100)
            lifetime = random.uniform(0.5, 1.0)
            size = random.uniform(1.0, 2.0)
            self.add_particle(Particle(pos, vel, color, lifetime, size))

class Particle:
    """Visual particle effect."""
    def __init__(self, position, velocity, color, lifetime, size):
        self.position = np.array(position, dtype=float)
        self.velocity = np.array(velocity, dtype=float)
        self.color = color
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.size = size
        self.drag = random.uniform(0.9, 0.99)
    def update(self, dt):
        self.position += self.velocity * dt
        self.velocity *= self.drag  # Apply drag
        self.lifetime -= dt
        return self.lifetime > 0
    def draw(self, surface, camera):
        alpha = int(255 * (self.lifetime / self.max_lifetime))
        current_color = self.color[:3] + (alpha,)
        screen_pos = camera.world_to_screen(self.position)
        screen_size = max(1, int(self.size * camera.zoom))
        if not (0 <= screen_pos[0] < camera.screen_width and 0 <= screen_pos[1] < camera.screen_height):
            return
        particle_surface = pygame.Surface((screen_size * 2, screen_size * 2), pygame.SRCALPHA)
        pygame.draw.circle(particle_surface, current_color, (screen_size, screen_size), screen_size)
        surface.blit(particle_surface, (screen_pos[0] - screen_size, screen_pos[1] - screen_size))

class CelestialBody:
    """Base class for all space objects."""
    def __init__(self, position, velocity, mass, radius, color, name="Body"):
        self.position = np.array(position, dtype=float)
        self.velocity = np.array(velocity, dtype=float)
        self.mass = float(mass)
        self.radius = float(radius)
        self.color = color
        self.name = name
        self.acceleration = np.zeros(2, dtype=float)
        self.rotation = 0.0
        self.rotation_speed = random.uniform(-0.5, 0.5)  # Random rotation
        self.particles = []  # For potential effects
    
    def apply_force(self, force):
        if self.mass > 0:
            self.acceleration += force / self.mass
    
    def update_position(self, dt):
        self.velocity += self.acceleration * dt
        self.position += self.velocity * dt
        self.acceleration = np.zeros(2, dtype=float)
        self.rotation = (self.rotation + self.rotation_speed * dt) % 360
    
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
    """Star with solar flares and radiation effects."""
    def __init__(self, position, mass, radius, color=CONFIG["star_color"], name="Star"):
        super().__init__(position, [0, 0], mass, radius, color, name)
        self.flare_timer = 0
        self.flare_interval = random.uniform(10.0, 30.0)
        self.glow_timer = 0
        self.glow_interval = 0.1
        self.radiation_level = random.uniform(0.5, 2.0)
        self.surface_rotation = 0
        # Generate star type
        types = ["Yellow Dwarf", "Red Giant", "Blue Giant", "White Dwarf", "Neutron Star"]
        type_weights = [0.5, 0.3, 0.1, 0.08, 0.02]
        self.star_type = random.choices(types, weights=type_weights)[0]
        
        # Adjust properties based on star type
        if self.star_type == "Red Giant":
            self.color = (255, 100, 50)
            self.radius *= 1.5
        elif self.star_type == "Blue Giant":
            self.color = (100, 150, 255)
            self.radius *= 1.3
            self.mass *= 1.5
        elif self.star_type == "White Dwarf":
            self.color = (220, 220, 255)
            self.radius *= 0.7
            self.mass *= 0.8
        elif self.star_type == "Neutron Star":
            self.color = (150, 150, 255)
            self.radius *= 0.5
            self.mass *= 2.0
    
    def update(self, dt, particle_system):
        self.surface_rotation = (self.surface_rotation + 0.05 * dt) % 360
        
        # Create ambient star glow
        if CONFIG["star_glow_effect"]:
            self.glow_timer -= dt
            if self.glow_timer <= 0:
                particle_system.add_star_glow(self.position, self.radius)
                self.glow_timer = self.glow_interval
        
        # Create occasional solar flares
        self.flare_timer -= dt
        if self.flare_timer <= 0:
            self.create_solar_flare(particle_system)
            self.flare_timer = self.flare_interval
    
    def create_solar_flare(self, particle_system):
        angle = random.uniform(0, 2 * np.pi)
        flare_pos = self.position + np.array([math.cos(angle), math.sin(angle)]) * self.radius
        for _ in range(15):
            direction = np.array([math.cos(angle + random.uniform(-0.5, 0.5)), 
                                math.sin(angle + random.uniform(-0.5, 0.5))])
            velocity = direction * random.uniform(50, 150)
            lifetime = random.uniform(1.0, 3.0)
            size = random.uniform(3.0, 8.0)
            color = (255, 200, 100)
            particle_system.add_particle(Particle(flare_pos.copy(), velocity, color, lifetime, size))
    
    def draw(self, surface, camera):
        screen_pos = camera.world_to_screen(self.position)
        screen_radius = int(self.radius * camera.zoom)
        
        if screen_radius >= 1:
            if -screen_radius < screen_pos[0] < camera.screen_width + screen_radius and \
               -screen_radius < screen_pos[1] < camera.screen_height + screen_radius:
                # Draw glow effect
                glow_surface = pygame.Surface((screen_radius * 4, screen_radius * 4), pygame.SRCALPHA)
                for i in range(3):
                    glow_radius = screen_radius * (1.5 - i * 0.2)
                    alpha = 100 - i * 30
                    pygame.draw.circle(glow_surface, (*self.color[:3], alpha), 
                                      (screen_radius * 2, screen_radius * 2), glow_radius)
                
                # Main star body
                pygame.draw.circle(glow_surface, self.color, 
                                  (screen_radius * 2, screen_radius * 2), screen_radius)
                
                # Draw surface details with subtle rotation
                detail_color = tuple(max(0, c - 50) for c in self.color)
                detail_angle = math.radians(self.surface_rotation)
                
                detail_pos = (screen_radius * 2 + math.cos(detail_angle) * screen_radius * 0.7,
                             screen_radius * 2 + math.sin(detail_angle) * screen_radius * 0.7)
                pygame.draw.circle(glow_surface, detail_color, detail_pos, screen_radius * 0.2)
                
                detail_pos2 = (screen_radius * 2 + math.cos(detail_angle + 2) * screen_radius * 0.5,
                              screen_radius * 2 + math.sin(detail_angle + 2) * screen_radius * 0.5)
                pygame.draw.circle(glow_surface, detail_color, detail_pos2, screen_radius * 0.15)
                
                surface.blit(glow_surface, (screen_pos[0] - screen_radius * 2, screen_pos[1] - screen_radius * 2))

class Planet(CelestialBody):
    """Planet with biome, atmosphere, and other properties."""
    def __init__(self, position, velocity, mass, radius, color, density, biome_type, has_rings=False, moons=0, name="Planet"):
        super().__init__(position, velocity, mass, radius, color, name)
        self.atmospheric_density = density
        self.discovered = False
        self.biome_type = biome_type
        self.has_rings = has_rings
        self.moons = []
        self.ring_color = self.generate_ring_color()
        self.surface_detail = random.random()  # Used for visual variety
        
        # --- Add moons visually (non-landable, purely atmospheric) ---
        self.visual_moons = []
        moon_count = random.randint(1, 3) if random.random() < 0.7 else 0  # 70% chance to have moons
        for i in range(moon_count):
            moon_orbit_radius = radius * random.uniform(2.5, 5.0)
            moon_orbit_period = random.uniform(18, 45)  # seconds for a full orbit
            moon_angle = random.uniform(0, 2 * np.pi)
            moon_radius = radius * random.uniform(0.12, 0.22)
            moon_color = tuple(min(255, max(0, c + random.randint(-40, 40))) for c in color)
            self.visual_moons.append({
                'orbit_radius': moon_orbit_radius,
                'orbit_period': moon_orbit_period,
                'angle': moon_angle,
                'radius': moon_radius,
                'color': moon_color,
                'name': f"{self.name} Moon {i+1}"
            })
        self.visual_moon_time = random.uniform(0, 1000)
        # --- End visual moons ---
    
    def generate_ring_color(self):
        # Generate a ring color that complements the planet color
        base_color = self.color
        brightness = sum(base_color) / 3
        if brightness > 150:  # If planet is bright
            return tuple(max(0, c - random.randint(50, 100)) for c in base_color)
        else:  # If planet is dark
            return tuple(min(255, c + random.randint(50, 100)) for c in base_color)
    
    def update(self, dt):
        super().update_position(dt)
        
        # Update visual moons' orbital positions
        self.visual_moon_time += dt
        for moon in self.visual_moons:
            # Circular orbit for now
            moon['angle'] += (2 * np.pi / moon['orbit_period']) * dt
            moon['angle'] %= 2 * np.pi
        
        # Update moons
        for moon in self.moons:
            # Calculate gravitational force between planet and moon
            force = moon.gravitational_force_from(self, CONFIG["gravity_constant"])
            moon.apply_force(force)
            moon.update_position(dt)
    
    def draw(self, surface, camera):
        screen_pos = camera.world_to_screen(self.position)
        screen_radius = int(self.radius * camera.zoom)
        
        if screen_radius < 1 and self.radius > 0.1:
            if -10 < screen_pos[0] < camera.screen_width + 10 and -10 < screen_pos[1] < camera.screen_height + 10:
                pygame.draw.circle(surface, self.color, screen_pos.astype(int), 1)
        elif screen_radius >= 1:
            if -screen_radius < screen_pos[0] < camera.screen_width + screen_radius and \
               -screen_radius < screen_pos[1] < camera.screen_height + screen_radius:
                # Draw planet rings if present
                if self.has_rings and screen_radius > 5:
                    ring_width = screen_radius * 0.8
                    ring_surface = pygame.Surface((2 * (screen_radius + ring_width), 
                                                 2 * (screen_radius + ring_width)), pygame.SRCALPHA)
                    
                    # Draw oval rings
                    ring_rect = pygame.Rect(ring_width - screen_radius * 0.3, 
                                          ring_width + screen_radius * 0.5, 
                                          2 * screen_radius + screen_radius * 0.6, 
                                          screen_radius)
                    
                    for i in range(3):
                        ring_color = self.ring_color + (150 - i * 50,)
                        pygame.draw.ellipse(ring_surface, ring_color, ring_rect, 
                                           max(1, int(screen_radius * 0.1)))
                        ring_rect.inflate_ip(-screen_radius * 0.2, -screen_radius * 0.1)
                    
                    # Rotate rings based on planet rotation
                    rot_surface = pygame.transform.rotate(ring_surface, self.rotation)
                    rot_rect = rot_surface.get_rect(center=screen_pos)
                    surface.blit(rot_surface, rot_rect.topleft)
                
                # Atmosphere glow for planets with atmosphere
                if self.atmospheric_density > 0.3 and screen_radius > 3:
                    atmo_color = list(self.color)
                    # Make atmosphere color more transparent and brighter
                    atmo_color = [min(255, c + 30) for c in atmo_color] + [80]
                    atmo_radius = int(screen_radius * (1 + 0.2 * self.atmospheric_density))
                    
                    atmo_surface = pygame.Surface((2 * atmo_radius, 2 * atmo_radius), pygame.SRCALPHA)
                    pygame.draw.circle(atmo_surface, atmo_color, (atmo_radius, atmo_radius), atmo_radius)
                    surface.blit(atmo_surface, (screen_pos[0] - atmo_radius, screen_pos[1] - atmo_radius))
                
                # Draw the planet itself
                pygame.draw.circle(surface, self.color, screen_pos.astype(int), screen_radius)
                
                # Add surface details based on biome type if planet is large enough
                if screen_radius > 8:
                    detail_color = tuple(max(0, min(255, c + random.randint(-60, -20))) for c in self.color)
                    
                    if self.biome_type == "desert":
                        # Desert patterns
                        for _ in range(3):
                            offset = np.array([random.uniform(-0.7, 0.7), random.uniform(-0.7, 0.7)]) * screen_radius
                            size = random.uniform(0.1, 0.3) * screen_radius
                            pygame.draw.circle(surface, detail_color, (screen_pos + offset).astype(int), int(size))
                    
                    elif self.biome_type == "gas":
                        # Gas bands
                        for i in range(3):
                            offset_y = (i - 1) * screen_radius * 0.4
                            rect = pygame.Rect(screen_pos[0] - screen_radius, 
                                             screen_pos[1] + offset_y - screen_radius * 0.1,
                                             screen_radius * 2, screen_radius * 0.2)
                            pygame.draw.ellipse(surface, detail_color, rect)
                    
                    elif self.biome_type in ["volcanic", "rocky"]:
                        # Craters/volcanoes
                        for _ in range(4):
                            angle = random.uniform(0, 2 * np.pi)
                            offset = np.array([math.cos(angle), math.sin(angle)]) * random.uniform(0.3, 0.7) * screen_radius
                            size = random.uniform(0.1, 0.3) * screen_radius
                            pygame.draw.circle(surface, detail_color, (screen_pos + offset).astype(int), int(size))
                    
                    elif self.biome_type == "ice":
                        # Ice caps
                        cap_color = (220, 230, 255)
                        cap_size = screen_radius * 0.4
                        pygame.draw.circle(surface, cap_color, 
                                          tuple(map(int, (screen_pos[0], screen_pos[1] - screen_radius * 0.6))), 
                                          int(cap_size))
                        pygame.draw.circle(surface, cap_color, 
                                          tuple(map(int, (screen_pos[0], screen_pos[1] + screen_radius * 0.6))), 
                                          int(cap_size))
                    
                    elif self.biome_type == "ocean":
                        # Ocean continents
                        continent_color = (min(255, self.color[0] + 30), min(255, self.color[1] + 30), min(255, self.color[2] - 20))
                        for _ in range(2):
                            angle = random.uniform(0, 2 * np.pi)
                            offset = np.array([math.cos(angle), math.sin(angle)]) * random.uniform(0.2, 0.5) * screen_radius
                            size = random.uniform(0.2, 0.4) * screen_radius
                            pygame.draw.circle(surface, continent_color, (screen_pos + offset).astype(int), int(size))
                    
                    elif self.biome_type == "forest":
                        # Forest patterns
                        for _ in range(5):
                            angle = random.uniform(0, 2 * np.pi)
                            offset = np.array([math.cos(angle), math.sin(angle)]) * random.uniform(0, 0.7) * screen_radius
                            size = random.uniform(0.05, 0.15) * screen_radius
                            pygame.draw.circle(surface, detail_color, (screen_pos + offset).astype(int), int(size))
                    
                    elif self.biome_type == "toxic":
                        # Toxic swirls
                        swirl_color = (min(255, self.color[0] - 50), min(255, self.color[1] + 40), min(255, self.color[2] - 50))
                        for i in range(3):
                            angle = i * 2.1
                            dist = 0.5 * screen_radius
                            offset = np.array([math.cos(angle), math.sin(angle)]) * dist
                            size = 0.2 * screen_radius
                            pygame.draw.circle(surface, swirl_color, (screen_pos + offset).astype(int), int(size))
                
                # Draw discovery indicator if newly discovered
                if self.discovered and hasattr(self, 'discovery_timer') and self.discovery_timer > 0:
                    indicator_radius = screen_radius + 10
                    alpha = int(min(255, self.discovery_timer * 200))
                    indicator_color = (255, 255, 200, alpha)
                    indicator_surface = pygame.Surface((indicator_radius * 2, indicator_radius * 2), pygame.SRCALPHA)
                    pygame.draw.circle(indicator_surface, indicator_color, 
                                      (indicator_radius, indicator_radius), indicator_radius, 2)
                    surface.blit(indicator_surface, 
                                (screen_pos[0] - indicator_radius, screen_pos[1] - indicator_radius))
                # --- Draw visual moons ---
                for moon in self.visual_moons:
                    moon_angle = moon['angle']
                    moon_orbit_radius = moon['orbit_radius'] * camera.zoom
                    moon_pos = screen_pos + np.array([math.cos(moon_angle), math.sin(moon_angle)]) * moon_orbit_radius
                    moon_radius = int(moon['radius'] * camera.zoom)
                    if moon_radius < 1:
                        moon_radius = 1
                    pygame.draw.circle(surface, moon['color'], moon_pos.astype(int), moon_radius)
                # --- End visual moons ---
        
        # Draw moons after planet
        for moon in self.moons:
            moon.draw(surface, camera)

class Moon(CelestialBody):
    """Moon orbiting a planet."""
    def __init__(self, position, velocity, mass, radius, color, parent_planet, name="Moon"):
        super().__init__(position, velocity, mass, radius, color, name)
        self.parent_planet = parent_planet
        self.orbit_distance = np.linalg.norm(position - parent_planet.position)
        self.orbit_angle = math.atan2(position[1] - parent_planet.position[1], 
                                     position[0] - parent_planet.position[0])
        self.craters = []
        
        # Generate random craters
        crater_count = random.randint(2, 5)
        for _ in range(crater_count):
            angle = random.uniform(0, 2 * np.pi)
            distance = random.uniform(0.2, 0.8) * radius
            size = random.uniform(0.1, 0.3) * radius
            self.craters.append((angle, distance, size))
    
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
                
                # Draw craters if moon is large enough
                if screen_radius > 3:
                    crater_color = tuple(max(0, c - 30) for c in self.color)
                    for angle, distance, size in self.craters:
                        current_angle = angle + self.rotation
                        offset = np.array([math.cos(current_angle), math.sin(current_angle)]) * distance * camera.zoom
                        crater_size = size * camera.zoom
                        pygame.draw.circle(surface, crater_color, 
                                          (screen_pos + offset).astype(int), int(crater_size))

class Asteroid(CelestialBody):
    """Small asteroid object that can be part of an asteroid field."""
    def __init__(self, position, velocity, mass, radius, color=CONFIG["asteroid_color"], resource_type="none"):
        super().__init__(position, velocity, mass, radius, color, "Asteroid")
        self.resource_type = resource_type
        self.rotation_speed = random.uniform(-2, 2)  # Faster rotation
        self.shape_points = self.generate_shape_points()
        self.collision_damage = mass * 0.5  # Damage caused on collision
    
    def generate_shape_points(self):
        """Generate irregular asteroid shape."""
        point_count = random.randint(6, 10)
        points = []
        for i in range(point_count):
            angle = i * (2 * np.pi / point_count)
            distance = self.radius * random.uniform(0.7, 1.3)
            points.append((math.cos(angle) * distance, math.sin(angle) * distance))
        return points
    
    def draw(self, surface, camera):
        screen_pos = camera.world_to_screen(self.position)
        screen_radius = int(self.radius * camera.zoom)
        
        if screen_radius < 1:
            if -10 < screen_pos[0] < camera.screen_width + 10 and -10 < screen_pos[1] < camera.screen_height + 10:
                pygame.draw.circle(surface, self.color, screen_pos.astype(int), 1)
        else:
            if -screen_radius < screen_pos[0] < camera.screen_width + screen_radius and \
               -screen_radius < screen_pos[1] < camera.screen_height + screen_radius:
                # Draw irregular asteroid shape
                rotated_points = []
                rot_angle = math.radians(self.rotation)
                for x, y in self.shape_points:
                    # Rotate point
                    rotated_x = x * math.cos(rot_angle) - y * math.sin(rot_angle)
                    rotated_y = x * math.sin(rot_angle) + y * math.cos(rot_angle)
                    # Scale and position
                    screen_x = screen_pos[0] + rotated_x * camera.zoom
                    screen_y = screen_pos[1] + rotated_y * camera.zoom
                    rotated_points.append((screen_x, screen_y))
                
                if len(rotated_points) >= 3:
                    pygame.draw.polygon(surface, self.color, rotated_points)

class BlackHole(CelestialBody):
    """Black hole with strong gravitational pull and visual distortion."""
    def __init__(self, position, mass=1e8, radius=80):
        color = (20, 20, 40)  # Almost black with a hint of blue
        super().__init__(position, [0, 0], mass, radius, color, "Black Hole")
        self.event_horizon_radius = radius * 0.4
        self.accretion_disk_color = (100, 50, 150)  # Purple-ish
        self.distortion_strength = 2.0
        self.particles = []
        self.particle_timer = 0
    
    def update(self, dt, particle_system):
        self.particle_timer -= dt
        if self.particle_timer <= 0:
            self.add_accretion_particles(particle_system)
            self.particle_timer = 0.1
    
    def add_accretion_particles(self, particle_system):
        angle = random.uniform(0, 2 * np.pi)
        distance = self.radius * random.uniform(0.5, 0.9)
        pos = self.position + np.array([math.cos(angle), math.sin(angle)]) * distance
        
        # Particles orbit around the black hole
        orbit_dir = np.array([-math.sin(angle), math.cos(angle)])
        orbit_speed = np.sqrt(CONFIG["gravity_constant"] * self.mass / distance) * 0.5
        vel = orbit_dir * orbit_speed
        
        color = (100 + random.randint(0, 155), 50 + random.randint(0, 100), 150 + random.randint(0, 105))
        lifetime = random.uniform(1.0, 3.0)
        size = random.uniform(2.0, 5.0)
        
        particle_system.add_particle(Particle(pos, vel, color, lifetime, size))
    
    def draw(self, surface, camera):
        screen_pos = camera.world_to_screen(self.position)
        screen_radius = int(self.radius * camera.zoom)
        event_screen_radius = int(self.event_horizon_radius * camera.zoom)
        
        if -screen_radius < screen_pos[0] < camera.screen_width + screen_radius and \
           -screen_radius < screen_pos[1] < camera.screen_height + screen_radius:
            
            # Draw accretion disk (glowing ring around black hole)
            for i in range(3):
                disk_radius = screen_radius * (0.6 + i * 0.15)
                disk_color = list(self.accretion_disk_color)
                disk_color[0] = min(255, disk_color[0] + i * 30)
                disk_color[1] = min(255, disk_color[1] + i * 15)
                disk_color.append(150 - i * 40)  # Add alpha
                
                disk_surface = pygame.Surface((disk_radius * 2, disk_radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(disk_surface, disk_color, (disk_radius, disk_radius), disk_radius, 
                                  max(1, int(disk_radius * 0.2)))
                
                # Add rotation to disk
                rot_angle = (self.rotation * (i + 1) * 0.2) % 360
                rot_surface = pygame.transform.rotate(disk_surface, rot_angle)
                rot_rect = rot_surface.get_rect(center=screen_pos)
                surface.blit(rot_surface, rot_rect.topleft)
            
            # Draw event horizon (the actual black hole)
            pygame.draw.circle(surface, (0, 0, 0), screen_pos.astype(int), event_screen_radius)
            
            # Draw subtle glow at the edge of event horizon
            glow_color = (50, 20, 80, 100)
            glow_surface = pygame.Surface((event_screen_radius * 2.2, event_screen_radius * 2.2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surface, glow_color, 
                              (event_screen_radius * 1.1, event_screen_radius * 1.1), 
                              event_screen_radius * 1.1)
            surface.blit(glow_surface, 
                        (screen_pos[0] - event_screen_radius * 1.1, screen_pos[1] - event_screen_radius * 1.1))

class Wormhole(CelestialBody):
    """Wormhole that can teleport objects to another location."""
    def __init__(self, position, exit_position, radius=120):
        color = (100, 200, 255)  # Cyan-ish blue
        super().__init__(position, [0, 0], 1e5, radius, color, "Wormhole")
        self.exit_position = np.array(exit_position, dtype=float)
        self.exit_angle = 0
        self.rotation_speed = 1.0
        self.portal_effect_timer = 0
        self.teleport_cooldown = 0
        self.active = True
    
    def update(self, dt, particle_system):
        self.rotation += self.rotation_speed * dt
        self.exit_angle -= self.rotation_speed * dt  # Rotate in opposite direction
        
        # Add wormhole particles
        self.portal_effect_timer -= dt
        if self.portal_effect_timer <= 0:
            self.add_portal_particles(particle_system)
            self.portal_effect_timer = 0.1
        
        # Update teleport cooldown
        if self.teleport_cooldown > 0:
            self.teleport_cooldown = max(0, self.teleport_cooldown - dt)
    
    def add_portal_particles(self, particle_system):
        if not self.active:
            return
            
        for _ in range(2):
            angle = random.uniform(0, 2 * np.pi)
            distance = self.radius * random.uniform(0.3, 0.7)
            pos = self.position + np.array([math.cos(angle), math.sin(angle)]) * distance
            
            # Particles spiral toward center
            center_dir = (self.position - pos) / max(0.1, np.linalg.norm(self.position - pos))
            tangent_dir = np.array([-center_dir[1], center_dir[0]])
            vel = center_dir * random.uniform(10, 30) + tangent_dir * random.uniform(5, 15)
            
            color = (
                100 + random.randint(0, 155), 
                150 + random.randint(0, 105), 
                200 + random.randint(0, 55), 
                200
            )
            lifetime = random.uniform(0.5, 1.5)
            size = random.uniform(2.0, 4.0)
            
            particle_system.add_particle(Particle(pos, vel, color, lifetime, size))
    
    def draw(self, surface, camera):
        if not self.active:
            return
            
        screen_pos = camera.world_to_screen(self.position)
        screen_radius = int(self.radius * camera.zoom)
        
        if -screen_radius < screen_pos[0] < camera.screen_width + screen_radius and \
           -screen_radius < screen_pos[1] < camera.screen_height + screen_radius:
            
            # Create wormhole surface with spiral effect
            portal_surface = pygame.Surface((screen_radius * 2, screen_radius * 2), pygame.SRCALPHA)
            
            # Draw concentric rings with spiral effect
            for i in range(10, 0, -1):
                radius_factor = i / 10
                ring_radius = int(screen_radius * radius_factor)
                if ring_radius < 1:
                    continue
                    
                # Adjust color based on depth
                depth_factor = i / 10
                color = (
                    int(self.color[0] * depth_factor),
                    int(self.color[1] * depth_factor),
                    int(min(255, self.color[2] * (1.5 - depth_factor)))
                )
                
                # Draw spiral segments
                segments = 8
                for s in range(segments):
                    start_angle = math.radians(s * (360 / segments) + self.rotation * (i * 3))
                    end_angle = math.radians((s + 0.8) * (360 / segments) + self.rotation * (i * 3))
                    
                    # Calculate arc points
                    arc_points = []
                    center = (screen_radius, screen_radius)
                    arc_points.append(center)
                    
                    # Add points along the arc
                    steps = 10
                    for step in range(steps + 1):
                        angle = start_angle + (end_angle - start_angle) * (step / steps)
                        x = center[0] + math.cos(angle) * ring_radius
                        y = center[1] + math.sin(angle) * ring_radius
                        arc_points.append((x, y))
                    
                    # Close the arc back to center
                    arc_points.append(center)
                    
                    # Draw the filled arc segment
                    if len(arc_points) > 2:
                        pygame.draw.polygon(portal_surface, color, arc_points)
            
            # Draw dark center
            pygame.draw.circle(portal_surface, (0, 0, 30), (screen_radius, screen_radius), 
                              int(screen_radius * 0.2))
            
            # Create final effect with alpha for glow
            for i in range(3):
                glow_radius = screen_radius * (1.2 - i * 0.1)
                alpha = 80 - i * 20
                glow_color = (*self.color, alpha)
                glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(glow_surface, glow_color, (glow_radius, glow_radius), glow_radius, 2)
                portal_surface.blit(glow_surface, 
                                   (screen_radius - glow_radius, screen_radius - glow_radius))
            
            # Apply wormhole surface to main surface
            surface.blit(portal_surface, (screen_pos[0] - screen_radius, screen_pos[1] - screen_radius))
            
            # Draw exit marker on the minimap
            exit_screen_pos = camera.world_to_screen(self.exit_position)
            if camera.is_on_screen(exit_screen_pos, screen_radius):
                exit_surface = pygame.Surface((screen_radius * 2, screen_radius * 2), pygame.SRCALPHA)
                exit_color = (self.color[0], self.color[1], self.color[2], 100)
                pygame.draw.circle(exit_surface, exit_color, (screen_radius, screen_radius), 
                                  int(screen_radius * 0.8))
                surface.blit(exit_surface, 
                            (exit_screen_pos[0] - screen_radius, exit_screen_pos[1] - screen_radius))
    
    def teleport(self, object):
        """Teleport an object to the exit location."""
        if not self.active or self.teleport_cooldown > 0:
            return False
        
        # Calculate distance to wormhole
        distance = np.linalg.norm(object.position - self.position)
        if distance < self.radius * 0.5:
            # Preserve velocity direction but apply a speed boost
            velocity_direction = object.velocity / (np.linalg.norm(object.velocity) or 1)
            object.position = self.exit_position.copy()
            object.velocity = velocity_direction * (np.linalg.norm(object.velocity) * 1.2)
            
            # Set cooldown
            self.teleport_cooldown = 2.0
            return True
        
        return False

class Pulsar(CelestialBody):
    """Rotating neutron star emitting energy beams."""
    def __init__(self, position, mass=8e7, radius=60):
        color = (150, 200, 255)  # Bright blue-white
        super().__init__(position, [0, 0], mass, radius, color, "Pulsar")
        self.rotation_speed = 10.0  # Fast rotation
        self.beam_length = radius * 10
        self.beam_width = radius * 0.5
        self.pulse_interval = 1.0
        self.pulse_timer = 0
        self.beam_angle = random.uniform(0, 2 * np.pi)
        self.emission_active = False
        self.emission_duration = 0.2
        self.emission_timer = 0
    
    def update(self, dt, particle_system):
        self.rotation += self.rotation_speed * dt
        
        # Update beam angle
        self.beam_angle = math.radians(self.rotation)
        
        # Pulsar emission cycle
        self.pulse_timer -= dt
        if self.pulse_timer <= 0:
            self.emission_active = True
            self.emission_timer = self.emission_duration
            self.pulse_timer = self.pulse_interval
            self.emit_energy_beam(particle_system)
        
        if self.emission_active:
            self.emission_timer -= dt
            if self.emission_timer <= 0:
                self.emission_active = False
    
    def emit_energy_beam(self, particle_system):
        """Emit particles along the energy beam."""
        beam_dir1 = np.array([math.cos(self.beam_angle), math.sin(self.beam_angle)])
        beam_dir2 = -beam_dir1  # Opposite direction
        
        for direction in [beam_dir1, beam_dir2]:
            for i in range(20):
                distance = self.radius * (0.8 + i * 0.5)
                pos = self.position + direction * distance
                
                # Add some spread perpendicular to the beam
                perp_dir = np.array([-direction[1], direction[0]])
                spread = perp_dir * random.uniform(-1, 1) * self.beam_width * 0.2
                
                # Calculate velocity - particles move outward
                vel = direction * random.uniform(200, 400) + spread
                
                # Bright beam particles
                color = (200, 230, 255)
                lifetime = random.uniform(0.2, 0.5)
                size = random.uniform(2.0, 4.0)
                
                particle_system.add_particle(Particle(pos, vel, color, lifetime, size))
    
    def draw(self, surface, camera):
        screen_pos = camera.world_to_screen(self.position)
        screen_radius = int(self.radius * camera.zoom)
        
        if -screen_radius < screen_pos[0] < camera.screen_width + screen_radius and \
           -screen_radius < screen_pos[1] < camera.screen_height + screen_radius:
            
            # Draw energy beams when active
            if self.emission_active:
                beam_dir1 = np.array([math.cos(self.beam_angle), math.sin(self.beam_angle)])
                beam_dir2 = -beam_dir1
                
                beam_length = self.beam_length * camera.zoom
                beam_width = self.beam_width * camera.zoom
                
                for direction in [beam_dir1, beam_dir2]:
                    # Create beam surface
                    beam_rect = pygame.Surface((beam_length, beam_width), pygame.SRCALPHA)
                    
                    # Draw gradient beam
                    for i in range(10):
                        alpha = 200 - i * 20
                        if alpha <= 0:
                            continue
                        
                        color = (200, 230, 255, alpha)
                        rect_width = beam_width * (1.0 - i * 0.1)
                        rect_y = (beam_width - rect_width) / 2
                        pygame.draw.rect(beam_rect, color, 
                                        (0, rect_y, beam_length, rect_width))
                    
                    # Rotate and position beam
                    angle = math.degrees(math.atan2(direction[1], direction[0]))
                    rotated_beam = pygame.transform.rotate(beam_rect, -angle)
                    beam_rect = rotated_beam.get_rect(center=screen_pos)
                    surface.blit(rotated_beam, beam_rect.topleft)
            
            # Draw pulsar body
            glow_radius = screen_radius * 1.5
            glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
            
            # Add glow
            for i in range(3):
                alpha = 150 - i * 40
                color = (*self.color, alpha)
                pygame.draw.circle(glow_surface, color, 
                                  (glow_radius, glow_radius), 
                                  int(glow_radius * (1.0 - i * 0.2)))
            
            # Core
            pygame.draw.circle(glow_surface, self.color, 
                              (glow_radius, glow_radius), screen_radius)
            
            surface.blit(glow_surface, 
                        (screen_pos[0] - glow_radius, screen_pos[1] - glow_radius))

class SpaceStation(CelestialBody):
    """Space station with docking capabilities and missions."""
    def __init__(self, position, radius=100, name="Space Station Alpha"):
        color = (150, 150, 180)
        super().__init__(position, [0, 0], 5e4, radius, color, name)
        self.rotation_speed = 0.2
        self.docking_available = True
        self.services = ["refuel", "repair", "missions", "trade"]
        self.mission_list = []
        self.upgrade_inventory = self.generate_upgrades()
        
        # Visual properties
        self.module_count = random.randint(3, 6)
        self.modules = []
        self.generate_modules()
        
        # Create some ambient particles
        self.particle_timer = 0
        self.particle_interval = 0.5
    
    def generate_modules(self):
        """Generate visual modules for the station."""
        for i in range(self.module_count):
            angle = i * (2 * np.pi / self.module_count)
            distance = self.radius * 0.7
            size = self.radius * random.uniform(0.2, 0.4)
            shape = random.choice(["circle", "rectangle"])
            self.modules.append({
                "angle": angle,
                "distance": distance,
                "size": size,
                "shape": shape,
                "color": (min(255, self.color[0] + random.randint(-20, 20)),
                         min(255, self.color[1] + random.randint(-20, 20)),
                         min(255, self.color[2] + random.randint(-20, 20)))
            })
    
    def generate_upgrades(self):
        """Generate available upgrades."""
        upgrades = {}
        for item_type in CONFIG["item_types"]:
            level = random.randint(1, 3)
            cost = CONFIG["upgrade_cost_base"] * level * random.uniform(0.8, 1.2)
            upgrades[item_type] = {"level": level, "cost": int(cost)}
        return upgrades
    
    def generate_missions(self):
        """Generate available missions."""
        mission_count = random.randint(2, 5)
        self.mission_list = []
        
        for i in range(mission_count):
            mission_type = random.choice(CONFIG["mission_types"])
            target_count = random.randint(1, 5)
            reward = random.randint(CONFIG["mission_reward_min"], CONFIG["mission_reward_max"])
            time_limit = random.randint(CONFIG["mission_time_min"], CONFIG["mission_time_max"])
            
            self.mission_list.append({
                "id": i,
                "type": mission_type,
                "target_count": target_count,
                "reward": reward,
                "time_limit": time_limit,
                "description": self.generate_mission_description(mission_type, target_count)
            })
    
    def generate_mission_description(self, mission_type, count):
        """Generate mission description text."""
        if mission_type == "collect":
            return f"Collect {count} resource samples from the nearby asteroid field."
        elif mission_type == "destroy":
            return f"Eliminate {count} enemy ships threatening our trade routes."
        elif mission_type == "explore":
            return f"Explore {count} uncharted locations in this system."
        elif mission_type == "deliver":
            return f"Deliver vital supplies to {count} outposts."
        elif mission_type == "rescue":
            return f"Rescue {count} escape pods from the abandoned station."
        elif mission_type == "defend":
            return f"Defend the outpost against {count} waves of attackers."
        elif mission_type == "research":
            return f"Collect {count} samples from the anomaly for research."
        return f"Complete {count} objectives."
    
    def update(self, dt, particle_system):
        self.rotation += self.rotation_speed * dt
        
        # Emit ambient particles
        self.particle_timer -= dt
        if self.particle_timer <= 0:
            self.add_station_particles(particle_system)
            self.particle_timer = self.particle_interval
    
    def add_station_particles(self, particle_system):
        """Add ambient particles around the station."""
        for _ in range(2):
            module_index = random.randrange(len(self.modules))
            module = self.modules[module_index]
            
            # Calculate position
            angle = module["angle"] + self.rotation
            distance = module["distance"] + module["size"] * 0.8
            
            offset = np.array([math.cos(angle), math.sin(angle)]) * distance
            pos = self.position + offset
            
            vel = np.array([random.uniform(-10, 10), random.uniform(-10, 10)])
            color = (200, 200, 200, 150)
            lifetime = random.uniform(0.5, 1.5)
            size = random.uniform(1.0, 2.0)
            
            particle_system.add_particle(Particle(pos, vel, color, lifetime, size))
    
    def draw(self, surface, camera):
        screen_pos = camera.world_to_screen(self.position)
        screen_radius = int(self.radius * camera.zoom)
        
        if -screen_radius < screen_pos[0] < camera.screen_width + screen_radius and \
           -screen_radius < screen_pos[1] < camera.screen_height + screen_radius:
            
            # Draw station base (ring)
            pygame.draw.circle(surface, self.color, screen_pos.astype(int), screen_radius, 
                              int(screen_radius * 0.2))
            
            # Draw the modules
            for module in self.modules:
                angle = module["angle"] + self.rotation
                distance = module["distance"] * camera.zoom
                size = module["size"] * camera.zoom
                
                module_pos = screen_pos + np.array([math.cos(angle), math.sin(angle)]) * distance
                
                if module["shape"] == "circle":
                    pygame.draw.circle(surface, module["color"], module_pos.astype(int), int(size))
                else:  # rectangle
                    rect_size = int(size * 1.5)
                    rect = pygame.Rect(module_pos[0] - size/2, module_pos[1] - size/2, size, rect_size)
                    rotated_surface = pygame.Surface((size, rect_size), pygame.SRCALPHA)
                    pygame.draw.rect(rotated_surface, module["color"], (0, 0, size, rect_size))
                    
                    # Rotate the rectangle
                    rot_surface = pygame.transform.rotate(rotated_surface, math.degrees(-angle))
                    rot_rect = rot_surface.get_rect(center=module_pos)
                    surface.blit(rot_surface, rot_rect.topleft)
            
            # Draw central hub
            central_radius = int(screen_radius * 0.4)
            pygame.draw.circle(surface, self.color, screen_pos.astype(int), central_radius)
            
            # Draw docking lights if available
            if self.docking_available:
                lights_radius = central_radius * 1.2
                for i in range(6):
                    light_angle = i * (math.pi / 3) + self.rotation * 0.5
                    light_pos = screen_pos + np.array([math.cos(light_angle), math.sin(light_angle)]) * lights_radius
                    light_color = (0, 255, 0) if i % 2 == 0 else (255, 255, 0)
                    pygame.draw.circle(surface, light_color, light_pos.astype(int), int(central_radius * 0.15))

class Nebula:
    """Colorful gas cloud with visual effects."""
    def __init__(self, position, radius=2000):
        self.position = np.array(position, dtype=float)
        self.radius = radius
        
        # Generate random properties
        r = random.randint(50, 200)
        g = random.randint(50, 200)
        b = random.randint(50, 200)
        self.color = (r, g, b)
        
        # Generate cloud clusters
        self.clusters = []
        cluster_count = random.randint(5, 15)
        for _ in range(cluster_count):
            angle = random.uniform(0, 2 * np.pi)
            distance = radius * random.uniform(0.1, 0.9)
            cluster_pos = self.position + np.array([math.cos(angle), math.sin(angle)]) * distance
            cluster_radius = radius * random.uniform(0.1, 0.4)
            cluster_color = (
                min(255, r + random.randint(-30, 30)),
                min(255, g + random.randint(-30, 30)),
                min(255, b + random.randint(-30, 30))
            )
            self.clusters.append({
                "position": cluster_pos,
                "radius": cluster_radius,
                "color": cluster_color,
                "density": random.uniform(0.5, 1.0)
            })
        
        # Effects on ships
        self.visibility_reduction = random.uniform(0.3, 0.7)
        self.speed_reduction = random.uniform(0.1, 0.3)
        self.damage_chance = random.uniform(0, 0.05)  # Chance of damaging ship per second
        
        # Animation
        self.animation_offset = random.uniform(0, 2 * np.pi)
        self.animation_speed = random.uniform(0.05, 0.2)
    
    def is_inside(self, position):
        """Check if a position is inside the nebula."""
        distance = np.linalg.norm(position - self.position)
        return distance < self.radius
    
    def update(self, dt):
        """Update nebula animation."""
        self.animation_offset += self.animation_speed * dt
    
    def draw(self, surface, camera):
        screen_pos = camera.world_to_screen(self.position)
        screen_radius = int(self.radius * camera.zoom)
        
        # Only draw if on screen
        if screen_radius < 1:
            return
            
        if not (-screen_radius < screen_pos[0] < camera.screen_width + screen_radius and \
                -screen_radius < screen_pos[1] < camera.screen_height + screen_radius):
            return
        
        # Draw nebula clusters
        for cluster in self.clusters:
            cluster_screen_pos = camera.world_to_screen(cluster["position"])
            cluster_screen_radius = int(cluster["radius"] * camera.zoom)
            
            if cluster_screen_radius < 1:
                continue
                
            # Create cluster surface with gradient
            cluster_surface = pygame.Surface((cluster_screen_radius * 2, cluster_screen_radius * 2), pygame.SRCALPHA)
            
            # Draw multiple transparent circles with decreasing radius for gradient effect
            for i in range(5):
                fade_factor = 1.0 - (i / 5)
                radius_factor = 1.0 - (i * 0.15)
                
                # Apply animation oscillation
                radius_animation = 0.1 * math.sin(self.animation_offset + i * 0.5)
                radius_factor += radius_animation
                
                gradient_radius = int(cluster_screen_radius * radius_factor)
                alpha = int(100 * fade_factor * cluster["density"])
                color = cluster["color"] + (alpha,)
                
                pygame.draw.circle(cluster_surface, color, 
                                  (cluster_screen_radius, cluster_screen_radius), gradient_radius)
            
            # Add some "stars" inside the nebula for visual interest
            for _ in range(3):
                star_pos = (random.randint(0, cluster_screen_radius * 2), 
                           random.randint(0, cluster_screen_radius * 2))
                star_radius = random.randint(1, 3)
                pygame.draw.circle(cluster_surface, (255, 255, 255, 150), star_pos, star_radius)
            
            # Apply to main surface
            surface.blit(cluster_surface, 
                        (cluster_screen_pos[0] - cluster_screen_radius, 
                         cluster_screen_pos[1] - cluster_screen_radius))

class Camera:
    """Camera system with zoom and pan capabilities."""
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.position = np.array([0, 0], dtype=float)
        self.zoom = 1.0
        self.target = None
    
    def world_to_screen(self, world_pos):
        """Convert world coordinates to screen coordinates."""
        relative_pos = (world_pos - self.position) * self.zoom
        screen_pos = np.array([
            self.screen_width / 2 + relative_pos[0],
            self.screen_height / 2 + relative_pos[1]
        ])
        return screen_pos
    
    def screen_to_world(self, screen_pos):
        """Convert screen coordinates to world coordinates."""
        relative_pos = np.array([
            screen_pos[0] - self.screen_width / 2,
            screen_pos[1] - self.screen_height / 2
        ])
        world_pos = self.position + relative_pos / self.zoom
        return world_pos
    
    def set_target(self, target):
        """Set camera to follow a target."""
        self.target = target
    
    def update(self):
        """Update camera position to follow target if set."""
        if self.target:
            self.position = self.target.position.copy()
    
    def move(self, direction):
        """Move camera in a direction."""
        self.position += direction / self.zoom * CONFIG["camera_speed"]
    
    def zoom_in(self):
        """Zoom camera in."""
        self.zoom = min(CONFIG["max_zoom"], self.zoom * CONFIG["zoom_speed"])
    
    def zoom_out(self):
        """Zoom camera out."""
        self.zoom = max(CONFIG["min_zoom"], self.zoom / CONFIG["zoom_speed"])
    
    def is_on_screen(self, screen_pos, buffer=0):
        """Check if a screen position is visible."""
        return (-buffer <= screen_pos[0] <= self.screen_width + buffer and
                -buffer <= screen_pos[1] <= self.screen_height + buffer)

class Rocket(CelestialBody):
    """Player-controlled rocket with physics and fuel."""
    def __init__(self, position, velocity=[0, 0]):
        super().__init__(position, velocity, CONFIG["rocket_mass"], 10, CONFIG["rocket_color"], "Player")
        self.thrust = CONFIG["rocket_thrust"]
        self.rotation_speed = CONFIG["rocket_rotation_speed"]
        self.angle = 0  # Rotation angle (radians)
        self.thrusting = False
        self.turning_left = False
        self.turning_right = False
        self.fuel = CONFIG["rocket_initial_fuel"]
        self.max_fuel = CONFIG["rocket_initial_fuel"]
        
        # Landing and takeoff system
        self.landed_on_planet = None
        self.takeoff_timer = 0
        self.takeoff_duration = 5.0  # 5 seconds to takeoff
        self.takeoff_fuel_cost = 100
        self.takeoff_thrust_multiplier = 5.0  # Stronger takeoff for smooth launch
        self.is_taking_off = False
        self.landing_velocity = 0  # Track landing velocity for damage
        
        # Combat properties
        self.health = 100
        self.max_health = 100
        self.shield = 0
        self.max_shield = 50
        self.weapon_level = 1
        self.engine_level = 1
        self.scanner_level = 1
        self.fire_rate_timer = 0
        self.damage_flash_timer = 0
        
        # Inventory and mission
        self.credits = 500
        self.current_mission = None
        self.mission_progress = 0
        self.mission_timer = 0
        self.mission_targets = []
        self.collected_items = []
        self.current_quest = None
        self.completed_quests = []
        
        # Trajectory prediction
        self.trajectory_points = []
        self.trajectory_update_timer = 0
        # --- Rocket sprite assets ---
        self._load_sprites()
        self.flame_anim_index = 0
        self.flame_anim_timer = 0
        self.flame_anim_speed = 0.08  # seconds per frame
    def _load_sprites(self):
        import os
        asset_dir = os.path.join("assets", "rocket")
        scale_factor = 2.0
        try:
            img = pygame.image.load(os.path.join(asset_dir, "rocket.png")).convert_alpha()
            # Rotate 90° clockwise so nose points upward
            img = pygame.transform.rotate(img, -90)
            w, h = img.get_size()
            self.rocket_img = pygame.transform.scale(img, (int(w * scale_factor), int(h * scale_factor)))
        except Exception:
            self.rocket_img = None
        self.flame_imgs = []
        for fname in ["leftflame.png", "centreflame.png", "rightflame.png", "centreflame.png"]:
            try:
                img = pygame.image.load(os.path.join(asset_dir, fname)).convert_alpha()
                w, h = img.get_size()
                img_scaled = pygame.transform.scale(img, (int(w * scale_factor), int(h * scale_factor)))
            except Exception:
                img_scaled = None
            self.flame_imgs.append(img_scaled)
    def draw(self, surface, camera):
        screen_pos = camera.world_to_screen(self.position)
        screen_radius = max(3, int(self.radius * camera.zoom))
        if not (-screen_radius < screen_pos[0] < camera.screen_width + screen_radius and \
                -screen_radius < screen_pos[1] < camera.screen_height + screen_radius):
            return
        direction = np.array([math.cos(self.angle), math.sin(self.angle)])
        rocket_length = screen_radius * 3
        # --- Sprite-based rendering ---
        if self.rocket_img:
            # Draw rocket body
            rocket_scale = rocket_length / self.rocket_img.get_height()
            rocket_img_scaled = pygame.transform.rotozoom(self.rocket_img, -math.degrees(self.angle), rocket_scale)
            rocket_rect = rocket_img_scaled.get_rect(center=screen_pos)
            surface.blit(rocket_img_scaled, rocket_rect)
            # Draw basic flame if thrusting
            if self.thrusting and self.fuel > 0:
                # Flame at the tail (opposite to direction)
                flame_offset = -direction * rocket_length * 0.5
                flame_pos = screen_pos + flame_offset
                # Flicker effect
                flame_length = rocket_length * 0.7 * (0.8 + 0.4 * (pygame.time.get_ticks() % 200) / 200)
                flame_width = rocket_length * 0.3
                flame_color = (255, random.randint(120, 200), 0)
                flame_points = [
                    flame_pos + direction * flame_length * 0.2,
                    flame_pos - direction * flame_length,
                    flame_pos + np.array([-direction[1], direction[0]]) * flame_width * 0.5,
                    flame_pos + np.array([direction[1], -direction[0]]) * flame_width * 0.5
                ]
                pygame.draw.polygon(surface, flame_color, [p.astype(int) for p in flame_points])
        else:
            # Fallback: draw polygon rocket
            nose = screen_pos + direction * rocket_length
            left_wing = screen_pos - direction * rocket_length/2 + direction * rocket_width
            right_wing = screen_pos - direction * rocket_length/2 - direction * rocket_width
            tail = screen_pos - direction * rocket_length/2
            color = self.color
            if self.damage_flash_timer > 0:
                flash_intensity = min(255, int(255 * self.damage_flash_timer / CONFIG["damage_visual_time"]))
                color = (255, flash_intensity, flash_intensity)
            pygame.draw.polygon(surface, color, [nose, left_wing, tail, right_wing])
            if self.thrusting and self.fuel > 0:
                flame_length = rocket_length * random.uniform(0.7, 1.0)
                flame_points = [
                    tail,
                    tail - direction * flame_length + direction * rocket_width/2,
                    tail - direction * flame_length * 1.2,
                    tail - direction * flame_length - direction * rocket_width/2
                ]
                flame_color = (255, random.randint(100, 200), 0)
                pygame.draw.polygon(surface, flame_color, flame_points)
        # Draw takeoff progress if taking off
        if self.is_taking_off and self.landed_on_planet:
            progress = self.takeoff_timer / self.takeoff_duration
            bar_width = rocket_length * 2
            bar_height = 6
            bar_x = screen_pos[0] - bar_width/2
            bar_y = screen_pos[1] - rocket_length - 15
            pygame.draw.rect(surface, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height))
            progress_width = int(bar_width * progress)
            pygame.draw.rect(surface, (0, 255, 0), (bar_x, bar_y, progress_width, bar_height))
            pygame.draw.rect(surface, (200, 200, 200), (bar_x, bar_y, bar_width, bar_height), 2)
            font = pygame.font.SysFont(None, 20)
            text = font.render(f"TAKEOFF: {int(progress * 100)}%", True, (255, 255, 255))
            text_rect = text.get_rect(center=(screen_pos[0], bar_y - 10))
            surface.blit(text, text_rect)
        # Draw shield if active
        if self.shield > 0:
            shield_radius = rocket_length * 1.5
            shield_alpha = int(100 * (self.shield / self.max_shield) + 50)
            shield_color = (100, 150, 255, shield_alpha)
            shield_surface = pygame.Surface((shield_radius * 2, shield_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(shield_surface, shield_color, (shield_radius, shield_radius), shield_radius, 2)
            surface.blit(shield_surface, (screen_pos[0] - shield_radius, screen_pos[1] - shield_radius))

    def update(self, dt):
        """Update rocket's position and physics."""
        if self.landed_on_planet:
            planet = self.landed_on_planet
            direction = (self.position - planet.position) / np.linalg.norm(self.position - planet.position)
            self.position = planet.position + direction * (planet.radius + self.radius)
            self.velocity = planet.velocity.copy()
            # Takeoff logic: hold Up or W for 2 seconds
            keys = pygame.key.get_pressed()
            if keys[pygame.K_w] or keys[pygame.K_UP]:
                if not self.is_taking_off:
                    self.is_taking_off = True
                    self.takeoff_timer = 0
                self.takeoff_timer += dt
                if self.takeoff_timer >= 2.0 and self.fuel >= self.takeoff_fuel_cost:
                    # Launch!
                    self.fuel -= self.takeoff_fuel_cost
                    self.landed_on_planet = None
                    self.is_taking_off = False
                    self.takeoff_timer = 0
                    # Give initial upward velocity
                    self.velocity = direction * self.thrust * self.takeoff_thrust_multiplier / self.mass
            else:
                self.is_taking_off = False
                self.takeoff_timer = 0
            self.landing_velocity = np.linalg.norm(self.velocity)
        else:
            self.update_position(dt)
            self.landing_velocity = np.linalg.norm(self.velocity)

    def accept_quest(self, quest):
        """Accept a story quest."""
        self.current_quest = quest
        # Create mission from quest
        self.current_mission = {
            "type": quest["mission_type"],
            "target_count": quest["target_count"],
            "reward": quest["reward"],
            "description": quest["description"],
            "quest_id": quest["id"],
            "time_limit": 0  # Story quests typically don't have time limits
        }
        self.generate_mission_targets()

    def accept_mission(self, mission):
        """Accept a standard mission."""
        self.current_mission = mission
        self.mission_progress = 0
        self.mission_timer = mission.get("time_limit", 0)
        self.generate_mission_targets()

    def generate_mission_targets(self):
        """Generate targets for the current mission."""
        if not self.current_mission:
            return
        self.mission_targets = []
        target_count = self.current_mission["target_count"]
        if self.current_mission["type"] == "collect":
            for i in range(target_count):
                angle = random.uniform(0, 2 * np.pi)
                distance = random.uniform(1000, 5000)
                position = self.position + np.array([math.cos(angle), math.sin(angle)]) * distance
                self.mission_targets.append(Collectible(position, "mission_item"))
        elif self.current_mission["type"] == "destroy":
            for i in range(target_count):
                angle = random.uniform(0, 2 * np.pi)
                distance = random.uniform(1000, 4000)
                position = self.position + np.array([math.cos(angle), math.sin(angle)]) * distance
                hp_boost = 0
                if self.current_quest:
                    hp_boost = self.current_quest["id"] * 2
                enemy = Enemy(position, health=CONFIG["enemy_health"] + hp_boost)
                self.mission_targets.append(enemy)
        elif self.current_mission["type"] == "explore":
            for i in range(target_count):
                angle = random.uniform(0, 2 * np.pi)
                distance = random.uniform(2000, 8000)
                position = self.position + np.array([math.cos(angle), math.sin(angle)]) * distance
                self.mission_targets.append({
                    "position": position,
                    "radius": 300,
                    "discovered": False,
                    "name": f"Unknown Location {i+1}"
                })
        elif self.current_mission["type"] == "deliver":
            for i in range(target_count):
                angle = random.uniform(0, 2 * np.pi)
                distance = random.uniform(3000, 10000)
                position = self.position + np.array([math.cos(angle), math.sin(angle)]) * distance
                self.mission_targets.append({
                    "position": position,
                    "radius": 300,
                    "delivered": False,
                    "name": f"Outpost {i+1}"
                })

    def complete_mission(self):
        """Handle mission completion."""
        if not self.current_mission:
            return
        self.credits += self.current_mission["reward"]
        if self.current_quest and self.current_quest["id"] == self.current_mission.get("quest_id"):
            self.completed_quests.append(self.current_quest)
            next_quest_id = self.current_quest["id"] + 1
            for quest in STORY["quests"]:
                if quest["id"] == next_quest_id:
                    self.current_quest = quest
                    break
            else:
                self.current_quest = None
        self.current_mission = None
        self.mission_targets = []
        self.mission_progress = 0

    def fail_mission(self, reason):
        """Handle mission failure."""
        self.current_mission = None
        self.mission_targets = []

    def update_mission(self, dt):
        """Update current mission status."""
        if not self.current_mission:
            return
        if self.current_mission.get("time_limit", 0) > 0:
            self.mission_timer -= dt
            if self.mission_timer <= 0:
                self.fail_mission("Time expired")
                return
        if self.current_mission["type"] == "collect":
            if self.mission_progress >= self.current_mission["target_count"]:
                self.complete_mission()
        elif self.current_mission["type"] == "destroy":
            if self.mission_progress >= self.current_mission["target_count"]:
                self.complete_mission()
        elif self.current_mission["type"] == "explore":
            discovered_targets = 0
            for target in self.mission_targets:
                if target.get("discovered", False):
                    discovered_targets += 1
            if discovered_targets >= self.current_mission["target_count"]:
                self.complete_mission()

    def update_rotation(self, dt):
        """Update the rocket's rotation based on input flags."""
        if self.turning_left:
            self.angle -= self.rotation_speed * dt
        if self.turning_right:
            self.angle += self.rotation_speed * dt
        # Keep angle within 0-2pi
        self.angle %= 2 * math.pi

    def apply_thrust(self):
        """Apply thrust if thrusting and has fuel."""
        if self.thrusting and self.fuel > 0:
            # Thrust in the direction of the rocket's nose (forward)
            direction = np.array([math.cos(self.angle), math.sin(self.angle)])
            thrust_force = direction * self.thrust * (self.engine_level if hasattr(self, 'engine_level') else 1)
            self.apply_force(thrust_force)
            self.fuel -= CONFIG["fuel_consumption_rate"]
            if self.fuel < 0:
                self.fuel = 0

    def update_trajectory(self, celestial_bodies, dt):
        """Predict and store the rocket's future trajectory points for visualization."""
        # Simple forward simulation for trajectory preview
        points = []
        pos = self.position.copy()
        vel = self.velocity.copy()
        steps = CONFIG.get("trajectory_length", 200)
        time_step = 0.2
        for _ in range(steps):
            # Sum gravity from all planets
            total_force = np.zeros(2)
            for body in celestial_bodies:
                if isinstance(body, Planet):
                    delta = body.position - pos
                    dist_sq = np.dot(delta, delta)
                    if dist_sq > 1:
                        dist = np.sqrt(dist_sq)
                        force_mag = CONFIG["gravity_constant"] * self.mass * body.mass / dist_sq
                        force = force_mag * (delta / dist)
                        total_force += force
            acc = total_force / self.mass
            vel = vel + acc * time_step
            pos = pos + vel * time_step
            points.append(pos.copy())
        self.trajectory_points = points

    def take_damage(self, amount):
        """Apply damage to the rocket, reducing shield first, then health."""
        if self.shield > 0:
            shield_damage = min(self.shield, amount)
            self.shield -= shield_damage
            amount -= shield_damage
        if amount > 0:
            self.health -= amount
            self.damage_flash_timer = CONFIG.get("damage_visual_time", 0.5)
            if self.health < 0:
                self.health = 0

    def collect_item(self, item):
        """Handle collecting an item: add to inventory and apply effects."""
        self.collected_items.append(item)
        if hasattr(item, 'type'):
            if item.type == 'fuel':
                self.fuel = min(self.max_fuel, self.fuel + item.value)
            elif item.type == 'health':
                self.health = min(self.max_health, self.health + item.value)
            elif item.type == 'shield':
                self.shield = min(self.max_shield, self.shield + item.value)
            elif item.type == 'credits':
                self.credits += item.value
        # For mission items or unknown types, just add to inventory

    def fire_weapon(self, bullets):
        """Fire a bullet from the rocket's nose, in the direction it's facing, if fire rate allows."""
        if hasattr(self, 'fire_rate_timer') and self.fire_rate_timer > 0:
            return  # Still in cooldown
        direction = np.array([math.cos(self.angle), math.sin(self.angle)])
        bullet_speed = CONFIG.get("bullet_speed", 600)
        bullet_velocity = direction * bullet_speed
        # Spawn bullet from the nose (front tip) of the rocket
        rocket_length = self.radius * 3
        bullet_pos = self.position + direction * rocket_length
        bullet = Bullet(bullet_pos, bullet_velocity, damage=10 * (self.weapon_level if hasattr(self, 'weapon_level') else 1), angle=self.angle)
        bullets.append(bullet)
        self.fire_rate_timer = CONFIG.get("rocket_fire_rate", 0.3)

class Bullet:
    """Projectile fired from weapons."""
    def __init__(self, position, velocity, damage, angle, size=2):
        self.position = np.array(position, dtype=float)
        self.velocity = np.array(velocity, dtype=float)
        self.damage = damage
        self.angle = angle
        self.size = size
        self.lifetime = CONFIG["bullet_lifetime"]
        self.color = CONFIG["bullet_color"]
        self.hit = False
    
    def update(self, dt):
        """Update bullet position and lifetime."""
        self.position += self.velocity * dt
        self.lifetime -= dt
        return self.lifetime > 0 and not self.hit
    
    def draw(self, surface, camera):
        """Draw the bullet."""
        screen_pos = camera.world_to_screen(self.position)
        
        # Only draw if on screen
        if not (0 <= screen_pos[0] < camera.screen_width and 
                0 <= screen_pos[1] < camera.screen_height):
            return
        
        # Draw as small circle
        pygame.draw.circle(surface, self.color, screen_pos.astype(int), int(self.size * camera.zoom))

class Enemy:
    """Enemy ship that can pursue and attack the player."""
    def __init__(self, position, velocity=None, health=None):
        self.position = np.array(position, dtype=float)
        self.velocity = np.array(velocity if velocity is not None else [0, 0], dtype=float)
        self.health = CONFIG["enemy_health"] if health is None else health
        self.max_health = self.health
        self.size = 15
        self.color = CONFIG["enemy_color"]
        self.speed = CONFIG["enemy_speed"]
        self.damage = 10
        self.angle = 0
        self.fire_timer = random.uniform(1, 3)
        self.target = None
        self.active = True
        self.aggro_range = 2000
        self.shooting_range = 800
        self.type = "standard"  # standard, elite, boss
        self.drops = []
        self.generate_drops()
        
        # For visual effects
        self.damaged_timer = 0
        self.rotation_speed = random.uniform(0.5, 1.5)
    
    def generate_drops(self):
        """Generate potential item drops."""
        drop_count = random.randint(1, 3)
        for _ in range(drop_count):
            drop_type = random.choice(["fuel", "health", "shield", "credits"])
            value = 0
            
            if drop_type == "fuel":
                value = random.randint(20, 50)
            elif drop_type == "health":
                value = random.randint(10, 25)
            elif drop_type == "shield":
                value = random.randint(5, 15)
            elif drop_type == "credits":
                value = random.randint(10, 50)
            
            self.drops.append({"type": drop_type, "value": value})
    
    def set_target(self, target):
        """Set target to pursue."""
        self.target = target
    
    def update(self, dt, bullets):
        """Update enemy position and behavior."""
        if not self.active:
            return
        
        # Update rotation
        self.angle += self.rotation_speed * dt
        
        # Decrease damage visual timer
        if self.damaged_timer > 0:
            self.damaged_timer -= dt
        
        # If no target or target too far, just drift
        if not self.target:
            self.position += self.velocity * dt
            return
        
        # Calculate distance to target
        distance_to_target = np.linalg.norm(self.target.position - self.position)
        
        # If target in range, pursue
        if distance_to_target < self.aggro_range:
            # Vector to target
            direction = self.target.position - self.position
            direction = direction / np.linalg.norm(direction)
            
            # Update velocity to move toward target
            pursue_speed = self.speed
            self.velocity = direction * pursue_speed
            self.position += self.velocity * dt
            
            # Update angle to face target
            self.angle = math.atan2(direction[1], direction[0])
            
            # If in shooting range, fire at target
            if distance_to_target < self.shooting_range:
                self.fire_timer -= dt
                if self.fire_timer <= 0:
                    self.fire(bullets)
                    self.fire_timer = random.uniform(1.5, 3.0)
        else:
            # Just drift if target out of range
            self.position += self.velocity * dt
    
    def fire(self, bullets):
        """Fire at target."""
        if not self.target or not self.active:
            return
            
        # Calculate bullet direction
        direction = self.target.position - self.position
        direction = direction / np.linalg.norm(direction)
        
        # Add some inaccuracy
        angle = math.atan2(direction[1], direction[0])
        angle += random.uniform(-0.1, 0.1)
        direction = np.array([math.cos(angle), math.sin(angle)])
        
        # Create bullet
        bullet_pos = self.position + direction * self.size
        bullet_speed = CONFIG["bullet_speed"] * 0.7  # Slower than player bullets
        bullet_vel = direction * bullet_speed
        bullet = Bullet(bullet_pos, bullet_vel, self.damage, angle)
        bullet.color = (255, 50, 50)  # Red bullets for enemies
        bullets.append(bullet)
    
    def take_damage(self, amount):
        """Handle damage to enemy."""
        self.health -= amount
        self.damaged_timer = 0.3  # Visual effect duration
        return self.health <= 0
    
    def draw(self, surface, camera):
        """Draw the enemy ship."""
        if not self.active:
            return
            
        screen_pos = camera.world_to_screen(self.position)
        screen_size = int(self.size * camera.zoom)
        
        # Only draw if on screen
        if not (0 <= screen_pos[0] < camera.screen_width and 
                0 <= screen_pos[1] < camera.screen_height):
            return
        
        # Draw ship body
        color = self.color
        if self.damaged_timer > 0:
            color = (255, 100, 100)  # Flash red when damaged
        
        # Calculate points for ship shape based on angle
        direction = np.array([math.cos(self.angle), math.sin(self.angle)])
        right = np.array([-direction[1], direction[0]])  # Perpendicular to direction
        
        ship_length = screen_size * 2
        ship_width = screen_size * 1.5
        
        # Ship shape points
        nose = screen_pos + direction * ship_length/2
        left_wing = screen_pos - direction * ship_length/2 + right * ship_width/2
        right_wing = screen_pos - direction * ship_length/2 - right * ship_width/2
        
        # Draw enemy shape
        ship_points = [nose, left_wing, right_wing]
        pygame.draw.polygon(surface, color, ship_points)
        
        # Draw engine glow
        engine_pos = screen_pos - direction * ship_length/2
        engine_size = screen_size * 0.4
        engine_color = (255, 150, 0)
        pygame.draw.circle(surface, engine_color, engine_pos.astype(int), int(engine_size))
        
        # Draw health bar if damaged
        if self.health < self.max_health:
            bar_width = screen_size * 2
            bar_height = 4
            bar_pos = (int(screen_pos[0] - bar_width/2), int(screen_pos[1] - ship_length))
            
            # Background bar (red)
            pygame.draw.rect(surface, (255, 0, 0), 
                            (bar_pos[0], bar_pos[1], bar_width, bar_height))
            
            # Health bar (green)
            health_width = int(bar_width * (self.health / self.max_health))
            pygame.draw.rect(surface, (0, 255, 0), 
                            (bar_pos[0], bar_pos[1], health_width, bar_height))

class Collectible:
    """Collectible items that benefit the player."""
    def __init__(self, position, item_type="fuel", value=None, lifetime=None):
        self.position = np.array(position, dtype=float)
        self.type = item_type
        self.radius = 10
        self.angle = random.uniform(0, 2 * np.pi)
        self.spin_speed = random.uniform(0.5, 2.0)
        self.active = True
        self.lifetime = random.uniform(60, 120) if lifetime is None else lifetime
        self.pulse_offset = random.uniform(0, 2 * np.pi)
        self.pulse_speed = random.uniform(1.0, 2.0)
        
        # Set value and color based on type
        if item_type == "fuel":
            self.value = random.randint(20, 50) if value is None else value
            self.color = (50, 200, 50)  # Green
        elif item_type == "health":
            self.value = random.randint(10, 25) if value is None else value
            self.color = (200, 50, 50)  # Red
        elif item_type == "shield":
            self.value = random.randint(10, 30) if value is None else value
            self.color = (50, 50, 200)  # Blue
        elif item_type == "credits":
            self.value = random.randint(10, 100) if value is None else value
            self.color = (200, 200, 50)  # Gold
        elif item_type == "mission_item":
            self.value = 1
            self.color = (200, 100, 200)  # Purple
        else:
            self.value = 1 if value is None else value
            self.color = (200, 200, 200)  # White
    
    def update(self, dt):
        """Update collectible state."""
        self.angle += self.spin_speed * dt
        self.lifetime -= dt
        return self.lifetime > 0 and self.active
    
    def collect(self):
        """Mark as collected."""
        self.active = False
    
    def draw(self, surface, camera):
        """Draw the collectible item."""
        if not self.active:
            return
            
        screen_pos = camera.world_to_screen(self.position)
        screen_radius = int(self.radius * camera.zoom)
        
        # Only draw if on screen
        if not (0 <= screen_pos[0] < camera.screen_width and 
                0 <= screen_pos[1] < camera.screen_height):
            return
        
        # Calculate pulse effect
        pulse = math.sin(self.pulse_offset + pygame.time.get_ticks() * 0.001 * self.pulse_speed)
        pulse_radius = int(screen_radius * (1.0 + pulse * 0.2))
        
        # Draw outer glow
        for i in range(3):
            glow_radius = pulse_radius * (1.0 + i * 0.3)
            alpha = int(150 * (1.0 - i * 0.25))
            glow_color = self.color + (alpha,)
            
            glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surface, glow_color, (glow_radius, glow_radius), glow_radius)
            surface.blit(glow_surface, (screen_pos[0] - glow_radius, screen_pos[1] - glow_radius))
        
        # Draw shape based on item type
        if self.type == "fuel":
            # Draw fuel canister
            rect_size = screen_radius * 1.5
            rect = pygame.Rect(screen_pos[0] - rect_size/2, screen_pos[1] - rect_size/2, rect_size, rect_size)
            pygame.draw.rect(surface, self.color, rect)
            
            # Draw "F" symbol
            font = pygame.font.SysFont(None, max(1, int(rect_size * 1.5)))
            text = font.render("F", True, (0, 0, 0))
            text_rect = text.get_rect(center=screen_pos)
            surface.blit(text, text_rect)
            
        elif self.type == "health":
            # Draw health cross
            cross_size = screen_radius * 1.5
            half_size = cross_size / 2
            quarter_size = cross_size / 4
            
            # Horizontal bar
            pygame.draw.rect(surface, self.color, 
                           (screen_pos[0] - half_size, screen_pos[1] - quarter_size, 
                            cross_size, half_size))
            
            # Vertical bar
            pygame.draw.rect(surface, self.color, 
                           (screen_pos[0] - quarter_size, screen_pos[1] - half_size, 
                            half_size, cross_size))
            
        elif self.type == "shield":
            # Draw shield circle
            shield_radius = screen_radius * 1.2
            pygame.draw.circle(surface, self.color, screen_pos.astype(int), shield_radius, 3)
            
        elif self.type == "credits":
            # Draw credits symbol
            pygame.draw.circle(surface, self.color, screen_pos.astype(int), screen_radius)
            
            # Draw "$" symbol
            font = pygame.font.SysFont(None, max(1, int(screen_radius * 2)))
            text = font.render("$", True, (0, 0, 0))
            text_rect = text.get_rect(center=screen_pos)
            surface.blit(text, text_rect)
            
        else:  # Default/mission item
            # Draw special item (diamond shape)
            diamond_size = screen_radius * 1.5
            points = [
                (screen_pos[0], screen_pos[1] - diamond_size),  # Top
                (screen_pos[0] + diamond_size, screen_pos[1]),  # Right
                (screen_pos[0], screen_pos[1] + diamond_size),  # Bottom
                (screen_pos[0] - diamond_size, screen_pos[1])   # Left
            ]
            pygame.draw.polygon(surface, self.color, points)

class Background:
    """Parallax star field background."""
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.layers = []
        
        # Create star layers with different parallax speeds
        for i in range(3):
            layer = {
                "stars": [],
                "parallax": 0.05 * (i + 1),
                "color": (100 + i * 50, 100 + i * 50, 100 + i * 50)
            }
            
            # Generate stars for this layer
            star_count = 100 * (i + 1)
            for _ in range(star_count):
                star = {
                    "x": random.randint(0, width),
                    "y": random.randint(0, height),
                    "size": random.randint(1, 2 + i)
                }
                layer["stars"].append(star)
            
            self.layers.append(layer)
    
    def draw(self, surface, camera):
        """Draw parallax star background."""
        for layer in self.layers:
            for star in layer["stars"]:
                # Apply parallax effect
                parallax_x = (star["x"] - camera.position[0] * layer["parallax"]) % self.width
                parallax_y = (star["y"] - camera.position[1] * layer["parallax"]) % self.height
                
                # Convert to screen coordinates
                screen_x = (parallax_x - self.width/2) * camera.zoom + camera.screen_width/2
                screen_y = (parallax_y - self.height/2) * camera.zoom + camera.screen_height/2
                
                # Draw star
                pygame.draw.circle(surface, layer["color"], (int(screen_x), int(screen_y)), int(star["size"] * 0.5 * camera.zoom))

class UI:
    """User interface elements."""
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.font = pygame.font.SysFont(None, 24)
        self.small_font = pygame.font.SysFont(None, 18)
        self.large_font = pygame.font.SysFont(None, 32)
        self.showing_map = False
        self.showing_inventory = False
        self.showing_missions = False
        self.target_info = None
    
    def draw_hud(self, surface, rocket):
        """Draw the heads-up display."""
        # Draw fuel bar
        fuel_width = 150
        fuel_height = 20
        fuel_x = 10
        fuel_y = 10
        
        # Background
        pygame.draw.rect(surface, (50, 50, 50), (fuel_x, fuel_y, fuel_width, fuel_height))
        
        # Fuel level
        fuel_percentage = rocket.fuel / rocket.max_fuel
        pygame.draw.rect(surface, (50, 200, 50), 
                       (fuel_x, fuel_y, int(fuel_width * fuel_percentage), fuel_height))
        
        # Border
        pygame.draw.rect(surface, (200, 200, 200), (fuel_x, fuel_y, fuel_width, fuel_height), 2)
        
        # Text
        fuel_text = self.font.render(f"Fuel: {int(rocket.fuel)}/{rocket.max_fuel}", True, (255, 255, 255))
        surface.blit(fuel_text, (fuel_x + 10, fuel_y + 2))
        
        # Draw health bar
        health_width = 150
        health_height = 20
        health_x = 10
        health_y = 40
        
        # Background
        pygame.draw.rect(surface, (50, 50, 50), (health_x, health_y, health_width, health_height))
        
        # Health level
        health_percentage = max(0, rocket.health / rocket.max_health)
        health_color = (0, 255, 0) if health_percentage > 0.6 else (255, 255, 0) if health_percentage > 0.3 else (255, 0, 0)
        pygame.draw.rect(surface, health_color, 
                       (health_x, health_y, int(health_width * health_percentage), health_height))
        
        # Border
        pygame.draw.rect(surface, (200, 200, 200), (health_x, health_y, health_width, health_height), 2)
        
        # Text
        health_text = self.font.render(f"Health: {int(rocket.health)}/{rocket.max_health}", True, (255, 255, 255))
        surface.blit(health_text, (health_x + 10, health_y + 2))
        
        # Draw shield bar if shields available
        if rocket.max_shield > 0:
            shield_width = 150
            shield_height = 10
            shield_x = 10
            shield_y = 65
            
            # Background
            pygame.draw.rect(surface, (50, 50, 50), (shield_x, shield_y, shield_width, shield_height))
            
            # Shield level
            shield_percentage = rocket.shield / rocket.max_shield
            pygame.draw.rect(surface, (50, 100, 255), 
                           (shield_x, shield_y, int(shield_width * shield_percentage), shield_height))
            
            # Border
            pygame.draw.rect(surface, (200, 200, 200), (shield_x, shield_y, shield_width, shield_height), 2)
        
        # Draw credits
        credits_text = self.font.render(f"Credits: {rocket.credits}", True, (255, 255, 255))
        surface.blit(credits_text, (10, 85))
        
        # Draw speed
        speed = np.linalg.norm(rocket.velocity)
        speed_text = self.font.render(f"Speed: {int(speed)}", True, (255, 255, 255))
        surface.blit(speed_text, (10, 115))
        
        # Draw current mission if available
        if rocket.current_mission:
            mission_y = 145
            mission_title = self.font.render("CURRENT MISSION:", True, (255, 200, 0))
            surface.blit(mission_title, (10, mission_y))
            
            mission_desc = rocket.current_mission["description"]
            mission_text = self.small_font.render(mission_desc, True, (200, 200, 200))
            surface.blit(mission_text, (10, mission_y + 25))
            
            progress_text = self.small_font.render(
                f"Progress: {rocket.mission_progress}/{rocket.current_mission['target_count']}", 
                True, (200, 200, 200))
            surface.blit(progress_text, (10, mission_y + 45))
            
            # Show timer if time-limited mission
            if rocket.mission_timer > 0:
                timer_text = self.small_font.render(
                    f"Time remaining: {int(rocket.mission_timer)}s", 
                    True, (255, 100, 100) if rocket.mission_timer < 10 else (200, 200, 200))
                surface.blit(timer_text, (10, mission_y + 65))
        
        # Draw takeoff instructions if landed on planet
        if rocket.landed_on_planet:
            takeoff_y = 220
            takeoff_title = self.font.render("LANDED ON PLANET", True, (255, 255, 0))
            surface.blit(takeoff_title, (10, takeoff_y))
            
            takeoff_instructions = self.small_font.render(
                "Hold SPACE + W for 5 seconds to takeoff", True, (200, 200, 200))
            surface.blit(takeoff_instructions, (10, takeoff_y + 25))
            
            fuel_cost_text = self.small_font.render(
                f"Takeoff cost: {rocket.takeoff_fuel_cost} fuel", True, (255, 100, 100))
            surface.blit(fuel_cost_text, (10, takeoff_y + 45))
            
            if rocket.is_taking_off:
                progress = rocket.takeoff_timer / rocket.takeoff_duration
                progress_text = self.small_font.render(
                    f"Takeoff progress: {int(progress * 100)}%", True, (0, 255, 0))
                surface.blit(progress_text, (10, takeoff_y + 65))
    
    def draw_minimap(self, surface, rocket, celestial_bodies, camera):
        """Draw a minimap of nearby objects."""
        map_size = 150
        map_x = self.screen_width - map_size - 10
        map_y = 10
        map_zoom = 0.01
        
        # Draw map background
        pygame.draw.rect(surface, (0, 0, 0, 150), (map_x, map_y, map_size, map_size))
        pygame.draw.rect(surface, (100, 100, 100), (map_x, map_y, map_size, map_size), 2)
        
        # Draw celestial bodies
        for body in celestial_bodies:
            if isinstance(body, CelestialBody) or isinstance(body, SpaceStation):
                # Calculate minimap position
                rel_pos = body.position - rocket.position
                map_pos_x = map_x + map_size/2 + rel_pos[0] * map_zoom
                map_pos_y = map_y + map_size/2 + rel_pos[1] * map_zoom
                
                # Only draw if on minimap
                if (map_x <= map_pos_x <= map_x + map_size and
                    map_y <= map_pos_y <= map_y + map_size):
                    
                    # Determine color
                    if isinstance(body, Planet):
                        color = body.color
                        size = 4
                    elif isinstance(body, SpaceStation):
                        color = (100, 200, 255)
                        size = 3
                    elif isinstance(body, Asteroid):
                        color = (150, 150, 150)
                        size = 2
                    else:
                        color = body.color
                        size = 2
                    
                    pygame.draw.circle(surface, color, (int(map_pos_x), int(map_pos_y)), size)
        
        # Draw mission targets if available
        if rocket.current_mission and rocket.mission_targets:
            for target in rocket.mission_targets:
                if hasattr(target, "position"):
                    target_pos = target.position
                elif isinstance(target, dict) and "position" in target:
                    target_pos = target["position"]
                else:
                    continue
                
                rel_pos = target_pos - rocket.position
                map_pos_x = map_x + map_size/2 + rel_pos[0] * map_zoom
                map_pos_y = map_y + map_size/2 + rel_pos[1] * map_zoom
                
                if (map_x <= map_pos_x <= map_x + map_size and
                    map_y <= map_pos_y <= map_y + map_size):
                    # Draw mission target as yellow triangle
                    pygame.draw.polygon(surface, (255, 255, 0), [
                        (map_pos_x, map_pos_y - 5),
                        (map_pos_x - 4, map_pos_y + 3),
                        (map_pos_x + 4, map_pos_y + 3)
                    ])
        
        # Draw player in the center
        pygame.draw.circle(surface, (0, 255, 0), (int(map_x + map_size/2), int(map_y + map_size/2)), 3)
    
    def draw_target_info(self, surface, target):
        """Draw information about the selected target."""
        if not target:
            return
            
        info_x = self.screen_width - 220
        info_y = 170
        info_width = 200
        info_height = 120
        
        # Background
        pygame.draw.rect(surface, (0, 0, 0, 200), (info_x, info_y, info_width, info_height))
        pygame.draw.rect(surface, (100, 100, 100), (info_x, info_y, info_width, info_height), 2)
        
        # Title
        if isinstance(target, Planet):
            title = target.name
            details = [
                f"Type: Planet",
                f"Mass: {target.mass/1000:.1f}k",
                f"Radius: {target.radius}",
                 f"Gravity: {getattr(target, 'gravity', 'Unknown')}"
           ]
        elif isinstance(target, Asteroid):
            title = "Asteroid"
            details = [
                f"Mass: {target.mass}",
                f"Size: {target.radius}",
                f"Resource: {target.resource_type}"
            ]
        elif isinstance(target, SpaceStation):
            title = target.name
            details = [
                f"Type: Space Station",
                f"Services: Trading, Repair",
                f"Docking: {'Available' if target.docking_available else 'Unavailable'}"
            ]
        elif isinstance(target, Enemy):
            title = "Enemy Ship"
            details = [
                f"Health: {target.health}/{target.max_health}",
                f"Type: {target.type.capitalize()}"
            ]
        else:
            title = "Unknown Object"
            details = []
        
        # Draw title
        title_text = self.font.render(title, True, (255, 200, 0))
        surface.blit(title_text, (info_x + 10, info_y + 10))
        
        # Draw details
        for i, detail in enumerate(details):
            detail_text = self.small_font.render(detail, True, (200, 200, 200))
            surface.blit(detail_text, (info_x + 10, info_y + 40 + i * 20))
    
    def draw_map_screen(self, surface, rocket, celestial_bodies, camera):
        """Draw full-screen map when requested."""
        if not self.showing_map:
            return
            
        # Semi-transparent background
        background = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        background.fill((0, 0, 0, 200))
        surface.blit(background, (0, 0))
        
        # Map title
        title_text = self.large_font.render("STAR MAP", True, (255, 255, 255))
        surface.blit(title_text, (self.screen_width/2 - title_text.get_width()/2, 20))
        
        # Instructions
        instructions = self.small_font.render("Press M to close map", True, (200, 200, 200))
        surface.blit(instructions, (self.screen_width/2 - instructions.get_width()/2, self.screen_height - 30))
        
        # Map settings
        map_zoom = 0.005
        
        # Draw grid lines
        grid_size = 2000
        grid_count = 10
        
        for i in range(-grid_count, grid_count + 1):
            grid_world_pos = i * grid_size
            
            # Horizontal line
            start_pos = rocket.position + np.array([-grid_count * grid_size, grid_world_pos])
            end_pos = rocket.position + np.array([grid_count * grid_size, grid_world_pos])
            
            start_screen = (self.screen_width/2 + (start_pos[0] - rocket.position[0]) * map_zoom,
                           self.screen_height/2 + (start_pos[1] - rocket.position[1]) * map_zoom)
            end_screen = (self.screen_width/2 + (end_pos[0] - rocket.position[0]) * map_zoom,
                         self.screen_height/2 + (end_pos[1] - rocket.position[1]) * map_zoom)
            
            pygame.draw.line(surface, (50, 50, 50), start_screen, end_screen, 1)
            
            # Vertical line
            start_pos = rocket.position + np.array([grid_world_pos, -grid_count * grid_size])
            end_pos = rocket.position + np.array([grid_world_pos, grid_count * grid_size])
            
            start_screen = (self.screen_width/2 + (start_pos[0] - rocket.position[0]) * map_zoom,
                           self.screen_height/2 + (start_pos[1] - rocket.position[1]) * map_zoom)
            end_screen = (self.screen_width/2 + (end_pos[0] - rocket.position[0]) * map_zoom,
                         self.screen_height/2 + (end_pos[1] - rocket.position[1]) * map_zoom)
            
            pygame.draw.line(surface, (50, 50, 50), start_screen, end_screen, 1)
        
        # Draw celestial bodies
        for body in celestial_bodies:
            if isinstance(body, CelestialBody) or isinstance(body, SpaceStation) or isinstance(body, Nebula):
                # Calculate map position
                rel_pos = body.position - rocket.position
                map_pos_x = self.screen_width/2 + rel_pos[0] * map_zoom
                map_pos_y = self.screen_height/2 + rel_pos[1] * map_zoom
                
                # Determine color and size
                if isinstance(body, Planet):
                    color = body.color
                    size = 8
                    # Draw planet name
                    name_text = self.small_font.render(body.name, True, (200, 200, 200))
                    surface.blit(name_text, (map_pos_x - name_text.get_width()/2, map_pos_y + 10))
                elif isinstance(body, SpaceStation):
                    color = (100, 200, 255)
                    size = 6
                    # Draw space station symbol (square)
                    pygame.draw.rect(surface, color, 
                                   (map_pos_x - size/2, map_pos_y - size/2, size, size))
                    
                    # Draw station name
                    name_text = self.small_font.render(body.name, True, (200, 200, 200))
                    surface.blit(name_text, (map_pos_x - name_text.get_width()/2, map_pos_y + 10))
                    continue  # Skip the circle drawing
                elif isinstance(body, Asteroid):
                    color = (150, 150, 150)
                    size = 3
                elif isinstance(body, Nebula):
                    # Draw nebula as semi-transparent circle
                    nebula_size = body.radius * map_zoom
                    nebula_surface = pygame.Surface((nebula_size * 2, nebula_size * 2), pygame.SRCALPHA)
                    pygame.draw.circle(nebula_surface, body.color + (100,), 
                                     (nebula_size, nebula_size), nebula_size)
                    surface.blit(nebula_surface, 
                                (map_pos_x - nebula_size, map_pos_y - nebula_size))
                    continue  # Skip the circle drawing
                else:
                    color = body.color
                    size = 4
                
                # Draw the object
                pygame.draw.circle(surface, color, (int(map_pos_x), int(map_pos_y)), size)
        
        # Draw mission targets
        if rocket.current_mission and rocket.mission_targets:
            for target in rocket.mission_targets:
                if hasattr(target, "position"):
                    target_pos = target.position
                elif isinstance(target, dict) and "position" in target:
                    target_pos = target["position"]
                else:
                    continue
                
                rel_pos = target_pos - rocket.position
                map_pos_x = self.screen_width/2 + rel_pos[0] * map_zoom
                map_pos_y = self.screen_height/2 + rel_pos[1] * map_zoom
                
                # Draw mission target as yellow diamond
                size = 8
                pygame.draw.polygon(surface, (255, 255, 0), [
                    (map_pos_x, map_pos_y - size),
                    (map_pos_x + size, map_pos_y),
                    (map_pos_x, map_pos_y + size),
                    (map_pos_x - size, map_pos_y)
                ])
                
                # Draw target label if available
                if isinstance(target, dict) and "name" in target:
                    name_text = self.small_font.render(target["name"], True, (255, 255, 0))
                    surface.blit(name_text, (map_pos_x - name_text.get_width()/2, map_pos_y + size + 5))
        
        # Draw player position
        pygame.draw.circle(surface, (0, 255, 0), (int(self.screen_width/2), int(self.screen_height/2)), 5)
        player_text = self.small_font.render("YOU", True, (0, 255, 0))
        surface.blit(player_text, (self.screen_width/2 - player_text.get_width()/2, self.screen_height/2 + 10))
    
    def draw_inventory_screen(self, surface, rocket):
        """Draw inventory screen when requested."""
        if not self.showing_inventory:
            return
            
        # Semi-transparent background
        background = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        background.fill((0, 0, 0, 200))
        surface.blit(background, (0, 0))
        
        # Inventory title
        title_text = self.large_font.render("INVENTORY", True, (255, 255, 255))
        surface.blit(title_text, (self.screen_width/2 - title_text.get_width()/2, 20))
        
        # Instructions
        instructions = self.small_font.render("Press I to close inventory", True, (200, 200, 200))
        surface.blit(instructions, (self.screen_width/2 - instructions.get_width()/2, self.screen_height - 30))
        
        # Draw inventory contents
        slot_size = 60
        slots_per_row = 8
        inventory_x = (self.screen_width - slots_per_row * slot_size) / 2
        inventory_y = 80
        
        # Draw stats section
        stats_x = 50
        stats_y = 100
        stats_width = 300
        stats_height = 200
        
        pygame.draw.rect(surface, (50, 50, 50, 150), (stats_x, stats_y, stats_width, stats_height))
        pygame.draw.rect(surface, (100, 100, 100), (stats_x, stats_y, stats_width, stats_height), 2)
        
        stat_title = self.font.render("SHIP STATS", True, (255, 200, 0))
        surface.blit(stat_title, (stats_x + 10, stats_y + 10))
        
        # Ship stats
        stats = [
            f"Health: {rocket.health}/{rocket.max_health}",
            f"Shield: {rocket.shield}/{rocket.max_shield}",
            f"Fuel: {int(rocket.fuel)}/{rocket.max_fuel}",
            f"Credits: {rocket.credits}",
            f"Engine Level: {rocket.engine_level}",
            f"Weapon Level: {rocket.weapon_level}",
            f"Scanner Level: {rocket.scanner_level}"
        ]
        
        for i, stat in enumerate(stats):
            stat_text = self.font.render(stat, True, (200, 200, 200))
            surface.blit(stat_text, (stats_x + 20, stats_y + 50 + i * 25))
        
        # Draw collected items section
        items_x = self.screen_width - 350
        items_y = 100
        items_width = 300
        items_height = 300
        
        pygame.draw.rect(surface, (50, 50, 50, 150), (items_x, items_y, items_width, items_height))
        pygame.draw.rect(surface, (100, 100, 100), (items_x, items_y, items_width, items_height), 2)
        
        items_title = self.font.render("COLLECTED ITEMS", True, (255, 200, 0))
        surface.blit(items_title, (items_x + 10, items_y + 10))
        
        if not rocket.collected_items:
            no_items = self.font.render("No items collected", True, (150, 150, 150))
            surface.blit(no_items, (items_x + 20, items_y + 50))
        else:
            for i, item in enumerate(rocket.collected_items[:10]):  # Show up to 10 items
                item_name = item.type if hasattr(item, "type") else "Unknown Item"
                item_text = self.font.render(f"• {item_name}", True, (200, 200, 200))
                surface.blit(item_text, (items_x + 20, items_y + 50 + i * 25))
    
    def draw_missions_screen(self, surface, rocket):
        """Draw missions screen when requested."""
        if not self.showing_missions:
            return
            
        # Semi-transparent background
        background = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        background.fill((0, 0, 0, 200))
        surface.blit(background, (0, 0))
        
        # Missions title
        title_text = self.large_font.render("MISSIONS", True, (255, 255, 255))
        surface.blit(title_text, (self.screen_width/2 - title_text.get_width()/2, 20))
        
        # Instructions
        instructions = self.small_font.render("Press N to close missions", True, (200, 200, 200))
        surface.blit(instructions, (self.screen_width/2 - instructions.get_width()/2, self.screen_height - 30))
        
        # Current mission
        current_x = 50
        current_y = 80
        current_width = self.screen_width - 100
        current_height = 150
        
        pygame.draw.rect(surface, (50, 50, 50, 150), (current_x, current_y, current_width, current_height))
        pygame.draw.rect(surface, (100, 100, 100), (current_x, current_y, current_width, current_height), 2)
        
        current_title = self.font.render("CURRENT MISSION", True, (255, 200, 0))
        surface.blit(current_title, (current_x + 10, current_y + 10))
        
        if rocket.current_mission:
            mission_type = rocket.current_mission["type"].capitalize()
            mission_desc = rocket.current_mission["description"]
            
            mission_info = [
                f"Type: {mission_type}",
                f"Description: {mission_desc}",
                f"Progress: {rocket.mission_progress}/{rocket.current_mission['target_count']}",
                f"Reward: {rocket.current_mission['reward']} credits"
            ]
            
            if rocket.mission_timer > 0:
                mission_info.append(f"Time remaining: {int(rocket.mission_timer)}s")
            
            for i, info in enumerate(mission_info):
                info_text = self.font.render(info, True, (200, 200, 200))
                surface.blit(info_text, (current_x + 20, current_y + 40 + i * 25))
        else:
            no_mission = self.font.render("No active mission", True, (150, 150, 150))
            surface.blit(no_mission, (current_x + 20, current_y + 50))
        
        # Current quest
        quest_x = 50
        quest_y = 250
        quest_width = self.screen_width - 100
        quest_height = 150
        
        pygame.draw.rect(surface, (50, 50, 50, 150), (quest_x, quest_y, quest_width, quest_height))
        pygame.draw.rect(surface, (100, 100, 100), (quest_x, quest_y, quest_width, quest_height), 2)
        
        quest_title = self.font.render("CURRENT STORY QUEST", True, (255, 200, 0))
        surface.blit(quest_title, (quest_x + 10, quest_y + 10))
        
        if rocket.current_quest:
            quest_name = rocket.current_quest["name"]
            quest_desc = rocket.current_quest["description"]
            
            quest_info = [
                f"Name: {quest_name}",
                f"Description: {quest_desc}",
                f"Reward: {rocket.current_quest['reward']} credits"
            ]
            
            for i, info in enumerate(quest_info):
                info_text = self.font.render(info, True, (200, 200, 200))
                surface.blit(info_text, (quest_x + 20, quest_y + 40 + i * 25))
        else:
            no_quest = self.font.render("No active story quest", True, (150, 150, 150))
            surface.blit(no_quest, (quest_x + 20, quest_y + 50))

class Game:
    """Main game class."""
    def __init__(self):
        pygame.init()
        
        # Set up display
        self.screen_width = 1280
        self.screen_height = 720
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Gravity Explorer")
        
        # Set up game objects
        self.camera = Camera(self.screen_width, self.screen_height)
        self.celestial_bodies = []
        self.space_stations = []
        self.background = Background(8000, 8000)
        self.ui = UI(self.screen_width, self.screen_height)
        self.bullets = []
        self.enemies = []
        self.collectibles = []
        self.nebulae = []
        self.particle_system = ParticleSystem()
        
        # Generate universe first, then spawn rocket on a planet
        self.generate_universe()
        self.spawn_rocket_on_planet()
        
        # Game state
        self.running = True
        self.paused = False
        self.game_over = False
        self.selected_target = None
        self.target_distance = 0
        self.scan_timer = 0
        
        # Set camera to follow rocket
        self.camera.set_target(self.rocket)
        
        # Start story quest
        self.rocket.current_quest = STORY["quests"][0]
        self.rocket.accept_quest(self.rocket.current_quest)
        
        # Timing
        self.clock = pygame.time.Clock()
        self.fps = 60
        self.fixed_time_step = CONFIG["time_step"]
        self.accumulated_time = 0
        self.last_time = pygame.time.get_ticks()
        self.scene = "planet_surface"  # Start on planet surface
        self.planet_surface_scene = None
        self.scene_transition = None
        self.fade_alpha = 0
        self.fade_direction = 0
        self.next_scene = None
        self.landing_prompt = None
        self.landing_prompt_planet = None
        self.landing_prompt_active = False
        self.saved_space_state = None  # For saving/restoring space state
        # ... existing code ...
        # Start on planet surface
        start_planet = None
        for body in self.celestial_bodies:
            if isinstance(body, Planet):
                start_planet = body
                break
        if start_planet:
            self.start_planet_surface_scene(start_planet)
        else:
            self.scene = "space"
        # ... existing code ...
    
    def generate_universe(self):
        """Generate the game universe."""
        # Create central star
        self.central_star = Star([0, 0], 10000000, 100, (255, 255, 150), "Alpha Centauri")
        self.celestial_bodies.append(self.central_star)
        
        # Create planets
        planet_names = ["Terra Prime", "New Mars", "Aquarius", "Vulcan", "Frost"]
        for i, name in enumerate(planet_names):
            distance = 2000 + i * 1200
            angle = random.uniform(0, 2 * np.pi)
            position = np.array([math.cos(angle), math.sin(angle)]) * distance

            # Use ML model to generate planet properties
            mass, radius, color, density, biome_type, has_rings, moons, takeoff_cost = generate_planet_properties(distance, self.central_star.mass)
            # --- SCALE UP PLANETS ---
            mass *= 2.5  # Increase mass for stronger gravity and visual prominence
            radius *= 2.2  # Increase radius for larger visual size
            # --- END SCALE UP ---
            velocity = np.array([-math.sin(angle), math.cos(angle)]) * math.sqrt(CONFIG["gravity_constant"] * self.central_star.mass / distance)

            # Create and add planet
            planet = Planet(position, velocity, mass, radius, color, density, biome_type, has_rings, moons, name)
            planet.takeoff_cost_multiplier = takeoff_cost
            self.celestial_bodies.append(planet)
        
        # Create asteroid belt
        asteroid_belt_distance = 8000
        num_asteroids = 100  # Reduced for better performance
        
        for i in range(num_asteroids):
            angle = random.uniform(0, 2 * np.pi)
            distance_variation = random.uniform(0.8, 1.2)
            distance = asteroid_belt_distance * distance_variation
            
            position = np.array([math.cos(angle), math.sin(angle)]) * distance
            
            # Orbital velocity with slight variation
            orbit_speed = math.sqrt(CONFIG["gravity_constant"] * self.central_star.mass / distance)
            speed_variation = random.uniform(0.9, 1.1)
            velocity = np.array([-math.sin(angle), math.cos(angle)]) * orbit_speed * speed_variation
            
            # Asteroid properties
            mass = random.uniform(100, 1000)
            radius = int(5 + mass / 100)
            color = (
                random.randint(150, 170),
                random.randint(150, 170),
                random.randint(150, 170)
            )
            
            # Determine resource type
            resource_type = random.choice(["iron", "gold", "platinum", "ice", "none", "none"])
            
            # Create asteroid
            asteroid = Asteroid(position, velocity, mass, radius, color, resource_type)
            self.celestial_bodies.append(asteroid)
        
        # Create space stations
        station_names = [
            "Trading Post Alpha", 
            "Scientific Outpost Beta", 
            "Mining Colony Gamma",
            "Military Base Delta"
        ]
        
        for i, name in enumerate(station_names):
            angle = random.uniform(0, 2 * np.pi)
            distance = 3000 + i * 1500
            position = np.array([math.cos(angle), math.sin(angle)]) * distance
            
            # Find nearby planet if possible
            nearest_planet = None
            nearest_distance = float('inf')
            
            for body in self.celestial_bodies:
                if isinstance(body, Planet):
                    dist = np.linalg.norm(body.position - position)
                    if dist < nearest_distance:
                        nearest_distance = dist
                        nearest_planet = body
            
            # Adjust position to be near a planet if one is close
            if nearest_planet and nearest_distance < 2000:
                direction = (position - nearest_planet.position) / nearest_distance
                position = nearest_planet.position + direction * (nearest_planet.radius * 3)
            
            # Create station
            station = SpaceStation(position, name=name)
            self.space_stations.append(station)
            self.celestial_bodies.append(station)
        
        # Create nebulae
        for i in range(3):
            angle = random.uniform(0, 2 * np.pi)
            distance = random.uniform(3000, 10000)
            position = np.array([math.cos(angle), math.sin(angle)]) * distance
            
            nebula = Nebula(position, random.uniform(1000, 3000))
            self.nebulae.append(nebula)
            self.celestial_bodies.append(nebula)
        
        # Create some initial enemies
        for i in range(3):  # Reduced for better performance
            angle = random.uniform(0, 2 * np.pi)
            distance = random.uniform(2000, 6000)
            position = np.array([math.cos(angle), math.sin(angle)]) * distance
            
            enemy = Enemy(position)
            self.enemies.append(enemy)
        
        # Create some initial collectibles
        for i in range(5):  # Reduced for better performance
            angle = random.uniform(0, 2 * np.pi)
            distance = random.uniform(1000, 4000)
            position = np.array([math.cos(angle), math.sin(angle)]) * distance
            
            item_type = random.choice(["fuel", "health", "shield", "credits"])
            collectible = Collectible(position, item_type)
            self.collectibles.append(collectible)
    
    def spawn_rocket_on_planet(self):
        """Spawn the rocket on the surface of a random planet."""
        # Find a suitable planet (not too close to the star)
        suitable_planets = []
        for body in self.celestial_bodies:
            if isinstance(body, Planet):
                distance_from_star = np.linalg.norm(body.position - self.central_star.position)
                if distance_from_star > 2000:  # Avoid planets too close to star
                    suitable_planets.append(body)
        
        if not suitable_planets:
            # Fallback: spawn near the first planet
            if self.celestial_bodies:
                first_planet = None
                for body in self.celestial_bodies:
                    if isinstance(body, Planet):
                        first_planet = body
                        break
                
                if first_planet:
                    # Spawn on planet surface
                    spawn_angle = random.uniform(0, 2 * np.pi)
                    spawn_direction = np.array([math.cos(spawn_angle), math.sin(spawn_angle)])
                    spawn_position = first_planet.position + spawn_direction * (first_planet.radius + 10)
                    self.rocket = Rocket(spawn_position, first_planet.velocity.copy())
                    self.rocket.landed_on_planet = first_planet
                else:
                    # Fallback: spawn at origin
                    self.rocket = Rocket([0, 0])
            else:
                # Fallback: spawn at origin
                self.rocket = Rocket([0, 0])
        else:
            # Choose a random suitable planet
            chosen_planet = random.choice(suitable_planets)
            
            # Spawn on planet surface
            spawn_angle = random.uniform(0, 2 * np.pi)
            spawn_direction = np.array([math.cos(spawn_angle), math.sin(spawn_angle)])
            spawn_position = chosen_planet.position + spawn_direction * (chosen_planet.radius + 10)
            
            # Create rocket with planet's velocity (so it stays on the planet)
            self.rocket = Rocket(spawn_position, chosen_planet.velocity.copy())
            self.rocket.landed_on_planet = chosen_planet
    
    def handle_input(self):
        """Handle player input."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.paused = not self.paused
                
                elif event.key == pygame.K_SPACE:
                    self.rocket.fire_weapon(self.bullets)
                
                elif event.key == pygame.K_m:
                    self.ui.showing_map = not self.ui.showing_map
                
                elif event.key == pygame.K_i:
                    self.ui.showing_inventory = not self.ui.showing_inventory
                
                elif event.key == pygame.K_n:
                    self.ui.showing_missions = not self.ui.showing_missions
                
                # Target scanning
                elif event.key == pygame.K_TAB:
                    self.scan_for_target()
                elif event.key == pygame.K_l and self.landing_prompt_active and self.landing_prompt_planet:
                    # Start landing transition
                    self.rocket.landed_on_planet = self.landing_prompt_planet
                    self.rocket.velocity = self.landing_prompt_planet.velocity.copy() if hasattr(self.landing_prompt_planet, 'velocity') else np.zeros(2)
                    direction = (self.rocket.position - self.landing_prompt_planet.position)
                    if np.linalg.norm(direction) == 0:
                        direction = np.array([1.0, 0.0])
                    else:
                        direction = direction / np.linalg.norm(direction)
                    self.rocket.position = self.landing_prompt_planet.position + direction * (self.landing_prompt_planet.radius + self.rocket.radius)
                    self.enter_planet_surface_scene(self.landing_prompt_planet)
                elif hasattr(self, 'landing_modal_active') and self.landing_modal_active:
                    if event.key == pygame.K_l:
                        # Save space state and fade out
                        self.save_space_state_and_land()
                        self.landing_modal_active = False
                        self.landing_prompt_active = False
                        self.landing_prompt = None
                        return
                    elif event.key == pygame.K_ESCAPE:
                        self.landing_modal_active = False
                        self.landing_prompt_active = False
                        self.landing_prompt = None
                        return
        
        # Get continuous key presses
        keys = pygame.key.get_pressed()
        
        # Reset control states
        self.rocket.thrusting = False
        self.rocket.turning_left = False
        self.rocket.turning_right = False
        
        # Movement controls
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            self.rocket.thrusting = True
        
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.rocket.turning_left = True
        
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.rocket.turning_right = True
        
        # Zoom controls
        if keys[pygame.K_EQUALS] or keys[pygame.K_PLUS]:
            self.camera.zoom_in()
        
        if keys[pygame.K_MINUS]:
            self.camera.zoom_out()
        
        # Debug: add fuel
        if keys[pygame.K_0] and keys[pygame.K_LCTRL]:
            self.rocket.fuel = self.rocket.max_fuel
    
    def scan_for_target(self):
        """Scan for and select nearest target."""
        # Only scan periodically to prevent spamming
        current_time = pygame.time.get_ticks() / 1000
        if current_time - self.scan_timer < 0.5:
            return
            
        self.scan_timer = current_time
        
        # Try to find nearest target
        nearest_target = None
        nearest_distance = float('inf')
        
        scan_range = 1000 * self.rocket.scanner_level  # Scanner range increases with upgrades
        
        # Check celestial bodies
        for body in self.celestial_bodies:
            if body != self.rocket:
                distance = np.linalg.norm(body.position - self.rocket.position)
                if distance < scan_range and distance < nearest_distance:
                    nearest_target = body
                    nearest_distance = distance
        
        # Check enemies
        for enemy in self.enemies:
            if enemy.active:
                distance = np.linalg.norm(enemy.position - self.rocket.position)
                if distance < scan_range and distance < nearest_distance:
                    nearest_target = enemy
                    nearest_distance = distance
        
        # Check collectibles
        for item in self.collectibles:
            if item.active:
                distance = np.linalg.norm(item.position - self.rocket.position)
                if distance < scan_range and distance < nearest_distance:
                    nearest_target = item
                    nearest_distance = distance
        
        # Set target and distance
        self.selected_target = nearest_target
        if nearest_target:
            self.target_distance = nearest_distance
            self.ui.target_info = {
                "target": nearest_target,
                "distance": nearest_distance,
                "gravity": "N/A" if not isinstance(nearest_target, Planet) else 
                           "Strong" if nearest_target.mass > 100000 else "Medium" if nearest_target.mass > 50000 else "Weak"
            }
    
    def update_physics(self, dt):
        """Update physics for all objects."""
        # Update rocket
        self.rocket.update_rotation(dt)
        self.rocket.apply_thrust()
        self.landing_prompt = None
        self.landing_prompt_planet = None
        self.landing_prompt_active = False
        for body in self.celestial_bodies:
            if isinstance(body, CelestialBody) and body != self.rocket:
                delta = body.position - self.rocket.position
                distance_sq = np.dot(delta, delta)
                if distance_sq > 1:
                    distance = np.sqrt(distance_sq)
                    # --- Space Station Collision ---
                    if isinstance(body, SpaceStation):
                        if distance < body.radius + self.rocket.radius:
                            relative_vel = np.linalg.norm(self.rocket.velocity - body.velocity)
                            # Trigger explosion
                            self.create_explosion(self.rocket.position, 40)
                            # End game or damage based on impact
                            if relative_vel > 30:
                                self.rocket.health = 0
                                self.game_over = True
                            else:
                                self.rocket.take_damage(int(relative_vel * 2))
                                if self.rocket.health <= 0:
                                    self.game_over = True
                            continue  # Skip further gravity/collision for this frame
                    # --- Planet Gravity Physics ---
                    if isinstance(body, Planet):
                        # True gravity field, smooth and strong for large planets
                        force_magnitude = CONFIG["gravity_constant"] * self.rocket.mass * body.mass / (distance ** 2)
                        force = force_magnitude * (delta / distance)
                        self.rocket.apply_force(force)
                        # Landing prompt logic
                        if (distance < body.radius * 1.2 + self.rocket.radius and
                            distance > body.radius + self.rocket.radius + 10 and
                            self.rocket.landed_on_planet != body):
                            self.landing_prompt = f"Do you want to land on {body.name}? (L = Yes, Esc = No)"
                            self.landing_prompt_planet = body
                            self.landing_prompt_active = True
                            self.landing_modal_active = True
                        else:
                            if not hasattr(self, 'landing_modal_active') or not self.landing_modal_active:
                                self.landing_prompt_active = False
                                self.landing_prompt = None
                    elif isinstance(body, (Star, BlackHole, Wormhole, Pulsar)):
                        # Other massive bodies also exert gravity
                        force_magnitude = CONFIG["gravity_constant"] * self.rocket.mass * body.mass / (distance ** 2)
                        force = force_magnitude * (delta / distance)
                        self.rocket.apply_force(force)
                    # Asteroids and stations do not exert gravity
                    else:
                        force_magnitude = CONFIG["gravity_constant"] * self.rocket.mass * body.mass / (distance ** 2)
                        force = force_magnitude * (delta / distance)
                        self.rocket.apply_force(force)
                    # Landing/crash detection
                    if distance < body.radius + self.rocket.radius:
                        relative_vel = np.linalg.norm(self.rocket.velocity - body.velocity)
                        if self.rocket.landed_on_planet != body:
                            if relative_vel > 30:
                                # Crash landing
                                self.rocket.take_damage(50)
                                self.create_explosion(self.rocket.position, 30)
                                normal = (self.rocket.position - body.position) / distance
                                self.rocket.velocity = self.rocket.velocity - 2 * np.dot(self.rocket.velocity, normal) * normal
                                self.rocket.velocity *= 0.3
                                # Auto-transition to surface scene (crash)
                                self.enter_planet_surface_scene(body, None, crash=True)
                            else:
                                # Soft landing
                                self.rocket.landed_on_planet = body
                                self.rocket.velocity = body.velocity.copy()
                                direction = (self.rocket.position - body.position) / distance
                                self.rocket.position = body.position + direction * (body.radius + self.rocket.radius)
        
        # Check for collisions with bullets
        for bullet in self.bullets[:]:
            # Check if bullet hits an enemy
            for enemy in self.enemies[:]:
                distance = np.linalg.norm(bullet.position - enemy.position)
                if distance < enemy.size and not bullet.hit:
                    # Register hit
                    bullet.hit = True
                    destroyed = enemy.take_damage(bullet.damage)
                    
                    if destroyed:
                        # Create explosion effect
                        self.create_explosion(enemy.position, 30)
                        
                        # Drop collectibles
                        for drop in enemy.drops:
                            collectible = Collectible(enemy.position, drop["type"], drop["value"])
                            self.collectibles.append(collectible)
                        
                        # Update mission if this was a target
                        if self.rocket.current_mission and self.rocket.current_mission["type"] == "destroy":
                            if enemy in self.rocket.mission_targets:
                                self.rocket.mission_progress += 1
                        
                        # Remove enemy
                        self.enemies.remove(enemy)
            
            # Check if bullet hits the player
            if bullet.color == (255, 50, 50):  # Only enemy bullets hit player
                distance = np.linalg.norm(bullet.position - self.rocket.position)
                if distance < self.rocket.radius and not bullet.hit:
                    bullet.hit = True
                    self.rocket.take_damage(bullet.damage)
                    
                    # Create small impact effect
                    self.create_explosion(bullet.position, 10)
        
        # Update rocket physics
        self.rocket.update(dt)
        
        # Update trajectory prediction
        self.rocket.update_trajectory(self.celestial_bodies, dt)
        
        # Update other celestial bodies
        for body in self.celestial_bodies:
            if isinstance(body, CelestialBody) and body != self.rocket:
                # Calculate gravity for each body
                for other in self.celestial_bodies:
                    if other != body and isinstance(other, CelestialBody):
                        delta = other.position - body.position
                        distance_sq = np.dot(delta, delta)
                        
                        if distance_sq > 1:
                            distance = np.sqrt(distance_sq)
                            force_magnitude = CONFIG["gravity_constant"] * body.mass * other.mass / distance_sq
                            force = force_magnitude * (delta / distance)
                            body.apply_force(force)
                
                # Update position - handle different update method signatures
                if isinstance(body, Star):
                    body.update(dt, self.particle_system)
                elif isinstance(body, (BlackHole, Wormhole, Pulsar)):
                    body.update(dt, self.particle_system)
                elif isinstance(body, Planet):
                    body.update(dt)
                else:
                    # For other celestial bodies, just update position
                    body.update_position(dt)
        
        # Update bullets
        self.bullets = [b for b in self.bullets if b.update(dt)]
        
        # Update enemies
        for enemy in self.enemies:
            enemy.set_target(self.rocket)
            enemy.update(dt, self.bullets)
        
        # Update collectibles
        for item in self.collectibles[:]:
            if not item.update(dt):
                self.collectibles.remove(item)
                continue
                
            # Check if player collects item
            distance = np.linalg.norm(item.position - self.rocket.position)
            if distance < self.rocket.radius + item.radius and item.active:
                self.rocket.collect_item(item)
                item.collect()
                
                # Check if this was a mission item
                if self.rocket.current_mission and self.rocket.current_mission["type"] == "collect":
                    if item.type == "mission_item" and item in self.rocket.mission_targets:
                        self.rocket.mission_progress += 1
                
                # Remove from collectibles list
                self.collectibles.remove(item)
        
        # Update nebulae
        for nebula in self.nebulae:
            nebula.update(dt)
            
            # Check if player is inside nebula
            if nebula.is_inside(self.rocket.position):
                # Apply nebula effects
                
                # Slow down movement
                self.rocket.velocity *= (1.0 - nebula.speed_reduction * dt)
                
                # Chance to damage ship
                if random.random() < nebula.damage_chance * dt:
                    self.rocket.take_damage(1)
                
                # Create particle effect
                if random.random() < 0.1:
                    offset = np.array([random.uniform(-20, 20), random.uniform(-20, 20)])
                    pos = self.rocket.position + offset
                    vel = np.array([random.uniform(-5, 5), random.uniform(-5, 5)])
                    color = nebula.color + (100,)
                    self.particle_system.add_particle(Particle(pos, vel, color, random.uniform(0.5, 1.5), random.uniform(2, 4)))
        
        # Update mission objectives
        if self.rocket.current_mission:
            self.rocket.update_mission(dt)
            
            # Check for "explore" mission objectives
            if self.rocket.current_mission["type"] == "explore":
                for target in self.rocket.mission_targets:
                    if isinstance(target, dict) and "position" in target and not target.get("discovered", False):
                        distance = np.linalg.norm(target["position"] - self.rocket.position)
                        if distance < target["radius"]:
                            target["discovered"] = True
                            self.rocket.mission_progress += 1
            
            # Check for "deliver" mission objectives
            elif self.rocket.current_mission["type"] == "deliver":
                for target in self.rocket.mission_targets:
                    if isinstance(target, dict) and "position" in target and not target.get("delivered", False):
                        distance = np.linalg.norm(target["position"] - self.rocket.position)
                        if distance < target["radius"]:
                            target["delivered"] = True
                            self.rocket.mission_progress += 1
        
        # Update space stations
        for station in self.space_stations:
            station.update(dt, self.particle_system)
            
            # Check for docking
            if station.docking_available:
                distance = np.linalg.norm(station.position - self.rocket.position)
                if distance < station.radius + self.rocket.radius * 5:
                    station_speed = np.linalg.norm(station.position - self.rocket.position)
                    
                    # Player is close enough to dock
                    if distance < station.radius + self.rocket.radius * 2 and station_speed < 5:
                        # Auto-repair and refuel
                        self.rocket.health = min(self.rocket.health + 1, self.rocket.max_health)
                        self.rocket.fuel = min(self.rocket.fuel + 1, self.rocket.max_fuel)
        
        # Update cooldown timers
        if self.rocket.fire_rate_timer > 0:
            self.rocket.fire_rate_timer -= dt
        
        if self.rocket.damage_flash_timer > 0:
            self.rocket.damage_flash_timer -= dt
        
        # Check game over condition
        if self.rocket.health <= 0:
            self.game_over = True
        
        # Update particles
        self.particle_system.update(dt)
        self.particle_system.particles = sorted(self.particle_system.particles, key=lambda p: np.linalg.norm(p.position - self.rocket.position))[:100]
    
    def create_explosion(self, position, particle_count):
        """Create an explosion effect at the given position."""
        for _ in range(particle_count):
            vel = np.array([random.uniform(-50, 50), random.uniform(-50, 50)])
            color = (255, random.randint(100, 200), 0, 200)
            lifetime = random.uniform(0.5, 1.0)
            size = random.uniform(2.0, 4.0)
            
            self.particle_system.add_particle(Particle(position, vel, color, lifetime, size))
    
    def spawn_enemies(self):
        """Spawn enemies periodically."""
        if len(self.enemies) < CONFIG["enemy_count_max"] and random.random() < 0.01:
            # Spawn away from player but in view
            angle = random.uniform(0, 2 * np.pi)
            distance = random.uniform(1000, 2000)
            position = self.rocket.position + np.array([math.cos(angle), math.sin(angle)]) * distance
            
            enemy = Enemy(position)
            self.enemies.append(enemy)
    
    def update(self):
        """Main update loop."""
        # Always process events and get key state
        pygame.event.pump()
        keys = pygame.key.get_pressed()
        current_time = pygame.time.get_ticks()
        frame_time = (current_time - self.last_time) / 1000.0
        self.last_time = current_time
        if frame_time > 0.25:
            frame_time = 0.25
        self.accumulated_time += frame_time
        while self.accumulated_time >= self.fixed_time_step:
            if self.fade_direction != 0:
                fade_speed = 400 * self.fixed_time_step
                self.fade_alpha += self.fade_direction * fade_speed
                if self.fade_direction < 0 and self.fade_alpha <= 0:
                    self.fade_alpha = 0
                    self.fade_direction = 0
                    self.scene_transition = None
                    if self.scene == "space":
                        self.camera.set_target(self.rocket)
                        self.camera.position = self.rocket.position.copy()
                    elif self.scene == "planet_surface" and self.planet_surface_scene:
                        pass
                elif self.fade_direction > 0 and self.fade_alpha >= 255:
                    self.fade_alpha = 255
                    if self.scene_transition == "to_space":
                        self._do_space_scene_switch()
                    elif self.scene_transition == "to_planet_surface":
                        self._do_planet_surface_scene_switch()
            else:
                if self.scene == "planet_surface" and self.planet_surface_scene:
                    self.planet_surface_scene.update(self.fixed_time_step, keys)
                elif self.scene == "space":
                    self.handle_input()
                    if not self.paused and not self.game_over:
                        self.update_physics(self.fixed_time_step)
                        self.spawn_enemies()
                        self.rocket.update_trajectory(self.celestial_bodies, self.fixed_time_step)
                        self.particle_system.update(self.fixed_time_step)
            self.accumulated_time -= self.fixed_time_step
        if self.scene == "space":
            self.camera.update()
        if self.game_over:
            self.running = False

    def render(self):
        """Render all game elements."""
        # Only render the active scene
        if self.scene == "planet_surface" and self.planet_surface_scene:
            self.planet_surface_scene.render(self.screen)
        elif self.scene == "space":
            self.screen.fill(CONFIG["background_color"])
            self.background.draw(self.screen, self.camera)
            render_distance = 1200 * self.camera.zoom  # Aggressively reduced
            for body in self.celestial_bodies:
                # Only draw gravity/atmosphere rings for actual planets, and only via their draw method
                if isinstance(body, Planet):
                    distance = np.linalg.norm(body.position - self.rocket.position)
                    if distance < render_distance:
                        body.draw(self.screen, self.camera)
                elif isinstance(body, CelestialBody):
                    # For other celestial bodies, draw as usual (no gravity/atmosphere rings)
                    distance = np.linalg.norm(body.position - self.rocket.position)
                    if distance < render_distance:
                        body.draw(self.screen, self.camera)
            for item in self.collectibles:
                distance = np.linalg.norm(item.position - self.rocket.position)
                if distance < render_distance:
                    item.draw(self.screen, self.camera)
            for enemy in self.enemies:
                distance = np.linalg.norm(enemy.position - self.rocket.position)
                if distance < render_distance:
                    enemy.draw(self.screen, self.camera)
            for bullet in self.bullets:
                distance = np.linalg.norm(bullet.position - self.rocket.position)
                if distance < render_distance:
                    bullet.draw(self.screen, self.camera)
            self.rocket.draw(self.screen, self.camera)
            for nebula in self.nebulae:
                distance = np.linalg.norm(nebula.position - self.rocket.position)
                if distance < render_distance:
                    nebula.draw(self.screen, self.camera)
            for station in self.space_stations:
                distance = np.linalg.norm(station.position - self.rocket.position)
                if distance < render_distance:
                    station.draw(self.screen, self.camera)
            self.particle_system.draw(self.screen, self.camera)
            self.ui.draw_hud(self.screen, self.rocket)
            self.ui.draw_minimap(self.screen, self.rocket, self.celestial_bodies, self.camera)
            self.ui.draw_target_info(self.screen, self.selected_target)
            self.ui.draw_map_screen(self.screen, self.rocket, self.celestial_bodies, self.camera)
            self.ui.draw_inventory_screen(self.screen, self.rocket)
            self.ui.draw_missions_screen(self.screen, self.rocket)
            if self.landing_prompt and self.landing_prompt_active:
                font = pygame.font.SysFont(None, 36)
                prompt_surf = font.render(self.landing_prompt, True, (255, 255, 0))
                prompt_bg = pygame.Surface((prompt_surf.get_width()+40, prompt_surf.get_height()+30), pygame.SRCALPHA)
                prompt_bg.fill((0,0,0,200))
                x = self.screen_width//2 - prompt_surf.get_width()//2
                y = self.screen_height//2 - prompt_surf.get_height()//2
                self.screen.blit(prompt_bg, (x-20, y-15))
                self.screen.blit(prompt_surf, (x, y))
        # Fade overlay
        if self.fade_alpha > 0:
            fade_overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
            fade_overlay.fill((0, 0, 0, int(self.fade_alpha)))
            self.screen.blit(fade_overlay, (0, 0))
        pygame.display.flip()

    def run(self):
        """Run the main game loop."""
        while self.running:
            self.update()
            self.render()
            self.clock.tick(self.fps)

        # Game over screen
        if self.game_over:
            self.show_game_over_screen()

    def show_game_over_screen(self):
        """Display the game over screen."""
        self.screen.fill((0, 0, 0))
        game_over_text = self.ui.large_font.render("GAME OVER", True, (255, 0, 0))
        restart_text = self.ui.small_font.render("Press R to Restart or ESC to Quit", True, (255, 255, 255))
        self.screen.blit(game_over_text, (self.screen_width // 2 - game_over_text.get_width() // 2, self.screen_height // 2 - 50))
        self.screen.blit(restart_text, (self.screen_width // 2 - restart_text.get_width() // 2, self.screen_height // 2 + 20))
        pygame.display.flip()

        # Wait for player input
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                    elif event.key == pygame.K_r:
                        self.__init__()
                        self.run()

    def start_planet_surface_scene(self, planet, rocket_state=None):
        surface_x = 400
        surface_y = 480
        if rocket_state is None:
            rocket_state = {
                "fuel": self.rocket.fuel,
                "health": self.rocket.health,
                "max_health": self.rocket.max_health,
                "shield": self.rocket.shield,
                "max_shield": self.rocket.max_shield,
                "credits": self.rocket.credits,
                "position": planet.position.copy(),
                "velocity": np.zeros(2),
                "engine_level": self.rocket.engine_level,
                "weapon_level": self.rocket.weapon_level,
                "scanner_level": self.rocket.scanner_level,
            }
        if getattr(planet, 'biome_type', None) == 'desert':
            self.planet_surface_scene = DesertSurfaceScene(self, planet, rocket_state, spawn_player_pos=(surface_x, surface_y))
        elif getattr(planet, 'biome_type', None) == 'forest':
            self.planet_surface_scene = ForestSurfaceScene(self, planet, rocket_state, spawn_player_pos=(surface_x, surface_y))
        else:
            self.planet_surface_scene = BiomeSurfaceScene(self, planet, rocket_state, spawn_player_pos=(surface_x, surface_y))
        self.scene = "planet_surface"
        self.fade_alpha = 0
        self.fade_direction = 0
        self.next_scene = None
    def exit_planet_surface_scene(self, planet, rocket_state):
        # Start fade-out and set transition state
        self.scene_transition = "to_space"
        self.fade_direction = 1  # Fade out
        self.next_scene = (planet, rocket_state)
    def _do_space_scene_switch(self):
        planet, rocket_state = self.next_scene if self.next_scene else (None, None)
        direction = np.array([1.0, 0.0])
        self.rocket.position = planet.position + direction * (planet.radius + self.rocket.radius + 10)
        self.rocket.velocity = np.array([0, -200])
        self.rocket.landed_on_planet = None
        for k, v in rocket_state.items():
            if hasattr(self.rocket, k):
                setattr(self.rocket, k, v)
        self.scene = "space"
        self.planet_surface_scene = None
        self.camera.set_target(self.rocket)
        self.camera.position = self.rocket.position.copy()
        self.fade_direction = -1
        self.fade_alpha = 255
        self.scene_transition = None
        self.next_scene = None

    def enter_planet_surface_scene(self, planet, rocket_state=None, crash=False):
        # Start fade-out and set transition state
        self.scene_transition = "to_planet_surface"
        self.fade_direction = 1  # Fade out
        self.next_scene = (planet, rocket_state, crash)

    def _do_planet_surface_scene_switch(self):
        planet, rocket_state, crash = self.next_scene if self.next_scene else (None, None, False)
        surface_x = 400 if not crash else 600
        surface_y = 480
        if rocket_state is None:
            # Use rocket state from saved space state if available
            if self.saved_space_state:
                rocket_state = {
                    "fuel": self.saved_space_state['rocket'].fuel,
                    "health": self.saved_space_state['rocket'].health,
                    "max_health": self.saved_space_state['rocket'].max_health,
                    "shield": self.saved_space_state['rocket'].shield,
                    "max_shield": self.saved_space_state['rocket'].max_shield,
                    "credits": self.saved_space_state['rocket'].credits,
                    "position": planet.position.copy() if planet else np.zeros(2),
                    "velocity": np.zeros(2),
                    "engine_level": self.saved_space_state['rocket'].engine_level,
                    "weapon_level": self.saved_space_state['rocket'].weapon_level,
                    "scanner_level": self.saved_space_state['rocket'].scanner_level,
                }
            else:
                rocket_state = {
                    "fuel": self.rocket.fuel,
                    "health": self.rocket.health,
                    "max_health": self.rocket.max_health,
                    "shield": self.rocket.shield,
                    "max_shield": self.rocket.max_shield,
                    "credits": self.rocket.credits,
                    "position": planet.position.copy() if planet else np.zeros(2),
                    "velocity": np.zeros(2),
                    "engine_level": self.rocket.engine_level,
                    "weapon_level": self.rocket.weapon_level,
                    "scanner_level": self.rocket.scanner_level,
                }
        self.planet_surface_scene = PlanetSurfaceScene(self, planet, rocket_state, spawn_player_pos=(surface_x, surface_y))
        self.scene = "planet_surface"
        self.camera.set_target(None)
        # Start fade-in
        self.fade_direction = -1
        self.fade_alpha = 255
        self.scene_transition = None
        self.next_scene = None

    def save_space_state_and_land(self):
        import copy
        # Deep copy all relevant state
        self.saved_space_state = {
            'rocket': copy.deepcopy(self.rocket),
            'celestial_bodies': copy.deepcopy(self.celestial_bodies),
            'space_stations': copy.deepcopy(self.space_stations),
            'background': copy.deepcopy(self.background),
            'ui': copy.deepcopy(self.ui),
            'bullets': copy.deepcopy(self.bullets),
            'enemies': copy.deepcopy(self.enemies),
            'collectibles': copy.deepcopy(self.collectibles),
            'nebulae': copy.deepcopy(self.nebulae),
            'particle_system': copy.deepcopy(self.particle_system),
            'selected_target': copy.deepcopy(self.selected_target),
            'target_distance': self.target_distance,
            'scan_timer': self.scan_timer,
            'paused': self.paused,
            'game_over': self.game_over,
        }
        # Start fade-out and set transition state
        self.scene_transition = "to_planet_surface"
        self.fade_direction = 1
        self.next_scene = (self.landing_prompt_planet, None, False)

    def _do_space_scene_switch(self):
        planet, rocket_state = self.next_scene if self.next_scene else (None, None)
        # Restore all saved space state
        if self.saved_space_state:
            import copy
            self.rocket = copy.deepcopy(self.saved_space_state['rocket'])
            self.celestial_bodies = copy.deepcopy(self.saved_space_state['celestial_bodies'])
            self.space_stations = copy.deepcopy(self.saved_space_state['space_stations'])
            self.background = copy.deepcopy(self.saved_space_state['background'])
            self.ui = copy.deepcopy(self.saved_space_state['ui'])
            self.bullets = copy.deepcopy(self.saved_space_state['bullets'])
            self.enemies = copy.deepcopy(self.saved_space_state['enemies'])
            self.collectibles = copy.deepcopy(self.saved_space_state['collectibles'])
            self.nebulae = copy.deepcopy(self.saved_space_state['nebulae'])
            self.particle_system = copy.deepcopy(self.saved_space_state['particle_system'])
            self.selected_target = copy.deepcopy(self.saved_space_state['selected_target'])
            self.target_distance = self.saved_space_state['target_distance']
            self.scan_timer = self.saved_space_state['scan_timer']
            self.paused = self.saved_space_state['paused']
            self.game_over = self.saved_space_state['game_over']
            # Place rocket just above planet
            direction = np.array([1.0, 0.0])
            if planet is not None:
                self.rocket.position = planet.position + direction * (planet.radius + self.rocket.radius + 10)
            self.rocket.velocity = np.array([0, -200])
            self.rocket.landed_on_planet = None
            if rocket_state:
                for k, v in rocket_state.items():
                    if hasattr(self.rocket, k):
                        setattr(self.rocket, k, v)
            self.scene = "space"
            self.planet_surface_scene = None
            self.camera.set_target(self.rocket)
            self.camera.position = self.rocket.position.copy()
            self.fade_direction = -1
            self.fade_alpha = 255
            self.scene_transition = None
            self.next_scene = None
            self.saved_space_state = None
        else:
            # fallback: old behavior
            direction = np.array([1.0, 0.0])
            self.rocket.position = planet.position + direction * (planet.radius + self.rocket.radius + 10)
            self.rocket.velocity = np.array([0, -200])
            self.rocket.landed_on_planet = None
            for k, v in rocket_state.items():
                if hasattr(self.rocket, k):
                    setattr(self.rocket, k, v)
            self.scene = "space"
            self.planet_surface_scene = None
            self.camera.set_target(self.rocket)
            self.camera.position = self.rocket.position.copy()
            self.fade_direction = -1
            self.fade_alpha = 255
            self.scene_transition = None
            self.next_scene = None

# --- Modular PlanetSurfaceScene ---
class PlanetSurfaceScene:
    def __init__(self, game, planet, rocket_state, spawn_player_pos=(400, 480)):
        self.game = game
        self.planet = planet
        self.rocket_state = rocket_state.copy()
        self.width = 2000
        self.height = 600
        self.surface_scroll = 0
        self.player = SurfacePlayer(self, rocket_state, spawn_player_pos)
        self.ship_pos = [400, self.height - 120]
        self.enter_ship_prompt = False
        self.prompt_timer = 0
        self.prompt_active = False
        self.transitioning = False
        self.ambient_elements = self.generate_ambient_elements()
    def generate_ambient_elements(self):
        # Generate simple terrain bumps, rocks, and plants
        elements = []
        for i in range(20):
            x = random.randint(50, self.width - 50)
            y = self.height - 100 + random.randint(-10, 10)
            kind = random.choice(["rock", "plant", "bump"])
            elements.append((x, y, kind))
        return elements
    def update(self, dt, keys):
        self.player.update(dt, keys)
        dist = abs(self.player.x - self.ship_pos[0])
        if dist < 60:
            self.enter_ship_prompt = True
            if not self.prompt_active:
                self.prompt_timer += dt
                if self.prompt_timer > 0.2:
                    self.prompt_active = True
        else:
            self.enter_ship_prompt = False
            self.prompt_active = False
            self.prompt_timer = 0
        if self.prompt_active and keys[pygame.K_e] and not self.transitioning:
            self.transitioning = True
            self.game.exit_planet_surface_scene(self.planet, self.rocket_state)
        if self.transitioning:
            return
    def render(self, surface):
        # Sky/atmosphere
        surface.fill((30, 30, 60))
        # Terrain
        pygame.draw.rect(surface, (60, 40, 20), (0, self.height - 100, self.width, 100))
        # Ambient elements
        for x, y, kind in self.ambient_elements:
            if kind == "rock":
                pygame.draw.circle(surface, (100, 100, 100), (x, y), 12)
            elif kind == "plant":
                pygame.draw.rect(surface, (50, 200, 50), (x, y - 18, 6, 18))
            elif kind == "bump":
                pygame.draw.ellipse(surface, (80, 60, 30), (x - 18, y - 6, 36, 12))
        # Landed rocket
        ship_rect = pygame.Rect(self.ship_pos[0] - 40, self.height - 140, 80, 40)
        pygame.draw.rect(surface, (180, 180, 200), ship_rect)
        pygame.draw.polygon(surface, (200, 200, 255), [
            (self.ship_pos[0] - 40, self.height - 140),
            (self.ship_pos[0] + 40, self.height - 140),
            (self.ship_pos[0], self.height - 170)
        ])
        # Player
        self.player.render(surface)
        # Prompt
        if self.enter_ship_prompt and self.prompt_active:
            font = pygame.font.SysFont(None, 32)
            prompt = font.render("Enter Rocket? (Press E)", True, (255, 255, 0))
            surface.blit(prompt, (self.ship_pos[0] - prompt.get_width()//2, self.height - 180))
        # Info
        font = pygame.font.SysFont(None, 28)
        info = font.render(f"{self.planet.name} Surface", True, (200, 200, 255))
        surface.blit(info, (20, 20))
    def get_rocket_state(self):
        state = self.rocket_state.copy()
        state["health"] = self.player.health
        state["fuel"] = self.player.fuel
        state["position"] = self.planet.position.copy()
        return state
class SurfacePlayer:
    def __init__(self, surface_scene, rocket_state, spawn_player_pos):
        self.scene = surface_scene
        self.x, self.y = spawn_player_pos
        self.vx = 0
        self.vy = 0
        self.width = 32
        self.height = 48
        self.on_ground = True
        self.health = rocket_state["health"]
        self.fuel = rocket_state["fuel"]
        self.speed = 220
        self.jump_power = 350
        self.gravity = 900
        self.color = (100, 255, 100)
    def update(self, dt, keys):
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vx = -self.speed
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vx = self.speed
        else:
            self.vx = 0
        if self.on_ground and (keys[pygame.K_UP] or keys[pygame.K_w] or keys[pygame.K_SPACE]):
            self.vy = -self.jump_power
            self.on_ground = False
        self.vy += self.gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.y > self.scene.height - 120:
            self.y = self.scene.height - 120
            self.vy = 0
            self.on_ground = True
        self.x = max(0, min(self.scene.width, self.x))
    def render(self, surface):
        rect = pygame.Rect(self.x - self.width//2, self.y - self.height, self.width, self.height)
        pygame.draw.rect(surface, self.color, rect)
        font = pygame.font.SysFont(None, 20)
        health = font.render(f"HP: {self.health}", True, (255, 100, 100))
        fuel = font.render(f"Fuel: {int(self.fuel)}", True, (100, 255, 255))
        surface.blit(health, (rect.x, rect.y - 22))
        surface.blit(fuel, (rect.x, rect.y - 10))

class BiomeSurfaceScene:
    def __init__(self, game, planet, rocket_state, spawn_player_pos=(400, 480)):
        self.game = game
        self.planet = planet
        self.rocket_state = rocket_state.copy()
        self.width = 2000
        self.height = 600
        self.surface_scroll = 0
        # Default ground setup
        self.sand_top_y = int(self.height * 0.6)
        self.sand_height = self.height - self.sand_top_y
        self.player = SurfacePlayer(self, rocket_state, (spawn_player_pos[0], self.sand_top_y))
        self.ship_pos = [400, self.height - 120]
        self.enter_ship_prompt = False
        self.prompt_timer = 0
        self.prompt_active = False
        self.transitioning = False
        self.ambient_elements = []
        self.background_layers = []
        self.hazards = []
        self.dust_storm_timer = 0
        self.dust_storm_active = False
        self.dust_storm_alpha = 0
        self.load_assets()
        self.generate_terrain_and_props()
    def load_assets(self):
        # No assets for generic biome
        self.sand_color = (200, 180, 120)
        self.sky_color = (120, 180, 255)
    def generate_terrain_and_props(self):
        # Simple ground and no props
        self.sand_top_y = int(self.height * 0.6)
        self.sand_height = self.height - self.sand_top_y
    def update(self, dt, keys):
        self.player.update(dt, keys)
        dist = abs(self.player.x - self.ship_pos[0])
        if dist < 60:
            self.enter_ship_prompt = True
            if not self.prompt_active:
                self.prompt_timer += dt
                if self.prompt_timer > 0.2:
                    self.prompt_active = True
        else:
            self.enter_ship_prompt = False
            self.prompt_active = False
            self.prompt_timer = 0
        if self.prompt_active and keys[pygame.K_e] and not self.transitioning:
            self.transitioning = True
            self.game.exit_planet_surface_scene(self.planet, self.rocket_state)
    def render(self, surface):
        # Simple sky
        surface.fill(self.sky_color)
        # Simple sand ground
        pygame.draw.rect(surface, self.sand_color, (0, self.sand_top_y, self.width, self.sand_height))
        # Landed rocket
        ship_rect = pygame.Rect(self.ship_pos[0] - 40, self.height - 140, 80, 40)
        pygame.draw.rect(surface, (180, 180, 200), ship_rect)
        pygame.draw.polygon(surface, (200, 200, 255), [
            (self.ship_pos[0] - 40, self.height - 140),
            (self.ship_pos[0] + 40, self.height - 140),
            (self.ship_pos[0], self.height - 170)
        ])
        # Player
        self.player.render(surface)
        # Prompt
        if self.enter_ship_prompt and self.prompt_active:
            font = pygame.font.SysFont(None, 32)
            prompt = font.render("Enter Rocket? (Press E)", True, (255, 255, 0))
            surface.blit(prompt, (self.ship_pos[0] - prompt.get_width()//2, self.sand_top_y - 60))
        # Info
        font = pygame.font.SysFont(None, 28)
        info = font.render(f"{self.planet.name} Surface", True, (200, 200, 255))
        surface.blit(info, (20, 20))
    def get_rocket_state(self):
        state = self.rocket_state.copy()
        state["health"] = self.player.health
        state["fuel"] = self.player.fuel
        state["position"] = self.planet.position.copy()
        return state

class DesertSurfaceScene(BiomeSurfaceScene):
    def load_assets(self):
        self.asset_dir = os.path.join("Assets", "desert")
        try:
            self.sand_img = pygame.image.load(os.path.join(self.asset_dir, "sand.png")).convert_alpha()
        except Exception:
            self.sand_img = pygame.Surface((100, 100))
            self.sand_img.fill((200, 180, 120))
        try:
            self.bg_img = pygame.image.load(os.path.join(self.asset_dir, "desertbackground.png")).convert_alpha()
        except Exception:
            self.bg_img = pygame.Surface((200, 100))
            self.bg_img.fill((220, 200, 180))
        self.cactus_imgs = []
        for i in range(1, 5):
            try:
                img = pygame.image.load(os.path.join(self.asset_dir, f"cactus{i}.png")).convert_alpha()
            except Exception:
                img = pygame.Surface((24, 48))
                img.fill((60, 200, 60))
            self.cactus_imgs.append(img)
        self.rock_imgs = []
        for i in range(1, 3):
            try:
                img = pygame.image.load(os.path.join(self.asset_dir, f"rock{i}.png")).convert_alpha()
            except Exception:
                img = pygame.Surface((32, 20))
                img.fill((120, 120, 120))
            self.rock_imgs.append(img)
        self.sun_img = pygame.Surface((120, 120), pygame.SRCALPHA)
        pygame.draw.circle(self.sun_img, (255, 255, 180, 220), (60, 60), 60)
    def generate_terrain_and_props(self):
        # --- Sand ground setup ---
        self.sand_top_y = int(self.height * 0.6)  # Player feet Y
        self.sand_height = self.height - self.sand_top_y
        # Scale sand.png to cover from sand_top_y to bottom of window, and tile horizontally
        sand_tile_w = self.sand_img.get_width()
        sand_scaled = pygame.transform.scale(self.sand_img, (sand_tile_w, self.sand_height))
        self.sand_tiles = []
        for i in range((self.width // sand_tile_w) + 3):
            self.sand_tiles.append({'img': sand_scaled, 'x': i * sand_tile_w, 'y': self.sand_top_y})
        # --- Dune background setup ---
        dune_h = self.bg_img.get_height()
        dune_w = self.bg_img.get_width()
        # Position dunes so their bottom edge aligns with sand top
        dune_y = self.sand_top_y - dune_h
        self.dune_tiles = []
        for i in range((self.width // dune_w) + 3):
            self.dune_tiles.append({'img': self.bg_img, 'x': i * dune_w, 'y': dune_y})
        # --- Sky gradient setup ---
        self.sky_gradient = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        for y in range(self.height):
            t = y / self.height
            r = int(255 * (1-t) + 255 * t)
            g = int(120 * (1-t) + 220 * t)
            b = int(40 * (1-t) + 180 * t)
            a = 255
            pygame.draw.line(self.sky_gradient, (r, g, b, a), (0, y), (self.width, y))
        # --- Sun animation ---
        self.sun_base_x = self.width // 2
        self.sun_base_y = self.sand_top_y - 40
        # --- Prop placement with Z-layering ---
        self.props_behind = []
        self.props_infront = []
        ground_y = self.sand_top_y  # Top of sand, player feet Y
        for i in range(16):
            img = random.choice(self.cactus_imgs + self.rock_imgs)
            scale = random.uniform(0.7, 1.2)
            prop_img = pygame.transform.rotozoom(img, random.uniform(-10, 10), scale)
            prop_w, prop_h = prop_img.get_size()
            x = random.randint(60, self.width - 60)
            y = ground_y + self.sand_height  # Place bottom of prop flush with sand top
            rect = prop_img.get_rect(midbottom=(x, y))
            z = random.choices(['behind', 'infront'], weights=[70, 30])[0]
            if z == 'behind':
                self.props_behind.append({'img': prop_img, 'rect': rect})
            else:
                self.props_infront.append({'img': prop_img, 'rect': rect})
            # Hazards only for cacti behind/infront
            if img in self.cactus_imgs:
                self.hazards.append({'type': 'cactus', 'rect': rect})
        # Add sand pits (hazards)
        for i in range(2):
            pit_x = random.randint(200, self.width - 200)
            pit_rect = pygame.Rect(pit_x, self.sand_top_y + self.sand_height - 30, 60, 18)
            self.hazards.append({'type': 'sandpit', 'rect': pit_rect})
    def render(self, surface):
        # --- Sky gradient (furthest back) ---
        surface.blit(self.sky_gradient, (0, 0))
        # --- Sun animation (on horizon) ---
        sun_x = self.sun_base_x + 120 * math.sin(pygame.time.get_ticks() * 0.00015)
        sun_y = self.sun_base_y + 10 * math.cos(pygame.time.get_ticks() * 0.0002)
        surface.blit(self.sun_img, (sun_x - 60, sun_y - 60), special_flags=pygame.BLEND_ADD)
        # --- Dune background (behind sand, above sky) ---
        for dune in self.dune_tiles:
            surface.blit(dune['img'], (dune['x'], dune['y']))
        # --- Sand ground (flat, walkable) ---
        for tile in self.sand_tiles:
            surface.blit(tile['img'], (tile['x'], tile['y']))
        # --- Sand pits (hazards) ---
        for hazard in self.hazards:
            if hazard['type'] == 'sandpit':
                pygame.draw.ellipse(surface, (220, 200, 120), hazard['rect'])
        # --- Props behind player ---
        for prop in self.props_behind:
            surface.blit(prop['img'], prop['rect'])
        # --- Player (always in front of behind props, behind infront props) ---
        self.player.render(surface)
        # --- Props in front of player ---
        for prop in self.props_infront:
            surface.blit(prop['img'], prop['rect'])
        # --- Prompt ---
        if self.enter_ship_prompt and self.prompt_active:
            font = pygame.font.SysFont(None, 32)
            prompt = font.render("Enter Rocket? (Press E)", True, (255, 255, 0))
            surface.blit(prompt, (self.ship_pos[0] - prompt.get_width()//2, self.sand_top_y - 60))
        # --- Info ---
        font = pygame.font.SysFont(None, 28)
        info = font.render(f"{self.planet.name} Surface (Desert)", True, (200, 200, 255))
        surface.blit(info, (20, 20))
        # --- Dust storm overlay ---
        if self.dust_storm_alpha > 0:
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((200, 180, 120, int(self.dust_storm_alpha)))
            surface.blit(overlay, (0, 0))

class ForestSurfaceScene(BiomeSurfaceScene):
    def load_assets(self):
        self.asset_dir = os.path.join("assets", "forest")
        # Use 'foor1.png' as the ground (assume typo for 'floor1.png')
        try:
            self.ground_img = pygame.image.load(os.path.join(self.asset_dir, "foor1.png")).convert_alpha()
        except Exception:
            self.ground_img = pygame.Surface((100, 100))
            self.ground_img.fill((80, 120, 60))
        try:
            self.bg_img = pygame.image.load(os.path.join(self.asset_dir, "forestbackground.png")).convert_alpha()
        except Exception:
            self.bg_img = pygame.Surface((200, 100))
            self.bg_img.fill((60, 100, 40))
        self.prop_imgs = []
        for name in ["Tree1.png", "Tree2.png", "Tree3.png", "log.png"]:
            try:
                img = pygame.image.load(os.path.join(self.asset_dir, name)).convert_alpha()
            except Exception:
                img = pygame.Surface((32, 48))
                img.fill((60, 120, 60))
            self.prop_imgs.append(img)
    def generate_terrain_and_props(self):
        self.sand_top_y = int(self.height * 0.6)
        self.sand_height = self.height - self.sand_top_y
        # --- Ground tiling ---
        ground_tile_w = self.ground_img.get_width()
        ground_tile_h = self.ground_img.get_height()
        ground_scaled = pygame.transform.scale(self.ground_img, (ground_tile_w, self.sand_height))
        self.ground_tiles = []
        for i in range((self.width // ground_tile_w) + 3):
            self.ground_tiles.append({'img': ground_scaled, 'x': i * ground_tile_w, 'y': self.sand_top_y})
        # --- Background tiling ---
        bg_h = self.bg_img.get_height()
        bg_w = self.bg_img.get_width()
        bg_y = self.sand_top_y - bg_h
        self.bg_tiles = []
        for i in range((self.width // bg_w) + 3):
            self.bg_tiles.append({'img': self.bg_img, 'x': i * bg_w, 'y': bg_y})
        # --- Sky gradient ---
        self.sky_gradient = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        for y in range(self.height):
            t = y / self.height
            r = int(80 * (1-t) + 120 * t)
            g = int(140 * (1-t) + 200 * t)
            b = int(60 * (1-t) + 120 * t)
            a = 255
            pygame.draw.line(self.sky_gradient, (r, g, b, a), (0, y), (self.width, y))
        # --- Prop placement with Z-layering ---
        self.props_behind = []
        self.props_infront = []
        ground_y = self.sand_top_y
        for i in range(16):
            img = random.choice(self.prop_imgs)
            scale = random.uniform(0.7, 1.2)
            prop_img = pygame.transform.rotozoom(img, random.uniform(-10, 10), scale)
            prop_w, prop_h = prop_img.get_size()
            x = random.randint(60, self.width - 60)
            y = ground_y + self.sand_height
            rect = prop_img.get_rect(midbottom=(x, y))
            z = random.choices(['behind', 'infront'], weights=[70, 30])[0]
            if z == 'behind':
                self.props_behind.append({'img': prop_img, 'rect': rect})
            else:
                self.props_infront.append({'img': prop_img, 'rect': rect})
    def render(self, surface):
        # --- Sky gradient (furthest back) ---
        surface.blit(self.sky_gradient, (0, 0))
        # --- Forest background (behind sand, above sky) ---
        for bg in self.bg_tiles:
            surface.blit(bg['img'], (bg['x'], bg['y']))
        # --- Ground (walkable) ---
        for tile in self.ground_tiles:
            surface.blit(tile['img'], (tile['x'], tile['y']))
        # --- Props behind player ---
        for prop in self.props_behind:
            surface.blit(prop['img'], prop['rect'])
        # --- Player ---
        self.player.render(surface)
        # --- Props in front of player ---
        for prop in self.props_infront:
            surface.blit(prop['img'], prop['rect'])
        # --- Prompt ---
        if self.enter_ship_prompt and self.prompt_active:
            font = pygame.font.SysFont(None, 32)
            prompt = font.render("Enter Rocket? (Press E)", True, (255, 255, 0))
            surface.blit(prompt, (self.ship_pos[0] - prompt.get_width()//2, self.sand_top_y - 60))
        # --- Info ---
        font = pygame.font.SysFont(None, 28)
        info = font.render(f"{self.planet.name} Surface (Forest)", True, (200, 255, 200))
        surface.blit(info, (20, 20))
    def get_rocket_state(self):
        state = self.rocket_state.copy()
        state["health"] = self.player.health
        state["fuel"] = self.player.fuel
        state["position"] = self.planet.position.copy()
        return state

# Integrate ForestSurfaceScene into planet surface logic
# In start_planet_surface_scene, add:
# if getattr(planet, 'biome_type', None) == 'forest':
#     self.planet_surface_scene = ForestSurfaceScene(self, planet, rocket_state, spawn_player_pos=(surface_x, surface_y))

# Start the game
if __name__ == "__main__":
    game = Game()
    game.run()