from typing import Any

from flood_adapt.object_model.interface.database import IDatabase
from flood_adapt.object_model.interface.projections import IProjection
from flood_adapt.object_model.projection import Projection


def get_projections(database: IDatabase) -> dict[str, Any]:
    # sorting and filtering either with PyQt table or in the API
    return database.get_projections()


def get_projection(name: str, database: IDatabase) -> IProjection:
    return database.get_projection(name)


def create_projection(attrs: dict[str, Any]) -> IProjection:
    return Projection.load_dict(attrs)


def save_projection(projection: IProjection, database: IDatabase) -> None:
    database.save_projection(projection)


def edit_projection(projection: IProjection, database: IDatabase) -> None:
    database.edit_projection(projection)


def delete_projection(name: str, database: IDatabase) -> None:
    database.delete_projection(name)


def copy_projection(
    old_name: str, database: IDatabase, new_name: str, new_long_name: str
) -> None:
    database.copy_projection(old_name, new_name, new_long_name)


# # on click add projection
# def create_new_projection(template: str) -> dict():  # get attributes
#     pass


# def set_projection(event: dict):  # set attributes
#     pass


# # on click edit projection
# def get_projection(name: str) -> dict():  # get attributes
#     # incl physical and spcio-economic
#     pass


# def set_projection(event: dict):  # set attributes
#     pass


# # on click copy projection
# # get_projection
# # set_projection


# # on click delete projection
# def remove_projection(name: str) -> dict():  # get attributes
#     # remove object from database object and toml file, both socio-economic and physical
#     pass


# # in projection pop-up window on click OK
# def save_projection(name: str):
#     pass
