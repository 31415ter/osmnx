import os

import osmnx as ox
import networkx as nx
import pandas as pd
import numpy as np
import streetnx as snx

from streetnx import poi_insertion
from streetnx import utils as graph_utils
from osmnx import utils as ox_utils
from osmnx import geocoder

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

ALL_ROAD_TYPES = (
    f'["highway"]["highway"~"motorway|trunk|primary|secondary|tertiary|unclassified|residential|living_street"]'
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
'cycleway': 15,
'living_street': 5
}

def download_graph(
        city_names,
        useful_tags_way = USEFUL_TAGS_WAY,
        custom_filter = None,
    ):

    assert len(city_names) > 0, "At least one city should be specified."

    ox_utils.log("Set tags to use.")
    ox.settings.useful_tags_way=useful_tags_way

    ox_utils.log("Start downloading the graph.")
    G = None
    for city_name in city_names:
        temp_graph = ox.graph_from_place(
            city_name,
            custom_filter = custom_filter if custom_filter is not None else ALL_ROAD_TYPES,
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

# TODO WRONG PLACE, IS NOT SAVING OR LOADING ANYTHING...
def process_deadends(
        G,
        depot_dict,
        hwy_speeds=HWY_SPEEDS
    ):

    assert len(depot_dict) > 0, "At least one depot should be specified."

    G = ox.add_edge_speeds(G, hwy_speeds, fallback = 30)
    ox_utils.log("Added edge speeds to the graph.")

    G = poi_insertion.graph_inserted_pois(G, depot_dict)
    ox_utils.log("Finished inserting depots into the graph.")

    lane_counts = {
        (from_node, to_node, key) : graph_utils.get_lane_count(data) 
        for (from_node, to_node, key, data) 
        in G.edges(keys = True, data=True)
    }
    nx.set_edge_attributes(G, name="lanes", values=lane_counts)
    ox_utils.log("Set lane count of edges.")

    empty_lane_edges = [edge for edge in G.edges(keys = True, data = True) if edge[3]['lanes'] <= 0]
    G.remove_edges_from(empty_lane_edges)
    ox_utils.log(f"Removed {len(empty_lane_edges)} lanes with empty lanes.")
    
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

def load_required_edges(G, required_cities, required_highway_types ,buffer_dist = 500):
    nodes, edges = ox.utils_graph.graph_to_gdfs(G)

    def check_highway(value, highway_types):
        if isinstance(value, list):
            for item in value:
                for type in highway_types:
                    if type in item:
                        return True
            return False
        else:
            for type in highway_types:
                if type in value:
                    return True
            else: return False

    mask = edges['highway'].apply(check_highway, highway_types = ["projected_footway"])
    required_edges_df = edges.loc[mask, ["lanes", "length", "lanes:forward", "lanes:backward", "turn:lanes", "speed_kph", "oneway", "geometry"]]

    if required_cities != None and len(required_cities) > 0:
        union_polygon = None
        for city in required_cities:
            city_gdf = geocoder.geocode_to_gdf(
                city, which_result=None, buffer_dist=buffer_dist
            )
            city_polygon = city_gdf["geometry"].unary_union

            if not union_polygon:
                union_polygon = city_polygon
            else:
                union_polygon = union_polygon.union(city_polygon)
		        
        mask = edges['geometry'].apply(lambda x: x.within(union_polygon))
        edges = edges.loc[mask]

        mask = edges.loc[mask, 'highway'].apply(check_highway, highway_types = required_highway_types)
        temp_required_edges_df = edges.loc[mask, ["lanes", "length", "lanes:forward", "lanes:backward", "turn:lanes", "speed_kph", "oneway", "geometry"]]
        required_edges_df = pd.concat([required_edges_df, temp_required_edges_df])
        required_edges_df = required_edges_df[~required_edges_df.index.duplicated(keep='first')]

    for col in required_edges_df.columns:
        
        # Adjust geometry column to be the average x,y coordinates of all available coordinates
        # the average x,y coordinates are used in the routing optimization
        if col == "geometry":
            xy = [value.coords.xy for value in required_edges_df[col]]
            average_xy = [(np.average(x), np.average(y)) for x,y in xy]
            required_edges_df['average_geometry'] = average_xy
        
        # check if any of the values within the column col are not a list
        # while others are, then put everything into lists
        elif not required_edges_df[col].apply(lambda x: not isinstance(x, list)).all():
            required_edges_df[col] = [[value] if not isinstance(value, list) else value for value in required_edges_df[col]]

    ox_utils.log(f"Loaded {len(required_edges_df)} required edges.")

    return required_edges_df

def save_shortest_paths(name: str):
    path = './data/'

    files = [f for f in os.listdir(path) if f.endswith('.gzip') and "distances" in f and f.startswith(name)]
    files.sort(key=lambda x: os.path.getctime(os.path.join(path, x)))
    df_list = []
    for file in files:
        file_path = os.path.join(path, file)
        df = pd.read_parquet(file_path)
        df_list.append(df)

    result = pd.concat(df_list, axis=0)
    result.to_parquet("./data/" + name + f"_distances.parquet.gzip", engine='pyarrow', compression='GZIP')

    files = [f for f in os.listdir(path) if f.endswith('.gzip') and "predecessors" in f]
    files.sort(key=lambda x: os.path.getctime(os.path.join(path, x)))
    df_list = []
    for file in files:
        file_path = os.path.join(path, file)
        df = pd.read_parquet(file_path)
        df_list.append(df)

    result = pd.concat(df_list, axis=0)
    result.to_parquet("./data/" + name + f"_predecessors.parquet.gzip", engine='pyarrow', compression='GZIP')


def load_shortest_paths(name: str):
    distances = pd.read_parquet(f"./data/" + name + "_distances.parquet.gzip", engine='pyarrow')
    paths = pd.read_parquet(f"./data/" + name + "_predecessors.parquet.gzip", engine='pyarrow')

    ox_utils.log(f"Loaded {len(distances)} x {len(distances)} distances and paths matrix.")

    return distances, paths

def save_route(route_map, name: str):
    ox_utils.log(f"Saving plotted solution to ./data/" + name + ".html")

    route_map.save(outfile= "./data/" + name + ".html")

