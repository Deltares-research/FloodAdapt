import shutil
from pathlib import Path

import pandas as pd

from flood_adapt.adapter.interface.offshore import IOffshoreSfincsHandler
from flood_adapt.adapter.sfincs_adapter import SfincsAdapter
from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.object_model.hazard.event.event_set import EventSet
from flood_adapt.object_model.hazard.event.forcing.wind import WindMeteo
from flood_adapt.object_model.hazard.event.historical import HistoricalEvent
from flood_adapt.object_model.hazard.event.hurricane import HurricaneEvent
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
    logger = FloodAdaptLogging.getLogger(__name__)
    template_path: Path

    def __init__(self) -> None:
        if self.database.site.attrs.sfincs.offshore_model is None:
            raise ValueError("No offshore model specified in site.toml")

        self.template_path = (
            self.database.static_path
            / "templates"
            / self.database.site.attrs.sfincs.offshore_model
        )

    def get_resulting_waterlevels(self, scenario: IScenario) -> pd.DataFrame:
        path = self._get_simulation_path(scenario)

        if not self.requires_offshore_run(scenario):
            raise ValueError("Offshore model is not required for this scenario")

        self.run_offshore(scenario)

        with SfincsAdapter(model_root=str(path)) as _offshore_model:
            return _offshore_model.get_wl_df_from_offshore_his_results()

    @staticmethod
    def requires_offshore_run(scenario: IScenario) -> bool:
        return any(
            forcing._source in [ForcingSource.MODEL, ForcingSource.TRACK]
            for forcing in scenario.get_event().get_forcings()
        )

    def run_offshore(self, scenario: IScenario):
        """Prepare the forcings of the historical event.

        If the forcings require it, this function will:
        - preprocess and run offshore model: prepare and run the offshore model to obtain water levels for the boundary condition of the nearshore model.

        """
        sim_path = self._get_simulation_path(scenario)

        sim_path.mkdir(parents=True, exist_ok=True)
        self._preprocess_sfincs_offshore(scenario)
        self._execute_sfincs_offshore(sim_path)

    def _preprocess_sfincs_offshore(self, scenario: IScenario):
        """Preprocess offshore model to obtain water levels for boundary condition of the nearshore model.

        This function is reused for ForcingSources: MODEL & TRACK.

        Args:
            sim_path path to the root of the offshore model
        """
        self.logger.info(
            f"Preparing offshore model to generate waterlevels for {scenario.attrs.name}..."
        )

        sim_path = self._get_simulation_path(scenario)

        with SfincsAdapter(model_root=str(self.template_path)) as _offshore_model:
            if _offshore_model.sfincs_completed(sim_path):
                self.logger.info(
                    f"Skip preprocessing offshore model as it has already been run for {scenario.attrs.name}."
                )
                return

            # Copy template model to the output destination to be able to edit it
            if Path(sim_path).exists():
                shutil.rmtree(sim_path)
            shutil.copytree(self.template_path, sim_path)

            # Set root & scenario
            _offshore_model._model.set_root(str(sim_path))
            _offshore_model._scenario = scenario

            event = scenario.get_event()
            physical_projection = scenario.get_projection().get_physical_projection()

            # Create any event specific files
            event.preprocess(sim_path)

            # Edit offshore model
            _offshore_model.set_timing(event.attrs.time)

            # Add water levels
            _offshore_model._add_bzs_from_bca(event, physical_projection.attrs)

            # Add spw if applicable
            if isinstance(event, HurricaneEvent):
                _offshore_model._sim_path = sim_path
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
                        ds = wind_forcing.get_data(
                            t0=event.attrs.time.start_time, t1=event.attrs.time.end_time
                        )
                        if ds["lon"].min() > 180:
                            # TODO move this if statement to meteohandler.read() ?
                            ds["lon"] = ds["lon"] - 360
                        _offshore_model._add_pressure_forcing_from_grid(ds=ds)

            # write sfincs model in output destination
            _offshore_model.write(path_out=sim_path)

    def _execute_sfincs_offshore(self, sim_path: Path):
        self.logger.info("Running offshore model...")

        with SfincsAdapter(model_root=str(sim_path)) as _offshore_model:
            if _offshore_model.sfincs_completed(sim_path):
                self.logger.info(
                    "Skip running offshore model as it has already been run."
                )
                return

            success = _offshore_model.execute(strict=False)

            if not success:
                raise RuntimeError(
                    f"Running offshore SFINCS model failed. See {sim_path} for more information."
                )

    def _get_simulation_path(self, scenario: IScenario) -> Path:
        event = scenario.get_event()
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
