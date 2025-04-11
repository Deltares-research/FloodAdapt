import shutil
from pathlib import Path

import pandas as pd

from flood_adapt.adapter.interface.offshore import IOffshoreSfincsHandler
from flood_adapt.adapter.sfincs_adapter import SfincsAdapter
from flood_adapt.misc.database_user import DatabaseUser
from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.misc.path_builder import (
    ObjectDir,
    TopLevelDir,
    db_path,
)
from flood_adapt.objects.events.event_set import EventSet
from flood_adapt.objects.events.events import Event, Mode
from flood_adapt.objects.events.historical import HistoricalEvent
from flood_adapt.objects.forcing.forcing import (
    ForcingSource,
    IWind,
)
from flood_adapt.objects.forcing.meteo_handler import MeteoHandler
from flood_adapt.objects.forcing.wind import WindMeteo
from flood_adapt.objects.scenarios.scenarios import Scenario


class OffshoreSfincsHandler(IOffshoreSfincsHandler, DatabaseUser):
    logger = FloodAdaptLogging.getLogger("OffshoreSfincsAdapter")
    template_path: Path

    def __init__(self, scenario: Scenario, event: Event) -> None:
        self.template_path = (
            self.database.static.get_offshore_sfincs_model().get_model_root()
        )
        self.scenario = scenario
        if isinstance(event, EventSet):
            raise ValueError(
                "OffshoreSfincsHandler does not support EventSets. Provide the sub events directly "
            )
        self.event = event

    def get_resulting_waterlevels(self) -> pd.DataFrame:
        """Get the water levels from the offshore model.

        Note that the returned water levels are relative to the reference datum of the offshore model.
        To convert to a different datum, add the offshore reference datum height and subtract the desired reference datum height.

        Returns
        -------
        pd.DataFrame
            A DataFrame with the water levels for each boundary condition point. Relative to the reference datum of the offshore model.

        """
        path = self._get_simulation_path()
        if not self.requires_offshore_run(self.event):
            raise ValueError("Offshore model is not required for this event")

        self.run_offshore()

        with SfincsAdapter(model_root=path) as offshore_model:
            waterlevels = offshore_model.get_wl_df_from_offshore_his_results()

        return waterlevels

    @staticmethod
    def requires_offshore_run(event: Event) -> bool:
        return any(
            forcing.source in [ForcingSource.MODEL, ForcingSource.TRACK]
            for forcing in event.get_forcings()
        )

    def run_offshore(self):
        """Prepare the forcings of the historical event.

        If the forcings require it, this function will:
        - preprocess and run offshore model: prepare and run the offshore model to obtain water levels for the boundary condition of the nearshore model.

        """
        sim_path = self._get_simulation_path()

        sim_path.mkdir(parents=True, exist_ok=True)
        self._preprocess_sfincs_offshore()
        self._execute_sfincs_offshore(sim_path)

    def _preprocess_sfincs_offshore(self):
        """Preprocess offshore model to obtain water levels for boundary condition of the nearshore model.

        This function is reused for ForcingSources: MODEL & TRACK.

        Args:
            sim_path path to the root of the offshore model
        """
        self.logger.info(
            f"Preparing offshore model to generate waterlevels for `{self.scenario.name}`"
        )
        sim_path = self._get_simulation_path()
        # SfincsAdapter.write() doesnt write the bca file apparently so we need to copy the template
        if sim_path.exists():
            shutil.rmtree(sim_path)
        shutil.copytree(self.template_path, sim_path)

        with SfincsAdapter(model_root=sim_path) as _offshore_model:
            if _offshore_model.sfincs_completed(sim_path):
                _offshore_model.logger.info(
                    f"Skip preprocessing offshore model as it has already been run for `{self.scenario.name}`."
                )
                return
            # Load objects, set root & write template model
            _offshore_model._load_scenario_objects(self.scenario, self.event)
            _offshore_model.write(path_out=sim_path)
            _offshore_model.set_timing(self.event.time)

            # Add water levels
            _offshore_model._add_bzs_from_bca(
                _offshore_model._event, _offshore_model._projection.physical_projection
            )

            # Add spw if applicable
            track_forcings = [
                f
                for f in _offshore_model._event.get_forcings()
                if f.source == ForcingSource.TRACK
            ]
            if track_forcings:
                for forcing in track_forcings:
                    _offshore_model.add_forcing(forcing)

            # Add wind and if applicable pressure forcing from meteo data
            elif isinstance(_offshore_model._event, HistoricalEvent):
                wind_forcings = [
                    f
                    for f in _offshore_model._event.get_forcings()
                    if isinstance(f, IWind)
                ]

                if wind_forcings:
                    if len(wind_forcings) > 1:
                        raise ValueError("Only one wind forcing is allowed")
                    wind_forcing = wind_forcings[0]

                    # Add wind forcing
                    if wind_forcing not in track_forcings:
                        _offshore_model.add_forcing(wind_forcing)

                    # Add pressure forcing for the offshore model (this doesnt happen normally in _add_forcing_wind() for overland models)
                    if isinstance(wind_forcing, WindMeteo):
                        ds = MeteoHandler().read(_offshore_model._event.time)
                        _offshore_model._add_pressure_forcing_from_grid(ds=ds)

            # write sfincs model in output destination
            _offshore_model.write(path_out=sim_path)

    def _execute_sfincs_offshore(self, sim_path: Path):
        self.logger.info(f"Running offshore model in {sim_path}")
        sim_path = self._get_simulation_path()
        with SfincsAdapter(model_root=sim_path) as _offshore_model:
            if _offshore_model.sfincs_completed(sim_path):
                self.logger.info(
                    "Skip running offshore model as it has already been run."
                )
                return
            try:
                _offshore_model.execute(path=sim_path)
            except RuntimeError as e:
                raise RuntimeError(
                    f"Failed to run offshore model for {self.scenario.name}"
                ) from e

    def _get_simulation_path(self) -> Path:
        main_event = self.database.events.get(self.scenario.event)
        if main_event.mode == Mode.risk:
            return (
                db_path(
                    TopLevelDir.output,
                    object_dir=ObjectDir.scenario,
                    obj_name=self.scenario.name,
                )
                / "Flooding"
                / "simulations"
                / self.event.name
                / self.template_path.name
            )
        else:
            return (
                db_path(
                    TopLevelDir.output,
                    object_dir=ObjectDir.scenario,
                    obj_name=self.scenario.name,
                )
                / "Flooding"
                / "simulations"
                / self.template_path.name
            )
