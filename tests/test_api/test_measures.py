import pytest

from flood_adapt.api.measures import (
    copy_measure,
    create_measure,
    delete_measure,
    get_measure,
    save_measure,
)
from flood_adapt.object_model.interface.measures import Measure
from tests.test_object_model.test_measures import (
    test_buyout,
    test_elevate,
    test_floodproof,
    test_floodwall,
    test_green_infra,
    test_pump,
)

__all__ = [
    "test_buyout",
    "test_elevate",
    "test_floodproof",
    "test_floodwall",
    "test_pump",
    "test_green_infra",
]
# dict of measure fixture names and their corresponding measure type
measure_fixtures = {
    "test_elevate": "elevate_properties",
    "test_buyout": "buyout_properties",
    "test_floodproof": "floodproof_properties",
    "test_floodwall": "floodwall",
    "test_pump": "pump",
    "test_green_infra": "greening",
}


@pytest.mark.parametrize("measure_fixture_name", measure_fixtures.keys())
def test_create_measure(measure_fixture_name, request):
    measure: Measure = request.getfixturevalue(measure_fixture_name)
    measure = create_measure(
        attrs=measure.model_dump(exclude_none=True), type=measure.type
    )
    assert measure is not None


@pytest.mark.parametrize("measure_fixture", measure_fixtures.keys())
def test_save_measure(test_db, measure_fixture, request):
    measure = request.getfixturevalue(measure_fixture)

    save_measure(measure)
    assert (test_db.measures.input_path / measure.name).exists()


@pytest.mark.parametrize("measure_fixture", measure_fixtures.keys())
def test_get_measure(test_db, measure_fixture, request):
    measure = request.getfixturevalue(measure_fixture)

    save_measure(measure)
    assert (test_db.measures.input_path / measure.name).exists()

    loaded_measure = get_measure(measure.name)
    assert loaded_measure == measure


@pytest.mark.parametrize("measure_fixture", measure_fixtures.keys())
def test_delete_measure(test_db, measure_fixture, request):
    measure = request.getfixturevalue(measure_fixture)
    save_measure(measure)
    assert (test_db.measures.input_path / measure.name).exists()

    delete_measure(measure.name)
    assert not (test_db.measures.input_path / measure.name).exists()


@pytest.mark.parametrize("measure_fixture", measure_fixtures.keys())
def test_copy_measure(test_db, measure_fixture, request):
    measure = request.getfixturevalue(measure_fixture)
    save_measure(measure)
    assert (test_db.measures.input_path / measure.name).exists()

    new_name = f"copy_{measure.name}"
    new_description = f"copy of {measure.description}"

    copy_measure(
        old_name=measure.name, new_name=new_name, new_description=new_description
    )
    new_measure = get_measure(new_name)

    assert (test_db.measures.input_path / new_name).exists()
    assert measure == new_measure
