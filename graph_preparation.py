import pandas as pd
import warnings
import numpy as np
import networkx as nx
import osmnx as ox

from shapely.errors import ShapelyDeprecationWarning
from osmnx import utils
from osmnx import toolbox 
from fibheap import *

from osmnx.utils_graph import _lane_count

warnings.filterwarnings("ignore", category=ShapelyDeprecationWarning) 
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.filterwarnings("ignore", category=np.VisibleDeprecationWarning) 

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

ox.config(log_file=True, log_console=True, use_cache=True, useful_tags_way=useful_tags_way)

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

load_from_memory = True

if not load_from_memory:
    rotterdam_graph = ox.graph_from_place("Rotterdam", custom_filter = cf, buffer_dist=2000, truncate_by_edge=True, simplify=False)
    hoogvliet_graph = ox.graph_from_place("Hoogvliet", custom_filter = cf, buffer_dist=3000, truncate_by_edge=True, simplify=False)
    schiedam_graph = ox.graph_from_place("Schiedam", custom_filter = cf, buffer_dist=1000, truncate_by_edge=True, simplify=False)

    G = nx.compose(rotterdam_graph, hoogvliet_graph)
    G = nx.compose(G, schiedam_graph)
    G = ox.add_edge_speeds(G, hwy_speeds, fallback = 30)

    # # set lanes of edges correctly.
    # lane_count = {(_from, _to, _key) : _lane_count(_data) for (_from, _to, _key, _data) in G.edges(keys = True, data=True)}
    # nx.set_edge_attributes(G, name="lanes", values=lane_count)

    utils.log("Save graph to parquet")
    gdf_nodes, gdf_edges = ox.graph_to_gdfs(G)

    gdf_edges["geometry"] = gdf_edges["geometry"].apply(lambda x : list(x.coords))
    gdf_nodes["geometry"] = gdf_nodes["geometry"].apply(lambda x : list(x.coords))

    gdf_nodes.to_parquet("./data/Rotterdam_nodes.parquet", engine='pyarrow')
    gdf_edges.to_parquet("./data/Rotterdam_edges.parquet", engine='pyarrow')

if load_from_memory:
    # load df from parquet
    import geopandas as gpd
    from shapely.geometry import LineString

    df_nodes = pd.read_parquet("./data/Rotterdam_nodes.parquet")
    df_edges = pd.read_parquet("./data/Rotterdam_edges.parquet")
    utils.log("Load nodes and edges from parquet")

    # convert df to gdf
    gdf_nodes = gpd.GeoDataFrame(df_nodes, geometry = gpd.points_from_xy(df_nodes.x, df_nodes.y))
    edge_geometry = df_edges["geometry"].apply(lambda x: LineString(x.tolist()))
    gdf_edges = gpd.GeoDataFrame(df_edges, geometry = edge_geometry)
    utils.log("Converted nodes and edges df to gdfs")

    # convert np.arrays to lists when applicable
    for col in gdf_edges.columns:
        if not gdf_edges[col].apply(lambda x: not isinstance(x, np.ndarray)).all():
            gdf_edges[col] = [value if not isinstance(value, np.ndarray) else value.tolist() for value in gdf_edges[col]]
    utils.log("Converted np.arrays to lists")

    # create graph from gdf
    G = ox.graph_from_gdfs(gdf_nodes = gdf_nodes, gdf_edges = gdf_edges)
    utils.log("Loaded graph from gdfs")

ox.save_graph_geopackage(G, filepath="./data/0_initial_graph.gpkg", directed = True)

depots = {
    "name" : ["Giesenweg", "Laagjes"],
    "lon" : [4.4279192, 4.5230457], 
    "lat" : [51.9263550, 51.8837905], 
    "amenity" : ["depot", "depot"]
}
G = toolbox.graph_inserted_pois(G, depots)
utils.log("Inserted depots.")

# set lanes of edges correctly.
lane_count = {(_from, _to, _key) : _lane_count(_data) for (_from, _to, _key, _data) in G.edges(keys = True, data=True)}
nx.set_edge_attributes(G, name="lanes", values=lane_count)
utils.log("Set lane count of edges correctly.")
ox.save_graph_geopackage(G, filepath="./data/1_depots_graph.gpkg", directed = True)

G = ox.simplify_graph(G, allow_lanes_diff=False)
ox.save_graph_geopackage(G, filepath="./data/2_simplified_graph.gpkg", directed = True)

gdf_nodes, gdf_edges = ox.graph_to_gdfs(G)
depot_nodes = gdf_nodes[gdf_nodes['highway'] == 'poi'].index.tolist()

removed_nodes_list = []
removed_edges_list = []
removed_nodes = True

utils.log("Begin removing deadends...")

while removed_nodes:
    # Remove nodes which only have 1 incoming or 1 outgoing edges
    dead_ends = [
        node for node in G.nodes() if len(G.in_edges(node)) == 0 or len(G.out_edges(node)) == 0
    ]

    # TODO CHECK IF THESE EDGES ARE THE SAME LENGTH?
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
            len(G.out_edges(node)) == 1
            and all([abs(ox.utils_geo.angle(G, in_edge, list(G.out_edges(node, data = True))[0])) < 40 for in_edge in list(G.in_edges(node, data = True))])
        )
    ]
    
    sharp_turns += ([
        node for node in G.nodes() if (
            len(G.in_edges(node)) == 1
            and all(abs(ox.utils_geo.angle(G, list(G.in_edges(node, data = True))[0], out_edge)) < 40 for out_edge in list(G.out_edges(node, data = True)))
        )
    ])

    nodes_to_remove = list(set(dead_ends + forbidden_u_turns + sharp_turns))

    edges_to_remove = []
    # scan for streets that have one incoming edge.
    for edge in G.edges(keys = True, data = True):
        if edge[0] in depot_nodes or edge[1] in depot_nodes:
            continue

        if len(G.out_edges(edge[1])) == 1:
            out_edge = list(G.out_edges(edge[1], data = True))[0]
            if out_edge[0] == edge[1] and out_edge[1] == edge[0]:
                edges_to_remove += [edge]
            elif abs(ox.utils_geo.angle(G, edge, out_edge)) < 40:
                edges_to_remove += [edge]
            
        if len(G.in_edges(edge[0])) == 1:
            in_edge = list(G.in_edges(edge[0], data = True))[0]
            if in_edge[0] == edge[1] and in_edge[1] == edge[0]:
                edges_to_remove += [edge]
            elif abs(ox.utils_geo.angle(G, in_edge, edge)) < 40:
                edges_to_remove += [edge]

    for depot in depot_nodes:
        if depot in nodes_to_remove:
            nodes_to_remove.remove(depot)

    if len(nodes_to_remove) == 0 and len(edges_to_remove) == 0:
        removed_nodes = False

    removed_nodes_list += nodes_to_remove
    removed_edges_list += edges_to_remove
    G.remove_nodes_from(nodes_to_remove)
    G.remove_edges_from(edges_to_remove)
    utils.log(f"Removed {len(nodes_to_remove)} nodes and {len(edges_to_remove)} edges.")

utils.log(f"Removed {len(removed_nodes_list) + len(removed_edges_list)} deadends.")
ox.save_graph_geopackage(G, filepath="./data/3_cleaned_graph.gpkg", directed = True)

G = ox.simplify_graph(G, allow_lanes_diff=False)

ox.save_graph_geopackage(G, filepath="./data/4_final_graph.gpkg", directed = True)

utils.log("Saving graph to parquet...")

gdf_nodes, gdf_edges = ox.graph_to_gdfs(G)

gdf_edges["geometry"] = gdf_edges["geometry"].apply(lambda x : list(x.coords))
gdf_nodes["geometry"] = gdf_nodes["geometry"].apply(lambda x : list(x.coords))

for col in gdf_edges.columns:
    if col == "geometry":
        continue
    # check if any of the values within the column col are not a list
    if not gdf_edges[col].apply(lambda x: not isinstance(x, list)).all():
        gdf_edges[col] = [[value] if not isinstance(value, list) else value for value in gdf_edges[col]]
        if col == "osmid":
            rows = []
            for row in gdf_edges[col]:
                new_row = []
                for value in row:
                    _value = value
                    if isinstance(value, str):
                        _value = [int(v) for v in value.split(",")]
                    new_row += _value if isinstance(_value, list) else [value]
                rows.append(new_row)
            gdf_edges[col] = rows# [[int(id) for id in value[0].split(",")] if isinstance(value[0], str) else value for value in gdf_edges[col]]

gdf_nodes.to_parquet("./data/Rotterdam_bereik_nodes.parquet", engine='pyarrow')
gdf_edges.to_parquet("./data/Rotterdam_bereik_edges.parquet", engine='pyarrow')