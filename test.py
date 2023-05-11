import math

def has_common_value(list1, list2):
    set1 = set(list1)
    for value in list2:
        if value in set1:
            return True
    return False

def split_turn_types(turn_types: str, max_size: int):
    turn_types_list = [turn_type if turn_type != '' else 'through' for turn_type in turn_types.split('|')]
    num_turns = len(turn_types_list)
    num_parts = math.ceil(num_turns / max_size)

    parts = []
    i = 0
    for _ in range(num_parts):
        part = []
        while i < len(turn_types_list) and len(part) < max_size:
            current_turn = turn_types_list[i]
            previous_turn_not_same = part and not has_common_value(current_turn.split(';'), part[-1].split(';'))
            next_turn_same = i + 1 < len(turn_types_list) and has_common_value(current_turn.split(';'), turn_types_list[i + 1].split(';'))
            parts_left = math.ceil((len(turn_types_list)-i) / max_size)
            balancing = (
                parts_left == 1 
                and num_turns - i == len(part) 
                and not next_turn_same 
                and previous_turn_not_same
                and i + 1 < len(turn_types_list)
            )
            if (
                previous_turn_not_same
                and next_turn_same 
                and parts_left != num_parts - len(parts) 
                or balancing
            ):
                break
            part.append(current_turn)
            i += 1
        parts.append('|'.join(part))

    return parts

print(split_turn_types('left|left;through|through;right|right', 3))


    # import math
    # def split_turn_types(turn_types: str, max_size: int):
    #     turn_types_list = [turn_type if turn_type != '' else 'through' for turn_type in turn_types.split('|')]
    #     num_turns = len(turn_types_list)
    #     num_parts = math.ceil(num_turns / max_size)

    #     parts = []
    #     i = 0
    #     for _ in range(num_parts):
    #         part = []
    #         while i < len(turn_types_list) and len(part) < max_size:
    #             current_turn = turn_types_list[i]
    #             next_turn_same = i + 1 < len(turn_types_list) and current_turn == turn_types_list[i + 1]
    #             parts_left = math.ceil((len(turn_types_list)-i) / max_size)
    #             balancing = (
    #                 parts_left == 1 
    #                 and num_turns - i == len(part) 
    #                 and not next_turn_same 
    #                 and current_turn != part[-1] 
    #                 and i + 1 < len(turn_types_list)
    #             )
    #             if (
    #                 part 
    #                 and current_turn != part[-1] 
    #                 and next_turn_same 
    #                 and parts_left != num_parts - len(parts) 
    #                 or balancing
    #             ):
    #                 break
    #             part.append(current_turn)
    #             i += 1
    #         parts.append('|'.join(part))

    #     return parts