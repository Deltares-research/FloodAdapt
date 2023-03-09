def test_add_elevate():
    measure = api_measures.add_elevate_measure()
    measure.selection_type = "aggregation_area"

    assert measure.type == "elevate_properties"
    assert measure.name == ""
    assert measure.long_name == ""
    assert measure.elevation.value == 0
    assert measure.elevation.units == "m"
    assert measure.elevation.type == "floodmap"
    assert measure.property_type == "RES"
    assert measure.selection_type == "aggregation_area"
