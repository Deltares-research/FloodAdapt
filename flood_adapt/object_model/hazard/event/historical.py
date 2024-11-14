import shutil
from pathlib import Path
from typing import ClassVar, List

from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.object_model.hazard.event.forcing.forcing_factory import ForcingFactory
from flood_adapt.object_model.hazard.event.forcing.waterlevels import (
    WaterlevelFromModel,
)
from flood_adapt.object_model.hazard.event.meteo import MeteoHandler
from flood_adapt.object_model.hazard.interface.events import (
    IEvent,
    IEventModel,
    Mode,
)
from flood_adapt.object_model.hazard.interface.forcing import (
    ForcingSource,
    ForcingType,
    IForcing,
)
from flood_adapt.object_model.hazard.interface.models import Template, TimeModel
from flood_adapt.object_model.interface.scenarios import IScenario


class HistoricalEventModel(IEventModel):
    """BaseModel describing the expected variables and data types for parameters of HistoricalNearshore that extend the parent class Event."""

    ALLOWED_FORCINGS: ClassVar[dict[ForcingType, List[ForcingSource]]] = {
        ForcingType.RAINFALL: [
            ForcingSource.CONSTANT,
            ForcingSource.CSV,
            ForcingSource.METEO,
        ],
        ForcingType.WIND: [
            ForcingSource.CONSTANT,
            ForcingSource.CSV,
            ForcingSource.METEO,
        ],
        ForcingType.WATERLEVEL: [
            ForcingSource.CSV,
            ForcingSource.MODEL,
            ForcingSource.GAUGED,
        ],
        ForcingType.DISCHARGE: [ForcingSource.CONSTANT, ForcingSource.CSV],
    }

    @staticmethod
    def default() -> "HistoricalEventModel":
        """Set default values for Synthetic event."""
        return HistoricalEventModel(
            name="Historical Event",
            time=TimeModel(),
            template=Template.Historical,
            mode=Mode.single_event,
            forcings={
                ForcingType.RAINFALL: ForcingFactory.get_default_forcing(
                    ForcingType.RAINFALL, ForcingSource.METEO
                ),
                ForcingType.WIND: ForcingFactory.get_default_forcing(
                    ForcingType.WIND, ForcingSource.METEO
                ),
                ForcingType.WATERLEVEL: ForcingFactory.get_default_forcing(
                    ForcingType.WATERLEVEL, ForcingSource.MODEL
                ),
                ForcingType.DISCHARGE: ForcingFactory.get_default_forcing(
                    ForcingType.DISCHARGE, ForcingSource.CONSTANT
                ),
            },
        )


class HistoricalEvent(IEvent):
    MODEL_TYPE = HistoricalEventModel

    attrs: HistoricalEventModel

    def __init__(self):
        self._logger = FloodAdaptLogging.getLogger(__name__)

    @property
    def site(self):
        return self.database.site

    def process(self, scenario: IScenario = None):
        """Prepare the forcings of the historical event.

        If the forcings require it, this function will:
        - preprocess and run offshore model: prepare and run the offshore model to obtain water levels for the boundary condition of the nearshore model.

        """
        self._scenario = scenario
        self.meteo_ds = None
        sim_path = self._get_simulation_path()
        if self._require_offshore_run():
            if self.site.attrs.sfincs.offshore_model is None:
                raise ValueError(
                    f"An offshore model needs to be defined in the site.toml with sfincs.offshore_model to run an event of type '{self.__class__.__name__}'"
                )

            sim_path.mkdir(parents=True, exist_ok=True)
            self._preprocess_sfincs_offshore(sim_path)
            self._run_sfincs_offshore(sim_path)

        self._logger.info("Collecting forcing data ...")
        for forcing in self.attrs.forcings.values():
            if forcing is None:
                continue

            # FIXME added temp implementations here to make forcing.get_data() succeed,
            # move this to the forcings themselves?
            if isinstance(forcing, WaterlevelFromModel):
                forcing.path = sim_path

    def _require_offshore_run(self) -> bool:
        for forcing in self.attrs.forcings.values():
            if forcing is not None:
                if isinstance(forcing, IForcing):
                    if forcing._source == ForcingSource.MODEL:
                        return True
                elif isinstance(forcing, dict):
                    return any(
                        forcing_instance._source == ForcingSource.MODEL
                        for forcing_instance in forcing.values()
                    )
                else:
                    raise ValueError(
                        f"Unknown forcing type: {forcing.__class__.__name__}"
                    )
        return False

    def _preprocess_sfincs_offshore(self, sim_path: Path):
        """Preprocess offshore model to obtain water levels for boundary condition of the nearshore model.

        This function is reused for ForcingSources: MODEL & TRACK.

        Args:
            sim_path path to the root of the offshore model
        """
        self._logger.info("Preparing offshore model to generate waterlevels...")
        from flood_adapt.integrator.sfincs_adapter import SfincsAdapter

        # Initialize
        if Path(sim_path).exists():
            shutil.rmtree(sim_path)
        Path(sim_path).mkdir(parents=True, exist_ok=True)

        template_offshore = self.database.static_path.joinpath(
            "templates", self.site.attrs.sfincs.offshore_model
        )
        with SfincsAdapter(model_root=template_offshore) as _offshore_model:
            # Edit offshore model
            _offshore_model.set_timing(self.attrs.time)

            # Add water levels
            physical_projection = self.database.projections.get(
                self._scenario.attrs.projection
            ).get_physical_projection()
            _offshore_model._add_bzs_from_bca(self.attrs, physical_projection.attrs)

            # Add wind and if applicable pressure forcing from meteo data
            wind_forcing = self.attrs.forcings[ForcingType.WIND]
            if wind_forcing is not None:
                # Add wind forcing
                _offshore_model._add_forcing_wind(wind_forcing)

                # Add pressure forcing for the offshore model (this doesnt happen normally in _add_forcing_wind() for overland models)
                if wind_forcing._source == ForcingSource.METEO:
                    ds = MeteoHandler().read(self.attrs.time)
                    if (
                        ds["lon"].min() > 180
                    ):  # TODO move this ifstatement to meteohandler.read() ?
                        ds["lon"] = ds["lon"] - 360
                    _offshore_model._add_pressure_forcing_from_grid(ds=ds)

            # write sfincs model in output destination
            _offshore_model.write(path_out=sim_path)

    def _run_sfincs_offshore(self, sim_path):
        self._logger.info("Running offshore model...")
        from flood_adapt.integrator.sfincs_adapter import SfincsAdapter

        with SfincsAdapter(model_root=sim_path) as _offshore_model:
            success = _offshore_model.execute(strict=False)

            if not success:
                raise RuntimeError(
                    f"Running offshore SFINCS model failed. See {sim_path} for more information."
                )

    def _get_simulation_path(self) -> Path:
        if self.attrs.mode == Mode.risk:
            return (
                self.database.scenarios.output_path
                / self._scenario.attrs.name
                / "Flooding"
                / "simulations"
                / self.attrs.name
                / self.site.attrs.sfincs.offshore_model
            )
        elif self.attrs.mode == Mode.single_event:
            return (
                self.database.scenarios.output_path
                / self._scenario.attrs.name
                / "Flooding"
                / "simulations"
                / self.site.attrs.sfincs.offshore_model
            )
        else:
            raise ValueError(f"Unknown mode: {self.attrs.mode}")
