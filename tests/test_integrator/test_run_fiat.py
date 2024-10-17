from pathlib import Path
import shutil
from unittest.mock import patch

from flood_adapt.object_model.hazard.run_fiat import execute_fiat

import pytest

@pytest.fixture
def setup_fiat_dir(test_db, tmp_path):
    scn = test_db.scenarios.get("hazard_already_run")
    if not scn.direct_impacts.hazard.has_run:
        scn.direct_impacts.hazard.preprocess_models()
        scn.direct_impacts.hazard.run_models()
        scn.direct_impacts.hazard.postprocess_models()
    else:
        print(f"Hazard for scenario '{scn.attrs.name}' has already been run.")
    
    scn.direct_impacts.preprocess_models()
    shutil.copytree(scn.results_path, tmp_path / "test_fiat")
    return tmp_path / "test_fiat"

def test_run_fiat_on_linux(setup_fiat_dir):   
    # Act
    success = execute_fiat(setup_fiat_dir)

    # Assert
    assert success
