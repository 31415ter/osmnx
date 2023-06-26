import time
import multiprocessing as mp
import pandas as pd

from multiprocessing import Manager
from osmnx import utils as ox_utils
from streetnx import utils as snx_utils
from fibheap import *

# calculate the travel time from the endpoint of the source_edge to the endpoint of the required_edges
def all_paths_dijkstra(G, source_edge, required_edges, counter, start_time, max_speed = 100):

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
            turn_type = G.turns[(in_edge, out_edge)]
            if in_edge == source_edge and travel_time == 0:
                turn_type = G.required_turns[(in_edge, out_edge)]
            turn_penalty = turn_type.value * G.gamma

            # Do not add a travel time if the in_edge is the source_edge
            # as we calculate the travel times between the endpoint of the source_edge to the endpoints of other edges
            # and thus if the in_edge is the source_edge, then no travel time is occured
            duration = travel_time + turn_penalty + (snx_utils.get_edge_travel_time(G, in_edge, max_speed) if in_edge == source_edge and travel_time != 0 else 0)
            if duration < dur[out_edge]:
                dur[out_edge] = duration
                prev[out_edge] = in_edge
                fheappush(Q, (dur[out_edge], out_edge))

    counter.value += 1
    if counter.value % 10 == 0:
        finish_time = time.time()
        est_finish_time = start_time + (finish_time - start_time) / counter.value * len(required_edges)
        time_remaining = est_finish_time - finish_time

        hours, remainder = divmod(time_remaining, 3600)
        minutes, seconds = divmod(remainder, 60)

        print(f"Completed {counter.value} of {len(required_edges)} shortest paths, est. time remaining: {'{:02d}:{:02d}:{:02d}'.format(int(hours), int(minutes), int(seconds))}")

    # return the distances corresponding to the targets and all previous edges
    return {t: dur[t] for t in required_edges}, {t: prev[t] for t in prev}


# WHAT DOES nodes VARIABLE DO?
def construct_paths(G, source_edge: tuple, predecessors: dict, required_edges: list, counter, start_time, nodes = True):
    # predecessors: keys are edges and values are previous edges
    paths_coordinates = []
    paths_nodes = []
    # construct the coordinate path from the end of source_edge to the start of the required edge
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

    counter.value += 1
    if counter.value % 10 == 0:
        finish_time = time.time()
        est_finish_time = start_time + (finish_time - start_time) / counter.value * len(required_edges)
        time_remaining = est_finish_time - finish_time

        hours, remainder = divmod(time_remaining, 3600)
        minutes, seconds = divmod(remainder, 60)

        print(f"Completed {counter.value} of {len(required_edges)} construction paths, est. time remaining: {'{:02d}:{:02d}:{:02d}'.format(int(hours), int(minutes), int(seconds))}")

    if nodes: 
        return paths_nodes        
    else: 
        return paths_coordinates

def get_all_shortest_paths(G, required_edges_df, cores, name, size = 500, max_speed = 100):

    required_edges = required_edges_df.index.values.tolist()

    import math

    for i in range(math.ceil(len(required_edges) / size)):
        start_index = i * size
        end_index = start_index + size
        end_index = end_index if end_index - len(required_edges) < 0 else len(required_edges)

        # setup datastructure to hold results
        distance_df = pd.DataFrame(index = required_edges[start_index:end_index], columns = required_edges)
        predecessors_df = pd.DataFrame(index = required_edges[start_index:end_index], columns = required_edges)

        ox_utils.log(f"Start calculating distances with {cores} cores")
        manager = Manager()
        counter = manager.Value('i', 0)
        start = time.time()
        args = [
            (G, edge, required_edges, counter, start, max_speed) 
            for edge in required_edges[start_index:end_index]
        ]
        with mp.Pool(processes=cores) as pool:
            results = pool.starmap(all_paths_dijkstra, args)
        end = time.time()
        ox_utils.log(f"With {cores} cores, shortest paths completed in {round(end-start,2)}")

        for i in range(len(required_edges[start_index:end_index])):
            distance_df.iloc[i] = list(results[i][0].values())    

        counter = manager.Value('i', 0)
        start = time.time()
        args = [
            (G, edge, results[required_edges.index(edge) - start_index][1], required_edges, counter, start) 
            for edge in required_edges[start_index:end_index]
        ]
        with mp.Pool(processes=cores) as pool:
            results = pool.starmap(construct_paths, args)
        end = time.time()
        ox_utils.log(f"With {mp.cpu_count()} cores, paths construction completed in {round(end-start,2)}")

        for i in range(len(required_edges[start_index:end_index])):
            predecessors_df.iloc[i] = results[i]

        distance_df.columns = [str(i) for i in range(len(required_edges))]
        predecessors_df.columns = [str(i) for i in range(len(required_edges))]

        assert predecessors_df.index.values.tolist()  == required_edges_df[start_index:end_index].index.values.tolist(), "Not matching indices"
        assert distance_df.index.values.tolist() == required_edges_df[start_index:end_index].index.values.tolist(), "Not matching indices"

        distance_df.to_parquet("./data/" + name + f"_distances_{start_index}_{end_index-1}.parquet.gzip", engine='pyarrow', compression='GZIP')
        predecessors_df.to_parquet("./data/" + name + f"_predecessors_{start_index}_{end_index-1}.parquet.gzip", engine='pyarrow', compression='GZIP')

    return distance_df, predecessors_df
