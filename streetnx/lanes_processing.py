import pandas as pd
import re
import math

from streetnx import utils as snx_utils

def save_lanes(name, required_edges_df, distances_df, depots_list):
    
    (
        distances,
        decode_map,
        encoded_depots
    ) = encode_distances(distances_df, depots_list)

    edge_travel_time = snx_utils.get_edge_travel_times(required_edges_df)
    edge_lengths = snx_utils.get_edge_lengths(required_edges_df)
    edge_lanes = get_lanes(required_edges_df)
    reverse_edge_map = map_reverses(required_edges_df, edge_lengths, depots_list)
    lanes = create_lanes(edge_lanes, edge_lengths, edge_travel_time, reverse_edge_map, required_edges_df["average_geometry"].values)

    to_remove = set()

    for i in range(len(lanes)):
        lane = lanes[i]
        if lane['reverse'] is not None:
            if (lane['gritted_lanes'] == 1 and lanes[lane['reverse']]['gritted_lanes'] == 3):
                to_remove.add(i)

    depot_map = {}
    for depot in depots_list:
        depot_map[depot] = {
            'outgoing': None,
            'incoming': None
        }

    # variable that contains all travel times in seconds between all edges
    for i in range(len(lanes)):
        value = lanes[i]
        # get edge from edge_df corresponding to the edge_ID in the value
        edge_index = required_edges_df.index[value['edge_ID']]
        if edge_index[0] in depots_list:
            depot_map[edge_index[0]]['outgoing'] = i
        elif edge_index[1] in depots_list:
            depot_map[edge_index[1]]['incoming'] = i

    # write each row of distances to a txt file
    with open('./data/' +  name + '_distances.txt', 'w') as f:
        f.write(str(len(distances)) + "\n")
        for row in distances:
            line = str(row)
            line = line.replace("[", "")
            line = line.replace("]", "")
            f.write(line)
            f.write("\n")

        # encoded depots to json file
    with open('./data/' +  name + '_depots.txt', 'w') as f:
        f.write(str(len(depot_map)) + "\n")
        for depot in depot_map:
            value = depot_map[depot]
            f.write(
                str(depot) + " " 
                + str(value['outgoing']) + " " 
                + str(value['incoming']) 
                + "\n"
            )
                
        # reverse edge map to json file
    with open('./data/' +  name + '_lanes.txt', 'w') as f:
        f.write(str(len(lanes)) + "\n")
        for value in lanes.values():
            f.write(
                str(value["edge_ID"]) + " "
                + str(value["gritted_lanes"]) + " "
                + str(value["length"]) + " "
                + str(value["travel_time"]) +  " "
                + str(value["x"]) + " "
                + str(value["y"]) + " "
                + str(value["reverse"])
                + "\n"
            )

   
def encode_distances(distances_df : pd.DataFrame, depots : list):
    """
    Convert a distances dataframe, indexed by edges, to a numpy array indexed by integers.
    Where the first indices are the outgoing edges from the depots, followed by the incoming edges to the depots. 
    Hereafter, the remaining edges.

    Parameters
    ----------
    distances : pd.DataFrame
        input distances dataframe
    depots : list
        list of depot nodes

    Returns
    -------
    tuple (encoded_distances, decode_map, encoded_depots)
        encoded_distances : np.array
            numpy array of distances indexed by integers
        decode_map : dict
            dictionary mapping integers to edges
        encoded_depots : set
            set of depot nodes encoded as integersv
    """
    
    def encode_edges(decode_map, edges):
        """
        Encode a list of edges into a list of integers, and update the decode map.
        """
        iterator = len(decode_map)
        for edge in edges:
            decode_map[iterator] = edge
            iterator += 1
        return decode_map

    # Create a dictionary mapping edges to integers
    decode_map = encode_edges({}, distances_df.index)
 
    # Create a dictonary of the depot nodes encoded as integers
    # containing the index of the outgoing and incoming edges
    encoded_depots = {}
    for depot_idx in range(len(depots)):
        depot = list(depots)[depot_idx]
        outgoing = None
        incoming = None

        for idx in range(len(decode_map)):
            edge = decode_map[idx]
            if edge[0] == depot:
                outgoing  = idx
            if edge[1] == depot:
                incoming = idx

        encoded_depots[depot_idx] = {
            "outgoing" : outgoing,
            "incoming" : incoming,
            "depot" : depot
        }

    return distances_df.values.tolist(), decode_map, encoded_depots


def get_lanes(edge_df):
    # if lanes is nan, return 0
    return [int(value) if value == value else 0 for value in edge_df["lanes"].values]


def map_reverses(edge_df, edge_lengths, depots):
    # map (from, to, key) to an index
    index_map = {}
    for i in range(len(edge_df.index)):
        index_map[(edge_df.index[i][0], edge_df.index[i][1], edge_df.index[i][2])] = i
        
    reverse_map = {}
    max_key = max([k for u,v,k in index_map.keys()])

    # iterate through all edges
    for (start, end, key) in index_map:

        # do not map reverse edges of the depots
        if start in depots or end in depots:
            continue

        index = index_map[(start, end, key)]
        length_index = edge_lengths[index]

        # iterate though all edges with the same start and end, but reversed
        for i in range(0, max_key + 1):
            if (end, start, i) in index_map:
                reverse_index = index_map[(end, start, i)]
                length_reverse_index = edge_lengths[reverse_index]

                # check if the length of the reverse edge is the same
                if abs(length_index - length_reverse_index) < 0.1:

                    # set the reverse edge
                    reverse_map[index] = reverse_index
                    
    return reverse_map


def create_lanes(
    edge_lanes, 
    edge_lengths, 
    edge_travel_time, 
    reverse_map, 
    edge_coords, 
    parallel_lanes=3, 
    lane_width=3.5
):
    assert parallel_lanes == 3, "Currently, only max_lanes=3 is supported"

    lane_ID = 0
    lanes_map = {}
    edge_to_lane = {}
    for i in range(len(edge_lanes)):
        lanes = edge_lanes[i]
        temp_lanes = lanes
        required_passes = math.ceil(lanes / parallel_lanes)
        edge_to_lane[i] = []

        for j in range(required_passes):
            edge_to_lane[i].append(lane_ID)

            if i in reverse_map:
                reverse_edge_index = reverse_map[i]
                reverse_lanes = edge_lanes[reverse_edge_index]

                if reverse_lanes <= 1 and lanes <= 2:
                    temp_lanes += reverse_lanes
                    assert required_passes == 1, 'This should not happen'
                elif reverse_lanes <= 2 and lanes <= 1:
                    temp_lanes += reverse_lanes
                    assert required_passes == 1, 'This should not happen'

            assert temp_lanes > 0, 'This should not happen'

            lanes_map[lane_ID] = {
                "edge_ID": i,
                "gritted_lanes": min(temp_lanes, parallel_lanes),
                "length": edge_lengths[i],
                "travel_time": edge_travel_time[i],
                "x": float(re.findall(r'\d+\.\d+', edge_coords[i])[0]),
                "y": float(re.findall(r'\d+\.\d+', edge_coords[i])[1]),
                "reverse": None
            }
            temp_lanes -= parallel_lanes
            lane_ID += 1

    # TODO: implement logic to account for the number of lanes gritted
    # TODO implement logic to account for the penalty when gritting opposite lanes

    # For example,
    # if edge_1 has 2 lanes, and edge_2 has 1 lane, then both lanes can be gritted at the same time.
    # However, the edges could also be gritted in two passes: once via edge_1 and once via edge_2.
    # Thus no penalty of gritting the opposite lanes would be incurred.

    for edge_u, edge_v in reverse_map.items():
        # quick and dirty way to set the reverse edges, not accouting for opposite lanes gritting penalties

        if (edge_lanes[edge_u], edge_lanes[edge_v]) in {(1,1), (2,1), (1,2)}:
            lane_u_ID = edge_to_lane[edge_u][0]
            lane_v_ID = edge_to_lane[edge_v][0]
            lanes_map[lane_u_ID]["reverse"] = lane_v_ID

    return lanes_map



# def process_turn_lanes(G, node: int, parallel_gritting = 3):

#     print(node)

#     in_edges = G.in_edges(node)
#     out_edges = G.out_edges(node)

#     for in_edge in in_edges:
#         for out_edge in out_edges:


#     return G
