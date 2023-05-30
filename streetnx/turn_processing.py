import math
from osmnx import utils as ox_utils
from streetnx.highway_type import HighwayType
from streetnx import penalties

# check if two lists have a value in common
def _has_common_value(list1, list2):
    set1 = set(list1)
    for value in list2:
        if value in set1:
            return True
    return False


def _split_turn_types(turn_types: str, parts_max_size: int):
    """
    This function takes a string of turn types and splits it into parts. 
    Each part has a maximum size as specified. The splitting preserves 
    the relative order of the turns and takes care of some specific balancing rules.
    
    Parameters:
    turn_types (str): A string of turn types, each separated by '|'. 
                      This string may come from a list, in which case the last element is chosen.
    max_size (int): Maximum size of each part after the split.

    Returns:
    list: List of strings. Each string is a part with turn types.
    """    
    # If turn_types is a list, select the last item
    if isinstance(turn_types, list):
        turn_types = turn_types[-1]

    # Split the string of turn types into a list, replacing empty strings with 'misc'
    turn_types_list = [turn_type if turn_type != '' else 'misc' for turn_type in turn_types.split('|')]

    num_turns = len(turn_types_list)
    num_parts = math.ceil(num_turns / parts_max_size)

    parts = [] # List to store the parts
    i = 0 # Initialize the index to start iterating through the turn types list
    for _ in range(num_parts):
        part = [] # Initialize the list for the current part
        while i < len(turn_types_list) and len(part) < parts_max_size:
            # Extract the current turn
            current_turn = turn_types_list[i]

            # Check if the previous turn is not the same as the current turn
            previous_turn_not_same = part and not _has_common_value(current_turn.split(';'), part[-1].split(';'))

            # Check if the next turn is the same as the current turn
            next_turn_same = i + 1 < len(turn_types_list) and _has_common_value(current_turn.split(';'), turn_types_list[i + 1].split(';'))

            # Calculate the number of parts left
            parts_left = math.ceil((len(turn_types_list)-i) / parts_max_size)

            # Check if the current part needs balancin
            balancing = (
                parts_left == 1 
                and num_turns - i == len(part) 
                and not next_turn_same 
                and previous_turn_not_same
                and i + 1 < len(turn_types_list)
            )           
            
            # If the current turn should not be added to the current part due to balancing rules, break the while loop
            if (
                previous_turn_not_same
                and next_turn_same 
                and parts_left != num_parts - len(parts) 
                or balancing
            ):
                break

            # Add the current turn to the current part
            part.append(current_turn)

            # Move to the next turn
            i += 1

        # Add the current part to the parts list
        parts.append('|'.join(part))

    return parts


def _edge_highest_key_map(graph):
    """
    This function returns a map that assigns the highest key found to each edge (u, v) in the graph.
    
    Parameters:
    graph (object): The input graph object. Assumes it has an edges method returning all edges.

    Returns:
    dict: A dictionary with edges as keys (u, v) and the corresponding highest keys as values.
    """    
    # Initialize an empty dictionary to store the highest key for each edge
    highest_key = {}

    # Get all edges from the graph, including keys
    edges = graph.edges(keys=True)

    for edge in edges:
        # Destructure the edge tuple into its constituent parts
        (u, v, key) = edge
        edge_pair = (u, v)
        
        # Check if the edge pair is not in the highest_key map or if the current key is higher than the stored key
        if (edge_pair) not in highest_key or highest_key[edge_pair] < key:
            # Update the highest_key map with the current key
            highest_key[edge_pair] = key

    # Return the highest_key map
    return highest_key


def _get_last_element_from_string_or_list(input_data):
    """
    This function takes an input that is either a string or a list.
    If the input is a list, returns the last element. 
    If the input is a string, it treats it as a comma-separated list enclosed by square brackets. 
    If the input is neither a string nor a list, it returns an empty string.

    Parameters:
    input_data (str or list): The input data to process.

    Returns:
    str: The last element from the processed input.
    """
    # Check if input is a string
    if isinstance(input_data, str):
        # Remove square brackets, spaces, and quotes from the string
        cleaned_string = input_data.replace('[', '').replace(']', '').replace(' ', '').replace('\'', '')

        # Split the cleaned string into elements using comma as a separator
        elements = cleaned_string.split(',')

        # Return the last element if there are more than one element, otherwise return the cleaned string
        return elements[-1] if len(elements) > 1 else cleaned_string
    
    # Check if input is a list
    elif isinstance(input_data, list):
        # Return the last element from the list
        return input_data[-1]
    
    # Return an empty string if input_data is neither a string nor a list
    return ''


def _get_turn_information(graph, edge, incoming=True):
    """
    Function to get outgoing turns in a given graph at a specified edge.
    
    Parameters:
    graph (object): Graph data structure containing nodes and edges. It also includes the 'turns' and 'edges' attributes.
    edge (tuple): A tuple consisting of the start node (u), end node (v), and key of the edge.
    incoming (bool): Indicates whether the incoming or outgoing turns are retrieved

    Returns:
    list: Returns a list of tuples. Each tuple consists of:
        - Name of the turn type for the incomming/outgoing edge towards the input edge
        - Number of lanes for the incomming/outgoing edge
        - Turn lanes for the incomming/outgoing edge
        - The incomming/outgoing edge (u,v,key) 
    """
    (u,v,key) = edge
    out_matches = [
        (
            graph.turns[pair].name,
            graph.edges[pair[not incoming]]['lanes'],
            graph.edges[pair[not incoming]]['highway'],
            _get_last_element_from_string_or_list(graph.edges[pair[not incoming]]['turn:lanes']),
            pair[not incoming]
        )
        for pair 
        in graph.turns.keys() 
        if pair[incoming] == (u, v, key)
    ]
    return out_matches


def get_outgoing_turns_information(graph, edge):
    """
    Function to get outgoing turns in a given graph at a specified edge.
    
    Parameters:
    graph (object): Graph data structure containing nodes and edges. It also includes the 'turns' and 'edges' attributes.
    edge (tuple): A tuple consisting of the start node (u), end node (v), and key of the edge.

    Returns:
    list: Returns a list of tuples. Each tuple consists of:
        - Name of the turn type for the outgoing edge towards the input edge
        - Number of lanes for the outgoing edge
        - Turn lanes for the outgoing edge
        - The outgoing edge (u,v,key) 
    """
    return _get_turn_information(graph, edge, incoming=False)


def get_incoming_turns_information(graph, edge):
    """
    Function to get incoming turns in a given graph at a specified edge.
    
    Parameters:
    graph (object): Graph data structure containing nodes and edges. It also includes the 'turns' and 'edges' attributes.
    edge (tuple): A tuple consisting of the start node (u), end node (v), and key of the edge.

    Returns:
    list: Returns a list of tuples. Each tuple consists of:
        - Name of the turn type for the incoming edge towards the input edge
        - Number of lanes for the incoming edge
        - Turn lanes for the incoming edge
        - The incoming edge (u,v,key) 
    """
    return _get_turn_information(graph, edge, incoming=True)


def filter_turns(filter_out_turns, turns_list):
    """
    This function filters out specific turns from a list of turns. The turns to be filtered out are provided as an input.
    Each turn in the input list is a string that can contain multiple sub-turns separated by semicolons.
    The function removes any sub-turns that match any turn in the filter_out_turns list.
    If a turn becomes empty after filtering out sub-turns, it is not included in the result.

    Parameters:
    filter_out_turns (list): A list of turns to be filtered out from the turns_list.
    turns_list (list): A list of turns, where each turn is a string that can contain multiple sub-turns separated by semicolons.

    Returns:
    list: A list of filtered turns. Each turn is a string with possibly multiple sub-turns (those that didn't match filter_out_turns) separated by semicolons.
    """
    # Initialize the result list
    result = []

    # Filter out lanes with 'none'
    filter_out_turns.append('none')

    # Iterate over each item in the turns list
    for turn in turns_list:
        # Split the turn into sub_turns for comparison
        sub_turns = turn.split(';')

        # Initialize a list to hold the filtered sub_turns
        filtered_sub_turns = []

        # For each sub_turn, check if it's in the filter_out_turns
        for sub_turn in sub_turns:
            # This flag will help us to understand if sub_turn is present in any of the filter_out_turns
            found = False
            for filter_turn in filter_out_turns:
                if filter_turn in sub_turn:
                    found = True
                    break  # No need to check other turns in filter_out_turns

            # If the sub_turn is not found in any filter_out_turns, add it to filtered_sub_turns
            if not found:
                filtered_sub_turns.append(sub_turn)

        # If there are any filtered_sub_turns, join them back together with ';' and append to the result
        if len(filtered_sub_turns) > 0:
            result.append(";".join(filtered_sub_turns))

    # Return the filtered result
    return result


def concatenate_turns(turns, highways, n_max):
    """
    This function receives two lists, 'turns' and 'highways', and a maximum number 'n_max'. It organizes the tuples (highway, turn) 
    keeping track of the maximum category highway. It then organizes the turns that happened within the same highway category into a
    single string separated by ';'.

    Args:
        turns (list): List of turns to be organized.
        highways (list): List of highways corresponding to the turns.
        n_max (int): Maximum number of tuples to keep track.

    Returns:
        list: List of turns for each category of highway, ordered by the category of the highway.
    """

    if len(turns) < n_max:
        n_missing = n_max - len(turns)

        if len(set(highways)) <= 1:  # check if all elements are the same
            if 'through' in turns:
                index = turns.index('through')
            else:
                index = highways.index(min(highways))
        else:
            index = highways.index(min(highways))
                
        turn = turns[index]
        highway = highways[index]

        new_turns = [turn] * n_missing
        new_highways = [highway] * n_missing

        turns[index:index] = new_turns
        highways[index:index] = new_highways
            

    assert len(turns) >= n_max, "Number of turns must be greater or equal to n_max."
    assert n_max > 1, "n_max must be greater than 1."

    result = []

    # Iterate over the turns list using index
    for index in range(len(turns)):
        current_highway = highways[index]
        current_turn = turns[index]

        if len(result) < n_max:
            result.append((current_highway, current_turn))
        else: # len(result) >= n_max
            first_item = result[0]
            last_category, last_turn = result[-1]

            if first_item[0] < current_highway:
                # Concatenate new turn_type with the last turn_type in the result
                if current_turn == last_turn and last_turn != result[-2]:
                    result[-2] = (result[-2][0], result[-2][1] + ";" + last_turn)

                result[-1] = (last_category, (last_turn.split(';')[0] + ";" + current_turn) if last_turn.split(';')[0] != current_turn else current_turn)
                continue

            if (first_item[0] == current_highway 
                and any(word in first_item[1] for word in ('through', 'roundabout')) 
                and first_item[1] != current_turn
            ):
                result[-1] = (last_category, last_turn.split(';')[0] + ";" + current_turn)
                continue

            # Pop the first item in the result
            popped = result.pop(0)
            # Check if the next turn is different from the last turn of the popped item
            if result[0][1] != popped[1].split(';')[-1]:
                next_category, next_turn = result[0]
                result[0] = (next_category, popped[1].split(';')[-1] + ";" + next_turn.split(';')[-1])

            if popped[1] == result[0][1] and len(result) > 1 and popped[1] != result[1][1]:
                result[1] = (result[1][0], popped[1] + ";" + result[1][1])

            if len(result) == 1 and popped[1] == result[0][1] and popped[1] != current_turn:
                current_turn = popped[1] + ";" + current_turn
            # Append the current (highway, turn) pair to the result
            result.append((current_highway, current_turn))
    
    highways, turns = map(list, zip(*result))
    # assert(set(organized_turns) == set(turns))

    return turns


def infer_lanes(data, outgoing_edges):
    """
    Infers the lanes for a given edge based on the outgoing edges.

    Args:
        u (vertex): Starting vertex of the edge.
        v (vertex): Ending vertex of the edge.
        key: Key associated with the edge.
        data (dict): Data associated with the edge.
        incoming_edges (list): List of incoming edges to the vertex.
        outgoing_edges (list): List of outgoing edges from the vertex.

    Returns:
        str: Concatenated string representation of inferred lanes.

    Raises:
        AssertionError: If the number of inferred lanes doesn't match the number of lanes on the edge.
    """
    
    result = []

    # Infer lanes based on the outgoing edges
    for outgoing_edge in outgoing_edges:
        if outgoing_edge[0] in ['uturn', 'infeasible']:
            continue
        pair = (outgoing_edge[0], outgoing_edge[2])
        for _ in range(int(outgoing_edge[1])):
            result.append(pair)

    # Sort the inferred lanes in the order: 'left', 'through', 'right'
    result.sort(key=lambda x: ('left', 'through', 'roundabout', 'right').index(x[0]))

    turns, highways = map(list, zip(*result))
    highways = [HighwayType.from_data(highway).value for highway in highways]

    if len(set(turns)) == 1:
        turns = turns[:int(data['lanes'])]

        if len(turns) != int(data['lanes']):
            turns = turns * int(data['lanes'])

    if len(turns) != int(data['lanes']):
        turns = concatenate_turns(turns, highways, int(data['lanes']))

    # Verify that the number of inferred lanes matches the number of lanes on the edge
    assert len(turns) == int(data['lanes']), "Number of turn:lanes should equal the number of lanes on an edge"
    
    # Concatenate the inferred lanes into a string representation   
    return "|".join(turns)


def infer_roundabout(u, v, key, data, graph, outgoing_edges):
    out_angles = {}
    closest_to_180 = None
    min_diff = float('inf')

    for outgoing_edge in outgoing_edges:
        out_angles[outgoing_edge] = penalties.get_turn(graph, in_edge=(u,v,key), out_edge=outgoing_edge[-1]).angle
        diff = abs(out_angles[outgoing_edge] - 180)

        if diff < min_diff:
            min_diff = diff
            closest_to_180 = outgoing_edge

    result = []
    result += list(zip(['through'] * int(closest_to_180[1]), [HighwayType.from_data(closest_to_180[2]).value] * int(closest_to_180[1])))

    for edge in out_angles.keys():
        if edge == closest_to_180: continue
        angle = out_angles[edge]
        turns = []
        if angle < out_angles[closest_to_180]:
            turns.extend(['left'] * int(edge[1]))
        else:
            turns.extend(['right'] * int(edge[1]))
        
        highways = []
        highways.extend([HighwayType.from_data(edge[2]).value] * int(edge[1]))

        result += list(zip(turns, highways))

    result.sort(key=lambda x: ('left', 'through', 'roundabout', 'right').index(x[0]))
    turns, highways = map(list, zip(*result))

    return concatenate_turns(turns, highways, int(data['lanes']))


def process_turn_lanes(graph):
    required_edges = [
        (u,v,key,data) 
        for (u,v,key,data) 
        in graph.edges(keys=True,data=True) 
        if data['required'] == 'True' 
        and int(data['lanes']) > 1
        and _get_last_element_from_string_or_list(data['turn:lanes']) == 'nan'
        and len(list(get_outgoing_turns_information(graph, (u, v, key)))) > 1
    ]

    ox_utils.log(f'Start processing {len(required_edges)} required edges that are missing turn:lanes')

    for u, v, key, data in required_edges:        
        outgoing_edges = get_outgoing_turns_information(graph, (u,v,key))

        # Skipping weird junctions for now...
        if data['junction'] == 'circular' or data['junction'] == 'roundabout':
            data['turn:lanes'] = infer_roundabout(u, v, key, data, graph, outgoing_edges)
            graph.add_edge(u, v, key, **data)
        else:
            data['turn:lanes'] = infer_lanes(data, outgoing_edges)
            graph.add_edge(u, v, key, **data)

    ox_utils.log(f'Finished processing the turn:lanes for the required edges')


def split_edges(graph, parallel_edges:int):
    highest_keys = _edge_highest_key_map(graph)

    required_edges = [
        (u,v,key,data) 
        for (u,v,key,data) 
        in graph.edges(keys=True,data=True) 
        if data['required'] == 'True' and int(data['lanes']) > 1 # only edges with multiple lanes have multiple turn:lanes
    ]

    ox_utils.log(f'Splitting {len(required_edges)} edges with lanes > {parallel_edges} with their turn:lanes in consideration')

    added_edges_count = 0
    for u, v, key, data in required_edges:
        turn_lane_str = _get_last_element_from_string_or_list(data['turn:lanes'])
        
        split_turn_lanes = _split_turn_types(turn_lane_str, parallel_edges)
        added_edges_count += len(split_turn_lanes) - 1
        # If no new split in the turn:lanes is identified, 
        # then only update the turn penalties for the edge
        
        for index, turn_lanes in enumerate(split_turn_lanes):
            # Deep copy the data dict of edge (u,v,key)
            new_data = dict(data)
            new_data['turn:lanes'] = turn_lanes
            new_data['lanes'] = str(len(turn_lanes.split("|")))

            update_or_create_edge(graph, index, (u, v, key, new_data), highest_keys)

    ox_utils.log(f'Finished splitting the lanes into turn parts, created {added_edges_count} new edges')

# update (if index == 0), or create a new edge for given edge
def update_or_create_edge(
        graph, 
        index: int, 
        edge: tuple, 
        highest_keys: dict,
    ) -> tuple:
    (u, v, key, data) = edge
    if index == 0:
        graph.edges[u, v, key].update(data)
        return edge
    else:
        new_key = highest_keys[(u, v)] + 1

        # Get all ingoing and outgoing edge pairs for (u, v, new_key) and their turns
        in_matches = get_turns(graph, (u, v, key), new_key, incoming=True)
        out_matches = get_turns(graph, (u, v, key), new_key, incoming=False)

        graph.add_edge(u, v, new_key, **data)

        # Update highest key for (u,v)
        highest_keys[(u, v)] = new_key

        # Add all new edge pairs for (u, v, new_key) in the turn penalties dictonary of the graph
        graph.turns.update(in_matches)
        graph.turns.update(out_matches)

        return (u, v, new_key, data)
    
def get_turns(graph, edge, new_key, incoming=True):
    (u, v, key) = edge
    matches = {
        (pair[0], (u, v, new_key)) if incoming else ((u, v, new_key), pair[1]): graph.turns[pair]
        for pair 
        in graph.turns.keys() 
        if pair[incoming] == (u, v, key)
    }
    return matches