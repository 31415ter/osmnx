import networkx as nx
import osmnx as ox
from toolbox import *

tags = {'amenity': ['restaurant', 'pub', 'cafe', 'fast_food', 'bar']}

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

city = "Delft"

G1 = ox.graph_from_place(city, custom_filter=cf_1, retain_all=True, simplify=False)
G2 = ox.graph_from_place(city, custom_filter=cf_2, retain_all=True, simplify=False)
G3 = ox.graph_from_place(city, custom_filter=cf_3, retain_all=True, simplify=False)

G = nx.compose(G1, G2)
G = nx.compose(G3, G)
G = ox.utils_graph.get_largest_component(G) # do not consider disconnected components
G = ox.simplify_graph(G)

G = graph_with_pois_inserted(G, city, tags)

ox.save_graph_geopackage(G, filepath="./data/" + city + "_2_pois_network.gpkg", directed = True)