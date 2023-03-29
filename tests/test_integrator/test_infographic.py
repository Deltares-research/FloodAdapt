from pathlib import Path

from flood_adapt.object_model.direct_impacts import DirectImpacts

test_database = Path().absolute() / "tests" / "test_database"


def test_infographic():
    DirectImpacts.infographic(
        Path(
            "p:/11207949-dhs-phaseii-floodadapt/FloodAdapt/Test_data/database/charleston"
        ),
        "current_kingtide2021_no_measures",
    )
