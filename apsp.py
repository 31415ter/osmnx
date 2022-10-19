import pandas as pd
import warnings
import numpy as np
import networkx as nx

import osmnx as ox

from shapely.errors import ShapelyDeprecationWarning
from shapely.geometry import LineString
from osmnx import utils

from fibheap import *

warnings.filterwarnings("ignore", category=ShapelyDeprecationWarning) 
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.filterwarnings("ignore", category=np.VisibleDeprecationWarning) 

ox.config(log_file=True, log_console=True, use_cache=True)

cf = (
    f'["highway"]["highway"~"motorway|trunk|primary|secondary|tertiary|unclassified"]'
    f'["access"!~"no|private"]'
)

hwy_speeds = {  
    'motorway': 100,
    'motorway_link': 100,
    'trunk': 70,
    'trunk_link': 70,
    'primary': 50,
    'primary_link': 50,
    'secondary': 50,
    'secondary_link': 50,
    'tertiary': 50,
    'tertiary_link': 50,
    'unclassified': 30,
    'residential': 30,
    'living_street': 5
}

rotterdam_graph = ox.graph_from_place("Rotterdam", custom_filter = cf, buffer_dist=2000, truncate_by_edge=True, simplify=False)
hoogvliet_graph = ox.graph_from_place("Hoogvliet", custom_filter = cf, buffer_dist=3000, truncate_by_edge=True, simplify=False)
schiedam_graph = ox.graph_from_place("Schiedam", custom_filter = cf, buffer_dist=1000, truncate_by_edge=True, simplify=False)

G = nx.compose(rotterdam_graph, hoogvliet_graph)
G = nx.compose(G, schiedam_graph)

# Remove any edges that are not connected to the needed_types
def remove_bad_connected_edges(
    G, 
    needed_types = ["motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link", "secondary", "secondary_link"]
):
    removed_nodes = []

    for node in list(G.nodes):
        in_edges = [d for u,v,d in G.in_edges(node, data = True) if d["highway"] in needed_types]
        out_edges = [d for u,v,d in G.out_edges(node, data = True) if d["highway"] in needed_types]
        if len(in_edges) == 0 or len(out_edges) == 0:
            removed_nodes.append(node)

    G.remove_nodes_from(removed_nodes)

# ox.save_graph_geopackage(G, filepath="./data/Rotterdam_network_0.gpkg", directed = True)

# remove_bad_connected_edges(G)

# ox.save_graph_geopackage(G, filepath="./data/Rotterdam_network_1.gpkg", directed = True)

G = ox.add_edge_speeds(G, hwy_speeds, fallback = 30)
G = ox.simplify_graph(G, allow_lanes_diff=False)
    
removed_nodes_list = []
removed_nodes = True

utils.log("Begin removing deadends...")

while removed_nodes:
    # Remove nodes which only have incoming or outgoing edges
    dead_ends = [
        node for node in G.nodes() if len(G.in_edges(node)) == 0 or len(G.out_edges(node)) == 0
    ]

    # Remove nodes with only one incoming and one outgoing edge, and these two edges originate from the same nodes (i.e., (u,v,k) == (v,u,k))
    forbidden_u_turns = [
        node for node in G.nodes() if (
            len(G.in_edges(node)) == 1 
            and len(G.out_edges(node)) == 1 
            and list(G.in_edges(node, keys = True))[0][0] == list(G.out_edges(node, keys = True))[0][1] # u == v
            and list(G.in_edges(node, keys = True))[0][1] == list(G.out_edges(node, keys = True))[0][0] # v == u
            and list(G.in_edges(node, keys = True))[0][2] == list(G.out_edges(node, keys = True))[0][2] # keys should be equal
        )
    ]

    sharp_turns = [
        node for node in G.nodes() if (
            len(G.in_edges(node)) == 1 
            and len(G.out_edges(node)) == 1
            and abs(ox.utils_geo.angle(G, list(G.in_edges(node, data = True))[0], list(G.out_edges(node, data = True))[0])) < 40
        )
    ]

    nodes_to_remove = list(set(dead_ends + forbidden_u_turns + sharp_turns))

    if len(nodes_to_remove) == 0:
        removed_nodes = False

    removed_nodes_list += nodes_to_remove
    G.remove_nodes_from(nodes_to_remove)

utils.log(f"Removed {len(removed_nodes_list)} deadends.")

G = ox.simplify_graph(G, allow_lanes_diff=False)

# ox.save_graph_geopackage(G, filepath="./data/Rotterdam_network_2.gpkg", directed = True)

# travel time in seconds
# length is in meters and speed is in km/h
# thus to calculate the travel time in seconds, we need to convert the speed to m/s
def travelTime(edge, max_speed):
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
            alt = travel_time + turn_penalty + travelTime(out_edge, max_speed)
            if alt < dist[out_edge]:
                dist[out_edge] = alt
                prev[out_edge] = in_edge
                fheappush(Q, (dist[out_edge], out_edge))

    # return the distances corresponding to the targets and all prev where non None
    return {t: dist[t] for t in required_edges if t != source_edge}, {t: prev[t] for t in prev if (prev[t] is not None or t == source_edge)}

def constructCoordinatePaths(G, from_edge : tuple, predecessors : dict, required_edges : list):
    # predecessors: keys are edges and values are previous edges
    paths_coordinates = {}
    # construct the coordinate path from the end of edge to the end of the required edge
    for required_edge in required_edges:
        if required_edge == from_edge:
            continue
        path = []
        edge = required_edge
        while edge is not None and edge != from_edge:
            prev_edge_data = G.get_edge_data(*edge)
            if "geometry" in prev_edge_data:
                coords = list(prev_edge_data["geometry"].coords)
            else:
                u = edge[0]
                v = edge[1]
                coords = [(G.nodes[u]["x"], G.nodes[u]["y"]), (G.nodes[v]["x"], G.nodes[v]["y"])]
            path = coords[1:] + path
            edge = predecessors[edge]
        path = [(G.nodes[from_edge[1]]["x"], G.nodes[from_edge[1]]["y"])] + path
        paths_coordinates[required_edge] = path
    return paths_coordinates

required_edges = [
    (edge[0], edge[1], edge[2]) 
    for edge in G.edges(data=True, keys = True) 
    if edge[3]["highway"] in ["primary", "primary_link", "secondary", "secondary_link"]
]

distance_df = pd.DataFrame(index = required_edges, columns = required_edges)
path_df = pd.DataFrame(index = required_edges, columns = required_edges)

utils.log("Start calculating distances")




count = 0
for edge in required_edges:
    count += 1
    utils.log(f"{count} / {len(required_edges)}")
    travel_times, predecessors = dijkstra(G, edge, required_edges, max_speed = 100)

    mask = (distance_df.index == edge)
    distance_df.loc[mask, travel_times.keys()] = list(travel_times.values())

    paths = constructCoordinatePaths(G, edge, predecessors, required_edges)

    # path_df.loc[mask, paths.keys()] = list(paths.values())


# distance_df.to_pickle('./data/distance_df.pkl')
# path_df.to_pickle('./data/path_df.pkl')

# import geopandas as gpd
# gdf3 = gpd.GeoDataFrame(geometry=list(linestrings.values()), crs = 'epsg:4326')  # Note GeoDataFrame geometry requires a list
# gdf3.to_file(filename='./data/nodes.shp', driver='ESRI Shapefile')

# print("stop")