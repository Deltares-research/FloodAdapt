import math

import pytest

from flood_adapt.object_model.io.unitfulvalue import (
    IUnitFullValue,
    UnitfulArea,
    UnitfulHeight,
    UnitfulIntensity,
    UnitfulLength,
    UnitfulTime,
    UnitfulVolume,
    UnitTypesArea,
    UnitTypesIntensity,
    UnitTypesLength,
    UnitTypesTime,
    UnitTypesVolume,
)


def _perform_conversion_test(
    test_class, initial_value, initial_unit, expected_value, target_unit
):
    """
    Perform a unit conversion test for a given test_class.

    Note:
        The only tests you need to write for a new IUnitFullValue are:
            the conversion tests (this function)
            validator tests (if you have custom validators).

    Args:
        test_class: The class to test, e.g., UnitfulIntensity, UnitfulLength.
        initial_value (float): The initial value for the conversion.
        initial_unit: The initial unit of the value.
        expected_value (float): The expected value after conversion.
        target_unit: The target unit for the conversion.
    """
    assert issubclass(
        test_class, IUnitFullValue
    ), f"Only child classes of IUnitFullValues can be tested by this function, not: {type(test_class).__name__}."

    instance = test_class(initial_value, initial_unit)
    converted = instance.convert(target_unit)

    assert converted == pytest.approx(
        expected_value, rel=1e-2
    ), f"{instance} Failed conversion: {initial_unit} to {target_unit}. Expected {expected_value}, got {converted}"


class TestUnitfulTime:
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
        "initial_value, initial_unit, expected_value, target_unit",
        TEST_TIME_CONVERSIONS,
    )
    def test_UnitFullTime_convert(
        self, initial_value, initial_unit, expected_value, target_unit
    ):
        _perform_conversion_test(
            UnitfulTime, initial_value, initial_unit, expected_value, target_unit
        )

    @pytest.mark.parametrize(
        "input_value, input_unit, expected_value",
        [
            (4, UnitTypesTime.days, 4 * 24 * 60 * 60),
            (10, UnitTypesTime.hours, 10 * 60 * 60),
            (5, UnitTypesTime.minutes, 5 * 60),
            (600, UnitTypesTime.seconds, 600),
        ],
    )
    def test_UnitfulTime_to_timedelta(self, input_value, input_unit, expected_value):
        time = UnitfulTime(input_value, input_unit)
        assert time.to_timedelta().total_seconds() == expected_value


class TestUnitfulIntensity:

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
        self, initial_value, initial_unit, expected_value, target_unit
    ):
        _perform_conversion_test(
            UnitfulIntensity, initial_value, initial_unit, expected_value, target_unit
        )

    def test_UnitFullIntensity_validator(self):
        with pytest.raises(ValueError):
            UnitfulIntensity(-1.0, UnitTypesIntensity.inch_hr)


class TestUnitfulLength:
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
        "initial_value, initial_unit, expected_value, target_unit",
        TEST_LENGTH_CONVERSIONS,
    )
    def test_UnitFullLength_convert(
        self, initial_value, initial_unit, expected_value, target_unit
    ):
        _perform_conversion_test(
            UnitfulLength, initial_value, initial_unit, expected_value, target_unit
        )


class TestUnitfulHeight:
    def test_unitfulHeight_convertMToFeet_correct(self):
        # Assert
        length = UnitfulHeight(value=10, units=UnitTypesLength.meters)

        # Act
        converted_length = length.convert(UnitTypesLength.feet)

        # Assert
        assert round(converted_length, 4) == 32.8084

    def test_unitfulHeight_convertFeetToM_correct(self):
        # Assert
        length = UnitfulHeight(value=10, units=UnitTypesLength.feet)
        inverse_length = UnitfulHeight(value=10, units=UnitTypesLength.meters)

        # Act
        converted_length = length.convert(UnitTypesLength.meters)
        inverse_converted_length = inverse_length.convert(UnitTypesLength.feet)

        # Assert
        assert round(converted_length, 4) == 3.048
        assert round(inverse_converted_length, 4) == 32.8084

    def test_unitfulHeight_convertMToCM_correct(self):
        # Assert
        length = UnitfulHeight(value=10, units=UnitTypesLength.meters)

        # Act
        converted_length = length.convert(UnitTypesLength.centimeters)

        # Assert
        assert round(converted_length, 4) == 1000

    def test_unitfulHeight_convertCMToM_correct(self):
        # Assert
        length = UnitfulHeight(value=1000, units=UnitTypesLength.centimeters)

        # Act
        converted_length = length.convert(UnitTypesLength.meters)

        # Assert
        assert round(converted_length, 4) == 10

    def test_unitfulHeight_convertMToMM_correct(self):
        # Assert
        length = UnitfulHeight(value=10, units=UnitTypesLength.meters)

        # Act
        converted_length = length.convert(UnitTypesLength.millimeters)

        # Assert
        assert round(converted_length, 4) == 10000

    def test_unitfulHeight_convertMMToM_correct(self):
        # Assert
        length = UnitfulHeight(value=10000, units=UnitTypesLength.millimeters)

        # Act
        converted_length = length.convert(UnitTypesLength.meters)

        # Assert
        assert round(converted_length, 4) == 10

    def test_unitfulHeight_convertMToInches_correct(self):
        # Assert
        length = UnitfulHeight(value=10, units=UnitTypesLength.meters)

        # Act
        converted_length = length.convert(UnitTypesLength.inch)

        # Assert
        assert round(converted_length, 4) == 393.7008

    def test_unitfulHeight_convertInchesToM_correct(self):
        # Assert
        length = UnitfulHeight(value=1000, units=UnitTypesLength.inch)

        # Act
        converted_length = length.convert(UnitTypesLength.meters)

        # Assert
        assert round(converted_length, 4) == 25.4

    def test_unitfulHeight_convertMToMiles_correct(self):
        # Assert
        length = UnitfulHeight(value=10, units=UnitTypesLength.meters)

        # Act
        converted_length = length.convert(UnitTypesLength.miles)

        # Assert
        assert round(converted_length, 4) == 0.0062

    def test_unitfulHeight_convertMilesToM_correct(self):
        # Assert
        length = UnitfulHeight(value=1, units=UnitTypesLength.miles)

        # Act
        converted_length = length.convert(UnitTypesLength.meters)

        # Assert
        assert round(converted_length, 4) == 1609.344

    def test_unitfulHeight_setValue_negativeValue(self):
        # Assert
        with pytest.raises(ValueError) as excinfo:
            UnitfulHeight(value=-10, units=UnitTypesLength.meters)
        assert "UnitfulHeight\nvalue\n  Input should be greater than 0" in str(
            excinfo.value
        )

    def test_unitfulHeight_setValue_zeroValue(self):
        # Assert
        with pytest.raises(ValueError) as excinfo:
            UnitfulHeight(value=0, units=UnitTypesLength.meters)
        assert "UnitfulHeight\nvalue\n  Input should be greater than 0" in str(
            excinfo.value
        )

    def test_unitfulHeight_setUnit_invalidUnits(self):
        # Assert
        with pytest.raises(ValueError) as excinfo:
            UnitfulHeight(value=10, units="invalid_units")
        assert "UnitfulHeight\nunits\n  Input should be " in str(excinfo.value)


class TestUnitfulArea:
    def test_unitfulArea_convertM2ToCM2_correct(self):
        # Assert
        area = UnitfulArea(value=10, units=UnitTypesArea.m2)

        # Act
        converted_area = area.convert(UnitTypesArea.cm2)

        # Assert
        assert round(converted_area, 4) == 100000

    def test_unitfulArea_convertCM2ToM2_correct(self):
        # Assert
        area = UnitfulArea(value=100000, units=UnitTypesArea.cm2)

        # Act
        converted_area = area.convert(UnitTypesArea.m2)

        # Assert
        assert round(converted_area, 4) == 10

    def test_unitfulArea_convertM2ToMM2_correct(self):
        # Assert
        area = UnitfulArea(value=10, units=UnitTypesArea.m2)

        # Act
        converted_area = area.convert(UnitTypesArea.mm2)

        # Assert
        assert round(converted_area, 4) == 10000000

    def test_unitfulArea_convertMM2ToM2_correct(self):
        # Assert
        area = UnitfulArea(value=10000000, units=UnitTypesArea.mm2)

        # Act
        converted_area = area.convert(UnitTypesArea.m2)

        # Assert
        assert round(converted_area, 4) == 10

    def test_unitfulArea_convertM2ToSF_correct(self):
        # Assert
        area = UnitfulArea(value=10, units=UnitTypesArea.m2)

        # Act
        converted_area = area.convert(UnitTypesArea.sf)

        # Assert
        assert round(converted_area, 4) == 107.64

    def test_unitfulArea_convertSFToM2_correct(self):
        # Assert
        area = UnitfulArea(value=100, units=UnitTypesArea.sf)

        # Act
        converted_area = area.convert(UnitTypesArea.m2)

        # Assert
        assert round(converted_area, 4) == 9.2902

    def test_unitfulArea_setValue_negativeValue(self):
        # Assert
        with pytest.raises(ValueError) as excinfo:
            UnitfulArea(value=-10, units=UnitTypesArea.m2)
        assert "UnitfulArea\nvalue\n  Input should be greater than 0" in str(
            excinfo.value
        )

    def test_unitfulArea_setValue_zeroValue(self):
        # Assert
        with pytest.raises(ValueError) as excinfo:
            UnitfulArea(value=0, units=UnitTypesArea.m2)
        assert "UnitfulArea\nvalue\n  Input should be greater than 0" in str(
            excinfo.value
        )

    def test_unitfulArea_setUnit_invalidUnits(self):
        # Assert
        with pytest.raises(ValueError) as excinfo:
            UnitfulArea(value=10, units="invalid_units")
        assert "UnitfulArea\nunits\n  Input should be " in str(excinfo.value)


class TestUnitfulVolume:
    def test_unitfulVolume_convertM3ToCF_correct(self):
        # Assert
        volume = UnitfulVolume(value=10, units=UnitTypesVolume.m3)

        # Act
        converted_volume = volume.convert(UnitTypesVolume.cf)

        # Assert
        pytest.approx(converted_volume, 4) == 353.1466

    def test_unitfulVolume_convertCFToM3_correct(self):
        # Assert
        volume = UnitfulVolume(value=100, units=UnitTypesVolume.cf)

        # Act
        converted_volume = volume.convert(UnitTypesVolume.m3)

        # Assert
        assert round(converted_volume, 4) == 2.8317

    def test_unitfulVolume_setValue_negativeValue(self):
        # Assert
        with pytest.raises(ValueError) as excinfo:
            UnitfulVolume(value=-10, units=UnitTypesVolume.m3)
        assert "UnitfulVolume\nvalue\n  Input should be greater than 0" in str(
            excinfo.value
        )

    def test_unitfulVolume_setValue_zeroValue(self):
        # Assert
        with pytest.raises(ValueError) as excinfo:
            UnitfulVolume(value=0, units=UnitTypesVolume.m3)
        assert "UnitfulVolume\nvalue\n  Input should be greater than 0" in str(
            excinfo.value
        )

    def test_unitfulVolume_setUnit_invalidUnits(self):
        # Assert
        with pytest.raises(ValueError) as excinfo:
            UnitfulVolume(value=10, units="invalid_units")
        assert "UnitfulVolume\nunits\n  Input should be " in str(excinfo.value)


class TestIUnitFullValue:
    """The tests below here test behaviour that is the same for all IUnitFullValues, so we only need to test one of them."""

    TEST_INITIALIZE_ENTRIES = [
        (1, UnitTypesLength.meters),
        (1, UnitTypesLength.centimeters),
        (1, UnitTypesLength.millimeters),
        (1, UnitTypesLength.feet),
        (1, UnitTypesLength.inch),
        (1, UnitTypesLength.miles),
    ]

    @pytest.mark.parametrize("value, units", TEST_INITIALIZE_ENTRIES)
    def test_UnitFullValue_initialization(self, value: float, units: UnitTypesLength):
        """Equal for all IUnitFullValues, so we only need to test one of them."""
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
    def test_UnitFullValue_equality(
        self, value_a, unit_a, value_b, unit_b, expected_result
    ):
        """
        The tests for ==, > and < are the same for all IUnitFullValues and only have different results due to convert().

        If you add a new IUnitFullValue, you should only add a test for the convert function.
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
    def test_UnitFullValue_less_than(
        self, value_a, unit_a, value_b, unit_b, expected_result
    ):
        """
        The tests for ==, > and < are the same for all IUnitFullValues and only have different results due to convert().

        If you add a new IUnitFullValue, you should only add a test for the convert function.
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
    def test_UnitFullValue_greater_than(
        self, value_a, unit_a, value_b, unit_b, expected_result
    ):
        """
        The tests for ==, > and < are the same for all IUnitFullValues and only have different results due to convert().

        If you add a new IUnitFullValue, you should only add a test for the convert function.
        """
        length_a = UnitfulLength(value_a, unit_a)
        length_b = UnitfulLength(value_b, unit_b)
        assert (
            length_a > length_b
        ) == expected_result, f"Failed greater than: {length_a} and {length_b}. Result {(length_a > length_b)}"

    TEST_COMPARE_RAISE_TYPEERRORS = [
        ("inch"),
        (2),
        (3.0),
        UnitfulTime(1, UnitTypesTime.days),
        UnitfulIntensity(1, UnitTypesIntensity.mm_hr),
    ]
    TEST_COMPARE_OPERATIONS = [
        (lambda x: UnitfulLength(1.0, UnitTypesLength.meters) - x, "subtraction"),
        (lambda x: UnitfulLength(1.0, UnitTypesLength.meters) + x, "addition"),
        (lambda x: UnitfulLength(1.0, UnitTypesLength.meters) == x, "equals"),
        (lambda x: UnitfulLength(1.0, UnitTypesLength.meters) != x, "not equals"),
        (lambda x: UnitfulLength(1.0, UnitTypesLength.meters) > x, "greater than"),
        (
            lambda x: UnitfulLength(1.0, UnitTypesLength.meters) >= x,
            "less than or equal",
        ),
        (lambda x: UnitfulLength(1.0, UnitTypesLength.meters) < x, "less than"),
        (
            lambda x: UnitfulLength(1.0, UnitTypesLength.meters) <= x,
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
            print(name)
            operation(value)

    @pytest.mark.parametrize("scalar", [2, 0.5])
    def test_UnitFullValue_multiplication_scalar(self, scalar):
        vup = UnitfulLength(1, UnitTypesLength.meters)
        result = vup * scalar
        assert result.value == 1 / scalar
        assert result.units == UnitTypesLength.meters

    @pytest.mark.parametrize("scalar", [2, 0.5])
    def test_UnitFullValue_truedivision_scalar(self, scalar):
        vup = UnitfulLength(1, UnitTypesLength.meters)
        result = vup / scalar
        assert result.value == 1 / scalar
        assert result.units == UnitTypesLength.meters

    @pytest.mark.parametrize(
        "value, unit, expected_value",
        [
            (2, UnitTypesLength.meters, 0.5),
            (1, UnitTypesLength.centimeters, 100),
            (10, UnitTypesLength.meters, 0.1),
        ],
    )
    def test_UnitFullValue_truedivision_vup(self, value, unit, expected_value):
        vup1 = UnitfulLength(1, UnitTypesLength.meters)
        vup2 = UnitfulLength(value, unit)
        result = vup1 / vup2
        assert isinstance(result, float)
        assert math.isclose(
            result, expected_value
        ), f"True division with unit conversion failed. Expected: {expected_value}, got: {result}"
