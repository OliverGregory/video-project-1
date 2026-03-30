import pygame

RESTITUTION = 0.75

class Environment:
    def __init__(self, width, height, cell_size=100):
        self.width     = width
        self.height    = height
        self.cell_size = cell_size
        self.screen    = pygame.display.set_mode((width, height))
        self.cells     = {}

    def apply_boundaries(self, ball):
        """Returns (hit, speed) so the game loop can fire events."""
        hit   = False
        speed = ball.speed

        if ball.x - ball.radius < 0:
            ball.x  = ball.radius
            ball.vx = abs(ball.vx) * RESTITUTION
            hit     = True
        if ball.x + ball.radius > self.width:
            ball.x  = self.width - ball.radius
            ball.vx = -abs(ball.vx) * RESTITUTION
            hit     = True
        if ball.y - ball.radius < 0:
            ball.y  = ball.radius
            ball.vy = abs(ball.vy) * RESTITUTION
            hit     = True
        if ball.y + ball.radius > self.height:
            ball.y  = self.height - ball.radius
            ball.vy = -abs(ball.vy) * RESTITUTION
            hit     = True

        return hit, speed

    def clear_grid(self):
        self.cells = {}

    def insert(self, ball):
        min_cx = int((ball.x - ball.radius) // self.cell_size)
        max_cx = int((ball.x + ball.radius) // self.cell_size)
        min_cy = int((ball.y - ball.radius) // self.cell_size)
        max_cy = int((ball.y + ball.radius) // self.cell_size)

        for cx in range(min_cx, max_cx + 1):
            for cy in range(min_cy, max_cy + 1):
                key = (cx, cy)
                if key not in self.cells:
                    self.cells[key] = []
                self.cells[key].append(ball)

    def get_nearby(self, ball):
        min_cx = int((ball.x - ball.radius) // self.cell_size)
        max_cx = int((ball.x + ball.radius) // self.cell_size)
        min_cy = int((ball.y - ball.radius) // self.cell_size)
        max_cy = int((ball.y + ball.radius) // self.cell_size)

        nearby = set()
        for cx in range(min_cx, max_cx + 1):
            for cy in range(min_cy, max_cy + 1):
                for other in self.cells.get((cx, cy), []):
                    if other is not ball:
                        nearby.add(other)
        return nearby

    def resolve_collisions(self, balls):
        self.clear_grid()
        for ball in balls:
            self.insert(ball)

        checked = set()
        for ball in balls:
            for other in self.get_nearby(ball):
                pair = frozenset((id(ball), id(other)))
                if pair not in checked:
                    ball.collide(other)
                    checked.add(pair)
