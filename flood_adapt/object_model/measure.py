# import os
# from typing import Union

# import tomli

# from flood_adapt.object_model.interface.measures import (
#     MeasureType,
#     MeasureModel,
# )


# class Measure:
#     attrs: MeasureModel

#     @staticmethod
#     def get_measure_type(filepath: Union[str, os.PathLike]):
#         """Get a measure type from toml file."""
#         with open(filepath, mode="rb") as fp:
#             toml = tomli.load(fp)
#         type = toml.get("type")
#         return MeasureType(type)
# TODO remove this file
