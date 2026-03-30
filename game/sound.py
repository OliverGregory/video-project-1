import numpy as np
import pygame

SAMPLE_RATE     = 44100
NUM_TONES       = 16
FADE_MS         = 200
SLEEP_THRESHOLD = 0.5
HYSTERESIS      = 1

def _make_sine(frequency, duration, volume=0.2):
    samples = int(SAMPLE_RATE * duration)
    t       = np.linspace(0, duration, samples, endpoint=False)
    wave    = (np.sin(2 * np.pi * frequency * t) * volume * 32767).astype(np.int16)
    stereo  = np.column_stack((wave, wave))
    return pygame.sndarray.make_sound(stereo)

def _make_decaying_sine(frequency, duration=1.0, volume=0.4):
    samples = int(SAMPLE_RATE * duration)
    t       = np.linspace(0, duration, samples, endpoint=False)
    decay   = np.exp(-4 * t / duration)
    wave    = (np.sin(2 * np.pi * frequency * t) * decay * volume * 32767).astype(np.int16)
    stereo  = np.column_stack((wave, wave))
    return pygame.sndarray.make_sound(stereo)

def _make_ping(frequency=1200, duration=0.15, volume=0.3):
    samples = int(SAMPLE_RATE * duration)
    t       = np.linspace(0, duration, samples, endpoint=False)
    decay   = np.exp(-20 * t / duration)
    wave    = (np.sin(2 * np.pi * frequency * t) * decay * volume * 32767).astype(np.int16)
    stereo  = np.column_stack((wave, wave))
    return pygame.sndarray.make_sound(stereo)


class SoundSystem:
    def __init__(self, min_freq=80, max_freq=880, max_speed=30):
        self.max_speed    = max_speed
        self.smooth_speed = 0.0
        self.current_idx  = 0
        self.mouse_volume = 0.0

        # Ambient tone
        freqs               = np.linspace(min_freq, max_freq, NUM_TONES)
        self.ambient_sounds = [_make_sine(f, 2.0) for f in freqs]
        self.ambient_ch     = pygame.mixer.Channel(0)
        self.ambient_ch.play(self.ambient_sounds[0], loops=-1)
        self.current_freq   = float(min_freq)
        self._freqs         = list(freqs)

        # Mouse tone — a soft low drone that swells in volume
        self.mouse_sound = _make_sine(110, 2.0, volume=1.0)
        self.mouse_ch    = pygame.mixer.Channel(1)

        # Ping and resolution sounds — pre-baked
        self.ping_sound       = _make_ping()
        self.resolution_sound = _make_decaying_sine(528, duration=1.5)
        self.ping_ch          = pygame.mixer.Channel(2)
        self.resolution_ch    = pygame.mixer.Channel(3)

    def update_ambient(self, avg_speed):
        effective_speed = avg_speed if avg_speed > SLEEP_THRESHOLD else 0.0
        self.smooth_speed += (effective_speed - self.smooth_speed) * 0.03
        t          = min(self.smooth_speed / self.max_speed, 1.0)
        target_idx = int(t * (NUM_TONES - 1))
        if abs(target_idx - self.current_idx) > HYSTERESIS:
            self.current_idx  = target_idx
            self.current_freq = self._freqs[target_idx]
            self.ambient_ch.play(self.ambient_sounds[target_idx], loops=-1, fade_ms=FADE_MS)

    def update_mouse(self, held):
        if held:
            self.mouse_volume = min(self.mouse_volume + 0.02, 0.4)
            if not self.mouse_ch.get_busy():
                self.mouse_ch.play(self.mouse_sound, loops=-1)
            self.mouse_ch.set_volume(self.mouse_volume)
        else:
            self.mouse_volume = max(self.mouse_volume - 0.04, 0.0)
            self.mouse_ch.set_volume(self.mouse_volume)
            if self.mouse_volume == 0.0:
                self.mouse_ch.stop()

    def ping(self):
        self.ping_ch.play(self.ping_sound)

    def resolution(self):
        self.resolution_ch.play(self.resolution_sound)
