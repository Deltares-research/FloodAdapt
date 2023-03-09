# User presses add measure when elevate properties and aggregation area are selected
import api

# add new measure
measure = api.add_elevate_measure("elevate_properties")

print(measure.name)


# API
def add_elevate_measure(props) -> IElevateMeasure:
    measure = ElevateMeasure(props)
    return measure


#
