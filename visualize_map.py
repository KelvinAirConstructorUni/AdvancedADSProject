# intelligent_route_planner.py
import pygame, math, random
from load_sprite import load_gif_frames
from path_finding import a_star_search

# -----------------------------
# Utility: Bezier Curve for Smooth Paths
# -----------------------------
def bezier_curve(points, num_steps=30):
    """Generates smooth interpolation between route points."""
    if len(points) < 2:
        return points
    def lerp(p1, p2, t):
        return (p1[0] + (p2[0] - p1[0]) * t, p1[1] + (p2[1] - p1[1]) * t)
    curve = []
    for i in range(len(points) - 1):
        p0, p1 = points[i], points[i + 1]
        for t in [j / num_steps for j in range(num_steps)]:
            curve.append(lerp(p0, p1, t))
    curve.append(points[-1])
    return curve

# -----------------------------
# Tint System
# -----------------------------
def apply_map_tint(color, mode="add"):
    tint_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    tint_surface.fill(color)
    flag = pygame.BLEND_RGBA_ADD if mode == "add" else pygame.BLEND_RGBA_MULT
    screen.blit(tint_surface, (0, 0), special_flags=flag)

def dynamic_day_night_tint(t):
    morning, evening, night = (20, 200, 0), (20, 150, 10), (0, 120, 1)
    cycle = (math.sin(t * 0.0000000000000001) + 1) / 2  # faster

    if cycle < 0.5:
        mix = cycle * 2
        r = int(evening[0]*(1-mix) + night[0]*mix)
        g = int(evening[1]*(1-mix) + night[1]*mix)
        b = int(evening[2]*(1-mix) + night[2]*mix)
    else:
        mix = (cycle - 0.5) * 2
        r = int(night[0]*(1-mix) + morning[0]*mix)
        g = int(night[1]*(1-mix) + morning[1]*mix)
        b = int(night[2]*(1-mix) + morning[2]*mix)
    apply_map_tint((r, g, b, 60))

# -----------------------------
# Init
# -----------------------------
# -----------------------------
# Init
# -----------------------------
# -----------------------------
# Init
# -----------------------------
pygame.init()
clock = pygame.time.Clock()

# Load the image once to get its original dimensions
temp_img = pygame.image.load("map_cartooned.png")
SCREEN_WIDTH, SCREEN_HEIGHT = temp_img.get_width(), temp_img.get_height()

# Create window matching the image size
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Intelligent Route Planner (Llama)")

# Now convert AFTER the window is ready
map_img = temp_img.convert()

print(f"[INFO] Loaded map at {SCREEN_WIDTH}x{SCREEN_HEIGHT}")



# -----------------------------
# Map + Data
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

frames = load_gif_frames("llama (2).gif", 50)
frame_index = 0
path_index = 0

start_node = None
end_node = None
path = []

# -----------------------------
# Background Dots (Aura)
# -----------------------------
NUM_DOTS = 300
dots = [
    {"x": random.randint(0, SCREEN_WIDTH),
     "y": random.randint(0, SCREEN_HEIGHT),
     "radius": random.randint(1, 3),
     "phase": random.uniform(0, math.pi * 2)}
    for _ in range(NUM_DOTS)
]

def draw_dotted_background(t, llama_pos):
    for d in dots:
        dx, dy = d["x"] - llama_pos[0], d["y"] - llama_pos[1]
        dist = math.hypot(dx, dy)
        base = 100 + 60 * math.sin(t * 0.03 + d["phase"])
        aura = max(0, 255 - dist * 1.2) if dist < 200 else 0
        brightness = min(255, int(base + aura))
        color = (0, brightness, brightness)
        y_off = int(4 * math.sin(t * 0.02 + d["phase"]))
        pygame.draw.circle(screen, color, (d["x"], d["y"] + y_off), d["radius"])

# -----------------------------
# Draw Graph (Nodes + Edges)
# -----------------------------
def draw_graph(t):
    for n, conns in edges.items():
        for c in conns:
            pygame.draw.line(screen, (40, 40, 40), nodes[n], nodes[c], 6)
            pygame.draw.line(screen, (0, 255, 200), nodes[n], nodes[c], 2)

    for name, (x, y) in nodes.items():
        pulse = math.sin((t + (hash(name) % 200)) * 0.05)
        radius = 10 + 4 * pulse
        color = (0, int(150 + 80 * pulse), 170)
        pygame.draw.circle(screen, color, (x, y), int(radius))
        pygame.draw.circle(screen, (0, 255, 255), (x, y), int(radius) + 2, 2)
        label = pygame.font.SysFont("Arial", 16, bold=True).render(name, True, (255, 255, 255))
        screen.blit(label, (x + 12, y - 12))

    if start_node:
        pygame.draw.circle(screen, (255, 200, 0), nodes[start_node], 14, 3)
    if end_node:
        pygame.draw.circle(screen, (255, 100, 100), nodes[end_node], 14, 3)

# -----------------------------
# Route Glow + Energy Particles
# -----------------------------
def draw_glowing_path(path_points, t):
    if not path_points:
        return

    smooth = bezier_curve(path_points, num_steps=30)

    # Pulse brightness (for line)
    pulse = (math.sin(t * 0.05) + 1) / 2
    glow = int(100 + 155 * pulse)

    # Outer glow
    for i in range(len(smooth) - 1):
        pygame.draw.line(screen, (0, glow//2, glow//2), smooth[i], smooth[i + 1], 10)
    # Inner bright core
    for i in range(len(smooth) - 1):
        pygame.draw.line(screen, (0, 255, 200), smooth[i], smooth[i + 1], 4)

    # Energy Particles (color shift along path)
    num_particles = 14
    for i in range(num_particles):
        idx = int((t * 0.5 + i * 20) % len(smooth))
        x, y = smooth[idx]

        # Progress along path (0=start, 1=end)
        progress_ratio = i / num_particles

        # Gradient color (blue → cyan → lime → yellow → gold)
        def lerp(a, b, t): return int(a + (b - a) * t)
        if progress_ratio < 0.5:
            # blue → cyan → lime
            r = lerp(0, 0, progress_ratio * 2)
            g = lerp(150, 255, progress_ratio * 2)
            b = lerp(255, 0, progress_ratio * 2)
        else:
            # lime → yellow → gold
            r = lerp(0, 255, (progress_ratio - 0.5) * 2)
            g = lerp(255, 200, (progress_ratio - 0.5) * 2)
            b = lerp(0, 50, (progress_ratio - 0.5) * 2)

        color = (r, g, b)
        r_size = 5 + 2 * math.sin(t * 0.1 + i)
        pygame.draw.circle(screen, color, (int(x), int(y)), int(r_size))

# -----------------------------
# Main Loop
# -----------------------------
running = True
time_wave = 0
llama_x, llama_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2

while running:
    clock.tick(30)
    time_wave += 2

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False

        # Click to set start/end
        if event.type == pygame.MOUSEBUTTONDOWN:
            x, y = event.pos
            for name, (nx, ny) in nodes.items():
                if math.hypot(nx - x, ny - y) < 20:
                    if event.button == 1:
                        start_node = name
                        print("Start:", start_node)
                    elif event.button == 3:
                        end_node = name
                        print("End:", end_node)
                    if start_node and end_node:
                        path = a_star_search(start_node, end_node, nodes, edges)
                        print("Path:", path)
                        frame_index = 0
                        path_index = 0
                    break

    # --- Draw Layers ---
    screen.blit(map_img, (0, 0))
    dynamic_day_night_tint(time_wave)

    if path and len(path) > 1:
        path_points = [nodes[p] for p in path]
        smooth_points = bezier_curve(path_points, num_steps=25)

        # Draw the smooth curved path instead of straight lines
        for i in range(len(smooth_points) - 1):
            pygame.draw.line(screen, (0, 255, 200), smooth_points[i], smooth_points[i + 1], 3)

        # Move Bingo along this smooth curve
        point = smooth_points[min(frame_index % len(smooth_points), len(smooth_points) - 1)]
        llama_x, llama_y = int(point[0]), int(point[1])
        frame_index += 1

    draw_dotted_background(time_wave, (llama_x, llama_y))
    draw_graph(time_wave)
    screen.blit(frames[frame_index % len(frames)], (llama_x - 20, llama_y - 20))

    pygame.display.flip()

pygame.quit()
