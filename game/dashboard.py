import pygame

HISTORY = 180

class Dashboard:
    def __init__(self, width=320, height=420):
        self.width  = width
        self.height = height

        self.energy_history = []
        self.freq_history   = []

        self.font_small = pygame.font.SysFont("monospace", 11)
        self.font_title = pygame.font.SysFont("monospace", 13, bold=True)

        # Pre-create surface
        self.surface = pygame.Surface((width, height))
        self.surface = self.surface.convert()

    def update(self, avg_speed, current_freq):
        self.energy_history.append(avg_speed)
        self.freq_history.append(current_freq)

        if len(self.energy_history) > HISTORY:
            self.energy_history.pop(0)
            self.freq_history.pop(0)

    def draw_graph(self, surf, data, rect, color, max_val=30):
        if len(data) < 2:
            return

        x, y, w, h = rect
        step = w / (HISTORY - 1)

        points = []
        for i, val in enumerate(data):
            px = x + i * step
            py = y + h - (val / max_val) * h
            points.append((px, py))

        pygame.draw.lines(surf, color, False, points, 2)

    def render(self, screen, params, x, y):
        s = self.surface
        s.fill((10, 10, 20))

        # Title
        title = self.font_title.render("SYSTEM DASHBOARD", True, (136, 170, 255))
        s.blit(title, (self.width // 2 - title.get_width() // 2, 5))

        # Graph areas
        energy_rect = pygame.Rect(20, 40, self.width - 40, 120)
        audio_rect  = pygame.Rect(20, 200, self.width - 40, 120)

        # Background boxes
        pygame.draw.rect(s, (15, 15, 30), energy_rect)
        pygame.draw.rect(s, (15, 15, 30), audio_rect)

        # Grid lines
        for i in range(0, 31, 5):
            py = energy_rect.y + energy_rect.height - (i / 30) * energy_rect.height
            pygame.draw.line(s, (60, 60, 120), (energy_rect.x, py), (energy_rect.right, py), 1)

        # Draw energy graph
        self.draw_graph(s, self.energy_history, energy_rect, (80, 220, 255))

        # Normalize frequency (80–880 → 0–30)
        freq_norm = [(f - 80) / (880 - 80) * 30 for f in self.freq_history]

        # Draw audio graph
        self.draw_graph(s, freq_norm, audio_rect, (200, 140, 255))
        self.draw_graph(s, self.energy_history, audio_rect, (80, 220, 255))

        # Labels
        s.blit(self.font_small.render("Energy", True, (120, 140, 255)), (energy_rect.x, energy_rect.y - 14))
        s.blit(self.font_small.render("Audio", True, (180, 150, 255)), (audio_rect.x, audio_rect.y - 14))

        # Parameters text
        py = self.height - 90
        for key, val in params.items():
            if isinstance(val, float):
                text = f"{key}: {val:.3f}"
            else:
                text = f"{key}: {val}"

            txt = self.font_small.render(text, True, (140, 140, 190))
            s.blit(txt, (20, py))
            py += 14

        # Blit to screen
        screen.blit(s, (x, y))
