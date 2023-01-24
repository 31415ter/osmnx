import graph_preparation.graph_preparation as prep

depots = {
    "name" : ["Giesenweg", "Laagjes"],
     "lon" : [4.4279192, 4.5230457], 
     "lat" : [51.9263550, 51.8837905], 
    "amenity" : ["depot", "depot"]
}

G = prep.load_graph(["Hoogvliet", "Rotterdam", "Schiedam"])
G = prep.process_graph(G, depots)
prep.save_graph(G, "Rotterdam_netwerk")