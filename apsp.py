import pandas as pd
import warnings
import numpy as np
import networkx as nx

import osmnx as ox

from shapely.errors import ShapelyDeprecationWarning
from shapely.geometry import LineString
from osmnx import utils

warnings.filterwarnings("ignore", category=ShapelyDeprecationWarning) 
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.filterwarnings("ignore", category=np.VisibleDeprecationWarning) 

def _dijkstra(G, source, targets, weight='length'):
    dist = dict.fromkeys(list(G), float('inf'))
    prev = dict.fromkeys(list(G))

    unvisited = set(targets)

    dist[source] = 0
    unvisited.discard(source)

    Q = makefheap()
    fheappush(Q, (0, source))
    
    while Q.num_nodes > 0:
        node = Q.extract_min()
        unvisited.discard(node.key[1])
        
        # if we've reached all targets, we're done
        if len(unvisited) == 0:
            break

        for u,v,k,d in G.out_edges(node.key[1], data = True, keys = True):
            alt = dist[u] + d[weight]
            if alt < dist[v]:
                dist[v] = alt
                prev[v] = (u,k)
                fheappush(Q, (dist[v], v))

    # return the distances corresponding to the targets and all prev where non None
    return {t: dist[t] for t in targets if t != source}, {t: prev[t] for t in prev if (prev[t] is not None or t == source)}

def _construct_coordinate_paths(G, source, targets):
    paths = dict.fromkeys([t for t in targets if t != source])
    for target in targets:
        # do not create path from source to itself
        if target == source:
            continue
        path = [(G.nodes[target]["x"], G.nodes[target]["y"])]
        v = target        
        while prev[v] is not None:
            u, k = prev[v]
            edge = G[u][v][k]

            # if no gemetry in edge, add node coordinates
            if "geometry" not in edge:
                # linestring = LineString([Point(G.nodes[u]["x"], G.nodes[u]["y"]), Point(G.nodes[v]["x"], G.nodes[v]["y"])])
                path = [(G.nodes[u]["x"], G.nodes[u]["y"])] + path
            else:
                x = edge["geometry"].coords.xy[0]
                y = edge["geometry"].coords.xy[1]

                # select all x and y coordinates, but not the last
                coordinates = list(zip(x[:-1], y[:-1]))
                path = coordinates + path
            v = u
        paths[target] = path
    return paths

def _construct_linestring(paths):
    linestrings = dict.fromkeys(paths.keys())
    for key in linestrings.keys():
        linestrings[key] = LineString(paths[key])
    return linestrings

ox.config(log_file=True, log_console=True, use_cache=True)

cf = (
    f'["highway"]["highway"~"motorway|trunk|primary|secondary|tertiary"]'
    f'["access"!~"no|private"]'
)

hwy_speeds = {'motorway': 100,
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
                'living_street': 5}

rotterdam_graph = ox.graph_from_place("Rotterdam", custom_filter = cf, buffer_dist=2000, truncate_by_edge=True, simplify=False)
hoogvliet_graph = ox.graph_from_place("Hoogvliet", custom_filter = cf, buffer_dist=3000, truncate_by_edge=True, simplify=False)
schiedam_graph = ox.graph_from_place("Schiedam", custom_filter = cf, buffer_dist=1000, truncate_by_edge=True, simplify=False)

G = nx.compose(rotterdam_graph, hoogvliet_graph)
G = nx.compose(G, schiedam_graph)
G = ox.simplify_graph(G, allow_lanes_diff=False)
G = ox.add_edge_speeds(G, hwy_speeds, fallback = 30)
    
removed_nodes_list = []
removed_nodes = True

utils.log("Begin removing deadends...")

while removed_nodes:
    # Remove nodes which only have incoming or outgoing edges
    dead_ends = [node for node in G.nodes() if len(G.in_edges(node)) == 0 or len(G.out_edges(node)) == 0]

    # Remove nodes with only one incoming and one outgoing edge, and these two edges originate from the same nodes (i.e., (u,v,k) == (v,u,k))
    forbidden_u_turns = [node for node in G.nodes() if (
        len(G.in_edges(node)) == 1 
        and len(G.out_edges(node)) == 1 
        and list(G.in_edges(node, keys = True))[0][0] == list(G.out_edges(node, keys = True))[0][1] # u == v
        and list(G.in_edges(node, keys = True))[0][1] == list(G.out_edges(node, keys = True))[0][0] # v == u
        and list(G.in_edges(node, keys = True))[0][2] == list(G.out_edges(node, keys = True))[0][2] # keys should be equal
        )
    ]

    sharp_turns = [node for node in G.nodes() if (
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

print(len(removed_nodes_list))

G = ox.simplify_graph(G, allow_lanes_diff=False)

ox.save_graph_geopackage(G, filepath="./data/Rotterdam_network_2_new.gpkg", directed = True)

targets = list(G)
sources = list(G)

distance_df = pd.DataFrame(index = sources, columns = targets)
path_df = pd.DataFrame(index = sources, columns = targets)

# distance_df = pd.read_pickle('./data/distance_df.pkl')
# path_df = pd.read_pickle('./data/path_df.pkl')

# O(|E||V| + |V|^2 log |V|)
for i in range(len(sources)):
    print(i, len(sources))
    source = sources[i]
    dist, prev = _dijkstra(G, source, targets)
    coordinate_paths = _construct_coordinate_paths(G, source, targets)
    linestrings = _construct_linestring(coordinate_paths)
    
    distance_df.loc[source, dist.keys()] = list(dist.values())
    path_df.loc[source, linestrings.keys()] = list(linestrings.values())

distance_df.to_pickle('./data/distance_df.pkl')
path_df.to_pickle('./data/path_df.pkl')

# import geopandas as gpd
# gdf3 = gpd.GeoDataFrame(geometry=list(linestrings.values()), crs = 'epsg:4326')  # Note GeoDataFrame geometry requires a list
# gdf3.to_file(filename='./data/nodes.shp', driver='ESRI Shapefile')

# print("stop")