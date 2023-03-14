from flood_adapt.object_model.interface.projections import PhysicalProjectionModel


class PhysicalProjection:
    """The Projection class containing various risk drivers."""

    def __init__(self, data: PhysicalProjectionModel):
        self.attrs = PhysicalProjectionModel.parse_obj(data)
