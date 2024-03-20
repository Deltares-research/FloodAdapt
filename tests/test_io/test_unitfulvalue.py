import pytest

from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulIntensity,
    UnitfulLength,
    UnitfulTime,
    UnitTypesIntensity,
    UnitTypesLength,
    UnitTypesTime,
    ValueUnitPair,
)


def _perform_conversion_test(
    test_class, initial_value, initial_unit, expected_value, target_unit
):
    """
    Performs a unit conversion test for a given test_class.
    Note:
        The only tests you need to write for a new ValueUnitPair are:
            the conversion tests (this function)
            validator tests (if you have custom validators)

    Args:
        test_class: The class to test, e.g., UnitfulIntensity, UnitfulLength.
        initial_value (float): The initial value for the conversion.
        initial_unit: The initial unit of the value.
        expected_value (float): The expected value after conversion.
        target_unit: The target unit for the conversion.
    """

    instance = test_class(initial_value, initial_unit)
    assert isinstance(
        instance, ValueUnitPair
    ), f"Only ValueUnitPairs can be tested by this function, not: {type(test_class).__name__}."

    converted = instance.convert(target_unit)

    assert converted.value == pytest.approx(
        expected_value, rel=1e-2
    ), f"{instance} Failed conversion: {initial_unit} to {target_unit}. Expected {expected_value}, got {converted.value}"


TEST_TIME_CONVERSIONS = [
    (
        1,
        UnitTypesTime.days,
        24,
        UnitTypesTime.hours,
    ),
    (
        1,
        UnitTypesTime.days,
        24 * 60,
        UnitTypesTime.minutes,
    ),
    (
        1,
        UnitTypesTime.days,
        24 * 60 * 60,
        UnitTypesTime.seconds,
    ),
    (1, UnitTypesTime.hours, 1 / 24, UnitTypesTime.days),
    (1, UnitTypesTime.hours, 60, UnitTypesTime.minutes),
    (1, UnitTypesTime.hours, 60 * 60, UnitTypesTime.seconds),
    (1, UnitTypesTime.minutes, 1 / 60 / 24, UnitTypesTime.days),
    (1, UnitTypesTime.minutes, 1 / 60, UnitTypesTime.hours),
    (1, UnitTypesTime.minutes, 60, UnitTypesTime.seconds),
    (1, UnitTypesTime.seconds, 1 / 60 / 60 / 24, UnitTypesTime.days),
    (1, UnitTypesTime.seconds, 1 / 60 / 60, UnitTypesTime.hours),
    (1, UnitTypesTime.seconds, 1 / 60, UnitTypesTime.minutes),
]


@pytest.mark.parametrize(
    "initial_value, initial_unit, expected_value, target_unit", TEST_TIME_CONVERSIONS
)
def test_UnitFullTime_convert(initial_value, initial_unit, expected_value, target_unit):
    _perform_conversion_test(
        UnitfulTime, initial_value, initial_unit, expected_value, target_unit
    )


TEST_INTENSITY_CONVERSIONS = [
    (1, UnitTypesIntensity.mm_hr, 1 / 25.39544832, UnitTypesIntensity.inch_hr),
    (180, UnitTypesIntensity.mm_hr, 7.08, UnitTypesIntensity.inch_hr),
    (1, UnitTypesIntensity.inch_hr, 25.39544832, UnitTypesIntensity.mm_hr),
    (4000, UnitTypesIntensity.inch_hr, 101581.8, UnitTypesIntensity.mm_hr),
    (180, UnitTypesIntensity.inch_hr, 4572, UnitTypesIntensity.mm_hr),
    (180, UnitTypesIntensity.mm_hr, 180, UnitTypesIntensity.mm_hr),
    (180, UnitTypesIntensity.inch_hr, 180, UnitTypesIntensity.inch_hr),
]


@pytest.mark.parametrize(
    "initial_value, initial_unit, expected_value, target_unit",
    TEST_INTENSITY_CONVERSIONS,
)
def test_UnitFullIntensity_convert(
    initial_value, initial_unit, expected_value, target_unit
):
    _perform_conversion_test(
        UnitfulIntensity, initial_value, initial_unit, expected_value, target_unit
    )


def test_UnitFullIntensity_validator():
    with pytest.raises(ValueError):
        UnitfulIntensity(-1.0, UnitTypesIntensity.inch_hr)


TEST_LENGTH_CONVERSIONS = [
    (1000, UnitTypesLength.millimeters, 100, UnitTypesLength.centimeters),
    (1000, UnitTypesLength.millimeters, 1, UnitTypesLength.meters),
    (1000, UnitTypesLength.millimeters, 3.28084, UnitTypesLength.feet),
    (1000, UnitTypesLength.millimeters, 39.3701, UnitTypesLength.inch),
    (1000, UnitTypesLength.millimeters, 0.000621371, UnitTypesLength.miles),
    (100, UnitTypesLength.centimeters, 1000, UnitTypesLength.millimeters),
    (100, UnitTypesLength.centimeters, 100, UnitTypesLength.centimeters),
    (100, UnitTypesLength.centimeters, 3.28084, UnitTypesLength.feet),
    (100, UnitTypesLength.centimeters, 39.3701, UnitTypesLength.inch),
    (100, UnitTypesLength.centimeters, 0.000621371, UnitTypesLength.miles),
    (1, UnitTypesLength.meters, 1000, UnitTypesLength.millimeters),
    (1, UnitTypesLength.meters, 100, UnitTypesLength.centimeters),
    (1, UnitTypesLength.meters, 3.28084, UnitTypesLength.feet),
    (1, UnitTypesLength.meters, 39.3701, UnitTypesLength.inch),
    (1, UnitTypesLength.meters, 0.000621371, UnitTypesLength.miles),
    (1, UnitTypesLength.inch, 0.0254, UnitTypesLength.meters),
    (1, UnitTypesLength.inch, 2.54, UnitTypesLength.centimeters),
    (1, UnitTypesLength.inch, 25.4, UnitTypesLength.millimeters),
    (1, UnitTypesLength.inch, 1 / 12, UnitTypesLength.feet),
    (1, UnitTypesLength.inch, 1.5783e-5, UnitTypesLength.miles),
    (1, UnitTypesLength.feet, 0.3048, UnitTypesLength.meters),
    (1, UnitTypesLength.feet, 30.48, UnitTypesLength.centimeters),
    (1, UnitTypesLength.feet, 304.8, UnitTypesLength.millimeters),
    (1, UnitTypesLength.feet, 12, UnitTypesLength.inch),
    (1, UnitTypesLength.feet, 0.000189394, UnitTypesLength.miles),
    (1, UnitTypesLength.miles, 1609.344, UnitTypesLength.meters),
    (1, UnitTypesLength.miles, 160934.4, UnitTypesLength.centimeters),
    (1, UnitTypesLength.miles, 1609344, UnitTypesLength.millimeters),
    (1, UnitTypesLength.miles, 5280, UnitTypesLength.feet),
    (1, UnitTypesLength.miles, 63360, UnitTypesLength.inch),
]


@pytest.mark.parametrize(
    "initial_value, initial_unit, expected_value, target_unit", TEST_LENGTH_CONVERSIONS
)
def test_UnitFullLength_convert(
    initial_value, initial_unit, expected_value, target_unit
):
    _perform_conversion_test(
        UnitfulLength, initial_value, initial_unit, expected_value, target_unit
    )


# The tests below here test behaviour that is the same for all ValueUnitPairs, so we only need to test one of them.
TEST_INITIALIZE_ENTRIES = [
    (1, UnitTypesLength.meters),
    (1, UnitTypesLength.centimeters),
    (1, UnitTypesLength.millimeters),
    (1, UnitTypesLength.feet),
    (1, UnitTypesLength.inch),
    (1, UnitTypesLength.miles),
]


@pytest.mark.parametrize("value, units", TEST_INITIALIZE_ENTRIES)
def test_UnitFullValue_initialization(value, units):
    """This is the same for all valueunitpairs, so we only need to test one of them."""
    vup = UnitfulLength(value, units)
    assert vup.value == float(value), f"Failed value: {vup}"
    assert vup.units == units, f"Failed units: {vup}"
    assert str(vup) == f"{float(value)} {units.value}", f"Failed string: {vup}"


TEST_EQUALITY_ENTRIES = [
    (1, UnitTypesLength.meters, 100, UnitTypesLength.centimeters, True),
    (1, UnitTypesLength.meters, 1, UnitTypesLength.meters, True),
    (2, UnitTypesLength.meters, 200, UnitTypesLength.centimeters, True),
    (3, UnitTypesLength.meters, 3, UnitTypesLength.meters, True),
    (0, UnitTypesLength.meters, 0, UnitTypesLength.centimeters, True),
    (0, UnitTypesLength.meters, 0, UnitTypesLength.meters, True),
    (0, UnitTypesLength.meters, 0, UnitTypesLength.miles, True),
    (1, UnitTypesLength.feet, 12, UnitTypesLength.inch, True),
    (2, UnitTypesLength.feet, 24, UnitTypesLength.inch, True),
    (0, UnitTypesLength.feet, 0, UnitTypesLength.inch, True),
    (1, UnitTypesLength.miles, 1609.34, UnitTypesLength.meters, True),
    (2, UnitTypesLength.miles, 3218.68, UnitTypesLength.meters, True),
    (0, UnitTypesLength.miles, 0, UnitTypesLength.meters, True),
    (1, UnitTypesLength.meters, 1, UnitTypesLength.miles, False),
    (2, UnitTypesLength.meters, 2, UnitTypesLength.miles, False),
    (1, UnitTypesLength.meters, 102, UnitTypesLength.centimeters, False),
    (1, UnitTypesLength.meters, 98, UnitTypesLength.centimeters, False),
    (1, UnitTypesLength.feet, 13, UnitTypesLength.inch, False),
    (1, UnitTypesLength.feet, 11, UnitTypesLength.inch, False),
    (1, UnitTypesLength.miles, 1590, UnitTypesLength.meters, False),
    (1, UnitTypesLength.miles, 1630, UnitTypesLength.meters, False),
]


@pytest.mark.parametrize(
    "value_a, unit_a, value_b, unit_b, expected_result", TEST_EQUALITY_ENTRIES
)
def test_UnitFullValue_equality(value_a, unit_a, value_b, unit_b, expected_result):
    """
    The tests for ==, > and < are the same for all ValueUnitPairs and only have different results due to convert().
    If you add a new ValueUnitPair, you should only add a test for the convert function.
    """
    length_a = UnitfulLength(value_a, unit_a)
    length_b = UnitfulLength(value_b, unit_b)

    assert (
        length_a == length_b
    ) == expected_result, f"Failed equality: {length_a} and {length_b}"


TEST_LESSTHAN_ENTRIES = [
    (999, UnitTypesLength.millimeters, 1, UnitTypesLength.meters, True),
    (1, UnitTypesLength.centimeters, 2, UnitTypesLength.centimeters, True),
    (100, UnitTypesLength.centimeters, 1.1, UnitTypesLength.meters, True),
    (1, UnitTypesLength.meters, 1001, UnitTypesLength.millimeters, True),
    (1, UnitTypesLength.meters, 101, UnitTypesLength.centimeters, True),
    (1, UnitTypesLength.feet, 1, UnitTypesLength.meters, True),
    (11, UnitTypesLength.inch, 1, UnitTypesLength.feet, True),
    (1, UnitTypesLength.miles, 1610, UnitTypesLength.meters, True),
    (1, UnitTypesLength.inch, 2.54, UnitTypesLength.centimeters, False),
    (1000, UnitTypesLength.millimeters, 1, UnitTypesLength.meters, False),
    (1, UnitTypesLength.miles, 1609, UnitTypesLength.meters, False),
    (1, UnitTypesLength.feet, 13, UnitTypesLength.inch, True),
    (100, UnitTypesLength.centimeters, 1, UnitTypesLength.meters, False),
    (1, UnitTypesLength.meters, 100, UnitTypesLength.centimeters, False),
]


@pytest.mark.parametrize(
    "value_a, unit_a, value_b, unit_b, expected_result", TEST_LESSTHAN_ENTRIES
)
def test_UnitFullValue_less_than(value_a, unit_a, value_b, unit_b, expected_result):
    """
    The tests for ==, > and < are the same for all ValueUnitPairs and only have different results due to convert().
    If you add a new ValueUnitPair, you should only add a test for the convert function.
    """
    length_a = UnitfulLength(value_a, unit_a)
    length_b = UnitfulLength(value_b, unit_b)
    assert (
        length_a < length_b
    ) is expected_result, f"Failed less than: {length_a} and {length_b}. {length_a} {length_b.convert(length_a.units)}"


TEST_GREATERTHAN_ENTRIES = [
    (2, UnitTypesLength.centimeters, 1, UnitTypesLength.centimeters, True),
    (1001, UnitTypesLength.millimeters, 1, UnitTypesLength.meters, True),
    (3, UnitTypesLength.feet, 1, UnitTypesLength.meters, False),
    (2, UnitTypesLength.miles, 3000, UnitTypesLength.meters, True),
]


@pytest.mark.parametrize(
    "value_a, unit_a, value_b, unit_b, expected_result", TEST_GREATERTHAN_ENTRIES
)
def test_UnitFullValue_greater_than(value_a, unit_a, value_b, unit_b, expected_result):
    """
    The tests for ==, > and < are the same for all ValueUnitPairs and only have different results due to convert().
    If you add a new ValueUnitPair, you should only add a test for the convert function.
    """
    length_a = UnitfulLength(value_a, unit_a)
    length_b = UnitfulLength(value_b, unit_b)
    assert (
        length_a > length_b
    ) == expected_result, f"Failed greater than: {length_a} and {length_b}. Result {(length_a > length_b)}"


TEST_RAISE_TYPEERRORS = [
    ("inch"),
    (2),
    (3.0),
    (UnitfulIntensity(1.0, UnitTypesIntensity.mm_hr)),
    (UnitfulTime(1.0, UnitTypesTime.seconds)),
]
BASE_VUP = UnitfulLength(1.0, UnitTypesLength.meters)
TEST_OPERATIONS = [
    lambda x: BASE_VUP - x,
    lambda x: BASE_VUP + x,
    lambda x: BASE_VUP == x,
    lambda x: BASE_VUP * x,
    lambda x: BASE_VUP > x,
    lambda x: BASE_VUP >= x,
    lambda x: BASE_VUP < x,
    lambda x: BASE_VUP <= x,
]


@pytest.mark.parametrize("value", TEST_RAISE_TYPEERRORS)
@pytest.mark.parametrize("operation", TEST_OPERATIONS)
def test_UnitFullValue_invalid_other_raise_type_error(operation, value):
    with pytest.raises(TypeError):
        operation(value)
