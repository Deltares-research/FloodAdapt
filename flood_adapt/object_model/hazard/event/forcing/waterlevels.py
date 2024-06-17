from flood_adapt.object_model.interface.events import IForcing, SurgeModel, TideModel


class IWaterlevel(IForcing):
    pass


class WaterlevelSynthetic(IWaterlevel):
    # Surge + tide
    surge: SurgeModel
    tide: TideModel


class WaterlevelFromFile(IWaterlevel):
    path: str


class WaterlevelFromModel(IWaterlevel):
    path: str
