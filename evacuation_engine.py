"""Core graph, informed-search, evacuation assignment and simulation logic."""
from __future__ import annotations

import math
import heapq
from collections import defaultdict
import networkx as nx

EXITS = ["exit_1", "exit_2", "exit_3", "exit_4"]

NODES = {
    "room_a":     {"label": "Room A", "floor": 1, "x": 1, "y": 1, "kind": "room"},
    "room_b":     {"label": "Room B", "floor": 1, "x": 1, "y": 3, "kind": "room"},
    "junction_1": {"label": "Junction 1", "floor": 1, "x": 3, "y": 2, "kind": "junction"},
    "corridor_1": {"label": "Corridor 1", "floor": 1, "x": 5, "y": 1, "kind": "corridor"},
    "corridor_2": {"label": "Corridor 2", "floor": 1, "x": 5, "y": 3, "kind": "corridor"},
    "stair_1":    {"label": "Staircase 1", "floor": 1, "x": 7, "y": 2, "kind": "stair"},
    "exit_1":     {"label": "Exit 1", "floor": 1, "x": 7, "y": 0, "kind": "exit"},
    "exit_2":     {"label": "Exit 2", "floor": 1, "x": 7, "y": 4, "kind": "exit"},
    "room_c":     {"label": "Room C", "floor": 2, "x": 1, "y": 1, "kind": "room"},
    "room_d":     {"label": "Room D", "floor": 2, "x": 1, "y": 3, "kind": "room"},
    "junction_2": {"label": "Junction 2", "floor": 2, "x": 3, "y": 2, "kind": "junction"},
    "corridor_3": {"label": "Corridor 3", "floor": 2, "x": 5, "y": 1, "kind": "corridor"},
    "corridor_4": {"label": "Corridor 4", "floor": 2, "x": 5, "y": 3, "kind": "corridor"},
    "stair_2":    {"label": "Staircase 2", "floor": 2, "x": 7, "y": 2, "kind": "stair"},
    "exit_3":     {"label": "Exit 3", "floor": 2, "x": 7, "y": 0, "kind": "exit"},
    "exit_4":     {"label": "Exit 4", "floor": 2, "x": 7, "y": 4, "kind": "exit"},
}

# Each edge has a length (m) and maximum flow capacity (people/minute).
EDGES = [
    ("room_a", "junction_1", 12, 18), ("room_b", "junction_1", 12, 18),
    ("junction_1", "corridor_1", 10, 20), ("junction_1", "corridor_2", 10, 20),
    ("corridor_1", "exit_1", 12, 18), ("corridor_2", "exit_2", 12, 18),
    ("junction_1", "stair_1", 14, 16), ("stair_1", "stair_2", 18, 12),
    ("room_c", "junction_2", 12, 18), ("room_d", "junction_2", 12, 18),
    ("junction_2", "corridor_3", 10, 20), ("junction_2", "corridor_4", 10, 20),
    ("corridor_3", "exit_3", 12, 18), ("corridor_4", "exit_4", 12, 18),
    ("junction_2", "stair_2", 14, 16),
]

ROOMS = ["room_a", "room_b", "room_c", "room_d"]
NODE_LABELS = {k: v["label"] for k, v in NODES.items()}
CONDITION_SPEED = {"Mobile": 1.0, "Reduced mobility": 0.65, "Needs assistance": 0.45}

def build_building_graph():
    graph = nx.Graph()
    for node, attrs in NODES.items():
        graph.add_node(node, **attrs)
    for a, b, distance, capacity in EDGES:
        graph.add_edge(a, b, distance=float(distance), capacity=float(capacity),
                       congestion=0.0, hazard=0.0, blocked=False)
    return graph

def apply_scenario(graph, scenario, hazard_node, severity, spread, blocked_edge=None, time_step=3):
    """Apply illustrative hazard penalties and an optional manually blocked edge."""
    for node in graph.nodes:
        graph.nodes[node]["hazard"] = 0.0
        graph.nodes[node]["unsafe"] = False

    # Time-stepped, simplified hazard propagation from the selected origin.
    active_radius = min(spread, max(0, time_step))
    time_factor = min(1.0, 0.25 + 0.20 * time_step)
    if hazard_node in graph:
        lengths = nx.single_source_shortest_path_length(graph, hazard_node, cutoff=active_radius)
        for node, hops in lengths.items():
            if scenario == "Flood" and graph.nodes[node]["floor"] == 1:
                intensity = 1.0
            else:
                intensity = max(0.15, 1.0 - 0.28 * hops)
            level = min(1.0, severity * intensity * time_factor)
            graph.nodes[node]["hazard"] = level
            graph.nodes[node]["unsafe"] = level >= 0.88

    for a, b in graph.edges:
        graph[a][b]["blocked"] = False
        graph[a][b]["congestion"] = 0.0
        graph[a][b]["hazard"] = max(graph.nodes[a]["hazard"], graph.nodes[b]["hazard"])
        if scenario == "Earthquake" and graph[a][b]["hazard"] >= 0.75:
            graph[a][b]["blocked"] = True

    if blocked_edge and blocked_edge[0] in graph and blocked_edge[1] in graph:
        if graph.has_edge(*blocked_edge):
            graph[blocked_edge[0]][blocked_edge[1]]["blocked"] = True

def edge_cost(graph, a, b, speed=1.0, extra_load=0):
    data = graph[a][b]
    if data.get("blocked") or graph.nodes[a].get("unsafe") or graph.nodes[b].get("unsafe"):
        return math.inf
    distance = data["distance"]
    congestion = data.get("congestion", 0.0)
    hazard = data.get("hazard", 0.0)
    capacity = max(1.0, data["capacity"])
    # Cost is a planning score in seconds-equivalent, not a certified prediction.
    travel = distance / max(0.2, 1.35 * speed) 
    crowd_penalty = 8.0 * congestion + 0.20 * extra_load / capacity
    hazard_penalty = 28.0 * hazard
    return travel + crowd_penalty + hazard_penalty

def astar_path(graph, start, goal, speed=1.0, extra_load=0):
    """A* search using a straight-line distance heuristic."""
    if start not in graph or goal not in graph:
        return None, math.inf, 0
    if graph.nodes[goal].get("unsafe"):
        return None, math.inf, 0

    def heuristic(node, target):
        p, q = graph.nodes[node], graph.nodes[target]
        # Floor changes are represented by an additional vertical penalty.
        return math.hypot(p["x"] - q["x"], p["y"] - q["y"]) * 0.35 + abs(p["floor"] - q["floor"]) * 3.0

    counter = 0
    frontier = [(heuristic(start, goal), 0.0, counter, start, [start])]
    best = {start: 0.0}
    explored = 0
    while frontier:
        _, cost_so_far, _, current, path = heapq.heappop(frontier)
        if cost_so_far > best.get(current, math.inf):
            continue
        explored += 1
        if current == goal:
            return path, cost_so_far, explored
        for neighbour in graph.neighbors(current):
            step = edge_cost(graph, current, neighbour, speed, extra_load)
            new_cost = cost_so_far + step
            if math.isfinite(new_cost) and new_cost < best.get(neighbour, math.inf):
                best[neighbour] = new_cost
                counter += 1
                priority = new_cost + heuristic(neighbour, goal)
                heapq.heappush(frontier, (priority, new_cost, counter, neighbour, path + [neighbour]))
    return None, math.inf, explored

def bfs_path(graph, start, goal):
    """Unweighted BFS baseline; skips blocked and unsafe locations."""
    if start not in graph or goal not in graph or graph.nodes[goal].get("unsafe"):
        return None
    queue = [(start, [start])]
    seen = {start}
    while queue:
        node, path = queue.pop(0)
        if node == goal:
            return path
        for nxt in graph.neighbors(node):
            if nxt not in seen and not graph[nxt][node].get("blocked") and not graph.nodes[nxt].get("unsafe"):
                seen.add(nxt)
                queue.append((nxt, path + [nxt]))
    return None

def path_distance(graph, path):
    if not path:
        return math.inf
    return sum(graph[a][b]["distance"] for a, b in zip(path, path[1:]))

def estimate_group_time(graph, path, people, condition, assigned_load=0):
    if not path:
        return math.inf
    speed = CONDITION_SPEED[condition]
    distance = path_distance(graph, path)
    travel_seconds = distance / (1.35 * speed) 
    bottleneck = min(graph[a][b]["capacity"] for a, b in zip(path, path[1:])) if len(path) > 1 else 60
    queue_seconds = (people + assigned_load) / max(1.0, bottleneck) * 60.0
    return travel_seconds + queue_seconds

def assign_groups(graph, groups):
    """Greedy capacity-aware group assignment across all safe exits."""
    exit_load = defaultdict(int)
    assignments = []
    total_explored = 0
    for group in sorted(groups, key=lambda g: g["people"], reverse=True):
        candidates = []
        for exit_node in EXITS:
            if exit_node not in graph or graph.nodes[exit_node].get("unsafe"):
                continue
            path, score, explored = astar_path(
                graph, group["start"], exit_node,
                CONDITION_SPEED[group["condition"]], exit_load[exit_node]
            )
            total_explored += explored
            if path:
                estimate = estimate_group_time(graph, path, group["people"], group["condition"], exit_load[exit_node])
                # Additional exit queue term encourages distributing groups.
                estimate += exit_load[exit_node] / 3.0
                candidates.append((estimate, exit_node, path, score))
        if candidates:
            estimate, exit_node, path, score = min(candidates, key=lambda x: x[0])
            exit_load[exit_node] += group["people"]
            assignments.append({**group, "exit": exit_node, "path": path,
                                "estimated_seconds": estimate, "search_score": score})
        else:
            assignments.append({**group, "exit": None, "path": None,
                                "estimated_seconds": math.inf, "search_score": math.inf})
    return assignments, dict(exit_load), total_explored


def multi_source_exit_search(graph, speed=1.0):
    """Multi-source Dijkstra search seeded from all currently safe exits."""
    frontier = []
    best = {}
    destination = {}
    next_hop = {}
    for exit_node in EXITS:
        if exit_node in graph and not graph.nodes[exit_node].get("unsafe"):
            best[exit_node] = 0.0
            destination[exit_node] = exit_node
            heapq.heappush(frontier, (0.0, exit_node))
    while frontier:
        cost, current = heapq.heappop(frontier)
        if cost > best.get(current, math.inf):
            continue
        for neighbour in graph.neighbors(current):
            step = edge_cost(graph, current, neighbour, speed)
            candidate = cost + step
            if math.isfinite(candidate) and candidate < best.get(neighbour, math.inf):
                best[neighbour] = candidate
                destination[neighbour] = destination[current]
                next_hop[neighbour] = current
                heapq.heappush(frontier, (candidate, neighbour))
    return {"cost": best, "exit": destination, "next_hop": next_hop}


def nearest_exit_assignments(graph, groups):
    """Naive baseline: choose the safe exit with shortest geometric path."""
    results = []
    for group in groups:
        choices = []
        for ex in EXITS:
            try:
                p = nx.shortest_path(graph, group["start"], ex)
                if any(graph.nodes[n].get("unsafe") for n in p):
                    continue
                if any(graph[a][b].get("blocked") for a, b in zip(p, p[1:])):
                    continue
                choices.append((path_distance(graph, p), ex, p))
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue
        if choices:
            _, ex, p = min(choices, key=lambda x: x[0])
            results.append({**group, "exit": ex, "path": p})
        else:
            results.append({**group, "exit": None, "path": None})
    return results

def generate_groups(total_people):
    """Create four illustrative occupant groups across the two floors."""
    starts = ["room_a", "room_b", "room_c", "room_d"]
    weights = [0.28, 0.22, 0.28, 0.22]
    counts = [int(total_people * w) for w in weights]
    counts[-1] += total_people - sum(counts)
    conditions = ["Mobile", "Reduced mobility", "Mobile", "Needs assistance"]
    return [{"name": f"Group {chr(65+i)}", "start": starts[i], "people": counts[i],
             "condition": conditions[i]} for i in range(4) if counts[i] > 0]

def apply_congestion(graph, groups):
    """Illustrative initial demand load on shared edges."""
    demand = defaultdict(int)
    for group in groups:
        for a, b in zip([group["start"], "junction_1" if group["start"] in ("room_a","room_b") else "junction_2"],
                        ["junction_1" if group["start"] in ("room_a","room_b") else "junction_2",
                         "stair_1" if group["start"] in ("room_a","room_b") else "stair_2"]):
            if graph.has_edge(a, b):
                demand[tuple(sorted((a,b)))] += group["people"]
    for a, b in graph.edges:
        cap = graph[a][b]["capacity"]
        load = demand[tuple(sorted((a,b)))]
        graph[a][b]["congestion"] = min(1.0, load / max(1.0, cap * 2.0))
