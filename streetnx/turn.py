from enum import Enum

class TurnType(Enum):
    STRAIGHT = 0
    ROUNDABOUT = 0
    RIGHT = 1
    LEFT = 3
    UTURN = float('inf')
    INFEASIBLE = float('inf')

class Turn:
    turn_penalty = 0

    def __init__(self, in_edge, out_edge, angle):
        self.in_edge = in_edge
        self.out_edge = out_edge
        self.angle = angle