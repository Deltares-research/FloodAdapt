import shutil

from flood_adapt.dbs_classes.dbs_template import DbsTemplate
from flood_adapt.workflows.benefit_runner import Benefit, BenefitRunner


class DbsBenefit(DbsTemplate[Benefit]):
    display_name = "Benefit"
    dir_name = "benefits"
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
        runner = BenefitRunner(self._database, benefit=object_model)

        # Check if all scenarios are created
        if not all(runner.scenarios["scenario created"] != "No"):
            raise ValueError(
                f"'{object_model.name}' name cannot be created before all necessary scenarios are created."
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

    def edit(self, benefit: Benefit):
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
        super().edit(benefit)

        # Delete output if edited
        output_path = self.output_path / benefit.name
        if output_path.exists():
            shutil.rmtree(output_path, ignore_errors=True)

    def get_runner(self, name: str) -> BenefitRunner:
        return BenefitRunner(self._database, self.get(name))

    def has_run_check(self, name: str) -> bool:
        return self.get_runner(name).has_run_check()

    def ready_to_run(self, name: str) -> bool:
        """Check if all the required scenarios have already been run.

        Returns
        -------
        bool
            True if required scenarios have been already run
        """
        return self.get_runner(name).ready_to_run()
