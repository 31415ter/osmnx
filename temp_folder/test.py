from itertools import count
import os
import time
import numpy as np
import pandas as pd
import networkx as nx
import osmnx as ox
import geopandas as gpd

from streetnx import poi_insertion 
from osmnx import utils
from fibheap import *
from shapely.geometry import LineString

import warnings
warnings.filterwarnings('ignore')

tags = {'amenity': ['pub', 'cafe', 'bar']}#, 'restaurant']} # 'fast_food', 'restaurant'

useful_tags_way = [
    "bridge",
    "tunnel",
    "oneway",
    "lanes",
    "ref",
    "name",
    "highway",
    "maxspeed",
    "service",
    "access",
    "area",
    "bicycle"
]

cf_1 = (
    f'["highway"]["highway"!~"pedestrian|footway|service|busway|motor|steps|platform|path|track|bridleway|construction"]'
    f'["bicycle"!~"^no|private|use_sidepath$"]["access"!~"no|private"]["area"!~"yes"]'
)

cf_2 = (f'["highway"]["highway"~"pedestrian|footway|service|busway|motor|steps|platform|path|track|bridleway|construction"]'
        f'["bicycle"~"yes|designated|permissive|dismount"]["access"!~"no|private"]["area"!~"yes"]')

cf_3 = (f'["highway"]["highway"="service"]'
        f'["bicycle"!~"^no|private|use_sidepath$"]["access"!~"no|private"]["area"!~"yes"]')

ox.config(log_file=True, log_console=True, use_cache=True, useful_tags_way=useful_tags_way)

city = "Rotterdam"

G1 = ox.graph_from_place(city, custom_filter=cf_1, retain_all=True, simplify=False)
G2 = ox.graph_from_place(city, custom_filter=cf_2, retain_all=True, simplify=False)
G3 = ox.graph_from_place(city, custom_filter=cf_3, retain_all=True, simplify=False)

G = nx.compose(G1, G2)
G = nx.compose(G3, G)
G = ox.utils_graph.get_largest_component(G) # do not consider disconnected components

hwy_speeds = {  
    'motorway': 15,
    'motorway_link': 15,
    'trunk': 15,
    'trunk_link': 15,
    'primary': 15,
    'primary_link': 15,
    'secondary': 15,
    'secondary_link': 15,
    'tertiary': 15,
    'tertiary_link': 15,
    'unclassified': 15,
    'residential': 15,
    'cycleway': 15,
    'footway': 5,
    'path': 5,
    'pedestrian': 5,
    'service': 15,
    'steps': 5,
    'proposed': 5
}

G = ox.add_edge_speeds(G, hwy_speeds, fallback = 15)
G = ox.simplify_graph(G, allow_lanes_diff=True)

G = poi_insertion.graph_with_pois_inserted(G, city, tags)

utils.log("Begin removing deadends...")
removed_nodes_list = []
removed_nodes = True
while removed_nodes:
    # Remove nodes which only have incoming or outgoing edges
    dead_ends = [
        node for node in G.nodes() if len(G.in_edges(node)) == 0 or len(G.out_edges(node)) == 0
    ]
    nodes_to_remove = list(set(dead_ends))

    if len(nodes_to_remove) == 0:
        removed_nodes = False

    removed_nodes_list += nodes_to_remove
    G.remove_nodes_from(nodes_to_remove)

utils.log(f"Removed {len(removed_nodes_list)} deadends.")

ox.save_graph_geopackage(G, filepath="./data/" + city + "_latest.gpkg", directed = True)

gdf_nodes, gdf_edges = ox.graph_to_gdfs(G)
for col in gdf_edges.columns:
    if col == "geometry":
        continue
    # check if any of the values within the column col are not a list
    if not gdf_edges[col].apply(lambda x: not isinstance(x, list)).all():
        gdf_edges[col] = [[value] if not isinstance(value, list) else value for value in gdf_edges[col]]

gdf_nodes["geometry"] = gdf_nodes["geometry"].apply(lambda x : list(x.coords))
gdf_edges["geometry"] = gdf_edges["geometry"].apply(lambda x : list(x.coords))

gdf_edges["osmid"] = gdf_edges["osmid"].apply(lambda x : [int(x) for x in str(x[0]).split("_")] if ("_" in str(x)) else x)

gdf_nodes.to_parquet("./data/Rotterdam_pois_nodes.parquet", engine='pyarrow')
gdf_edges.to_parquet("./data/Rotterdam_pois_edges.parquet", engine='pyarrow')

# load df from parquet
df_edges = pd.read_parquet("./data/Rotterdam_pois_edges.parquet")
df_nodes = pd.read_parquet("./data/Rotterdam_pois_nodes.parquet")

# convert df to gdf
gdf_nodes = gpd.GeoDataFrame(df_nodes, geometry = gpd.points_from_xy(df_nodes.x, df_nodes.y))
edge_geometry = df_edges["geometry"].apply(lambda x: LineString(x.tolist()))
gdf_edges = gpd.GeoDataFrame(df_edges, geometry = edge_geometry)

# convert np.arrays to lists when applicable
for col in gdf_edges.columns:
    if not gdf_edges[col].apply(lambda x: not isinstance(x, np.ndarray)).all():
        gdf_edges[col] = [value if not isinstance(value, np.ndarray) else value.tolist() for value in gdf_edges[col]]

# create graph from gdf
G = ox.graph_from_gdfs(gdf_nodes = gdf_nodes, gdf_edges = gdf_edges)

required_nodes = [44409833] + [node for (node, data) in G.nodes(data = True) if 'amenity' in data and data['amenity'] == data['amenity']]

def travelTime(G, edge, max_speed):
    edge_data = G.get_edge_data(*edge)
    if isinstance(edge_data["length"], list):
        distance = 0
        for i in range(len(edge_data["length"])):
            distance += edge_data["length"][i] / (min(max_speed, edge_data["speed_kph"][i]) / 3.6)
        return distance
    else:
        if isinstance(edge_data["speed_kph"], list):
            return edge_data["length"] / (min(max_speed, edge_data["speed_kph"][0]) / 3.6)
        return edge_data["length"] / (edge_data["speed_kph"] / 3.6)

def dijkstra(G, source, required_nodes):
    start = time.time()

    dist = dict.fromkeys(list(G.nodes()), float('inf'))
    dist[source] = 0

    prev = dict.fromkeys(list(G.nodes()), None)

    unvisited = set(required_nodes)
    unvisited.discard(source)    

    Q = makefheap()
    fheappush(Q, (0, source))

    while Q.num_nodes > 0:
        heap_node = Q.extract_min()
        travel_time = heap_node.key[0]
        node = heap_node.key[1]
        unvisited.discard(node)
        
        # if we've reached all targets, we're done
        if len(unvisited) == 0:
            break

        for out_edge in G.out_edges(node, keys = True):
            next_node = out_edge[1]
            alt = travel_time + travelTime(G, out_edge, max_speed=15)
            if alt < dist[next_node]:
                dist[next_node] = alt
                prev[next_node] = node
                fheappush(Q, (dist[next_node], next_node))

    # return the distances corresponding to the targets and all prev where non None
    return {t: dist[t] for t in required_nodes if t != source}, {t: prev[t] for t in prev if (prev[t] is not None or t == source)}

def constructCoordinatePaths(source_node, predecessors : dict, required_nodes : list):
    # predecessors: keys are edges and values are previous edges
    paths_coordinates = {}
    # construct the coordinate path from the end of edge to the end of the required edge
    for required_node in required_nodes:
        if required_node == source_node:
            continue
        path = [required_node]
        node = required_node
        while predecessors[node] is not None:
            path = [predecessors[node]] + path
            node = predecessors[node]
        paths_coordinates[required_node] = path
    return paths_coordinates

distance_df = pd.DataFrame(index = required_nodes, columns = required_nodes)
path_df = pd.DataFrame(index = required_nodes, columns = required_nodes)

counter = 0
for source in required_nodes:
    counter += 1
    print(f"{counter}/{len(required_nodes)}")
    results, predecessors = dijkstra(G, source, required_nodes)
    mask = (distance_df.index == source)
    distance_df.loc[mask, results.keys()] = list(results.values())
    paths = constructCoordinatePaths(source, predecessors, required_nodes)
    path_df.loc[mask, paths.keys()] = list(paths.values())

distance_df.columns = [str(col) for col in distance_df.columns]
path_df.columns = [str(col) for col in path_df.columns]

distance_df.to_parquet("./data/Rotterdam_pois_distance.parquet", engine='pyarrow')
path_df.to_parquet("./data/Rotterdam_pois_path.parquet", engine='pyarrow')