import pandas as pd

from flood_adapt.object_model.hazard.event.forcing.wind import (
    WindConstant,
)
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulDirection,
    UnitfulVelocity,
    UnitTypesDirection,
    UnitTypesVelocity,
)


class TestWindConstant:
    def test_wind_constant_get_data(self):
        # Arrange
        speed = UnitfulVelocity(10, UnitTypesVelocity.mps)
        direction = UnitfulDirection(90, UnitTypesDirection.degrees)

        # Act
        wind_df = WindConstant(speed=speed, direction=direction).get_data()

        # Assert
        assert isinstance(wind_df, pd.DataFrame)
        assert not wind_df.empty
        assert len(wind_df) == 1
        assert wind_df["mag"].iloc[0] == 10
        assert wind_df["dir"].iloc[0] == 90


# class TestWindFromCSV:
#     def test_wind_from_csv_get_data(self, tmp_path):
#         # Arrange
#         path = Path(tmp_path) / "wind/test.csv"

#         # Required variables: ['wind_u' (m/s), 'wind_v' (m/s)]
#         # Required coordinates: ['time', 'y', 'x']

#         data = {
#             "time": ["2021-01-01 00:00:00", "2021-01-01 01:00:00"],
#             "wind_u": [1, 2],
#             "wind_v": [2, 3],
#         }

#         # Act
#         wind_df = WindFromCSV(path=path).get_data()

#         # Assert
#         assert isinstance(wind_df, pd.DataFrame)
#         assert not wind_df.empty
# Add additional assertions as needed
