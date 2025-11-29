import pygame, math, requests
from helper_functions.load_sprite import load_gif_frames


def heuristic(a, b):
    return math.dist(a, b)


def a_star(start, goal):
    open_set = {start}
    came_from = {}

    g = {node: float("inf") for node in graph_nodes}
    f = {node: float("inf") for node in graph_nodes}

    g[start] = 0
    f[start] = heuristic(graph_nodes[start], graph_nodes[goal])

    while open_set:
        current = min(open_set, key=lambda x: f[x])

        if current == goal:
            # reconstruct path
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path

        open_set.remove(current)

        for neighbor in graph_edges[current]:
            tentative_g = g[current] + math.dist(graph_nodes[current], graph_nodes[neighbor])
            if tentative_g < g[neighbor]:
                came_from[neighbor] = current
                g[neighbor] = tentative_g
                f[neighbor] = tentative_g + heuristic(graph_nodes[neighbor], graph_nodes[goal])
                open_set.add(neighbor)

    return None


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


def set_room_node(coordinates, label="", color=(255, 80, 80), radius=10):
    """
    Draws a room node with glow and optional label.
    `coordinates` can be a single tuple (x, y) or a list of tuples [(x, y), ...].
    Coordinates are assumed to already be in SCREEN space.
    """
    global scene, time_wave, manual_offset

    # Ensure we have a list of coordinates
    if isinstance(coordinates, tuple):
        coords_list = [coordinates]
    elif isinstance(coordinates, list):
        coords_list = coordinates
    else:
        return

    for coord in coords_list:
        if not isinstance(coord, tuple) or len(coord) != 2:
            continue

        x, y = coord

        # Apply offset only in campus scene
        if scene == "campus":
            x = int(x + manual_offset[0])
            y = int(y + manual_offset[1])
        else:
            x, y = int(x), int(y)

        # -----------------------------
        # 1. Blinking Pulse (sin wave)
        # -----------------------------
        pulse = (math.sin(time_wave * 0.15) + 1) / 2  # 0 → 1
        glow_radius = int(radius + 8 + pulse * 6)
        glow_alpha = int(80 + pulse * 100)

        glow_surface = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
        pygame.draw.circle(glow_surface, (color[0], color[1], color[2], glow_alpha), (x, y), glow_radius)
        screen.blit(glow_surface, (0, 0))

        # -----------------------------
        # 2. Solid dot
        # -----------------------------
        pygame.draw.circle(screen, color, (x, y), radius)

        # -----------------------------
        # 3. Label (text above the node)
        # -----------------------------
        if label:
            font = pygame.font.Font(None, 26)
            text_surf = font.render(label, True, (255, 255, 255))
            outline_surf = font.render(label, True, (0, 0, 0))

            # Outline
            screen.blit(outline_surf, (x - outline_surf.get_width() // 2 + 1, y - 25 + 1))
            screen.blit(outline_surf, (x - outline_surf.get_width() // 2 - 1, y - 25 - 1))

            # Text
            screen.blit(text_surf, (x - text_surf.get_width() // 2, y - 25))


# -----------------------------
# Constants
# -----------------------------
EARTH_RADIUS = 6378137
BASE_LAT = 53.1670
BASE_LON = 8.65222
SCREEN_TITLE = "Intelligent Route Planner (Llama)"
GPS_SERVER_URL = "http://127.0.0.1:8000/get"
scene = "campus"

# RLH outline polygon (from path editor)
RLH_POLYGON = [
    (198, 138), (196, 161), (190, 179), (190, 202), (208, 207),
    (210, 190), (224, 193), (229, 181), (253, 185), (251, 209),
    (270, 215), (279, 150), (260, 147), (256, 168),
    (215, 163), (216, 141), (200, 138)
]

# -----------------------------
# Buildings (Clickable)
# -----------------------------
buildings = {
    "RLH": {"pos": (235, 188), "radius": 60, "image": "img/rlh_groundfloor.png"}
}

# Hallway / passage nodes (raw map coords on floor plan)
passages = [
    (436, 356),
    (575, 352),
    (642, 354),
    (642, 473),
    (643, 563),
    (643, 616),
    (643, 315),
    (644, 215),
    (643, 177),
]

rooms = {
    "CNL Hall": {"pos": [(642, 151)]},
    "Room 134": {"pos": [(680, 615)]},
    "Room 135": {"pos": [(671, 563)]},
    "passages": {"pos": passages}  # not a room, just storing the list
}

# -----------------------------
# RLH Graph for A* Pathfinding
# -----------------------------
graph_nodes = {
    # hallway intersection nodes
    "H1": (600, 350),
    "H2": (620, 420),
    "H3": (650, 500),

    # connect rooms to hallway nodes
    "CNL Hall": rooms["CNL Hall"]["pos"][0],
    "Room 134": rooms["Room 134"]["pos"][0],
    "Room 135": rooms["Room 135"]["pos"][0],
    # you could add more if you want: e.g. each passage as its own node
}

# Edges (bidirectional, weighted by Euclidean distance)
graph_edges = {
    "H1": ["H2"],
    "H2": ["H1", "H3", "CNL Hall"],
    "H3": ["H2", "Room 134", "Room 135"],
    "CNL Hall": ["H2"],
    "Room 134": ["H3"],
    "Room 135": ["H3"],
}

selected_room = None  # which room was clicked
last_path = []  # last A* path found (list of node names)


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
# Routes for RLH (Front/Back)
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
# State Variables
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

            elif e.key == pygame.K_n:
                path_editor = not path_editor
                print(f"[MODE] Path Editor {'ON' if path_editor else 'OFF'}")

            elif e.key == pygame.K_s and path_editor:
                with open("path_nodes.txt", "w") as f:
                    for x, y in path_points:
                        f.write(f"{x},{y}\n")

                print("[INFO] Saved path_nodes.txt")

        # Mouse drag for map
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

        # Path Editor Mode
        if e.type == pygame.MOUSEBUTTONDOWN and path_editor:
            mx, my = pygame.mouse.get_pos()
            map_x, map_y = mx - manual_offset[0], my - manual_offset[1]
            if e.button == 1:
                path_points.append((map_x, map_y))
                print(f"[NODE] Added MAP ({int(map_x)}, {int(map_y)}) [screen=({mx},{my}) offset={manual_offset}]")
            elif e.button == 3 and path_points:
                removed = path_points.pop()
                print(f"[NODE] Removed {removed}")

        # Building click detection
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and not path_editor:
            mx, my = pygame.mouse.get_pos()
            map_x, map_y = mx - manual_offset[0], my - manual_offset[1]
            for name, b in buildings.items():
                bx, by = b["pos"]
                if math.hypot(map_x - bx, map_y - by) < b["radius"]:
                    print(f"[INFO] Clicked on {name}")
                    if name == "RLH":
                        scene = "rlh_floor"
                        rlh_floor_img = pygame.image.load(b["image"])
                        print("[SCENE] Switched to RLH Ground Floor view.")

        # GPS simulation
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
        bingo_x, bingo_y = target_x + offset_x, target_y + offset_y

        # Draw campus map
        map_to_draw = map_img
        if pixel_mode:
            small = pygame.transform.scale(map_img, (W // 6, H // 6))
            map_to_draw = pygame.transform.scale(small, (W, H))
        screen.blit(map_to_draw, (offset_x, offset_y))
        dynamic_day_night_tint(screen, time_wave)

        # RLH Hover Highlight
        mx, my = pygame.mouse.get_pos()
        map_x, map_y = mx - manual_offset[0], my - manual_offset[1]
        hover_distance = min(math.hypot(map_x - x, map_y - y) for x, y in RLH_POLYGON)

        if hover_distance < 80:  # hover range
            proximity_factor = max(0.1, 1 - hover_distance / 80)
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.004))
            breathe = 1 + 0.04 * math.sin(pygame.time.get_ticks() * 0.003)
            glow_intensity = int(160 + 80 * pulse * proximity_factor)
            glow_color = (0, glow_intensity, 255)

            cx = sum(x for x, _ in RLH_POLYGON) / len(RLH_POLYGON)
            cy = sum(y for _, y in RLH_POLYGON) / len(RLH_POLYGON)
            scaled_poly = [
                (
                    (x - cx) * breathe + cx + manual_offset[0],
                    (y - cy) * breathe + cy + manual_offset[1],
                )
                for x, y in RLH_POLYGON
            ]

            poly_surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            pygame.draw.polygon(poly_surface, (*glow_color, int(90 * proximity_factor)), scaled_poly)
            screen.blit(poly_surface, (0, 0))

            pygame.draw.polygon(screen, glow_color, scaled_poly, 3)

            font = pygame.font.SysFont("PressStart2P", 10)
            text = font.render("RLH BUILDING", True, (0, 255, 255))
            screen.blit(text, (map_x + 10, map_y - 25))

            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                print("[INFO] Clicked inside RLH polygon.")
                scene = "rlh_floor"
                rlh_floor_img = pygame.image.load(buildings["RLH"]["image"])
                print("[SCENE] Switched to RLH Ground Floor view.")

        # Path visualization (campus routes)
        if path_points:
            for i, (x, y) in enumerate(path_points):
                sx, sy = int(x + offset_x), int(y + offset_y)
                pygame.draw.circle(screen, (0, 255, 0), (sx, sy), 6)
                if i > 0:
                    px, py = path_points[i - 1]
                    pygame.draw.line(screen, (255, 255, 0),
                                     (int(px + offset_x), int(py + offset_y)), (sx, sy), 2)

        # Bingo + radar
        draw_radar(screen, (int(bingo_x), int(bingo_y)), time_wave)
        screen.blit(frames[frame_idx % len(frames)], (bingo_x - 20, bingo_y - 20))
        set_cursor("grab" if (dragging_map or path_editor) else "arrow")

    # -----------------------------
    # RLH Floor Plan Scene (Fit-to-Screen + A* Path)
    # -----------------------------
    elif scene == "rlh_floor":
        win_w, win_h = screen.get_size()
        orig_w, orig_h = rlh_floor_img.get_size()
        scale_floor = max(win_w / orig_w, win_h / orig_h)

        scaled_floor = pygame.transform.smoothscale(
            rlh_floor_img, (int(orig_w * scale_floor), int(orig_h * scale_floor))
        )
        pos_x = (win_w - scaled_floor.get_width()) // 2
        pos_y = (win_h - scaled_floor.get_height()) // 2

        # 1) Draw floor background
        screen.fill((245, 245, 245))
        screen.blit(scaled_floor, (pos_x, pos_y))

        mx, my = pygame.mouse.get_pos()

        # 2) Handle click on rooms (scaled hitboxes)
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for room_name, data in rooms.items():
                if room_name == "passages":
                    continue

                rx_raw, ry_raw = data["pos"][0]
                rx = int(rx_raw * scale_floor + pos_x)
                ry = int(ry_raw * scale_floor + pos_y)
                radius = 12

                if math.hypot(mx - rx, my - ry) <= radius:
                    selected_room = room_name
                    print(f"[ROOM] Selected: {room_name}")

                    # A* from H1 to the selected room
                    start_node = "H1"
                    goal_node = room_name
                    last_path = a_star(start_node, goal_node)
                    print("[PATH]", last_path)

        # 3) Draw A* path (if exists), scaled to screen
        if last_path:
            for i in range(len(last_path) - 1):
                p1 = graph_nodes[last_path[i]]
                p2 = graph_nodes[last_path[i + 1]]

                x1 = int(p1[0] * scale_floor + pos_x)
                y1 = int(p1[1] * scale_floor + pos_y)
                x2 = int(p2[0] * scale_floor + pos_x)
                y2 = int(p2[1] * scale_floor + pos_y)

                pygame.draw.line(screen, (255, 240, 0), (x1, y1), (x2, y2), 6)

        # 3) passages
        for px_raw, py_raw in passages:
            px = int(px_raw * scale_floor + pos_x)
            py = int(py_raw * scale_floor + pos_y)
            pygame.draw.circle(screen, (0, 150, 200), (px, py), 5)


        # 4) room nodes (ONLY DRAW ONCE PER ROOM)
        for room_name, data in rooms.items():
            if room_name == "passages":
                continue  # skip passages, they use small blue dots

            pos = pygame.mouse.get_pos()
            print(pos)

            rx_raw, ry_raw = data["pos"][0]
            rx = int(rx_raw )
            ry = int(ry_raw )

            # highlight selected room
            if room_name == selected_room:
                set_room_node((rx, ry), label=room_name, color=(255, 230, 50), radius=10)
            else:
                set_room_node((rx, ry), label=room_name, color=(0, 200, 130), radius=7)

        # 6) Draw Bingo radar (center or back door)
        if last_route == "front":
            bx, by = win_w // 2, win_h // 2
            draw_radar(screen, (bx, by), time_wave)
            screen.blit(frames[frame_idx % len(frames)], (bx - 20, by - 20))

        elif last_route == "back":
            bx, by = 645, 348  # these are screen coords already
            draw_radar(screen, (bx, by), time_wave)
            screen.blit(frames[frame_idx % len(frames)], (bx - 20, by - 20))

        # 7) UI text
        font = pygame.font.SysFont("PressStart2P", 12)
        screen.blit(font.render("← BACK TO CAMPUS (ESC)", True, (0, 0, 0)), (20, 20))
        screen.blit(font.render(f"RLH Scale Fit: {scale_floor:.2f}", True, (80, 80, 80)), (20, 45))

    pygame.display.flip()
    frame_idx += 1

pygame.quit()
