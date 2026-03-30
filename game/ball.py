import math
import pygame

GRAVITY     = 1
RESTITUTION = 0.75

def speed_to_colour(speed, max_speed=30):
    t = min(speed / max_speed, 1.0)
    if t < 0.4:
        # Dark grey to deep blue-purple (cold nebula)
        s  = t / 0.4
        r  = int(40  + s * (80  - 40))
        g  = int(40  + s * (40  - 40))
        b  = int(60  + s * (120 - 60))
    elif t < 0.75:
        # Deep purple to electric cyan (nebula glow)
        s  = (t - 0.4) / 0.35
        r  = int(80  + s * (20  - 80))
        g  = int(40  + s * (180 - 40))
        b  = int(120 + s * (255 - 120))
    else:
        # Cyan to white-hot (supernova core)
        s  = (t - 0.75) / 0.25
        r  = int(20  + s * (255 - 20))
        g  = int(180 + s * (255 - 180))
        b  = 255
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
        s = math.sqrt(self.vx ** 2 + self.vy ** 2)
        return s if s > 0.5 else 0

    def attract(self, tx, ty, strength=0.5):
        dx   = tx - self.x
        dy   = ty - self.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist == 0:
            return
        self.vx += (dx / dist) * strength
        self.vy += (dy / dist) * strength

    def update(self, gravity_on=True, gravity_strength=0.15):
        if gravity_on:
            self.vy += gravity_strength
        self.x += self.vx
        self.y += self.vy

    def draw(self, surface):
        colour = speed_to_colour(self.speed)
        cx, cy = int(self.x), int(self.y)

        # Soft glow halo — larger faint circle behind
        glow_col = tuple(min(255, int(c * 0.35)) for c in colour)
        pygame.draw.circle(surface, glow_col, (cx, cy), self.radius + 3)

        # Core particle
        pygame.draw.circle(surface, colour, (cx, cy), self.radius)

        # Bright centre pinpoint for fast particles
        if self.speed > 15:
            t = min((self.speed - 15) / 15, 1.0)
            w = max(1, int(self.radius * 0.4 * t))
            pygame.draw.circle(surface, (255, 255, 255), (cx, cy), w)

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
