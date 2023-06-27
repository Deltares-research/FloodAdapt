import os
from pathlib import Path
from typing import Any, Union

import pandas as pd
import tomli
import tomli_w

from flood_adapt.object_model.interface.benefits import BenefitModel, IBenefit
from flood_adapt.object_model.scenario import Scenario


class Benefit(IBenefit):
    """class holding all information related to a benefit analysis"""

    attrs: BenefitModel
    database_input_path: Union[str, os.PathLike]
    has_run: bool = False

    def check_scenarios(self):
        """Check which scenarios are needed for this benefit calculation and if they have already been created"""

        # Define names of scenarios
        scenarios_calc = {
            "current_no_measures": {},
            "current_measures": {},
            "future_no_measures": {},
            "future_measures": {},
        }

        # Use the predefined names for the current projections and no measures strategy
        for scenario in scenarios_calc.keys():
            scenarios_calc[scenario]["event"] = self.attrs.event_set

            if "current" in scenario:
                scenarios_calc[scenario]["projection"] = "current"
            elif "future" in scenario:
                scenarios_calc[scenario]["projection"] = self.attrs.projection

            if "no_measures" in scenario:
                scenarios_calc[scenario]["strategy"] = "no_measures"
            else:
                scenarios_calc[scenario]["strategy"] = self.attrs.strategy

        # Get the available scenarios
        # TODO this should be done with a function of the database controller
        # but the way it is set-up now there will be issues with cyclic imports
        scenarios_avail = []
        for scenario_path in list(
            self.database_input_path.joinpath("scenarios").glob("*")
        ):
            scenarios_avail.append(
                Scenario.load_file(scenario_path.joinpath(f"{scenario_path.name}.toml"))
            )

        # Check if any of the needed scenarios are already there
        for scenario in scenarios_calc.keys():
            scn_dict = scenarios_calc[scenario].copy()
            scn_dict["name"] = scenario
            scn_dict["long_name"] = scenario
            scenario_obj = Scenario.load_dict(scn_dict, self.database_input_path)
            created = [
                scn_avl for scn_avl in scenarios_avail if scenario_obj == scn_avl
            ]
            if len(created) > 0:
                scenarios_calc[scenario]["scenario created"] = created[0].attrs.name
                if created[0].init_object_model().direct_impacts.has_run:
                    scenarios_calc[scenario]["scenario run"] = "Yes"
                else:
                    scenarios_calc[scenario]["scenario run"] = "No"
            else:
                scenarios_calc[scenario]["scenario created"] = "No"
                scenarios_calc[scenario]["scenario run"] = "No"

        self.scenarios = pd.DataFrame(scenarios_calc).T

        return self.scenarios

    def ready_to_run(self):
        """Checks if all the required scenarios have already been run"""
        ...

    def run_cost_benefit(self):
        """Runs the cost-benefit calculation"""
        ...

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """create Benefit object from toml file"""

        obj = Benefit()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = BenefitModel.parse_obj(toml)
        # if benefits is created by path use that to get to the database path
        obj.database_input_path = Path(filepath).parents[2]
        return obj

    @staticmethod
    def load_dict(data: dict[str, Any], database_input_path: Union[str, os.PathLike]):
        """create Benefit object from dictionary, e.g. when initialized from GUI"""

        obj = Benefit()
        obj.attrs = BenefitModel.parse_obj(data)
        obj.database_input_path = database_input_path
        return obj

    def save(self, filepath: Union[str, os.PathLike]):
        """save Benefit object to a toml file"""
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.dict(exclude_none=True), f)
