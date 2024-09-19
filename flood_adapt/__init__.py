from flood_adapt.log import FloodAdaptLogging

FloodAdaptLogging()  # Initialize logging once for the entire package

__version__ = "0.1.1"

# this will be a part of Settings() when that PR is merged (https://github.com/Deltares-research/FloodAdapt/pull/546)
# Set this to False to disable the deletion of crashed/corrupted runs.
DELETE_CRASHED_RUNS = True
