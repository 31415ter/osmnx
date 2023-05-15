import math
import streetnx as snx
import osmnx as ox
import networkx as nx
from streetnx import utils as nsx_utils
from osmnx import utils as ox_utils

if __name__ == '__main__':
    ox.settings.log_file=True
    ox.settings.log_console=True
    ox.settings.use_cache=True

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


    ### DELFT
    depots = {
        "name": ["Depot"],
        "lon": [4.3575636],
        "lat": [52.0197675],
        "amenity": ["depot"]
    }

    cf = (
        f'["highway"]["highway"~"motorway|trunk|primary|secondary|tertiary|unclassified|residential|living_street|cycleway"]'
        f'["access"!~"no|private"]'
    ) 

    cities = ["Delft"]
    name = "_".join(cities)

    ### Downloading graph and processing deadends
    # G = snx.load_graph(name)
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
    
    # get_required_edges(cities = ["Delft"], highway_types = ["primary", "secondary", "tertiary"])

    # osmid_list = [
    # #     # 53224295, 171939038, 157251769, 7532700, [137559408, 53224296, 137559405], 137559407, [50369744, 137458531, 50369741, 609734558],
    # #     # [7532659, 441974364, 7532621], 441979155, [53224299, 754683917], 171939038, 53224299, [424502796, 176564390],
    # #     # [361246624, 361246625, 293999298], [53216363, 50369756, 144715597], [53216362, 50369739, 50369751], 319334668, 670570697,
    # #     # 491178334, 64194440, 64194472, 7532809, 64194485, 510799036, 510798056, 28415820,
    # #     # 47573945, 47573945, 65649835, 65649862, 7532769, 7532769, 65717848, 424502796,
    # #     # [64194512, 637555100, 575687031]
    # ]

    # def filter_edges_by_list(search_list, name, gdf):
    #     """
    #     Takes a list of osmid values and a GeoDataFrame of edges, and returns a filtered
    #     GeoDataFrame containing only the edges that have an osmid value in the input list.
    #     """
    #     filtered_gdf = gdf[gdf[name].isin(search_list)]
    #     return filtered_gdf
    
    # gdf_nodes, gdf_edges = ox.utils_graph.graph_to_gdfs(G)
    # edges = filter_edges_by_list(osmid_list,'osmid',gdf_edges)

    # required_edges_mask = gdf_edges.index.isin(edges.index.values)
    # attr_required_bool = {
    #     gdf_edges.index[index] : required_edges_mask[index] 
    #     for index in range(len(gdf_edges))
    #     if required_edges_mask[index]
    # }
    # nx.set_edge_attributes(G, attr_required_bool, name='required')

    # snx.save_graph(G, name)

    # TESTING do happen here!
    

    def string_2_bool(v:str) -> bool:
        return v.lower() in ("yes", "true", "t", "1")


    def has_common_value(list1, list2):
        set1 = set(list1)
        for value in list2:
            if value in set1:
                return True
        return False


    def split_turn_types(turn_types: str, max_size: int):
        if isinstance(turn_types, list):
            turn_types = turn_types[-1] # select last turns
        turn_types_list = [turn_type if turn_type != '' else 'misc' for turn_type in turn_types.split('|')]
        num_turns = len(turn_types_list)
        num_parts = math.ceil(num_turns / max_size)

        parts = []
        i = 0
        for _ in range(num_parts):
            part = []
            while i < len(turn_types_list) and len(part) < max_size:
                current_turn = turn_types_list[i]
                previous_turn_not_same = part and not has_common_value(current_turn.split(';'), part[-1].split(';'))
                next_turn_same = i + 1 < len(turn_types_list) and has_common_value(current_turn.split(';'), turn_types_list[i + 1].split(';'))
                parts_left = math.ceil((len(turn_types_list)-i) / max_size)
                balancing = (
                    parts_left == 1 
                    and num_turns - i == len(part) 
                    and not next_turn_same 
                    and previous_turn_not_same
                    and i + 1 < len(turn_types_list)
                )
                if (
                    previous_turn_not_same
                    and next_turn_same 
                    and parts_left != num_parts - len(parts) 
                    or balancing
                ):
                    break
                part.append(current_turn)
                i += 1
            parts.append('|'.join(part))

        return parts


    def split_required_edges(graph, parallel_lanes:int) -> None:        
        highest_key = {}
        edges = graph.edges(keys=True)
        for edge in edges:
            key = edge[2]
            if (edge[0], edge[1]) not in highest_key or highest_key[(edge[0], edge[1])] < key:
                highest_key[(edge[0], edge[1])] = key

        edges = [(u,v,key,data) for (u,v,key,data) in graph.edges(keys=True,data=True)]

        added_edges : int = 0

        for u, v, key, data in edges:
            required = string_2_bool(data.get('required'))
            if not required: 
                continue

            # Get the last turn:lanes that are available within an edge
            a = data.get('turn:lanes')
            if a == 'nan':
                continue

            c = ''
            if isinstance(a, str):
                b = a.replace('[', '').replace(']', '').replace(' ', '').replace('\'', '')
                c = b.split(',')
                if len(c) > 1:
                    c = c[-1]
            else:
                c = a[-1]

            turn_types = split_turn_types(c, parallel_lanes)
            if len(turn_types) == 1:
                new_data = dict(data) # copies the data dict
                new_data['turn:lanes'] = turn_types[0]
                new_data['lanes'] = str(len(turn_types[0].split('|')))
                graph.edges[u, v, key].update(new_data)

                continue # if only one turn, nothing to split
            added_edges += len(turn_types) - 1
            for i in range(len(turn_types)):
                new_data = dict(data) # copies the data dict
                new_data['turn:lanes'] = turn_types[i]
                new_data['lanes'] = str(len(turn_types[i].split('|')))

                if i == 0:
                    graph.edges[u, v, key].update(new_data)
                else:
                    in_matches = {(pair[0], (u, v, highest_key[(u, v)]+i)):G.turns[pair] for pair in G.turns.keys() if pair[1] == (u,v,key)}
                    out_matches = {((u, v, highest_key[(u, v)]+i), pair[1]):G.turns[pair] for pair in G.turns.keys() if pair[0] == (u,v,key)}
                    graph.add_edge(u, v, key=highest_key[(u, v)]+i, **new_data)

                    graph.turns.update(in_matches)
                    graph.turns.update(out_matches)

        ox_utils.log(f"Added {added_edges} copies of edges.")


    def duplicate_edges(graph) -> None:
        required_edges = [
            (u,v,key,data) 
            for (u,v,key,data)
            in graph.edges(keys=True,data=True) 
            if string_2_bool(data['required']) and data['lanes'] == '2' and data['turn:lanes'] != 'nan' and len(set(data['turn:lanes'].split("|"))) != 1
        ]

        # 1.
        # iterate over each edge and create an duplicate edge for each possible direction
        # COPY THE TURN PENALTIES INTO THE NEWLY CREATED EDGES
        # THE OUTGOING TURN PENALTIES WILL BE UPDATED LATER..
        # each edge should indicate on which lane is driven, such that paths to other edges can be routed correctly
        
        # 2.
        # Save the duplicates into a map

        # 3.
        # For edges with lanes > 2, split these edges!
        # set the correct lane that will be driven over (such that paths to other edges can be routed correctly)

        # 4. 
        # Set turn penalties between adjacent edges, based on lanes and/or turn penalties


    def set_split_edge_penalties(G) -> None:
        required_edges = [(u,v,key,data) for (u,v,key,data) in G.edges(keys=True,data=True) if string_2_bool(data['required'])]

        for u, v, key, data in required_edges:
            in_matches = {pair:G.turns[pair] for pair in G.turns.keys() if pair[1] == (u,v,key)}
            out_matches = {pair:G.turns[pair] for pair in G.turns.keys() if pair[0] == (u,v,key)}


    G = snx.load_graph(name)
    snx.add_penalties(G)
    split_required_edges(G, 3)
    duplicate_edges(G)
    

    # print("test")

    # ### Loading graph and saving distances
    # G = snx.load_graph(name + ("_Spaanse_Polder" if cf is None else "_custom_network"))
    # snx.add_penalties(G)
    
    # def load_required_edges():
    #     nodes, edges = ox.utils_graph.graph_to_gdfs(G)
    #     mask = (edges['required'] == 'True')
    #     return edges.loc[mask, ["lanes", "length", "lanes:forward", "lanes:backward", "turn:lanes", "speed_kph", "oneway", "average_geometry"]]
    
    # required_edges_df = load_required_edges()
    # distances, predecessors = snx.get_all_shortest_paths(G, required_edges_df=required_edges_df, cores=8, name=name, size=500, max_speed=100)
    # snx.save_shortest_paths(name=name)

    # ### Saving lanes for the routing optimization  
    # G = snx.load_graph(name + ("_Spaanse_Polder" if cf is None else "_custom_network"))
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








#     ### Visualizing a solution
#     G = snx.load_graph(name + ("_Spaanse_Polder" if cf is None else "_custom_network"))
#     distances, paths = snx.load_shortest_paths(name)

#     nodes, edges = ox.utils_graph.graph_to_gdfs(G)
#     mask = (edges['required'] == 'True')
#     required_edges_df = edges.loc[mask, ["lanes", "length", "lanes:forward", "lanes:backward", "turn:lanes", "speed_kph", "oneway", "average_geometry"]]

#     depot_dict = nsx_utils.load_depot_indices(G, required_edges_df)
#     solution = [9990000000, 320,76,47,54,77,121,103,111,117,122,225,205,107,147,176,313,314,296,206,312,316,259,242,241,289,303,106,100,63,52,51,67,66,28,0,4,5,13,18,31,3,15,6,16,9,22,37,42,56,97,157,156,213,237,294,287,282,240,270,300,283,275,301,224,202,223,298,170,174,155,154,96,85,33,62,82,90,23,46,86,57,196,172,211,200,184,140,133,129,118,126,188,191,149,182,190,180,216,308,278,273,252,233,265,251,167,150,199,218,246,272,220,228,232,235,226,192,178,160,249,255,307,305,286,280,247,209,217,257,262,263,267,274,258,194,187,125,162,177,119,132,134,145,153,165,198,168,142,135,138,91,81,105,60,34,44,36,30,27,43,59,68,87,88,101,113,109,73,112,72,71,292
# ]
#     route_map = snx.plot_route(G, solution=solution, depot_dict=depot_dict, paths=paths)
#     snx.save_ar3(route_map, "HR_NOORD_2")