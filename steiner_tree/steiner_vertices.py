import networkx as nx
from networkx.utils import pairwise

from .utils import prune_tree, graph_weight


def try_insert_edge(s, e, w_e):
    """
    Try to insert edge e = (u, v) with weight w_e into S.
    We replace the longest edge connecting u and v in S
    by e if its weight is greater than w_e.
    """
    # The path connecting v and w in S
    path = nx.dijkstra_path(s, *e)

    # The edges on the path
    path_edges = pairwise(path)

    # Find the longest edge in the path connecting v and w in S
    longest_edge = max(path_edges, key=lambda x: s.edges[x]['weight'])

    # Replace the longest edge if it leads to an improvement
    if s.edges[longest_edge]['weight'] > w_e:
        s.remove_edge(*longest_edge)
        s.add_edge(*e, weight=w_e)

    return s


def steiner_vertices_insertion(g, s, terminals, early_stop=True):
    """
    Determine if there is a vertex v not in V_S such that MST(G[V_S ∪ v])
    is cheaper than S. For each available node, we add the edges connecting
    v and S one-by-one, and see if adding the edges leads to an improvement.
    """
    available_nodes = set(g.nodes) - set(s.nodes)  # nodes can be inserted to S
    if not available_nodes:
        return s

    original_s = s.copy()
    s_weight = graph_weight(s)

    for v in available_nodes:
        # Find the edges connecting v and S
        connecting_edges = ((v, w) for w in g[v] & original_s.nodes)

        new_s = original_s.copy()
        for i, ei in enumerate(connecting_edges):
            # We add the edges e1, e2,... in E(S, v) one at a time, after i-th step,
            # new_s is the MST of (V_S ∪ v, E_S ∪ {e1,...,ei}

            if i == 0:
                # Simply add the first connecting edge without doing anything extra
                new_s = g.edge_subgraph(list(new_s.edges) + [ei]).copy()
            else:
                # Now v is a node in S, we need to check if adding ei improve the weight
                new_s = try_insert_edge(new_s, ei, g.edges[ei]['weight'])

        new_s_weight = graph_weight(new_s)

        if new_s_weight < s_weight:
            s_weight = new_s_weight
            s = new_s.copy()

            if early_stop:
                # Break the loop as soon as we have an improvement
                # without looking for the best one
                break

    return prune_tree(s, terminals)


def steiner_vertices_elimination(g, s, terminals, early_stop=True):
    """
    Determine if there is a vertex v in V_S \ T such that MST(G[V_S - v])
    is cheaper than S. We evaluate each possible removal by rerunning
    Kruskal's algorithm on the induced subgraph.
    """
    available_nodes = set(s.nodes) - terminals  # nodes can be deleted from s
    if not available_nodes:
        return s

    original_s = s.copy()
    s_weight = graph_weight(s)

    for v in available_nodes:
        # Temporarily remove v from S
        temp = g.subgraph(original_s.nodes).copy()
        temp.remove_node(v)

        if not nx.is_connected(temp):
            continue

        new_s = nx.minimum_spanning_tree(temp)
        new_s_weight = graph_weight(new_s)

        if new_s_weight < s_weight:
            if early_stop:
                # Return as soon as we have an improvement
                # without looking for the best one
                return prune_tree(new_s, terminals)

            s_weight = new_s_weight
            s = new_s.copy()

    s = prune_tree(s, terminals)

    return s


def local_search(g, s, terminals, early_stop=True):
    s = steiner_vertices_elimination(g, s, terminals, early_stop=early_stop)
    s = steiner_vertices_insertion(g, s, terminals, early_stop=early_stop)

    return s
