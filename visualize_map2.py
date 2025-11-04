# intelligent_route_planner_wifi_sim.py
# Wi-Fi Fingerprinting SIM integrated with your Pygame campus app
# Features:
#  - Click building -> Enter indoor mode
#  - Virtual APs + RSSI simulation (path-loss + noise)
#  - Auto-generated fingerprint DB (grid)
#  - kNN matching to estimate position
#  - Click inside indoor map to set "real" (ground-truth) pos
#  - Visualize true pos (green), estimated pos (magenta), APs, uncertainty circle
#
# NOTE: adjust resource filenames (map_cartooned.png, map_interior.png, llama gif) if needed.

import pygame, math, random, requests, time
from load_sprite import load_gif_frames

# -----------------------------
# Config / Constants
# -----------------------------
GPS_SERVER_URL = "http://127.0.0.1:8000/get"  # still used for campus, optional
MAP_FILE = "map_cartooned.png"                # campus map (keeps same size)
INTERIOR_FILE = "irc_interior.png"            # interior floor plan (use a small PNG)
LLAMA_GIF = "llama (2).gif"

# Wi-Fi sim params
TX_DBM = -30         # tx power at 1m
PATH_LOSS_EXP = 2.2  # indoor path loss exponent (2-3 typical)
RSSI_NOISE_SD = 2.5  # dBm noise
KNN_K = 3            # number of neighbors for kNN

# fingerprint grid spacing (pixels) inside interior map
FINGERPRINT_SPACING = 40

# Visuals
AP_COLOR = (255, 200, 0)
TRUE_COLOR = (0, 255, 100)
EST_COLOR = (255, 0, 255)
UNCERT_COLOR = (255, 255, 0)

# -----------------------------
# Utilities: RSSI model + kNN
# -----------------------------
def rssi_from_distance_m(d_meters):
    # d meters -> rssi dBm using log-distance path loss
    if d_meters < 1.0:
        d_meters = 1.0
    mean = TX_DBM - 10 * PATH_LOSS_EXP * math.log10(d_meters)
    return mean + random.gauss(0, RSSI_NOISE_SD)

def pixel_dist(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])

def compute_rssi_vector(pos_px, ap_list):
    """Return dict {ap_id: rssi} for pos (pixels). ap_list entries: dict with 'pos',(x,y) and 'id'."""
    vec = {}
    for ap in ap_list:
        dist_px = pixel_dist(pos_px, ap['pos'])
        # we need approximate real-world meters -> assume interior scale (1 pixel ~ 0.05 m default)
        # But we don't need true meters; distance ratio works. We'll treat 1 px = 0.05m (20 px = 1m).
        px_to_m = 1.0 / 20.0
        d_m = max(0.5, dist_px * px_to_m)
        vec[ap['id']] = rssi_from_distance_m(d_m)
    return vec

def vector_distance(obs, ref):
    """Euclidean distance between two RSSI dictionaries (missing keys handled)."""
    keys = set(obs.keys()) | set(ref.keys())
    s = 0.0
    for k in keys:
        o = obs.get(k, -100.0)
        r = ref.get(k, -100.0)
        s += (o - r) ** 2
    return math.sqrt(s)

def knn_locate(obs, fingerprint_db, k=KNN_K):
    """Return weighted centroid location from top-k matches."""
    dists = []
    for entry in fingerprint_db:
        d = vector_distance(obs, entry['rssi'])
        dists.append((d, entry['pos']))
    dists.sort(key=lambda x: x[0])
    top = dists[:max(1, k)]
    # weighted by 1/(dist+eps)
    numx = numy = den = 0.0
    for d, (x,y) in top:
        w = 1.0 / (d + 1e-4)
        numx += x * w; numy += y * w; den += w
    if den == 0:
        return None
    return (numx/den, numy/den), (top[0][0] if top else 0.0)

# -----------------------------
# Build fingerprint DB for a given interior box
# -----------------------------
def build_fingerprint_db(map_w, map_h, ap_list, spacing=FINGERPRINT_SPACING):
    db = []
    # create grid points inside interior image
    for y in range(spacing//2, map_h - spacing//2, spacing):
        for x in range(spacing//2, map_w - spacing//2, spacing):
            rssi = compute_rssi_vector((x,y), ap_list)
            # optionally average multiple samples to simulate survey
            db.append({"pos": (x,y), "rssi": rssi})
    return db

# -----------------------------
# Pygame / Scenes
# -----------------------------
pygame.init()
clock = pygame.time.Clock()

# load campus map - keep same size as before (user asked not to change)
campus_img = pygame.image.load(MAP_FILE)
W, H = campus_img.get_width(), campus_img.get_height()
screen = pygame.display.set_mode((W + 20, H + 140))
pygame.display.set_caption("Intelligent Route Planner (WiFi SIM)")

# load an interior image for the building (if not found, we will use a blank surface)
try:
    interior_img = pygame.image.load(INTERIOR_FILE).convert_alpha()
except Exception:
    interior_img = pygame.Surface((600, 400))
    interior_img.fill((30,30,40))
    # simple placeholder layout
    pygame.draw.rect(interior_img, (50,50,80), (20,20,560,360), 2)

# llama frames
frames = load_gif_frames(LLAMA_GIF, 40)
frame_idx = 0

# Buildings (same as your earlier structure)
buildings = {
    "IRC": {"pos": (318, 218), "radius": 45, "rooms": ["201–210", "301–310"], "interior": interior_img},
    "RLH": {"pos": (235, 188), "radius": 45, "rooms": ["101–110", "201–220"], "interior": interior_img},
    "C3 D-block": {"pos": (662, 508), "radius": 50, "rooms": ["401–410", "Lab 1–3"], "interior": interior_img},
    "Main Gate": {"pos": (155, 224), "radius": 40, "rooms": ["Security", "Reception"], "interior": interior_img},
}

# initial state
scene = "campus"        # or "building"
current_building = None
hovered = None

# Indoor simulation state (per-building)
indoor = {
    # will be filled: 'ap_list', 'fingerprint_db', 'map' (surface), 'w','h', 'true_pos', 'est_pos'
}

# auto-generate APs per interior when entering
def gen_virtual_aps(map_w, map_h, n=4):
    aps = []
    for i in range(n):
        x = random.randint(int(map_w*0.15), int(map_w*0.85))
        y = random.randint(int(map_h*0.15), int(map_h*0.85))
        aps.append({"id": f"AP{i+1}", "pos": (x,y)})
    return aps

# HUD helper
font = pygame.font.SysFont("Menlo", 16)
def draw_text(surf, text, x,y, c=(255,255,255)):
    surf.blit(font.render(text, True, c), (x,y))

# -----------------------------
# Main Loop
# -----------------------------
running = True
while running:
    dt = clock.tick(30) / 1000.0
    mx, my = pygame.mouse.get_pos()
    hovered = None

    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            running = False
        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                running = False
            elif ev.key == pygame.K_b:
                # back to campus
                scene = "campus"
                current_building = None
        elif ev.type == pygame.MOUSEBUTTONDOWN:
            if scene == "campus":
                # check building click
                for name,b in buildings.items():
                    bx,by = b['pos']
                    if math.hypot(mx-bx, my-by) < b['radius']:
                        # enter building
                        scene = "building"
                        current_building = name
                        # prepare indoor sim state
                        surf = b['interior']
                        iw, ih = surf.get_width(), surf.get_height()
                        aps = gen_virtual_aps(iw, ih, n=4)
                        db = build_fingerprint_db(iw, ih, aps, spacing=FINGERPRINT_SPACING)
                        indoor = {
                            "map": surf,
                            "w": iw, "h": ih,
                            "ap_list": aps,
                            "fingerprint_db": db,
                            "true_pos": (iw//2, ih//2),
                            "est_pos": (iw//2, ih//2),
                            "last_obs": None
                        }
                        print(f"[SIM] Entered {name}: {len(aps)} APs, fingerprint samples={len(db)}")
                        break
            elif scene == "building":
                # set true position inside interior (relative coordinates)
                bx, by = buildings[current_building]['pos']  # not needed here
                # transform click coordinates from global screen to interior local
                # interior is drawn centered in the screen area below campus; we'll draw it at (20, H+20)
                interior_x = mx - 20
                interior_y = my - (H + 20)
                if 0 <= interior_x < indoor['w'] and 0 <= interior_y < indoor['h']:
                    indoor['true_pos'] = (int(interior_x), int(interior_y))
                    print(f"[SIM] true_pos set -> {indoor['true_pos']}")

    # --- Rendering ---
    screen.fill((18,18,20))

    if scene == "campus":
        # draw campus map at top-left (preserves original size)
        screen.blit(campus_img, (10,10))

        # buildings
        for name,b in buildings.items():
            bx,by = b['pos']
            pygame.draw.circle(screen, (0,200,170), (bx,by), 6)
            pygame.draw.circle(screen, (0,200,170), (bx,by), b['radius'], 1)
            # hover detection
            if math.hypot(mx-bx, my-by) < b['radius']:
                hovered = name
                pygame.draw.circle(screen, (0,255,255), (bx,by), b['radius']+6, 2)
                # popup quick text
                draw_text(screen, f"Click to enter {name}", bx+12, by-6, (255,255,255))

        # draw llama centered on campus (just decorative)
        screen.blit(frames[frame_idx % len(frames)], (W//2 - 20, H//2 - 20))

        draw_text(screen, "Campus view - click a building to enter (B to return)", 10, H+20)

    elif scene == "building":
        # draw the interior map in the bottom portion of window (placed at x=20,y=H+20)
        ix, iy = 20, H + 20
        screen.fill((20,20,30), (ix-2, iy-2, indoor['w']+4, indoor['h']+4))
        screen.blit(indoor['map'], (ix, iy))

        # draw APs (local coordinates -> screen coords)
        for ap in indoor['ap_list']:
            ax, ay = ap['pos']
            sx, sy = ix + ax, iy + ay
            pygame.draw.circle(screen, AP_COLOR, (sx, sy), 6)
            draw_text(screen, ap['id'], sx+8, sy-6, (220,200,0))

        # compute observed RSSI vector at the true_pos (simulated measurement)
        true_px = indoor['true_pos']
        # convert to screen coords for drawing
        true_screen = (ix + true_px[0], iy + true_px[1])
        observed = compute_rssi_vector(true_px, indoor['ap_list'])
        indoor['last_obs'] = observed

        # kNN estimate based on fingerprint_db
        est, best_dist = knn_locate(observed, indoor['fingerprint_db'], k=KNN_K)
        if est is not None:
            indoor['est_pos'] = est

        est_screen = (ix + int(indoor['est_pos'][0]), iy + int(indoor['est_pos'][1]))

        # Draw true pos (green) and estimated pos (magenta)
        pygame.draw.circle(screen, TRUE_COLOR, true_screen, 6)
        pygame.draw.circle(screen, EST_COLOR, est_screen, 6)
        # uncertainty circle (radius ~ proportional to best_dist)
        unc_px = int(max(8, min(150, best_dist * 8 if best_dist else 12)))
        s = pygame.Surface((unc_px*2, unc_px*2), pygame.SRCALPHA)
        pygame.draw.circle(s, (255,255,0,45), (unc_px, unc_px), unc_px)
        screen.blit(s, (est_screen[0]-unc_px, est_screen[1]-unc_px))

        # draw fingerprint sample points faintly
        for entry in indoor['fingerprint_db']:
            ex, ey = entry['pos']
            screen.set_at((ix+ex, iy+ey), (30,30,40))

        # display RSSI values for each AP near it
        y0 = iy + indoor['h'] + 6
        draw_text(screen, f"Building: {current_building}  (click interior to set true pos)  |  Press B to go back", 10, y0)
        y0 += 20
        for ap in indoor['ap_list']:
            r = observed.get(ap['id'], -100.0)
            draw_text(screen, f"{ap['id']}: {r:.1f} dBm", 10, y0)
            y0 += 18

        # small legend
        draw_text(screen, "Green = true pos (click inside). Magenta = kNN estimate. Yellow = uncertainty.", 10, y0+6)

    # flip / frame
    pygame.display.flip()
    frame_idx += 1

pygame.quit()
