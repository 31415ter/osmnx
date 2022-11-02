import os
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
    
    highway_name = set(edge[3]["highway"])

    if bool(highway_name & {"motorway", "motorway_link"}):
        return 0
    elif bool(highway_name & {"trunk", "trunk_link"}):
        return 1
    elif bool(highway_name & {"primary", "primary_link"}):
        return 2
    elif bool(highway_name & {"secondary", "secondary_link"}):
        return 3
    elif bool(highway_name & {"tertiary", "tertiary_link"}):
        return 4
    elif bool(highway_name & {"residential", "living_street", "unclassified"}):
        return 5
    elif bool(highway_name & {"service", "services"}):
        return 6

    print(f"ERROR: highway type not found {highway_name}")
    return float('inf')
    
def setTurnPenalties(G, gamma = 3):
    G.turn_penalties = {}

    start = time.time()
    for node in G.nodes:
        straights = []
        outgoing_straights = {}
        turns = []

        if node == 735629288:
            print()
        # for each incoming road (edge) at the intersection (node), determine which outgoing road is the 'straight' road (edge)
        for incoming_edge in list(G.in_edges(node, data = True, keys = True)):
            straight = None
            incoming_road_type = highwayType(incoming_edge)

            for outgoing_edge in list(G.out_edges(node, data = True, keys = True)):
                if (incoming_edge[0] == outgoing_edge[1]) and (incoming_edge[2] == outgoing_edge[2]):
                    G.turn_penalties[(incoming_edge[0], incoming_edge[2], incoming_edge[1], outgoing_edge[1], outgoing_edge[2])] = float('inf')
                    continue # cannot perform u-turns todo, is this correct? are edge lenghts the same?
                angle = ox.utils_geo.angle(G, incoming_edge, outgoing_edge) # calculate angle between the two edges
                if angle < 0: angle = 360 + angle

                road_turn = turn(incoming_edge, outgoing_edge, angle)
                turns.append(road_turn)

                # Determine whether this turn could be the straight turn
                if abs(angle) < 35 or angle > 325: # if the angle is less than 35 degrees or greater than 325 degrees
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
            straights += list(outgoing_straights.values())[0]
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
            if "junction" in road_turn.in_edge[3].keys() and bool({"circular", "roundabout"} & {road_turn.in_edge[3]["junction"]}):
                # turn is onto a roundabout, no penalty is applied
                road_turn.penalty = 0
            elif (road_turn.in_edge[0] == road_turn.out_edge[1]) and (road_turn.in_edge[2] == road_turn.out_edge[2]):
                # turn is a u-turn, which is prohibited
                road_turn.penalty = float('inf')
            # elif (abs(road_turn.angle) < 45 or abs(road_turn.angle) > 315) and (True in road_turn.in_edge[3]['oneway'] and True in road_turn.out_edge[3]['oneway']):
            #     # turn is very tight, which is prohibited
            #     road_turn.penalty = float('inf')
            elif (abs(road_turn.angle) < 45 or abs(road_turn.angle) > 315):
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

            G.turn_penalties[(road_turn.in_edge[0], road_turn.in_edge[2], road_turn.in_edge[1], road_turn.out_edge[1], road_turn.out_edge[2])] = road_turn.penalty

    end = time.time()
    print(f"Turn penalties calculated in {round(end - start, 1)} seconds")
    print()

# calculate the travel time from the endpoint of the source_edge to the endpoint of the required_edges
def dijkstra(G, source_edge, required_edges, max_speed = 100):
    start = time.time()

    dist = dict.fromkeys(list(G.edges(keys=True)), float('inf'))
    dist[source_edge] = 0

    prev = dict.fromkeys(list(G.edges(keys=True)), None)

    unvisited = set(required_edges)
    unvisited.discard(source_edge)    

    Q = makefheap()
    fheappush(Q, (0, source_edge))

    while Q.num_nodes > 0:
        heap_node = Q.extract_min()
        travel_time = heap_node.key[0]
        in_edge = heap_node.key[1]
        unvisited.discard(in_edge)
        
        # if we've reached all targets, we're done
        if len(unvisited) == 0:
            break

        for out_edge in G.out_edges(in_edge[1], keys = True):
            turn_penalty = 0#G.turn_penalties[(in_edge[0], in_edge[2], in_edge[1], out_edge[1], out_edge[2])]
            alt = travel_time + turn_penalty + travelTime(G, out_edge, max_speed)
            if alt < dist[out_edge]:
                dist[out_edge] = alt
                prev[out_edge] = in_edge
                fheappush(Q, (dist[out_edge], out_edge))

    print(f"PPID {os.getppid()}->{os.getpid()} Completed in {round(time.time() - start,2)} seconds.")

    # return the distances corresponding to the targets and all prev where non None
    return {t: dist[t] for t in required_edges if t != source_edge}, {t: prev[t] for t in prev if (prev[t] is not None or t == source_edge)}

if __name__ == '__main__':
    # load df from parquet
    df_edges = pd.read_parquet("./data/Rotterdam_edges.parquet")
    df_nodes = pd.read_parquet("./data/Rotterdam_nodes.parquet")

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

    # TODO: determine inverse edge mapping?

    # save graph for comparison purposes
    #ox.save_graph_geopackage(G, filepath="./data/Rotterdam_network.gpkg", directed = True)

    setTurnPenalties(G, gamma = 3)

    # selected required edges
    required_edges = [
        (edge[0], edge[1], edge[2]) 
        for edge in G.edges(data=True, keys = True) 
        if bool(set(edge[3]["highway"]) & {"primary", "primary_link", "secondary", "secondary_link"})
    ]

    # process distances in batches to ease memory usage
    edge_count = 1

    distance_df_workers = pd.DataFrame(index = required_edges[0:edge_count], columns = required_edges)
    path_df_workers = pd.DataFrame(index = required_edges[0:edge_count], columns = required_edges)

    distance_df_non_workers = pd.DataFrame(index = required_edges, columns = required_edges)
    path_df_non_workers = pd.DataFrame(index = required_edges, columns = required_edges)

    print("Start calculating distances")

    MAX_SPEED = 100

    start = time.time()
    args = [(G, edge, required_edges, MAX_SPEED) for edge in required_edges[0:edge_count]]
    with mp.Pool(processes=mp.cpu_count()) as pool:  
        results = pool.starmap(dijkstra, args)
    end = time.time()
    print("-------------------------------------------")
    print(f"With workers completed in {round(end-start,2)}")

    for i in range(len(required_edges[0:edge_count])):
        mask = (distance_df_workers.index == required_edges[i])
        distance_df_workers.loc[mask, results[i][0].keys()] = list(results[i][0].values())

    distance_df_workers.columns = [str(i) for i in range(len(required_edges))]
    distance_df_workers.to_parquet(f"./data/Rotterdam_distance_{0}_{edge_count}.parquet.gzip", engine='pyarrow', compression='GZIP')

    def constructCoordinatePaths(G, from_edge : tuple, predecessors : dict, required_edges : list):
        # predecessors: keys are edges and values are previous edges
        paths_coordinates = {}
        # construct the coordinate path from the end of edge to the end of the required edge
        for required_edge in required_edges:
            # if required_edge == from_edge:
            #     continue
            path = []
            edge = required_edge
            while edge is not None and edge != from_edge:
                prev_edge_data = G.get_edge_data(*edge)
                if "geometry" in prev_edge_data:
                    coords = list(prev_edge_data["geometry"].coords)
                else:
                    u = edge[0]
                    v = edge[1]
                    coords = [(G.nodes[u]["x"], G.nodes[u]["y"]), (G.nodes[v]["x"], G.nodes[v]["y"])]
                path = coords[1:] + path
                print(G.turn_penalties[(predecessors[edge][0], predecessors[edge][2], predecessors[edge][1], edge[1], edge[2])])
                print(f"{edge} - {predecessors[edge]}")
                edge = predecessors[edge]
            path = [(G.nodes[from_edge[1]]["x"], G.nodes[from_edge[1]]["y"])] + path
            paths_coordinates[required_edge] = path
        return paths_coordinates

    # for edge in required_edges[0:edge_count]:
    #     mask = (distance_df_workers.index == required_edges[i])
    #     path_df_workers.loc[mask, :] = constructCoordinatePaths(G, edge, results[required_edges.index(edge)][1], required_edges)

    # path_df_workers

    pd.DataFrame(
        constructCoordinatePaths(G, required_edges[0:edge_count][0], results[required_edges.index(required_edges[0:edge_count][0])][1], [(44088701, 4247298055, 0)])[(44088701, 4247298055, 0)], columns = ["x", "y"]
        ).to_csv("./data/paths/test.csv", sep=',')
    path_df_workers