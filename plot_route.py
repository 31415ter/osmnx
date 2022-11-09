import osmnx as ox
import pandas as pd
import numpy as np
import folium
import folium.plugins as plugins

def _plot_route(solution, G, paths, depot_node, route_map = None):
    edges_ids = paths.index
    paths = paths.values

    from_depot_arcs = [edges_ids[depot_node][0]] + paths[depot_node, solution[0]]
    route_map = ox.plot_route_folium(G, from_depot_arcs, color='#00FF00', opacity=1, route_map=route_map)
    for i in range(0, len(solution)):

        service_arc = [edges_ids[solution[i]][0], edges_ids[solution[i]][1]]
        route_map = ox.plot_route_folium(G, service_arc, color='#FF0000', opacity=1, route_map=route_map)
        
        if i+1 < len(solution):
            route_next_arc = paths[solution[i], solution[i+1]]
            route_map = ox.plot_route_folium(G, route_next_arc, color='#0000FF', opacity=1, route_map=route_map)

    to_depot_arcs = paths[solution[-1], depot_node]
    if len(to_depot_arcs) > 1: route_map = ox.plot_route_folium(G, to_depot_arcs, color='#00FF00', opacity=1, route_map=route_map)

    route_map.save(outfile= "./data/solution.html")

    return route_map#_plot_route_markers_folium(G, route_map, solution, paths)
    
def _plot_route_markers_folium(G, route_map, solution, paths):
    required_nodes = [44409833] + [node for (node, data) in G.nodes(data = True) if 'amenity' in data and data['amenity'] == data['amenity']]
    gdf_nodes = ox.graph_to_gdfs(G)[0]
    nodes = gdf_nodes.loc[np.isin(gdf_nodes.index, required_nodes)]

    indices = list(pd.read_parquet("./data/Rotterdam_pois_distances.parquet").index)
    sequence = [(indices[solution[i]], i+1) for i in range(len(solution))]
    
    for key,value in sequence:
        nodes.loc[key, "sequence"] = int(value)
    
    for i in range(0,len(nodes)):
        folium.Marker(
            location=[nodes.iloc[i]['y'], nodes.iloc[i]['x']], popup=None,
            icon=plugins.BeautifyIcon(
                             icon="arrow-down", icon_shape="marker",
                             number=nodes.iloc[i]['sequence'],
                             border_color= "#757575",
                             background_color="#FFFFFF"
                         )
        ).add_to(route_map)

    return route_map