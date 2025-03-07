import shutil

from flood_adapt.dbs_classes.dbs_template import DbsTemplate
from flood_adapt.object_model.benefit import Benefit


class DbsBenefit(DbsTemplate[Benefit]):
    _object_class = Benefit

    def save(self, object_model: Benefit, overwrite: bool = False):
        """Save a benefit object in the database.

        Parameters
        ----------
        object_model : Benefit
            object of Benefit type
        overwrite : bool, optional
            whether to overwrite existing benefit with same name, by default False

        Raises
        ------
        ValueError
            Raise error if name is already in use. Names of benefits assessments should be unique.
        """
        # Check if all scenarios are created
        if not all(object_model.scenarios["scenario created"] != "No"):
            raise ValueError(
                f"'{object_model.attrs.name}' name cannot be created before all necessary scenarios are created."
            )

        # Save the benefit
        super().save(object_model, overwrite=overwrite)

    def delete(self, name: str, toml_only: bool = False):
        """Delete an already existing benefit in the database.

        Parameters
        ----------
        name : str
            name of the benefit
        toml_only : bool, optional
            whether to only delete the toml file or the entire folder. If the folder is empty after deleting the toml,
            it will always be deleted. By default False

        Raises
        ------
        ValueError
            Raise error if benefit has already model output
        """
        # First delete the benefit
        super().delete(name, toml_only=toml_only)

        # Delete output if edited
        output_path = self.output_path / name
        if output_path.exists():
            shutil.rmtree(output_path, ignore_errors=True)

    def edit(self, object_model: Benefit):
        """Edits an already existing benefit in the database.

        Parameters
        ----------
        benefit : Benefit
            benefit to be edited in the database

        Raises
        ------
        ValueError
            Raise error if name is already in use.
        """
        # Check if it is possible to edit the benefit.
        super().edit(object_model)

        # Delete output if edited
        output_path = self.output_path / object_model.attrs.name
        if output_path.exists():
            shutil.rmtree(output_path, ignore_errors=True)
