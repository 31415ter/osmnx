from enum import Enum

class TurnType(Enum):
    STRAIGHT = 1
    ROUNDABOUT = 0
    RIGHT = 3
    LEFT = 5
    UTURN = float('inf')
    INFEASIBLE = float('inf')

class Turn:
    def __init__(self, in_edge, out_edge, angle):
        self.in_edge = in_edge
        self.out_edge = out_edge
        self.angle = angle

    def set_type(self, turnType):
        self.turn_type = turnType