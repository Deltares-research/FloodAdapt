from pathlib import Path

import pytest

from flood_adapt.objects.benefits.benefits import CurrentSituationModel
from flood_adapt.workflows.benefit_runner import Benefit


@pytest.fixture
def benefit():
    return Benefit(
        name="benefit_raise_properties_2080",
        description="",
        event_set="test_set",
        strategy="elevate_comb_correct",
        projection="all_projections",
        future_year=2080,
        current_situation=CurrentSituationModel(projection="current", year=2023),
        baseline_strategy="no_measures",
        discount_rate=0.07,
        implementation_cost=200000000,
        annual_maint_cost=100000,
    )


def test_benefit_save_and_load(benefit: Benefit, tmp_path: Path):
    benefit.save(tmp_path / "benefit.toml")
    loaded_benefit = Benefit.load_file(tmp_path / "benefit.toml")
    assert benefit == loaded_benefit
