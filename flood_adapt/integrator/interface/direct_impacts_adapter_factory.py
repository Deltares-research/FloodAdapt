from flood_adapt.integrator.interface.direct_impacts_adapter import DirectImpactsAdapter


class DirectImpactsAdapterFactory:
    """Simple parser to get the respective DirectImpactAdapter class from a model name string given in the config file.

    Args:
        type (str): name of the model

    Returns
    -------
        Measure: ImpactMeasure subclass
    """

    @staticmethod
    def get_adapter(model: str) -> DirectImpactsAdapter:
        if model == "fiat":
            from flood_adapt.integrator.fiat_adapter import FiatAdapter

            return FiatAdapter
        else:
            raise ValueError(
                f"'{model}' is not a recognized name for a FloodAdapt direct impacts adapter."
            )
