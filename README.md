Intelligent Route Planner (Llama)

Overview

This is a Pygame-based campus navigation visualizer that can follow live GPS from your phone and lets you explore buildings with interactive visuals and pathfinding.

What’s inside

- Campus map with a live “bingo” marker (llama sprite) and radar sweep
- Live GPS stream via a tiny Flask server
- Dynamic day/night tint effect on the map
- Clickable RLH building that opens an indoor floor plan
- A* pathfinding on the RLH ground floor (to rooms like “CNL Hall”, “Room 134/135”)
- Advanced A* heuristic (ALT landmarks) — toggle at runtime to compare heuristics
- Path editor mode for quickly sketching/saving route nodes
- Coordinate picker helper for measuring map points

Repository layout

- visualize_map.py — main Pygame app (campus + RLH floor scenes)
- helper_functions/gps_server.py — Flask + CORS server that receives phone GPS and exposes `/get` and `/api/gps`
- helper_functions/load_sprite.py — GIF loader for the llama sprite
- helper_functions/map.py — simple helper to print pixel coordinates when you click the map
- index.html — minimal page to run on your phone to stream GPS to the server
- web/ — browser viewer (Leaflet) that shows live GPS from the server
- img/ — images, floor plans, and gif assets

Prerequisites

- Python 3.9+ (3.10+ recommended)
- pip

Install dependencies

Run these in your project environment:

```
pip install pygame flask flask-cors pillow requests
```

Quick start

1) Start the GPS server on your laptop/PC

```
python helper_functions\gps_server.py
```

This starts Flask on port 8000 and prints updates when GPS arrives.

2) Configure and open index.html on your phone (sender)

- Edit `index.html`, line with `SERVER_URL` to point to your laptop’s IP, for example:
  `http://192.168.1.50:8000/update`
- Make sure your phone and laptop are on the same Wi‑Fi network.
- Open `index.html` on your phone. Options:
  - Easiest: Serve it from your laptop so the phone can open it over Wi‑Fi:
    - In the project root, run: `python -m http.server 5500`
    - On your phone, open: `http://<your_laptop_ip>:5500/index.html`
  - Or copy the file to your phone and open it there. Note: some mobile browsers require HTTPS for geolocation; serving over HTTP from your LAN usually works.

If everything is correct, the page will display your current `lat, lon` and POST to the server continuously.

2b) Open the Web Viewer (browser)

- With the server running, open this in any browser on your LAN:
  - `http://<your_laptop_ip>:8000/`
- You should see a map with a marker. It polls `GET /api/gps` every ~1.5s.
- Keep using the phone page (step 2) to send live GPS to the server.

3) Run the desktop visualizer (optional)

```
python visualize_map.py
```

By default it queries `GPS_SERVER_URL = "http://127.0.0.1:8000/get"`. If your GPS server runs on a different machine/IP, update that constant near the top of `visualize_map.py` accordingly (port 8000).

Controls

Global

- ESC — back from RLH floor to campus; on campus ESC closes the app
- H — toggle A* heuristic between Euclidean and ALT (shows mode and last expansions in HUD)

Campus scene

- Mouse drag (left) — pan the map (disables follow mode until restart)
- z — toggle pixelation effect
- + / = — zoom in
- - / _ — zoom out
- b — load preset RLH “back” route points (visual only)
- f — load preset RLH “front” route points (visual only)
- n — toggle Path Editor mode
  - Left‑click — add a node at mouse position (stored relative to map)
  - Right‑click — remove last node
  - s — save nodes to `path_nodes.txt`
- Click inside the RLH polygon glow to enter the RLH floor plan scene

RLH floor scene

- Click a room marker to select it and compute an A* path from entrance `H1`:
  - CNL Hall
  - Room 134
  - Room 135
- ESC — return to campus scene

Algorithms

This project implements graph search for indoor routing and includes two heuristics for A*:

- Baseline: Euclidean-distance heuristic on a 2D embedded hallway graph.
- ALT (A*, Landmarks, Triangle inequality): we precompute single-source shortest paths from a small set of landmark nodes using Dijkstra. At query time, the heuristic uses the admissible bound `max_L |d(L, goal) − d(L, u)|`. This tightens estimates and typically reduces expansions. You can switch heuristics at runtime with the `H` key and observe the current mode and last expansion count on the HUD. ALT precomputation runs once on startup and covers all RLH nodes.

Notes on evaluation: On our RLH test queries (e.g., `H1 → Room 134/135` and `H1 → CNL Hall`), ALT reduces the number of node expansions versus plain Euclidean, while preserving optimality (admissible and consistent on this graph).

Testing GPS without a phone

You can POST coordinates directly to the server (either endpoint works):

```
curl -X POST http://127.0.0.1:8000/update \
  -H "Content-Type: application/json" \
  -d "{\"lat\":53.1670,\"lon\":8.65222}"
```

Or using the normalized API route:

```
curl -X POST http://127.0.0.1:8000/api/gps \
  -H "Content-Type: application/json" \
  -d "{\"lat\":53.1670,\"lon\":8.65222}"
```

Then check:

```
http://127.0.0.1:8000/get
```

Troubleshooting

- Geolocation doesn’t update on phone page
  - Ensure the phone and laptop are on the same Wi‑Fi.
  - Make sure `SERVER_URL` in `index.html` uses your laptop’s reachable IP (not 127.0.0.1).
  - Some browsers require HTTPS for geolocation; serving `index.html` via `http.server` on your LAN often works. Try a different mobile browser if needed.
  - Windows Firewall might block inbound connections; allow Python/port 8000.

- Web Viewer shows no movement
  - Confirm the server receives updates (terminal prints 📍 Updated GPS: {...}).
  - Open `http://<server_ip>:8000/api/gps` in a browser; you should see `{"lat":..., "lon":...}`.
  - Make sure your phone sender page (root `index.html`) is posting to the correct reachable IP (not 127.0.0.1).

- Visualizer shows no movement
  - Confirm the server receives updates (terminal prints 📍 Updated GPS: {...}).
  - Open `http://<server_ip>:8000/get` in a browser; you should see `{"lat":..., "lon":...}`.
  - If the server runs on a different machine, update `GPS_SERVER_URL` in `visualize_map.py` to point to it.

- Pygame import or SDL errors
  - Ensure you installed dependencies via pip. On Windows, try running from a standard terminal (not as admin).

Notes

- Images and GIFs live under `img/`. Replace with your own assets if you like, but keep paths consistent.
- No license file is provided; default is “all rights reserved” unless you add a LICENSE.

Credits

- Pygame, Flask, Pillow
- Simple A* implementation adapted for indoor graph
- Llama GIF and map images provided in `img/`
