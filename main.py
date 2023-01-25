import streetnx as snx
import osmnx as ox

# depots = {
#     "name" : ["Giesenweg", "Laagjes"],
#      "lon" : [4.4279192, 4.5230457], 
#      "lat" : [51.9263550, 51.8837905], 
#     "amenity" : ["depot", "depot"]
# }

# G = snx.download_graph(["Rotterdam", "Hoogvliet", "Schiedam"])
# G = snx.process_graph(G, depots)
# snx.save_graph(G, "Rotterdam_totale_netwerk")

if __name__ == '__main__':
    ox.config(log_console=True)
    name = "Rotterdam_totale_netwerk"
    G = snx.load_graph(name)

    # snx.add_penalties(G)
    # required_edges = snx.load_required_edges(G)
    # distances, paths = snx.get_shortest_paths(G, required_edges=required_edges, max_speed=100)
    # snx.save_shortest_paths(distances, paths, name)

    distances, paths = snx.load_shortest_paths(name)

    route_map = snx.plot_route(G, solution=[35], depot_edges=[48,46], paths=paths)
    snx.save_route(route_map, name)
