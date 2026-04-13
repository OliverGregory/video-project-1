import numpy as np   # NumPy: numerical computing library.
                     # Used here for generating audio waveform arrays efficiently.
import pygame        # Game library; used for audio playback via pygame.mixer

# Audio constants
SAMPLE_RATE     = 44100   # Number of audio samples per second (44100 Hz = CD quality).
                          # Each "sample" is one amplitude value in the waveform.
NUM_TONES       = 32      # How many discrete ambient tones to divide the frequency range into.
FADE_MS         = 200     # Crossfade duration in milliseconds when switching ambient tones.
SLEEP_THRESHOLD = 0.5     # If average particle speed is below this, treat the system as "at rest"
                          # and stop the ambient sound from reacting.
HYSTERESIS      = 1       # Minimum change in tone index before switching.
                          # Prevents rapid flickering between two adjacent tones.


def _make_sine(frequency, duration, volume=0.2):
    """
    Generates a loopable stereo sine wave and returns it as a pygame Sound object.
    A sine wave is the purest possible tone — a single frequency with no harmonics.

    Parameters:
        frequency : pitch in Hz (e.g. 440 Hz = concert A)
        duration  : length of the sound clip in seconds (it will be looped)
        volume    : amplitude scaling, where 1.0 = maximum (can clip above ~0.7 in practice)

    Returns:
        A pygame.mixer.Sound object ready to play.
    """
    samples = int(SAMPLE_RATE * duration)   # Total number of samples in the clip

    # Create a linearly spaced time array: [0, 1/44100, 2/44100, ..., duration]
    # endpoint=False avoids a discontinuity when the clip loops (last sample ≠ first sample of next loop)
    t = np.linspace(0, duration, samples, endpoint=False)

    # Generate the sine wave: A·sin(2π·f·t)
    # Multiply by volume and 32767 (max value for 16-bit signed int) to scale correctly
    wave = (np.sin(2 * np.pi * frequency * t) * volume * 32767).astype(np.int16)

    # Duplicate the mono wave into two columns to create a stereo signal
    stereo = np.column_stack((wave, wave))   # Shape: (samples, 2)

    return pygame.sndarray.make_sound(stereo)   # Convert numpy array to pygame Sound


def _make_decaying_sine(frequency, duration=1.0, volume=0.4):
    """
    Generates a sine tone that decays exponentially from full amplitude to near silence.
    Used for the "resolution" event sound — a pleasant, bell-like tone.

    Parameters:
        frequency : pitch in Hz
        duration  : total clip length in seconds
        volume    : peak amplitude

    Returns:
        A pygame.mixer.Sound object.
    """
    samples = int(SAMPLE_RATE * duration)
    t       = np.linspace(0, duration, samples, endpoint=False)

    # Exponential decay envelope: starts at 1.0, falls toward 0 over the duration.
    # -4 controls how fast it decays; larger magnitude = faster decay.
    decay = np.exp(-4 * t / duration)

    # Multiply the sine wave by the decay envelope to get a fading tone
    wave   = (np.sin(2 * np.pi * frequency * t) * decay * volume * 32767).astype(np.int16)
    stereo = np.column_stack((wave, wave))
    return pygame.sndarray.make_sound(stereo)


def _make_ping(frequency=1200, duration=0.15, volume=0.3):
    """
    Generates a very short, sharp decaying tone — the "ping" for wall impacts.
    Higher frequency (1200 Hz) and fast decay gives a crisp click sound.

    Parameters:
        frequency : pitch in Hz (default: 1200, bright and percussive)
        duration  : total clip length in seconds
        volume    : peak amplitude

    Returns:
        A pygame.mixer.Sound object.
    """
    samples = int(SAMPLE_RATE * duration)
    t       = np.linspace(0, duration, samples, endpoint=False)

    # Very fast decay: exp(-20 * ...) drops to near zero well before `duration` ends
    decay  = np.exp(-20 * t / duration)
    wave   = (np.sin(2 * np.pi * frequency * t) * decay * volume * 32767).astype(np.int16)
    stereo = np.column_stack((wave, wave))
    return pygame.sndarray.make_sound(stereo)


class SoundSystem:
    """
    Manages all audio for the simulation.
    Uses four separate pygame mixer channels for independent volume/playback control:
      Channel 0: Ambient background tone (changes pitch with energy level)
      Channel 1: Mouse drone (swells when mouse is held)
      Channel 2: Wall impact ping
      Channel 3: Resolution chime (triggered by energy threshold events)
    """

    def __init__(self, min_freq=80, max_freq=880, max_speed=30):
        """
        Pre-bakes all audio samples and begins playing the ambient background tone.

        Parameters:
            min_freq  : lowest ambient frequency in Hz (played when system is nearly still)
            max_freq  : highest ambient frequency in Hz (played at maximum energy)
            max_speed : speed value that corresponds to max_freq
        """
        self.max_speed    = max_speed
        self.smooth_speed = 0.0   # A smoothed (low-pass filtered) version of avg_speed.
                                  # Prevents the tone from jumping erratically frame to frame.
        self.current_idx  = 0     # Index into self.ambient_sounds for the currently playing tone
        self.mouse_volume = 0.0   # Current volume of the mouse drone (fades in/out smoothly)

        # --- Pre-generate NUM_TONES ambient tones, evenly spaced in frequency ---
        # np.linspace(80, 880, 16) gives: [80, 106.7, 133.3, ..., 880]
        freqs               = np.linspace(min_freq, max_freq, NUM_TONES)
        self.ambient_sounds = [_make_sine(f, 2.0) for f in freqs]   # One Sound object per frequency

        # Grab a dedicated mixer channel and start the first (lowest) tone looping immediately
        self.ambient_ch = pygame.mixer.Channel(0)
        self.ambient_ch.play(self.ambient_sounds[0], loops=-1)   # loops=-1 means loop forever

        self.current_freq = float(min_freq)   # Track the currently playing frequency for the dashboard
        self._freqs       = list(freqs)       # Store all frequencies for lookup

        # --- Mouse drone: a low 110 Hz tone that grows louder when the mouse is held ---
        self.mouse_sound = _make_sine(110, 2.0, volume=1.0)   # Full-volume source; we control volume separately
        self.mouse_ch    = pygame.mixer.Channel(1)

        # --- Pre-baked one-shot sounds ---
        self.ping_sound       = _make_ping()                          # Short wall-impact click
        self.resolution_sound = _make_decaying_sine(528, duration=1.5)  # 528 Hz = "love frequency" / C5
        self.ping_ch          = pygame.mixer.Channel(2)
        self.resolution_ch    = pygame.mixer.Channel(3)

    def update_ambient(self, avg_speed):
        """
        Called every frame. Smoothly adjusts the ambient pitch to reflect current particle energy.
        Uses a low-pass filter (exponential moving average) to prevent sudden jumps.
        Only switches to a new tone if the target index has changed by more than HYSTERESIS.

        Parameters:
            avg_speed : mean speed of all particles this frame
        """
        # Dead-zone: treat very slow motion as silence to avoid constant low-level noise
        effective_speed = avg_speed if avg_speed > SLEEP_THRESHOLD else 0.0

        # Exponential moving average: smooth_speed moves 3% of the way toward effective_speed each frame.
        # This is a simple 1st-order low-pass filter: y[n] = y[n-1] + α * (x[n] - y[n-1])
        self.smooth_speed += (effective_speed - self.smooth_speed) * 0.03

        # Map smooth_speed to a tone index in range [0, NUM_TONES-1]
        t          = min(self.smooth_speed / self.max_speed, 1.0)   # Normalise to [0, 1]
        target_idx = int(t * (NUM_TONES - 1))                       # Scale to tone index

        # Only switch tone if the change exceeds the hysteresis threshold
        if abs(target_idx - self.current_idx) > HYSTERESIS:
            self.current_idx  = target_idx
            self.current_freq = self._freqs[target_idx]
            # Switch to the new tone with a 200ms crossfade (fade_ms) for a smooth transition
            self.ambient_ch.play(self.ambient_sounds[target_idx], loops=-1, fade_ms=FADE_MS)

    def update_mouse(self, held):
        """
        Called every frame. Fades the mouse drone in when the mouse button is held,
        and fades it out when released.

        Parameters:
            held : True if the left mouse button is currently pressed
        """
        if held:
            # Increase volume by 0.02 per frame (takes ~1 second to reach max volume of 0.4)
            self.mouse_volume = min(self.mouse_volume + 0.02, 0.4)

            # Start the drone if it isn't already playing
            if not self.mouse_ch.get_busy():
                self.mouse_ch.play(self.mouse_sound, loops=-1)

            self.mouse_ch.set_volume(self.mouse_volume)   # Apply the new volume level

        else:
            # Decrease volume faster than it increases (0.04 per frame) — snappier release feel
            self.mouse_volume = max(self.mouse_volume - 0.04, 0.0)
            self.mouse_ch.set_volume(self.mouse_volume)

            # Stop the channel completely once volume reaches zero (frees the resource)
            if self.mouse_volume == 0.0:
                self.mouse_ch.stop()

    def ping(self):
        """
        Plays the wall-impact ping sound once.
        The dedicated channel means it won't interrupt other sounds.
        """
        self.ping_ch.play(self.ping_sound)

    def resolution(self):
        """
        Plays the resolution chime once (triggered by energy threshold events).
        """
        self.resolution_ch.play(self.resolution_sound)
