import networkx as nx
import osmnx as ox
import geopandas as gpd
from toolbox import connect_poi
from osmnx.utils_graph import get_largest_component

tags = {'amenity': ['restaurant', 'pub', 'hotel'],
        'building': 'hotel',
        'tourism': 'hotel'}

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
        f'["highway"]["highway"!~"footway|service|busway|motor|steps|platform|path|track|bridleway|construction"]'
        f'["bicycle"!~"^no|private|use_sidepath$"]["access"!~"no|private"]["area"!~"yes"]'
    )

cf_2 = (
        f'["highway"]["highway"~"footway|service|busway|motor|steps|platform|path|track|bridleway|construction"]'
        f'["bicycle"~"yes|designated|permissive|dismount"]["access"!~"no|private"]["area"!~"yes"]'
    )

cf_3 = (
        f'["highway"]["highway"="service"]["service"!="parking_aisle"]'
        f'["bicycle"!~"^no|private|use_sidepath$"]["access"!~"no|private"]["area"!~"yes"]'
    )

ox.config(log_file=True, log_console=True, use_cache=True, useful_tags_way=useful_tags_way)

# get road network and save as .shp
G_1 = ox.graph_from_place("Delft", custom_filter=cf_1, retain_all=True, simplify=False)
G_2 = ox.graph_from_place("Delft", custom_filter=cf_2, retain_all=True, simplify=False)
G_3 = ox.graph_from_place("Delft", custom_filter=cf_3, retain_all=True, simplify=False)

G_4 = nx.compose(G_1, G_2)
G = nx.compose(G_3, G_4)
G = get_largest_component(G) # do not consider disconnected components
G = ox.simplify_graph(G)

ox.save_graph_shapefile(G, filepath='data/delft/', encoding='utf-8', directed=True)

# load as GeoDataFrame
nodes = gpd.read_file('data/delft/nodes.shp')
edges = gpd.read_file('data/delft/edges.shp')

# ONLY SAVE EDGES THAT ARE NOT REVERSED!
# LATER ADD REVERSE OF EDGES!

edges = edges.loc[(edges["reversed"] == "False")]
edges['from'] = edges['u']
edges['to'] = edges['v']

pois = ox.geometries.geometries_from_place("Delft", buffer_dist=500, tags=tags)
pois = pois.to_crs(epsg = 4326)
pois = pois[pois['geometry'].geom_type == 'Point']
pois['lon'] = pois['geometry'].apply(lambda p: p.x)
pois['lat'] = pois['geometry'].apply(lambda p: p.y)
pois['key'] = pois.index  # set a primary key column

# pois = pois.loc[pois['name'] == "Hotel Eetcafé Het Konings Huys"]

new_nodes, new_edges = connect_poi(pois, nodes, edges, key_col='key', path=None)

new_nodes = new_nodes[new_nodes['highway'] != 'poi']
new_edges = new_edges[new_edges['highway'] != 'projected_footway']

new_nodes.drop('osmid', axis = 1).to_file('data/sample/test_nodes.shp')
new_edges.to_file('data/sample/new_edges.shp')

# add reversed edges to the graph
new_edges['key'] = new_edges['key'].astype(int)

V = nx.from_pandas_edgelist(df = new_edges, source = 'from', target = 'to', edge_attr = True, create_using = nx.MultiDiGraph(), edge_key = 'key')
nx.set_node_attributes(V, new_nodes.set_index('osmid').to_dict('index'))
V.graph["crs"] = 'epsg:4326'
ox.save_graph_geopackage(V, filepath="./data/TEST_simplified_network.gpkg")

node = 44809902
in_edge = [d for u,v,d in G.in_edges(node, data=True)]
out_edge = [d for u,v,d in G.out_edges(node, data=True)]

print((len(in_edge), len(out_edge)))