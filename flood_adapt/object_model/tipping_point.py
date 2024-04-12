import os
import shutil
from pathlib import Path
from typing import Any, Union

import geopandas as gpd
import numpy as np
import numpy_financial as npf
import pandas as pd
import plotly.graph_objects as go
import tomli
import tomli_w
from fiat_toolbox.metrics_writer.fiat_read_metrics_file import MetricsFileReader

from flood_adapt.object_model.interface.tipping_points import TipPointModel, ITipPoint, TippingPointStatus
from flood_adapt.object_model.scenario import Scenario
from flood_adapt.object_model.site import Site

# add running sfincs & fiat
from flood_adapt.object_model.scenario import run

'''
Instructions for creating tipping point class:

We will create a class for the Tipping Points model. 
Obective: the tipping point model will be used to calculate when sea 
level rise matches a certain metric value (this metric is a result of floodadapt 
simulations, so could be population exposd, houses flooded, etc.)

We should run flooadapt in a for loop for each sea level rise and calculate the 
impacts for the corresponding metric. Once and if the tipping point is reached, 
we should stop the loop and return the tipping point value and corresponding sea level.

Inputs:
slr: list of floats
tipping_point: dict with the following: metric_name, metric_value, metric_unit, metric_type

so for every value in slr, we simulate flooadapt and calculate the output for
the metric value, then we compare the output with our tipping point value. 
Stop when output > tipping point value. 

We also want to include functions like check scenario, create missing scenario, etc.
'''

class TippingPoints(ITipPoint):
    """Class holding all information related to tipping points analysis"""

    def init(self):
        """Initiation function called when object is created through the file or dict options"""
        self.results_path = Path(self.database_input_path).parent.joinpath(
            "output", "tipping_points", self.attrs.name
        )
        self.check_scenarios()
        self.has_run = self.has_run_check()
        # get site config
        self.site_toml_path = (
            Path(self.database_input_path).parent / "static" / "site" / "site.toml"
        )
        self.site_info = Site.load_file(self.site_toml_path)

    def has_run_check(self):
        """Check if the tipping point analysis has already been run"""
        results_toml = self.results_path.joinpath("results.toml")
        results_csv = self.results_path.joinpath("results.csv")
        results_html = self.results_path.joinpath("results.html")
        #TODO: check this
        
        check = all(
            results_toml.exists() for result in [results_toml, results_csv]
        )
        if check:
            with open(results_toml, "rb") as fp:
                self.results = tomli.load(fp)
            #TODO: here what to do?
                
    def check_scenarios(self):
        """Check which scenarios are needed for this tipping point calculation and if they have already been created"""
        # MY CHANGES -calculating scenarios per slr level
        scenarios_calc = {
            f"slr_{slr}": Scenario(
                scenario_id=f"slr_{slr}",
                event_set=self.attrs.event_set,
                projection=self.attrs.projection,
                future_year=self.attrs.future_year,
                slr=slr,
            )
            for slr in self.attrs.sealevelrise
        }

        # Use the predefined names for the current projections and no measures strategy
        for scenario in scenarios_calc.keys():
            scenarios_calc[scenario]["event"] = self.attrs.event_set

            if "current" in scenario:
                scenarios_calc[scenario][
                    "projection"
                ] = self.attrs.current_situation.projection
            elif "future" in scenario:
                scenarios_calc[scenario]["projection"] = self.attrs.projection

            if "no_measures" in scenario:
                scenarios_calc[scenario]["strategy"] = self.attrs.baseline_strategy
            else:
                scenarios_calc[scenario]["strategy"] = self.attrs.strategy
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
            scenario_obj = Scenario.load_dict(scn_dict, self.database_input_path)
            created = [
                scn_avl for scn_avl in scenarios_avail if scenario_obj == scn_avl
            ]
            if len(created) > 0:
                scenarios_calc[scenario]["scenario created"] = created[0].attrs.name
                if created[0].init_object_model().direct_impacts.has_run:
                    scenarios_calc[scenario]["scenario run"] = True
                else:
                    scenarios_calc[scenario]["scenario run"] = False
            else:
                scenarios_calc[scenario]["scenario created"] = "No"
                scenarios_calc[scenario]["scenario run"] = False

        df = pd.DataFrame(scenarios_calc).T
        self.scenarios = df.astype(
            dtype={
                "event": "str",
                "projection": "str",
                "strategy": "str",
                "scenario created": "str",
                "scenario run": bool,
            }
        )
        return self.scenarios
    
    def check_tipping_point(self, scenario: Scenario):
        """Check if the tipping point is reached"""
        # get the metric value
        metric_value = scenario.direct_impacts.metrics[self.attrs.tipping_point["metric_name"]]
        if metric_value > self.attrs.tipping_point["metric_value"]:
            print("Tipping point reached")
            return True
        else:
            return False
        
    def tipping_point_reached(self):
        # function to tell if tipping point was reached or not.
        # if all scenarios have been run, check if tipping point is reached



    # my changes - if some scenarios are not ready, run them
    # TODO: double check this is correct
    def create_missing_scenarios(self, scenario: Scenario):
        """Create missing scenarios"""

        #If scenario has run, you don't need to run it again
        if not scenario.attrs['scenario run']: 
            scens = self.scenarios["scenario created"][~self.scenarios["scenario run"]]
            for scen in scens:
                scenario = Scenario.load_file(scen)
                scenario.run()

                # if the status is reached, save the SLR and the metric value
                if self.check_tipping_point():
                    self.attrs.status = TippingPointStatus.reached
                    break
            
# one base scenario for the tipping points
                # create a list of tipping point scenarios
# then save a tippingpoint folder for different scenarios (so they don't mix) - name is base_scenario + tippingpoint metric+ metric value
# then save the results in the tippingpoint folder
# base scenario ; actual tipping point scenarios (group - save in one folder) : scenario + SLR 
# from the base scenario, it starts generating multiple tipping point scenarios and check if it reaches the tipping point
                
# new attribute: status - running, completed and reached, completed and not reached.
# if reached, save the SLR and the metric value
                    

# post processing stuff still to be done
                # make html & plots
                # write to file

 # test 1s scenarios to check status
                # could also try adding evertyhing        

# TODO: check it's changed to Tipping points
    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """create Benefit object from toml file"""

        obj = Benefit()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = BenefitModel.parse_obj(toml)
        # if benefits is created by path use that to get to the database path
        obj.database_input_path = Path(filepath).parents[2]
        obj.init()
        return obj

    @staticmethod
    def load_dict(data: dict[str, Any], database_input_path: Union[str, os.PathLike]):
        """create Benefit object from dictionary, e.g. when initialized from GUI"""

        obj = Benefit()
        obj.attrs = BenefitModel.parse_obj(data)
        obj.database_input_path = Path(database_input_path)
        obj.init()
        return obj

    def save(self, filepath: Union[str, os.PathLike]):
        """save Benefit object to a toml file"""
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.dict(exclude_none=True), f)
