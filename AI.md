
## AI Tools Used

- **ChatGPT/Claude** - Algorithm explanations, code generation, debugging help
- **Junie** - Code completion and boilerplate

---

## What AI Helped With

### 1. Algorithm Selection & Understanding

When we started, we asked AI about advanced pathfinding algorithms beyond basic A*. AI introduced us to **ALT (A*, Landmarks, Triangle inequality)** and explained how it works:
- Precompute distances from landmark nodes using Dijkstra
- Use triangle inequality to get better heuristic bounds: `max_L |d(L,goal) - d(L,u)|`
- This reduces the number of nodes explored while staying optimal

We chose ALT over other options (like Contraction Hierarchies or Jump Point Search) because it fit well with our indoor navigation graph and we could understand and implement it properly.

### 2. Core Algorithm Code

**A* Implementation** (`visualize_map.py`, lines 254-290)
- AI generated the basic A* structure with priority queue
- We added expansion counting, integrated it with our graph, and optimized for visualization

**Dijkstra's Algorithm** (`visualize_map.py`, lines 205-220)  
- AI provided the implementation for landmark preprocessing
- We adapted it to our graph with Euclidean edge weights

**ALT Heuristic** (`visualize_map.py`, lines 233-251)
- AI explained the math and gave initial code
- We added fallback to Euclidean distance and runtime toggling between heuristics

**Landmark Preprocessing** (`visualize_map.py`, lines 223-230)
- AI suggested the preprocessing approach
- We manually selected the 4 landmark positions based on our building layout

### 3. Test Suite

AI generated most of the test code in `tests/test_alt_astar.py`:
- **test_path_correct_and_optimal** - Verifies path length matches Dijkstra (proves optimality)
- **test_alt_admissibility** - Checks heuristic never overestimates (required for A*)
- **test_alt_expansions_not_worse** - Shows ALT explores fewer nodes than Euclidean

We provided the specific test cases (like "H1 → Room 134") and validated the results.


