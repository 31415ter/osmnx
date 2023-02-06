import streetnx as snx
import osmnx as ox

from streetnx import utils as nsx_utils

if __name__ == '__main__':

    ox.settings.log_file=True
    ox.settings.log_console=True
    ox.settings.use_cache=False

    depots = {
        "name" : ["Giesenweg", "Laagjes"],
         "lon" : [4.4279192, 4.5230457], 
         "lat" : [51.9263550, 51.8837905], 
        "amenity" : ["depot", "depot"]
    }

    use_custom = False # Adjust which streetnetwork 
    cities = ["Rotterdam", "Hoogvliet", "Schiedam"]
    name = "_".join(cities)

    # ### Downloading graph and processing deadends
    # G = snx.download_graph(cities, use_custom = use_custom)
    # G = snx.process_deadends(G, depots)    
    # snx.save_graph(G, name + ("_road_network" if not use_custom else "_custom_network"))

    # # ### Loading graph and saving distances
    # G = snx.load_graph(name + ("_road_network" if not use_custom else "_custom_network"))
    # snx.add_penalties(G)
    # required_edges_df = snx.load_required_edges(G, required_cities=["Rotterdam", "Hoogvliet"])
    # distances, predecessors = snx.get_all_shortest_paths(G, required_edges_df=required_edges_df, cores=8, name = name, size=500, max_speed=100)
    # snx.save_shortest_paths(name=name)

    # ### Saving lanes for the routing optimization  
    # G = snx.load_graph(name + ("_road_network" if not use_custom else "_custom_network"))
    # required_edges_df = snx.load_required_edges(G, required_cities=["Rotterdam", "Hoogvliet"])
    # distances_df, paths_df = snx.load_shortest_paths(name)
    # depots_list = nsx_utils.get_depot_nodes(G)
    # snx.save_lanes(name, required_edges_df, distances_df, depots_list)

    ### Visualizing a solution
    G = snx.load_graph(name + ("_road_network" if not use_custom else "_custom_network"))
    distances, paths = snx.load_shortest_paths(name)
    required_edges_df = snx.load_required_edges(G, required_cities=["Rotterdam", "Hoogvliet"])
    depot_dict = nsx_utils.load_depot_indices(G, required_edges_df)
    route_map = snx.plot_route(G, solution=[9990000001, 35, 120, 66], depot_dict=depot_dict, paths=paths)
    snx.save_route(route_map, name)

    # ### Save solution to AR3 format
    # distances, paths = snx.load_shortest_paths(name)
    # depot_indices = nsx_utils.load_depot_indices(G, required_edges_df)
    # snx.ar3_route(G, solution = [35, 120, 66], depot_indices=depot_indices, paths=paths)