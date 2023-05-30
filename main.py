import math
import streetnx as snx
import osmnx as ox
import networkx as nx
from streetnx import utils as nsx_utils
from streetnx.turn import Turn, TurnType
from osmnx import utils as ox_utils

if __name__ == '__main__':
    ox.settings.log_file=True
    ox.settings.log_console=True
    ox.settings.use_cache=False

    # ### GLADHEIDBESTRIJDING
    # depots = {
    #     "name" : ["Giesenweg", "Laagjes"],
    #      "lon" : [4.4279192, 4.5230457], 
    #      "lat" : [51.9263550, 51.8837905], 
    #     "amenity" : ["depot", "depot"]
    # }

    # depots = {
    #     "name" : ["Giesenweg"],
    #      "lon" : [4.4279192], 
    #      "lat" : [51.9263550], 
    #     "amenity" : ["depot"]
    # }

    depots = {
        "name" : ["Laagjes"],
         "lon" : [4.5230457], 
         "lat" : [51.8837905], 
        "amenity" : ["depot"]
    }


    ### DELFT
    # depots = {
    #     "name": ["Depot"],
    #     "lon": [4.3575636],
    #     "lat": [52.0197675],
    #     "amenity": ["depot"]
    # }

    cf = (
        f'["highway"]["highway"~"motorway|trunk|primary|secondary|tertiary|unclassified|residential|living_street|cycleway"]'
        f'["access"!~"no|private"]'
    ) 

    cities = ["Rotterdam"]
    name = 'HR-zuid' #"_".join(cities)

    ## Downloading graph and processing deadends
    # G = snx.load_graph('Rotterdam')
    # G = snx.download_graph(cities, custom_filter=None)
    # G = snx.process_deadends(G, depots)
    
    # def get_required_edges(cities, highway_types):
    #     required_edges_df = snx.load_required_edges(
    #         G, 
    #         required_cities=cities, 
    #         required_highway_types=highway_types,
    #         buffer_dist = 0
    #     )
    #     gdf_nodes, gdf_edges = ox.utils_graph.graph_to_gdfs(G)
    
    #     required_edges_mask = gdf_edges.index.isin(required_edges_df.index.values)
    #     attr_required_bool = {gdf_edges.index[index] : required_edges_mask[index] for index in range(len(gdf_edges))}
    #     attr_avg_geometry = {required_edges_df.index[index] : required_edges_df.iloc[index]['average_geometry'] for index in range(len(required_edges_df))}
    
    #     nx.set_edge_attributes(G, attr_required_bool, name='required')
    #     nx.set_edge_attributes(G, attr_avg_geometry, name='average_geometry')
    
    # get_required_edges(cities = ["Waalhaven-Zuid"], highway_types = ["unclassified", "tertiary"])

    # osmid_list = [
    #     7517367, 468346012, 1125839328, 891323816, 7517223, 1125839328, 
    #     [7517292, 1126480708], 688216204, 7517375, 158179209, 363024154, 363024154,
    #     7519005, 7518950, 7519095, 7518950, 7519005, 7519005, [7518932, 7518933], 
    #     [300547416, 651852963], [651852960, 7519068], 165817256, 7519052,
    #     165817256, 7519052, 165817256, 7519052, [243745087, 7519054, 7519055], 165817257,
    #     300547417, 59306570, [651852961, 59306583], [651852962, 59306565], 59306581, 29376518,
    #     502766223, [502766221, 150555406],

    #     [558316737, 7517270], 7518940, [381814617, 1024669100], 381812020, [7518779, 381812020], [554323316, 185671164, 308192855],
    #     185671156, [185671157, 82198526, 334296991], 306396481, 7518805, 7518811, 35329330, 7519034, 1092843370, 1058366853,
    #     [554323316, 308192855, 185671164], [306396481, 334296985], 7518779, 7518779, 7518779, [554323316, 308192855, 185671164],554446121,
    #     554446121, [381814617, 381812020], 1092843821, 1092843371, 1092843371, 750092436, 48287774, 7517299,

    #     558316753, 1092843372, 1092843373, 1092843374, 1092843375, 1092843374, 1092843375, 7517312, 131549576, 131549577, 1078326074, 558316743,
    #     7518922, 7518917, 1092843820, [556861157, 7517270]
    # ]

    # def filter_edges_by_list(search_list, name, gdf):
    #     """
    #     Takes a list of osmid values and a GeoDataFrame of edges, and returns a filtered
    #     GeoDataFrame containing only the edges that have an osmid value in the input list.
    #     """
    #     filtered_gdf = gdf[gdf[name].isin(search_list)]
    #     return filtered_gdf
    
    # gdf_nodes, gdf_edges = ox.utils_graph.graph_to_gdfs(G)
    # edges = filter_edges_by_list(osmid_list, 'osmid', gdf_edges)

    # required_edges_mask = gdf_edges.index.isin(edges.index.values)
    # attr_required_bool = {
    #     gdf_edges.index[index] : required_edges_mask[index] 
    #     for index in range(len(gdf_edges))
    #     if required_edges_mask[index]
    # }
    # nx.set_edge_attributes(G, attr_required_bool, name='required')

    # snx.save_graph(G, name)





    # # # Load graph from memory (if cached) or from OSM server
    # # G = snx.load_graph(name)    

    # # # Add turn penalties to the graph
    # # snx.add_penalties(G)

    # # # Set turn:lanes on edges which are unspecified but are necesarry
    # # snx.process_turn_lanes(G)

    # # snx.split_edges(G, 3)
    
    # # print("test")


    # ### Loading graph and saving distances
    # G = snx.load_graph(name)
    # snx.add_penalties(G)
    
    # def load_required_edges():
    #     nodes, edges = ox.utils_graph.graph_to_gdfs(G)
    #     mask = (edges['required'] == 'True')
    #     return edges.loc[mask, ["lanes", "length", "lanes:forward", "lanes:backward", "turn:lanes", "speed_kph", "oneway", "average_geometry"]]
    
    # required_edges_df = load_required_edges()
    # print(len(required_edges_df))
    # distances, predecessors = snx.get_all_shortest_paths(G, required_edges_df=required_edges_df, cores=8, name=name, size=500, max_speed=100)
    # snx.save_shortest_paths(name=name)





    # ### Saving lanes for the routing optimization  
    # G = snx.load_graph(name)
    # nodes, edges = ox.utils_graph.graph_to_gdfs(G)
    # mask = (edges['required'] == 'True')
    # required_edges_df = edges.loc[mask, ["lanes", "length", "lanes:forward", "lanes:backward", "turn:lanes", "speed_kph", "oneway", "average_geometry"]]

    # for col in required_edges_df.columns:
    #     if 'geometry' in col:
    #         continue
    #     elif not required_edges_df[col].apply(lambda x: not isinstance(x, list)).all():
    #         required_edges_df[col] = [[value] if not isinstance(value, list) else value for value in required_edges_df[col]]

    # distances_df, paths_df = snx.load_shortest_paths(name)
    # depots_list = nsx_utils.get_depot_nodes(G)
    # snx.save_lanes(name, required_edges_df, distances_df, depots_list)








    # ### Visualizing a solution
    G = snx.load_graph(name)
    distances, paths = snx.load_shortest_paths(name)

    nodes, edges = ox.utils_graph.graph_to_gdfs(G)
    mask = (edges['required'] == 'True')
    required_edges_df = edges.loc[mask, ["lanes", "length", "lanes:forward", "lanes:backward", "turn:lanes", "speed_kph", "oneway", "average_geometry"]]

    depot_dict = nsx_utils.load_depot_indices(G, required_edges_df)
    solution = [
        9990000000, 66,68,79,118,122,119,109,65,57,83,75,100,97,104,111,110,115,117,121,80,63,56,55,48,51,43,46,74,101,130,134,129,95,81,61,105,103,124,209,132,136,92,30,87,90,39,76,47,45,211,41,88,185,217,141,144,145,146,147,187,143,146,147,149,161,157,160,154,155,163,201,153,158,162,165,186,168,172,182,207,216,169,191,190,200,166,192,174,175,178,180,215,204,197,206,171,170,189,159,188,203,202,148,152,218,151,150,142,125,137,138,37,34,32,29,85,94,23,14,5,12,21,25,26,198,195,194,84,67,24,17,8,6,16,1,18,22,11,9,7,2,3
    ]
    route_map = snx.plot_route(G, solution=solution, depot_dict=depot_dict, paths=paths)
    snx.save_ar3(route_map, "HR_ZUID_1")