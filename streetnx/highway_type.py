from enum import Enum

class HighwayType(Enum):
    MOTORWAY = 1
    TRUNK = 2
    PRIMARY = 3
    SECONDARY = 4
    TERTIARY = 5
    UNCLASSIFIED = 6
    LIVING_STREET = 6
    RESIDENTIAL = 6
    SERVICE = 7
    PROJECTED_FOOTWAY = 7

    @classmethod
    def from_edge(cls, edge):
        string = edge["highway"]
        for name, member in cls.__members__.items():
            if name.lower() in string:
                return member
        raise ValueError(f"Invalid highway type string: {string}")