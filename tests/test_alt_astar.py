import os
import math
import importlib


def setup_module(module=None):
    # Ensure headless mode before importing the visualizer module
    os.environ["LLAMA_HEADLESS"] = "1"


def test_path_correct_and_optimal():
    import visualize_map as vm

    start, goal = "H1", "Room 134"
    path = vm.a_star(start, goal)
    assert path is not None and len(path) >= 2
    assert path[0] == start and path[-1] == goal

    # Compute length of the returned path
    length = 0.0
    for u, v in zip(path, path[1:]):
        length += math.dist(vm.graph_nodes[u], vm.graph_nodes[v])

    # Compare to true shortest path via Dijkstra
    # On an undirected graph with symmetric weights, d(u,v) == d(v,u)
    dist_from_start = vm.dijkstra_from(start)
    assert abs(length - dist_from_start[goal]) < 1e-6


def test_alt_admissibility():
    import visualize_map as vm

    vm.USE_ALT = True
    goal = "Room 135"
    # True distances from goal to all nodes (symmetric to all->goal)
    true_d = vm.dijkstra_from(goal)

    for u in vm.graph_nodes.keys():
        h = vm.heuristic(u, goal)
        assert h <= true_d[u] + 1e-6


def test_alt_expansions_not_worse():
    import visualize_map as vm

    start, goal = "H1", "Room 135"

    vm.USE_ALT = False
    _ = vm.a_star(start, goal)
    expansions_euclid = vm.last_astar_expansions

    vm.USE_ALT = True
    _ = vm.a_star(start, goal)
    expansions_alt = vm.last_astar_expansions

    assert expansions_alt <= expansions_euclid
