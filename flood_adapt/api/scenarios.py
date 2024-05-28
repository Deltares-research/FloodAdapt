import logging
import os
from pathlib import Path
from typing import Any, Union

from flood_adapt.dbs_controller import Database
from flood_adapt.object_model.direct_impacts import DirectImpacts
from flood_adapt.object_model.interface.scenarios import IScenario
from flood_adapt.object_model.scenario import Scenario


def get_scenarios() -> dict[str, Any]:
    # sorting and filtering either with PyQt table or in the API
    return Database().scenarios.list_objects()


def get_scenario(name: str) -> IScenario:
    return Database().scenarios.get(name)


def create_scenario(attrs: dict[str, Any]) -> IScenario:
    return Scenario.load_dict(attrs, Database().input_path)


def save_scenario(scenario: IScenario) -> (bool, str):
    """Save the scenario to the Database().
    Parameters
    ----------
    scenario : IScenario
        The scenario to save.
    database : IDatabase
        The database to save the scenario to.
    Returns
    -------
    bool
        Whether the scenario was saved successfully.
    str
        The error message if the scenario was not saved successfully.
    """
    try:
        Database().scenarios.save(scenario)
        return True, ""
    except Exception as e:
        return False, str(e)


def edit_scenario(scenario: IScenario) -> None:
    Database().scenarios.edit(scenario)


def delete_scenario(name: str) -> None:
    Database().scenarios.delete(name)


def run_scenario(name: Union[str, list[str]]) -> None:
    if isinstance(name, str):
        scenario_name = [name]
    else:
        scenario_name = name

    errors = []
    database = Database()
    for scn in scenario_name:
        try:
            database.scenarios.has_run(scn) # TODO: Make this into has run hazard, not both
            scenario = database.scenarios.get(scn)
            results_path = Path(database.output_path).joinpath(
                "output", "Scenarios", scn
            )
            direct_impacts = DirectImpacts(
                scenario=scenario.attrs,
                database_input_path=Path(database.input_path),
                results_path=results_path,
            )
            os.makedirs(results_path, exist_ok=True)

            version = "0.1.0"
            logging.info(f"FloodAdapt version {version}")
            logging.info(
                f"Started evaluation of {scn}"
            )

            scenario.initiate_root_logger(
                results_path.joinpath(f"logfile_{scn}.log")
            )

            # preprocess model input data first, then run, then post-process
            if not direct_impacts.hazard.has_run:
                direct_impacts.hazard.preprocess_models()
                direct_impacts.hazard.run_models()
                direct_impacts.hazard.postprocess_models()
            else:
                print(f"Hazard for scenario '{scn}' has already been run.")
            if not direct_impacts.has_run:
                direct_impacts.preprocess_models()
                direct_impacts.run_models()
                direct_impacts.postprocess_models()
            else:
                print(
                    f"Direct impacts for scenario '{scn}' has already been run."
                )

            logging.info(
                f"Finished evaluation of {scn}"
            )
            scenario.close_root_logger_handlers()

        except RuntimeError as e:
            if "SFINCS model failed to run." in str(e):
                errors.append(str(scn))

    if errors:
        raise RuntimeError(
            "SFincs model failed to run for the following scenarios: "
            + ", ".join(errors)
            + ". Check the logs for more information."
        )

