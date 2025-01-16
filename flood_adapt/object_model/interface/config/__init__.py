from enum import Enum


class Cstype(str, Enum):
    """The accepted input for the variable cstype in Site."""

    projected = "projected"
    spherical = "spherical"
