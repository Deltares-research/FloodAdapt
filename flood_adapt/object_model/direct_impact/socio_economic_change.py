from flood_adapt.object_model.interface.projections import SocioEconomicChangeModel


class SocioEconomicChange:
    """The Projection class containing various risk drivers."""

    def __init__(self, data: SocioEconomicChangeModel):
        self.attrs = SocioEconomicChangeModel.parse_obj(data)
