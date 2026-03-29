import numpy as np
import pygame
 
SAMPLE_RATE = 44100
 
class AmbientTone:
    def __init__(self, min_freq=80, max_freq=880, max_speed=30):
        self.min_freq    = min_freq
        self.max_freq    = max_freq
        self.max_speed   = max_speed
        self.current_freq = min_freq
        self.channel     = pygame.mixer.Channel(0)
        self._play(self.current_freq)
 
    def _make_sound(self, frequency):
        # Generate two seconds of samples so the loop is long enough to avoid clicks
        samples  = SAMPLE_RATE * 2
        t        = np.linspace(0, 2, samples, endpoint=False)
        wave     = (np.sin(2 * np.pi * frequency * t) * 0.2 * 32767).astype(np.int16)
        stereo   = np.column_stack((wave, wave))
        return pygame.sndarray.make_sound(stereo)
 
    def _play(self, frequency):
        sound = self._make_sound(frequency)
        self.channel.play(sound, loops=-1, fade_ms=50)
 
    def update(self, avg_speed):
        t      = min(avg_speed / self.max_speed, 1.0)
        target = self.min_freq + t * (self.max_freq - self.min_freq)
 
        # Smoothly drift toward target
        self.current_freq += (target - self.current_freq) * 0.05
 
        # Only regenerate if frequency has shifted enough to be audible
        if abs(target - self.current_freq) > 5:
            self._play(self.current_freq)
 
