import pygame    # Core game library: window, input, drawing, timing
import random    # Used to place particles at random starting positions and velocities

# Import all the custom classes from the other files in the project
from ball        import Ball          # The particle/ball physics object
from environment import Environment   # Manages the window, walls, and collision grid
from events      import EventSystem   # Manages visual effects (sparks, supernovas)
from sound       import SoundSystem   # Manages audio tones and sound effects
from dashboard   import Dashboard     # The HUD overlay showing graphs and parameters

# Initialise pygame's core systems (must be called before anything else in pygame)
pygame.init()
# Initialise the audio mixer with specific settings:
#   frequency=44100 : audio sample rate in Hz (CD quality)
#   size=-16        : 16-bit signed audio samples
#   channels=2      : stereo output
#   buffer=512      : small buffer for low-latency audio
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

# Clock object used to cap the frame rate and measure time between frames
clock = pygame.time.Clock()

# --- Simulation constants ---
GRAVITY_STRENGTH = 0.15   # Downward acceleration per frame (pixels per frame²)
IMPULSE          = 2.0    # Speed added to the player ball per arrow-key press (pixels per frame)
CENTRAL_FORCE    = 0.8    # Attraction strength toward the mouse when held (pixels per frame²)
NUM_PARTICLES    = 75     # Total number of balls in the simulation

# --- Create the main system objects ---
env    = Environment(1280, 720)              # 1280×720 pixel window
events = EventSystem(env.width, env.height)  # Pass screen size so Supernova knows the boundaries
sound  = SoundSystem()                       # Generates and plays audio tones
dash   = Dashboard(width=320, height=460)    # HUD panel: 320×460 pixels

# --- Spawn particles at random positions with small random initial velocities ---
# List comprehension creates NUM_PARTICLES Ball objects in one go
particles = [
    Ball(
        x=random.randint(50, 1230),          # Random x position within the window (with padding)
        y=random.randint(50, 670),           # Random y position
        radius=6,                            # All balls have the same radius
        vx=random.uniform(-1.5, 1.5),        # Random horizontal velocity in range [-1.5, 1.5]
        vy=random.uniform(-1.5, 1.5),        # Random vertical velocity
    )
    for _ in range(NUM_PARTICLES)            # _ means "we don't need the loop index"
]

# The first particle is designated as the "player" ball (controlled by arrow keys)
player   = particles[0]

# Gravity starts switched on
gravity_on = True

# --- Main game loop ---
# This loop runs once per frame, at up to 60 frames per second.
running = True
while running:

    # --- Event processing: handle keyboard and window events ---
    for event in pygame.event.get():

        # The user clicked the window's close button
        if event.type == pygame.QUIT:
            running = False   # Signal the loop to exit after this frame

        # A key was pressed (not held — fires once per press)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                player.vx -= IMPULSE   # Nudge player leftward
            if event.key == pygame.K_RIGHT:
                player.vx += IMPULSE   # Nudge player rightward
            if event.key == pygame.K_UP:
                player.vy -= IMPULSE   # Nudge player upward (negative because y increases downward)
            if event.key == pygame.K_DOWN:
                player.vy += IMPULSE   # Nudge player downward
            if event.key == pygame.K_SPACE:
                gravity_on = not gravity_on   # Toggle gravity on/off

    # Check if the left mouse button is currently held (index 0 = left button)
    mouse_held = pygame.mouse.get_pressed()[0]

    # Tell the sound system whether the mouse is held; it adjusts the drone volume accordingly
    sound.update_mouse(mouse_held)

    # --- Physics update: move every particle and handle wall collisions ---
    for p in particles:

        # If mouse is held, attract every particle toward the cursor
        if mouse_held:
            mx, my = pygame.mouse.get_pos()   # Get current mouse cursor position in pixels
            p.attract(mx, my, CENTRAL_FORCE)  # Apply attraction force toward (mx, my)

        # Update position using velocity (and optionally gravity)
        p.update(gravity_on=gravity_on, gravity_strength=GRAVITY_STRENGTH)

        # Check wall collisions and reflect velocity if needed
        # Returns whether a wall was hit and the ball's speed at impact
        hit, speed = env.apply_boundaries(p)

        if hit:
            events.wall_hit(p.x, p.y, speed)   # Spawn a spark visual effect at impact point
            sound.ping()                        # Play a brief ping sound

    # --- Ball-ball collision detection and resolution ---
    # Uses the spatial grid inside env to avoid O(n²) pair checking
    env.resolve_collisions(particles)

    # --- Global energy and audio ---
    # Compute the mean speed across all particles this frame
    avg_speed = sum(p.speed for p in particles) / len(particles)

    sound.update_ambient(avg_speed)       # Adjust the background ambient tone to match energy level
    events.check_energy(avg_speed, sound) # Check if energy crossed a threshold → fire Supernova
    events.update()                       # Advance all active visual effects by one frame

    # Record this frame's data in the dashboard history
    dash.update(avg_speed, sound.current_freq)

    # --- Rendering ---
    # Fill the screen with a near-black deep-space colour before drawing anything
    env.screen.fill((5, 3, 12))   # (R=5, G=3, B=12) — very dark navy/black

    # Draw every particle
    for p in particles:
        p.draw(env.screen)

    # Draw any active visual effects (sparks, supernovas) on top of the particles
    events.draw(env.screen)

    # Draw the HUD dashboard in the top-left corner, with a description of current parameters
    dash.render(env.screen, {
        "Fps":               f"{clock.get_fps():.1f}",
        "Gravity":           f"{'ON' if gravity_on else 'OFF'} at {GRAVITY_STRENGTH} (px/frame)",
        "Impulse":           f"{IMPULSE} (px/frame)",
        "Attraction force":  f"{CENTRAL_FORCE} (px/frame)",
        "Particles":         NUM_PARTICLES,
        "Restitution":       f"{0.75} (dimensionless)",
    }, x=20, y=20)   # Place the dashboard at screen position (20, 20)

    # Flip the display: swap the back buffer to the screen (makes all drawing visible at once)
    pygame.display.flip()

    # Cap the frame rate at 60 FPS.
    # clock.tick(60) will pause long enough so each frame takes at least 1/60 of a second.
    clock.tick(60)

# Clean up and close the window once the loop exits
pygame.quit()
