import pygame
import random
from ball import Ball
from environment import Environment
from events import EventSystem
from sound import SoundSystem
from dashboard import Dashboard

pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
clock = pygame.time.Clock()

GRAVITY_STRENGTH = 0.15   # px/frame²
IMPULSE          = 2.0    # px/frame
CENTRAL_FORCE    = 0.8    # px/frame²
NUM_PARTICLES    = 50

env    = Environment(1280, 720)
events = EventSystem(env.width, env.height)
sound  = SoundSystem()
dash   = Dashboard(width=320, height=460)

particles = [
    Ball(
        x=random.randint(50, 1230),
        y=random.randint(50, 670),
        radius=6,
        vx=random.uniform(-1.5, 1.5),
        vy=random.uniform(-1.5, 1.5),
    )
    for _ in range(NUM_PARTICLES)
]
player   = particles[0]
gravity_on = True

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                player.vx -= IMPULSE
            if event.key == pygame.K_RIGHT:
                player.vx += IMPULSE
            if event.key == pygame.K_UP:
                player.vy -= IMPULSE
            if event.key == pygame.K_DOWN:
                player.vy += IMPULSE
            if event.key == pygame.K_SPACE:
                gravity_on = not gravity_on

    mouse_held = pygame.mouse.get_pressed()[0]
    sound.update_mouse(mouse_held)

    for p in particles:
        if mouse_held:
            mx, my = pygame.mouse.get_pos()
            p.attract(mx, my, CENTRAL_FORCE)
        p.update(gravity_on=gravity_on, gravity_strength=GRAVITY_STRENGTH)
        hit, speed = env.apply_boundaries(p)
        if hit:
            events.wall_hit(p.x, p.y, speed)
            sound.ping()

    env.resolve_collisions(particles)

    avg_speed = sum(p.speed for p in particles) / len(particles)
    sound.update_ambient(avg_speed)
    events.check_energy(avg_speed, sound)
    events.update()
    dash.update(avg_speed, sound.current_freq)

    env.screen.fill((5, 3, 12))   # deep space black
    for p in particles:
        p.draw(env.screen)
    events.draw(env.screen)

    dash.render(env.screen, {
        "gravity":           f"{'ON' if gravity_on else 'OFF'}  [{GRAVITY_STRENGTH} px/frame²]",
        "impulse":           f"{IMPULSE} px/frame",
        "attraction force":  f"{CENTRAL_FORCE} px/frame²",
        "particles":         NUM_PARTICLES,
        "restitution":       f"{0.75} (dimensionless)",
    }, x=20, y=20)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
