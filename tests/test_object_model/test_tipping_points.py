from pathlib import Path

import pytest

from flood_adapt.dbs_controller import Database
from flood_adapt.object_model.scenario import Scenario
from flood_adapt.object_model.tipping_point import TippingPoint, TippingPointStatus


class TestTippingPoints:
    @pytest.fixture()
    def tp_dict(self):
        return {
            "name": "tipping_point_test",
            "description": "",
            "event_set": "extreme12ft",
            "strategy": "no_measures",
            "projection": "current",
            "sealevelrise": [0.5, 0.75, 1.0, 1.5],
            "tipping_point_metric": [
                ("TotalDamageEvent", 110974525.0, "greater"),
                ("FullyFloodedRoads", 2305, "greater"),
            ],
        }

    @pytest.fixture()
    def created_tp_scenarios(self, tp_dict):
        test_point = TippingPoint.load_dict(tp_dict)
        test_point.create_tp_scenarios()
        return test_point

    @pytest.fixture()
    def run_tp_scenarios(self, created_tp_scenarios):
        created_tp_scenarios.run_tp_scenarios()
        return created_tp_scenarios

    def test_createTippingPoints_scenariosAlreadyExist_notDuplicated(
        self, test_db, tp_dict
    ):
        test_point = TippingPoint.load_dict(tp_dict)
        test_point.create_tp_scenarios()
        assert test_point is not None
        assert isinstance(test_point, TippingPoint)

    def test_run_scenarios(self, test_db, created_tp_scenarios):
        created_tp_scenarios.run_tp_scenarios()
        assert created_tp_scenarios is not None

    def test_slr_projections_creation(self, test_db, tp_dict):
        test_point = TippingPoint.load_dict(tp_dict)
        for slr in test_point.attrs.sealevelrise:
            test_point.slr_projections(slr)
            projection_path = (
                Path(Database().input_path)
                / "projections"
                / f"{test_point.attrs.projection}_slr{str(slr).replace('.', '')}"
                / f"{test_point.attrs.projection}_slr{str(slr).replace('.', '')}.toml"
            )
            assert projection_path.exists()

    def test_scenario_tippingpoint_reached(self, test_db, run_tp_scenarios):
        for name, scenario in run_tp_scenarios.scenarios.items():
            assert (
                "tipping point reached" in scenario
            ), f"Key 'tipping point reached' not found in scenario: {name}"
            assert isinstance(
                scenario["tipping point reached"], bool
            ), f"Value for 'tipping point reached' is not boolean in scenario: {name}"


# TODO create test for tipping point reached being true and another for false

# TODO: check if the tipping point reached is indeed correct


class TestTippingPointInvalidInputs:
    @pytest.mark.parametrize(
        "invalid_tp_dict",
        [
            # Missing required fields
            {},
            {"name": "missing_other_fields"},
            # Incorrect data types
            {
                "name": 123,
                "description": 456,
                "event_set": "extreme12ft",
                "strategy": "no_measures",
                "projection": "current",
                "sealevelrise": "not_a_list",
                "tipping_point_metric": "not_a_list",
            },
            # Invalid values
            {
                "name": "",
                "description": "",
                "event_set": "unknown_event",
                "strategy": "no_measures",
                "projection": "future",
                "sealevelrise": [-1, -2],
                "tipping_point_metric": [
                    ("TotalDamageEvent", "not_a_number", "greater")
                ],
            },
        ],
    )
    def test_load_dict_with_invalid_inputs(self, invalid_tp_dict):
        with pytest.raises(ValueError):
            TippingPoint.load_dict(invalid_tp_dict)

    def test_edge_cases_empty_sealevelrise(self, test_db):
        tp_dict = {
            "name": "tipping_point_test",
            "description": "",
            "event_set": "extreme12ft",
            "strategy": "no_measures",
            "projection": "current",
            "sealevelrise": [],
            "tipping_point_metric": [
                ("TotalDamageEvent", 110974525.0, "greater"),
                ("FullyFloodedRoads", 2305, "greater"),
            ],
        }
        test_point = TippingPoint.load_dict(tp_dict)
        test_point.create_tp_scenarios()
        assert (
            len(test_point.scenarios) == 0
        ), "Scenarios should not be created for empty sealevelrise list"