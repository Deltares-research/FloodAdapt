import math
import shutil
import time
from pathlib import Path

from flood_adapt.adapter.fiat_adapter import FiatAdapter
from flood_adapt.adapter.interface.impact_adapter import IImpactAdapter
from flood_adapt.misc.config import Settings
from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.object_model.direct_impact.impact_strategy import ImpactStrategy
from flood_adapt.object_model.hazard.floodmap import FloodMap
from flood_adapt.object_model.interface.database_user import DatabaseUser
from flood_adapt.object_model.interface.path_builder import (
    ObjectDir,
    TopLevelDir,
    db_path,
)
from flood_adapt.object_model.interface.projections import SocioEconomicChange
from flood_adapt.object_model.interface.scenarios import IScenario


# TODO move code that is related to fiat to the Fiat Adapter
class Impacts(DatabaseUser):
    """All information related to the direct impacts of the scenario.

    Includes methods to run the impact model or check if it has already been run.
    """

    logger = FloodAdaptLogging.getLogger(__name__)
    name: str
    socio_economic_change: SocioEconomicChange
    impact_strategy: ImpactStrategy

    def __init__(self, scenario: IScenario):
        self.name = scenario.attrs.name
        self.scenario = scenario
        self.site_info = self.database.site
        self.models: list[IImpactAdapter] = [self.database.static.get_fiat_model()]

        self.set_socio_economic_change(scenario.attrs.projection)
        self.set_impact_strategy(scenario.attrs.strategy)

    @property
    def hazard(self) -> FloodMap:
        return FloodMap(self.name)

    @property
    def results_path(self) -> Path:
        return db_path(
            TopLevelDir.output, object_dir=ObjectDir.scenario, obj_name=self.name
        )

    @property
    def impacts_path(self) -> Path:
        return self.results_path / "Impacts"

    @property
    def fiat_path(self) -> Path:
        return self.impacts_path / "fiat_model"

    @property
    def has_run(self) -> bool:
        return self.has_run_check()

    def run(self):
        """Run the direct impact model(s)."""
        if self.has_run:
            self.logger.info("Direct impacts have already been run.")
            return
        for model in self.models:
            model.run(self.scenario)

    def has_run_check(self) -> bool:
        """Check if the direct impact has been run.

        Returns
        -------
        bool
            _description_
        """
        checks = []
        for model in self.models:
            checks.append(model.has_run(self.scenario))
        return all(checks)

    def set_socio_economic_change(self, projection: str) -> None:
        """Set the SocioEconomicChange object of the scenario.

        Parameters
        ----------
        projection : str
            Name of the projection used in the scenario
        """
        self.socio_economic_change = self.database.projections.get(
            projection
        ).get_socio_economic_change()

    def set_impact_strategy(self, strategy: str) -> None:
        """Set the ImpactStrategy object of the scenario.

        Parameters
        ----------
        strategy : str
            Name of the strategy used in the scenario
        """
        self.impact_strategy = self.database.strategies.get(
            strategy
        ).get_impact_strategy()

    def preprocess_models(self):
        self.logger.info("Preparing impact models...")
        # Preprocess all impact model input
        start_time = time.time()
        self.preprocess_fiat()
        end_time = time.time()
        self.logger.info(
            f"FIAT preprocessing took {str(round(end_time - start_time, 2))} seconds"
        )

    def preprocess_fiat(self):
        """Update FIAT model based on scenario information and then runs the FIAT model."""
        # Check if hazard is already run
        if not self.hazard.has_run:
            raise ValueError(
                "Hazard for this scenario has not been run yet! FIAT cannot be initiated."
            )

        # Get the location of the FIAT template model
        template_path = self.database.static_path / "templates" / "fiat"

        # Read FIAT template with FIAT adapter
        with FiatAdapter(
            model_root=str(template_path), database_path=str(Settings().database_path)
        ) as fa:
            # This should be done by a function in the FiatAdapter
            if self.fiat_path.is_dir():
                shutil.rmtree(self.fiat_path)
            self.fiat_path.mkdir(parents=True)

            # Get ids of existing objects
            ids_existing = fa.fiat_model.exposure.exposure_db["Object ID"].to_list()

            # Implement socioeconomic changes if needed
            # First apply economic growth to existing objects
            if self.socio_economic_change.attrs.economic_growth is not None:
                if not math.isclose(
                    self.socio_economic_change.attrs.economic_growth, 0, abs_tol=1e-6
                ):
                    fa.apply_economic_growth(
                        economic_growth=self.socio_economic_change.attrs.economic_growth,
                        ids=ids_existing,
                    )

            # Then we create the new population growth area if provided
            # In that area only the economic growth is taken into account
            # Order matters since for the pop growth new, we only want the economic growth!
            if self.socio_economic_change.attrs.population_growth_new is not None:
                if not math.isclose(
                    self.socio_economic_change.attrs.population_growth_new,
                    0,
                    abs_tol=1e-6,
                ):
                    # Get path of new development area geometry
                    area_path = (
                        self.database.projections.input_path
                        / self.scenario.projection
                        / self.socio_economic_change.attrs.new_development_shapefile
                    )
                    dem = (
                        self.database.static_path
                        / "dem"
                        / self.site_info.attrs.sfincs.dem.filename
                    )
                    aggregation_areas = [
                        self.database.static_path / aggr.file
                        for aggr in self.site_info.attrs.fiat.config.aggregation
                    ]
                    attribute_names = [
                        aggr.field_name
                        for aggr in self.site_info.attrs.fiat.config.aggregation
                    ]
                    label_names = [
                        f"Aggregation Label: {aggr.name}"
                        for aggr in self.site_info.attrs.fiat.config.aggregation
                    ]

                    fa.apply_population_growth_new(
                        population_growth=self.socio_economic_change.attrs.population_growth_new,
                        ground_floor_height=self.socio_economic_change.attrs.new_development_elevation.value,
                        elevation_type=self.socio_economic_change.attrs.new_development_elevation.type,
                        area_path=area_path,
                        ground_elevation=dem,
                        aggregation_areas=aggregation_areas,
                        attribute_names=attribute_names,
                        label_names=label_names,
                    )

            # Last apply population growth to existing objects
            if self.socio_economic_change.attrs.population_growth_existing is not None:
                if not math.isclose(
                    self.socio_economic_change.attrs.population_growth_existing,
                    0,
                    abs_tol=1e-6,
                ):
                    fa.apply_population_growth_existing(
                        population_growth=self.socio_economic_change.attrs.population_growth_existing,
                        ids=ids_existing,
                    )

            # Then apply Impact Strategy by iterating trough the impact measures
            for measure in self.impact_strategy.measures:
                if measure.attrs.type == "elevate_properties":
                    fa.elevate_properties(
                        elevate=measure,
                        ids=ids_existing,
                    )
                elif measure.attrs.type == "buyout_properties":
                    fa.buyout_properties(
                        buyout=measure,
                        ids=ids_existing,
                    )
                elif measure.attrs.type == "floodproof_properties":
                    fa.floodproof_properties(
                        floodproof=measure,
                        ids=ids_existing,
                    )
                else:
                    self.logger.warning(
                        f"Impact measure type not recognized: {measure.attrs.type}"
                    )

            # setup hazard for fiat
            fa.set_hazard(self.hazard)

            # Save the updated FIAT model
            fa.fiat_model.set_root(self.fiat_path)
            fa.fiat_model.write()
