# intelligent_route_planner.py
import pygame, math, random, requests
from load_sprite import load_gif_frames

# -----------------------------
# Constants
# -----------------------------
EARTH_RADIUS = 6378137  # meters
BASE_LAT = 53.1665  # approx. campus center
BASE_LON = 8.652
SCREEN_TITLE = "Intelligent Route Planner (Llama)"
GPS_SERVER_URL = "http://127.0.0.1:8000/get"


# -----------------------------
# Web Mercator Conversion
# -----------------------------
def latlon_to_meters(lat, lon):
    """Convert lat/lon (degrees) → Web Mercator meters."""
    x = EARTH_RADIUS * math.radians(lon)
    y = EARTH_RADIUS * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    return x, y


BASE_X, BASE_Y = latlon_to_meters(BASE_LAT, BASE_LON)


def gps_to_pixel(lat, lon, scale, width, height):
    """Map GPS to pixel using Mercator projection and current scale."""
    x_m, y_m = latlon_to_meters(lat, lon)
    dx = (x_m - BASE_X) * scale
    dy = (y_m - BASE_Y) * -scale  # north-up
    return int(width / 2 + dx), int(height / 2 + dy)


# -----------------------------
# Tint System (day-night)
# -----------------------------
def apply_map_tint(screen, color, mode="add"):
    surf = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    surf.fill(color)
    flag = pygame.BLEND_RGBA_ADD if mode == "add" else pygame.BLEND_RGBA_MULT
    screen.blit(surf, (0, 0), special_flags=flag)


def dynamic_day_night_tint(screen, t):
    morning, evening, night = (0, 0, 220),(0, 100, 0), (0, 100, 0)
    cycle = (math.sin(t * 1e-13) + 1) / 2
    if cycle < 0.5:
        mix = cycle * 2
        r = int(evening[0] * (1 - mix) + night[0] * mix)
        g = int(evening[1] * (1 - mix) + night[1] * mix)
        b = int(evening[2] * (1 - mix) + night[2] * mix)
    else:
        mix = (cycle - 0.5) * 2
        r = int(night[0] * (1 - mix) + morning[0] * mix)
        g = int(night[1] * (1 - mix) + morning[1] * mix)
        b = int(night[2] * (1 - mix) + morning[2] * mix)
    apply_map_tint(screen, (r, g, b, 60))


# -----------------------------
# Dotted Background (aura)
# -----------------------------
def make_dots(w, h, n=300):
    return [{"x": random.randint(0, w),
             "y": random.randint(0, h),
             "r": random.randint(1, 3),
             "p": random.uniform(0, math.pi * 2)} for _ in range(n)]


def draw_dotted_background(screen, dots, t, center):
    for d in dots:
        dx, dy = d["x"] - center[0], d["y"] - center[1]
        dist = math.hypot(dx, dy)
        base = 100 + 60 * math.sin(t * 0.03 + d["p"])
        aura = max(0, 255 - dist * 1.2) if dist < 200 else 0
        bright = min(255, int(base + aura))
        col = (0, bright, bright)
        yoff = int(4 * math.sin(t * 0.02 + d["p"]))
        pygame.draw.circle(screen, col, (d["x"], d["y"] + yoff), d["r"])


# -----------------------------
# Trail Drawing
# -----------------------------
def draw_trail(screen, trail):
    n = len(trail)
    for i, (x, y, alpha) in enumerate(trail):
        t = i / n if n > 1 else 0
        # gradient rainbow
        if t < 0.25:
            r, g, b = 255, int(255 * (t / 0.25)), 0
        elif t < 0.5:
            r, g, b = int(255 * (1 - (t - 0.25) / 0.25)), 255, 0
        elif t < 0.75:
            r, g, b = 0, 255, int(255 * ((t - 0.5) / 0.25))
        else:
            r, g, b = 0, int(255 * (1 - (t - 0.75) / 0.25)), 255
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.005 + i * 0.2)
        fade = alpha * pulse
        col = (int(r * fade), int(g * fade), int(b * fade))
        radius = int(5 * fade) + 2
        pygame.draw.circle(screen, col, (int(x), int(y)), radius)


# -----------------------------
# HUD
# -----------------------------
def draw_hud(screen, lat, lon, scale):
    font = pygame.font.SysFont("Menlo", 16)
    lines = [
        f"GPS: {lat:.6f}, {lon:.6f}",
        f"Scale: {scale:.3f} px/m",
        "Zoom: + / -"
    ]
    y = 8
    for txt in lines:
        screen.blit(font.render(txt, True, (255, 255, 255)), (8, y))
        y += 18


# -----------------------------
# Init
# -----------------------------
pygame.init()
clock = pygame.time.Clock()

map_img = pygame.image.load("map_cartooned.png")
W, H = map_img.get_width(), map_img.get_height()
screen = pygame.display.set_mode((W + 20, H + 140))
pygame.display.set_caption(SCREEN_TITLE)

frames = load_gif_frames("llama (2).gif", 50)
frame_idx = 0
dots = make_dots(W, H)

trail = []
TRAIL_MAX = 250
time_wave = 0
scale = 0.6  # px per meter
llama_x = W // 2
llama_y = H // 2

latest_lat = BASE_LAT
latest_lon = BASE_LON
smooth_lat = latest_lat
smooth_lon = latest_lon

print(f"[INFO] Map {W}x{H} loaded, base=({BASE_LAT},{BASE_LON})")

# -----------------------------
# Main Loop
# -----------------------------
running = True
while running:
    clock.tick(20)
    time_wave += 2

    # --- Handle events ---
    for e in pygame.event.get():
        if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
            running = False
        elif e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_PLUS, pygame.K_EQUALS):
                scale *= 1.1
            elif e.key in (pygame.K_MINUS, pygame.K_UNDERSCORE):
                scale /= 1.1
            scale = max(0.05, min(5.0, scale))

    # --- Fetch GPS ---
    try:
        res = requests.get(GPS_SERVER_URL, timeout=1)
        data = res.json()
        lat, lon = data.get("lat"), data.get("lon")
        if lat and lon:
            latest_lat, latest_lon = float(lat), float(lon)
    except Exception:
        pass

    # --- Smooth GPS ---
    smooth_lat = 0.9 * smooth_lat + 0.1 * latest_lat
    smooth_lon = 0.9 * smooth_lon + 0.1 * latest_lon

    # --- Map projection ---
    target_x, target_y = gps_to_pixel(smooth_lat, smooth_lon, scale, W, H)
    offset_x = W / 2 - target_x
    offset_y = H / 2 - target_y

    # --- Draw map + effects ---
    screen.blit(map_img, (offset_x, offset_y))
    dynamic_day_night_tint(screen, time_wave)
    draw_dotted_background(screen, dots, time_wave, (W / 2, H / 2))

    # --- Trail ---
    if not trail or math.hypot(trail[-1][0] - W / 2, trail[-1][1] - H / 2) > 2:
        trail.append((W / 2, H / 2, 1.0))
        if len(trail) > TRAIL_MAX:
            trail.pop(0)
    for i in range(len(trail)):
        x, y, a = trail[i]
        trail[i] = (x, y, max(0, a - 0.01))
    draw_trail(screen, trail)

    # --- Bingo (fixed center) ---
    screen.blit(frames[frame_idx % len(frames)], (W // 2 - 20, H // 2 - 20))
    draw_hud(screen, smooth_lat, smooth_lon, scale)

    pygame.display.flip()
    frame_idx += 1

pygame.quit()
