import shutil
from pathlib import Path

from dotenv import load_dotenv
from hydromt_fiat import FiatModel

from flood_adapt import unit_system as us
from flood_adapt.config.config import Settings
from flood_adapt.config.hazard import DemModel, FloodModel, RiverModel
from flood_adapt.database_builder.database_builder import (
    ConfigModel,
    DatabaseBuilder,
    GuiConfigModel,
    SpatialJoinModel,
    UnitSystems,
)
from flood_adapt.flood_adapt import FloodAdapt
from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.objects.events.synthetic import SyntheticEvent
from flood_adapt.objects.forcing.discharge import DischargeConstant
from flood_adapt.objects.forcing.forcing import ForcingType
from flood_adapt.objects.forcing.time_frame import TimeFrame
from flood_adapt.objects.forcing.timeseries import (
    GaussianTimeseries,
)
from flood_adapt.objects.forcing.waterlevels import (
    SurgeModel,
    TideModel,
    WaterlevelSynthetic,
)
from flood_adapt.objects.scenarios.scenarios import Scenario


def save_test_scn(fa: FloodAdapt) -> Scenario:
    event = SyntheticEvent(
        name="test_event",
        time=TimeFrame(),
        forcings={
            ForcingType.WATERLEVEL: [
                WaterlevelSynthetic(
                    surge=SurgeModel(
                        timeseries=GaussianTimeseries(
                            peak_time=us.UnitfulTime(
                                value=0, units=us.UnitTypesTime.hours
                            ),
                            peak_value=us.UnitfulLength(
                                value=5, units=us.UnitTypesLength.feet
                            ),
                            duration=us.UnitfulTime(
                                value=6, units=us.UnitTypesTime.hours
                            ),
                        )
                    ),
                    tide=TideModel(
                        harmonic_amplitude=us.UnitfulLength(
                            value=1, units=us.UnitTypesLength.feet
                        ),
                        harmonic_phase=us.UnitfulTime(
                            value=0, units=us.UnitTypesTime.hours
                        ),
                        harmonic_period=us.UnitfulTime(
                            value=12, units=us.UnitTypesTime.hours
                        ),
                    ),
                )
            ],
            ForcingType.DISCHARGE: [
                DischargeConstant(
                    river=RiverModel(
                        name="river1",
                        x_coordinate=342659.4,
                        y_coordinate=3387590.8,
                        mean_discharge=us.UnitfulDischarge(
                            value=5000, units=us.UnitTypesDischarge.cfs
                        ),
                    ),
                    discharge=us.UnitfulDischarge(
                        value=10, units=us.UnitTypesDischarge.cfs
                    ),
                ),
                DischargeConstant(
                    river=RiverModel(
                        name="river2",
                        x_coordinate=296476.6,
                        y_coordinate=3382603.3,
                        mean_discharge=us.UnitfulDischarge(
                            value=1000, units=us.UnitTypesDischarge.cfs
                        ),
                    ),
                    discharge=us.UnitfulDischarge(
                        value=1000, units=us.UnitTypesDischarge.cfs
                    ),
                ),
            ],
        },
    )
    scn = Scenario(
        name="test_scenario",
        event=event.name,
        projection="current",
        strategy="no_measures",
    )

    if scn.name in fa.get_scenarios()["name"]:
        fa.delete_scenario(scn.name)

    if event.name in fa.get_events()["name"]:
        fa.delete_event(event.name)

    fa.save_event(event)
    fa.save_scenario(scn)
    return scn


def validate(config: ConfigModel):
    load_dotenv()
    settings = Settings(
        DATABASE_ROOT=ROOT / "Database",
        DATABASE_NAME="jackson_test",
        VALIDATE_BINARIES=True,
        VALIDATE_ALLOWED_FORCINGS=True,
    )
    fa = FloodAdapt(database_path=settings.database_path)
    scn = save_test_scn(fa)
    fa.run_scenario(scn.name)


def update_fiat_model(fiat_dir: Path) -> Path:
    new_dir = fiat_dir.with_name("jackson_fiat_updated")
    shutil.rmtree(new_dir, ignore_errors=True)
    shutil.copytree(fiat_dir, new_dir, dirs_exist_ok=True)

    model = FiatModel(root=fiat_dir.as_posix(), config_fn="settings.toml", mode="r")
    model.read()
    model.set_root(root=new_dir.as_posix(), mode="w+")

    # take first curve available, in this case: `AGR1_structure`.
    # ! Selecting the correct damage function for your exposure data is part of the data preparation process!
    structural_dmg_fn = model.vulnerability_curves.iloc[0][1]
    model.exposure.exposure_db["fn_damage_Structure"] = structural_dmg_fn

    # Set config output->csv to `output.csv`
    model.set_config("output.csv.name", "output.csv")

    model.write()
    return new_dir


def build_config():
    # General
    gui = GuiConfigModel(
        max_aggr_dmg=1e5,
        max_benefits=1e5,
        max_flood_depth=1e5,
        max_footprint_dmg=1e5,
    )

    # Hazard
    overland_model = FloodModel(
        name=SFINCS_DIR.as_posix(),
        reference="MSL",  # TODO !
    )
    dem = DemModel(
        filename=(SFINCS_DIR / "subgrid" / "dep_subgrid.tif").as_posix(),
        units=us.UnitTypesLength.feet,
    )

    # Impacts
    aggregation_areas = [
        SpatialJoinModel(
            name="Census Blockgroup",
            field_name="GEOID",
            file=(
                FIAT_DIR / "geoms" / "aggregation_areas" / "block_groups.gpkg"
            ).as_posix(),
        ),
    ]

    # Final
    config = ConfigModel(
        name="jackson_test",
        database_path=(ROOT / "Database").as_posix(),
        unit_system=UnitSystems.imperial,
        gui=gui,
        infographics=False,
        fiat=FIAT_DIR.as_posix(),
        aggregation_areas=aggregation_areas,
        fiat_buildings_name="buildings",
        sfincs_overland=overland_model,
        dem=dem,
    )
    config.write(ROOT / "database_builder_config.toml")
    return config


logger = FloodAdaptLogging.getLogger(__name__)
ROOT = Path("C:/Users/blom_lk/Projects/FloodAdapt/temp/deltares_share").resolve()
FIAT_DIR = update_fiat_model(ROOT / "jackson_fiat_new")
SFINCS_DIR = ROOT / "sfincs_overland"

if __name__ == "__main__":
    config = build_config()
    DatabaseBuilder(config).build(overwrite=True)
    validate(config)


"""
Changes compared to the email from 14/10/2025

fiat:
# bugs
- add a skip + warning to `DatabaseBuilder._delete_extra_geometries` if no object_id column (deleted region.gpkg)
- svi: add early return statements to `DatabaseBuilder.create_svi` when svi config is incomplete
- fiat_adapter: add `_clean_suffix_columns` to remove duplicate columns after merging exposure and results

# data changes
- delete spatial_joins.toml, added `aggregation_areas` above
- settings.toml: change exposure.geom_names `roads` to `buildings`, and update exposure.geoms.file2
- exposure.csv: rename column `Primary Object` to `primary_object_type`
- exposure.csv: Assigned structure dmg functions to the buildings (was missing for all, please see https://deltares.github.io/hydromt_fiat/stable/_generated/hydromt_fiat.fiat.FiatModel.setup_vulnerability.html#hydromt_fiat.fiat.FiatModel.setup_vulnerability )

sfincs:
- delete forcing timeseries files and delete corresponding config entries in sfincs.inp: [precip_2d.nc, press_2d.nc, wind_2d.nc, sfincs.bzs, sfincs.dis]

QUESTIONS FOR WATER INSTITUTE:
? Question: what is `si.gpkg`? (SVI ?)
? Question: Do you want Infometrics?
? Question: Do you want Infographics?
? Question: Do you want Hurricanes?
? Question: Do you want Probabilistic event sets?
? Question: Do you want Observation points?
? Question: Do you want Tide Gauges?
? Question: Do you want Water level references?

LUUK TASKS:
TODO: run the forcing validation of SfincsAdapter in DatabaseBuilder.build()
TODO: Add automatic reading of obs points from a hydromt sfincs model in DatabaseBuilder. See ` DatabaseBuilder.create_rivers()`

PANOS TASKS:
TODO: check if the added if check in DatabaseBuilder._delete_extra_geometries is correct. @Panos
TODO: check if the added early return statements in DatabaseBuilder.create_svi is correct. @Panos
"""
