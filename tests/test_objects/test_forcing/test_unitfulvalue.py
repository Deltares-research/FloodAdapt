import math

import pytest

from flood_adapt.objects.forcing import unit_system as us


def _perform_conversion_test(
    test_class, initial_value, initial_unit, expected_value, target_unit
):
    """
    Perform a unit conversion test for a given test_class.

    Note:
        The only tests you need to write for a new us.ValueUnitPair are:
            the conversion tests (this function)
            validator tests (if you have custom validators).

    Args:
        test_class: The class to test, e.g., us.UnitfulIntensity, us.UnitfulLength.
        initial_value (float): The initial value for the conversion.
        initial_unit: The initial unit of the value.
        expected_value (float): The expected value after conversion.
        target_unit: The target unit for the conversion.
    """
    assert issubclass(
        test_class, us.ValueUnitPair
    ), f"Only child classes of us.ValueUnitPairs can be tested by this function, not: {type(test_class).__name__}."

    instance = test_class(value=initial_value, units=initial_unit)
    converted = instance.convert(target_unit)

    assert (
        converted == pytest.approx(expected_value, rel=1e-2)
    ), f"{instance} Failed conversion: {initial_unit} to {target_unit}. Expected {expected_value}, got {converted}"


class TestUnitfulTime:
    TEST_TIME_CONVERSIONS = [
        (
            1,
            us.UnitTypesTime.days,
            24,
            us.UnitTypesTime.hours,
        ),
        (
            1,
            us.UnitTypesTime.days,
            24 * 60,
            us.UnitTypesTime.minutes,
        ),
        (
            1,
            us.UnitTypesTime.days,
            24 * 60 * 60,
            us.UnitTypesTime.seconds,
        ),
        (1, us.UnitTypesTime.hours, 1 / 24, us.UnitTypesTime.days),
        (1, us.UnitTypesTime.hours, 60, us.UnitTypesTime.minutes),
        (1, us.UnitTypesTime.hours, 60 * 60, us.UnitTypesTime.seconds),
        (1, us.UnitTypesTime.minutes, 1 / 60 / 24, us.UnitTypesTime.days),
        (1, us.UnitTypesTime.minutes, 1 / 60, us.UnitTypesTime.hours),
        (1, us.UnitTypesTime.minutes, 60, us.UnitTypesTime.seconds),
        (1, us.UnitTypesTime.seconds, 1 / 60 / 60 / 24, us.UnitTypesTime.days),
        (1, us.UnitTypesTime.seconds, 1 / 60 / 60, us.UnitTypesTime.hours),
        (1, us.UnitTypesTime.seconds, 1 / 60, us.UnitTypesTime.minutes),
    ]

    @pytest.mark.parametrize(
        "initial_value, initial_unit, expected_value, target_unit",
        TEST_TIME_CONVERSIONS,
    )
    def test_UnitFullTime_convert(
        self, initial_value, initial_unit, expected_value, target_unit
    ):
        _perform_conversion_test(
            us.UnitfulTime, initial_value, initial_unit, expected_value, target_unit
        )

    @pytest.mark.parametrize(
        "input_value, input_unit, expected_value",
        [
            (4, us.UnitTypesTime.days, 4 * 24 * 60 * 60),
            (10, us.UnitTypesTime.hours, 10 * 60 * 60),
            (5, us.UnitTypesTime.minutes, 5 * 60),
            (600, us.UnitTypesTime.seconds, 600),
        ],
    )
    def test_UnitfulTime_to_timedelta(self, input_value, input_unit, expected_value):
        time = us.UnitfulTime(value=input_value, units=input_unit)
        assert time.to_timedelta().total_seconds() == expected_value


class TestUnitfulIntensity:
    TEST_INTENSITY_CONVERSIONS = [
        (
            1,
            us.UnitTypesIntensity.mm_hr,
            1 / 25.39544832,
            us.UnitTypesIntensity.inch_hr,
        ),
        (180, us.UnitTypesIntensity.mm_hr, 7.08, us.UnitTypesIntensity.inch_hr),
        (1, us.UnitTypesIntensity.inch_hr, 25.39544832, us.UnitTypesIntensity.mm_hr),
        (4000, us.UnitTypesIntensity.inch_hr, 101581.8, us.UnitTypesIntensity.mm_hr),
        (180, us.UnitTypesIntensity.inch_hr, 4572, us.UnitTypesIntensity.mm_hr),
        (180, us.UnitTypesIntensity.mm_hr, 180, us.UnitTypesIntensity.mm_hr),
        (180, us.UnitTypesIntensity.inch_hr, 180, us.UnitTypesIntensity.inch_hr),
    ]

    @pytest.mark.parametrize(
        "initial_value, initial_unit, expected_value, target_unit",
        TEST_INTENSITY_CONVERSIONS,
    )
    def test_UnitFullIntensity_convert(
        self, initial_value, initial_unit, expected_value, target_unit
    ):
        _perform_conversion_test(
            us.UnitfulIntensity,
            initial_value,
            initial_unit,
            expected_value,
            target_unit,
        )

    def test_UnitFullIntensity_validator(self):
        with pytest.raises(ValueError):
            us.UnitfulIntensity(value=-1.0, units=us.UnitTypesIntensity.inch_hr)


class TestUnitfulDischarge:
    TEST_DISCHARGE_CONVERSIONS = [
        (
            1,
            us.UnitTypesDischarge.cms,
            35.314684921034,
            us.UnitTypesDischarge.cfs,
        ),
        (
            50,
            us.UnitTypesDischarge.cms,
            1765.7342460517,
            us.UnitTypesDischarge.cfs,
        ),
        (
            3531.4684921034,
            us.UnitTypesDischarge.cfs,
            100,
            us.UnitTypesDischarge.cms,
        ),
        (
            3920,
            us.UnitTypesDischarge.cfs,
            111,
            us.UnitTypesDischarge.cms,
        ),
    ]

    @pytest.mark.parametrize(
        "initial_value, initial_unit, expected_value, target_unit",
        TEST_DISCHARGE_CONVERSIONS,
    )
    def test_UnitFullIntensity_convert(
        self, initial_value, initial_unit, expected_value, target_unit
    ):
        _perform_conversion_test(
            us.UnitfulDischarge,
            initial_value,
            initial_unit,
            expected_value,
            target_unit,
        )

    def test_UnitFullIntensity_validator(self):
        with pytest.raises(ValueError):
            us.UnitfulDischarge(value=-1.0, units=us.UnitTypesDischarge.cms)


class TestUnitfulLength:
    TEST_LENGTH_CONVERSIONS = [
        (1000, us.UnitTypesLength.millimeters, 100, us.UnitTypesLength.centimeters),
        (1000, us.UnitTypesLength.millimeters, 1, us.UnitTypesLength.meters),
        (1000, us.UnitTypesLength.millimeters, 3.28084, us.UnitTypesLength.feet),
        (1000, us.UnitTypesLength.millimeters, 39.3701, us.UnitTypesLength.inch),
        (1000, us.UnitTypesLength.millimeters, 0.000621371, us.UnitTypesLength.miles),
        (100, us.UnitTypesLength.centimeters, 1000, us.UnitTypesLength.millimeters),
        (100, us.UnitTypesLength.centimeters, 100, us.UnitTypesLength.centimeters),
        (100, us.UnitTypesLength.centimeters, 3.28084, us.UnitTypesLength.feet),
        (100, us.UnitTypesLength.centimeters, 39.3701, us.UnitTypesLength.inch),
        (100, us.UnitTypesLength.centimeters, 0.000621371, us.UnitTypesLength.miles),
        (1, us.UnitTypesLength.meters, 1000, us.UnitTypesLength.millimeters),
        (1, us.UnitTypesLength.meters, 100, us.UnitTypesLength.centimeters),
        (1, us.UnitTypesLength.meters, 3.28084, us.UnitTypesLength.feet),
        (1, us.UnitTypesLength.meters, 39.3701, us.UnitTypesLength.inch),
        (1, us.UnitTypesLength.meters, 0.000621371, us.UnitTypesLength.miles),
        (1, us.UnitTypesLength.inch, 0.0254, us.UnitTypesLength.meters),
        (1, us.UnitTypesLength.inch, 2.54, us.UnitTypesLength.centimeters),
        (1, us.UnitTypesLength.inch, 25.4, us.UnitTypesLength.millimeters),
        (1, us.UnitTypesLength.inch, 1 / 12, us.UnitTypesLength.feet),
        (1, us.UnitTypesLength.inch, 1.5783e-5, us.UnitTypesLength.miles),
        (1, us.UnitTypesLength.feet, 0.3048, us.UnitTypesLength.meters),
        (1, us.UnitTypesLength.feet, 30.48, us.UnitTypesLength.centimeters),
        (1, us.UnitTypesLength.feet, 304.8, us.UnitTypesLength.millimeters),
        (1, us.UnitTypesLength.feet, 12, us.UnitTypesLength.inch),
        (1, us.UnitTypesLength.feet, 0.000189394, us.UnitTypesLength.miles),
        (1, us.UnitTypesLength.miles, 1609.344, us.UnitTypesLength.meters),
        (1, us.UnitTypesLength.miles, 160934.4, us.UnitTypesLength.centimeters),
        (1, us.UnitTypesLength.miles, 1609344, us.UnitTypesLength.millimeters),
        (1, us.UnitTypesLength.miles, 5280, us.UnitTypesLength.feet),
        (1, us.UnitTypesLength.miles, 63360, us.UnitTypesLength.inch),
    ]

    @pytest.mark.parametrize(
        "initial_value, initial_unit, expected_value, target_unit",
        TEST_LENGTH_CONVERSIONS,
    )
    def test_UnitFullLength_convert(
        self, initial_value, initial_unit, expected_value, target_unit
    ):
        _perform_conversion_test(
            us.UnitfulLength, initial_value, initial_unit, expected_value, target_unit
        )


class TestUnitfulHeight:
    def test_unitfulHeight_convertMToFeet_correct(self):
        # Assert
        length = us.UnitfulHeight(value=10, units=us.UnitTypesLength.meters)

        # Act
        converted_length = length.convert(us.UnitTypesLength.feet)

        # Assert
        assert round(converted_length, 4) == 32.8084

    def test_unitfulHeight_convertFeetToM_correct(self):
        # Assert
        length = us.UnitfulHeight(value=10, units=us.UnitTypesLength.feet)
        inverse_length = us.UnitfulHeight(value=10, units=us.UnitTypesLength.meters)

        # Act
        converted_length = length.convert(us.UnitTypesLength.meters)
        inverse_converted_length = inverse_length.convert(us.UnitTypesLength.feet)

        # Assert
        assert round(converted_length, 4) == 3.048
        assert round(inverse_converted_length, 4) == 32.8084

    def test_unitfulHeight_convertMToCM_correct(self):
        # Assert
        length = us.UnitfulHeight(value=10, units=us.UnitTypesLength.meters)

        # Act
        converted_length = length.convert(us.UnitTypesLength.centimeters)

        # Assert
        assert round(converted_length, 4) == 1000

    def test_unitfulHeight_convertCMToM_correct(self):
        # Assert
        length = us.UnitfulHeight(value=1000, units=us.UnitTypesLength.centimeters)

        # Act
        converted_length = length.convert(us.UnitTypesLength.meters)

        # Assert
        assert round(converted_length, 4) == 10

    def test_unitfulHeight_convertMToMM_correct(self):
        # Assert
        length = us.UnitfulHeight(value=10, units=us.UnitTypesLength.meters)

        # Act
        converted_length = length.convert(us.UnitTypesLength.millimeters)

        # Assert
        assert round(converted_length, 4) == 10000

    def test_unitfulHeight_convertMMToM_correct(self):
        # Assert
        length = us.UnitfulHeight(value=10000, units=us.UnitTypesLength.millimeters)

        # Act
        converted_length = length.convert(us.UnitTypesLength.meters)

        # Assert
        assert round(converted_length, 4) == 10

    def test_unitfulHeight_convertMToInches_correct(self):
        # Assert
        length = us.UnitfulHeight(value=10, units=us.UnitTypesLength.meters)

        # Act
        converted_length = length.convert(us.UnitTypesLength.inch)

        # Assert
        assert round(converted_length, 4) == 393.7008

    def test_unitfulHeight_convertInchesToM_correct(self):
        # Assert
        length = us.UnitfulHeight(value=1000, units=us.UnitTypesLength.inch)

        # Act
        converted_length = length.convert(us.UnitTypesLength.meters)

        # Assert
        assert round(converted_length, 4) == 25.4

    def test_unitfulHeight_convertMToMiles_correct(self):
        # Assert
        length = us.UnitfulHeight(value=10, units=us.UnitTypesLength.meters)

        # Act
        converted_length = length.convert(us.UnitTypesLength.miles)

        # Assert
        assert round(converted_length, 4) == 0.0062

    def test_unitfulHeight_convertMilesToM_correct(self):
        # Assert
        length = us.UnitfulHeight(value=1, units=us.UnitTypesLength.miles)

        # Act
        converted_length = length.convert(us.UnitTypesLength.meters)

        # Assert
        assert round(converted_length, 4) == 1609.344

    def test_unitfulHeight_setValue_negativeValue(self):
        # Assert
        with pytest.raises(ValueError):
            us.UnitfulHeight(value=-10, units=us.UnitTypesLength.meters)

    def test_unitfulHeight_setUnit_invalidUnits(self):
        # Assert
        with pytest.raises(ValueError) as excinfo:
            us.UnitfulHeight(value=10, units="invalid_units")

        errors = excinfo.value.errors()
        assert len(errors) == 1, "Expected one error"
        error = errors[0]
        assert error["loc"] == ("units",)
        assert "Input should be" in error["msg"]


class TestUnitfulArea:
    def test_unitfulArea_convertM2ToCM2_correct(self):
        # Assert
        area = us.UnitfulArea(value=10, units=us.UnitTypesArea.m2)

        # Act
        converted_area = area.convert(us.UnitTypesArea.cm2)

        # Assert
        assert round(converted_area, 4) == 100000

    def test_unitfulArea_convertCM2ToM2_correct(self):
        # Assert
        area = us.UnitfulArea(value=100000, units=us.UnitTypesArea.cm2)

        # Act
        converted_area = area.convert(us.UnitTypesArea.m2)

        # Assert
        assert round(converted_area, 4) == 10

    def test_unitfulArea_convertM2ToMM2_correct(self):
        # Assert
        area = us.UnitfulArea(value=10, units=us.UnitTypesArea.m2)

        # Act
        converted_area = area.convert(us.UnitTypesArea.mm2)

        # Assert
        assert round(converted_area, 4) == 10000000

    def test_unitfulArea_convertMM2ToM2_correct(self):
        # Assert
        area = us.UnitfulArea(value=10000000, units=us.UnitTypesArea.mm2)

        # Act
        converted_area = area.convert(us.UnitTypesArea.m2)

        # Assert
        assert round(converted_area, 4) == 10

    def test_unitfulArea_convertM2ToSF_correct(self):
        # Assert
        area = us.UnitfulArea(value=10, units=us.UnitTypesArea.m2)

        # Act
        converted_area = area.convert(us.UnitTypesArea.sf)

        # Assert
        assert round(converted_area, 4) == 107.64

    def test_unitfulArea_convertSFToM2_correct(self):
        # Assert
        area = us.UnitfulArea(value=100, units=us.UnitTypesArea.sf)

        # Act
        converted_area = area.convert(us.UnitTypesArea.m2)

        # Assert
        assert round(converted_area, 4) == 9.2902

    def test_unitfulArea_setValue_negativeValue(self):
        # Assert
        with pytest.raises(ValueError):
            us.UnitfulArea(value=-10, units=us.UnitTypesArea.m2)

    def test_unitfulArea_setUnit_invalidUnits(self):
        # Assert
        with pytest.raises(ValueError) as excinfo:
            us.UnitfulArea(value=10, units="invalid_units")

        errors = excinfo.value.errors()
        assert len(errors) == 1, "Expected one error"
        error = errors[0]
        assert error["loc"] == ("units",)
        assert "Input should be" in error["msg"]


class TestUnitfulVolume:
    def test_unitfulVolume_convertM3ToCF_correct(self):
        # Assert
        volume = us.UnitfulVolume(value=10, units=us.UnitTypesVolume.m3)

        # Act
        converted_volume = volume.convert(us.UnitTypesVolume.cf)

        # Assert
        pytest.approx(converted_volume, 4) == 353.1466

    def test_unitfulVolume_convertCFToM3_correct(self):
        # Assert
        volume = us.UnitfulVolume(value=100, units=us.UnitTypesVolume.cf)

        # Act
        converted_volume = volume.convert(us.UnitTypesVolume.m3)

        # Assert
        assert round(converted_volume, 4) == 2.8317

    def test_unitfulVolume_setValue_negativeValue(self):
        # Assert
        with pytest.raises(ValueError):
            us.UnitfulVolume(value=-10, units=us.UnitTypesVolume.m3)

    def test_unitfulVolume_setUnit_invalidUnits(self):
        # Assert
        with pytest.raises(ValueError) as excinfo:
            us.UnitfulVolume(value=10, units="invalid_units")

        errors = excinfo.value.errors()
        assert len(errors) == 1, "Expected one error"
        error = errors[0]
        assert error["loc"] == ("units",)
        assert "Input should be" in error["msg"]


class TestValueUnitPair:
    """The tests below here test behaviour that is the same for all us.ValueUnitPairs, so we only need to test one of them."""

    TEST_INITIALIZE_ENTRIES = [
        (1, us.UnitTypesLength.meters),
        (1, us.UnitTypesLength.centimeters),
        (1, us.UnitTypesLength.millimeters),
        (1, us.UnitTypesLength.feet),
        (1, us.UnitTypesLength.inch),
        (1, us.UnitTypesLength.miles),
    ]

    @pytest.mark.parametrize("value, units", TEST_INITIALIZE_ENTRIES)
    def test_UnitFullValue_initialization(
        self, value: float, units: us.UnitTypesLength
    ):
        """Equal for all us.ValueUnitPairs, so we only need to test one of them."""
        vup = us.UnitfulLength(value=value, units=units)
        assert vup.value == float(value), f"Failed value: {vup}"
        assert vup.units == units, f"Failed units: {vup}"
        assert str(vup) == f"{float(value):.2f} {units.value}", f"Failed string: {vup}"

    TEST_EQUALITY_ENTRIES = [
        (1, us.UnitTypesLength.meters, 100, us.UnitTypesLength.centimeters, True),
        (1, us.UnitTypesLength.meters, 1, us.UnitTypesLength.meters, True),
        (2, us.UnitTypesLength.meters, 200, us.UnitTypesLength.centimeters, True),
        (3, us.UnitTypesLength.meters, 3, us.UnitTypesLength.meters, True),
        (0, us.UnitTypesLength.meters, 0, us.UnitTypesLength.centimeters, True),
        (0, us.UnitTypesLength.meters, 0, us.UnitTypesLength.meters, True),
        (0, us.UnitTypesLength.meters, 0, us.UnitTypesLength.miles, True),
        (1, us.UnitTypesLength.feet, 12, us.UnitTypesLength.inch, True),
        (2, us.UnitTypesLength.feet, 24, us.UnitTypesLength.inch, True),
        (0, us.UnitTypesLength.feet, 0, us.UnitTypesLength.inch, True),
        (1, us.UnitTypesLength.miles, 1609.34, us.UnitTypesLength.meters, True),
        (2, us.UnitTypesLength.miles, 3218.68, us.UnitTypesLength.meters, True),
        (0, us.UnitTypesLength.miles, 0, us.UnitTypesLength.meters, True),
        (1, us.UnitTypesLength.meters, 1, us.UnitTypesLength.miles, False),
        (2, us.UnitTypesLength.meters, 2, us.UnitTypesLength.miles, False),
        (1, us.UnitTypesLength.meters, 102, us.UnitTypesLength.centimeters, False),
        (1, us.UnitTypesLength.meters, 98, us.UnitTypesLength.centimeters, False),
        (1, us.UnitTypesLength.feet, 13, us.UnitTypesLength.inch, False),
        (1, us.UnitTypesLength.feet, 11, us.UnitTypesLength.inch, False),
        (1, us.UnitTypesLength.miles, 1590, us.UnitTypesLength.meters, False),
        (1, us.UnitTypesLength.miles, 1630, us.UnitTypesLength.meters, False),
    ]

    @pytest.mark.parametrize(
        "value_a, unit_a, value_b, unit_b, expected_result", TEST_EQUALITY_ENTRIES
    )
    def test_UnitFullValue_equality(
        self, value_a, unit_a, value_b, unit_b, expected_result
    ):
        """
        The tests for ==, > and < are the same for all us.ValueUnitPairs and only have different results due to convert().

        If you add a new us.ValueUnitPair, you should only add a test for the convert function.
        """
        length_a = us.UnitfulLength(value=value_a, units=unit_a)
        length_b = us.UnitfulLength(value=value_b, units=unit_b)

        assert (
            length_a == length_b
        ) == expected_result, f"Failed equality: {length_a} and {length_b}"

    TEST_LESSTHAN_ENTRIES = [
        (999, us.UnitTypesLength.millimeters, 1, us.UnitTypesLength.meters, True),
        (1, us.UnitTypesLength.centimeters, 2, us.UnitTypesLength.centimeters, True),
        (100, us.UnitTypesLength.centimeters, 1.1, us.UnitTypesLength.meters, True),
        (1, us.UnitTypesLength.meters, 1001, us.UnitTypesLength.millimeters, True),
        (1, us.UnitTypesLength.meters, 101, us.UnitTypesLength.centimeters, True),
        (1, us.UnitTypesLength.feet, 1, us.UnitTypesLength.meters, True),
        (11, us.UnitTypesLength.inch, 1, us.UnitTypesLength.feet, True),
        (1, us.UnitTypesLength.miles, 1610, us.UnitTypesLength.meters, True),
        (1, us.UnitTypesLength.inch, 2.54, us.UnitTypesLength.centimeters, False),
        (1000, us.UnitTypesLength.millimeters, 1, us.UnitTypesLength.meters, False),
        (1, us.UnitTypesLength.miles, 1609, us.UnitTypesLength.meters, False),
        (1, us.UnitTypesLength.feet, 13, us.UnitTypesLength.inch, True),
        (100, us.UnitTypesLength.centimeters, 1, us.UnitTypesLength.meters, False),
        (1, us.UnitTypesLength.meters, 100, us.UnitTypesLength.centimeters, False),
    ]

    @pytest.mark.parametrize(
        "value_a, unit_a, value_b, unit_b, expected_result", TEST_LESSTHAN_ENTRIES
    )
    def test_UnitFullValue_less_than(
        self, value_a, unit_a, value_b, unit_b, expected_result
    ):
        """
        The tests for ==, > and < are the same for all us.ValueUnitPairs and only have different results due to convert().

        If you add a new us.ValueUnitPair, you should only add a test for the convert function.
        """
        length_a = us.UnitfulLength(value=value_a, units=unit_a)
        length_b = us.UnitfulLength(value=value_b, units=unit_b)
        assert (
            (length_a < length_b) is expected_result
        ), f"Failed less than: {length_a} and {length_b}. {length_a} {length_b.convert(length_a.units)}"

    TEST_GREATERTHAN_ENTRIES = [
        (2, us.UnitTypesLength.centimeters, 1, us.UnitTypesLength.centimeters, True),
        (1001, us.UnitTypesLength.millimeters, 1, us.UnitTypesLength.meters, True),
        (3, us.UnitTypesLength.feet, 1, us.UnitTypesLength.meters, False),
        (2, us.UnitTypesLength.miles, 3000, us.UnitTypesLength.meters, True),
    ]

    @pytest.mark.parametrize(
        "value_a, unit_a, value_b, unit_b, expected_result", TEST_GREATERTHAN_ENTRIES
    )
    def test_UnitFullValue_greater_than(
        self, value_a, unit_a, value_b, unit_b, expected_result
    ):
        """
        The tests for ==, > and < are the same for all us.ValueUnitPairs and only have different results due to convert().

        If you add a new us.ValueUnitPair, you should only add a test for the convert function.
        """
        length_a = us.UnitfulLength(value=value_a, units=unit_a)
        length_b = us.UnitfulLength(value=value_b, units=unit_b)
        assert (
            (length_a > length_b) == expected_result
        ), f"Failed greater than: {length_a} and {length_b}. Result {(length_a > length_b)}"

    TEST_COMPARE_RAISE_TYPEERRORS = [
        ("inch"),
        (2),
        (3.0),
        us.UnitfulTime(value=1, units=us.UnitTypesTime.days),
        us.UnitfulIntensity(value=1, units=us.UnitTypesIntensity.mm_hr),
    ]
    TEST_COMPARE_OPERATIONS = [
        (
            lambda x: us.UnitfulLength(value=1.0, units=us.UnitTypesLength.meters) - x,
            "subtraction",
        ),
        (
            lambda x: us.UnitfulLength(value=1.0, units=us.UnitTypesLength.meters) + x,
            "addition",
        ),
        (
            lambda x: us.UnitfulLength(value=1.0, units=us.UnitTypesLength.meters) == x,
            "equals",
        ),
        (
            lambda x: us.UnitfulLength(value=1.0, units=us.UnitTypesLength.meters) != x,
            "not equals",
        ),
        (
            lambda x: us.UnitfulLength(value=1.0, units=us.UnitTypesLength.meters) > x,
            "greater than",
        ),
        (
            lambda x: us.UnitfulLength(value=1.0, units=us.UnitTypesLength.meters) >= x,
            "less than or equal",
        ),
        (
            lambda x: us.UnitfulLength(value=1.0, units=us.UnitTypesLength.meters) < x,
            "less than",
        ),
        (
            lambda x: us.UnitfulLength(value=1.0, units=us.UnitTypesLength.meters) <= x,
            "greater than or equal",
        ),
    ]

    @pytest.mark.parametrize("value", TEST_COMPARE_RAISE_TYPEERRORS)
    @pytest.mark.parametrize("operation", TEST_COMPARE_OPERATIONS)
    def test_UnitFullValue_compare_invalid_other_raise_type_error(
        self, operation, value
    ):
        operation, name = operation
        with pytest.raises(TypeError):
            operation(value)

    @pytest.mark.parametrize("scalar", [2, 0.5])
    def test_UnitFullValue_multiplication_scalar(self, scalar):
        vup = us.UnitfulLength(value=1, units=us.UnitTypesLength.meters)
        result = vup * scalar
        assert result.value == 1 * scalar
        assert result.units == us.UnitTypesLength.meters

    @pytest.mark.parametrize("scalar", [2, 0.5])
    def test_UnitFullValue_truedivision_scalar(self, scalar):
        vup = us.UnitfulLength(value=1, units=us.UnitTypesLength.meters)
        result = vup / scalar
        assert result.value == 1 / scalar
        assert result.units == us.UnitTypesLength.meters

    @pytest.mark.parametrize(
        "value, unit, expected_value",
        [
            (2, us.UnitTypesLength.meters, 0.5),
            (1, us.UnitTypesLength.centimeters, 100),
            (10, us.UnitTypesLength.meters, 0.1),
        ],
    )
    def test_UnitFullValue_truedivision_vup(self, value, unit, expected_value):
        vup1 = us.UnitfulLength(value=1, units=us.UnitTypesLength.meters)
        vup2 = us.UnitfulLength(value=value, units=unit)
        result = vup1 / vup2
        assert isinstance(result, float)
        assert math.isclose(
            result, expected_value
        ), f"True division with unit conversion failed. Expected: {expected_value}, got: {result}"


@pytest.mark.parametrize(
    "unit_instance",
    [
        us.UnitfulLength(value=1, units=us.UnitTypesLength.meters),
        us.UnitfulIntensity(value=1, units=us.UnitTypesIntensity.mm_hr),
        us.UnitfulDischarge(value=1, units=us.UnitTypesDischarge.cms),
        us.UnitfulTime(value=1, units=us.UnitTypesTime.days),
        us.UnitfulArea(value=1, units=us.UnitTypesArea.m2),
        us.UnitfulVolume(value=1, units=us.UnitTypesVolume.m3),
    ],
)
def test_model_dump_doesnt_contain_CONVERSION_FACTORS(unit_instance: us.ValueUnitPair):
    """Test that the conversion factors are not included in the model dump."""
    dump = unit_instance.model_dump()
    assert dump == {"value": unit_instance.value, "units": unit_instance.units.value}
    assert "_CONVERSION_FACTORS" not in dump
    assert "_DEFAULT_UNIT" not in dump
