import osmnx as ox
import networkx as nx
import pandas as pd

from streetnx import toolbox
from streetnx import utils as graph_utils
from osmnx import utils as ox_utils

FILE_PATH = "./data/"

USEFUL_TAGS_WAY = [
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
    "landuse",
    "width",
    "est_width",
    "junction",
    "turn:lanes",
    "turn:lanes:backward",
    "turn:lanes:forward",
    "lanes:forward",
    "lanes:backward"
]

CUSTOM_FILTER = (
    f'["highway"]["highway"~"motorway|trunk|primary|secondary|tertiary|unclassified"]'
    f'["access"!~"no|private"]'
)

HWY_SPEEDS = {  
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

def download_graph(
        city_names,
        useful_tags_way = USEFUL_TAGS_WAY,
        custom_filter = CUSTOM_FILTER,
    ):

    assert len(city_names) > 0, "At least one city should be specified."

    ox.config(
        log_file=True,
        log_console=True,
        use_cache=True,
        useful_tags_way=useful_tags_way
    )

    ox_utils.log("Start downloading the graph.")
    G = None
    for city_name in city_names:
        temp_graph = ox.graph_from_place(
            city_name,
            custom_filter = custom_filter,
            buffer_dist=2000,
            truncate_by_edge=True,
            simplify=False
        )
        if G is not None:
            G = nx.compose(temp_graph, G)
        else:
            G = temp_graph
    ox_utils.log("Finished downloading the graph.")

    return G

def process_graph(
        G,
        depot_dict,
        hwy_speeds=HWY_SPEEDS
    ):

    assert len(depot_dict) > 0, "At least one depot should be specified."

    G = ox.add_edge_speeds(G, hwy_speeds, fallback = 30)
    ox_utils.log("Added edge speeds to the graph.")

    G = toolbox.graph_inserted_pois(G, depot_dict)
    ox_utils.log("Finished inserting depots into the graph.")

    lane_counts = {
        (from_node, to_node, key) : graph_utils.get_lane_count(data) 
        for (from_node, to_node, key, data) 
        in G.edges(keys = True, data=True)
    }
    nx.set_edge_attributes(G, name="lanes", values=lane_counts)
    ox_utils.log("Set lane count of edges.")
        
    G = ox.simplify_graph(G, allow_lanes_diff=False)

    gdf_nodes, gdf_edges = ox.graph_to_gdfs(G)
    depot_nodes = gdf_nodes[gdf_nodes['highway'] == 'poi'].index.tolist()

    ox_utils.log("Start removing deadends")
    graph_utils.remove_deadends(G, depot_nodes)
    ox_utils.log("Finished removing deadends")

    G = ox.simplify_graph(G, allow_lanes_diff=False)

    return G

def save_graph(G, name):
    ox_utils.log("Start saving the graph.")
    ox.save_graphml(G, filepath=FILE_PATH + name + ".graphml")
    ox.save_graph_geopackage(G, filepath=FILE_PATH + name + ".gpkg", directed = True)
    ox_utils.log("Finished saving the graph.")

def load_graph(name):
    ox_utils.log("Start reading the graph.")
    G = ox.load_graphml(filepath=FILE_PATH + name + ".graphml")
    ox_utils.log("Finished reading the graph.")
    return G

def load_required_edges(G):
    # TODO create function to download required edges from ARCGIS?

    required_edges = [
        (u,v,k)
        for u,v,k,d 
        in G.edges(keys=True, data=True) 
        if d['highway'] in ["primary", "projected_footway"] # , "primary_link", "secondary", "secondary_link"
    ]

    return required_edges[-50:]

def save_shortest_paths(distances, paths, name: str):
    distances.to_parquet(f"./data/" + name + "_distances.parquet.gzip", engine='pyarrow', compression='GZIP')
    paths.to_parquet(f"./data/" + name + "_paths.parquet.gzip", engine='pyarrow', compression='GZIP')

def load_shortest_paths(name: str):
    distances = pd.read_parquet(f"./data/" + name + "_distances.parquet.gzip", engine='pyarrow')
    paths = pd.read_parquet(f"./data/" + name + "_paths.parquet.gzip", engine='pyarrow')
    return distances, paths

def save_route(route_map, name: str):
    route_map.save(outfile= "./data/" + name + ".html")

