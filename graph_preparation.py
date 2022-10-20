import pandas as pd
import warnings
import numpy as np
import networkx as nx

import osmnx as ox

from shapely.errors import ShapelyDeprecationWarning
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

# remove_bad_connected_edges(G)

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

ox.save_graph_geopackage(G, filepath="./data/Rotterdam_network.gpkg", directed = True)

utils.log("Save graph to parquet")

gdf_nodes, gdf_edges = ox.graph_to_gdfs(G)
for col in gdf_edges.columns:
    if col == "geometry":
        continue
    # check if any of the values within the column col are not a list
    if not gdf_edges[col].apply(lambda x: not isinstance(x, list)).all():
        gdf_edges[col] = [[value] if not isinstance(value, list) else value for value in gdf_edges[col]]


gdf_edges["geometry"] = gdf_edges["geometry"].apply(lambda x : list(x.coords))
gdf_nodes["geometry"] = gdf_nodes["geometry"].apply(lambda x : list(x.coords))

gdf_nodes.to_parquet("./data/Rotterdam_nodes.parquet", engine='pyarrow')
gdf_edges.to_parquet("./data/Rotterdam_edges.parquet", engine='pyarrow')