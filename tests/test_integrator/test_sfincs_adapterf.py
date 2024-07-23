from unittest import mock

import pandas as pd
import pytest

from flood_adapt.integrator.sfincs_adapter import SfincsAdapter
from flood_adapt.object_model.hazard.event.forcing.discharge import (
    DischargeSynthetic,
)
from flood_adapt.object_model.hazard.event.forcing.rainfall import (
    RainfallConstant,
    RainfallFromMeteo,
    RainfallSynthetic,
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
    IWind,
)
from flood_adapt.object_model.hazard.interface.models import ForcingType
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulDirection,
    UnitfulIntensity,
    UnitfulVelocity,
)


@pytest.fixture(scope="class")
def mock_sfincs_adapter(test_db_class) -> SfincsAdapter:
    overland_path = test_db_class.static_path / "templates" / "overland"
    adapter = SfincsAdapter(model_root=overland_path)
    adapter._logger = mock.Mock()
    adapter._logger.handlers = []  # Mock the handlers attribute as an empty list

    return adapter


class TestAddForcing:
    @pytest.fixture(scope="class")
    def sfincs_adapter(self, mock_sfincs_adapter):
        mock_sfincs_adapter._add_forcing_wind = mock.Mock()
        mock_sfincs_adapter._add_forcing_rain = mock.Mock()
        mock_sfincs_adapter._add_forcing_discharge = mock.Mock()
        mock_sfincs_adapter._add_forcing_waterlevels = mock.Mock()
        return mock_sfincs_adapter

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


class TestAddForcingWind:
    @pytest.fixture(scope="class")
    def sfincs_adapter(self, mock_sfincs_adapter):
        mock_sfincs_adapter._model = mock.Mock()
        mock_sfincs_adapter._add_wind_forcing_from_grid = mock.Mock()
        mock_sfincs_adapter._set_config_spw = mock.Mock()
        return mock_sfincs_adapter

    def test_add_forcing_wind_constant(self, sfincs_adapter):
        forcing = WindConstant(
            speed=UnitfulVelocity(10, "m/s"), direction=UnitfulDirection(20, "deg N")
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
        sfincs_adapter._add_wind_forcing_from_grid.assert_called_once_with(forcing.path)

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


class TestAddForcingRain:
    @pytest.fixture(scope="class")
    def sfincs_adapter(self, mock_sfincs_adapter):
        # mock_sfincs_adapter._model = mock.Mock()
        return mock_sfincs_adapter

    def test_add_forcing_rain_constant(self, sfincs_adapter):
        forcing = RainfallConstant(intensity=UnitfulIntensity(10, "mm_hr"))
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


class TestAddForcingDischarge:
    @pytest.fixture(scope="class")
    def sfincs_adapter_2_rivers(self, test_db_class) -> SfincsAdapter:
        overland_path = test_db_class.static_path / "templates" / "overland_2_rivers"
        adapter = SfincsAdapter(model_root=overland_path)

        return adapter

    def test_add_forcing_discharge_synthetic(self, sfincs_adapter_2_rivers):
        sfincs_adapter = sfincs_adapter_2_rivers
        sfincs_adapter._model.setup_discharge_forcing = mock.Mock()

        forcing = mock.Mock(spec=DischargeSynthetic)
        forcing.get_data.return_value = pd.DataFrame(
            {
                "time": [0, 1, 2],
                "discharge": [10, 20, 30],
            }
        )

        sfincs_adapter._add_forcing_discharge(forcing)

        sfincs_adapter._model.setup_discharge_forcing.assert_called_once_with(
            timeseries=forcing.get_data(), locations=mock.ANY, merge=False
        )

    def test_add_forcing_discharge_unsupported(self, sfincs_adapter_2_rivers):
        sfincs_adapter = sfincs_adapter_2_rivers

        class UnsupportedDischarge(IDischarge):
            pass

        sfincs_adapter._logger.warning = mock.Mock()

        forcing = UnsupportedDischarge()

        sfincs_adapter._add_forcing_discharge(forcing)

        sfincs_adapter._logger.warning.assert_called_once_with(
            f"Unsupported discharge forcing type: {forcing.__class__.__name__}"
        )

    def test_add_dis_bc_no_rivers(self, sfincs_adapter_2_rivers):
        sfincs_adapter = sfincs_adapter_2_rivers
        sfincs_adapter._model.setup_discharge_forcing = mock.Mock()
        sfincs_adapter._site = mock.Mock()
        sfincs_adapter._site.attrs.river = []

        list_df = pd.DataFrame(
            {
                "time": pd.date_range(start="2023-01-01", periods=3, freq="D"),
                "discharge": [10, 20, 30],
            }
        )

        sfincs_adapter._add_dis_bc(list_df)

        sfincs_adapter._model.setup_discharge_forcing.assert_called_once_with(
            timeseries=list_df, locations=mock.ANY, merge=False
        )

    def test_add_dis_bc_matching_rivers(self, sfincs_adapter_2_rivers):
        sfincs_adapter = sfincs_adapter_2_rivers
        list_df = pd.DataFrame(
            {
                "time": pd.date_range(start="2023-01-01", periods=3, freq="D"),
                "discharge1": [10, 20, 30],
                "discharge2": [15, 25, 35],
            }
        )
        sfincs_adapter._site = mock.Mock()
        sfincs_adapter._site.attrs.river = [
            mock.Mock(name="River1", x_coordinate=1, y_coordinate=1),
            mock.Mock(name="River2", x_coordinate=2, y_coordinate=2),
        ]
        gdf_locs = mock.Mock()
        gdf_locs.geometry = [mock.Mock(x=1, y=1), mock.Mock(x=2, y=2)]
        gdf_locs.__len__ = mock.Mock(return_value=2)  # Ensure len(gdf_locs) works
        sfincs_adapter._model.forcing["dis"].vector.to_gdf = mock.Mock(
            return_value=gdf_locs
        )

        sfincs_adapter._add_dis_bc(list_df)

        sfincs_adapter._model.setup_discharge_forcing.assert_called_once_with(
            timeseries=list_df, locations=gdf_locs, merge=False
        )

    def test_add_dis_bc_mismatched_coordinates(self, sfincs_adapter_2_rivers):
        sfincs_adapter = sfincs_adapter_2_rivers
        list_df = pd.DataFrame(
            {
                "time": pd.date_range(start="2023-01-01", periods=3, freq="D"),
                "discharge1": [10, 20, 30],
                "discharge2": [15, 25, 35],
            }
        )
        sfincs_adapter._site = mock.Mock()
        sfincs_adapter._site.attrs.river = [
            mock.Mock(name="River1", x_coordinate=1, y_coordinate=1),
            mock.Mock(name="River2", x_coordinate=2, y_coordinate=2),
        ]
        gdf_locs = mock.Mock()
        gdf_locs.geometry = [mock.Mock(x=1, y=1), mock.Mock(x=3, y=3)]
        gdf_locs.__len__ = mock.Mock(return_value=2)  # Ensure len(gdf_locs) works
        sfincs_adapter._model.forcing["dis"].vector.to_gdf = mock.Mock(
            return_value=gdf_locs
        )

        with pytest.raises(
            ValueError, match="Incompatible river coordinates for river"
        ):
            sfincs_adapter._add_dis_bc(list_df)

    def test_add_dis_bc_mismatched_number_of_rivers(self, sfincs_adapter_2_rivers):
        sfincs_adapter = sfincs_adapter_2_rivers

        list_df = pd.DataFrame(
            {
                "time": pd.date_range(start="2023-01-01", periods=3, freq="D"),
                "discharge1": [10, 20, 30],
                "discharge2": [15, 25, 35],
                "discharge3": [15, 25, 35],
            }
        )

        with pytest.raises(
            ValueError,
            match="Number of rivers in site.toml and SFINCS template model not compatible",
        ):
            sfincs_adapter._add_dis_bc(list_df)
