import osmnx as ox
import networkx as nx

from streetnx import toolbox
from streetnx import utils as graph_utils
from osmnx import utils

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

    utils.log("Start loading the graph.")
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
    utils.log("Finished loading the graph.")

    return G

def process_graph(
        G,
        depot_dict,
        hwy_speeds=HWY_SPEEDS
    ):

    assert len(depot_dict) > 0, "At least one depot should be specified."

    G = ox.add_edge_speeds(G, hwy_speeds, fallback = 30)
    utils.log("Added edge speeds to the graph.")

    G = toolbox.graph_inserted_pois(G, depot_dict)
    utils.log("Finished inserting depots into the graph.")

    lane_counts = {
        (from_node, to_node, key) : graph_utils.get_lane_count(data) 
        for (from_node, to_node, key, data) 
        in G.edges(keys = True, data=True)
    }
    nx.set_edge_attributes(G, name="lanes", values=lane_counts)
    utils.log("Set lane count of edges.")
        
    G = ox.simplify_graph(G, allow_lanes_diff=False)

    gdf_nodes, gdf_edges = ox.graph_to_gdfs(G)
    depot_nodes = gdf_nodes[gdf_nodes['highway'] == 'poi'].index.tolist()

    utils.log("Start removing deadends")
    graph_utils.remove_deadends(G, depot_nodes)
    utils.log("Finished removing deadends")

    G = ox.simplify_graph(G, allow_lanes_diff=False)

    return G

def save_graph(G, name):
    ox.save_graphml(G, filepath=FILE_PATH + name + ".graphml")
    ox.save_graph_geopackage(G, filepath=FILE_PATH + name + ".gpkg", directed = True)

def load_graph(name):
    return ox.load_graphml(filepath=FILE_PATH + name + ".graphml")