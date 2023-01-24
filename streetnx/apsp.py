import time
import numpy as np
import multiprocessing as mp
import osmnx as ox
import pandas as pd
import geopandas as gpd

from fibheap import *
from shapely.geometry import LineString

class turn:
    turn_penalty = 0
    def __init__(self, in_edge, out_edge, angle):
        self.in_edge = in_edge
        self.out_edge = out_edge
        self.angle = angle

def travelTime(G, edge, max_speed):
    edge_data = G.get_edge_data(*edge)
    if isinstance(edge_data["length"], list):
        distance = 0
        for i in range(len(edge_data["length"])):
            distance += edge_data["length"][i] / (min(max_speed, edge_data["speed_kph"][i]) / 3.6)
        return distance
    else:
        return edge_data["length"] / (edge_data["speed_kph"] / 3.6)

def highwayType(edge):
    if edge == None:
        return float('inf')
    
    highway_name = edge[3]["highway"]

    if highway_name in {"motorway", "motorway_link"}:
        return 0
    elif highway_name in {"trunk", "trunk_link"}:
        return 1
    elif highway_name in {"primary", "primary_link"}:
        return 2
    elif highway_name in {"secondary", "secondary_link"}:
        return 3
    elif highway_name in {"tertiary", "tertiary_link"}:
        return 4
    elif highway_name in {"residential", "living_street", "unclassified"}:
        return 5
    elif highway_name in {"service", "services", "projected_footway"}:
        return 6

    print(f"ERROR: highway type not found { edge[3] }")
    return float('inf')
    
def setTurnPenalties(G, gamma = 10, minimum_turn_angle = 40):
    G.turn_penalties = {}

    start = time.time()
    for node in G.nodes:
        straights = []
        outgoing_straights = {}
        turns = []

        # for each incoming road (edge) at the intersection (node), determine which outgoing road is the 'straight' road (edge)
        for incoming_edge in list(G.in_edges(node, data = True, keys = True)):
            in_edge = (incoming_edge[0], incoming_edge[1], incoming_edge[2])

            straight = None
            incoming_road_type = highwayType(incoming_edge)

            for outgoing_edge in list(G.out_edges(node, data = True, keys = True)):
                out_edge = (outgoing_edge[0], outgoing_edge[1], outgoing_edge[2])
                if (incoming_edge[0] == outgoing_edge[1]) and (incoming_edge[2] == outgoing_edge[2]) and (outgoing_edge[3]['length'] == incoming_edge[3]['length']):
                    G.turn_penalties[(in_edge, out_edge)] = float('inf')
                    continue # cannot perform u-turns todo, is this correct? are edge lenghts the same?
                angle = ox.utils_geo.angle(G, incoming_edge, outgoing_edge) # calculate angle between the two edges
                if angle < 0: 
                    angle = 360 + angle

                road_turn = turn(incoming_edge, outgoing_edge, angle)
                turns.append(road_turn)

                # Determine whether this turn could be the straight turn
                if angle < minimum_turn_angle or angle > 360 - minimum_turn_angle: # if the angle is less than 35 degrees or greater than 325 degrees
                    continue
                # elif inverse of out == in, then this is a u-turn 
                if straight is None:
                    straight = road_turn
                    continue

                # A situation can happen where a crossroad has multiple outgoing roads of various road types.
                # Then the outgoing roads which are relatively the same type of road as the incoming road
                # are considered to be potential better candidates for the straight road.
                if abs(highwayType(straight.out_edge) - incoming_road_type) > 1:
                    if abs(highwayType(outgoing_edge) - incoming_road_type) <= 1:
                        # if the difference between road types is greater than 1, then this is not a potential straight road
                        straight = road_turn
                    elif abs(180 - angle) < abs(180 - straight.angle):
                        # if the angle between the two roads is less than the current straight road, then this is the new straight road
                        straight = road_turn
                    # TODO WHAT IF THE ANGLES ARE VERY CLOSELY ALIGNED BUT NOT EXACTLY? THE STRAIGHT ROAD COULD BE DIFFERENT
                    elif abs(180 - angle) == abs(180 - straight.angle):
                        print("does this ever happen?")
                        # determine whether the new turn is on the right hand side of the current straight turn
                        # if it is, this means that the new turn is the new straight turn
                else: 
                    # else, the straight road is roughly the same type as the incoming road
                    if abs(highwayType(outgoing_edge) - incoming_road_type) > 1:
                        # if the difference between road types is greater than 1, then this is not a potential straight road
                        continue
                    if abs(180 - angle) < abs(180 - straight.angle):
                        # if the angle between the two roads is less than the current straight road, then this is the new straight road
                        straight = road_turn
                    # TODO WHAT IF THE ANGLES ARE VERY CLOSELY ALIGNED BUT NOT EXACTLY? THE STRAIGHT ROAD COULD BE DIFFERENT
                    elif abs(180 - angle) == abs(180 - straight.angle):
                        print("does this ever happen?")
                        # determine whether the new turn is on the right hand side of the current straight turn
                        # if it is, this means that the new turn is the new straight turn

            # add the straight road to the straight roads of the intersection (node)
            if straight == None:
                continue
            if (straight.out_edge[0], straight.out_edge[1], straight.out_edge[2]) not in outgoing_straights:
                outgoing_straights[(straight.out_edge[0], straight.out_edge[1], straight.out_edge[2])] = []
            outgoing_straights[(straight.out_edge[0], straight.out_edge[1], straight.out_edge[2])].append(straight)

        # if only one outgoing road (edge) is possible, add all to_straights to the straights
        # and later determine which of these straight is the one straight to rule them all. 
        # One straight to find them, one straight to bring them all and in the darkness bind them.
        if len(list(G.out_edges(node, data = True))) == 1:
            straights += list(outgoing_straights.values())[0] if len(outgoing_straights) != 0 else []
        else:
            # multiple outgoing roads (edges) are possible and thus the best straight must be determined for each incomming road (edge)
            # for each outgoing road (edge), determine which incoming road (edge) is the true straight.
            for edge in list(outgoing_straights.keys()):
                best = None
                for road_turn in outgoing_straights[edge]:
                    if best == None:
                        # no best turn has been found yet, so this turn is the best turn
                        best = road_turn
                        continue

                    if abs(highwayType(road_turn.out_edge) - highwayType(road_turn.in_edge)) <= 1 and abs(highwayType(road_turn.out_edge) - highwayType(best.in_edge)) > 1:
                        # the considered turn is rouhgly the same type as the outgoing road (edge) and the current best turn is not
                        best = road_turn
                    elif abs(highwayType(road_turn.out_edge) - highwayType(road_turn.in_edge)) <= 1 and abs(highwayType(road_turn.out_edge) - highwayType(best.in_edge)) <= 1:      
                        # the best and considered turn are rouhgly the same type as the outgoing road (edge)
                        if abs(180 - road_turn.angle) < abs(180 - best.angle):       
                            # this turn is better than the current best turn                 
                            best = road_turn
                        elif abs(180 - road_turn.angle) == abs(180 - best.angle):
                            # TODO WHAT IF THE ANGLES ARE VERY CLOSELY ALIGNED BUT NOT EXACTLY? THE STRAIGHT ROAD COULD BE DIFFERENT
                            print("does this ever happen?")
                    elif abs(highwayType(road_turn.out_edge) - highwayType(road_turn.in_edge)) > 1 and abs(highwayType(road_turn.out_edge) - highwayType(best.in_edge)) > 1:                     
                       # the best and considered turn are not roughly the same type as the outgoing road (edge)
                        if abs(180 - road_turn.angle) < abs(180 - best.angle):    
                            # this turn is better than the current best turn                    
                            best = road_turn
                        elif abs(180 - road_turn.angle) == abs(180 - best.angle):
                            # TODO WHAT IF THE ANGLES ARE VERY CLOSELY ALIGNED BUT NOT EXACTLY? THE STRAIGHT ROAD COULD BE DIFFERENT
                            print("does this ever happen?")
                
                # add the best turn to the straights
                if best == None: continue
                straights.append(best)

        in_edge_straight_turns = {}
        # map all incoming streets (edges) of the intersection (node) to the straights, such that ?? TODO
        for road_turn in straights:
            in_edge_straight_turns[(road_turn.in_edge[0], road_turn.in_edge[1], road_turn.in_edge[2])] = road_turn

        for road_turn in turns:
            if "junction" in road_turn.in_edge[3].keys() and bool({"circular", "roundabout"} & {road_turn.in_edge[3]["junction"][0]}):
                # turn is onto a roundabout, no penalty is applied
                road_turn.penalty = 0
            elif (road_turn.in_edge[0] == road_turn.out_edge[1]) and (road_turn.in_edge[2] == road_turn.out_edge[2]):
                # turn is a u-turn, which is prohibited
                road_turn.penalty = float('inf')
            elif (abs(road_turn.angle) < minimum_turn_angle or abs(road_turn.angle) > 360 - minimum_turn_angle):
                # turn angle is too tight
                road_turn.penalty = float('inf')
            elif road_turn in straights:
                # turn is a straight
                road_turn.penalty = 0
            elif (road_turn.in_edge[0], road_turn.in_edge[1], road_turn.in_edge[2]) in in_edge_straight_turns:
                # if a straight turn was previously identified for the incoming road (edge) of the road_turn
                # then the penalty is the difference between the angle of the turn and the angle of the straight
                if road_turn.angle >= in_edge_straight_turns[(road_turn.in_edge[0], road_turn.in_edge[1], road_turn.in_edge[2])].angle:
                    road_turn.penalty = 1 * gamma
                else:
                    road_turn.penalty = 5 * gamma
            else:
                if road_turn.angle > 180:
                    road_turn.penalty = 1 * gamma
                else:
                    road_turn.penalty = 5 * gamma

            in_edge = (road_turn.in_edge[0], road_turn.in_edge[1], road_turn.in_edge[2])
            out_edge = (road_turn.out_edge[0], road_turn.out_edge[1], road_turn.out_edge[2])
            # add the turns to the graph
            # save edges with keys as: (start_osmid, start_key, mid_osmid, end_osmid, end_key)
            G.turn_penalties[(in_edge, out_edge)] = road_turn.penalty

    end = time.time()
    print(f"Turn penalties calculated in {round(end - start, 1)} seconds")

# calculate the travel time from the endpoint of the source_edge to the endpoint of the required_edges
def dijkstra(G, source_edge, required_edges, max_speed = 100):

    dur = dict.fromkeys(list(G.edges(keys=True)), float('inf'))
    prev = dict.fromkeys(list(G.edges(keys=True)), None)
    unvisited = set(required_edges)

    Q = makefheap()
    fheappush(Q, (0, source_edge))

    while Q.num_nodes > 0:
        heap_node = Q.extract_min()
        travel_time = heap_node.key[0]
        in_edge = heap_node.key[1]

        # Only remove the edge from the unvisited set
        # if the edge isn't the first edge in the heap
        if in_edge != source_edge:
            unvisited.discard(in_edge)
        
        # if we've visited all targets, we're done
        if len(unvisited) == 0:
            break

        for out_edge in G.out_edges(in_edge[1], keys = True):
            turn_penalty = G.turn_penalties[(in_edge, out_edge)]

            # Do not add a travel time if the in_edge is the source_edge
            # as we calculate the travel times between the endpoint of the source_edge to the endpoints of other edges
            # and thus if the in_edge is the source_edge, then no travel time is occured
            duration = travel_time + turn_penalty + (travelTime(G, in_edge, max_speed) if in_edge != source_edge else 0)
            if duration < dur[out_edge]:
                dur[out_edge] = duration
                prev[out_edge] = in_edge
                fheappush(Q, (dur[out_edge], out_edge))

    index = required_edges.index(source_edge)
    if index % 100 == 0 and index != 0:
        print(f"Completed asps for {index} of {len(required_edges)}")

    # return the distances corresponding to the targets and all previous edges
    return {t: dur[t] for t in required_edges}, {t: prev[t] for t in prev}

def constructPaths(G, from_edge : tuple, predecessors : dict, required_edges : list, nodes = True):
    # predecessors: keys are edges and values are previous edges
    paths_coordinates = []
    paths_nodes = []
    # construct the coordinate path from the end of edge to the start of the required edge
    for required_edge in required_edges:
        path = []
        nodes_path = []
        edge = predecessors[required_edge]
        while edge != from_edge and edge != None:
            prev_edge_data = G.get_edge_data(*edge)
            if "geometry" in prev_edge_data:
                coords = list(prev_edge_data["geometry"].coords)
                coords = [coords[i] for i in range(len(coords)) if i == 0 or coords[i] != coords[i-1]]
            else:
                u = edge[0]
                v = edge[1]
                coords = [(G.nodes[u]["x"], G.nodes[u]["y"]), (G.nodes[v]["x"], G.nodes[v]["y"])]
            path = coords[1:] + path
            nodes_path = [edge[1]] + nodes_path
            edge = predecessors[edge]
        path = [(G.nodes[from_edge[1]]["x"], G.nodes[from_edge[1]]["y"])] + path
        nodes_path = [from_edge[1]] + nodes_path
        paths_coordinates.append(path)
        paths_nodes.append(nodes_path)
    return paths_coordinates if nodes == False else paths_nodes

if __name__ == '__main__':

    print("Loading graph from parquet file...")
    # load df from parquet
    df_edges = pd.read_parquet("./data/Rotterdam_bereik_edges.parquet")
    df_nodes = pd.read_parquet("./data/Rotterdam_bereik_nodes.parquet")

    df_edges.to_json("./data/asps_output/Rotterdam_bereik_edges.json")
    df_nodes.to_json("./data/asps_output/Rotterdam_bereik_nodes.json")

    # convert df to gdf
    gdf_nodes = gpd.GeoDataFrame(df_nodes, geometry = gpd.points_from_xy(df_nodes.x, df_nodes.y))
    edge_geometry = df_edges["geometry"].apply(lambda x: LineString(x.tolist()))
    gdf_edges = gpd.GeoDataFrame(df_edges, geometry = edge_geometry)

    # convert np.arrays to lists when applicable
    for col in gdf_edges.columns:
        if not gdf_edges[col].apply(lambda x: not isinstance(x, np.ndarray)).all():
            gdf_edges[col] = [value if not isinstance(value, np.ndarray) else value.tolist() for value in gdf_edges[col]]

    # create graph from gdf
    G = ox.graph_from_gdfs(gdf_nodes = gdf_nodes, gdf_edges = gdf_edges)
    depot_nodes = df_nodes[df_nodes['highway'] == 'poi'].index.values
    print("Graph loaded from parquet file.")

    print("Calculating turn penalties...")
    setTurnPenalties(G, gamma = 3)
    print("Turn penalties calculated.")

    # selected required edges
    required_edges = [
        (edge[0], edge[1], edge[2]) 
        for edge in G.edges(data=True, keys = True)
    #     if bool(set(edge[3]["highway"]) & {"primary", "primary_link", "secondary", "secondary_link", "projected_footway"})
    ]
    required_edges_data = [
        edge[3]
        for edge in G.edges(data=True, keys = True)
    #     if bool(set(edge[3]["highway"]) & {"primary", "primary_link", "secondary", "secondary_link", "projected_footway"})
    ]

    # test if edges are reachable.
    temp_distances = dijkstra(G, required_edges[0], required_edges)[0]

    for (key,value) in temp_distances.items():
        if value == float('inf'):
            if key[0] in depot_nodes or key[1] in depot_nodes:
                continue
            print(f"Removing edge {key} from required edges, as it is not reachable.")
            index = required_edges.index(key)
            del required_edges[index]
            del required_edges_data[index]
                
    # convert required_edges_data to a dataframe
    # to save the dataframe to a parquet file
    df_required_edges = pd.DataFrame(
        required_edges_data, 
        index = required_edges, 
        columns = ['lanes', 'length', 'lanes:forward', 'lanes:backward', 'turn:lanes', 'speed_kph', 'oneway', 'geometry']
    )

    # Average the x,y coordinates of the required edge
    # to an average coordinate for the routing optimisation
    coordinates = []
    for i in range(len(required_edges)):
        coordinates_x = [x for x,y in list(df_required_edges.iloc[i]['geometry'].coords)]
        coordinates_y = [y for x,y in list(df_required_edges.iloc[i]['geometry'].coords)]
        avg_x = sum(coordinates_x) / len(coordinates_x)
        avg_y = sum(coordinates_y) / len(coordinates_y)
        coordinates.append((avg_x, avg_y))

    df_required_edges['geometry'] = coordinates

    # Get the indices of edges that are connected to a depot node
    depot_edge_indices = []
    for i, edge in enumerate(required_edges):
        if edge[0] in depot_nodes:
            depot_edge_indices.append(i)

    for i, edge in enumerate(required_edges):
        if edge[1] in depot_nodes:
            depot_edge_indices.append(i)
    
    df_required_edges.to_parquet(f"./data/asps_output/Rotterdam_edges.parquet.gzip", engine='pyarrow', compression='GZIP')
    
    distance_df_workers = pd.DataFrame(index = required_edges, columns = required_edges)
    path_df_workers = pd.DataFrame(index = required_edges, columns = required_edges)

    print("Start calculating distances")
    print(f"{len(required_edges)}")

    MAX_SPEED = 100

    start = time.time()
    args = [(G, edge, required_edges, MAX_SPEED) for edge in required_edges]
    with mp.Pool(processes=mp.cpu_count()) as pool:
        results = pool.starmap(dijkstra, args)
    end = time.time()
    print("-------------------------------------------")
    print(f"With workers completed in {round(end-start,2)}")

    for i in range(len(required_edges)):
        mask = (distance_df_workers.index == required_edges[i])
        distance_df_workers.loc[mask, results[i][0].keys()] = list(results[i][0].values())

    distance_df_workers.columns = [str(i) for i in range(len(required_edges))]
    distance_df_workers.to_parquet(f"./data/asps_output/Rotterdam_distances.parquet.gzip", engine='pyarrow', compression='GZIP')
    distance_df_workers.to_json(f"./data/asps_output/Rotterdam_distances.json")

    # save the depots nodes to a df
    df_depots = pd.DataFrame(depot_nodes, columns = ["depots"])
    df_depots.to_parquet(f"./data/asps_output/Rotterdam_depots.parquet.gzip", engine='pyarrow', compression='GZIP')

    start = time.time()
    args = [
        (G, edge, results[required_edges.index(edge)][1], required_edges) 
        for edge in required_edges 
        if edge[1] not in depot_nodes # skip over edges that are going into the depot
    ] 
    with mp.Pool(processes=mp.cpu_count()) as pool:
        results = pool.starmap(constructPaths, args)
    end = time.time()
    print("-------------------------------------------")
    print(f"With workers completed in {round(end-start,2)}")

    for i in range(len(args)):
        edge = args[i][1]
        mask = (distance_df_workers.index == edge)
        path_df_workers.loc[mask, :] = results[i]

    path_df_workers.columns = [str(i) for i in range(len(required_edges))]
    path_df_workers.to_parquet(f"./data/asps_output/Rotterdam_paths.parquet.gzip", engine='pyarrow', compression='GZIP')

    from plot_route import _plot_route
    route_map = _plot_route([30, 154], G, path_df_workers, depot_edge_indices)
    route_map.save(outfile= "./data/asps_output/solution.html")