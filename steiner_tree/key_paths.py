from copy import deepcopy
from itertools import chain

import networkx as nx
from networkx.utils import groups, pairwise

from .utils import graph_weight, prune_tree


class VoronoiDiagram:
    """
    Given G = (V, E) and a set A ⊆ V of centers a Voronoi diagram of V with respect to A is
    a partition of V into |A| connected regions such that (i) each region contains exactly
    one vertex of A (the base of this region) and (ii) each vertex v in V \ A is assigned to
    the region whose base is closest to v. This generalizes Voronoi diagrams in geometric
    settings.

    The diagram associates three pieces of information with each vertex v: base(v) is the
    base of the region containing v; p(v) is the predecessor of v on the shortest path from
    base(v) (if v is a base, then p(v) = v); and vdist(v) is the distance from base(v) to v.

    Here for each vertex v, we store the path from base(v) to v instead of the predecessor,
    as we don't really need to use the predecessor, but the path from the base to construct
    the shortest path between two bases.
    """
    def __init__(self, g, centers):
        dists, paths = nx.multi_source_dijkstra(g, centers)

        self.bases = {}
        self.paths = {}
        self.dists = {}

        for v, path in paths.items():
            # path is the Dijkstra path from a center to v

            # Determine the center node from which the shortest path originates
            base = path[0]

            # The distance from the base to v
            dist = dists[v]

            self.bases[v] = base
            self.paths[v] = path
            self.dists[v] = dist

    @property
    def cells(self):
        """
        The cells of a Voronoi diagram, which is a mapping from a center
        to the nodes in its cell.
        """
        return groups(self.bases)

    def copy(self):
        """
        Make a copy of a Voronoi diagram to modify it without affecting
        the original diagram.
        """
        cls = self.__class__
        voronoi = cls.__new__(cls)

        voronoi.bases = deepcopy(self.bases)
        voronoi.paths = deepcopy(self.paths)
        voronoi.dists = deepcopy(self.dists)

        return voronoi

    def repair(self, g, s, key_path):
        """
        Repair the Voronoi diagram after removing a key path in S. Since we
        might have unassigned vertices, corresponding to the removed Voronoi
        cells, we need to find the new bases for these vertices, which is the
        nearest vertex in the two components of s.

        Return the two sets which partition V_G, corresponding to two connected
        components of S after removing the path. Each set is the union of the
        cells in the repaired Voronoi diagram of the vertices in two components.
        """
        internal_vertices = key_path[1:-1]
        new_s = s.copy()
        new_s.remove_edges_from(pairwise(key_path))
        new_s.remove_nodes_from(internal_vertices)

        # The vertices of the two subtrees created after removing the key path
        s1, s2 = list(nx.connected_components(new_s))

        # Join the Voronoi cells
        s1_cells = set.union(*(self.cells[v] for v in s1))
        s2_cells = set.union(*(self.cells[v] for v in s2))

        if internal_vertices:
            # We need to reassign the vertices in the cells of
            # the internal vertices to partition V_G into two sets
            # corresponding to the two subtrees of S

            # The vertices unassigned after removing the key path
            unassigned_vertices = set.union(*(self.cells[v] for v in internal_vertices))
            assert len(s1_cells) + len(s2_cells) + len(unassigned_vertices) == len(g)

            # For each unassigned vertex u, we find the nearest vertex v in the two subtrees,
            # then assign u to the Voronoi cell of v
            for u in unassigned_vertices:
                dists, paths = nx.single_source_dijkstra(g, u)

                # Filter the dijkstra dists and paths to look for paths to
                # the vertices in s1 and s2 only
                dists = {v: dists[v] for v in s1 | s2}
                paths = {v: paths[v] for v in s1 | s2}

                # Find the new base for u, which is the vertex in s1 ∪ s2 nearest to u
                base = min(dists, key=dists.get)
                self.bases[u] = base

                # We need to reverse the path since a Voronoi path
                # starts from the base
                path = paths[base]
                self.paths[u] = path[::-1]

                self.dists[u] = dists[base]

                # Add u to the corresponding node set
                if base in s1:
                    s1_cells.add(u)
                else:
                    s2_cells.add(u)

        return s1_cells, s2_cells


def boundary_edge_cost(edge, weight, voronoi):
    """
    Calculate the cost of a boundary edge in a Voronoi diagram.
    """
    u, v = edge

    assert voronoi.bases[u] != voronoi.bases[v]

    return voronoi.dists[u] + weight + voronoi.dists[v]


def base_path(u, v, voronoi):
    """
    Find the path connecting base(u) and base(v), given that
    (u, v) is a boundary edge.
    """
    assert voronoi.bases[u] != voronoi.bases[v]

    return voronoi.paths[u] + voronoi.paths[v][::-1]


def auxiliary_graph(g, voronoi):
    """
    Construct the auxiliary graph G' of G w.r.t. to a set of centers.
    The nodes of G' correspond to the centers provided. For each boundary edge
    (u, v) in the Voronoi diagram, G' has an edge between base(u) and base(v),
    with the weight of dist(u) + weight(u, v) + dist(v). Here we only store
    such edges with min distance among the boundary edges connecting the same
    Voronoi regions, together with the chosen boundary edges connecting them.
    """
    aux = nx.Graph()

    for u, v, d in g.edges.data('weight'):
        base_u = voronoi.bases[u]
        base_v = voronoi.bases[v]

        # Skip non-boundary edges
        if base_u == base_v:
            continue

        # Add the edge (base_u, base_v) to the auxiliary graph
        # if it was not already added
        if (base_u, base_v) not in aux.edges:
            aux.add_edge(base_u, base_v)

        cost_uv = boundary_edge_cost((u, v), d, voronoi)

        # Update the weight and the boundary edge between two centers if
        # the boundary edge cost is smaller than the current weight
        if cost_uv < aux.edges[base_u, base_v].get('weight', float('inf')):
            aux.edges[base_u, base_v]['weight'] = cost_uv
            aux.edges[base_u, base_v]['boundary_edge'] = (u, v)

    return aux


def distance_network_heuristics(g, terminals):
    """
    A 2-approximate constructive algorithm for Steiner tree.
    The algorithm computes the MST of the auxiliary graph of G w.r.t.
    the terminals, then expands its edges to obtain a tree in G.
    """
    voronoi = VoronoiDiagram(g, terminals)
    aux = auxiliary_graph(g, voronoi)
    mst = nx.minimum_spanning_tree(aux)
    edge_container = []  # container for the edges of the Steiner tree

    for _, _, (u, v) in mst.edges.data('boundary_edge'):
        # The path from base(u) to base(v) in the mst
        path = base_path(u, v, voronoi)

        # Add the edges from the path to the container
        edge_container.append(pairwise(path))

    # The DNH is formed by joining all the edges found above
    dnh = nx.Graph(g.edge_subgraph(
        chain.from_iterable(edge_container)
    ))

    return dnh


def find_key_paths(g, crucial_vertices):
    """
    Find all the key paths of a graph G w.r.t. the set of crucial vertices.
    A key path connects two crucial vertices and has no internal crucial
    vertices. In our context, G is a tree, C = K ∪ T, where K is the set
    of key vertices, which are non-terminal and degree at least 3,
    T is the set of terminals, which covers all leaves. Thus the set of
    key paths partitions the edges of the graph G.
    """
    key_paths = []

    # Given a tree, the path from a leaf to the nearest key vertex
    # is a key path, thus we start from a leaf, repeatedly prune
    # edges until we reach a key vertex

    def prune(tree):
        leaves = [node for node in tree.nodes if tree.degree(node) == 1]
        assert set(leaves).issubset(crucial_vertices)

        for v in leaves:
            path = [v]
            while True:
                v_neighbors = list(nx.all_neighbors(tree, v))
                if not v_neighbors:
                    # Now v is the last vertices in the tree,
                    # we return an empty graph to end the loop
                    return nx.Graph()

                w = v_neighbors[0]
                tree.remove_node(v)
                path.append(w)
                v = w

                # Stop pruning if we reach a key vertex
                if w in crucial_vertices:
                    break

            key_paths.append(path)

        return tree

    # Repeatedly prune the tree to find key paths, until there is no edges left
    t = g.copy()
    while t.edges:
        t = prune(t)

    return key_paths


def replace_path(g, s, old_path, new_path):
    new_s = s.copy()

    # Remove path edges
    new_s.remove_edges_from(pairwise(old_path))

    # Remove internal vertices
    new_s.remove_nodes_from(old_path[1:-1])

    # Add the edges from new_path
    new_s.add_weighted_edges_from((u, v, g.edges[u, v]['weight'])
                                  for u, v in pairwise(new_path))

    return new_s


def key_path_exchange(g, s, terminals, early_stop=True):
    """
    Determine whether it is possible to remove some key path and reconnect
    the two resulting components more cheaply.

    Initially, we have the Voronoi diagram with all vertices in S as bases.
    By removing a key path in S, we remove all the Voronoi cells with bases
    are vertices on the key path. Then repair the Voronoi diagram. After that,
    we proceed to find the best boundary edge re-connect the two components
    of S to obtain a new solution.
    """
    crucial_vertices = {node for node in s.nodes
                        if s.degree(node) >= 3 or node in terminals}

    key_paths = find_key_paths(s, crucial_vertices)
    voronoi = VoronoiDiagram(g, s.nodes)

    diff = 0
    key_path_to_del = None
    key_path_to_add = None

    for key_path in key_paths:
        key_path_weight = sum(g.edges[e]['weight'] for e in pairwise(key_path))

        temp_voronoi = voronoi.copy()

        # Temporarily remove the key path from the current solution, together
        # with the associated Voronoi cells, we need to repair the diagram
        # to find the partition formed by the two components of S
        s1, s2 = temp_voronoi.repair(g, s, key_path)

        # Now s1 and s2 form a partition of V_G, we iterate over
        # the boundary edges to look for an improvement
        best_boundary_edge, cost = min(((e, boundary_edge_cost(e, g.edges[e]['weight'], temp_voronoi))
                                        for e in nx.edge_boundary(g, s1, s2)),
                                       key=lambda x: x[1])

        best_path = base_path(*best_boundary_edge, temp_voronoi)

        if cost < key_path_weight:
            # Find the best improvement to make
            new_diff = key_path_weight - cost
            if new_diff > diff:
                diff = new_diff
                key_path_to_del = key_path
                key_path_to_add = best_path

            if early_stop:
                # Break the loop to return immediately,
                # without looking for the best improvement
                break

    # No improvement was found, we return the unmodified solution
    if key_path_to_add is None:
        return s

    return replace_path(g, s, key_path_to_del, key_path_to_add)


def key_vertex_elimination(g, s, terminals, early_stop=True):
    """
    Determine if there is a key vertex v such that the solution S' associated
    with C' = C \ {v} is cheaper, with C is the set of crucial vertices.

    The solution is found by applying DNH to C' for each removal.
    """
    key_vertices = {node for node in s.nodes
                    if s.degree(node) >= 3 and node not in terminals}
    s_weight = graph_weight(s)
    diff = 0
    best_s = None

    for key_vertex in key_vertices:
        k = key_vertices.copy()
        k.remove(key_vertex)

        # Find the solution associated to C \ {v}
        new_s = distance_network_heuristics(g, k | terminals)

        # We need to prune the solution, as there are non-terminals
        # in the distance network vertices
        new_s = prune_tree(new_s, terminals)

        new_s_weight = graph_weight(new_s)

        if new_s_weight < s_weight:
            if early_stop:
                # Return the better solution as soon as we find one
                return new_s

            # Find the best improvement to make
            new_diff = s_weight - new_s_weight
            if new_diff > diff:
                diff = new_diff
                best_s = new_s

    # No improvement was found, we return the unmodified solution
    if best_s is None:
        return s

    return best_s


def local_search(g, s, terminals, early_stop=True):
    from .steiner_vertices import steiner_vertices_insertion

    s = steiner_vertices_insertion(g, s, terminals, early_stop=early_stop)
    s = key_vertex_elimination(g, s, terminals, early_stop=early_stop)
    s = key_path_exchange(g, s, terminals, early_stop=early_stop)

    return s
