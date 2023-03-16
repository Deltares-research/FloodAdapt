from typing import Any

from flood_adapt.object_model.interface.database import IDatabase


def get_projections(database: IDatabase) -> dict[str, Any]:
    # sorting and filtering either with PyQt table or in the API
    return database.get_projections()


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
