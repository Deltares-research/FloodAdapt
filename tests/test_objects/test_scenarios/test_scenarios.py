import pytest

from flood_adapt.objects.scenarios.scenarios import Scenario


@pytest.fixture
def test_scenario():
    return Scenario(
        name="test_projection",
        event="test_event",
        projection="test_projection",
        strategy="test_strategy",
    )


def test_save_load_eq(test_scenario, tmp_path):
    # Arrange
    toml_path = tmp_path / "test_file.toml"

    # Act
    test_scenario.save(toml_path)
    loaded = Scenario.load_file(toml_path)

    # Assert
    assert loaded == test_scenario
