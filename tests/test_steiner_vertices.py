import networkx as nx

from .utils import get_path


def test_try_insert_edge():
    from steiner_tree.steiner_vertices import try_insert_edge

    inp = nx.read_gpickle(get_path('testcases/insert_edge_inp_1.gpickle'))
    out = nx.read_gpickle(get_path('testcases/insert_edge_out_1.gpickle'))

    g = try_insert_edge(inp, (4, 5), 3)

    assert g._adj == out._adj


def test_find_starting_solution():
    from steiner_tree.utils import parse_graph, find_starting_solution

    for i in range(1, 10, 2):
        g, terminals = parse_graph(i)
        s = find_starting_solution(g, terminals)
        leaves = {node for node in s.nodes if s.degree(node) == 1}

        assert nx.is_tree(s), 'S is not a tree'
        assert leaves.issubset(terminals), 'There are non-leaf terminals'
        assert terminals.issubset(s.nodes), 'S does not contain all the terminals'
