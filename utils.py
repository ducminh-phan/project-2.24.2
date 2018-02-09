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


def check_solution(s, terminals):
    leaves = {node for node in s.nodes if s.degree(node) == 1}

    assert nx.is_tree(s), 'S is not a tree'
    assert leaves.issubset(terminals), 'There are non-leaf terminals'
    assert terminals.issubset(s.nodes), 'S does not contain all the terminals'


def get_contest_results():
    """
    Get the current results of the participants
    """
    import requests
    import bs4
    import numpy as np

    def to_int(s):
        try:
            s = s.replace(',', '')
            return int(float(s))
        except ValueError:
            return float('inf')

    url = 'https://www.optil.io/optilion/problem/3025/standing'
    response = requests.get(url)
    soup = bs4.BeautifulSoup(response.text, 'html5lib')

    # Get the result table
    table = soup.find('table')
    table_body = table.find('tbody')
    rows = table_body.find_all('tr')

    # Parse the table
    data = []
    for row in rows:
        cells = row.find_all('td')
        cells = [to_int(cell.text.strip()) for cell in cells]
        data.append(cells)

    # Convert the table to numpy array
    data = np.array(data)

    # Remove non-result columns
    data = data[:, 4:]

    # Save the results
    np.save('results.npy', data)

    return data
