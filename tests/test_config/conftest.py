import pytest

from flood_adapt.config import get_settings
from flood_adapt.config.fiat import (
    FiatModel,
)
from flood_adapt.config.gui import GuiModel
from flood_adapt.config.sfincs import (
    SfincsModel,
)
from flood_adapt.config.site import (
    Site,
)
from tests.data.create_test_static import (
    create_fiat_config,
    create_gui_config,
    create_sfincs_config,
    create_standard_objects,
)


@pytest.fixture
def test_sfincs():
    return create_sfincs_config()


@pytest.fixture
def test_gui():
    return create_gui_config(get_settings().database_path)


@pytest.fixture
def test_fiat():
    return create_fiat_config()


@pytest.fixture
def test_site(
    test_sfincs: SfincsModel, test_gui: GuiModel, test_fiat: FiatModel
) -> Site:
    return Site(
        name="Charleston",
        description="Charleston, SC",
        lat=32.7765,
        lon=-79.9311,
        standard_objects=create_standard_objects(),
        sfincs=test_sfincs,
        gui=test_gui,
        fiat=test_fiat,
    )
