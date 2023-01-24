import osmnx as ox

from streetnx.highway_type import HighwayType
from streetnx.turn import Turn, TurnType

def add_penalties(G, turn_angle_threshold = 40):
    # create dictonary that contains the turn 
    # types of each adjacent pair of edges
    turn_dict = {}

    # iterate over each node (i.e. intersection) in the graph and
    # check each adjacent pair of edges (i.e. road) to that node
    # to assign the correct turn type to the edge pair
    for node in G.nodes():
        straights = []
        outgoing_straights = {}
        turns = []

        # determine which outgoing edge is most likely 
        # the 'straight' turn for the given incoming edge
        for in_edge in list(G.in_edges(node, keys = True)):
            straight = None
            in_edge_data = G.get_edge_data(*in_edge)
            for out_edge in list(G.out_edges(node, keys = True)):
                out_edge_data = G.get_edge_data(*out_edge)
                # if the in and out edge visit the same nodes, but in opposing direction,
                # and the edge lengths are equal, then the turn is a U-turn
                if (in_edge[0] == out_edge[1]) and (in_edge_data['length'] == out_edge_data['length']):
                    turn_dict[(in_edge, out_edge)] = TurnType.UTURN
                    continue

                turn = get_turn(G, in_edge=in_edge, out_edge=out_edge)
                turns.append(turn)

                # A situation can occur where a node has multiple outgoing edges of various highway types.
                # Then the outgoing edges which matches the type of the incoming edge the most is considered
                # to be a potential better candidates for the straight road originating from the incoming edge
                straight = classify_straight_turn(
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
            # TODO: create documentation drawing why this is the case.
            if straight is not None:
                if (straight.out_edge[0], straight.out_edge[1], straight.out_edge[2]) not in outgoing_straights:
                    outgoing_straights[(straight.out_edge[0], straight.out_edge[1], straight.out_edge[2])] = []
                outgoing_straights[(straight.out_edge[0], straight.out_edge[1], straight.out_edge[2])].append(straight)

        # If only 1 outgoing edge is present at the node: add all outgoing_straights to the straights.
        # Later determine which of these straight is the one straight to rule them all. 
        # One straight to find them, one straight to bring them all and in the darkness bind them.
        if len(list(G.out_edges(node, data = True))) == 1:
            straights += list(outgoing_straights.values())[0] if len(outgoing_straights) != 0 else []
        else:
            # The node has multiple outgoing edges, and thus the best candidate for the straight turn must be determined for each incomming edge
            #TODO: HIER BEN IK GEBLEVEN MET REFACTORING!
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

def get_turn(G, in_edge, out_edge):
    angle = ox.utils_geo.angle(G, in_edge, out_edge) 
    if angle < 0: 
        angle = 360 + angle
    edge_turn = Turn(in_edge, out_edge, angle)

    return edge_turn

def classify_straight_turn(G, straight, turn, in_edge_data, out_edge_data, turn_angle_threshold):
    """
    This function classifies whether the pair (in_edge, out_edge) 
    is a better option for the straight road (pair of two adjacent edges) 
    through an intersection (node), compared to the pair: (in_edge, straight).

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
            raise ValueError(f"This should not happen.")
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
            raise ValueError(f"This should not happen.")   