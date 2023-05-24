
import math
from streetnx.turn import Turn, TurnType
from osmnx import utils as ox_utils


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
        ((edge_pair), key) = edge
        
        # Check if the edge pair is not in the highest_key map or if the current key is higher than the stored key
        if (edge_pair) not in highest_key or highest_key[edge_pair] < key:
            # Update the highest_key map with the current key
            highest_key[edge_pair] = key

    # Return the highest_key map
    return highest_key


def _get_last_element_from_string_or_list(input_data):
    """
    Takes a string or list and returns the last element.
    """
    if isinstance(input_data, str):
        cleaned_string = input_data.replace('[', '').replace(']', '').replace(' ', '').replace('\'', '')
        elements = cleaned_string.split(',')
        return elements[-1] if len(elements) > 1 else cleaned_string
    elif isinstance(input_data, list):
        return input_data[-1]
    return ''


def _partition_integer(n, max_partition_size):
    """
    Partitions the given integer into groups of at most 'max_partition_size',
    trying to make the groups as evenly distributed as possible.

    Parameters:
    n (int): The integer to partition.
    max_partition_size (int): The maximum size for a partition.

    Returns:
    list: A list of integers representing the partitions.
    """
    quotient, remainder = divmod(n, max_partition_size)
    partitions = [max_partition_size] * quotient
    if remainder:
        partitions.append(remainder)

    # Balance the partitions
    for i in range(len(partitions) - 1, 0, -1):
        while partitions[i] < partitions[i-1] - 1:
            partitions[i] += 1
            partitions[i-1] -= 1

    return partitions


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
        (graph.turns[pair].name, graph.edges[pair[incoming]]['lanes'], graph.edges[pair[incoming]]['turn:lanes'], pair[incoming])
        for pair 
        in graph.turns.keys() 
        if pair[not incoming] == (u, v, key)
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
    return _get_turns(graph, edge, incoming=False)


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
    return _get_turns(graph, edge, incoming=True)


def filter_turns(filter_out_turns, turns_list):
    # Initialize the result list
    result = []

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


def process_turn_lanes(graph):
    highest_keys = edge_highest_key_map(graph)

    required_edges = [
        (u,v,key,data) 
        for (u,v,key,data) 
        in graph.edges(keys=True,data=True) 
        if data['required'] == 'True' 
        and int(data['lanes']) > 1
        and get_last_element_from_string_or_list(data['turn:lanes']) == 'nan'
        and len(list(get_outgoing_turns_information(graph, (u, v, key)))) > 1
    ]

    for u,v,key,data in required_edges:
        lane_count = int(data['lanes'])
        
        incomming_edges = get_incoming_turns_information(graph, (u,v,key))
        outgoing_edges = get_outgoing_turns_information(graph, (u,v,key))

        # get the straight incoming edge, if it exists
        for in_edge in incomming_edges:
            if in_edge[0] != 'through':
                continue
            
            # in_edge is straight
            in_through_lanes = int(in_edge[1])
            in_turn_types = in_edge[2].split("|")
            in_through_edge = in_edge[3]

            in_through_edge_outgoing_turns = [turn[0] for turn in get_outgoing_turns_information(graph, in_through_edge) if 'through' not in turn[0]]
            
            turn_types = filter_turns(in_through_edge_outgoing_turns, in_turn_types)

            if len(turn_types) == lane_count:
                print("DONE!")
            else:
                print("fuckk...")

        # given the number of lanes, the types of outgoing turns, the number of lanes for these outgoing lanes
        
        print()

