import math
from evacuation_engine import build_building_graph, apply_scenario, astar_path, bfs_path, generate_groups, assign_groups, multi_source_exit_search

def test_graph_has_two_floors_and_exits():
    g = build_building_graph()
    assert g.nodes["room_a"]["floor"] == 1
    assert g.nodes["room_c"]["floor"] == 2
    assert all(e in g for e in ["exit_1", "exit_2", "exit_3", "exit_4"])

def test_astar_finds_route_in_safe_building():
    g = build_building_graph()
    apply_scenario(g, "Fire", "room_a", 0.2, 0)
    path, cost, explored = astar_path(g, "room_a", "exit_1")
    assert path[0] == "room_a"
    assert path[-1] == "exit_1"
    assert math.isfinite(cost)
    assert explored > 0

def test_blocked_edge_is_avoided():
    g = build_building_graph()
    apply_scenario(g, "Fire", "room_a", 0.1, 0, ("corridor_1", "exit_1"))
    path, cost, _ = astar_path(g, "room_a", "exit_1")
    assert path is None or ("corridor_1" not in path or "exit_1" not in path)

def test_groups_sum_to_requested_population():
    groups = generate_groups(123)
    assert sum(g["people"] for g in groups) == 123

def test_assignment_returns_one_record_per_group():
    g = build_building_graph()
    apply_scenario(g, "Fire", "room_a", 0.2, 0)
    groups = generate_groups(80)
    assigned, loads, explored = assign_groups(g, groups)
    assert len(assigned) == len(groups)
    assert explored >= 0


def test_multi_source_search_maps_rooms_to_a_safe_exit():
    g = build_building_graph()
    apply_scenario(g, "Fire", "room_a", 0.1, 0, time_step=0)
    result = multi_source_exit_search(g)
    assert "room_a" in result["exit"]
    assert result["exit"]["room_a"] in ["exit_1", "exit_2", "exit_3", "exit_4"]
