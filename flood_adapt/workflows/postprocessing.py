
from flood_adapt.adapter import SfincsAdapter
from flood_adapt.objects.scenarios.scenarios import Scenario
from flood_adapt.dbs_classes.database import Database



def make_animation(database: Database, scenario: Scenario
):
    """Create an animation of the flood extent over time.
    Produced floodmap is in the units defined in the sfincs config settings.

    Parameters
    ----------
    scenario : Scenario
        Scenario for which to create the floodmap.
    """

    results_path = (
        database.scenarios.output_path / 
        scenario.name / "Flooding"
    )
    sim_path = (
        results_path / "simulations"
        / database.site.sfincs.config.overland_model.name
    )
    
    with SfincsAdapter(model_root=sim_path) as model:
        model.create_animation_qt(scenario=scenario, 
        bbox=None, zoomlevel=16,
    )