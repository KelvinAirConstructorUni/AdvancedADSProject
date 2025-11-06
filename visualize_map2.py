import pygame, math, requests
from helper_functions.load_sprite import load_gif_frames

# -----------------------------
# Cursor Helper
# -----------------------------
def set_cursor(state):
    if state == "hand":
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
    elif state == "grab":
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZEALL)
    else:
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

# -----------------------------
# Constants
# -----------------------------
EARTH_RADIUS = 6378137
BASE_LAT = 53.1665
BASE_LON = 8.652
SCREEN_TITLE = "Intelligent Route Planner (Llama)"
GPS_SERVER_URL = "http://127.0.0.1:8000/get"
scene = "campus"

# -----------------------------
# Coordinate Conversion
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
# Visual Helpers
# -----------------------------
def apply_map_tint(screen, color, mode="add"):
    surf = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    surf.fill(color)
    flag = pygame.BLEND_RGBA_ADD if mode == "add" else pygame.BLEND_RGBA_MULT
    screen.blit(surf, (0, 0), special_flags=flag)

def dynamic_day_night_tint(screen, t):
    morning, evening, night = (120, 0, 0), (120, 150, 40), (40, 80, 30)
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

def draw_trail(screen, trail):
    for i, (x, y, a) in enumerate(trail):
        t = i / len(trail) if len(trail) > 1 else 0
        if t < 0.25:
            r, g, b = 255, int(255 * (t / 0.25)), 0
        elif t < 0.5:
            r, g, b = int(255 * (1 - (t - 0.25) / 0.25)), 255, 0
        elif t < 0.75:
            r, g, b = 0, 255, int(255 * ((t - 0.5) / 0.25))
        else:
            r, g, b = 0, int(255 * (1 - (t - 0.75) / 0.25)), 255
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.005 + i * 0.2)
        fade = a * pulse
        col = (int(r * fade), int(g * fade), int(b * fade))
        pygame.draw.circle(screen, col, (int(x), int(y)), int(5 * fade) + 2)

# -----------------------------
# Init
# -----------------------------
pygame.init()
clock = pygame.time.Clock()
map_img = pygame.image.load("img/map_cartooned.png")
frames = load_gif_frames("img/llama (2).gif", 50)
W, H = map_img.get_width(), map_img.get_height()
screen = pygame.display.set_mode((W - 30, H - 20))
pygame.display.set_caption(SCREEN_TITLE)

# -----------------------------
# States
# -----------------------------
time_wave = 0
frame_idx = 0
trail = []
TRAIL_MAX = 250
scale = 0.6
pixel_mode = False
latest_lat, latest_lon = BASE_LAT, BASE_LON
smooth_lat, smooth_lon = latest_lat, latest_lon
dragging_map = False
follow_gps = True
manual_offset = [0, 0]
map_drag_start = (0, 0)
map_orig_offset = (0, 0)

# Initial Bingo position (center map)
bingo_pos = [W // 2, H // 2]

# Path nodes + walking state
path_nodes = []
walking = False
path_index = 0
bingo_speed = 2.0

# -----------------------------
# Main Loop
# -----------------------------
running = True
while running:
    clock.tick(24)
    time_wave += 2
    e = pygame.event.poll()
    if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
        running = False

    # --- Controls ---
    if e.type == pygame.KEYDOWN:
        if e.key == pygame.K_p and path_nodes:
            walking = not walking
            if walking:
                path_index = 0
                bingo_pos = list(path_nodes[0])  # ✅ start at first node
                print(f"[PATH] Bingo starting at {bingo_pos}")
            print(f"[PATH] Walking {'ON' if walking else 'OFF'}")
        elif e.key == pygame.K_c:
            follow_gps = True
            manual_offset = [0, 0]
        elif e.key in (pygame.K_PLUS, pygame.K_EQUALS):
            scale *= 1.1
        elif e.key in (pygame.K_MINUS, pygame.K_UNDERSCORE):
            scale /= 1.1
        elif e.key == pygame.K_z:
            pixel_mode = not pixel_mode
        elif e.key == pygame.K_s and path_nodes:
            with open("path_nodes.txt", "w") as f:
                for x, y in path_nodes:
                    f.write(f"{x},{y}\n")
            print("[INFO] Saved path_nodes.txt")

    # --- Dragging ---
    if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
        dragging_map = True
        map_drag_start = pygame.mouse.get_pos()
        map_orig_offset = tuple(manual_offset)
        follow_gps = False
    elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
        dragging_map = False
    elif e.type == pygame.MOUSEMOTION and dragging_map:
        mx, my = pygame.mouse.get_pos()
        dx, dy = mx - map_drag_start[0], my - map_drag_start[1]
        manual_offset = [map_orig_offset[0] + dx, map_orig_offset[1] + dy]

    # --- Add or Remove Path Points (glued to map) ---
    if e.type == pygame.MOUSEBUTTONDOWN:
        if e.button == 1:  # left-click to add node
            mx, my = pygame.mouse.get_pos()
            map_x, map_y = mx - manual_offset[0], my - manual_offset[1]
            path_nodes.append((int(map_x), int(map_y)))
            print(f"[NODE] Added glued point ({int(map_x)}, {int(map_y)})")
        elif e.button == 3 and path_nodes:
            removed = path_nodes.pop()
            print(f"[NODE] Removed {removed}")

    # --- GPS Update (optional) ---
    try:
        res = requests.get(GPS_SERVER_URL, timeout=1)
        data = res.json()
        lat, lon = data.get("lat"), data.get("lon")
        if lat and lon:
            latest_lat, latest_lon = float(lat), float(lon)
    except Exception:
        pass

    smooth_lat = 0.9 * smooth_lat + 0.1 * latest_lat
    smooth_lon = 0.9 * smooth_lon + 0.1 * latest_lon
    target_x, target_y = gps_to_pixel(smooth_lat, smooth_lon, scale, W, H)

    if follow_gps:
        offset_x = W / 2 - target_x
        offset_y = H / 2 - target_y
        manual_offset = [offset_x, offset_y]
    else:
        offset_x, offset_y = manual_offset

    # --- Path Walking ---
    if walking and path_index < len(path_nodes) - 1:
        tx, ty = path_nodes[path_index + 1]
        dx, dy = tx - bingo_pos[0], ty - bingo_pos[1]
        dist = math.hypot(dx, dy)
        if dist < bingo_speed:
            path_index += 1
        else:
            bingo_pos[0] += (dx / dist) * bingo_speed
            bingo_pos[1] += (dy / dist) * bingo_speed
    elif walking and path_index >= len(path_nodes) - 1:
        walking = False
        print("[PATH] Arrived at destination.")

    # --- Draw Map ---
    map_to_draw = map_img
    if pixel_mode:
        small = pygame.transform.scale(map_img, (W // 6, H // 6))
        map_to_draw = pygame.transform.scale(small, (W, H))
    screen.blit(map_to_draw, (offset_x, offset_y))
    dynamic_day_night_tint(screen, time_wave)

    # --- Draw Path (glued) ---
    for i, (x, y) in enumerate(path_nodes):
        pygame.draw.circle(screen, (0, 255, 0), (int(x + offset_x), int(y + offset_y)), 5)
        if i > 0:
            px, py = path_nodes[i - 1]
            pygame.draw.line(screen, (255, 255, 0),
                             (int(px + offset_x), int(py + offset_y)),
                             (int(x + offset_x), int(y + offset_y)), 2)

    # --- Start & End markers ---
    if path_nodes:
        sx, sy = path_nodes[0]
        ex, ey = path_nodes[-1]
        pygame.draw.circle(screen, (0, 255, 0), (int(sx + offset_x), int(sy + offset_y)), 10, 3)
        pygame.draw.circle(screen, (255, 0, 0), (int(ex + offset_x), int(ey + offset_y)), 10, 3)

    # --- Draw Bingo + Radar ---
    bx, by = bingo_pos[0] + offset_x, bingo_pos[1] + offset_y
    if not trail or math.hypot(trail[-1][0] - bx, trail[-1][1] - by) > 2:
        trail.append((bx, by, 1.0))
        if len(trail) > TRAIL_MAX:
            trail.pop(0)
    for i in range(len(trail)):
        x, y, a = trail[i]
        trail[i] = (x, y, max(0, a - 0.01))
    draw_trail(screen, trail)

    # Radar (above tint)
    for i in range(3):
        radius = 40 + i * 25 + (time_wave % 50)
        alpha = max(0, 180 - (radius - 40) * 3)
        radar_surf = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        pygame.draw.circle(radar_surf, (0, 255, 200, alpha), (int(bx), int(by)), radius, 2)
        screen.blit(radar_surf, (0, 0))

    # Draw Bingo sprite LAST
    if frames:
        frame = frames[frame_idx % len(frames)].copy()
        frame.set_alpha(255)
        screen.blit(frame, (bx - 20, by - 20))

    # --- Debug Overlay ---
    font_dbg = pygame.font.SysFont("Menlo", 15)
    dbg_lines = [
        f"Offset: ({int(offset_x)}, {int(offset_y)})",
        f"Bingo map: ({int(bingo_pos[0])}, {int(bingo_pos[1])})",
        f"Nodes: {len(path_nodes)} | Index: {path_index + 1 if path_nodes else 0}",
    ]
    for i, line in enumerate(dbg_lines):
        screen.blit(font_dbg.render(line, True, (255, 255, 255)), (8, 8 + i * 18))

    set_cursor("grab" if dragging_map else "arrow")
    pygame.display.flip()
    frame_idx += 1

pygame.quit()
