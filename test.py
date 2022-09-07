import networkx as nx
import osmnx as ox
from toolbox import connect_poi

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
    "landuse",
    "width",
    "est_width",
    "junction",
    "bicycle",
    "cycleway:left",
    "cycleway:right",
    "cycleway:both"
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

nodes, edges = ox.utils_graph.graph_to_gdfs(ox.utils_graph.get_undirected(G))

u = [u for u,v,k in list(edges.index)]
v = [v for u,v,k in list(edges.index)]
k = [k for u,v,k in list(edges.index)]
edges.index = range(0, len(edges))
edges['u'] = u
edges['v'] = v
edges['k'] = k

nodes['osmid'] = nodes.index
nodes.index = range(0, len(nodes))

pois = ox.geometries.geometries_from_place(city, buffer_dist=100, tags=tags)
pois = pois.to_crs(epsg = 4326)
pois = pois[pois['geometry'].geom_type == 'Point']
pois['lon'] = pois['geometry'].apply(lambda p: p.x)
pois['lat'] = pois['geometry'].apply(lambda p: p.y)
pois = pois.droplevel('element_type')
pois['key'] = pois.index  # set a primary key column

new_nodes, new_edges = connect_poi(pois, nodes, edges, key_col='osmid', projected_footways=False, node_pois = False, dict_tags = {'amenity', 'name'})

def _add_reversed_edges(G):
    from shapely.geometry import LineString
    oneway_values = {"yes", "true", "1", "-1", "reverse", "T", "F", 1, -1, True}
    for u,v,data in list(G.edges(data=True)):
        if "oneway" in data and data["oneway"] not in oneway_values:
            new_data = data.copy()
            new_data["reversed"] = True
            new_data["geometry"] = LineString(list(new_data["geometry"].coords)[::-1])
            if "key" in new_data:
                new_data.pop("key")

            # check if edge v,u exists in G
            key_list = list(G[u][v])
            if G.has_edge(v, u):
                key_list += list(G[v][u])
            new_key = max(key_list) + 1

            G.add_edge(v,u, key = new_key, **new_data)

V = nx.from_pandas_edgelist(df = new_edges, source = 'from', target = 'to', edge_attr = True, create_using = nx.MultiDiGraph(), edge_key = 'k')
nx.set_node_attributes(V, new_nodes.set_index('osmid').to_dict('index'))
V.graph["crs"] = 'epsg:4326'

_add_reversed_edges(V)

ox.save_graph_geopackage(V, filepath="./data/" + city + "_pois_network.gpkg", directed = True)