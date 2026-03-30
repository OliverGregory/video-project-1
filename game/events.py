import pygame
import math
import random

class WallFlash:
    """Small spark at the point of wall impact."""
    def __init__(self, x, y):
        self.x        = x
        self.y        = y
        self.lifetime = 8
        self.age      = 0
        self.radius   = 3

    @property
    def alive(self):
        return self.age < self.lifetime

    def update(self):
        self.age    += 1
        self.radius += 1.5

    def draw(self, surface):
        t      = 1 - self.age / self.lifetime
        alpha  = int(160 * t)
        ring   = pygame.Surface((int(self.radius * 2 + 2), int(self.radius * 2 + 2)), pygame.SRCALPHA)
        pygame.draw.circle(ring, (180, 220, 255, alpha),
                           (int(self.radius + 1), int(self.radius + 1)),
                           int(self.radius), 1)
        surface.blit(ring, (int(self.x - self.radius - 1), int(self.y - self.radius - 1)))


class Supernova:
    """Full-screen flash + expanding ring when energy crosses a threshold."""
    def __init__(self, screen_w, screen_h):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.lifetime = 40
        self.age      = 0
        self.ring_r   = 20

    @property
    def alive(self):
        return self.age < self.lifetime

    def update(self):
        self.age    += 1
        self.ring_r += 18

    def draw(self, surface):
        t = 1 - self.age / self.lifetime

        # Faint full-screen nebula tint
        if self.age < 10:
            alpha = int(30 * (1 - self.age / 10))
            tint  = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
            tint.fill((160, 80, 255, alpha))
            surface.blit(tint, (0, 0))

        # Expanding shockwave ring from screen centre
        cx, cy = self.screen_w // 2, self.screen_h // 2
        alpha  = int(200 * t)
        r      = int(self.ring_r)
        if r > 0:
            ring = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(ring, (200, 160, 255, alpha), (r + 2, r + 2), r, 2)
            surface.blit(ring, (cx - r - 2, cy - r - 2))

        # Starburst spokes
        if self.age < 6:
            spoke_alpha = int(180 * (1 - self.age / 6))
            for angle in range(0, 360, 45):
                rad  = math.radians(angle)
                length = 60 + random.randint(0, 30)
                ex   = int(cx + math.cos(rad) * length)
                ey   = int(cy + math.sin(rad) * length)
                spoke_surf = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
                pygame.draw.line(spoke_surf, (220, 180, 255, spoke_alpha),
                                 (cx, cy), (ex, ey), 1)
                surface.blit(spoke_surf, (0, 0))


class EventSystem:
    def __init__(self, screen_w, screen_h):
        self.screen_w         = screen_w
        self.screen_h         = screen_h
        self.effects          = []
        self.last_threshold   = 0

    def wall_hit(self, x, y, speed):
        if speed > 3:
            self.effects.append(WallFlash(x, y))

    def check_energy(self, avg_speed, sound_system):
        current_threshold = int(avg_speed // 5) * 5
        if current_threshold > 0 and current_threshold > self.last_threshold:
            self.effects.append(Supernova(self.screen_w, self.screen_h))
            sound_system.resolution()
            self.last_threshold = current_threshold
        elif current_threshold < self.last_threshold:
            self.last_threshold = current_threshold

    def update(self):
        for effect in self.effects:
            effect.update()
        self.effects = [e for e in self.effects if e.alive]

    def draw(self, surface):
        for effect in self.effects:
            effect.draw(surface)
