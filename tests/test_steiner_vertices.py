import os
import sys

import networkx as nx

my_path = os.path.dirname(os.path.abspath(__file__))


def get_path(rel_path):
    """
    Get the absolute path from relative path
    """
    return os.path.abspath(
        os.path.join(my_path, rel_path)
    )


# insert the parent directory to sys.path so that we can import modules and functions
sys.path.insert(0, get_path('..'))


def test_try_insert_edge():
    from steiner_vertices import try_insert_edge

    inp = nx.read_gpickle(get_path('testcases/insert_edge_inp_1.gpickle'))
    out = nx.read_gpickle(get_path('testcases/insert_edge_out_1.gpickle'))

    g = try_insert_edge(inp, (4, 5), 3)

    assert g._adj == out._adj


def test_find_starting_solution():
    from utils import parse_graph, find_starting_solution

    for i in range(1, 10, 2):
        g, terminals = parse_graph(i)
        s = find_starting_solution(g, terminals)
        leaves = (node for node in s.nodes if s.degree(node) == 1)

        assert nx.is_tree(s) and all(leaf in terminals for leaf in leaves)


if __name__ == '__main__':
    test_find_starting_solution()
