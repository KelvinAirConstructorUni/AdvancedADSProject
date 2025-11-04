# intelligent_route_planner.py
import pygame, math, random, requests
from load_sprite import load_gif_frames

# =====================================================
# CONFIG
# =====================================================
GPS_SERVER_URL = "http://127.0.0.1:8000/get"

pygame.init()
clock = pygame.time.Clock()
SCREEN_WIDTH, SCREEN_HEIGHT = 1280, 800
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Intelligent Route Planner (Campus Edition 🦙)")

frames = load_gif_frames("llama (2).gif", 50)
frame_idx = 0

# =====================================================
# LOAD CAMPUS MAP
# =====================================================
try:
    map_img = pygame.image.load("map_cartooned.png").convert()
    map_img = pygame.transform.smoothscale(map_img, (SCREEN_WIDTH, SCREEN_HEIGHT))
    print(f"[INFO] Loaded campus map at {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
except Exception as e:
    raise SystemExit(f"❌ Could not load campus map: {e}")

# =====================================================
# BACKGROUND EFFECTS
# =====================================================
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

def beautify_map():
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((15, 20, 40, 60))
    screen.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    vignette = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    for x in range(0, SCREEN_WIDTH, 6):
        for y in range(0, SCREEN_HEIGHT, 6):
            dx, dy = (x - SCREEN_WIDTH/2)/(SCREEN_WIDTH/2), (y - SCREEN_HEIGHT/2)/(SCREEN_HEIGHT/2)
            dist = min(1, math.sqrt(dx*dx + dy*dy))
            shade = int(150 * dist)
            vignette.fill((0, 0, 0, shade), (x, y, 6, 6))
    screen.blit(vignette, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)

def dynamic_day_night_tint(t):
    morning, evening, night = (20, 100, 0), (20, 100, 10), (0, 100, 1)
    cycle = (math.sin(t * 0.0000000000000001) + 1) / 2
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
    tint_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    tint_surface.fill((r, g, b, 60))
    screen.blit(tint_surface, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

# =====================================================
# TRAIL EFFECT
# =====================================================
trail = []
TRAIL_MAX_LEN = 250
def draw_trail(surface):
    n = len(trail)
    for i, (x, y, alpha) in enumerate(trail):
        t = i / n if n > 1 else 0
        # Rainbow gradient
        if t < 0.25: r, g, b = 255, int(255*(t/0.25)), 0
        elif t < 0.5: r, g, b = int(255*(1-(t-0.25)/0.25)), 255, 0
        elif t < 0.75: r, g, b = 0, 255, int(255*((t-0.5)/0.25))
        else: r, g, b = 0, int(255*(1-(t-0.75)/0.25)), 255
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.005 + i * 0.2)
        fade = alpha * pulse
        color = (int(r*fade), int(g*fade), int(b*fade))
        radius = int(5 * fade) + 2
        pygame.draw.circle(surface, color, (int(x), int(y)), radius)

# =====================================================
# MAIN LOOP
# =====================================================
running = True
time_wave = 0
frame_idx = 0
llama_x, llama_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
latest_lat = latest_lon = None

print("[INFO] Campus map mode active 🏫")

while running:
    clock.tick(30)
    time_wave += 2

    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            running = False

    # --- Fetch GPS ---
    try:
        res = requests.get(GPS_SERVER_URL, timeout=1)
        data = res.json()
        latest_lat, latest_lon = data.get("lat"), data.get("lon")
    except Exception:
        pass

    # --- Draw layers ---
    screen.blit(map_img, (0, 0))
    beautify_map()
    dynamic_day_night_tint(time_wave)
    draw_dotted_background(time_wave, (llama_x, llama_y))

    # --- Trail ---
    if not trail or math.hypot(trail[-1][0]-llama_x, trail[-1][1]-llama_y) > 2:
        trail.append((llama_x, llama_y, 1.0))
        if len(trail) > TRAIL_MAX_LEN: trail.pop(0)
    for i in range(len(trail)):
        x, y, alpha = trail[i]
        trail[i] = (x, y, max(0, alpha - 0.01))
    draw_trail(screen)

    # --- Bingo 🦙 ---
    screen.blit(frames[frame_idx % len(frames)], (llama_x - 20, llama_y - 20))
    frame_idx += 1

    pygame.display.flip()

pygame.quit()
