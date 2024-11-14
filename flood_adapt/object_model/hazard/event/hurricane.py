import shutil
from pathlib import Path
from typing import ClassVar, List, Optional

import pyproj
from cht_cyclones.tropical_cyclone import TropicalCyclone
from pydantic import BaseModel
from shapely.affinity import translate

from flood_adapt.object_model.hazard.event.forcing.forcing_factory import ForcingFactory
from flood_adapt.object_model.hazard.event.forcing.waterlevels import (
    WaterlevelFromModel,
)
from flood_adapt.object_model.hazard.interface.events import IEvent, IEventModel
from flood_adapt.object_model.hazard.interface.forcing import (
    ForcingSource,
    ForcingType,
)
from flood_adapt.object_model.hazard.interface.models import Mode, Template, TimeModel
from flood_adapt.object_model.interface.scenarios import IScenario
from flood_adapt.object_model.io.unitfulvalue import UnitfulLength, UnitTypesLength


class TranslationModel(BaseModel):
    """BaseModel describing the expected variables and data types for translation parameters of hurricane model."""

    eastwest_translation: UnitfulLength = UnitfulLength(
        value=0.0, units=UnitTypesLength.meters
    )
    northsouth_translation: UnitfulLength = UnitfulLength(
        value=0.0, units=UnitTypesLength.meters
    )


class HurricaneEventModel(IEventModel):
    """BaseModel describing the expected variables and data types for parameters of HistoricalHurricane that extend the parent class Event."""

    ALLOWED_FORCINGS: ClassVar[dict[ForcingType, List[ForcingSource]]] = {
        ForcingType.RAINFALL: [ForcingSource.TRACK],
        ForcingType.WIND: [ForcingSource.TRACK],
        ForcingType.WATERLEVEL: [ForcingSource.MODEL],
        ForcingType.DISCHARGE: [ForcingSource.CONSTANT, ForcingSource.CSV],
    }

    hurricane_translation: TranslationModel
    track_name: str

    @staticmethod
    def default() -> "HurricaneEventModel":
        """Set default values for HurricaneEvent."""
        return HurricaneEventModel(
            name="Hurricane Event",
            time=TimeModel(),
            template=Template.Hurricane,
            mode=Mode.single_event,
            hurricane_translation=TranslationModel(),
            track_name="",
            forcings={
                ForcingType.RAINFALL: ForcingFactory.get_default_forcing(
                    ForcingType.RAINFALL, ForcingSource.TRACK
                ),
                ForcingType.WIND: ForcingFactory.get_default_forcing(
                    ForcingType.WIND, ForcingSource.TRACK
                ),
                ForcingType.WATERLEVEL: ForcingFactory.get_default_forcing(
                    ForcingType.WATERLEVEL, ForcingSource.MODEL
                ),
                ForcingType.DISCHARGE: ForcingFactory.get_default_forcing(
                    ForcingType.DISCHARGE, ForcingSource.CONSTANT
                ),
            },
        )


class HurricaneEvent(IEvent):
    MODEL_TYPE = HurricaneEventModel

    attrs: HurricaneEventModel

    def process(self, scenario: IScenario = None):
        """Prepare the forcings of the hurricane event.

        If the forcings require it, this function will:
        - preprocess and run offshore model: prepare and run the offshore model to obtain water levels for the boundary condition of the nearshore model.

        """
        self._scenario = scenario
        self.meteo_ds = None
        sim_path = self._get_simulation_path()

        if self.database.site.attrs.sfincs.offshore_model is None:
            raise ValueError(
                f"An offshore model needs to be defined in the site.toml with sfincs.offshore_model to run an event of type '{self.__class__.__name__}'"
            )

        sim_path.mkdir(parents=True, exist_ok=True)
        self._preprocess_sfincs_offshore(sim_path)
        self._run_sfincs_offshore(sim_path)

        self.logger.info("Collecting forcing data ...")
        for forcing in self.attrs.forcings.values():
            # temporary fix to set the path of the forcing
            if isinstance(forcing, WaterlevelFromModel):
                forcing.path = sim_path

    def make_spw_file(
        self, cyc_file: Optional[Path] = None, output_dir: Optional[Path] = None
    ) -> Path:
        """
        Create a spiderweb file from a given TropicalCyclone track.

        Parameters
        ----------
        cyc_file : Path, optional
            Path to the cyc file, if None the .cyc file in the event's input directory is used
        output_dir : Path, optional
            Directory to save the spiderweb file, if None the spiderweb file is saved in the event's input directory

        Returns
        -------
        Path
            the path to the created spiderweb file
        """
        cyc_file = cyc_file or self.database.events.input_path.joinpath(
            f"{self.attrs.name}", f"{self.attrs.track_name}.cyc"
        )
        # Initialize the tropical cyclone database
        tc = TropicalCyclone()
        tc.read_track(filename=cyc_file, fmt="ddb_cyc")

        # Alter the track of the tc if necessary
        if (
            self.attrs.hurricane_translation.eastwest_translation.value != 0
            or self.attrs.hurricane_translation.northsouth_translation.value != 0
        ):
            tc = self.translate_tc_track(tc=tc)

        if self.attrs.forcings[ForcingType.RAINFALL] is not None:
            tc.include_rainfall = (
                self.attrs.forcings[ForcingType.RAINFALL]._source == ForcingSource.TRACK
            )

        # Location of spw file
        if output_dir is None:
            spw_file = cyc_file.parent / f"{self.attrs.track_name}.spw"
        else:
            spw_file = output_dir / f"{self.attrs.track_name}.spw"

        # Create spiderweb file from the track
        tc.to_spiderweb(spw_file)

        return spw_file

    def translate_tc_track(self, tc: TropicalCyclone):
        # First convert geodataframe to the local coordinate system
        crs = pyproj.CRS.from_string(self.database.site.attrs.sfincs.csname)
        tc.track = tc.track.to_crs(crs)

        # Translate the track in the local coordinate system
        tc.track["geometry"] = tc.track["geometry"].apply(
            lambda geom: translate(
                geom,
                xoff=self.attrs.hurricane_translation.eastwest_translation.convert(
                    "meters"
                ),
                yoff=self.attrs.hurricane_translation.northsouth_translation.convert(
                    "meters"
                ),
            )
        )

        # Convert the geodataframe to lat/lon
        tc.track = tc.track.to_crs(epsg=4326)

        return tc

    def _preprocess_sfincs_offshore(self, sim_path: Path):
        """Preprocess offshore model to obtain water levels for boundary condition of the nearshore model.

        This function is reused for ForcingSources: MODEL & TRACK.

        Args:
            sim_path path to the root of the offshore model
        """
        self.logger.info("Preparing offshore model to generate waterlevels...")
        from flood_adapt.integrator.sfincs_adapter import SfincsAdapter

        # Initialize
        if Path(sim_path).exists():
            shutil.rmtree(sim_path)
        Path(sim_path).mkdir(parents=True, exist_ok=True)

        template_offshore = self.database.static_path.joinpath(
            "templates", self.database.site.attrs.sfincs.offshore_model
        )
        with SfincsAdapter(model_root=template_offshore) as _offshore_model:
            # Edit offshore model
            _offshore_model.set_timing(self.attrs.time)

            # Add water levels
            physical_projection = self.database.projections.get(
                self._scenario.attrs.projection
            ).get_physical_projection()

            _offshore_model._add_bzs_from_bca(self.attrs, physical_projection.attrs)

            self.make_spw_file(output_dir=sim_path)
            _offshore_model._set_config_spw(f"{self.attrs.track_name}.spw")

            # write sfincs model in output destination
            _offshore_model.write(path_out=sim_path)

    def _run_sfincs_offshore(self, sim_path):
        self.logger.info("Running offshore model...")
        from flood_adapt.integrator.sfincs_adapter import SfincsAdapter

        with SfincsAdapter(model_root=sim_path) as _offshore_model:
            _offshore_model.execute()

    def _get_simulation_path(self) -> Path:
        if self.attrs.mode == Mode.risk:
            return (
                self.database.scenarios.output_path
                / self._scenario.attrs.name
                / "Flooding"
                / "simulations"
                / self.attrs.name
                / self.database.site.attrs.sfincs.offshore_model
            )
        elif self.attrs.mode == Mode.single_event:
            return (
                self.database.scenarios.output_path
                / self._scenario.attrs.name
                / "Flooding"
                / "simulations"
                / self.database.site.attrs.sfincs.offshore_model
            )
        else:
            raise ValueError(f"Unknown mode: {self.attrs.mode}")
