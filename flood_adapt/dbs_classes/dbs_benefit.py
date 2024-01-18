import shutil

from flood_adapt.dbs_classes.dbs_template import DbsTemplate
from flood_adapt.object_model.benefit import Benefit
from flood_adapt.object_model.interface.benefits import IBenefit


class DbsBenefit(DbsTemplate):
    _type = "benefit"
    _folder_name = "benefits"
    _object_model_class = Benefit

    def save(self, benefit: IBenefit, overwrite: bool = False):
        """Saves a benefit object in the database.

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
        # If overwrite is True, delete existing benefit with same name
        if overwrite:
            self.delete(benefit.attrs.name)
        
        names = self.list_objects()["name"]
        if benefit.attrs.name in names:
            raise ValueError(
                f"'{benefit.attrs.name}' name is already used by another benefit. Choose a different name"
            )
        elif not all(benefit.scenarios["scenario created"] != "No"):
            raise ValueError(
                f"'{benefit.attrs.name}' name cannot be created before all necessary scenarios are created."
            )
        else:
            (self._path / benefit.attrs.name).mkdir()
            benefit.save(self._path / benefit.attrs.name / f"{benefit.attrs.name}.toml")

    def delete(self, name: str):
        """Deletes an already existing benefit in the database.

        Parameters
        ----------
        name : str
            name of the benefit

        Raises
        ------
        ValueError
            Raise error if benefit has already model output
        """

        # Check if it is possible to delete the benefit. This then also covers checking whether the
        # benefit is locked. If this is the case, it cannot be deleted.
        if self.is_locked(name=name):
            raise ValueError(
                f"'{name}' {self._type} is locked by another process and cannot be deleted."
            )
        
        # Delete benefit
        benefit_path = self._path / name
        benefit = Benefit.load_file(benefit_path / f"{name}.toml")
        shutil.rmtree(benefit_path, ignore_errors=True)
        # Delete output if edited
        output_path = (
            self._database.input_path.parent
            / "output"
            / "Benefits"
            / benefit.attrs.name
        )

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
        # Check if it is possible to edit the benefit. This then also covers checking whether the
        # benefit is already used in a higher level object. If this is the case, it cannot be edited.
        try:
            super().edit(benefit)
        except ValueError as e:
            # If not, raise error
            raise ValueError(e)
        else:
            # Delete output if edited
            output_path = (
                self._database.input_path.parent
                / "output"
                / "Benefits"
                / benefit.attrs.name
            )

            if output_path.exists():
                shutil.rmtree(output_path, ignore_errors=True)
