from flood_adapt.object_model.models.projections import SocioEconomicChangeModel


class SocioEconomicChange:
    """The Projection class containing various risk drivers."""

    def __init__(self, data: SocioEconomicChangeModel):
        self.attrs = SocioEconomicChangeModel.parse_obj(data)
