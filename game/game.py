import pygame
import random
from ball import Ball
from environment import Environment
from sound import AmbientTone
 
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
clock = pygame.time.Clock()
 
IMPULSE       = 3
CENTRAL_FORCE = 1.5
 
env  = Environment(1280, 720)
balls = [
    Ball(
        x=random.randint(50, 1230),
        y=random.randint(50, 670),
        radius=6,
        vx=random.uniform(0, 0),
        vy=random.uniform(0, 0),
    )
    for _ in range(50)
]
player = balls[0]
tone   = AmbientTone()
 
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
                player.vy -= 5 * IMPULSE
            if event.key == pygame.K_DOWN:
                player.vy += IMPULSE
 
    for ball in balls:
        if pygame.mouse.get_pressed()[0]:
            mx, my = pygame.mouse.get_pos()
            ball.attract(mx, my, CENTRAL_FORCE)
        ball.update()
        env.apply_boundaries(ball)
 
    env.resolve_collisions(balls)
 
    avg_speed = sum(b.speed for b in balls) / len(balls)
    tone.update(avg_speed)
 
    env.screen.fill((15, 15, 15))
    for ball in balls:
        ball.draw(env.screen)
    pygame.display.flip()
    clock.tick(60)
 
pygame.quit()
 
