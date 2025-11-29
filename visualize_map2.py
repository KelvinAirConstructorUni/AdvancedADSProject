import pygame
import math

pygame.init()
screen = pygame.display.set_mode((1200, 800))
clock = pygame.time.Clock()

# --------------------------------------------------------
# Your Data
# --------------------------------------------------------
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
    "passages": {"pos": passages}
}

graph_nodes = {
    "H1": (600, 350),
    "H2": (620, 420),
    "H3": (650, 500),

    "CNL Hall": rooms["CNL Hall"]["pos"][0],
    "Room 134": rooms["Room 134"]["pos"][0],
    "Room 135": rooms["Room 135"]["pos"][0],
}

graph_edges = {
    "H1": ["H2"],
    "H2": ["H1", "H3", "CNL Hall"],
    "H3": ["H2", "Room 134", "Room 135"],
    "CNL Hall": ["H2"],
    "Room 134": ["H3"],
    "Room 135": ["H3"]
}

# --------------------------------------------------------
# Bingo's START location
# --------------------------------------------------------
bingo_node = "H1"

# Last path that was computed
last_path = None


# --------------------------------------------------------
# Helper Functions
# --------------------------------------------------------
def dist(a, b):
    return math.dist(a, b)


def dijkstra(start, goal):
    """Return shortest path from start → goal."""
    unvisited = set(graph_nodes.keys())
    dist_to = {n: float("inf") for n in unvisited}
    parent = {n: None for n in unvisited}

    dist_to[start] = 0

    while unvisited:
        current = min(unvisited, key=lambda n: dist_to[n])
        unvisited.remove(current)

        if current == goal:
            break

        for nxt in graph_edges.get(current, []):
            cost = dist(graph_nodes[current], graph_nodes[nxt])
            if dist_to[current] + cost < dist_to[nxt]:
                dist_to[nxt] = dist_to[current] + cost
                parent[nxt] = current

    if dist_to[goal] == float("inf"):
        return None

    # rebuild path
    path = []
    p = goal
    while p is not None:
        path.append(p)
        p = parent[p]
    path.reverse()
    return path


def node_at_pos(mx, my, radius=20):
    """Return node clicked if close enough"""
    for name, (x, y) in graph_nodes.items():
        if (mx - x) ** 2 + (my - y) ** 2 <= radius ** 2:
            return name
    return None


# --------------------------------------------------------
# Main Loop
# --------------------------------------------------------
running = True
while running:
    screen.fill((240, 240, 240))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # When click → compute shortest path
        if event.type == pygame.MOUSEBUTTONDOWN:
            clicked = node_at_pos(*event.pos)
            if clicked:
                last_path = dijkstra(bingo_node, clicked)
                print("PATH:", last_path)

    # Draw edges (gray)
    for a, neighbors in graph_edges.items():
        for b in neighbors:
            ax, ay = graph_nodes[a]
            bx, by = graph_nodes[b]
            pygame.draw.line(screen, (180, 180, 180), (ax, ay), (bx, by), 4)

    # Draw path (yellow)
    if last_path:
        for i in range(len(last_path) - 1):
            ax, ay = graph_nodes[last_path[i]]
            bx, by = graph_nodes[last_path[i + 1]]
            pygame.draw.line(screen, (255, 220, 0), (ax, ay), (bx, by), 8)

    # Draw nodes
    for name, (x, y) in graph_nodes.items():
        color = (0, 200, 50) if name != bingo_node else (255, 120, 0)
        pygame.draw.circle(screen, color, (x, y), 15)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
