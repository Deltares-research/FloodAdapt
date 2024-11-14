import shutil

from flood_adapt.dbs_classes.dbs_template import DbsTemplate
from flood_adapt.object_model.interface.tipping_points import ITipPoint
from flood_adapt.object_model.tipping_point import TippingPoint


class DbsTippingPoint(DbsTemplate):
    _type = "tipping_point"
    _folder_name = "tipping_points"
    _object_model_class = TippingPoint

    def save(self, tipping_point: ITipPoint, overwrite: bool = False):
        """Save a tipping point object in the database.

        Parameters
        ----------
        tipping_point : ITipPoint
            object of tipping point type
        overwrite : bool, optional
            whether to overwrite existing tipping point with same name, by default False

        Raises
        ------
        ValueError
            Raise error if name is already in use. Names of tipping points should be unique.
        """
        # Save the tipping point
        super().save(tipping_point, overwrite=overwrite)

    def delete(self, name: str, toml_only: bool = False):
        """Delete an already existing tipping point in the database.

        Parameters
        ----------
        name : str
            name of the tipping point
        toml_only : bool, optional
            whether to only delete the toml file or the entire folder. If the folder is empty after deleting the toml,
            it will always be deleted. By default False
        """
        # First delete the tipping point
        super().delete(name, toml_only=toml_only)

        # Delete output if edited
        output_path = (
            self._database.tipping_points.get_database_path(get_input_path=False) / name
        )

        if output_path.exists():
            shutil.rmtree(output_path)

    def edit(self, tipping_point: ITipPoint):
        """Edit an already existing tipping point in the database.

        Parameters
        ----------
        tipping_point : ITipPoint
            object of tipping point type
        """
        # Edit the tipping point
        super().edit(tipping_point)

        # Delete output if edited
        output_path = (
            self._database.tipping_points.get_database_path(get_input_path=False)
            / tipping_point.attrs.name
        )

        if output_path.exists():
            shutil.rmtree(output_path)
