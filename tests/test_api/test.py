import datetime

import tomli_w

from flood_adapt.object_model.hazard.interface.models import TimeModel
from flood_adapt.object_model.io.unitfulvalue import UnitfulTime

model = TimeModel(
    start_time=datetime.datetime(year=2024, month=10, day=1),
    end_time=datetime.datetime(year=2024, month=10, day=3),
    time_step=UnitfulTime(value=1, units="hours").to_timedelta(),
)
with open("test.toml", "wb") as f:
    tomli_w.dump(model.model_dump(), f)
