import os
import shutil
from pathlib import Path
from typing import Any, Union
import glob 

import numpy as np
import numpy_financial as npf
import pandas as pd
import plotly.graph_objects as go
import tomli
import tomli_w
from fiat_toolbox.metrics_writer.fiat_read_metrics_file import MetricsFileReader

from flood_adapt.object_model.interface.benefits import BenefitModel, IBenefit
from flood_adapt.object_model.scenario import Scenario
from flood_adapt.object_model.site import Site


class Benefit(IBenefit):
    """Class holding all information related to a benefit analysis"""

    attrs: BenefitModel
    database_input_path: Union[str, os.PathLike]
    results_path: Union[str, os.PathLike]
    scenarios: pd.DataFrame
    has_run: bool = False

    def init(self):
        """Initiation function called when object is created through the file or dict options"""
        self.results_path = Path(self.database_input_path).parent.joinpath(
            "output", "Benefits", self.attrs.name
        )
        self.check_scenarios()
        self.has_run = self.has_run_check()
        # Get monetary units
        site_obj = Site.load_file(
            Path(self.database_input_path).parent / "static" / "site" / "site.toml"
        )
        self.unit = site_obj.attrs.fiat.damage_unit

    def has_run_check(self):
        """Check if the benefit assessment has already been run"""
        results_toml = self.results_path.joinpath("results.toml")
        results_csv = self.results_path.joinpath("time_series.csv")
        results_html = self.results_path.joinpath("benefits.html")

        check = all(
            result.exists() for result in [results_toml, results_csv, results_html]
        )
        if check:
            with open(results_toml, mode="rb") as fp:
                self.results = tomli.load(fp)
            self.results["html"] = str(results_html)
        return check

    def check_scenarios(self):
        """Check which scenarios are needed for this benefit calculation and if they have already been created"""

        # Define names of scenarios
        scenarios_calc = {
            "current_no_measures": {},
            "current_with_strategy": {},
            "future_no_measures": {},
            "future_with_strategy": {},
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

    def ready_to_run(self):
        """Checks if all the required scenarios have already been run"""
        self.check_scenarios()
        check = all(self.scenarios["scenario run"])
        return check

    def run_cost_benefit(self):
        """Runs the cost-benefit calculation"""

        # Throw an error if not all runs are finished
        if not self.ready_to_run():
            scens = self.scenarios["scenario created"][~self.scenarios["scenario run"]]
            raise RuntimeError(
                f"Scenarios {', '.join(scens.values)} need to be run before the cost-benefit analysis can be performed"
            )
        # Run the cost-benefit analysis
        self.cba()
        # Updates results
        self.has_run_check()

    def cba(self):
        """Cost-benefit analysis"""
        # Get EAD for each scenario and save to new dataframe
        scenarios = self.scenarios.copy(deep=True)
        scenarios_agg = self.scenarios.copy(deep=True)
        scenarios["EAD"] = None

        results_path = self.database_input_path.parent.joinpath("output", "Scenarios")
        count2= 0
        for index, scenario in scenarios.iterrows():
            scn_name = scenario["scenario created"]
            collective_fn = results_path.joinpath(scn_name, f"Infometrics_{scn_name}.csv")
            aggregation_fn = glob.glob(str(results_path.joinpath(scn_name, f"Infometrics_{scn_name}_*")))
            collective_metrics = MetricsFileReader(collective_fn,).read_metrics_from_file()
            aggregation_metrics = []
            aggregation_metrics_zones = []
            nested_df={}
            for i in aggregation_fn:
                aggregated_metrics = MetricsFileReader(i,).read_aggregated_metric_from_file("ExpectedAnnualDamages")[2:]
                aggregated_metrics= aggregated_metrics.loc[aggregated_metrics.index.dropna()]
                EAD = aggregated_metrics.astype(float).values
                zones = aggregated_metrics.index
                aggregation_metrics.append(EAD)
                aggregation_metrics_zones.append(zones)
            count = 0
            for idx, arr in enumerate(aggregation_metrics):
                df = pd.DataFrame({f"{Path(aggregation_fn[count]).name}": arr})
                nested_df[idx] = df
                count = count + 1
            aggregation_metrics_df=[]
            agg_scenarios_dic = {}
            count = 0
            for key, value in nested_df.items():
                df_transpose = value.transpose()
                column_names = aggregation_metrics_zones[count]
                df_transpose.columns = column_names
                aggregation_metrics_df.append(df_transpose) #create horizontal data to fill in in scenarios
                agg_scenarios = pd.concat([scenarios_agg,pd.DataFrame(columns=column_names)]) 
                agg_scenarios_dic[f"{Path(aggregation_fn[count]).name}"] = agg_scenarios    # Create dictionary with df inside of scenarios and empty columns with layer names
                count = count + 1                  

            #Fill scenarios EAD column with values from metrics
            scenarios.loc[index, "EAD"] = float(
                collective_metrics["Value"]["ExpectedAnnualDamages"] 
            )
               
            count = 0
            scenarios_agg_EAD = {}
            for key,value in agg_scenarios_dic.items():
                df = value
                df.reset_index()
                df.iloc[count2,5:] = df.iloc[count2,5:].fillna(aggregation_metrics_df[count].iloc[0,0:])
                df.to_csv(os.path.join(r"C:\Users\rautenba\OneDrive - Stichting Deltares\Documents\Projects\FloodAdapt\Benefit_Aggregation\test_run_files", (f"{scn_name}_{Path(aggregation_fn[count]).name}")))
                scenarios_agg_EAD[f"{Path(aggregation_fn[count]).name}"] = df 
                count = count +1
            count2 = count2 +1 

        #Open files to create one dataframe for aggregation per level
        # # Find way with glob open all files and then run through all
        #                                        
        df_1 = pd.read_csv(r"C:\Users\rautenba\OneDrive - Stichting Deltares\Documents\Projects\FloodAdapt\Benefit_Aggregation\test_run_files\all_projections_test_set_elevate_comb_correct_Infometrics_all_projections_test_set_elevate_comb_correct_aggr_lvl_1.csv")
        df_2 = pd.read_csv(r"C:\Users\rautenba\OneDrive - Stichting Deltares\Documents\Projects\FloodAdapt\Benefit_Aggregation\test_run_files\current_test_set_no_measures_Infometrics_current_test_set_no_measures_aggr_lvl_1.csv")
        df_3 = pd.read_csv(r"C:\Users\rautenba\OneDrive - Stichting Deltares\Documents\Projects\FloodAdapt\Benefit_Aggregation\test_run_files\all_projections_test_set_no_measures_Infometrics_all_projections_test_set_no_measures_aggr_lvl_1.csv")
        df_4=  pd.read_csv(r"C:\Users\rautenba\OneDrive - Stichting Deltares\Documents\Projects\FloodAdapt\Benefit_Aggregation\test_run_files\current_test_set_elevate_comb_correct_Infometrics_current_test_set_elevate_comb_correct_aggr_lvl_1.csv")
        df_1.update(df_2)
        df_1.update(df_3)
        df_1.update(df_4)
        aggregation_scenarios_EAD_level1 = df_1
        #For all column after aggregation_scenarios_EAD_level1.iloc[0:,6] do subtraction current no - current with and future no - future with
        df_1 = pd.read_csv(r"C:\Users\rautenba\OneDrive - Stichting Deltares\Documents\Projects\FloodAdapt\Benefit_Aggregation\test_run_files\all_projections_test_set_elevate_comb_correct_Infometrics_all_projections_test_set_elevate_comb_correct_aggr_lvl_2.csv")
        df_2 = pd.read_csv(r"C:\Users\rautenba\OneDrive - Stichting Deltares\Documents\Projects\FloodAdapt\Benefit_Aggregation\test_run_files\current_test_set_no_measures_Infometrics_current_test_set_no_measures_aggr_lvl_2.csv")
        df_3 = pd.read_csv(r"C:\Users\rautenba\OneDrive - Stichting Deltares\Documents\Projects\FloodAdapt\Benefit_Aggregation\test_run_files\all_projections_test_set_no_measures_Infometrics_all_projections_test_set_no_measures_aggr_lvl_2.csv")
        df_4=  pd.read_csv(r"C:\Users\rautenba\OneDrive - Stichting Deltares\Documents\Projects\FloodAdapt\Benefit_Aggregation\test_run_files\current_test_set_elevate_comb_correct_Infometrics_current_test_set_elevate_comb_correct_aggr_lvl_2.csv")
        df_1.update(df_2)
        df_1.update(df_3)
        df_1.update(df_4)
        aggregation_scenarios_EAD_level2 = df_1
        aggregation_scenarios_EAD =[aggregation_scenarios_EAD_level1,aggregation_scenarios_EAD_level2]

        # Calculate current and future benefits
        for idx, i in enumerate(aggregation_scenarios_EAD):
            current_benefit = pd.Series(i.iloc[0, 6:] - i.iloc[1, 6:], name="current Benefits")
            future_benefit = pd.Series(i.iloc[2, 6:] - i.iloc[3, 6:], name="Future Benefits")
            i = i.append(current_benefit, ignore_index=True)
            i = i.append(future_benefit, ignore_index=True)
            aggregation_scenarios_EAD[idx] = i

       
        # Get years of interest
        year_start = self.attrs.current_situation.year
        year_end = self.attrs.future_year

        # Prepare dataframe
        cba = pd.DataFrame(
            data={"risk_no_measures": np.nan, "risk_with_strategy": np.nan},
            index=np.arange(year_start, year_end + 1),
        )
        cba.index.names = ["year"]

        # Fill in dataframe
        for strat in ["no_measures", "with_strategy"]:
            cba.loc[year_start, f"risk_{strat}"] = scenarios.loc[
                f"current_{strat}", "EAD"
            ]
            cba.loc[year_end, f"risk_{strat}"] = scenarios.loc[f"future_{strat}", "EAD"]

        # Assume linear trend between current and future
        cba = cba.interpolate(method="linear")
        # Calculate benefits
        cba["benefits"] = cba["risk_no_measures"] - cba["risk_with_strategy"]
        # Calculate discounted benefits using the provided discount rate
        cba["benefits_discounted"] = cba["benefits"] / (
            1 + self.attrs.discount_rate
        ) ** (cba.index - cba.index[0])
        cba = cba.round(0)  # Round results

        results = {}
        # Get net present value of benefits
        results["benefits"] = cba["benefits_discounted"].sum()

        # Only if costs are provided do the full cost-benefit analysis
        cost_calc = (self.attrs.implementation_cost is not None) and (
            self.attrs.annual_maint_cost is not None
        )
        if cost_calc:
            cba["costs"] = np.nan
            # implementations costs at current year and maintenance from year 1
            cba.loc[year_start, "costs"] = self.attrs.implementation_cost
            cba.loc[cba.index[1:], "costs"] = self.attrs.annual_maint_cost
            cba["costs_discounted"] = cba["costs"] / (1 + self.attrs.discount_rate) ** (
                cba.index - cba.index[0]
            )
            cba = cba.round(0)  # Round results
            results["costs"] = cba["costs_discounted"].sum()

            results["BCR"] = np.round(
                results["benefits"] / results["costs"], 2
            )  # Benefit to Cost Ratio
            cba["profits"] = cba["benefits"] - cba["costs"]
            cba["profits_discounted"] = cba["profits"] / (
                1 + self.attrs.discount_rate
            ) ** (cba.index - cba.index[0])
            cba = cba.round(0)  # Round results
            results["NPV"] = cba["profits_discounted"].sum()
            results["IRR"] = np.round(
                npf.irr(cba["profits"]), 3
            )  #  Internal Rate of Return

        # Save results
        # If path for results does not yet exist, make it
        if not self.results_path.is_dir():
            self.results_path.mkdir(parents=True)
        else:
            shutil.rmtree(self.results_path)
            self.results_path.mkdir(parents=True)

        # Save indicators in a toml file
        indicators = self.results_path.joinpath("results.toml")
        with open(indicators, "wb") as f:
            tomli_w.dump(results, f)

        # Save time-series in a csv
        time_series = self.results_path.joinpath("time_series.csv")
        cba.to_csv(time_series)

        # Make html
        self._make_html(cba)

    def _make_html(self, cba):
        "Make an html with the time-series of the benefits and discounted benefits"
        # Save a plotly graph in an html
        fig = go.Figure()

        # Get only endpoints
        cba2 = cba.iloc[[0, -1]]

        # Add graph with benefits
        fig.add_trace(
            go.Scatter(
                x=cba.index,
                y=cba["benefits"],
                mode="lines",
                line_color="black",
                name="Interpolated benefits",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=cba2.index,
                y=cba2["benefits"],
                mode="markers",
                marker_size=10,
                marker_color="rgba(53,217,44,1)",
                name="Calculated benefits",
            )
        )

        fig.add_trace(
            go.Scatter(
                x=cba.index,
                y=cba["benefits_discounted"],
                mode="lines",
                line_color="rgba(35,150,29,1)",
                name="Discounted benefits",
            ),
        )
        # fig.add_trace(
        #     go.Scatter(
        #         x=cba2.index,
        #         y=cba2["benefits_discounted"],
        #         mode="markers",
        #         marker_size=10,
        #         marker_color="rgba(35,150,29,1)",
        #         name="Calculated discounted benefits",
        #     )
        # )

        fig.add_trace(
            go.Scatter(
                x=cba.index,
                y=cba["benefits_discounted"],
                mode="none",
                fill="tozeroy",
                fillcolor="rgba(35,150,29,0.5)",
                name="Benefits",
            )
        )

        # Update xaxis properties
        fig.update_xaxes(title_text="Year")
        # Update yaxis properties
        fig.update_yaxes(title_text=f"Annual Benefits ({self.unit})")

        fig.update_layout(
            autosize=False,
            height=400,
            width=800,
            margin={"r": 0, "l": 0, "b": 0, "t": 0},
            font={"size": 12, "color": "black", "family": "Arial"},
        )

        # write html to results folder
        html = self.results_path.joinpath("benefits.html")
        fig.write_html(html)

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
