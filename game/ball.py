import math
import pygame
 
GRAVITY     = 1
RESTITUTION = 0.75
SLEEP_THRESHOLD = 0.5 

def speed_to_colour(speed, max_speed=30):
    t = min(speed / max_speed, 1.0)
    r = int(80 + t * (0   - 80))
    g = int(80 + t * (220 - 80))
    b = int(80 + t * (255 - 80))
    return (r, g, b)

class Ball:
    def __init__(self, x, y, radius, vx=0, vy=0):
        self.x      = float(x)
        self.y      = float(y)
        self.radius = radius
        self.vx     = float(vx)
        self.vy     = float(vy)
 
    @property
    def speed(self):
        return math.sqrt(self.vx ** 2 + self.vy ** 2)
        return s if s > SLEEP_THRESHOLD else 0

    def attract(self, tx, ty, strength=0.5):
        dx   = tx - self.x
        dy   = ty - self.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist == 0:
            return
        self.vx += (dx / dist) * strength
        self.vy += (dy / dist) * strength
 
    def update(self, gravity=True):
        if gravity:
            self.vy += GRAVITY
        self.x += self.vx
        self.y += self.vy
 
    def draw(self, surface):
        colour = speed_to_colour(self.speed)
        pygame.draw.circle(surface, colour, (int(self.x), int(self.y)), self.radius)
 
    def collide(self, other):
        dx   = other.x - self.x
        dy   = other.y - self.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist == 0 or dist >= self.radius + other.radius:
            return
 
        overlap = self.radius + other.radius - dist
        nx = dx / dist
        ny = dy / dist
        self.x  -= nx * overlap / 2
        self.y  -= ny * overlap / 2
        other.x += nx * overlap / 2
        other.y += ny * overlap / 2
 
        dot_self  = self.vx  * nx + self.vy  * ny
        dot_other = other.vx * nx + other.vy * ny
        self.vx  += (dot_other - dot_self) * nx * RESTITUTION
        self.vy  += (dot_other - dot_self) * ny * RESTITUTION
        other.vx -= (dot_other - dot_self) * nx * RESTITUTION
        other.vy -= (dot_other - dot_self) * ny * RESTITUTION
