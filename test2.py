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
        if 'through' in turns:
            turns.extend('through' * (n_max - len(turns)))

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
    
    organized_turns = [turn for highway, turn in result]
    # assert(set(organized_turns) == set(turns))

    return organized_turns

print(concatenate_turns(['left', 'through'], [5, 5], 3))

# assert ['left;through', 'through;right', 'right']  == concatenate_turns(['left', 'left', 'through', 'through', 'right', 'right'], [3, 3, 1, 1, 2, 2], 3)
# assert ['left;through', 'through;right'] == concatenate_turns(['left', 'left', 'through', 'through', 'right', 'right'], [3, 3, 1, 1, 2, 2], 2)
# assert ['left;through', 'through', 'right', 'right'] == concatenate_turns(['left', 'left', 'through', 'through', 'right', 'right'], [3, 3, 1, 1, 2, 2], 4)
# assert ['left', 'left;through', 'through', 'right', 'right'] == concatenate_turns(['left', 'left', 'through', 'through', 'right', 'right'], [3, 3, 1, 1, 2, 2], 5)

# assert ['left;through', 'through;right'] == concatenate_turns(['left', 'left', 'through', 'through', 'right', 'right'], [1, 1, 1, 1, 2, 2], 2)
# assert ['left', 'left;through', 'through;right'] == concatenate_turns(['left', 'left', 'through', 'through', 'right', 'right'], [1, 1, 1, 1, 2, 2], 3)
# assert ['left', 'left', 'through', 'through;right'] == concatenate_turns(['left', 'left', 'through', 'through', 'right', 'right'], [1, 1, 1, 1, 2, 2], 4)
# assert ['left', 'left', 'through', 'through;right', 'right'] == concatenate_turns(['left', 'left', 'through', 'through', 'right', 'right'], [1, 1, 1, 1, 2, 2], 5)

# assert ['left;through', 'through'] == (concatenate_turns(['left', 'through', 'through'], [3, 1, 1], 2))
# assert ['left', 'left;through'] == (concatenate_turns(['left', 'left', 'through'], [3, 3, 1], 2))

# assert ['left;through', 'through'] == (concatenate_turns(['left', 'left', 'through', 'through'], [3, 3, 1, 1], 2))
# assert ['left', 'left;through', 'through'] == (concatenate_turns(['left', 'left', 'through', 'through'], [3, 3, 1, 1], 3))

# assert concatenate_turns(['left', 'through', 'right'], [3, 1, 1], 2) == ['left;through', 'right']
# assert concatenate_turns(['left', 'through', 'right'], [1, 1, 3], 2) == ['left', 'through;right']
# print()