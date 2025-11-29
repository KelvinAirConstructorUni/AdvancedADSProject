import math
from visualize_map import graph_nodes, graph_edges


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
