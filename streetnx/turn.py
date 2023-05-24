from enum import Enum

class TurnType(Enum):
    through = 1
    roundabout = 0
    right = 3
    left = 5
    uturn = float('inf')
    infeasible = float('inf')

class Turn:
    def __init__(self, in_edge, out_edge, angle):
        self.in_edge = in_edge
        self.out_edge = out_edge
        self.angle = angle

    def set_type(self, turnType):
        self.turn_type = turnType