from streetnx import utils as street_utils
from fibheap import *

# calculate the travel time from the endpoint of the source_edge to the endpoint of the required_edges
def dijkstra(G, source_edge, required_edges, max_speed = 100):

    dur = dict.fromkeys(list(G.edges(keys=True)), float('inf'))
    prev = dict.fromkeys(list(G.edges(keys=True)), None)
    unvisited = set(required_edges)

    Q = makefheap()
    fheappush(Q, (0, source_edge))

    while Q.num_nodes > 0:
        heap_node = Q.extract_min()
        travel_time = heap_node.key[0]
        in_edge = heap_node.key[1]

        # Only remove the edge from the unvisited set
        # if the edge isn't the first edge in the heap
        if in_edge != source_edge:
            unvisited.discard(in_edge)
        
        # if we've visited all targets, we're done
        if len(unvisited) == 0:
            break

        for out_edge in G.out_edges(in_edge[1], keys = True):
            turn_penalty = G.turn_penalties[(in_edge, out_edge)]

            # Do not add a travel time if the in_edge is the source_edge
            # as we calculate the travel times between the endpoint of the source_edge to the endpoints of other edges
            # and thus if the in_edge is the source_edge, then no travel time is occured
            duration = travel_time + turn_penalty + (street_utils.get_travel_time(G, in_edge, max_speed) if in_edge != source_edge else 0)
            if duration < dur[out_edge]:
                dur[out_edge] = duration
                prev[out_edge] = in_edge
                fheappush(Q, (dur[out_edge], out_edge))

    # return the distances corresponding to the targets and all previous edges
    return {t: dur[t] for t in required_edges}, {t: prev[t] for t in prev}