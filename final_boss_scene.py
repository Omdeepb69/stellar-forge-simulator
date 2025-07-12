import pygame
import math
import os

class FinalBossScene:
    """Multi-phase final boss battle scene after collecting all 3 items."""
    
    def __init__(self, game):
        self.game = game
        self.width = game.screen_width
        self.height = game.screen_height
        
        # Phase management
        self.current_phase = 1
        self.phase_timer = 0
        self.phase_transition_timer = 0
        self.is_transitioning = False
        self.phase_complete = False
        
        # Player state
        self.player_health = game.rocket.health
        self.player_max_health = game.rocket.max_health
        self.player_position = [100, self.height - 150]  # Start near ground
        self.player_facing_right = True
        self.player_sword_drawn = False
        self.player_sword_swinging = False
        self.player_sword_timer = 0
        self.player_sword_cooldown = 0
        self.player_sword_frame = 0
        
        # Boss state
        self.boss_health = 100
        self.boss_max_health = 100
        self.boss_position = [self.width // 2, self.height // 2]
        self.boss_facing_right = False
        self.boss_sword_swinging = False
        self.boss_sword_timer = 0
        self.boss_attack_timer = 0
        self.boss_attack_cooldown = 2.0
        self.boss_floating_offset = 0
        self.boss_sword_frame = 0
        
        # Combat entities
        self.aliens = []
        self.alien_bullets = []
        self.boss_bullets = []
        self.player_bullets = []
        
        # Victory state
        self.boss_defeated = False
        self.victory_timer = 0
        
        # Fade effects
        self.fade_alpha = 255  # Start with fade in
        self.fade_direction = -1  # Fade in
        self.fade_speed = 255  # 1 second fade
        
        # Load assets
        self.load_assets()
        self.setup_environment()
        
        # Initialize first phase
        self.start_phase(1)
        
        print("[FinalBossScene] Multi-phase boss battle initialized")
    
    def load_assets(self):
        """Load all boss battle assets with error handling."""
        try:
            # Boss fight environment assets
            self.background_img = pygame.image.load("assets/boss_fight/background.png").convert_alpha()
            self.background_img = pygame.transform.scale(self.background_img, (self.width, self.height))
            
            self.pillar_img = pygame.image.load("assets/boss_fight/pillar.png").convert_alpha()
            self.pillar_img = pygame.transform.scale(self.pillar_img, (120, 300))
            
            self.skull_img = pygame.image.load("assets/boss_fight/skull.png").convert_alpha()
            self.skull_img = pygame.transform.scale(self.skull_img, (40, 40))
            
            self.testtube_img = pygame.image.load("assets/boss_fight/testtube.png").convert_alpha()
            self.testtube_img = pygame.transform.scale(self.testtube_img, (30, 50))
            
            # Alien assets
            self.alien_img = pygame.image.load("assets/alien/alien.png").convert_alpha()
            self.alien_img = pygame.transform.scale(self.alien_img, (60, 60))
            
            self.alien_orb_img = pygame.image.load("assets/alien/orb.png").convert_alpha()
            self.alien_orb_img = pygame.transform.scale(self.alien_orb_img, (20, 20))
            
            # Final boss assets
            self.boss_gun_img = pygame.image.load("assets/finalboss/bossGun.png").convert_alpha()
            self.boss_gun_img = pygame.transform.scale(self.boss_gun_img, (120, 120))
            
            self.boss_orb_img = pygame.image.load("assets/finalboss/orb.png").convert_alpha()
            self.boss_orb_img = pygame.transform.scale(self.boss_orb_img, (30, 30))
            
            # Boss sword swing animation
            self.boss_swing_frames = []
            for i in range(1, 5):
                frame = pygame.image.load(f"assets/finalboss/boss_swing/bossSwordSwing{i}.png").convert_alpha()
                frame = pygame.transform.scale(frame, (100, 100))
                self.boss_swing_frames.append(frame)
            
            # Player assets (reuse from surface scenes)
            try:
                self.player_idle_img = pygame.image.load("assets/player/mainCharStill.png").convert_alpha()
            except:
                self.player_idle_img = pygame.image.load("assets/player/idle.png").convert_alpha()
            self.player_idle_img = pygame.transform.scale(self.player_idle_img, (50, 80))
            
            # Load sword frames
            self.player_sword_frames = []
            for i in range(1, 5):
                try:
                    frame = pygame.image.load(f"assets/player/swing/swordSwing{i}.png").convert_alpha()
                    frame = pygame.transform.scale(frame, (60, 80))
                    self.player_sword_frames.append(frame)
                except:
                    # Create placeholder sword frame if not found
                    frame = pygame.Surface((60, 80), pygame.SRCALPHA)
                    pygame.draw.rect(frame, (255, 255, 0), (20, 20, 40, 60))
                    self.player_sword_frames.append(frame)
            
            print("[FinalBossScene] All assets loaded successfully")
            
        except Exception as e:
            print(f"[FinalBossScene] Error loading assets: {e}")
            self.create_placeholder_assets()
    
    def create_placeholder_assets(self):
        """Create placeholder assets if loading fails."""
        # Background
        self.background_img = pygame.Surface((self.width, self.height))
        self.background_img.fill((20, 10, 30))
        
        # Pillar
        self.pillar_img = pygame.Surface((120, 300))
        self.pillar_img.fill((100, 100, 100))
        
        # Skull and testtube
        self.skull_img = pygame.Surface((40, 40))
        self.skull_img.fill((150, 150, 150))
        
        self.testtube_img = pygame.Surface((30, 50))
        self.testtube_img.fill((0, 255, 255))
        
        # Alien
        self.alien_img = pygame.Surface((60, 60))
        self.alien_img.fill((0, 255, 0))
        
        self.alien_orb_img = pygame.Surface((20, 20))
        self.alien_orb_img.fill((255, 255, 0))
        
        # Boss
        self.boss_gun_img = pygame.Surface((120, 120))
        self.boss_gun_img.fill((255, 0, 0))
        
        self.boss_orb_img = pygame.Surface((30, 30))
        self.boss_orb_img.fill((255, 100, 0))
        
        # Boss swing frames
        self.boss_swing_frames = []
        for i in range(4):
            frame = pygame.Surface((100, 100))
            frame.fill((255, 50, 50))
            self.boss_swing_frames.append(frame)
        
        # Player
        self.player_idle_img = pygame.Surface((50, 80))
        self.player_idle_img.fill((0, 255, 255))
        
        self.player_sword_frames = []
        for i in range(4):
            frame = pygame.Surface((60, 80))
            frame.fill((255, 255, 0))
            self.player_sword_frames.append(frame)
    
    def setup_environment(self):
        """Setup the boss battle environment with props."""
        # Floor level
        self.floor_y = self.height - 100
        
        # Pillar positions (symmetrical)
        self.pillars = [
            (100, self.floor_y - 250),  # Left pillar
            (self.width - 220, self.floor_y - 250)  # Right pillar
        ]
        
        # Scattered props
        self.props = [
            {"type": "skull", "pos": [200, self.floor_y - 50], "img": self.skull_img},
            {"type": "testtube", "pos": [300, self.floor_y - 60], "img": self.testtube_img},
            {"type": "skull", "pos": [self.width - 250, self.floor_y - 50], "img": self.skull_img},
            {"type": "testtube", "pos": [self.width - 350, self.floor_y - 60], "img": self.testtube_img},
            {"type": "skull", "pos": [self.width // 2 - 100, self.floor_y - 50], "img": self.skull_img},
            {"type": "testtube", "pos": [self.width // 2 + 100, self.floor_y - 60], "img": self.testtube_img}
        ]
    
    def start_phase(self, phase):
        """Start a new phase of the boss battle."""
        self.current_phase = phase
        self.phase_timer = 0
        self.is_transitioning = True
        self.phase_transition_timer = 0
        self.phase_complete = False
        
        # Clear existing entities
        self.aliens.clear()
        self.alien_bullets.clear()
        self.boss_bullets.clear()
        self.player_bullets.clear()
        
        if phase == 1:
            # Phase 1: 5 Alien Minions
            self.spawn_aliens(5)
            print("[FinalBossScene] Phase 1: Alien Minions")
            
        elif phase == 2:
            # Phase 2: Final Boss + 10 Alien Minions
            self.spawn_aliens(10)
            self.boss_position = [self.width // 2, self.height // 2]
            print("[FinalBossScene] Phase 2: Final Boss + Alien Minions")
            
        elif phase == 3:
            # Phase 3: Final Boss Sword Duel
            self.boss_position = [self.width // 2, self.height // 2]
            self.boss_health = 50  # Reset boss health for final phase
            print("[FinalBossScene] Phase 3: Final Boss Sword Duel")
    
    def spawn_aliens(self, count):
        """Spawn alien minions with varied positions and timing."""
        for i in range(count):
            x = 200 + (i * 150) % (self.width - 400)
            y = 150 + (i * 80) % (self.height // 2)
            alien = {
                "pos": [x, y],
                "health": 30,
                "max_health": 30,
                "facing_right": False,
                "floating_offset": i * 0.5,
                "attack_timer": i * 0.5,
                "attack_cooldown": 2.0 + (i % 3) * 0.5,
                "floating_speed": 2.0 + (i % 2) * 0.5
            }
            self.aliens.append(alien)
    
    def update(self, dt, keys):
        """Update boss battle logic."""
        # Update fade effect
        if self.fade_direction == -1:  # Fade in
            self.fade_alpha = max(0, self.fade_alpha - self.fade_speed * dt)
        elif self.fade_direction == 1:  # Fade out
            self.fade_alpha = min(255, self.fade_alpha + self.fade_speed * dt)
        
        # Handle victory state
        if self.boss_defeated:
            self.victory_timer += dt
            if self.victory_timer > 3.0:
                self.fade_direction = 1  # Fade out
                if self.fade_alpha >= 255:
                    print("[FinalBossScene] Congratulations! You have completed the game!")
                    self.game.running = False
            return
        
        # Handle phase transitions
        if self.is_transitioning:
            self.phase_transition_timer += dt
            if self.phase_transition_timer > 1.0:  # 1 second transition
                self.is_transitioning = False
                self.phase_transition_timer = 0
        
        # Update phase timer
        self.phase_timer += dt
        
        # Check phase completion conditions
        if self.current_phase == 1 and len(self.aliens) == 0:
            self.start_phase(2)
        elif self.current_phase == 2 and self.boss_health <= 0:
            self.start_phase(3)
        elif self.current_phase == 3 and self.boss_health <= 0:
            self.boss_defeated = True
            self.victory_timer = 0
        
        # Update player
        self.update_player(dt, keys)
        
        # Update boss
        self.update_boss(dt)
        
        # Update aliens
        self.update_aliens(dt)
        
        # Update projectiles
        self.update_projectiles(dt)
        
        # Check collisions
        self.check_collisions()
    
    def update_player(self, dt, keys):
        """Update player movement and combat."""
        # Player movement
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.player_position[0] -= 200 * dt
            self.player_facing_right = False
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.player_position[0] += 200 * dt
            self.player_facing_right = True
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.player_position[1] -= 200 * dt
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.player_position[1] += 200 * dt
        
        # Keep player on screen
        self.player_position[0] = max(50, min(self.width - 50, self.player_position[0]))
        self.player_position[1] = max(50, min(self.height - 50, self.player_position[1]))
        
        # Sword combat
        if keys[pygame.K_f]:
            self.player_sword_drawn = True
        
        if keys[pygame.K_SPACE] and self.player_sword_drawn and self.player_sword_cooldown <= 0:
            self.player_sword_swinging = True
            self.player_sword_timer = 0
            self.player_sword_cooldown = 0.5
            self.player_sword_frame = 0
        
        # Update sword cooldown
        if self.player_sword_cooldown > 0:
            self.player_sword_cooldown -= dt
        
        # Update sword swing animation
        if self.player_sword_swinging:
            self.player_sword_timer += dt
            if self.player_sword_timer >= 0.1:  # 10fps animation
                self.player_sword_timer = 0
                self.player_sword_frame += 1
                if self.player_sword_frame >= 4:
                    self.player_sword_swinging = False
                    self.player_sword_frame = 0
    
    def update_boss(self, dt):
        """Update boss AI and behavior."""
        # Boss floating animation
        self.boss_floating_offset += dt * 2
        boss_y = self.height // 2 + 50 * math.sin(self.boss_floating_offset)
        
        if self.current_phase == 2:
            # Phase 2: Gun boss
            self.boss_position[1] = boss_y
            self.boss_attack_timer += dt
            
            if self.boss_attack_timer >= self.boss_attack_cooldown:
                self.boss_attack_timer = 0
                self.boss_shoot_orb()
                
        elif self.current_phase == 3:
            # Phase 3: Sword boss
            self.boss_position[1] = boss_y
            
            # Move towards player
            dx = self.player_position[0] - self.boss_position[0]
            if abs(dx) > 50:  # Don't get too close
                if dx > 0:
                    self.boss_position[0] += 100 * dt
                    self.boss_facing_right = True
                else:
                    self.boss_position[0] -= 100 * dt
                    self.boss_facing_right = False
            
            # Sword attack
            self.boss_attack_timer += dt
            if self.boss_attack_timer >= self.boss_attack_cooldown:
                dist = math.hypot(self.player_position[0] - self.boss_position[0],
                                self.player_position[1] - self.boss_position[1])
                if dist < 100:  # Close enough to attack
                    self.boss_sword_swinging = True
                    self.boss_sword_timer = 0
                    self.boss_attack_timer = 0
                    self.boss_sword_frame = 0
        
        # Update boss sword swing animation
        if self.boss_sword_swinging:
            self.boss_sword_timer += dt
            if self.boss_sword_timer >= 0.1:  # 10fps animation
                self.boss_sword_timer = 0
                self.boss_sword_frame += 1
                if self.boss_sword_frame >= 4:
                    self.boss_sword_swinging = False
                    self.boss_sword_frame = 0
    
    def boss_shoot_orb(self):
        """Boss shoots an orb at the player."""
        dx = self.player_position[0] - self.boss_position[0]
        dy = self.player_position[1] - self.boss_position[1]
        dist = math.hypot(dx, dy)
        
        if dist > 0:
            speed = 200
            vel_x = (dx / dist) * speed
            vel_y = (dy / dist) * speed
            
            self.boss_bullets.append({
                "pos": self.boss_position.copy(),
                "vel": [vel_x, vel_y],
                "timer": 0
            })
    
    def update_aliens(self, dt):
        """Update alien minions."""
        for alien in self.aliens[:]:
            # Floating motion
            alien["floating_offset"] += dt * alien["floating_speed"]
            alien["pos"][1] = 150 + 50 * math.sin(alien["floating_offset"])
            
            # Face player
            dx = self.player_position[0] - alien["pos"][0]
            alien["facing_right"] = dx > 0
            
            # Attack
            alien["attack_timer"] += dt
            if alien["attack_timer"] >= alien["attack_cooldown"]:
                alien["attack_timer"] = 0
                self.alien_shoot_orb(alien)
    
    def alien_shoot_orb(self, alien):
        """Alien shoots an orb at the player."""
        dx = self.player_position[0] - alien["pos"][0]
        dy = self.player_position[1] - alien["pos"][1]
        dist = math.hypot(dx, dy)
        
        if dist > 0:
            speed = 150
            vel_x = (dx / dist) * speed
            vel_y = (dy / dist) * speed
            
            self.alien_bullets.append({
                "pos": alien["pos"].copy(),
                "vel": [vel_x, vel_y],
                "timer": 0
            })
    
    def update_projectiles(self, dt):
        """Update all projectiles."""
        # Update alien bullets
        for bullet in self.alien_bullets[:]:
            bullet["pos"][0] += bullet["vel"][0] * dt
            bullet["pos"][1] += bullet["vel"][1] * dt
            bullet["timer"] += dt
            
            if bullet["timer"] > 3.0 or (bullet["pos"][0] < 0 or bullet["pos"][0] > self.width or
                                        bullet["pos"][1] < 0 or bullet["pos"][1] > self.height):
                self.alien_bullets.remove(bullet)
        
        # Update boss bullets
        for bullet in self.boss_bullets[:]:
            bullet["pos"][0] += bullet["vel"][0] * dt
            bullet["pos"][1] += bullet["vel"][1] * dt
            bullet["timer"] += dt
            
            if bullet["timer"] > 4.0 or (bullet["pos"][0] < 0 or bullet["pos"][0] > self.width or
                                        bullet["pos"][1] < 0 or bullet["pos"][1] > self.height):
                self.boss_bullets.remove(bullet)
    
    def check_collisions(self):
        """Check all collision detection."""
        # Player sword vs aliens
        if self.player_sword_swinging and self.current_phase in [1, 2]:
            sword_range = 80
            for alien in self.aliens[:]:
                dist = math.hypot(self.player_position[0] - alien["pos"][0],
                                self.player_position[1] - alien["pos"][1])
                if dist < sword_range:
                    alien["health"] -= 30
                    if alien["health"] <= 0:
                        self.aliens.remove(alien)
        
        # Player sword vs boss (Phase 3)
        if self.player_sword_swinging and self.current_phase == 3:
            sword_range = 80
            dist = math.hypot(self.player_position[0] - self.boss_position[0],
                            self.player_position[1] - self.boss_position[1])
            if dist < sword_range:
                self.boss_health -= 20
        
        # Boss sword vs player (Phase 3)
        if self.boss_sword_swinging and self.current_phase == 3:
            sword_range = 80
            dist = math.hypot(self.player_position[0] - self.boss_position[0],
                            self.player_position[1] - self.boss_position[1])
            if dist < sword_range:
                self.player_health -= 25
        
        # Alien bullets vs player
        for bullet in self.alien_bullets[:]:
            dist = math.hypot(bullet["pos"][0] - self.player_position[0],
                            bullet["pos"][1] - self.player_position[1])
            if dist < 25:
                self.player_health -= 15
                self.alien_bullets.remove(bullet)
                if self.player_health <= 0:
                    print("[FinalBossScene] Game Over - You were defeated!")
                    self.game.running = False
        
        # Boss bullets vs player
        for bullet in self.boss_bullets[:]:
            dist = math.hypot(bullet["pos"][0] - self.player_position[0],
                            bullet["pos"][1] - self.player_position[1])
            if dist < 25:
                self.player_health -= 25
                self.boss_bullets.remove(bullet)
                if self.player_health <= 0:
                    print("[FinalBossScene] Game Over - You were defeated!")
                    self.game.running = False
    
    def draw(self, surface):
        """Draw the complete boss battle scene."""
        # Draw background
        surface.blit(self.background_img, (0, 0))
        
        # Draw floor
        pygame.draw.rect(surface, (40, 40, 40), (0, self.floor_y, self.width, self.height - self.floor_y))
        
        # Draw pillars
        for pillar_x, pillar_y in self.pillars:
            surface.blit(self.pillar_img, (pillar_x, pillar_y))
        
        # Draw props (behind characters)
        for prop in self.props:
            surface.blit(prop["img"], prop["pos"])
        
        # Draw aliens
        for alien in self.aliens:
            alien_img = self.alien_img
            if alien["facing_right"]:
                alien_img = pygame.transform.flip(self.alien_img, True, False)
            surface.blit(alien_img, (alien["pos"][0] - 30, alien["pos"][1] - 30))
        
        # Draw boss
        if self.current_phase == 2:
            # Gun boss
            surface.blit(self.boss_gun_img, (self.boss_position[0] - 60, self.boss_position[1] - 60))
        elif self.current_phase == 3:
            # Sword boss
            if self.boss_sword_swinging:
                boss_img = self.boss_swing_frames[self.boss_sword_frame]
            else:
                boss_img = self.boss_swing_frames[0]  # Idle frame
            
            if self.boss_facing_right:
                boss_img = pygame.transform.flip(boss_img, True, False)
            surface.blit(boss_img, (self.boss_position[0] - 50, self.boss_position[1] - 50))
        
        # Draw player
        if self.player_sword_swinging:
            player_img = self.player_sword_frames[self.player_sword_frame]
        else:
            player_img = self.player_idle_img
        
        if self.player_facing_right:
            player_img = pygame.transform.flip(player_img, True, False)
        surface.blit(player_img, (self.player_position[0] - 25, self.player_position[1] - 40))
        
        # Draw projectiles
        for bullet in self.alien_bullets:
            surface.blit(self.alien_orb_img, (bullet["pos"][0] - 10, bullet["pos"][1] - 10))
        
        for bullet in self.boss_bullets:
            surface.blit(self.boss_orb_img, (bullet["pos"][0] - 15, bullet["pos"][1] - 15))
        
        # Draw UI
        self.draw_ui(surface)
        
        # Draw phase transition overlay
        if self.is_transitioning:
            overlay = pygame.Surface((self.width, self.height))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(128)
            surface.blit(overlay, (0, 0))
            
            font = pygame.font.SysFont(None, 48)
            phase_text = f"Phase {self.current_phase}"
            text_surface = font.render(phase_text, True, (255, 255, 255))
            surface.blit(text_surface, (self.width // 2 - text_surface.get_width() // 2, 
                                      self.height // 2 - text_surface.get_height() // 2))
        
        # Draw victory screen
        if self.boss_defeated:
            overlay = pygame.Surface((self.width, self.height))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(180)
            surface.blit(overlay, (0, 0))
            
            victory_font = pygame.font.SysFont(None, 72)
            victory_text = victory_font.render("VICTORY!", True, (255, 255, 0))
            surface.blit(victory_text, (self.width // 2 - victory_text.get_width() // 2, 
                                      self.height // 2 - 100))
            
            subtitle_font = pygame.font.SysFont(None, 36)
            subtitle_text = subtitle_font.render("You have saved the galaxy!", True, (255, 255, 255))
            surface.blit(subtitle_text, (self.width // 2 - subtitle_text.get_width() // 2, 
                                       self.height // 2 - 20))
        
        # Draw fade overlay
        if self.fade_alpha > 0:
            fade_overlay = pygame.Surface(surface.get_size())
            fade_overlay.fill((0, 0, 0))
            fade_overlay.set_alpha(self.fade_alpha)
            surface.blit(fade_overlay, (0, 0))
    
    def draw_ui(self, surface):
        """Draw the user interface."""
        # Phase indicator
        font = pygame.font.SysFont(None, 36)
        phase_text = f"Phase {self.current_phase}"
        if self.current_phase == 1:
            phase_desc = "Alien Minions"
        elif self.current_phase == 2:
            phase_desc = "Final Boss + Minions"
        else:
            phase_desc = "Sword Duel"
        
        phase_surface = font.render(f"{phase_text}: {phase_desc}", True, (255, 255, 255))
        surface.blit(phase_surface, (20, 20))
        
        # Player health bar
        player_health_width = 200
        player_health_height = 20
        player_health_x = 20
        player_health_y = 60
        pygame.draw.rect(surface, (100, 100, 100), (player_health_x, player_health_y, 
                                                   player_health_width, player_health_height))
        health_percent = self.player_health / self.player_max_health
        pygame.draw.rect(surface, (0, 255, 0), (player_health_x, player_health_y, 
                                               int(player_health_width * health_percent), player_health_height))
        pygame.draw.rect(surface, (255, 255, 255), (player_health_x, player_health_y, 
                                                   player_health_width, player_health_height), 2)
        
        # Player health text
        health_text = font.render(f"Player: {self.player_health}/{self.player_max_health}", True, (255, 255, 255))
        surface.blit(health_text, (player_health_x, player_health_y - 25))
        
        # Boss health bar (Phases 2 and 3)
        if self.current_phase in [2, 3]:
            boss_health_width = 200
            boss_health_height = 20
            boss_health_x = self.width - boss_health_width - 20
            boss_health_y = 60
            pygame.draw.rect(surface, (100, 100, 100), (boss_health_x, boss_health_y, 
                                                       boss_health_width, boss_health_height))
            health_percent = self.boss_health / self.boss_max_health
            pygame.draw.rect(surface, (255, 0, 0), (boss_health_x, boss_health_y, 
                                                   int(boss_health_width * health_percent), boss_health_height))
            pygame.draw.rect(surface, (255, 255, 255), (boss_health_x, boss_health_y, 
                                                       boss_health_width, boss_health_height), 2)
            
            # Boss health text
            boss_text = font.render(f"Boss: {self.boss_health}/{self.boss_max_health}", True, (255, 255, 255))
            surface.blit(boss_text, (boss_health_x, boss_health_y - 25))
        
        # Alien count (Phase 1 and 2)
        if self.current_phase in [1, 2]:
            alien_text = font.render(f"Aliens: {len(self.aliens)}", True, (255, 255, 255))
            surface.blit(alien_text, (self.width // 2 - alien_text.get_width() // 2, 20))
        
        # Controls
        controls_font = pygame.font.SysFont(None, 24)
        controls_text = controls_font.render("WASD: Move, F: Draw Sword, SPACE: Swing", True, (200, 200, 200))
        surface.blit(controls_text, (20, self.height - 30)) 