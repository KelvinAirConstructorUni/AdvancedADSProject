# intelligent_route_planner.py
import pygame, math, random, requests
from load_sprite import load_gif_frames

# -----------------------------
# Constants
# -----------------------------
EARTH_RADIUS = 6378137
BASE_LAT = 53.1665
BASE_LON = 8.652
SCREEN_TITLE = "Intelligent Route Planner (Llama)"
GPS_SERVER_URL = "http://127.0.0.1:8000/get"
# --- Keep this global state at top of file ---
popup_alpha = 0
last_hovered = None

# -----------------------------
# Web Mercator Conversion
# -----------------------------
def latlon_to_meters(lat, lon):
    x = EARTH_RADIUS * math.radians(lon)
    y = EARTH_RADIUS * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    return x, y

BASE_X, BASE_Y = latlon_to_meters(BASE_LAT, BASE_LON)

def gps_to_pixel(lat, lon, scale, width, height):
    x_m, y_m = latlon_to_meters(lat, lon)
    dx = (x_m - BASE_X) * scale
    dy = (y_m - BASE_Y) * -scale
    return int(width / 2 + dx), int(height / 2 + dy)

# -----------------------------
# Tint System
# -----------------------------
def apply_map_tint(screen, color, mode="add"):
    surf = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    surf.fill(color)
    flag = pygame.BLEND_RGBA_ADD if mode == "add" else pygame.BLEND_RGBA_MULT
    screen.blit(surf, (0, 0), special_flags=flag)

def dynamic_day_night_tint(screen, t):
    morning, evening, night = (0, 0, 220), (0, 100, 0), (0, 100, 0)
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
# Background Dots
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
# Trail
# -----------------------------
def draw_trail(screen, trail):
    n = len(trail)
    for i, (x, y, alpha) in enumerate(trail):
        t = i / n if n > 1 else 0
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
# Hover Popup
# -----------------------------
def draw_popup(screen, name, info, pos, t=0):
    """Pixel-style speech bubble popup for building hover."""
    font_title = pygame.font.SysFont("PressStart2P", 13, bold=True)
    font_text = pygame.font.SysFont("PressStart2P", 11)
    lines = [name] + [f"Rooms: {', '.join(info)}"]
    text_surfaces = [font_title.render(lines[0], True, (255, 255, 255))] + [
        font_text.render(l, True, (200, 255, 255)) for l in lines[1:]
    ]

    max_w = max(s.get_width() for s in text_surfaces)
    total_h = sum(s.get_height() for s in text_surfaces) + 12

    # Speech bubble container
    bubble = pygame.Surface((max_w + 18, total_h + 10), pygame.SRCALPHA)
    bubble.fill((20, 20, 20, 240))
    pygame.draw.rect(bubble, (0, 255, 255), bubble.get_rect(), 2)

    # Pixelated jagged edges for retro look
    for i in range(0, bubble.get_width(), 3):
        pygame.draw.line(bubble, (0, 255, 255), (i, 0), (i, 1))
        pygame.draw.line(bubble, (0, 255, 255), (i, bubble.get_height() - 2), (i, bubble.get_height() - 1))
    for j in range(0, bubble.get_height(), 3):
        pygame.draw.line(bubble, (0, 255, 255), (0, j), (1, j))
        pygame.draw.line(bubble, (0, 255, 255), (bubble.get_width() - 2, j), (bubble.get_width() - 1, j))

    # Add text
    y = 6
    for s in text_surfaces:
        bubble.blit(s, (9, y))
        y += s.get_height()

    # Tail triangle (speech tip)
    tip = pygame.Surface((20, 12), pygame.SRCALPHA)
    pygame.draw.polygon(tip, (20, 20, 20, 240), [(0, 0), (20, 0), (10, 12)])
    pygame.draw.polygon(tip, (0, 255, 255), [(0, 0), (20, 0), (10, 12)], 2)

    # Gentle pop animation (hover pulse)
    pop = 1.0 + 0.02 * math.sin(pygame.time.get_ticks() * 0.01)
    bw, bh = bubble.get_width(), bubble.get_height()
    bubble = pygame.transform.scale(bubble, (int(bw * pop), int(bh * pop)))

    # Draw bubble + tail
    bubble_x, bubble_y = pos[0] + 15, pos[1] - bh - 15
    screen.blit(bubble, (bubble_x, bubble_y))
    screen.blit(tip, (bubble_x + bw // 2 - 10, bubble_y + bh - 2))

# -----------------------------
# HUD
# -----------------------------
def draw_hud(screen, lat, lon, scale, pixel_mode):
    font = pygame.font.SysFont("Menlo", 16)
    lines = [
        f"GPS: {lat:.6f}, {lon:.6f}",
        f"Scale: {scale:.3f} px/m",
        f"Zoom: + / - | Pixel mode: {'ON' if pixel_mode else 'OFF'} (Z)"
    ]
    y = 8
    for txt in lines:
        screen.blit(font.render(txt, True, (255, 255, 255)), (8, y))
        y += 18

# -----------------------------
# Bingo Radar Pulse
# -----------------------------
def draw_radar(screen, center, time_wave):
    for i in range(3):
        radius = 40 + i * 25 + (time_wave % 50)
        alpha = max(0, 150 - (radius - 40) * 3)
        color = (0, 255, 200, alpha)
        surf = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        pygame.draw.circle(surf, color, center, radius, 2)
        screen.blit(surf, (0, 0))

# -----------------------------
# Init
# -----------------------------
pygame.init()
clock = pygame.time.Clock()

map_img = pygame.image.load("map_cartooned.png")
W, H = map_img.get_width(), map_img.get_height()
screen = pygame.display.set_mode((W - 30, H - 20))
pygame.display.set_caption(SCREEN_TITLE)

frames = load_gif_frames("llama (2).gif", 50)
frame_idx = 0
dots = make_dots(W, H)

trail = []
TRAIL_MAX = 250
time_wave = 0
scale = 0.6
pixel_mode = False
latest_lat, latest_lon = BASE_LAT, BASE_LON
smooth_lat, smooth_lon = latest_lat, latest_lon
llama_x, llama_y = W // 2, H // 2

# -----------------------------
# Buildings
# -----------------------------
buildings = {
    "IRC": {"pos": (318, 218), "radius": 45, "rooms": ["201–210", "301–310"]},
    "RLH": {"pos": (235, 188), "radius": 45, "rooms": ["101–110", "201–220"]},
    "C3 D-block": {"pos": (662, 508), "radius": 50, "rooms": ["XD-101", "XD-320"]},
    "C3 C-block": {"pos": (628, 503), "radius": 50, "rooms": ["XC-101", "XC-320"]},
    "Main Gate": {"pos": (155, 224), "radius": 40, "rooms": ["Security", "Reception"]},
}

print(f"[INFO] Map {W}x{H} loaded, base=({BASE_LAT},{BASE_LON})")

# -----------------------------
# Main Loop
# -----------------------------
running = True
while running:
    clock.tick(20)
    time_wave += 2
    hovered = None

    # --- Events ---
    for e in pygame.event.get():
        if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
            running = False
        elif e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_PLUS, pygame.K_EQUALS): scale *= 1.1
            elif e.key in (pygame.K_MINUS, pygame.K_UNDERSCORE): scale /= 1.1
            elif e.key == pygame.K_z: pixel_mode = not pixel_mode
            scale = max(0.05, min(5.0, scale))

    # --- GPS ---
    try:
        res = requests.get(GPS_SERVER_URL, timeout=1)
        data = res.json()
        lat, lon = data.get("lat"), data.get("lon")
        if lat and lon: latest_lat, latest_lon = float(lat), float(lon)
    except Exception: pass

    # --- Smooth ---
    smooth_lat = 0.9 * smooth_lat + 0.1 * latest_lat
    smooth_lon = 0.9 * smooth_lon + 0.1 * latest_lon

    # --- Projection ---
    target_x, target_y = gps_to_pixel(smooth_lat, smooth_lon, scale, W, H)
    offset_x, offset_y = W / 2 - target_x, H / 2 - target_y

    # --- Map ---
    map_to_draw = map_img
    if pixel_mode:
        small = pygame.transform.scale(map_img, (W // 6, H // 6))
        map_to_draw = pygame.transform.scale(small, (W, H))
    screen.blit(map_to_draw, (offset_x, offset_y))
    dynamic_day_night_tint(screen, time_wave)
    draw_dotted_background(screen, dots, time_wave, (W / 2, H / 2))

    # --- Trail ---
    if not trail or math.hypot(trail[-1][0] - W / 2, trail[-1][1] - H / 2) > 2:
        trail.append((W / 2, H / 2, 1.0))
        if len(trail) > TRAIL_MAX: trail.pop(0)
    for i in range(len(trail)):
        x, y, a = trail[i]
        trail[i] = (x, y, max(0, a - 0.01))
    draw_trail(screen, trail)

    # --- Radar Pulse ---
    draw_radar(screen, (W // 2, H // 2), time_wave)

    # --- Bingo ---
    screen.blit(frames[frame_idx % len(frames)], (W // 2 - 20, H // 2 - 20))

    # --- Hover Buildings ---
    mx, my = pygame.mouse.get_pos()
    for name, b in buildings.items():
        bx, by = b["pos"]
        bx += offset_x; by += offset_y
        if math.hypot(mx - bx, my - by) < b["radius"]:
            hovered = name
            glow = 120 + 120 * math.sin(pygame.time.get_ticks() * 0.005)
            pygame.draw.circle(screen, (0, int(glow), 255), (int(bx), int(by)), b["radius"] + 6, 3)
            draw_popup(screen, name, b["rooms"], (bx, by))
            break

    draw_hud(screen, smooth_lat, smooth_lon, scale, pixel_mode)
    pygame.display.flip()
    frame_idx += 1

pygame.quit()
