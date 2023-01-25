import time
import multiprocessing as mp
import pandas as pd

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
            turn_penalty = G.turns[(in_edge, out_edge)].value * G.gamma

            # Do not add a travel time if the in_edge is the source_edge
            # as we calculate the travel times between the endpoint of the source_edge to the endpoints of other edges
            # and thus if the in_edge is the source_edge, then no travel time is occured
            duration = travel_time + turn_penalty + (street_utils.get_travel_time(G, in_edge, max_speed) if in_edge != source_edge else 0)
            if duration < dur[out_edge]:
                dur[out_edge] = duration
                prev[out_edge] = in_edge
                fheappush(Q, (dur[out_edge], out_edge))

    index = required_edges.index(source_edge)
    if index % 100 == 0 and index != 0:
        print(f"Completed asps for {index} of {len(required_edges)}")

    # return the distances corresponding to the targets and all previous edges
    return {t: dur[t] for t in required_edges}, {t: prev[t] for t in prev}

def construct_paths(G, source_edge: tuple, predecessors: dict, required_edges: list, nodes = True):
    # predecessors: keys are edges and values are previous edges
    paths_coordinates = []
    paths_nodes = []
    # construct the coordinate path from the end of edge to the start of the required edge
    for required_edge in required_edges:
        path = []
        nodes_path = []
        edge = predecessors[required_edge]
        while edge != source_edge and edge != None:
            prev_edge_data = G.get_edge_data(*edge)
            if "geometry" in prev_edge_data:
                coords = list(prev_edge_data["geometry"].coords)
                coords = [coords[i] for i in range(len(coords)) if i == 0 or coords[i] != coords[i-1]]
            else:
                u = edge[0]
                v = edge[1]
                coords = [(G.nodes[u]["x"], G.nodes[u]["y"]), (G.nodes[v]["x"], G.nodes[v]["y"])]
            path = coords[1:] + path
            nodes_path = [edge[1]] + nodes_path
            edge = predecessors[edge]
        path = [(G.nodes[source_edge[1]]["x"], G.nodes[source_edge[1]]["y"])] + path
        nodes_path = [source_edge[1]] + nodes_path
        paths_coordinates.append(path)
        paths_nodes.append(nodes_path)
    return paths_coordinates if nodes == False else paths_nodes

def get_shortest_paths(G, required_edges, max_speed = 100):
    depot_nodes = [n for n,d in G.nodes(data=True) if d['highway'] == 'poi']

    # setup datastructure to hold results
    distance_df_workers = pd.DataFrame(index = required_edges, columns = required_edges)
    path_df_workers = pd.DataFrame(index = required_edges, columns = required_edges)

    print("Start calculating distances")
    print(f"{len(required_edges)}")

    start = time.time()
    args = [(G, edge, required_edges, max_speed) for edge in required_edges]
    with mp.Pool(processes=mp.cpu_count()) as pool:
        results = pool.starmap(dijkstra, args)
    end = time.time()
    print("-------------------------------------------")
    print(f"With workers completed in {round(end-start,2)}")

    for i in range(len(required_edges)):
        mask = (distance_df_workers.index == required_edges[i])
        distance_df_workers.loc[mask, results[i][0].keys()] = list(results[i][0].values())

    start = time.time()
    args = [
        (G, edge, results[required_edges.index(edge)][1], required_edges) 
        for edge in required_edges 
        if edge[1] not in depot_nodes # skip over edges that are going into the depot
    ] 
    with mp.Pool(processes=mp.cpu_count()) as pool:
        results = pool.starmap(construct_paths, args)
    end = time.time()
    print("-------------------------------------------")
    print(f"With workers completed in {round(end-start,2)}")

    for i in range(len(args)):
        edge = args[i][1]
        mask = (distance_df_workers.index == edge)
        path_df_workers.loc[mask, :] = results[i]

    distance_df_workers.columns = [str(i) for i in range(len(required_edges))]
    path_df_workers.columns = [str(i) for i in range(len(required_edges))]

    return distance_df_workers, path_df_workers