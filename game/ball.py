import math      # Provides mathematical functions, e.g: math.sqrt for square roots
import pygame    # The game library: handles drawing, windows, input, etc.

# Physical constants used throughout the simulation
RESTITUTION = 0.75   # The bounciness coefficient. A value of 1.0 = perfectly elastic, no energy lost.
                     # 0.75 means each bounce retains 75% of the momentum. Energy is gradually lost, like a real ball.


def speed_to_colour(speed, max_speed=30):
    """
    Maps a particle's speed to an RGB colour, so fast particles glow brighter/hotter.
    Much like a heat map: slow = dark/cold, fast = bright/white-hot.

    Parameters:
        speed     : the current speed of the particle (a non-negative float)
        max_speed : the reference maximum speed used to normalise (default 30)

    Returns:
        A tuple (r, g, b) where each value is an integer in the range [0, 255].
    """

    # Use t to normalise speed to the range [0, 1].
    # min(..., 1.0) clamps it so values above max_speed don't exceed 1.
    t = min(speed / max_speed, 1.0)

    if t < 0.4:
        # Slow particles: dark grey transitioning to deep-purple
        # s is a local sub-parameter that re-normalises t within this band [0, 0.4] → [0, 1]
        s  = t / 0.4
        # Linear interpolation: start colour + s * (end colour - start colour)
        # At s=0 (very slow): (40, 40, 60) - dark grey
        # At s=1 (t=0.4):     (80, 40, 120) - deep-purple
        r  = int(40  + s * (80  - 40))
        g  = int(40  + s * (40  - 40))   # green stays flat at 40
        b  = int(60  + s * (120 - 60))

    elif t < 0.75:
        # Medium particles: deep purple transitioning to electric cyan
        # Re-normalise t within the band [0.4, 0.75] → [0, 1]
        s  = (t - 0.4) / 0.35
        # At s=0 (t=0.4):  (80, 40, 120) - deep-purple
        # At s=1 (t=0.75): (20, 180, 255) - electric cyan
        r  = int(80  + s * (20  - 80))
        g  = int(40  + s * (180 - 40))
        b  = int(120 + s * (255 - 120))

    else:
        # Fast particles: cyan to white-hot
        # Re-normalise t within the band [0.75, 1.0] → [0, 1]
        s  = (t - 0.75) / 0.25
        # At s=0 (t=0.75): (20, 180, 255) - bright cyan
        # At s=1 (t=1.0):  (255, 255, 255) - pure white
        r  = int(20  + s * (255 - 20))
        g  = int(180 + s * (255 - 180))
        b  = 255   # blue stays maxed throughout this band

    return (r, g, b)   # Return the colour as an (R, G, B) tuple


class Ball:
    """
    Represents a single circular particle in the simulation.
    Each ball has a position (x, y), a radius, and a velocity (vx, vy).
    Velocity is a 2D vector: vx is the horizontal component, vy is vertical.
    """

    def __init__(self, x, y, radius, vx=0, vy=0):
        """
        Constructor - called when you write Ball(x, y, radius, ...).
        Initialises the ball's state.

        Parameters:
            x, y   : starting position in pixels
            radius : size of the ball in pixels
            vx, vy : initial velocity components in pixels per frame
        """
        self.x      = float(x)       # Store as float for sub-pixel precision during physics
        self.y      = float(y)
        self.radius = radius
        self.vx     = float(vx)      # Horizontal velocity (positive = rightward)
        self.vy     = float(vy)      # Vertical velocity   (positive = downward, since y increases downward in pygame)
        self._speed_cache = None     # None means "not yet calculated this frame"

    @property
    def speed(self):
        """
        Computes the scalar speed (magnitude of the velocity vector).
        By Pythagoras: speed = sqrt(vx² + vy²).
        @property means you access it as ball.speed (no parentheses needed).
        Returns 0 if speed is negligibly small (< 0.3), treating it as "at rest".
        """
        if self._speed_cache is None:       # Only calculate if we haven't yet
            s = math.sqrt(self.vx ** 2 + self.vy ** 2)
            self._speed_cache = s if s > 0.5 else 0
        return self._speed_cache            # Return stored result

    def attract(self, tx, ty, strength=0.5):
        """
        Applies a gravitational-style attraction force toward the target point (tx, ty).
        Modifies the ball's velocity by adding a small nudge in the direction of the target.
        This is used when the mouse button is held down.

        Parameters:
            tx, ty   : target coordinates (e.g: mouse position) in pixels
            strength : how strong the attraction is (pixels per frame)
        """
        dx   = tx - self.x    # Horizontal displacement from ball to target
        dy   = ty - self.y    # Vertical displacement from ball to target
        dist = math.sqrt(dx * dx + dy * dy)   # Euclidean distance to target

        if dist == 0:
            return   # Avoid division by zero if ball is exactly on the target

        # Normalise the direction vector (dx, dy) to unit length, then scale by strength.
        # This ensures the force magnitude is always `strength`, regardless of distance.
        self.vx += (dx / dist) * strength
        self.vy += (dy / dist) * strength

    def update(self, gravity_on=True, gravity_strength=0.15):
        """
        Advances the ball by one frame. Updates velocity (via gravity) then position.
        This is simple Euler integration: new_position = old_position + velocity.

        Parameters:
            gravity_on       : whether to apply gravity this frame
            gravity_strength : how many pixels per frame² to accelerate downward
        """
        self._speed_cache = None   # Velocity is about to change, so wipe the old result

        if gravity_on:
            self.vy += gravity_strength   # Gravity accelerates the ball downward each frame

        # Update position using current velocity (Euler method)
        self.x += self.vx
        self.y += self.vy

    def draw(self, surface):
        """
        Renders the ball onto the given pygame surface.
        Draws three layers: a soft glow halo, a solid core, and (for fast balls) a bright centre.

        Parameters:
            surface : the pygame Surface to draw onto
        """
        colour = speed_to_colour(self.speed)   # Get the colour for this ball's current speed
        cx, cy = int(self.x), int(self.y)      # Integer pixel coordinates for drawing

        # Soft glow halo:
        # Darken the main colour to ~35% brightness for a faint halo behind the ball.
        # min(255, ...) ensures no channel exceeds the maximum allowed value of 255.
        glow_col = tuple(min(255, int(c * 0.35)) for c in colour)
        pygame.draw.circle(surface, glow_col, (cx, cy), self.radius + 3)   # Slightly larger than the ball

        # Core particle:
        # Draw the main filled circle at full brightness
        pygame.draw.circle(surface, colour, (cx, cy), self.radius)

        # Bright centre pinpoint (for fast particles only)
        # At speed > 15 a small white dot is drawn to simulate a super-hot core
        if self.speed > 15:
            # t goes from 0 (speed=15) to 1 (speed=40), controlling how large the pinpoint is
            t = min((self.speed - 15) / 15, 1.0)
            w = max(1, int(self.radius * 0.4 * t))   # Minimum 1-pixel dot
            pygame.draw.circle(surface, (255, 255, 255), (cx, cy), w)   # Pure white

    def collide(self, other):
        """
        Resolves a collision between this ball and another ball.
        Uses an impulse-based approach: overlapping circles are separated,
        then velocities are exchanged along the collision normal.

        This is a simplified elastic collision, scaled by RESTITUTION to lose some energy.

        Parameters:
            other : another Ball object to check and resolve against
        """
        dx   = other.x - self.x    # Vector from self to other (x component)
        dy   = other.y - self.y    # Vector from self to other (y component)
        dist = math.sqrt(dx * dx + dy * dy)   # Distance between centres

        # If distance is zero (exact overlap) or they're not touching, do nothing
        if dist == 0 or dist >= self.radius + other.radius:
            return

        # Positional correction:
        # How much the balls are overlapping
        overlap = self.radius + other.radius - dist

        # Unit normal vector pointing from self toward other
        nx = dx / dist
        ny = dy / dist

        # Push each ball apart by half the overlap along the normal
        self.x  -= nx * overlap / 2
        self.y  -= ny * overlap / 2
        other.x += nx * overlap / 2
        other.y += ny * overlap / 2

        # Velocity exchange (1D collision along the normal axis)
        # Project each ball's velocity onto the collision normal (dot product)
        # This gives the component of velocity that's "along the line of impact"
        dot_self  = self.vx  * nx + self.vy  * ny
        dot_other = other.vx * nx + other.vy * ny

        # For equal-mass balls, the normal velocity components are swapped.
        # The RESTITUTION factor reduces the exchanged impulse, losing some energy.
        # The ± signs correctly apply the impulse in opposite directions to each ball.
        self.vx  += (dot_other - dot_self) * nx * RESTITUTION
        self.vy  += (dot_other - dot_self) * ny * RESTITUTION
        other.vx -= (dot_other - dot_self) * nx * RESTITUTION
        other.vy -= (dot_other - dot_self) * ny * RESTITUTION
