import pytest

from flood_adapt.object_model.tipping_point import TippingPoint


class TestTippingPoints:
    @pytest.fixture()
    def tp_dict(self):
        return {
            "name": "tipping_point_test",
            "description": "",
            "event_set": "extreme12ft",
            "strategy": "no_measures",
            "projection": "current",
            "sealevelrise": [0.5, 1.0, 1.5],
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


# database = read_database(
#     rf"C:\\Users\\morenodu\\OneDrive - Stichting Deltares\\Documents\\GitHub\\FloodAdapt-Database",
#     "charleston_full",
# )
# set_system_folder(
#     rf"C:\\Users\\morenodu\\OneDrive - Stichting Deltares\\Documents\\GitHub\\FloodAdapt-Database\\system"
# )

# tp_dict = {
#     "name": "tipping_point_test",
#     "description": "",
#     "event_set": "extreme12ft",
#     "strategy": "no_measures",
#     "projection": "current",
#     "sealevelrise": [0.5, 1.0, 1.5],
#     "tipping_point_metric": [
#         ("FloodedAll", 34195.0, "greater"),
#         ("FullyFloodedRoads", 2000, "greater"),
#     ],
# }
# # load
# test_point = TippingPoint.load_dict(tp_dict)
# # create scenarios for tipping points
# test_point.create_tp_scenarios()
# # run all scenarios
# test_point.run_tp_scenarios()
