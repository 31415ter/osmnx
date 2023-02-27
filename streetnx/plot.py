import osmnx as ox
import folium
import folium.plugins as plugins

from streetnx import utils as nsx_utils
from osmnx import utils as ox_utils

def plot_route(G, solution, depot_dict, paths, route_map=None):

    ox_utils.log(f"Plotting solution {solution}")

    edges_ids = paths.index
    paths = paths.values

    # retrieve the depot node from the solution
    depot = solution[0]
    solution = solution[1:]

    from_depot_arcs = [depot] + paths[depot_dict[depot]['out'], solution[0]].tolist()
    route_map = ox.plot_route_folium(G, from_depot_arcs, color='#ffff00', opacity=1, route_map=route_map) # geel, heenweg
    for i in range(0, len(solution)):

        service_arc = [edges_ids[solution[i]][0], edges_ids[solution[i]][1]]
        route_map = ox.plot_route_folium(G, service_arc, color='#FF0000', opacity=1, route_map=route_map) # red

        start = G.nodes[service_arc[0]]
        start_x, start_y = start['x'], start['y']

        end = G.nodes[service_arc[1]]
        end_x, end_y = end['x'], end['y']

        # folium.Marker(
        #     location=[start_y, start_x], popup=None,
        #     icon=plugins.BeautifyIcon(
        #                      icon="arrow-down", icon_shape="marker",
        #                      number=str(i) + "\'",
        #                      border_color= "#757575",
        #                      background_color="#FFFFFF"
        #                  )
        # ).add_to(route_map)

        # folium.Marker(
        #     location=[end_y, end_x], popup=None,
        #     icon=plugins.BeautifyIcon(
        #                      icon="arrow-down", icon_shape="marker",
        #                      number=i,
        #                      border_color= "#757575",
        #                      background_color="#FFFFFF"
        #                  )
        # ).add_to(route_map)
        
        if i+1 < len(solution):
            route_next_arc = paths[solution[i], solution[i+1]].tolist()
            if len(route_next_arc) == 1:
                continue 
            route_map = ox.plot_route_folium(G, route_next_arc, color='#0000FF', opacity=1, route_map=route_map) # blue

    to_depot_arcs = paths[solution[-1], depot_dict[depot]['in']].tolist() + [depot]
    if len(to_depot_arcs) > 1: route_map = ox.plot_route_folium(G, to_depot_arcs, color='#fb00ff', opacity=1, route_map=route_map) # roze, terugweg

    return route_map


def ar3_route(G, solution, depot_indices, path):
    print("")
