import os
from unittest import mock

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest

from flood_adapt.api.static import read_database
from flood_adapt.integrator.sfincs_adapter import SfincsAdapter
from flood_adapt.object_model.hazard.event.forcing.discharge import (
    DischargeConstant,
    DischargeSynthetic,
)
from flood_adapt.object_model.hazard.event.forcing.rainfall import (
    RainfallConstant,
    RainfallFromMeteo,
    RainfallSynthetic,
)
from flood_adapt.object_model.hazard.event.forcing.waterlevels import (
    WaterlevelFromCSV,
    WaterlevelFromGauged,
    WaterlevelFromModel,
    WaterlevelSynthetic,
)
from flood_adapt.object_model.hazard.event.forcing.wind import (
    WindConstant,
    WindFromMeteo,
    WindFromTrack,
    WindSynthetic,
)
from flood_adapt.object_model.hazard.interface.forcing import (
    IDischarge,
    IForcing,
    IRainfall,
    IWaterlevel,
    IWind,
)
from flood_adapt.object_model.hazard.interface.models import ForcingType
from flood_adapt.object_model.hazard.measure.floodwall import FloodWall
from flood_adapt.object_model.hazard.measure.green_infrastructure import (
    GreenInfrastructure,
)
from flood_adapt.object_model.hazard.measure.pump import Pump
from flood_adapt.object_model.hazard.physical_projection import PhysicalProjection
from flood_adapt.object_model.interface.database import IDatabase
from flood_adapt.object_model.interface.measures import HazardType, IMeasure
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulDirection,
    UnitfulIntensity,
    UnitfulLength,
    UnitfulVelocity,
    UnitTypesDischarge,
    UnitTypesIntensity,
)


@pytest.fixture()
def default_sfincs_adapter(test_db) -> SfincsAdapter:
    overland_path = test_db.static_path / "templates" / "overland"
    adapter = SfincsAdapter(model_root=overland_path)
    adapter._logger = mock.Mock()
    adapter._logger.handlers = []
    return adapter


class TestAddForcing:
    """
    Class to test the add_forcing method of the SfincsAdapter class.

    Since the add_forcing method is a dispatcher method, we will test the different cases of forcing types, while mocking the specific methods that handle each forcing type.
    To validate that hydromt_sfincs accepts the data that is returned by the forcing, the mocked methods should be tested separately.
    """

    class TestDispatch:
        @pytest.fixture()
        def sfincs_adapter(self, default_sfincs_adapter) -> SfincsAdapter:
            adapter = default_sfincs_adapter

            adapter._add_forcing_wind = mock.Mock()
            adapter._add_forcing_rain = mock.Mock()
            adapter._add_forcing_discharge = mock.Mock()
            adapter._add_forcing_waterlevels = mock.Mock()
            return adapter

        def test_add_forcing_wind(self, sfincs_adapter):
            forcing = mock.Mock(spec=IForcing)
            forcing._type = ForcingType.WIND
            sfincs_adapter.add_forcing(forcing)
            sfincs_adapter._add_forcing_wind.assert_called_once_with(forcing)

        def test_add_forcing_rain(self, sfincs_adapter):
            forcing = mock.Mock(spec=IForcing)
            forcing._type = ForcingType.RAINFALL
            sfincs_adapter.add_forcing(forcing)
            sfincs_adapter._add_forcing_rain.assert_called_once_with(forcing)

        def test_add_forcing_discharge(self, sfincs_adapter):
            forcing = mock.Mock(spec=IForcing)
            forcing._type = ForcingType.DISCHARGE
            sfincs_adapter.add_forcing(forcing)
            sfincs_adapter._add_forcing_discharge.assert_called_once_with(forcing)

        def test_add_forcing_waterlevels(self, sfincs_adapter):
            forcing = mock.Mock(spec=IForcing)
            forcing._type = ForcingType.WATERLEVEL
            sfincs_adapter.add_forcing(forcing)
            sfincs_adapter._add_forcing_waterlevels.assert_called_once_with(forcing)

        def test_add_forcing_unsupported(self, sfincs_adapter):
            forcing = mock.Mock(spec=IForcing)
            forcing._type = "unsupported_type"
            sfincs_adapter.add_forcing(forcing)
            sfincs_adapter._logger.warning.assert_called_once_with(
                f"Skipping unsupported forcing type {forcing.__class__.__name__}"
            )

    class TestWind:
        @pytest.fixture()
        def sfincs_adapter(self, default_sfincs_adapter) -> SfincsAdapter:
            adapter = default_sfincs_adapter
            adapter._model = mock.Mock()
            adapter._set_wind_forcing = mock.Mock()
            adapter._set_config_spw = mock.Mock()
            return adapter

        def test_add_forcing_wind_constant(self, sfincs_adapter):
            forcing = WindConstant(
                speed=UnitfulVelocity(10, "m/s"),
                direction=UnitfulDirection(20, "deg N"),
            )
            sfincs_adapter._add_forcing_wind(forcing)

            sfincs_adapter._model.setup_wind_forcing.assert_called_once_with(
                timeseries=None,
                const_mag=forcing.speed,
                const_dir=forcing.direction,
            )

        def test_add_forcing_wind_synthetic(self, sfincs_adapter):
            forcing = mock.Mock(spec=WindSynthetic)
            forcing.path = "path/to/timeseries.csv"

            sfincs_adapter._add_forcing_wind(forcing)

            sfincs_adapter._model.setup_wind_forcing.assert_called_once_with(
                timeseries=forcing.path,
                const_mag=None,
                const_dir=None,
            )

        def test_add_forcing_wind_from_meteo(self, sfincs_adapter):
            forcing = mock.Mock(spec=WindFromMeteo)
            forcing.path = "path/to/meteo/grid"

            sfincs_adapter._add_forcing_wind(forcing)
            sfincs_adapter._set_wind_forcing.assert_called_once_with(forcing.path)

        def test_add_forcing_wind_from_track(self, sfincs_adapter):
            forcing = mock.Mock(spec=WindFromTrack)
            forcing.path = "path/to/track"

            sfincs_adapter._add_forcing_wind(forcing)

            sfincs_adapter._set_config_spw.assert_called_once_with(forcing.path)

        def test_add_forcing_wind_unsupported(self, sfincs_adapter):
            class UnsupportedWind(IWind):
                pass

            forcing = UnsupportedWind()

            sfincs_adapter._add_forcing_wind(forcing)

            sfincs_adapter._logger.warning.assert_called_once_with(
                f"Unsupported wind forcing type: {forcing.__class__.__name__}"
            )

    class TestRainfall:
        @pytest.fixture()
        def sfincs_adapter(self, default_sfincs_adapter) -> SfincsAdapter:
            adapter = default_sfincs_adapter
            adapter._model = mock.Mock()
            return adapter

        def test_add_forcing_rain_constant(self, sfincs_adapter):
            forcing = RainfallConstant(
                intensity=UnitfulIntensity(value=10, units=UnitTypesIntensity.mm_hr)
            )
            sfincs_adapter._add_forcing_rain(forcing)

            sfincs_adapter._model.setup_precip_forcing.assert_called_once_with(
                timeseries=None,
                magnitude=forcing.intensity,
            )

        def test_add_forcing_rain_synthetic(self, sfincs_adapter):
            forcing = mock.Mock(spec=RainfallSynthetic)
            forcing.get_data.return_value = "path/to/timeseries.csv"

            sfincs_adapter._add_forcing_rain(forcing)

            sfincs_adapter._model.add_precip_forcing.assert_called_once_with(
                timeseries=forcing.get_data()
            )

        def test_add_forcing_rain_from_meteo(self, sfincs_adapter):
            forcing = mock.Mock(spec=RainfallFromMeteo)

            forcing.get_data.return_value = "path/to/meteo/grid"

            sfincs_adapter._add_forcing_rain(forcing)

            sfincs_adapter._model.setup_precip_forcing_from_grid.assert_called_once_with(
                precip=forcing.get_data()
            )

        def test_add_forcing_rain_unsupported(self, sfincs_adapter):
            class UnsupportedRain(IRainfall):
                pass

            forcing = UnsupportedRain()

            sfincs_adapter._add_forcing_rain(forcing)

            sfincs_adapter._logger.warning.assert_called_once_with(
                f"Unsupported rainfall forcing type: {forcing.__class__.__name__}"
            )

    class TestDischarge:
        @pytest.fixture()
        def sfincs_adapter_0_rivers(self, test_db) -> SfincsAdapter:
            os.remove(test_db.static_path / "site" / "site.toml")
            os.rename(
                test_db.static_path / "site" / "site_without_river.toml",
                test_db.static_path / "site" / "site.toml",
            )

            test_db.reset()
            test_db = read_database(test_db.static_path.parents[1], "charleston_test")

            overland_path = test_db.static_path / "templates" / "overland_0_rivers"

            adapter = SfincsAdapter(model_root=overland_path)
            adapter._logger = mock.Mock()
            adapter._logger.handlers = []

            return adapter

        @pytest.fixture()
        def sfincs_adapter_1_rivers(self, test_db) -> SfincsAdapter:
            overland_path = test_db.static_path / "templates" / "overland"

            adapter = SfincsAdapter(model_root=overland_path)
            adapter._logger = mock.Mock()
            adapter._logger.handlers = []
            return adapter

        def test_add_forcing_discharge_synthetic(self, sfincs_adapter_1_rivers):
            # Arrange
            sfincs_adapter = sfincs_adapter_1_rivers
            sfincs_adapter._model.setup_discharge_forcing = mock.Mock()

            forcing = mock.Mock(spec=DischargeSynthetic)
            time = pd.date_range(start="2023-01-01", periods=3, freq="D")
            forcing.get_data.return_value = pd.DataFrame(
                index=time,
                data={
                    "discharge1": [10, 20, 30],
                },
            )
            # Act
            sfincs_adapter._add_forcing_discharge(forcing)

            # Assert
            sfincs_adapter._model.setup_discharge_forcing.assert_called_once
            call_args = sfincs_adapter._model.setup_discharge_forcing.call_args

            assert call_args[1]["timeseries"].equals(forcing.get_data())
            assert all(call_args[1]["locations"] == mock.ANY)
            assert not call_args[1]["merge"]

        def test_add_forcing_discharge_unsupported(self, sfincs_adapter_1_rivers):
            # Arrange
            sfincs_adapter = sfincs_adapter_1_rivers

            class UnsupportedDischarge(IDischarge):
                pass

            sfincs_adapter._logger.warning = mock.Mock()
            forcing = UnsupportedDischarge()

            # Act
            sfincs_adapter._add_forcing_discharge(forcing)

            # Assert
            sfincs_adapter._logger.warning.assert_called_once_with(
                f"Unsupported discharge forcing type: {forcing.__class__.__name__}"
            )

        def test_set_discharge_forcing_no_rivers(self, sfincs_adapter_0_rivers):
            # Arrange
            sfincs_adapter = sfincs_adapter_0_rivers
            forcing = mock.Mock(spec=DischargeConstant)
            time = pd.date_range(start="2023-01-01", periods=3, freq="D")
            ret_val = pd.DataFrame(
                index=time,
                data={},
            )
            forcing.get_data.return_value = ret_val
            sfincs_adapter._model.setup_discharge_forcing = mock.Mock()

            # Act
            sfincs_adapter._set_discharge_forcing(ret_val)

            # Assert
            assert sfincs_adapter._model.setup_discharge_forcing.call_count == 0

        def test_set_discharge_forcing_matching_rivers(self, sfincs_adapter_1_rivers):
            # Arrange
            sfincs_adapter = sfincs_adapter_1_rivers
            sfincs_adapter._model.setup_discharge_forcing = mock.Mock()

            forcing = mock.Mock(spec=DischargeSynthetic)
            time = pd.date_range(start="2023-01-01", periods=3, freq="D")
            ret_val = pd.DataFrame(
                index=time,
                data={
                    "discharge1": [10, 20, 30],
                },
            )
            forcing.get_data.return_value = ret_val

            # Act
            sfincs_adapter._add_forcing_discharge(forcing)

            # Assert
            sfincs_adapter._model.setup_discharge_forcing.assert_called_once
            call_args = sfincs_adapter._model.setup_discharge_forcing.call_args

            assert call_args[1]["timeseries"].equals(forcing.get_data())
            assert all(call_args[1]["locations"] == mock.ANY)
            assert not call_args[1]["merge"]

        def test_set_discharge_forcing_mismatched_coordinates(self, test_db):
            forcing = mock.Mock(spec=DischargeSynthetic)
            time = pd.date_range(start="2023-01-01", periods=3, freq="D")
            overland_path = test_db.static_path / "templates" / "overland"

            with open(overland_path / "sfincs.src", "w") as f:
                f.write("10\t20\n")

            sfincs_adapter = SfincsAdapter(model_root=overland_path)
            sfincs_adapter._logger = mock.Mock()
            sfincs_adapter._logger.handlers = []

            ret_val = pd.DataFrame(
                index=time,
                data={
                    "discharge1": [10, 20, 30],
                },
            )
            forcing.get_data.return_value = ret_val

            expected_message = (
                r"Incompatible river coordinates for river: .+\.\n"
                r"site.toml: \(.+\)\n"
                r"SFINCS template model \(.+\)."
            )

            with pytest.raises(ValueError, match=expected_message):
                sfincs_adapter._set_discharge_forcing(ret_val)

        def test_set_discharge_forcing_mismatched_river_count(
            self, sfincs_adapter_1_rivers
        ):
            sfincs_adapter = sfincs_adapter_1_rivers
            list_df = pd.DataFrame(
                index=pd.date_range(start="2023-01-01", periods=3, freq="D"),
                data={
                    "discharge1": [10, 20, 30],
                    "discharge2": [15, 25, 35],
                    "discharge3": [15, 25, 35],
                    "discharge4": [15, 25, 35],
                },
            )

            with pytest.raises(
                ValueError,
                match="Number of rivers in site.toml and SFINCS template model not compatible",
            ):
                sfincs_adapter._set_discharge_forcing(list_df)

    class TestWaterLevel:
        @pytest.fixture()
        def sfincs_adapter(self, default_sfincs_adapter) -> SfincsAdapter:
            return default_sfincs_adapter

        @pytest.mark.parametrize(
            "forcing_cls",
            [
                WaterlevelSynthetic,
                WaterlevelFromCSV,
                WaterlevelFromGauged,
            ],
        )
        def test_add_forcing_waterlevels_simple(self, sfincs_adapter, forcing_cls):
            sfincs_adapter._set_waterlevel_forcing = mock.Mock()

            forcing = mock.Mock(spec=forcing_cls)
            forcing.get_data.return_value = pd.DataFrame(
                data={"waterlevel": [1, 2, 3]},
                index=pd.date_range("2023-01-01", periods=3, freq="D"),
            )
            sfincs_adapter._add_forcing_waterlevels(forcing)

            sfincs_adapter._set_waterlevel_forcing.assert_called_once_with(
                forcing.get_data()
            )

        def test_add_forcing_waterlevels_model(self, sfincs_adapter):
            sfincs_adapter._set_waterlevel_forcing = mock.Mock()
            sfincs_adapter._turn_off_bnd_press_correction = mock.Mock()

            forcing = mock.Mock(spec=WaterlevelFromModel)
            forcing.get_data.return_value = pd.DataFrame(
                data={"waterlevel": [1, 2, 3]},
                index=pd.date_range("2023-01-01", periods=3, freq="D"),
            )
            sfincs_adapter._add_forcing_waterlevels(forcing)

            sfincs_adapter._set_waterlevel_forcing.assert_called_once_with(
                forcing.get_data()
            )
            sfincs_adapter._turn_off_bnd_press_correction.assert_called_once()

        def test_add_forcing_waterlevels_unsupported(self, sfincs_adapter):
            sfincs_adapter._logger.warning = mock.Mock()

            class UnsupportedWaterLevel(IWaterlevel):
                pass

            forcing = UnsupportedWaterLevel()
            sfincs_adapter._add_forcing_waterlevels(forcing)

            sfincs_adapter._logger.warning.assert_called_once_with(
                f"Unsupported waterlevel forcing type: {forcing.__class__.__name__}"
            )

        def test_set_waterlevel_forcing(self, sfincs_adapter):
            sfincs_adapter._model.set_forcing_1d = mock.Mock()
            forcing = mock.Mock(spec=WaterlevelSynthetic)
            forcing.get_data.return_value = pd.DataFrame(
                data={"waterlevel": [1, 2, 3]},
                index=pd.date_range("2023-01-01", periods=3, freq="D"),
            )

            sfincs_adapter._set_waterlevel_forcing(forcing.get_data())

            sfincs_adapter._model.set_forcing_1d.assert_called_once_with(
                name="bzs", df_ts=forcing.get_data(), gdf_locs=mock.ANY, merge=False
            )


class TestAddMeasure:
    """Class to test the add_measure method of the SfincsAdapter class."""

    class TestDispatch:
        @pytest.fixture()
        def sfincs_adapter(self, default_sfincs_adapter) -> SfincsAdapter:
            adapter = default_sfincs_adapter

            adapter._add_measure_floodwall = mock.Mock()
            adapter._add_measure_greeninfra = mock.Mock()
            adapter._add_measure_pump = mock.Mock()
            adapter._logger.warning = mock.Mock()

            return adapter

        def test_add_measure_pump(self, sfincs_adapter):
            measure = mock.Mock(spec=Pump)
            measure.attrs = mock.Mock()
            measure.attrs.type = HazardType.pump
            sfincs_adapter.add_measure(measure)
            sfincs_adapter._add_measure_pump.assert_called_once_with(measure)

        def test_add_measure_greeninfra(self, sfincs_adapter):
            measure = mock.Mock(spec=GreenInfrastructure)
            measure.attrs = mock.Mock()
            measure.attrs.type = HazardType.greening
            sfincs_adapter.add_measure(measure)
            sfincs_adapter._add_measure_greeninfra.assert_called_once_with(measure)

        def test_add_measure_floodwall(self, sfincs_adapter):
            measure = mock.Mock(spec=FloodWall)
            measure.attrs = mock.Mock()
            measure.attrs.type = HazardType.floodwall
            sfincs_adapter.add_measure(measure)
            sfincs_adapter._add_measure_floodwall.assert_called_once_with(measure)

        def test_add_measure_unsupported(self, sfincs_adapter):
            class UnsupportedMeasure(IMeasure):
                pass

            measure = mock.Mock(spec=UnsupportedMeasure)
            measure.attrs = mock.Mock()
            measure.attrs.type = "UnsupportedMeasure"
            sfincs_adapter.add_measure(measure)
            sfincs_adapter._logger.warning.assert_called_once_with(
                f"Skipping unsupported measure type {measure.__class__.__name__}"
            )

    class TestFloodwall:
        @pytest.fixture()
        def sfincs_adapter(self, test_db) -> SfincsAdapter:
            overland_path = test_db.static_path / "templates" / "overland"
            adapter = SfincsAdapter(model_root=overland_path)
            adapter._logger = mock.Mock()
            adapter._logger.handlers = []

            return adapter, test_db

        def test_add_measure_floodwall(self, sfincs_adapter):
            sfincs_adapter, test_db = sfincs_adapter
            sfincs_adapter._model.setup_structures = mock.Mock()
            floodwall = test_db.measures.get("seawall")

            sfincs_adapter._add_measure_floodwall(floodwall)
            sfincs_adapter._model.setup_structures.assert_called_once_with(
                structures=mock.ANY,
                stype="weir",
                merge=True,
            )

    class TestPump:
        @pytest.fixture()
        def sfincs_adapter(self, test_db) -> SfincsAdapter:
            overland_path = test_db.static_path / "templates" / "overland"
            adapter = SfincsAdapter(model_root=overland_path)
            adapter._logger = mock.Mock()
            adapter._logger.handlers = []

            return adapter, test_db

        def test_add_measure_pump(self, sfincs_adapter):
            sfincs_adapter, test_db = sfincs_adapter
            sfincs_adapter._model.setup_drainage_structures = mock.Mock()
            pump = test_db.measures.get("pump")

            sfincs_adapter._add_measure_pump(pump)

            sfincs_adapter._model.setup_drainage_structures.assert_called_once_with(
                structures=mock.ANY,
                stype="pump",
                discharge=pump.attrs.discharge.convert(UnitTypesDischarge("m3/s")),
                merge=True,
            )

    class TestGreenInfrastructure:
        @pytest.fixture()
        def sfincs_adapter(self, test_db) -> SfincsAdapter:
            overland_path = test_db.static_path / "templates" / "overland"
            adapter = SfincsAdapter(model_root=overland_path)
            adapter._logger = mock.Mock()
            adapter._logger.handlers = []

            return adapter, test_db

        def test_add_measure_greeninfra(self, sfincs_adapter):
            sfincs_adapter, test_db = sfincs_adapter
            sfincs_adapter._model.setup_storage_volume = mock.Mock()
            green_infra = test_db.measures.get("green_infra")

            sfincs_adapter._add_measure_greeninfra(green_infra)
            sfincs_adapter._model.setup_storage_volume.assert_called_once_with(
                storage_locs=mock.ANY,  # This would be the exploded geodataframe
                volume=1,
                height=None,
                merge=True,
            )


class TestAddProjection:
    """Class to test the add_projection method of the SfincsAdapter class."""

    def test_add_slr(self, default_sfincs_adapter):
        adapter = default_sfincs_adapter
        adapter._set_waterlevel_forcing(
            pd.DataFrame(
                index=pd.date_range("2023-01-01", periods=3, freq="D"),
                data={"waterlevel": [1, 2, 3]},
            )
        )

        projection = PhysicalProjection(
            data={
                "sea_level_rise": UnitfulLength(value=10, units="meters"),
                "subsidence": UnitfulLength(value=1, units="meters"),
                "rainfall_increase": 1,
                "storm_frequency_increase": 1,
            }
        )

        wl_df_before = adapter.get_water_levels()
        wl_df_expected = wl_df_before.apply(
            lambda x: x + projection.attrs.sea_level_rise.convert("meters")
        )

        adapter.add_projection(projection)
        wl_df_after = adapter.get_water_levels()

        assert wl_df_expected.equals(wl_df_after)


class TestAddObsPoint:
    def test_add_obs_points(self, test_db: IDatabase):
        scenario_name = "current_extreme12ft_no_measures"
        path_in = (
            test_db.static_path / "templates" / test_db.site.attrs.sfincs.overland_model
        )

        with SfincsAdapter(model_root=path_in) as model:
            model._add_obs_points()
            # write sfincs model in output destination
            new_model_dir = (
                test_db.scenarios.get_database_path(get_input_path=False)
                / scenario_name
                / "sfincs_model_obs_test"
            )
            model.write(path_out=new_model_dir)

        # assert points are the same
        sfincs_obs = pd.read_csv(
            new_model_dir.joinpath("sfincs.obs"),
            header=None,
            delim_whitespace=True,
        )

        names = []
        lat = []
        lon = []

        site_points = test_db.site.attrs.obs_point
        for pt in site_points:
            names.append(pt.name)
            lat.append(pt.lat)
            lon.append(pt.lon)
        df = pd.DataFrame({"Name": names, "Latitude": lat, "Longitude": lon})
        gdf = gpd.GeoDataFrame(
            df, geometry=gpd.points_from_xy(df.Longitude, df.Latitude), crs="EPSG:4326"
        )
        site_obs = gdf.drop(columns=["Longitude", "Latitude"]).to_crs(epsg=26917)

        assert np.abs(sfincs_obs.loc[0, 0] - site_obs.loc[0].geometry.x) < 1
        assert np.abs(sfincs_obs.loc[0, 1] - site_obs.loc[0].geometry.y) < 1
        assert np.abs(sfincs_obs.loc[1, 0] - site_obs.loc[1].geometry.x) < 1
        assert np.abs(sfincs_obs.loc[1, 1] - site_obs.loc[1].geometry.y) < 1
