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
    ox.settings.use_cache=True

    ### GLADHEIDBESTRIJDING
    # depots = {
    #     "name" : ["Giesenweg", "Laagjes"],
    #      "lon" : [4.4279192, 4.5230457], 
    #      "lat" : [51.9263550, 51.8837905], 
    #     "amenity" : ["depot", "depot"]
    # }

    depots = {
        "name" : ["Giesenweg"],
         "lon" : [4.4279192], 
         "lat" : [51.9263550], 
        "amenity" : ["depot"]
    }

    # depots = {
    #     "name" : ["Laagjes"],
    #      "lon" : [4.5230457], 
    #      "lat" : [51.8837905], 
    #     "amenity" : ["depot"]
    # }


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
    name = "_".join(cities)

    ### Downloading graph and processing deadends
    # G = snx.load_graph(name + "_raw")
    # G = snx.download_graph(cities, custom_filter = None)
    # G = snx.process_deadends(G, depots)
    # snx.save_graph(G, name + "_new")
    
    # G = snx.load_graph(name + "_new")

    # def get_required_edges(cities, highway_types, buffer_dist = 0):
    #     required_edges_df = snx.load_required_edges(
    #         G, 
    #         required_cities=cities, 
    #         required_highway_types=highway_types,
    #         buffer_dist = buffer_dist
    #     )
    #     gdf_nodes, gdf_edges = ox.utils_graph.graph_to_gdfs(G)
    
    #     required_edges_mask = gdf_edges.index.isin(required_edges_df.index.values)
    #     attr_required_bool = {gdf_edges.index[index] : required_edges_mask[index] for index in range(len(gdf_edges))}
    #     attr_avg_geometry = {required_edges_df.index[index] : required_edges_df.iloc[index]['average_geometry'] for index in range(len(required_edges_df))}
    
    #     nx.set_edge_attributes(G, attr_required_bool, name='required')
    #     nx.set_edge_attributes(G, attr_avg_geometry, name='average_geometry')
    
    # get_required_edges(cities = ["Rotterdam"], highway_types = ["primary", "secondary"], buffer_dist = 0)

    # osmid_list = [
    #     [137881873, 137881875, 931175412], 27694746, 82834274, 7518889, [7518955, 7519004, 7518959], 7518931,
    #     562579611, [562579611, 160039831], 160039831, 144714506, 144714501, 144714502, [144714636, 7518989], 144714636,
    #     [144714506, 558313750], [397120528, 382881910], [156558732, 7518756], [958466434, 7518812], 
    # ]

    # remove_osmid_list = [
    #     [158220168, 148739666, 148739668, 158220167], 144315108, [7517265, 7517075, 7517325], 7516881, 7516940, 7516566, 755614523, 27694738, 7516949, 838270799, 7516949, 
    #     697641242, 755614522, 755614522, 697641245
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
    # removed_edges = filter_edges_by_list(remove_osmid_list, 'osmid', gdf_edges)

    # required_edges_mask = gdf_edges.index.isin(edges.index.values)
    # not_required_edges_mask = gdf_edges.index.isin(removed_edges.index.values)


    # attr_required_bool = {
    #     gdf_edges.index[index] : required_edges_mask[index] 
    #     for index in range(len(gdf_edges))
    #     if required_edges_mask[index]
    # }
    # attr_not_required_bool = {
    #     gdf_edges.index[index] : not not_required_edges_mask[index] 
    #     for index in range(len(gdf_edges))
    #     if not_required_edges_mask[index]
    # }

    # attr_required_bool.update(attr_not_required_bool)
    # nx.set_edge_attributes(G, attr_required_bool, name='required')
    # snx.save_graph(G, name + "_required")

    # # # # # Load graph from memory (if cached) or from OSM server
    # G = snx.load_graph(name + "_required")
    # # Add turn penalties to the graph
    # snx.add_penalties(G)
    # # Set turn:lanes on edges which are unspecified but are necesarry
    # snx.process_turn_lanes(G, 3)
    # snx.save_graph(G, name + "_processed_1")

    # split_edges = snx.split_edges(G, 3)
    # snx.update_turn_penalties(G, split_edges)
    # snx.save_graph(G, name + "_processed_2")
    # print("test")

    ### Loading graph and saving distances
    # G = snx.load_graph(name + "_processed_2")
    # snx.add_penalties(G)
    
    # def load_required_edges():
    #     nodes, edges = ox.utils_graph.graph_to_gdfs(G)
    #     mask = (edges['required'] == 'True')
    #     return edges.loc[mask, ["lanes", "length", "lanes:forward", "lanes:backward", "turn:lanes", "speed_kph", "oneway", "average_geometry"]]
    
    # required_edges_df = load_required_edges()
    # print(len(required_edges_df))
    # distances, predecessors = snx.get_all_shortest_paths(G, required_edges_df=required_edges_df, cores=8, name=name, size=500, max_speed=100)
    # snx.save_shortest_paths(name = name)


    # ## Saving lanes for the routing optimization  
    # G = snx.load_graph(name + "_required")
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


    # Visualizing a solution
    # G = snx.load_graph(name + "_required")
    distances, paths = snx.load_shortest_paths(name)

    # nodes, edges = ox.utils_graph.graph_to_gdfs(G)
    # mask = (edges['required'] == 'True')
    # required_edges_df = edges.loc[mask, ["lanes", "length", "lanes:forward", "lanes:backward", "turn:lanes", "speed_kph", "oneway", "average_geometry"]]

    # depot_dict = nsx_utils.load_depot_indices(G, required_edges_df)
    
    # def function(solution, name):
    #     route_map = snx.plot_route(G, solution=solution, depot_dict=depot_dict, paths=paths)
    #     # snx.save_ar3(route_map, "FR_ZUID")
    #     route_map.save(f"./data/{name}.html")

#     solution = [
# 9990000000, 832,256,246,244,242,237,618,604,230,437,617,837,616,217,209,173,354,827,613,314,427,175,160,763,155,1,130,276,368,90,104,102,93,116,114,113,125,350,371,374,442,95,347,948,947,74,70,927,985,987,981,988,986,984,982,928,46,924,823,821,41,522,294,443,317,444,438,485,648,521,649,821,439,966,318,49,628,655,657,48,671,830,946,944,949,672,302,47,629,652,50,19,648,523,42,343,650,651,822,925,929,983,926,58,61,65,64,69,75,81,80,945,96,441,376,826,200,839,232,235,239,241,243,245,247,252,255,257,831,250,326,265,259,262,264,330,270,269,261,260,873,808,805,914,913,918,937,921,886,844,876,907,902,852,889,765,56,591,589,585,578,575,574,557,551,550,561,732,15,560,711,562,567,593,582,586,494,500,503,507,505,788,502,501,496,537,536,493,500,498,497,588,587,575,574,569,557,556,555,551,552,561,731,17,570,572,593,586,494,544,546,492,469,942,787,897,898,900,849,854,939,857,846,882,883,884,885,919,922,162,154,152,756,923,920,938,908,909,912,910,799,800,803,795,806,789,267,820
#     ]
#     function(solution, "1A")

#     solution = [
# 9990000000, 249,840,258,327,301,817,807,770,395,782,779,218,222,221,224,388,772,382,397,215,662,663,214,213,289,608,590,737,399,404,401,409,625,951,623,624,622,621,283,954,955,952,410,403,406,414,413,416,449,736,419,370,450,724,453,452,878,879,472,466,365,792,793,868,869,847,377,351,144,157,435,183,517,519,323,322,321,273,319,516,515,514,274,513,602,324,272,271,950,815,812,809,810,811,814,813,766,781,888,777,660,191,193,185,670,163,761,447,445,446,448,760,164,668,669,190,661,213,384,380,286,226,396,287,73,78,658,960,383,959,285,286,227,226,385,288,608,589,487,579,581,584,626,489,607,462,460,871,843,881,890,72,797,665,71,872,784,293,973,967,870,825,373,372,379,158,177,517,169,512,520,184,170,828,295,520,171,181,428,895,313,159,145,378,375,964,824,969,348,467,292,611,612,836,907,902,853,889,842,764,461,483,459,755,355,357,752,753,475,454,456,725,420,415,726,727,411,405,744,332,336,335,59,610,340,341,482,307,308,835,864,863,860,480,858,862,865,859,861,481,311,866,310,60,338,334,333,331,337,605,417,400,402,627,626,488,592,76,84,490,960,381,771,225,887,220,219,783,390,393,775,917,915,801,802,804,796,874,789,266,262,263,268,329
#     ]
#     function(solution, "2A")

#     solution = [
# 9990000000, 328,791,816,819,911,943,936,768,767,916,153,194,197,207,758,392,394,391,759,205,204,195,168,166,297,165,296,149,139,122,121,298,100,98,300,127,134,137,141,142,147,150,757,491,131,845,856,940,855,851,848,786,468,545,542,543,833,540,933,646,645,978,643,637,633,935,976,14,934,632,631,635,636,639,642,977,647,534,932,931,541,730,834,498,583,580,578,576,20,27,25,22,739,741,747,31,34,750,35,38,478,282,281,956,958,957,953,408,412,627,486,83,659,86,89,99,666,664,68,891,56,591,737,398,440,418,743,605,417,486,607,463,754,751,474,366,367,455,458,464,40,473,471,723,457,451,39,722,721,720,742,23,734,718,577,568,16,565,12,566,577,16,15,564,558,9,979,906,548,549,554,553,547,904,8,10,7,696,699,690,683,679,673,677,676,682,693,695,422,421,715,563,559,426,708,962,905,903,980,961,425,712,713,709,424,423,691,688,685,275,710,714,716,13,12,571,573,717,733,719,735,26,30,28,29,470,880,358,360,362,363,364,356,359,345,344,509,506,788,501,496,495,535,432,431,539,434,531,532,530,528,526,524,429,990,703,704,701,729,700,702,525,527,529,433,538,536,493,499,503,504,877,508,510,746,745,44,43,361,465,476,511,53,728,55,792,794,867,869,850,875,784,124,349,479,971,970,972,126,103,105,108,92,595,110,785,111,278,598,601,599,369,597,594,596,600,0,3,316,156,161,179,176,894,893,172,188,187,208,216,615,838,436,603,619,620,236
#     ]
#     function(solution, "3A")
