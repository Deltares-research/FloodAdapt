import shutil
from typing import Any

import geopandas as gpd
import numpy as np
import numpy_financial as npf
import pandas as pd
import plotly.graph_objects as go
import tomli
import tomli_w
from fiat_toolbox.metrics_writer.fiat_read_metrics_file import MetricsFileReader

from flood_adapt.misc.path_builder import (
    ObjectDir,
    TopLevelDir,
    db_path,
)
from flood_adapt.objects.benefits.benefits import Benefit
from flood_adapt.objects.scenarios.scenarios import Scenario
from flood_adapt.workflows.scenario_runner import ScenarioRunner


class BenefitRunner:
    """Object holding all attributes and methods related to a benefit analysis."""

    benefit: Benefit
    _scenarios: pd.DataFrame

    def __init__(self, database, benefit: Benefit):
        """Initialize function called when object is created through the load_file or load_dict methods."""
        self.database = database
        self.benefit = benefit

        # Get output path based on database path
        self.check_scenarios()
        self.results_path = self.database.benefits.output_path.joinpath(
            self.benefit.name
        )
        self.site_info = self.database.site
        self.unit = self.site_info.fiat.config.damage_unit

    @property
    def has_run(self):
        return self.has_run_check()

    @property
    def results(self):
        if hasattr(self, "_results"):
            return self._results
        self._results = self.get_output()
        return self._results

    def get_output(self) -> dict[str, Any]:
        if not self.has_run:
            raise RuntimeError(
                f"Cannot read output since benefit analysis '{self.benefit.name}' has not been run yet."
            )

        results_toml = self.results_path.joinpath("results.toml")
        results_html = self.results_path.joinpath("benefits.html")
        with open(results_toml, mode="rb") as fp:
            results = tomli.load(fp)
        results["html"] = str(results_html)
        self._results = results
        return results

    def has_run_check(self) -> bool:
        """Check if the benefit analysis has already been run.

        Returns
        -------
        has_run : bool
            True if the analysis has already been run, else False
        """
        # Output files to check
        results_toml = self.results_path.joinpath("results.toml")
        results_csv = self.results_path.joinpath("time_series.csv")
        results_html = self.results_path.joinpath("benefits.html")

        check = all(
            result.exists() for result in [results_toml, results_csv, results_html]
        )
        return check

    def check_scenarios(self) -> pd.DataFrame:
        """Check which scenarios are needed for this benefit calculation and if they have already been created.

        The scenarios attribute of the object is updated accordingly and the table of the scenarios is returned.

        Returns
        -------
        pd.DataFrame
            a table with the scenarios of the Benefit analysis and their status
        """
        # Define names of scenarios
        scenarios_calc = {
            "current_no_measures": {},
            "current_with_strategy": {},
            "future_no_measures": {},
            "future_with_strategy": {},
        }

        # Use the predefined names for the current projections and no measures strategy
        for scenario in scenarios_calc.keys():
            scenarios_calc[scenario]["event"] = self.benefit.event_set

            if "current" in scenario:
                scenarios_calc[scenario]["projection"] = (
                    self.benefit.current_situation.projection
                )
            elif "future" in scenario:
                scenarios_calc[scenario]["projection"] = self.benefit.projection

            if "no_measures" in scenario:
                scenarios_calc[scenario]["strategy"] = self.benefit.baseline_strategy
            else:
                scenarios_calc[scenario]["strategy"] = self.benefit.strategy

        # Get the available scenarios
        scenarios_avail = [
            self.database.scenarios.get(scn)
            for scn in self.database.scenarios.summarize_objects()["name"]
        ]

        # Check if any of the needed scenarios are already there
        for scenario in scenarios_calc.keys():
            scn_dict = scenarios_calc[scenario].copy()
            scn_dict["name"] = scenario
            scenario_obj = Scenario(**scn_dict)
            created = [
                scn_avl for scn_avl in scenarios_avail if scenario_obj == scn_avl
            ]
            if len(created) > 0:
                runner = ScenarioRunner(self.database, scenario=created[0])
                scenarios_calc[scenario]["scenario created"] = created[0].name
                scenarios_calc[scenario]["scenario run"] = runner.impacts.has_run
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

    def ready_to_run(self) -> bool:
        """Check if all the required scenarios have already been run.

        Returns
        -------
        bool
            True if required scenarios have been already run
        """
        self.check_scenarios()
        check = all(self.scenarios["scenario run"])

        return check

    def run_cost_benefit(self):
        """Run the cost-benefit calculation for the total study area and the different aggregation levels."""
        # Throw an error if not all runs are finished
        if not self.ready_to_run():
            # First check is scenarios are there
            if "No" in self.scenarios["scenario created"].to_numpy():
                raise RuntimeError("Necessary scenarios have not been created yet.")
            scens = self.scenarios["scenario created"][~self.scenarios["scenario run"]]
            raise RuntimeError(
                f"Scenarios {', '.join(scens.values)} need to be run before the cost-benefit analysis can be performed"
            )

        # If path for results does not yet exist, make it, and if it does delete it and recreate it
        if not self.results_path.is_dir():
            self.results_path.mkdir(parents=True)
        else:
            shutil.rmtree(self.results_path)
            self.results_path.mkdir(parents=True)

        # Run the cost-benefit analysis
        self.cba()
        # Run aggregation benefits
        self.cba_aggregation()
        # Updates results
        self.has_run_check()

        # Cache results
        self.results

    def cba(self):
        """Cost-benefit analysis for the whole study area."""
        # Get EAD for each scenario and save to new dataframe
        scenarios = self.scenarios.copy(deep=True)
        scenarios["EAD"] = None

        scn_output_path = db_path(TopLevelDir.output, ObjectDir.scenario)

        # Get metrics per scenario
        for index, scenario in scenarios.iterrows():
            scn_name = scenario["scenario created"]
            collective_fn = scn_output_path.joinpath(
                scn_name, f"Infometrics_{scn_name}.csv"
            )
            collective_metrics = MetricsFileReader(
                collective_fn,
            ).read_metrics_from_file()

            # Fill scenarios EAD column with values from metrics
            scenarios.loc[index, "EAD"] = float(
                collective_metrics["Value"]["ExpectedAnnualDamages"]
            )

        # Get years of interest
        year_start = self.benefit.current_situation.year
        year_end = self.benefit.future_year

        # Calculate benefits
        cba = self._calc_benefits(
            years=[year_start, year_end],
            risk_no_measures=[
                scenarios.loc["current_no_measures", "EAD"],
                scenarios.loc["future_no_measures", "EAD"],
            ],
            risk_with_strategy=[
                scenarios.loc["current_with_strategy", "EAD"],
                scenarios.loc["future_with_strategy", "EAD"],
            ],
            discount_rate=self.benefit.discount_rate,
        )

        # Save indicators in dictionary
        results = {}
        # Get net present value of benefits
        results["benefits"] = cba["benefits_discounted"].sum()

        # Only if costs are provided do the full cost-benefit analysis
        cost_calc = (self.benefit.implementation_cost is not None) and (
            self.benefit.annual_maint_cost is not None
        )
        if cost_calc:
            cba = self._calc_costs(
                benefits=cba,
                implementation_cost=self.benefit.implementation_cost,
                annual_maint_cost=self.benefit.annual_maint_cost,
                discount_rate=self.benefit.discount_rate,
            )
            # Calculate costs
            results["costs"] = cba["costs_discounted"].sum()
            # Benefit to Cost Ratio
            results["BCR"] = np.round(results["benefits"] / results["costs"], 2)
            # Net present value
            results["NPV"] = cba["profits_discounted"].sum()
            # Internal Rate of Return
            results["IRR"] = np.round(npf.irr(cba["profits"]), 3)

        # Save results
        if not self.results_path.is_dir():
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

    def cba_aggregation(self):
        """Zonal Benefits analysis for the different aggregation areas."""
        results_path = db_path(TopLevelDir.output, ObjectDir.scenario)
        # Get years of interest
        year_start = self.benefit.current_situation.year
        year_end = self.benefit.future_year

        # Get EAD for each scenario and save to new dataframe
        scenarios = self.scenarios.copy(deep=True)

        # Read in the names of the aggregation area types
        aggregations = [aggr.name for aggr in self.site_info.fiat.config.aggregation]

        # Check if equity information is available to define variables to use
        vars = []
        for i, aggr_name in enumerate(aggregations):
            if self.site_info.fiat.config.aggregation[i].equity is not None:
                vars.append(["EAD", "EWEAD"])
            else:
                vars.append(["EAD"])

        # Define which names are used in the metric tables
        var_metric = {"EAD": "ExpectedAnnualDamages", "EWEAD": "EWEAD"}

        # Prepare dictionary to save values
        risk = {}

        # Fill in the dictionary
        for i, aggr_name in enumerate(aggregations):
            risk[aggr_name] = {}
            values = {}
            for var in vars[i]:
                values[var] = []
            for index, scenario in scenarios.iterrows():
                scn_name = scenario["scenario created"]
                # Get available aggregation levels
                aggregation_fn = results_path.joinpath(
                    scn_name, f"Infometrics_{scn_name}_{aggr_name}.csv"
                )
                for var in vars[i]:
                    # Get metrics per scenario and per aggregation
                    aggregated_metrics = MetricsFileReader(
                        aggregation_fn,
                    ).read_aggregated_metric_from_file(var_metric[var])[2:]
                    aggregated_metrics = aggregated_metrics.loc[
                        aggregated_metrics.index.dropna()
                    ]
                    aggregated_metrics.name = scenario.name
                    values[var].append(aggregated_metrics)

            # Combine values in a single dataframe
            for var in vars[i]:
                risk[aggr_name][var] = pd.DataFrame(values[var]).T.astype(float)

        var_output = {"EAD": "Benefits", "EWEAD": "Equity Weighted Benefits"}

        # Calculate benefits
        benefits = {}
        for i, aggr_name in enumerate(aggregations):
            benefits[aggr_name] = pd.DataFrame()
            benefits[aggr_name].index = risk[aggr_name]["EAD"].index
            for var in vars[i]:
                for index, row in risk[aggr_name][var].iterrows():
                    cba = self._calc_benefits(
                        years=[year_start, year_end],
                        risk_no_measures=[
                            row["current_no_measures"],
                            row["future_no_measures"],
                        ],
                        risk_with_strategy=[
                            row["current_with_strategy"],
                            row["future_with_strategy"],
                        ],
                        discount_rate=self.benefit.discount_rate,
                    )
                    benefits[aggr_name].loc[row.name, var_output[var]] = cba[
                        "benefits_discounted"
                    ].sum()

        # Save results
        if not self.results_path.is_dir():
            self.results_path.mkdir(parents=True)

        # Save benefits per aggregation area (csv and gpkg)
        for i, aggr_name in enumerate(aggregations):
            csv_filename = self.results_path.joinpath(f"benefits_{aggr_name}.csv")
            benefits[aggr_name].to_csv(csv_filename, index=True)

            # Load aggregation areas
            ind = [
                i
                for i, n in enumerate(self.site_info.fiat.config.aggregation)
                if n.name == aggr_name
            ][0]
            aggr_areas_path = (
                db_path(TopLevelDir.static)
                / self.site_info.fiat.config.aggregation[ind].file
            )
            aggr_areas = gpd.read_file(aggr_areas_path, engine="pyogrio")
            # Define output path
            outpath = self.results_path.joinpath(f"benefits_{aggr_name}.gpkg")
            # Save file
            aggr_areas = aggr_areas.join(
                benefits[aggr_name],
                on=self.site_info.fiat.config.aggregation[ind].field_name,
            )
            aggr_areas.to_file(outpath, driver="GPKG")

    @staticmethod
    def _calc_benefits(
        years: list[int, int],
        risk_no_measures: list[float, float],
        risk_with_strategy: list[float, float],
        discount_rate: float,
    ) -> pd.DataFrame:
        """Calculate per year benefits and discounted benefits.

        Parameters
        ----------
        years : list[int, int]
            the current and future year for the analysis
        risk_no_measures : list[float, float]
            the current and future risk value without any measures
        risk_with_strategy : list[float, float]
            the current and future risk value with the strategy under investigation
        discount_rate : float
            the yearly discount rate used to calculated the total benefit

        Returns
        -------
        pd.DataFrame
            Dataframe containing the time-series of risks and benefits per year
        """
        benefits = pd.DataFrame(
            data={"risk_no_measures": np.nan, "risk_with_strategy": np.nan},
            index=np.arange(years[0], years[1] + 1),
        )
        benefits.index.names = ["year"]

        # Fill in dataframe
        for strat, risk in zip(
            ["no_measures", "with_strategy"], [risk_no_measures, risk_with_strategy]
        ):
            benefits.loc[years[0], f"risk_{strat}"] = risk[0]
            benefits.loc[years[1], f"risk_{strat}"] = risk[1]

        # Assume linear trend between current and future
        benefits = benefits.interpolate(method="linear")

        # Calculate benefits
        benefits["benefits"] = (
            benefits["risk_no_measures"] - benefits["risk_with_strategy"]
        )
        # Calculate discounted benefits using the provided discount rate
        benefits["benefits_discounted"] = benefits["benefits"] / (
            1 + discount_rate
        ) ** (benefits.index - benefits.index[0])

        return benefits

    @staticmethod
    def _calc_costs(
        benefits: pd.DataFrame,
        implementation_cost: float,
        annual_maint_cost: float,
        discount_rate: float,
    ) -> pd.DataFrame:
        """Calculate per year costs and discounted costs.

        Parameters
        ----------
        benefits : pd.DataFrame
            a time series of benefits per year (produced with __calc_benefits method)
        implementation_cost : float
            initial costs of implementing the adaptation strategy
        annual_maint_cost : float
            annual maintenance cost of the adaptation  strategy
        discount_rate : float
            yearly discount rate

        Returns
        -------
        pd.DataFrame
            Dataframe containing the time-series of benefits, costs and profits per year
        """
        benefits = benefits.copy()
        benefits["costs"] = np.nan
        # implementations costs at current year and maintenance from year 1
        benefits.loc[benefits.index[0], "costs"] = implementation_cost
        benefits.loc[benefits.index[1:], "costs"] = annual_maint_cost
        benefits["costs_discounted"] = benefits["costs"] / (1 + discount_rate) ** (
            benefits.index - benefits.index[0]
        )

        # Benefit to Cost Ratio
        benefits["profits"] = benefits["benefits"] - benefits["costs"]
        benefits["profits_discounted"] = benefits["profits"] / (1 + discount_rate) ** (
            benefits.index - benefits.index[0]
        )

        return benefits

    def _make_html(self, cba):
        """Make an html with the time-series of the benefits and discounted benefits."""
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
