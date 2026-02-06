# import necessary libraries
import pytest
from typing import Tuple

from flood_adapt.objects.scenarios.scenarios import Scenario
from flood_adapt.workflows.postprocessing import make_animation
from flood_adapt.dbs_classes.database import Database
from flood_adapt.adapter import SfincsAdapter
from tests.fixtures import TEST_DATA_DIR



@pytest.fixture(scope="class")
def test_write_geotiff(
        self,
        postprocess_scenario_class: Tuple[Database, Scenario],
    ):
        # Arrange   
        database, scn = postprocess_scenario_class
        # animation_path = scn._get_result_path(scn) / f"{scn.name}.mp4"

        # Act
        make_animation(database=database, scenario=scn, 
        bbox=None, zoomlevel=16,
    )

        # Assert
        # assert animation_path.exists()

