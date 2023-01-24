from highway_type import HighwayType

def add_penalties(G):
    turn_penalties = {}

    for node in G.nodes():
        straights = []
        outgoing_straights = {}
        turns = []

        # for each incoming road (edge) at an intersection (node),
        # determine which outgoing road is most likely the 'straight' road
        for incoming_edge in list(G.in_edges(node, data = True, keys = True)):
            in_edge = (incoming_edge[0], incoming_edge[1], incoming_edge[2])
            in_edge_data = incoming_edge[3]

            straight = None
            incoming_road_type = HighwayType(incoming_edge)