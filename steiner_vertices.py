import networkx as nx

from utils import prune_tree, graph_weight


def try_insert_edge(s, e, w_e):
    """
    Try to insert edge e = (u, v) with weight w_e into S.
    We replace the longest edge connecting u and v in S by e if its weight greater than w_e.
    """
    path = nx.dijkstra_path(s, *e)  # the path connecting v and w in S
    path_edges = zip(path[:-1], path[1:])  # the edges on the path
    longest_edge = max(path_edges, key=lambda x: s.edges[x]['weight'])

    if s.edges[longest_edge]['weight'] > w_e:
        s.remove_edge(*longest_edge)
        s.add_edge(*e, weight=w_e)

    return s


def steiner_vertices_insertion(g, s, terminals):
    """
    Determine if there is a vertex v not in V_S such that MST(G[V_S ∪ v]) is cheaper than S.
    """
    available_nodes = set(g.nodes) - set(s.nodes)  # nodes can be inserted to S
    if not available_nodes:
        return s

    s_weight = graph_weight(s)

    for v in available_nodes:
        connecting_edges = ((v, w) for w in g[v] & s.nodes)  # edges connecting v and S

        new_s = s.copy()
        for i, ei in enumerate(connecting_edges):
            # we add the edges e1, e2,... in E(S, v) one at a time, after i-th step, new_s is
            # the MST of (V_S ∪ v, E_S ∪ {e1,...,ei}

            if i == 0:
                # simply add the first connecting edge without doing anything extra
                new_s = g.edge_subgraph(list(s.edges) + [ei])

                # make new_s a Graph instead of a SubGraph so that we can modify it
                new_s = nx.Graph(new_s)
            else:
                # now v is a node in S, we need to check if adding ei improve the weight
                new_s = try_insert_edge(new_s, ei, g.edges[ei]['weight'])

        new_s_weight = graph_weight(new_s)

        if new_s_weight < s_weight:
            s_weight = new_s_weight
            s = new_s.copy()

    s = prune_tree(s, terminals)

    return s


def steiner_vertices_elimination(g, s, terminals):
    """
    Determine if there is a vertex v in V_S \ T such that MST(G[V_S - v]) is cheaper than S.
    We evaluate each possible removal by rerunning Kruskal's algorithm on the induced subgraph.
    """
    available_nodes = set(s.nodes) - terminals  # nodes can be deleted from s
    if not available_nodes:
        return s

    original_s = s.copy()
    s_weight = graph_weight(s)

    for v in available_nodes:
        temp = g.subgraph(original_s.nodes)
        temp = nx.Graph(temp)
        temp.remove_node(v)

        if not nx.is_connected(temp):
            continue

        new_s = nx.minimum_spanning_tree(temp)
        new_s_weight = graph_weight(new_s)

        if new_s_weight < s_weight:
            s_weight = new_s_weight
            s = new_s.copy()

    s = prune_tree(s, terminals)

    return s


def local_search(g, s, terminals):
    s = steiner_vertices_elimination(g, s, terminals)
    s = steiner_vertices_insertion(g, s, terminals)

    assert nx.is_tree(s)
    assert terminals.issubset(s.nodes)

    return s
