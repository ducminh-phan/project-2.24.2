import os

import networkx as nx

my_path = os.path.dirname(os.path.abspath(__file__))


def get_path(rel_path):
    """
    Get the absolute path from relative path to the file f
    """
    return os.path.abspath(
        os.path.join(my_path, rel_path)
    )


def parse_graph(instance_id):
    file_path = get_path('public/instance{}.gr'.format(str(instance_id).zfill(3)))

    with open(file_path) as f:
        f.readline()
        _ = int(f.readline().split()[1])
        n_edges = int(f.readline().split()[1])

        g = nx.Graph()

        for _ in range(n_edges):
            u, v, w = map(int, f.readline().split()[1:])
            g.add_edge(u, v, weight=w)

        for _ in range(3):
            f.readline()

        n_terminals = int(f.readline().split()[1])
        terminals = set(int(f.readline().split()[1]) for _ in range(n_terminals))

    return g, terminals


def find_starting_solution(g, terminals):
    """
    Find a starting solution for the local search.
    Return S = (V_S, E_S) where S = MST(G[V_S]),
    and all degree-one vertices are terminals
    """
    tree = nx.minimum_spanning_tree(g)
    tree = prune_tree(tree, terminals)

    return tree


def prune_tree(tree, terminals):
    leaves = [node for node in tree.nodes
              if tree.degree(node) == 1 and node not in terminals]

    for leaf in leaves:
        while tree.degree(leaf) == 1 and leaf not in terminals:
            w = list(nx.all_neighbors(tree, leaf))[0]
            tree.remove_node(leaf)
            leaf = w

    return tree


def graph_weight(g):
    return sum(edge_data['weight'] for edge_data in g.edges.values())
