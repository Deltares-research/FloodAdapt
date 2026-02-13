from flood_adapt.dbs_classes.dbs_template import DbsTemplate
from flood_adapt.misc.exceptions import DatabaseError
from flood_adapt.workflows.benefit_runner import Benefit, BenefitRunner


class DbsBenefit(DbsTemplate[Benefit]):
    display_name = "Benefit"
    dir_name = "benefits"
    _object_class = Benefit
    _higher_lvl_object = ""

    def add(self, obj: Benefit, overwrite: bool = False):
        self._assert_all_scenarios_created(obj)
        super().add(obj, overwrite=overwrite)

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

    def _assert_all_scenarios_created(self, benefit: Benefit):
        runner = BenefitRunner(self._database, benefit=benefit)

        # Check if all scenarios are created
        if not all(runner.scenarios["scenario created"] != "No"):
            raise DatabaseError(
                f"'{benefit.name}' name cannot be created before all necessary scenarios are created."
            )
