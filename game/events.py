import pygame    # Game library: used for drawing shapes and surfaces
import math      # For trigonometric functions (cos, sin, radians)
import random    # For randomness in Supernova class


class WallFlash:
    """
    A short-lived visual spark that appears at the point where a ball hits a wall.
    Renders as an expanding translucent ring that fades out over 10 frames.
    """

    def __init__(self, x, y):
        """
        Creates a new WallFlash at position (x, y) — typically the ball's position at impact.

        Parameters:
            x, y : screen coordinates of the impact point
        """
        self.x        = x
        self.y        = y
        self.lifetime = 10    # Total number of frames this effect lives for
        self.age      = 0    # Current age in frames; starts at 0, counts up to lifetime
        self.radius   = 3    # Starting ring radius in pixels

    @property
    def alive(self):
        """
        Returns True if the effect has not yet reached the end of its lifetime.
        Used by EventSystem to know whether to keep or discard this effect.
        """
        return self.age < self.lifetime

    def update(self):
        """
        Advances the effect by one frame.
        The ring grows outward and ages toward death.
        """
        self.age    += 1      # Age by one frame
        self.radius += 1.5    # Ring expands by 1.5 pixels per frame

    def draw(self, surface):
        """
        Draws the fading ring onto the given surface.
        Uses an SRCALPHA surface to support per-pixel transparency (alpha blending).

        Parameters:
            surface : the pygame Surface to draw onto
        """
        # t goes from 1.0 (new) to 0.0 (dead) — used to fade out the effect
        t     = 1 - self.age / self.lifetime
        alpha = int(160 * t)   # Opacity: starts at 160 (semi-transparent), fades to 0

        # Create a small transparent surface just large enough to hold the ring.
        # SRCALPHA mode allows individual pixels to have their own alpha (transparency) value.
        ring = pygame.Surface((int(self.radius * 2 + 2), int(self.radius * 2 + 2)), pygame.SRCALPHA)

        # Draw a hollow circle (ring) with width=1 onto this mini surface.
        # The circle is centred within the surface, and its colour includes the computed alpha.
        pygame.draw.circle(ring, (180, 220, 255, alpha),
                           (int(self.radius + 1), int(self.radius + 1)),
                           int(self.radius), 1)   # Last argument: line width (1 = outline only)

        # Blit (copy) the ring surface onto the main surface, positioned so the ring is centred at (x, y)
        surface.blit(ring, (int(self.x - self.radius - 1), int(self.y - self.radius - 1)))


class Supernova:
    """
    A dramatic full-screen flash effect triggered when the system's energy crosses a threshold.
    Consists of three layers:
      1. A brief faint full-screen purple tint
      2. An expanding shockwave ring from the screen centre
      3. Short starburst spokes radiating from the centre (only in the first few frames)
    """

    def __init__(self, screen_w, screen_h):
        """
        Parameters:
            screen_w, screen_h : dimensions of the game window in pixels
        """
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.lifetime = 40   # Effect lasts 40 frames (~0.67 seconds at 60 fps)
        self.age      = 0
        self.ring_r   = 20   # Starting radius of the expanding shockwave ring in pixels

    @property
    def alive(self):
        """Returns True while the effect is still playing."""
        return self.age < self.lifetime

    def update(self):
        """Advances the effect by one frame. The ring grows rapidly outward."""
        self.age    += 1
        self.ring_r += 18   # Ring expands by 18 pixels per frame — covers the screen in ~35 frames

    def draw(self, surface):
        """
        Renders all three layers of the supernova effect.

        Parameters:
            surface : the main game surface to draw onto
        """
        # t: normalised age from 1.0 (just started) to 0.0 (about to die) — controls fade-out
        t = 1 - self.age / self.lifetime

        # --- Layer 1: Faint full-screen nebula tint (only during the first 10 frames) ---
        if self.age < 10:
            # alpha fades from ~30 down to 0 during frames 0–10
            alpha = int(30 * (1 - self.age / 10))
            tint  = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
            tint.fill((160, 80, 255, alpha))   # Pale purple wash
            surface.blit(tint, (0, 0))         # Cover the entire screen

        # --- Layer 2: Expanding shockwave ring centred on the screen ---
        cx, cy = self.screen_w // 2, self.screen_h // 2   # Screen centre in pixels
        alpha  = int(200 * t)   # Ring fades out as t approaches 0
        r      = int(self.ring_r)

        if r > 0:
            # Create a transparent surface big enough to contain the ring
            ring = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(ring, (200, 160, 255, alpha), (r + 2, r + 2), r, 2)   # Hollow ring, 2px wide
            # Blit so the ring is centred at (cx, cy)
            surface.blit(ring, (cx - r - 2, cy - r - 2))

        # --- Layer 3: Starburst spokes (only visible in the first 6 frames) ---
        if self.age < 6:
            # Fade the spokes out quickly during frames 0–6
            spoke_alpha = int(180 * (1 - self.age / 6))

            # Draw 8 spokes evenly spaced at 45° intervals around the centre
            for angle in range(0, 360, 45):
                rad    = math.radians(angle)   # Convert degrees to radians for trig functions
                length = 60 + random.randint(0, 30)   # Each spoke has a slightly random length

                # Endpoint of the spoke using basic trigonometry:
                # x = cx + cos(angle) * length, y = cy + sin(angle) * length
                ex = int(cx + math.cos(rad) * length)
                ey = int(cy + math.sin(rad) * length)

                # Draw each spoke onto its own full-screen SRCALPHA surface (for transparency support)
                spoke_surf = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
                pygame.draw.line(spoke_surf, (220, 180, 255, spoke_alpha),
                                 (cx, cy), (ex, ey), 1)   # Thin 1-pixel line
                surface.blit(spoke_surf, (0, 0))


class EventSystem:
    """
    Manages the collection of active visual effects and decides when to spawn new ones.
    Acts as the central coordinator between game events (wall hits, energy thresholds)
    and the visual effects (WallFlash, Supernova).
    """

    def __init__(self, screen_w, screen_h):
        """
        Parameters:
            screen_w, screen_h : window dimensions, passed to Supernova effects
        """
        self.screen_w         = screen_w
        self.screen_h         = screen_h
        self.effects          = []     # List of currently active effect objects (WallFlash or Supernova)
        self.last_threshold   = 0      # Tracks the last energy band that triggered a Supernova,
                                       # so we only fire once per band crossing

    def wall_hit(self, x, y, speed):
        """
        Called by the game loop when a ball bounces off a wall.
        Only creates a spark effect if the ball was moving fast enough to be visible.

        Parameters:
            x, y  : position of the collision on the screen
            speed : how fast the ball was moving at the moment of impact
        """
        if speed > 3:   # Threshold: ignore very slow/gentle grazes
            self.effects.append(WallFlash(x, y))

    def check_energy(self, avg_speed, sound_system):
        """
        Checks whether the system's average energy has crossed into a new 5-unit band.
        If it has risen to a new band, a Supernova is fired and a sound is played.
        If energy has dropped back, the threshold is reset so it can trigger again later.

        Parameters:
            avg_speed    : the mean speed of all particles this frame
            sound_system : reference to the SoundSystem object, used to play a resolution tone
        """
        # Round avg_speed down to the nearest multiple of 20.
        # e.g. avg_speed=22.3 → current_threshold=20; avg_speed=77 → current_threshold=60
        current_threshold = int(avg_speed // 20) * 20

        # Fire a Supernova when energy rises into a new band (strictly higher than before)
        if current_threshold > 0 and current_threshold > self.last_threshold:
            self.effects.append(Supernova(self.screen_w, self.screen_h))
            sound_system.resolution()          # Play the musical resolution sound
            self.last_threshold = current_threshold   # Remember this band so we don't re-trigger

        # If energy has fallen back, lower the watermark so future rises can trigger again
        elif current_threshold < self.last_threshold:
            self.last_threshold = current_threshold

    def update(self):
        """
        Advances all active effects by one frame, then removes any that have expired.
        Called once per frame in the game loop.
        """
        for effect in self.effects:
            effect.update()

        # List comprehension: keep only effects whose .alive property is True
        self.effects = [e for e in self.effects if e.alive]

    def draw(self, surface):
        """
        Draws all currently active effects onto the surface.
        Called once per frame after update().

        Parameters:
            surface : the main game surface to draw onto
        """
        for effect in self.effects:
            effect.draw(surface)
