import osmnx as ox
import math

from osmnx import utils

# set lane count of the edge using the assumptions when lanes are not specified,
# see https://wiki.openstreetmap.org/wiki/Key:lanes#Assumptions for more details
# a roundabout is assumed to have 1 lane, if not specified otherwise
def get_lane_count(edge):
    lane_count = None

    # number of lanes are not defined, so we use the lanes#assumptions
    if 'lanes' not in edge:        
        if edge["highway"] in ["motorway", "trunk"]:
            lane_count = 2
        else:
            lane_count = 1
    # number of lanes are defined, infer the count
    else:
        if edge["lanes"] == edge["lanes"]:
            # if edge is not oneway, lanes are divided equally between both directions
            if edge["oneway"] not in {"yes", True, 1, "true", "1"}:
                lane_count = int(int(edge["lanes"]) / 2)
            else:
                lane_count = int(edge["lanes"])
        else:
            lane_count = 1

    reversed = edge['reversed']
    lanes_backward = edge['lanes:backward'] if 'lanes:backward' in edge else float('nan')
    lanes_forward = edge['lanes:forward'] if 'lanes:forward' in edge else float('nan')
    
    # x == x checks if a variable is 'nan', returns False if it is nan
    # https://stackoverflow.com/questions/944700/how-can-i-check-for-nan-values
    # Thus only execute this piece of code if one of the two variables is not nan
    if (lanes_backward == lanes_backward or lanes_forward == lanes_forward):
        if reversed and lanes_backward == lanes_backward:
            # edge is reversed and lanes backward is specified
            lane_count = int(lanes_backward)
        elif reversed:
            # edge is reversed and lanes forward is specified (must be specified as lanes backward were not)
            lane_count = int(edge["lanes"]) - int(lanes_forward)
        elif not reversed and lanes_forward == lanes_forward:
            # edge is not reversed and lanes forward is specified
            lane_count = int(lanes_forward)
        else:
            # edge is not reversed and lanes backward is specified (must be specified as lanes forward were not)
            lane_count = int(edge["lanes"]) - int(lanes_backward)     

    return lane_count

def get_deadend_nodes_and_edges(G, depot_nodes, angle_treshold):

    # Remove nodes which only have 1 incoming or 1 outgoing edges,
    # as these nodes are absorbing and thus cannot be used in a routing solution
    dead_ends = [
        node for node in G.nodes() if len(G.in_edges(node)) == 0 or len(G.out_edges(node)) == 0
    ]

    # Remove nodes with only one incoming and one outgoing edge, and these two edges originate from the same nodes (i.e., (u,v,k) == (v,u,k))
    # I.e., u-turns 
    forbidden_u_turns = [
        node for node in G.nodes() if (
            len(G.in_edges(node)) == 1 
            and len(G.out_edges(node)) == 1 
            and list(G.in_edges(node, keys = True))[0][0] == list(G.out_edges(node, keys = True))[0][1] # u == v
            and list(G.in_edges(node, keys = True))[0][1] == list(G.out_edges(node, keys = True))[0][0] # v == u
            and list(G.in_edges(node, keys = True))[0][2] == list(G.out_edges(node, keys = True))[0][2] # keys should be equal
            and ox.utils_geo.angle(G, list(G.in_edges(node, keys = True, data = True))[0], list(G.out_edges(node, keys = True, data = True))[0]) < angle_treshold
        )
    ]

    # Find sharp turns in a graph by checking if the angle between incoming and outgoing edges is greater than 'angle_treshold' degrees.
    sharp_turns = []
    for node in G.nodes():
        found_sufficient_angle = False

        for in_edge in list(G.in_edges(node, keys = True, data = True)):
            for out_edge in list(G.out_edges(node, keys = True, data = True)):
                if abs(ox.utils_geo.angle(G, in_edge, out_edge)) >= angle_treshold:
                    found_sufficient_angle = True

        if not found_sufficient_angle:
            sharp_turns += [node]

    nodes_to_remove = list(set(dead_ends + forbidden_u_turns + sharp_turns))

    edges_to_remove = []
    for edge in G.edges(keys = True, data = True):

        # if the edge is adjacent to a depot, do not consider it for removal
        if edge[0] in depot_nodes or edge[1] in depot_nodes:
            continue

        # If the number of outgoing edges from the target node of the considered edge is 1,
        # check if the outgoing edge is equal to the considered edge or its angle is smaller than 40
        if len(G.out_edges(edge[1])) == 1:
            out_edge = list(G.out_edges(edge[1], data = True))[0]
            if abs(ox.utils_geo.angle(G, edge, out_edge)) < angle_treshold:
                edges_to_remove += [edge]
            
        # If the number of incoming edges from the starting node of the considered edge is 1,
        # check if the incoming edge is equal to the considered edge or its angle is smaller than 40
        if len(G.in_edges(edge[0])) == 1:
            in_edge = list(G.in_edges(edge[0], data = True))[0]
            if abs(ox.utils_geo.angle(G, in_edge, edge)) < angle_treshold:
                edges_to_remove += [edge]

    # make sure that the depot node is not removed
    for depot in depot_nodes:
        if depot in nodes_to_remove:
            nodes_to_remove.remove(depot)

    return (nodes_to_remove, edges_to_remove)

def remove_deadends(G, depot_nodes, angle_treshold = 40):
    """
    This function removes dead-end nodes and edges from the input graph G,
    using the provided list of depot nodes and angle treshold to determine dead-ends.
    
    Parameters:
    - G: A networkx graph object representing the input graph.
    - depot_nodes: A list of nodes in G that are considered as depots and hence will not be removed.
    - angle_treshold: An angle threshold value (in degrees) used to determine whether a edge pair is a dead-end or not.

    Returns:
    None. The input graph G is modified in place.
    """
    nodes, edges = get_deadend_nodes_and_edges(G, depot_nodes, angle_treshold)

    while not are_lists_empty((nodes, edges)):
        G.remove_nodes_from(nodes)
        G.remove_edges_from(edges)
        utils.log(f"Removed {len(nodes)} nodes and {len(edges)} edges.")

        nodes, edges = get_deadend_nodes_and_edges(G, depot_nodes, angle_treshold)

def are_lists_empty(pair):
    """
    Check if the lists in a pair data structure (i.e, a tuple of two lists) are both empty.

    Parameters:
    pair (tuple): A tuple of two lists.

    Returns:
    bool: True if both lists are empty, False otherwise.

    Example:
    >>> are_lists_empty(([], []))
    True
    >>> are_lists_empty(([1,2,3], []))
    False
    """
    return all(len(lst) == 0 for lst in pair)

def get_travel_time(G, edge, max_speed):
    edge_data = G.get_edge_data(*edge)
    if isinstance(edge_data["length"], list):
        distance = 0
        for i in range(len(edge_data["length"])):
            distance += edge_data["length"][i] / (min(max_speed, edge_data["speed_kph"][i]) / 3.6)
        return distance
    else:
        return edge_data["length"] / (edge_data["speed_kph"] / 3.6)
    
def is_nan(value):
    return math.isnan(value)