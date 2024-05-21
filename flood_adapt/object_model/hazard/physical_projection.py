from flood_adapt.object_model.interface.projections import PhysicalProjectionModel


class PhysicalProjection:
    """The Projection class containing various risk drivers."""

    attrs: PhysicalProjectionModel

    def __init__(self, data: PhysicalProjectionModel):
        self.attrs = PhysicalProjectionModel.model_validate(data)

    def __eq__(self, other):
        if not isinstance(other, PhysicalProjection):
            # don't attempt to compare against unrelated types
            return NotImplemented

        return self.attrs == other.attrs
