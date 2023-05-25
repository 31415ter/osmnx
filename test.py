

def concatenate_turns(turns, highways, max_lanes):
    """
    Concatenates elements in 'turns' list to meet 'max_lanes' requirement.
    
    Parameters
    ----------
    turns: list
        A list of turn strings to be concatenated.
    max_lanes: int
        The maximum number of lanes that can be formed.

    Returns
    -------
    list
        The list of turns, concatenated as necessary.
    
    Raises
    ------
    AssertionError
        If max_lanes is not greater than 1.
    """
    assert isinstance(max_lanes, int) and max_lanes > 1, \
    'Concatenating is only needed if multiple lanes are possible on an edge'
    
    if len(turns) <= max_lanes:
        return turns 

    new_turns = []
    i = 0

    while len(new_turns) < max_lanes and i < len(turns):
        current_turn = turns[i]
        next_turn = None if i == len(turns) - 1 else turns[i+1]

        remaining_turns = len(turns) - i

        if next_turn and current_turn != next_turn and remaining_turns > len(new_turns):
            new_turns.append(current_turn + ";" + next_turn)
            i += 2
        else:
            new_turns.append(current_turn)
            i += 1

    return new_turns, alternate_turns

print(concatenate_turns(['left', 'left', 'through', 'through'], [5, 5, 3, 3], 2))
