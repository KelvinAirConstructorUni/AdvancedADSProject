import heapq
import math

def heuristic(a, b, edges, nodes):
    """Euclidean distance heuristic for A*"""
    (x1, y1) = nodes[a]
    (x2, y2) = nodes[b]
    return math.hypot(x2 - x1, y2 - y1)

def a_star_search(start, goal, edges, nodes):
    """Computes the shortest path between start and goal."""
    frontier = []
    heapq.heappush(frontier, (0, start))
    came_from = {start: None}
    cost_so_far = {start: 0}

    while frontier:
        _, current = heapq.heappop(frontier)
        if current == goal:
            break

        for neighbor in edges[current]:
            # cost = distance between nodes
            new_cost = cost_so_far[current] + heuristic(current, neighbor)
            if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                cost_so_far[neighbor] = new_cost
                priority = new_cost + heuristic(neighbor, goal)
                heapq.heappush(frontier, (priority, neighbor))
                came_from[neighbor] = current

    # reconstruct path
    path = []
    current = goal
    while current is not None:
        path.append(current)
        current = came_from.get(current)
    path.reverse()
    return path
