# intelligent_route_planner.py
import pygame, math, random
from load_sprite import load_gif_frames

def apply_map_tint(color, mode="add"):
    """Applies a transparent color overlay for warm/cool mood."""
    tint_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    tint_surface.fill(color)
    if mode == "add":
        screen.blit(tint_surface, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    elif mode == "mult":
        screen.blit(tint_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)


def dynamic_day_night_tint(t):
    """
    Smoothly shifts between morning (warm), noon (neutral),
    evening (golden), and night (cool).
    """

    # Base colors for each time of day
    morning = (255, 200, 150)
    noon = (255, 255, 255)
    evening = (255, 150, 80)
    night = (80, 120, 255)

    # Create smooth oscillation 0→1→0
    cycle = (math.sin(t * 0.001) + 1) / 2

    # Blend between evening and night (cycle through day)
    if cycle < 0.5:
        # transition from evening → night
        mix = cycle * 2
        r = int(evening[0] * (1 - mix) + night[0] * mix)
        g = int(evening[1] * (1 - mix) + night[1] * mix)
        b = int(evening[2] * (1 - mix) + night[2] * mix)
    else:
        # transition from night → morning
        mix = (cycle - 0.5) * 2
        r = int(night[0] * (1 - mix) + morning[0] * mix)
        g = int(night[1] * (1 - mix) + morning[1] * mix)
        b = int(night[2] * (1 - mix) + morning[2] * mix)

    # Apply tint
    apply_map_tint((r, g, b, 60), mode="add")


# -----------------------------
# Initialize
# -----------------------------
pygame.init()
clock = pygame.time.Clock()

info = pygame.display.Info()
SCREEN_WIDTH, SCREEN_HEIGHT = info.current_w, info.current_h
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Intelligent Route Planner (Llama)")

# -----------------------------
# Load Map
# -----------------------------
map_img = pygame.image.load("map.JPG")
map_img = pygame.transform.scale(map_img, (SCREEN_WIDTH, SCREEN_HEIGHT))

# -----------------------------
# Node + Edge Data
# -----------------------------
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
    "IRC": ["Main Gate", "C3 C-Block", "RLH", "C3 D-block"],
    "C3 C-Block": ["Main Gate", "IRC", "C3 D-block", "RLH"]
}

# -----------------------------
# Llama Sprite
# -----------------------------
frames = load_gif_frames("llama (2).gif", 50)
frame_index = 0
path = ["Main Gate", "IRC", "RLH"]
path_index = 0

# -----------------------------
# Background Dots (for aura)
# -----------------------------
NUM_DOTS = 300
dots = [
    {
        "x": random.randint(0, SCREEN_WIDTH),
        "y": random.randint(0, SCREEN_HEIGHT),
        "radius": random.randint(1, 3),
        "phase": random.uniform(0, math.pi * 2)
    }
    for _ in range(NUM_DOTS)
]

# -----------------------------
# Draw Dotted Background with Aura
# -----------------------------
def draw_dotted_background(t, llama_pos):
    for d in dots:
        # Distance to llama
        dx = d["x"] - llama_pos[0]
        dy = d["y"] - llama_pos[1]
        dist = math.sqrt(dx * dx + dy * dy)

        # Base shimmer
        base_brightness = 100 + 60 * math.sin(t * 0.03 + d["phase"])

        # Aura: brighten near llama
        aura_boost = max(0, 255 - dist * 1.2) if dist < 200 else 0
        brightness = min(255, int(base_brightness + aura_boost))
        color = (0, brightness, brightness)

        # Slight vertical motion
        y_offset = int(4 * math.sin(t * 0.02 + d["phase"]))
        pygame.draw.circle(screen, color, (d["x"], d["y"] + y_offset), d["radius"])

# -----------------------------
# Draw Pulsing Graph
# -----------------------------
def draw_graph(t):
    # Edges
    for node, connections in edges.items():
        for target in connections:
            pygame.draw.line(screen, (150, 150, 150), nodes[node], nodes[target], 2)

    # Nodes
    for name, (x, y) in nodes.items():
        base_radius = 10
        pulse_strength = 4
        phase_offset = hash(name) % 200
        pulse = math.sin((t + phase_offset) * 0.05)
        radius = base_radius + pulse_strength * pulse
        color_intensity = int(150 + 80 * pulse)
        color = (0, color_intensity, 170)

        pygame.draw.circle(screen, color, (x, y), int(radius))
        pygame.draw.circle(screen, (0, 255, 255), (x, y), int(radius) + 2, 2)

        font = pygame.font.SysFont("Arial", 16, bold=True)
        label = font.render(name, True, (255, 255, 255))
        screen.blit(label, (x + 12, y - 12))

# -----------------------------
# Main Loop
# -----------------------------
running = True
time_wave = 0
while running:
    clock.tick(30)
    time_wave += 2

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False

    # --- Animate llama position ---
    current = nodes[path[path_index]]
    next_index = (path_index + 1) % len(path)
    next_pos = nodes[path[next_index]]
    progress = (frame_index % 20) / 20.0
    llama_x = int(current[0] + (next_pos[0] - current[0]) * progress)
    llama_y = int(current[1] + (next_pos[1] - current[1]) * progress)

    # --- Draw everything ---
    screen.blit(map_img, (0, 0))
    draw_dotted_background(time_wave, (llama_x, llama_y))
    draw_graph(time_wave)

    # Draw llama sprite
    screen.blit(frames[frame_index % len(frames)], (llama_x - 20, llama_y - 20))
    frame_index = (frame_index + 1) % len(frames)
    if frame_index % 20 == 0:
        path_index = (path_index + 1) % len(path)

    pygame.display.flip()
    dynamic_day_night_tint(time_wave)
    screen.blit(map_img, (0, 0))

pygame.quit()
