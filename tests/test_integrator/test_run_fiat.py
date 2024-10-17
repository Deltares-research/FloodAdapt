import shutil

import pytest

from flood_adapt.log import FloodAdaptLogging
from flood_adapt.object_model.hazard.run_fiat import execute_fiat

logger = FloodAdaptLogging.getLogger("test_run_fiat")


@pytest.fixture
def setup_scn_dir(test_db, tmp_path):
    scn = test_db.scenarios.get("all_projections_extreme12ft_strategy_comb")
    if not scn.direct_impacts.hazard.has_run:
        scn.direct_impacts.hazard.preprocess_models()
        scn.direct_impacts.hazard.run_models()
        scn.direct_impacts.hazard.postprocess_models()
    else:
        print(f"Hazard for scenario '{scn.attrs.name}' has already been run.")

    scn.direct_impacts.preprocess_models()
    shutil.copytree(scn.results_path, tmp_path / "test_fiat")
    return tmp_path / "test_fiat"


def test_run_fiat_on_linux(setup_scn_dir):
    logger.info(f"Running test_run_fiat_on_linux for {setup_scn_dir}")

    # Act
    success = execute_fiat(setup_scn_dir / "Impacts" / "fiat_model")

    # Assert
    assert success
