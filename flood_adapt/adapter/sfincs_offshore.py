import shutil
from pathlib import Path

import pandas as pd

from flood_adapt.adapter.interface.offshore import IOffshoreSfincsHandler
from flood_adapt.adapter.sfincs_adapter import SfincsAdapter
from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.object_model.hazard.event.event_set import EventSet
from flood_adapt.object_model.hazard.event.historical import HistoricalEvent
from flood_adapt.object_model.hazard.event.hurricane import HurricaneEvent
from flood_adapt.object_model.hazard.forcing.meteo_handler import MeteoHandler
from flood_adapt.object_model.hazard.forcing.wind import WindMeteo
from flood_adapt.object_model.hazard.interface.forcing import (
    ForcingSource,
    IWind,
)
from flood_adapt.object_model.interface.database_user import DatabaseUser
from flood_adapt.object_model.interface.path_builder import (
    ObjectDir,
    TopLevelDir,
    db_path,
)
from flood_adapt.object_model.interface.scenarios import IScenario


class OffshoreSfincsHandler(IOffshoreSfincsHandler, DatabaseUser):
    logger = FloodAdaptLogging.getLogger("OffshoreSfincsAdapter")
    template_path: Path

    def __init__(self) -> None:
        self.template_path = (
            self.database.static.get_offshore_sfincs_model().get_model_root()
        )

    def get_resulting_waterlevels(self, scenario: IScenario) -> pd.DataFrame:
        path = self._get_simulation_path(scenario)

        if not self.requires_offshore_run(scenario):
            raise ValueError("Offshore model is not required for this scenario")

        self.run_offshore(scenario)

        with SfincsAdapter(model_root=path) as offshore_model:
            waterlevels = offshore_model.get_wl_df_from_offshore_his_results()

        return waterlevels

    @staticmethod
    def requires_offshore_run(scenario: IScenario) -> bool:
        return any(
            forcing.source in [ForcingSource.MODEL, ForcingSource.TRACK]
            for forcing in scenario.event.get_forcings()
        )

    def run_offshore(self, scenario: IScenario):
        """Prepare the forcings of the historical event.

        If the forcings require it, this function will:
        - preprocess and run offshore model: prepare and run the offshore model to obtain water levels for the boundary condition of the nearshore model.

        """
        sim_path = self._get_simulation_path(scenario)

        sim_path.mkdir(parents=True, exist_ok=True)
        self._preprocess_sfincs_offshore(scenario)
        self._execute_sfincs_offshore(sim_path, scenario)

    def _preprocess_sfincs_offshore(self, scenario: IScenario):
        """Preprocess offshore model to obtain water levels for boundary condition of the nearshore model.

        This function is reused for ForcingSources: MODEL & TRACK.

        Args:
            sim_path path to the root of the offshore model
        """
        self.logger.info(
            f"Preparing offshore model to generate waterlevels for `{scenario.attrs.name}`"
        )

        sim_path = self._get_simulation_path(scenario)
        with SfincsAdapter(model_root=self.template_path) as _offshore_model:
            if _offshore_model.sfincs_completed(scenario):
                self.logger.info(
                    f"Skip preprocessing offshore model as it has already been run for `{scenario.attrs.name}`."
                )
                return

            # SfincsAdapter.write() doesnt write the bca file apparently so we need to copy the template
            if sim_path.exists():
                shutil.rmtree(sim_path)
            shutil.copytree(self.template_path, sim_path)

            # Set root & create dir and write template model
            _offshore_model.write(path_out=sim_path)

            event = scenario.event
            physical_projection = scenario.projection.get_physical_projection()

            # Create any event specific files
            event.preprocess(sim_path)

            # Edit offshore model
            _offshore_model.set_timing(event.attrs.time)

            # Add water levels
            _offshore_model._add_bzs_from_bca(event, physical_projection.attrs)

            # Add spw if applicable
            if isinstance(event, HurricaneEvent):
                _offshore_model._add_forcing_spw(
                    sim_path / f"{event.attrs.track_name}.spw"
                )

            # Add wind and if applicable pressure forcing from meteo data
            elif isinstance(event, HistoricalEvent):
                wind_forcings = [
                    f for f in event.get_forcings() if isinstance(f, IWind)
                ]

                if wind_forcings:
                    if len(wind_forcings) > 1:
                        raise ValueError("Only one wind forcing is allowed")
                    wind_forcing = wind_forcings[0]

                    # Add wind forcing
                    _offshore_model._add_forcing_wind(wind_forcing)

                    # Add pressure forcing for the offshore model (this doesnt happen normally in _add_forcing_wind() for overland models)
                    if isinstance(wind_forcing, WindMeteo):
                        ds = MeteoHandler().read(event.attrs.time)
                        _offshore_model._add_pressure_forcing_from_grid(ds=ds)

            # write sfincs model in output destination
            _offshore_model.write(path_out=sim_path)

    def _execute_sfincs_offshore(self, sim_path: Path, scenario: IScenario):
        self.logger.info(f"Running offshore model in {sim_path}")

        with SfincsAdapter(model_root=sim_path) as _offshore_model:
            if _offshore_model.sfincs_completed(scenario):
                self.logger.info(
                    "Skip running offshore model as it has already been run."
                )
                return

            success = _offshore_model.execute(path=sim_path, strict=False)

            if not success:
                raise RuntimeError(
                    f"Running offshore SFINCS model failed. See {sim_path} for more information."
                )

    def _get_simulation_path(self, scenario: IScenario) -> Path:
        event = scenario.strategy
        if isinstance(event, EventSet):
            return (
                db_path(
                    TopLevelDir.output,
                    object_dir=ObjectDir.scenario,
                    obj_name=scenario.attrs.name,
                )
                / "Flooding"
                / "simulations"
                / event.attrs.name  # ? add sub event name? or do we only run offshore once for the entire event set?
                / self.template_path.name
            )
        else:
            return (
                db_path(
                    TopLevelDir.output,
                    object_dir=ObjectDir.scenario,
                    obj_name=scenario.attrs.name,
                )
                / "Flooding"
                / "simulations"
                / self.template_path.name
            )
