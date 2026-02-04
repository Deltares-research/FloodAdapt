import logging
import time
from functools import wraps

from flood_adapt.misc.log import FloodAdaptLogging


def debug_timer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        _logger = FloodAdaptLogging.getLogger()  # No forced log level
        if _logger.isEnabledFor(logging.DEBUG):
            _logger.debug(f"Started '{func.__name__}'")
            start_time = time.perf_counter()

            result = func(*args, **kwargs)

            end_time = time.perf_counter()
            elapsed = end_time - start_time
            _logger.debug(f"Finished '{func.__name__}' in {elapsed:.4f} seconds")
        else:
            result = func(*args, **kwargs)

        return result

    return wrapper
