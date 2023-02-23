

def convert_unit(unit: str) -> float:
    """Generic function to convert units comments describe default SI units

    Args:
        str of units description

    Returns:
        conversion factor
    """
    if unit == 'centimeters':
        conversion = 1./100 # meters
    elif unit == 'meters':
        conversion = 1. # meters
    elif unit == 'feet':
        conversion = 1./3.28084 # meters
    elif unit == 'inch':
        conversion = 25.4 # millimeters
    elif unit == 'knots':
        conversion = 1. / 1.943844  # m/s
    elif unit == 'cfs': # cubic feet per second
        conversion = 0.02832 # m3/s
    elif unit == 'cms':
        conversion = 1.  # m3/s
    else:
        conversion = None
    return conversion