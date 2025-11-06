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
# Building Areas (for clicking)
# -----------------------------
buildings = {
    "RLH": {"pos": (235, 188), "radius": 60, "image": "img/rlh_groundfloor.png"}
}


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
# Visuals
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


def draw_radar(screen, center, t):
    for i in range(3):
        r = 40 + i * 25 + (t % 50)
        a = max(0, 150 - (r - 40) * 3)
        s = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        pygame.draw.circle(s, (0, 255, 200, a), center, r, 2)
        screen.blit(s, (0, 0))


# -----------------------------
# Init
# -----------------------------
pygame.init()
clock = pygame.time.Clock()
map_img = pygame.image.load("img/map_cartooned.png")
W, H = map_img.get_width(), map_img.get_height()
screen = pygame.display.set_mode((W - 30, H - 20))
pygame.display.set_caption(SCREEN_TITLE)
frames = load_gif_frames("img/llama (2).gif", 50)

# -----------------------------
# Predefined Navigation Routes
# -----------------------------
routes = {
    "RLH": {
        "front": [
            (615, 505), (444, 481), (434, 524), (395, 528),
            (221, 503), (200, 485), (213, 390), (233, 238),
            (241, 237), (244, 213), (246, 197), (231, 189)
        ],
        "back": [
            (614, 505), (455, 485), (442, 481), (455, 382),
            (467, 310), (471, 268), (398, 257), (410, 150),
            (291, 133), (282, 188)
        ]
    }
}

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
path_points = []
path_editor = False

# -----------------------------
# Main Loop
# -----------------------------
running = True
while running:
    clock.tick(24)
    time_wave += 2
    e = pygame.event.poll()
    if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
        if scene == "rlh_floor":
            scene = "campus"
            print("[SCENE] Returned to campus map.")
        else:
            running = False

    # -----------------------------
    # Campus Scene
    # -----------------------------
    if scene == "campus":
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_z:
                pixel_mode = not pixel_mode
            elif e.key in (pygame.K_PLUS, pygame.K_EQUALS):
                scale *= 1.1
            elif e.key in (pygame.K_MINUS, pygame.K_UNDERSCORE):
                scale /= 1.1
            elif e.key == pygame.K_b:
                path_points = routes["RLH"]["back"]
                print("[ROUTE] RLH back route loaded.")
            elif e.key == pygame.K_f:
                path_points = routes["RLH"]["front"]
                print("[ROUTE] RLH front route loaded.")
            elif e.key == pygame.K_n:
                path_editor = not path_editor
                print(f"[MODE] Path Editor {'ON' if path_editor else 'OFF'}")
            elif e.key == pygame.K_s and path_editor:
                with open("path_nodes.txt", "w") as f:
                    for x, y in path_points:
                        f.write(f"{x},{y}\n")
                print("[INFO] Saved path_nodes.txt")

        # dragging map
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and not path_editor:
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

        # path editor mouse
        if e.type == pygame.MOUSEBUTTONDOWN and path_editor:
            if e.button == 1:
                mx, my = pygame.mouse.get_pos()
                map_x, map_y = mx - manual_offset[0], my - manual_offset[1]
                path_points.append((map_x, map_y))
                print(f"[NODE] Added MAP ({int(map_x)},{int(map_y)})")
            elif e.button == 3 and path_points:
                removed = path_points.pop()
                print(f"[NODE] Removed {removed}")

        # gps
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
        offset_x, offset_y = manual_offset
        bingo_x = target_x + offset_x
        bingo_y = target_y + offset_y

        # --- Building click detection ---
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and not path_editor:
            mx, my = pygame.mouse.get_pos()
            map_x = mx - offset_x
            map_y = my - offset_y
            for name, b in buildings.items():
                bx, by = b["pos"]
                if math.hypot(map_x - bx, map_y - by) < b["radius"]:
                    print(f"[INFO] Clicked on {name} building.")
                    if name == "RLH":
                        scene = "rlh_floor"
                        rlh_floor_img = pygame.image.load(b["image"])
                        print("[SCENE] Switched to RLH Ground Floor view.")

        # draw map
        map_to_draw = map_img
        if pixel_mode:
            small = pygame.transform.scale(map_img, (W // 6, H // 6))
            map_to_draw = pygame.transform.scale(small, (W, H))
        screen.blit(map_to_draw, (offset_x, offset_y))
        dynamic_day_night_tint(screen, time_wave)

        # draw route
        for i, (x, y) in enumerate(path_points):
            sx, sy = int(x + offset_x), int(y + offset_y)
            pygame.draw.circle(screen, (0, 255, 0), (sx, sy), 6)
            if i > 0:
                px, py = path_points[i - 1]
                pygame.draw.line(screen, (255, 255, 0),
                                 (int(px + offset_x), int(py + offset_y)), (sx, sy), 2)

        # radar + bingo
        draw_radar(screen, (int(bingo_x), int(bingo_y)), time_wave)
        screen.blit(frames[frame_idx % len(frames)], (bingo_x - 20, bingo_y - 20))
        set_cursor("grab" if (dragging_map or path_editor) else "arrow")

    # -----------------------------
    # RLH Ground Floor Scene
    # -----------------------------
    # -----------------------------
    # RLH Ground Floor Scene (Zoomable)
    # -----------------------------
    # -----------------------------
    # RLH Ground Floor Scene (Zoomable + Bingo)
    # -----------------------------
    # -----------------------------
    # RLH Ground Floor Scene (Zoomable + Auto-Entrance + Bingo)
    # -----------------------------
    elif scene == "rlh_floor":
        # static zoom + spawn tracking
        if "scale_floor" not in locals():
            scale_floor = 1.0
            # Determine which entrance based on last route key
            floor_entry = last_route if 'last_route' in locals() else "front"
            if floor_entry == "front":
                floor_spawn = (300, 480)  # near bottom of map
            else:
                floor_spawn = (300, 120)  # near top of map
            floor_bingo_pos = list(floor_spawn)
            print(f"[RLH] Bingo entered via {floor_entry} entrance.")

        # Zoom control
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_PLUS, pygame.K_EQUALS):
                scale_floor *= 1.1
            elif e.key in (pygame.K_MINUS, pygame.K_UNDERSCORE):
                scale_floor /= 1.1
            elif e.key == pygame.K_b:
                path_points = routes["RLH"]["back"]
                last_route = "back"
                print("[ROUTE] RLH back route loaded.")
            elif e.key == pygame.K_f:
                path_points = routes["RLH"]["front"]
                last_route = "front"
                print("[ROUTE] RLH front route loaded.")

            scale_floor = max(0.29, min(3.0, scale_floor))
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            scene = "campus"
            print("[SCENE] Returned to campus map.")

        # Prepare zoomed image
        orig_w, orig_h = rlh_floor_img.get_size()
        new_w, new_h = int(orig_w * scale_floor), int(orig_h * scale_floor)
        scaled_floor = pygame.transform.smoothscale(rlh_floor_img, (new_w, new_h))

        screen.fill((245, 245, 245))  # whitesmoke background
        pos_x = (screen.get_width() - new_w) // 2
        pos_y = (screen.get_height() - new_h) // 2
        screen.blit(scaled_floor, (pos_x, pos_y))

        # Draw Bingo inside the hall
        bx = int(pos_x + floor_bingo_pos[0] * scale_floor)
        by = int(pos_y + floor_bingo_pos[1] * scale_floor)
        draw_radar(screen, (bx, by), time_wave)
        screen.blit(frames[frame_idx % len(frames)], (bx - 20, by - 20))

        # HUD
        font = pygame.font.SysFont("PressStart2P", 12)
        screen.blit(font.render("← BACK TO CAMPUS (ESC)", True, (0, 0, 0)), (20, 20))
        screen.blit(font.render(f"Zoom: {scale_floor:.2f}x (+/-)", True, (60, 60, 60)), (20, 45))
        screen.blit(font.render(f"Bingo entered from: {floor_entry.upper()}", True, (0, 100, 200)), (20, 70))

    pygame.display.flip()
    frame_idx += 1

pygame.quit()
