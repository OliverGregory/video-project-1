import pygame   # Game library used here for drawing text, rectangles, and lines onto surfaces

HISTORY = 180   # Number of past data points to keep in memory for the graphs.
                # At 60 frames per second, this represents the last 3 seconds of data.


class Dashboard:
    """
    A heads-up display (HUD) panel drawn in the corner of the screen.
    Shows two real-time line graphs:
      1. Average particle energy (speed) over time
      2. Audio frequency over time
    Also displays the current simulation parameters as text.
    """

    def __init__(self, width=320, height=420):
        """
        Constructor. Sets up the dashboard dimensions, empty data histories, fonts, and drawing surface.

        Parameters:
            width, height : size of the dashboard panel in pixels
        """
        self.width  = width
        self.height = height

        # These lists accumulate data over time; each frame a new value is appended.
        # They are trimmed to `HISTORY` entries so the graph always shows a fixed time window.
        self.energy_history = []   # Stores average particle speed values over time
        self.freq_history   = []   # Stores the audio frequency values over time

        # Load two monospace fonts at different sizes for labels and titles.
        # "monospace" gives a clean, technical look suited to a data dashboard.
        self.font_small = pygame.font.SysFont("monospace", 11)
        self.font_title = pygame.font.SysFont("monospace", 13, bold=True)

        # Create a dedicated off-screen surface to draw the dashboard onto each frame.
        # This avoids drawing directly on the main screen until everything is ready.
        self.surface = pygame.Surface((width, height))
        self.surface = self.surface.convert()   # .convert() speeds up blitting (copying to screen)

    def update(self, avg_speed, current_freq):
        """
        Records a new data point for each graph. Called once per frame.

        Parameters:
            avg_speed    : mean speed of all particles this frame
            current_freq : audio tone frequency currently playing
        """
        # Append new readings to the history lists
        self.energy_history.append(avg_speed)
        self.freq_history.append(current_freq)

        # Keep each list at most HISTORY entries long.
        # pop(0) removes the oldest entry from the front, like a queue (FIFO).
        if len(self.energy_history) > HISTORY:
            self.energy_history.pop(0)
            self.freq_history.pop(0)

    def draw_graph(self, surf, data, rect, color, max_val=30):
        """
        Draws a line graph of `data` inside the rectangle `rect`.
        The graph scrolls left as new data arrives — older values are on the left.

        Parameters:
            surf    : the pygame Surface to draw onto
            data    : list of numerical values to plot
            rect    : a (x, y, width, height) tuple defining the graph's bounding box
            color   : RGB tuple for the line colour
            max_val : the value that maps to the top of the graph (used for scaling)
        """
        if len(data) < 2:
            return   # Need at least 2 points to draw a line; skip if we don't have enough yet

        x, y, w, h = rect   # Unpack the bounding box

        # Horizontal spacing between data points.
        # If HISTORY=180 points fit in width w pixels, each step is w/179 pixels wide.
        step = w / (HISTORY - 1)

        # Build a list of (px, py) screen coordinates for each data value.
        points = []
        for i, val in enumerate(data):
            px = x + i * step                      # x grows left-to-right with each sample
            py = y + h - (val / max_val) * h       # y: subtract from bottom so higher values appear higher
                                                   # (val/max_val) is a fraction in [0,1]; multiply by h to get pixels
            points.append((px, py))

        # Draw all the points connected as a continuous polyline (not closed/filled)
        pygame.draw.lines(surf, color, False, points, 2)   # line thickness = 2 pixels

    def render(self, screen, params, x, y):
        """
        Draws the entire dashboard onto the main screen.
        Called once per frame after update().

        Parameters:
            screen : the main pygame display surface
            params : a dictionary of simulation parameters to display as text
            x, y   : pixel position on the main screen where the dashboard is placed
        """
        s = self.surface        # Shorthand alias for the dashboard's own surface
        s.fill((10, 10, 20))   # Clear the surface with a very dark navy background each frame

        # Title:
        title = self.font_title.render("SYSTEM DASHBOARD", True, (136, 170, 255))
        # Centre the title horizontally: offset = (panel_width - text_width) / 2
        s.blit(title, (self.width // 2 - title.get_width() // 2, 5))

        # Define graph bounding rectangles:
        # Each Rect is (left, top, width, height) in pixels relative to the dashboard surface
        energy_rect = pygame.Rect(20, 40, self.width - 40, 120)    # Top graph (energy)
        audio_rect  = pygame.Rect(20, 200, self.width - 40, 120)   # Bottom graph (audio)

        # Background fill for each graph area:
        pygame.draw.rect(s, (15, 15, 30), energy_rect)   # Slightly lighter than background
        pygame.draw.rect(s, (15, 15, 30), audio_rect)

        # Horizontal grid lines for the energy graph:
        # Draw a faint horizontal line every 5 units from 0 to 30
        for i in range(0, 31, 5):
            # Map data value i → a pixel y-coordinate inside energy_rect
            py = energy_rect.y + energy_rect.height - (i / 30) * energy_rect.height
            pygame.draw.line(s, (60, 60, 120),
                             (energy_rect.x, py),
                             (energy_rect.right, py), 1)   # 1-pixel-thick faint line

        # Draw the energy graph (cyan line):
        self.draw_graph(s, self.energy_history, energy_rect, (80, 220, 255))

        # Normalise audio frequency for the graph:
        # The frequency range is 80 Hz to 880 Hz.
        # We remap this to [0, 30] so it fits on the same scale as the energy graph.
        # Formula: (f - min) / (max - min) * target_max
        freq_norm = [(f - 80) / (880 - 80) * 30 for f in self.freq_history]

        # Draw both lines on the audio graph panel:
        self.draw_graph(s, freq_norm, audio_rect, (200, 140, 255))    # Purple: frequency
        self.draw_graph(s, self.energy_history, audio_rect, (80, 220, 255))  # Cyan: energy (overlaid for comparison)

        # Graph labels (small text above each graph):
        s.blit(self.font_small.render("Energy", True, (120, 140, 255)), (energy_rect.x, energy_rect.y - 14))
        s.blit(self.font_small.render("Audio",  True, (180, 150, 255)), (audio_rect.x, audio_rect.y - 14))

        # Simulation parameters text block:
        # Start drawing text near the bottom of the dashboard panel
        py = self.height - 90

        for key, val in params.items():
            # Format floats to 3 decimal places; display other types (int, str) as-is
            if isinstance(val, float):
                text = f"{key}: {val:.3f}"
            else:
                text = f"{key}: {val}"

            txt = self.font_small.render(text, True, (140, 140, 190))   # Light blue-grey text
            s.blit(txt, (20, py))   # Draw each parameter line 20 pixels from the left
            py += 14                # Move down 14 pixels for the next line

        # Blit the completed dashboard surface onto the main screen:
        # Everything above was drawn to self.surface (off-screen); this copies it to the visible window.
        screen.blit(s, (x, y))
