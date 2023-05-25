import osmnx as ox

from osmnx import utils as ox_utils
from streetnx import utils as snx_utils
from streetnx.highway_type import HighwayType
from streetnx.turn import Turn, TurnType

def add_penalties(G, turn_angle_threshold = 40):
    """
    Concatenates elements in 'turns' list to meet 'max_lanes' requirement.
    """
    ox_utils.log("Start turn penalties assignment.")

    G.turns = {}
    G.gamma = snx_utils.get_average_edge_duration(G)
    ox_utils.log(f"Turn penalty gamma = {G.gamma}.")

    # iterate over each node (i.e. intersection) in the graph and
    # check each adjacent pair of edges (i.e. road) to that node
    # to assign the correct turn type to the edge pair
    for node in G.nodes():
        straights = []
        outgoing_straights = {}
        turns = []

        for in_edge in list(G.in_edges(node, keys = True)):
            
            # determine which outgoing edge is most likely 
            # the 'straight' turn for the given incoming edge
            straight = None
            in_edge_data = G.get_edge_data(*in_edge)
            for out_edge in list(G.out_edges(node, keys = True)):
                out_edge_data = G.get_edge_data(*out_edge)
                
                # if the in and out edge visit the same nodes, but in opposing direction,
                # and the edge lengths are equal, then the turn is a U-turn
                if (in_edge[0] == out_edge[1]) and (in_edge_data['length'] == out_edge_data['length']):
                    G.turns[(in_edge, out_edge)] = TurnType.uturn
                    continue

                turn = get_turn(G, in_edge=in_edge, out_edge=out_edge)
                turns.append(turn)

                # A situation can occur where a node has multiple outgoing edges of various highway types.
                # Then the outgoing edges which matches the type of the incoming edge the most is considered
                # to be a potential better candidates for the straight road originating from the incoming edge
                straight = get_straight_turn(
                    G=G,
                    straight=straight,
                    turn=turn,
                    in_edge_data=in_edge_data,
                    out_edge_data=out_edge_data,
                    turn_angle_threshold=turn_angle_threshold
                )

            # Add the straight edge to all outgoing_straights present at the node (intersection).
            # As multiple pairs of incoming and outgoing edges could have a straight to the same outgoing edge. 
            # However, only one outgoing edge should be used as a straight 
            # (otherwise two ingoing edges have a straight turn to the same outgoing edge, which is not possible)
            # TODO: documentation drawing why this is the case.
            if straight is not None:
                if straight.out_edge not in outgoing_straights:
                    outgoing_straights[straight.out_edge] = []
                outgoing_straights[straight.out_edge].append(straight)

        # If only 1 outgoing edge is present at the node, then add all outgoing_straights to the straights.
        # Later determine which of these straight is the one straight to rule them all. 
        # One straight to find them, one straight to bring them all and in the darkness bind them.
        if len(list(G.out_edges(node, data = True))) == 1:
            straights += list(outgoing_straights.values())[0] if len(outgoing_straights) != 0 else []
        else:
            # Else, the node has multiple outgoing edges, and a outgoing edge can only be used in a single straight turn.

            # Iterate over all the outgoing edges of the documented straight turns
            for edge in list(outgoing_straights.keys()):

                # Check which straight turn is the best fitting straight turn for the given outgoing edge.
                best_fit = best_fitting_straight(G, outgoing_edge=edge, outgoing_straights=outgoing_straights)

                # add the best turn to the straights
                if best_fit is not None: 
                    straights.append(best_fit)
                
        # Assign the type of turns to all turns
        assign_turn_types(G, straights=straights, turns=turns, turn_angle_threshold=turn_angle_threshold)

    ox_utils.log("Finished turn penalties assignment.")

def get_turn(G, in_edge, out_edge):
    angle = ox.utils_geo.angle(G, in_edge, out_edge) 
    if angle < 0: 
        angle = 360 + angle
    return Turn(in_edge, out_edge, angle)

def get_straight_turn(G, straight, turn, in_edge_data, out_edge_data, turn_angle_threshold):
    """
    This function returns a turn that best fits the straight turn originating from the in_edge.
    It compares the current best fit turn (in_edge, straight) and (in_edge, out_edge).
     
    Parameters:
    - G, the graph
    - straight, the best found outgoing edge to represent the straight through an intersection for the given in_edge
    - out_edge, the out_edge to classify
    - turn_angle_threshold, if the angle between the edge pair (in_edge, out_edge) is smaller than the threshold, the turn is invalid

    Returns:
    - None, if the adjacent edges (in_edge, out_edge) does not represent a better straight through the intersection for the given in_edge
    - Turn, if the  adjacent edges (in_edge, out_edge) better represents the straight through the intersection for the given in_edge
    """

    in_type = HighwayType.from_edge(in_edge_data).value
    out_type = HighwayType.from_edge(out_edge_data).value

    # if the angle is less than 'threshold' degrees or greater than 360-'threshold' degrees,
    # then this turn cannot be a straight turn.
    if turn.angle < turn_angle_threshold or turn.angle > 360 - turn_angle_threshold:
        return straight

    # if no straight turn was yet determined originating from the in edge,
    # set the straight to this turn
    if straight is None:
        return turn

    # Check if a difference larger than 1 in highway type exists 
    # between the current out edge of the straight and the incoming edge
    if abs(HighwayType.from_edge(G.get_edge_data(*straight.out_edge)).value - in_type) > 1:
        # if the difference in types between the outgoing en incoming edge is smaller or equal to 1,
        # then these two edges better match their types and thus will be used as straight
        if abs(out_type - in_type) <= 1:                        
            return turn              
        # if the difference in types between the outgoing and incoming edge is larger than 1, 
        # just as the current selected outgoing straight edge, 
        # then check if the angle of the outgoing edge better matches the incoming edge
        elif abs(180 - turn.angle) < abs(180 - straight.angle):                        
            return turn
        elif abs(180 - turn.angle) == abs(180 - straight.angle):
            raise ValueError(f"This should never happen.")
        else:
            return turn
    # Else, the straight road is roughly the same type as the incoming road
    else:       
        # if the difference between road types is greater than 1, then this is not a potential straight road.
        # As the selected outgoing straight edge and the incoming edge differ at most 1 in types.
        if abs(out_type - in_type) > 1:                        
            return straight
        # if the angle between the two roads is less than the current straight road, then this is the new straight road
        if abs(180 - turn.angle) < abs(180 - straight.angle):
            return turn            
        elif abs(180 - turn.angle) == abs(180 - straight.angle):
            raise ValueError(f"This should never happen.")   
        else:
            return straight
        
def best_fitting_straight(G, outgoing_edge, outgoing_straights):
    """
    Check which straight turn is the best fitting straight turn for the given outgoing edge.

    Parameter:
    - G, the input graph.
    - outgoing_edge, an outgoing edge for a node
    - outgoing_straights, all outgoing edges for all straight turns going through a node.

    Returns:
    Turn, best fitting turn for the given outgoing edge
    """
    best_fit = None

    # iterate over all straight turns that use the given edge as its outgoing edge
    for turn in outgoing_straights[outgoing_edge]:

        # If no best fitting straight turn for the outgoing edge has been found yet,
        # this turn is considered as the best fitting turn
        if best_fit == None:            
            best_fit = turn
            continue

        in_type_value = HighwayType.from_edge(G.get_edge_data(*turn.in_edge)).value
        out_type_value = HighwayType.from_edge(G.get_edge_data(*turn.out_edge)).value
        best_in_type_value = HighwayType.from_edge(G.get_edge_data(*best_fit.out_edge)).value

        # Check whether the edges of the considered turn (in_edge, edge) have similar types.
        # While the current best turn (best_in_edge, edge), differ greatly in the type of edges.
        if abs(out_type_value - in_type_value) <= 1 and abs(out_type_value - best_in_type_value) > 1:
            best_fit = turn

        # Check whether the edges of the considered turn (in_edge, edge) have similar types.
        # While the current best turn (best_in_edge, edge), also have similar types.
        elif abs(out_type_value - in_type_value) <= 1 and abs(out_type_value - best_in_type_value) <= 1:      
            
            # if the considered turn's angle is closer alligned to 180 degrees,
            # select the considered turn as a better fit.

            if abs(180 - turn.angle) < abs(180 - best_fit.angle):       
                # this turn is better than the current best turn                 
                best_fit = turn
            elif abs(180 - turn.angle) == abs(180 - best_fit.angle):
                raise ValueError(f"This should never happen.")
            
        elif abs(out_type_value - in_type_value) > 1 and abs(out_type_value - best_in_type_value) > 1:                     
            # the best and considered turn are not roughly the same type as the outgoing road (edge)
            if abs(180 - turn.angle) < abs(180 - best_fit.angle):    
                # this turn is better than the current best turn                    
                best_fit = turn
            elif abs(180 - turn.angle) == abs(180 - best_fit.angle):
                raise ValueError(f"This should never happen.")
    
    # add the best turn to the straights
    return best_fit

def assign_turn_types(G, straights, turns, turn_angle_threshold):
    # Map all incoming edges of the node to its straights
    # These will later be used to determine right/left turns on intersections
    in_edge_straight_turns = {}        
    for road_turn in straights:
        in_edge_straight_turns[road_turn.in_edge] = road_turn

    for road_turn in turns:

        turn_in_edge_data = G.get_edge_data(*road_turn.in_edge)
        turn_out_edge_data = G.get_edge_data(*road_turn.out_edge)

        # check if the outgoing edge is part of a roundabout
        if 'roundabout' in turn_out_edge_data['junction'] or 'circular' in turn_out_edge_data['junction']:
            road_turn.set_type(TurnType.roundabout)

        # check if the outgoing edge is part of a roundabout
        elif 'roundabout' in turn_in_edge_data['junction'] or 'circular' in turn_in_edge_data['junction']:
            road_turn.set_type(TurnType.roundabout)

        # Check if the turn is a u-turn, which is prohibited
        elif (road_turn.in_edge[0] == road_turn.out_edge[1]) and (turn_in_edge_data['length'] == turn_out_edge_data['length']):                
            road_turn.set_type(TurnType.uturn)

        # Check if the turn angle is too tight.
        elif (abs(road_turn.angle) < turn_angle_threshold) or (abs(road_turn.angle) > 360 - turn_angle_threshold):                
            road_turn.set_type(TurnType.infeasible)

        # Check if the turn resides in the straight list
        elif road_turn in straights:                
            road_turn.set_type(TurnType.through)

        # if a straight turn was previously identified for the incoming edge of the turn,
        # then the straight turn will be used to determine the right and left turns
        elif road_turn.in_edge in in_edge_straight_turns:                
            if road_turn.angle >= in_edge_straight_turns[road_turn.in_edge].angle:
                road_turn.set_type(TurnType.right)
            else:
                road_turn.set_type(TurnType.left)

        # if no straight turn was identified using the in_edge of the turn on the node,
        # then simply use the turn's angle to determine right and left turns.
        else:
            if road_turn.angle > 180:
                road_turn.set_type(TurnType.right)
            else:
                road_turn.set_type(TurnType.left)

        # add the turns to the graph by their key: (in_edge, out_edge).
        G.turns[(road_turn.in_edge, road_turn.out_edge)] = road_turn.turn_type
