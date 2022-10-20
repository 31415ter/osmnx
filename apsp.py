import os
import time
import numpy as np
import multiprocessing as mp
import osmnx as ox
import pandas as pd
import geopandas as gpd

from osmnx import utils
from fibheap import *
from time import sleep
from random import random
from multiprocessing import Pool
from shapely.geometry import Point, LineString

def travelTime(G, edge, max_speed):
    edge_data = G.get_edge_data(*edge)
    if isinstance(edge_data["length"], list):
        distance = 0
        for i in range(len(edge_data["length"])):
            distance += edge_data["length"][i] / (min(max_speed, edge_data["speed_kph"][i]) / 3.6)
        return distance
    else:
        return edge_data["length"] / (edge_data["speed_kph"] / 3.6)

def turnPenalty(edge1, edge2):
    return 0

# calculate the travel time from the endpoint of the source_edge to the endpoint of the required_edges
def dijkstra(G, source_edge, required_edges, max_speed = 100):
    start = time.time()

    dist = dict.fromkeys(list(G.edges(keys=True)), float('inf'))
    dist[source_edge] = 0

    prev = dict.fromkeys(list(G.edges(keys=True)), None)

    unvisited = set(required_edges)
    unvisited.discard(source_edge)    

    Q = makefheap()
    fheappush(Q, (0, source_edge))

    while Q.num_nodes > 0:
        heap_node = Q.extract_min()
        travel_time = heap_node.key[0]
        in_edge = heap_node.key[1]
        unvisited.discard(in_edge)
        
        # if we've reached all targets, we're done
        if len(unvisited) == 0:
            break

        for out_edge in G.out_edges(in_edge, keys = True):
            turn_penalty = turnPenalty(in_edge, out_edge)
            alt = travel_time + turn_penalty + travelTime(G, out_edge, max_speed)
            if alt < dist[out_edge]:
                dist[out_edge] = alt
                prev[out_edge] = in_edge
                fheappush(Q, (dist[out_edge], out_edge))

    print(f"PPID {os.getppid()}->{os.getpid()} Completed in {round(time.time() - start,2)} seconds.")

    # return the distances corresponding to the targets and all prev where non None
    return {t: dist[t] for t in required_edges if t != source_edge}, {t: prev[t] for t in prev if (prev[t] is not None or t == source_edge)}

if __name__ == '__main__':
    # load df from parquet
    df_edges = pd.read_parquet("./data/Rotterdam_edges.parquet")
    df_nodes = pd.read_parquet("./data/Rotterdam_nodes.parquet")

    # convert df to gdf
    gdf_nodes = gpd.GeoDataFrame(df_nodes, geometry = gpd.points_from_xy(df_nodes.x, df_nodes.y))
    edge_geometry = df_edges["geometry"].apply(lambda x: LineString(x.tolist()))
    gdf_edges = gpd.GeoDataFrame(df_edges, geometry = edge_geometry)

    for col in gdf_edges.columns:
        if not gdf_edges[col].apply(lambda x: not isinstance(x, np.ndarray)).all():
            gdf_edges[col] = [value if not isinstance(value, np.ndarray) else value.tolist() for value in gdf_edges[col]]

    G = ox.graph_from_gdfs(gdf_nodes = gdf_nodes, gdf_edges = gdf_edges)

    # save graph for comparison purposes
    #ox.save_graph_geopackage(G, filepath="./data/Rotterdam_network_test.gpkg", directed = True)

    # def constructCoordinatePaths(G, from_edge : tuple, predecessors : dict, required_edges : list):
    #     # predecessors: keys are edges and values are previous edges
    #     paths_coordinates = {}
    #     # construct the coordinate path from the end of edge to the end of the required edge
    #     for required_edge in required_edges:
    #         if required_edge == from_edge:
    #             continue
    #         path = []
    #         edge = required_edge
    #         while edge is not None and edge != from_edge:
    #             prev_edge_data = G.get_edge_data(*edge)
    #             if "geometry" in prev_edge_data:
    #                 coords = list(prev_edge_data["geometry"].coords)
    #             else:
    #                 u = edge[0]
    #                 v = edge[1]
    #                 coords = [(G.nodes[u]["x"], G.nodes[u]["y"]), (G.nodes[v]["x"], G.nodes[v]["y"])]
    #             path = coords[1:] + path
    #             edge = predecessors[edge]
    #         path = [(G.nodes[from_edge[1]]["x"], G.nodes[from_edge[1]]["y"])] + path
    #         paths_coordinates[required_edge] = path
    #     return paths_coordinates

    required_edges = [
        (edge[0], edge[1], edge[2]) 
        for edge in G.edges(data=True, keys = True) 
        if set(edge[3]["highway"]).isdisjoint({"primary", "primary_link", "secondary", "secondary_link"})
    ]
    required_edges = required_edges[0:1000]

    distance_df = pd.DataFrame(index = required_edges, columns = required_edges)
    path_df = pd.DataFrame(index = required_edges, columns = required_edges)

    print("Start calculating distances")

    MAX_SPEED = 100

    start = time.time()
    args = [(G, edge, required_edges, MAX_SPEED) for edge in required_edges]
    with mp.Pool(processes=mp.cpu_count()) as pool:  
        results = pool.starmap(dijkstra, args)
    end = time.time()
    print("-------------------------------------------")
    print(f"With workers completed in {round(end-start,2)}")

    count = 0
    start = time.time()
    for edge in required_edges:
        count += 1
        # print(count)
        travel_times, predecessors = dijkstra(G, edge, required_edges, MAX_SPEED)

        # mask = (distance_df.index == edge)
        # distance_df.loc[mask, travel_times.keys()] = list(travel_times.values())
    end = time.time()
    print("-------------------------------------------")
    print(f"Without workers completed in {round(end-start,2)}")