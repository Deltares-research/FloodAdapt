import shutil

from flood_adapt.dbs_classes.dbs_template import DbsTemplate
from flood_adapt.object_model.benefit import Benefit
from flood_adapt.object_model.interface.benefits import IBenefit


class DbsBenefit(DbsTemplate):
    _type = "benefit"
    _folder_name = "benefits"
    _object_model_class = Benefit

    def save(self, benefit: IBenefit, overwrite: bool = False):
        """Save a benefit object in the database.

        Parameters
        ----------
        measure : IBenefit
            object of scenario type
        overwrite : bool, optional
            whether to overwrite existing benefit with same name, by default False

        Raises
        ------
        ValueError
            Raise error if name is already in use. Names of benefits assessments should be unique.
        """
        # Check if all scenarios are created
        if not all(benefit.scenarios["scenario created"] != "No"):
            raise ValueError(
                f"'{benefit.attrs.name}' name cannot be created before all necessary scenarios are created."
            )

        # Save the benefit
        super().save(benefit, overwrite=overwrite)

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
        output_path = self._database.output_path / "Benefits" / name

        if output_path.exists():
            shutil.rmtree(output_path, ignore_errors=True)

    def edit(self, benefit: IBenefit):
        """Edits an already existing benefit in the database.

        Parameters
        ----------
        benefit : IBenefit
            benefit to be edited in the database

        Raises
        ------
        ValueError
            Raise error if name is already in use.
        """
        # Check if it is possible to edit the benefit.
        super().edit(benefit)

        # Delete output if edited
        output_path = self._database.output_path / "Benefits" / benefit.attrs.name

        if output_path.exists():
            shutil.rmtree(output_path, ignore_errors=True)
