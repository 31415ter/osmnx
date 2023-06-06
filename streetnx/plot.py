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
        route_map = ox.plot_route_folium(G, service_arc, color='#FF0000', opacity=1, route_map=route_map, required=True) # red

        start = G.nodes[service_arc[0]]
        start_x, start_y = start['x'], start['y']

        end = G.nodes[service_arc[1]]
        end_x, end_y = end['x'], end['y']

        folium.Marker(
            location=[start_y, start_x], popup=None,
            icon=plugins.BeautifyIcon(
                             icon="arrow-down", icon_shape="marker",
                             number=str(i) + "\'",
                             border_color= "#757575",
                             background_color="#FFFFFF"
                         )
        ).add_to(route_map)

        folium.Marker(
            location=[end_y, end_x], popup=None,
            icon=plugins.BeautifyIcon(
                             icon="arrow-down", icon_shape="marker",
                             number=i,
                             border_color= "#757575",
                             background_color="#FFFFFF"
                         )
        ).add_to(route_map)
        
        if i+1 < len(solution):
            route_next_arc = paths[solution[i], solution[i+1]].tolist()
            if len(route_next_arc) == 1:
                continue 
            route_map = ox.plot_route_folium(G, route_next_arc, color='#0000FF', opacity=1, route_map=route_map) # blue

    to_depot_arcs = paths[solution[-1], depot_dict[depot]['in']].tolist() + [depot]
    if len(to_depot_arcs) > 1: route_map = ox.plot_route_folium(G, to_depot_arcs, color='#fb00ff', opacity=1, route_map=route_map) # roze, terugweg

    return route_map


def save_ar3(route_map, route_name):
    import folium
    polylines = []

    for key, val in route_map._children.items():
        if isinstance(val, folium.features.PolyLine):
            polylines.append(val)

    lat_pts = []
    lng_pts = []
    change_pts = []
    # Print the polyline options and data
    for ii in range(len(polylines)):
        type = ''
        if polylines[ii].options['color'] == '#ffff00':
            type = 'heenweg'
            print('heenweg')
        elif polylines[ii].options['color'] == '#FF0000':
            type = 'actie'
            print('actie')
        elif polylines[ii].options['color'] == '#0000FF':
            type = 'deadhead'
            print('deadhead')
        elif polylines[ii].options['color'] == '#fb00ff':
            type = 'terugweg'
            print('terugweg')

        if ii == (len(polylines) - 1):
            lng = [coord[0] for coord in polylines[ii].locations]
            lat = [coord[1] for coord in polylines[ii].locations]
        else:
            lng = [coord[0] for coord in polylines[ii].locations[:-1]]
            lat = [coord[1] for coord in polylines[ii].locations[:-1]]

        # remove duplicates, stupid polylines...
        temp_lat = []
        temp_lng = []

        for ii in range(len(lat)):
            if (lat[ii] not in temp_lat) or (lng[ii] not in temp_lng):
                temp_lat.append(lat[ii])
                temp_lng.append(lng[ii])

        lat = temp_lat
        lng = temp_lng

        lat_pts.extend(lat)
        lng_pts.extend(lng)
        if type != 'actie':
            change_pts.extend([0] * len(lat))
        else:
            change_pts.extend([1] * len(lat))

    distances = []
    cum_distance = 0
    status = 0
    changes = []
    for ii in range(len(lat_pts)):
        if ii == 0:
            dist = 0
        else:
            dist = int(ox.distance.great_circle_vec(lat_pts[ii-1], lng_pts[ii-1], lat_pts[ii], lng_pts[ii]) * 100)
            assert dist > 0, "wtf!"
        cum_distance += dist
        distances.append(cum_distance)

        if change_pts[ii] != status:
            status = change_pts[ii]
            changes.append((cum_distance, status))

    FILE_PATH = "./data/"
    # Open a new text file in write mode
    with open(FILE_PATH + f'{route_name}.ar3', 'w') as file:

        # Write some lines of text to the file
        file.write('Ar3Version: 3\n')
        file.write('Creator: PAJ Versfelt\n')
        file.write('Last edited by: unknown\n')
        file.write('MachineType: standardspreader\n')
        file.write('SoundFiles: \n')
        file.write('RouteID:{route_name}\n')
        file.write('RouteTimestamp: 20230227 12.00.00\n')
        file.write('WayPoints: Longitude, Latitude, DistanceFromStartInCm\n')

        for ii in range(len(lat_pts)):
            file.write(f'WayPoint[{ii}]:{lat_pts[ii]},{lng_pts[ii]},{distances[ii]}\n')

        file.write('ChangePoints: DistanceFromStartInCm, SpreadSprayOnOff, SprayModeOnOff, Max, SecMat,Dosage, WidthLeft, WidthRight, SecDos, WidthLeftSpraying, WidthRightSpraying, CombiPercentage, HopperSelection, Marker, Message, TankSelection\n')
        file.write('ChangePoint[0]:0,0,0,0,1,1000,500,200,500,0,600,30,0,1,,0\n')
        for ii in range(1, len(changes)):
            file.write(f'ChangePoint[{ii}]:{changes[ii][0]},{changes[ii][1]},,,,,,,,,,,,,,\n')
