import pygame
import requests




pygame.init()
map_img = pygame.image.load("../img/map.JPG")
screen = pygame.display.set_mode(map_img.get_size())
pygame.display.set_caption("Click to get coordinates")

info = pygame.display.Info()
SCREEN_WIDTH, SCREEN_HEIGHT = info.current_w, info.current_h
print(SCREEN_WIDTH, SCREEN_HEIGHT)

pygame.display.set_caption("Intelligent Route Planner (Llama)")

nodes = {
    "Main Gate": (155, 224),
    "C3 D-block": (662, 508),
    "C3 C-Block": (628, 503),
    "RLH": (235, 188),
    "IRC": (318, 218)
}

edges = {
    "Main Gate": ["C3 D-block", "C3 C-Block", "RLH", "IRC"],
    "C3 D-block": ["Main Gate", "C3 C-Block", "RLH", "IRC"],
    "RLH": ["Main Gate", "C3 C-Block", "IRC", "C3 D-block"],
    "IRC": ["Main Gate", "C3 C-Block", "RLH", "C3 D-Block"],
    "C3 C-Block": ["Main Gate", "IRC", "C3 D-block", "RLH"]
}

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            x, y = event.pos
            print(f"Clicked at: ({x}, {y})")

    screen.blit(map_img, (0, 0))
    pygame.display.update()

pygame.quit()
