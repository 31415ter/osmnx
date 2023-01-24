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

    @classmethod
    def from_string(cls, string):
        for name, member in cls.__members__.items():
            if name.lower() == string.lower():
                return member
        raise ValueError(f"Invalid highway type string: {string}")