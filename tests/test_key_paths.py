from .utils import small_instances


def test_find_key_paths():
    from utils import parse_graph
    from key_paths import find_key_paths, distance_network_heuristics

    for i in small_instances:
        g, terminals = parse_graph(i)
        s = distance_network_heuristics(g, terminals)
        crucial_vertices = {node for node in s.nodes
                            if s.degree(node) >= 3 or node in terminals}

        key_paths = find_key_paths(s, crucial_vertices)
        ends = set()
        nodes = set()
        for path in key_paths:
            nodes.update(path)

            ends.add(path.pop(0))
            ends.add(path.pop())

        assert ends == crucial_vertices
        assert nodes == set(s.nodes)
