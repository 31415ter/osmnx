import osmnx as ox
import networkx as nx

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

# G = ox.graph_from_place("Amsterdam", network_type="drive", simplify=False)
# G = ox.simplify_graph(G)
# ox.save_graph_geopackage(G, filepath="./data/network.gpkg")

city = "Delft"

G2 = ox.graph_from_place(city, network_type="drive", simplify=False)
G2 = ox.simplify_graph(G2, allow_lanes_diff=False)

ox.save_graph_geopackage(G2, filepath="./data/" + city.replace(" ", "_") + "_simplified_network.gpkg")
# ox.save_graph_shapefile(G2, filepath="./data/simplified_network.shp")

print("hey")