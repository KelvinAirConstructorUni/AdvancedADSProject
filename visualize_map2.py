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
# Building Areas + Polygon
# -----------------------------
buildings = {
    "RLH": {"pos": (235, 188), "radius": 60, "image": "img/rlh_groundfloor.png"}
}

# RLH outline polygon (from your path editor)
RLH_POLYGON = [
    (198, 138), (196, 161), (190, 179), (190, 202), (208, 207),
    (210, 190), (224, 193), (229, 181), (253, 185), (251, 209),
    (270, 215), (279, 150), (260, 147), (256, 168),
    (215, 163), (216, 141), (200, 138)
]


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
# Routes + States
# -----------------------------
routes = {
    "RLH": {
        "front": [(615, 505), (444, 481), (434, 524), (395, 528),
                  (221, 503), (200, 485), (213, 390), (233, 238),
                  (241, 237), (244, 213), (246, 197), (231, 189)],
        "back": [(614, 505), (455, 485), (442, 481), (455, 382),
                 (467, 310), (471, 268), (398, 257), (410, 150),
                 (291, 133), (282, 188)]
    }
}

time_wave = 0
frame_idx = 0
trail = []
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
last_route = "front"

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
                last_route = "back"
                print("[ROUTE] RLH back route loaded.")
            elif e.key == pygame.K_f:
                path_points = routes["RLH"]["front"]
                last_route = "front"
                print("[ROUTE] RLH front route loaded.")

        # mouse drag
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

        # draw map
        screen.blit(map_img, manual_offset)
        dynamic_day_night_tint(screen, time_wave)

        # --- RLH Hover Highlight (Polygon Glow) ---
        mx, my = pygame.mouse.get_pos()
        map_x, map_y = mx - manual_offset[0], my - manual_offset[1]
        hover_distance = min(math.hypot(map_x - x, map_y - y) for x, y in RLH_POLYGON)

        if hover_distance < 70:
            proximity_factor = max(0.1, 1 - hover_distance / 70)
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.004))
            glow_intensity = int(150 + 100 * pulse * proximity_factor)
            glow_color = (0, glow_intensity, 255)

            # filled transparent highlight
            poly_surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            pygame.draw.polygon(poly_surface, (*glow_color, int(80 * proximity_factor)),
                                [(x + manual_offset[0], y + manual_offset[1]) for x, y in RLH_POLYGON])
            screen.blit(poly_surface, (0, 0))

            # outline
            pygame.draw.polygon(screen, glow_color,
                                [(x + manual_offset[0], y + manual_offset[1]) for x, y in RLH_POLYGON], 3)

            # label
            font = pygame.font.SysFont("PressStart2P", 10)
            text = font.render("RLH BUILDING", True, (0, 255, 255))
            screen.blit(text, (map_x + 10, map_y - 25))

            # click to enter
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                print("[INFO] Clicked inside RLH polygon.")
                scene = "rlh_floor"
                rlh_floor_img = pygame.image.load(buildings["RLH"]["image"])
                print("[SCENE] Switched to RLH Ground Floor view.")

        # radar + bingo
        draw_radar(screen, (W // 2, H // 2), time_wave)
        screen.blit(frames[frame_idx % len(frames)], (W // 2 - 20, H // 2 - 20))

    pygame.display.flip()
    frame_idx += 1

pygame.quit()
