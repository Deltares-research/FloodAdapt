from pathlib import Path

from flood_adapt.flood_adapt import FloodAdapt


def test_flood_adapt():
    db_path = Path(__file__).parents[3] / "Database" / "charleston_test"

    fa = FloodAdapt(database_path=db_path)

    scn = fa.get_scenarios()["name"][0]
    fa.run_scenario(scn)

    assert fa.database.scenarios.get_floodmap(scn) is not None
