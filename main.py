import streetnx as snx
import osmnx as ox

ox.config(log_console=True)

# depots = {
#     "name" : ["Giesenweg", "Laagjes"],
#      "lon" : [4.4279192, 4.5230457], 
#      "lat" : [51.9263550, 51.8837905], 
#     "amenity" : ["depot", "depot"]
# }

# G = snx.download_graph(["Rotterdam", "Hoogvliet", "Schiedam"])
# G = snx.process_graph(G, depots)
# snx.save_graph(G, "Rotterdam_totale_netwerk")

G = snx.load_graph("Rotterdam_totale_netwerk")
snx.add_penalties(G)

print(G)