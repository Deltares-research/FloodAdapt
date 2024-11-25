import math

import pytest

import flood_adapt.object_model.io.unitfulvalue as uv


def _perform_conversion_test(
    test_class, initial_value, initial_unit, expected_value, target_unit
):
    """
    Perform a unit conversion test for a given test_class.

    Note:
        The only tests you need to write for a new uv.IUnitFullValue are:
            the conversion tests (this function)
            validator tests (if you have custom validators).

    Args:
        test_class: The class to test, e.g., uv.UnitfulIntensity, uv.UnitfulLength.
        initial_value (float): The initial value for the conversion.
        initial_unit: The initial unit of the value.
        expected_value (float): The expected value after conversion.
        target_unit: The target unit for the conversion.
    """
    assert issubclass(
        test_class, uv.IUnitFullValue
    ), f"Only child classes of uv.IUnitFullValues can be tested by this function, not: {type(test_class).__name__}."

    instance = test_class(initial_value, initial_unit)
    converted = instance.convert(target_unit)

    assert (
        converted == pytest.approx(expected_value, rel=1e-2)
    ), f"{instance} Failed conversion: {initial_unit} to {target_unit}. Expected {expected_value}, got {converted}"


class TestUnitfulTime:
    TEST_TIME_CONVERSIONS = [
        (
            1,
            uv.UnitTypesTime.days,
            24,
            uv.UnitTypesTime.hours,
        ),
        (
            1,
            uv.UnitTypesTime.days,
            24 * 60,
            uv.UnitTypesTime.minutes,
        ),
        (
            1,
            uv.UnitTypesTime.days,
            24 * 60 * 60,
            uv.UnitTypesTime.seconds,
        ),
        (1, uv.UnitTypesTime.hours, 1 / 24, uv.UnitTypesTime.days),
        (1, uv.UnitTypesTime.hours, 60, uv.UnitTypesTime.minutes),
        (1, uv.UnitTypesTime.hours, 60 * 60, uv.UnitTypesTime.seconds),
        (1, uv.UnitTypesTime.minutes, 1 / 60 / 24, uv.UnitTypesTime.days),
        (1, uv.UnitTypesTime.minutes, 1 / 60, uv.UnitTypesTime.hours),
        (1, uv.UnitTypesTime.minutes, 60, uv.UnitTypesTime.seconds),
        (1, uv.UnitTypesTime.seconds, 1 / 60 / 60 / 24, uv.UnitTypesTime.days),
        (1, uv.UnitTypesTime.seconds, 1 / 60 / 60, uv.UnitTypesTime.hours),
        (1, uv.UnitTypesTime.seconds, 1 / 60, uv.UnitTypesTime.minutes),
    ]

    @pytest.mark.parametrize(
        "initial_value, initial_unit, expected_value, target_unit",
        TEST_TIME_CONVERSIONS,
    )
    def test_UnitFullTime_convert(
        self, initial_value, initial_unit, expected_value, target_unit
    ):
        _perform_conversion_test(
            uv.UnitfulTime, initial_value, initial_unit, expected_value, target_unit
        )

    @pytest.mark.parametrize(
        "input_value, input_unit, expected_value",
        [
            (4, uv.UnitTypesTime.days, 4 * 24 * 60 * 60),
            (10, uv.UnitTypesTime.hours, 10 * 60 * 60),
            (5, uv.UnitTypesTime.minutes, 5 * 60),
            (600, uv.UnitTypesTime.seconds, 600),
        ],
    )
    def test_UnitfulTime_to_timedelta(self, input_value, input_unit, expected_value):
        time = uv.UnitfulTime(input_value, input_unit)
        assert time.to_timedelta().total_seconds() == expected_value


class TestUnitfulIntensity:
    TEST_INTENSITY_CONVERSIONS = [
        (
            1,
            uv.UnitTypesIntensity.mm_hr,
            1 / 25.39544832,
            uv.UnitTypesIntensity.inch_hr,
        ),
        (180, uv.UnitTypesIntensity.mm_hr, 7.08, uv.UnitTypesIntensity.inch_hr),
        (1, uv.UnitTypesIntensity.inch_hr, 25.39544832, uv.UnitTypesIntensity.mm_hr),
        (4000, uv.UnitTypesIntensity.inch_hr, 101581.8, uv.UnitTypesIntensity.mm_hr),
        (180, uv.UnitTypesIntensity.inch_hr, 4572, uv.UnitTypesIntensity.mm_hr),
        (180, uv.UnitTypesIntensity.mm_hr, 180, uv.UnitTypesIntensity.mm_hr),
        (180, uv.UnitTypesIntensity.inch_hr, 180, uv.UnitTypesIntensity.inch_hr),
    ]

    @pytest.mark.parametrize(
        "initial_value, initial_unit, expected_value, target_unit",
        TEST_INTENSITY_CONVERSIONS,
    )
    def test_UnitFullIntensity_convert(
        self, initial_value, initial_unit, expected_value, target_unit
    ):
        _perform_conversion_test(
            uv.UnitfulIntensity,
            initial_value,
            initial_unit,
            expected_value,
            target_unit,
        )

    def test_UnitFullIntensity_validator(self):
        with pytest.raises(ValueError):
            uv.UnitfulIntensity(-1.0, uv.UnitTypesIntensity.inch_hr)


class TestUnitfulLength:
    TEST_LENGTH_CONVERSIONS = [
        (1000, uv.UnitTypesLength.millimeters, 100, uv.UnitTypesLength.centimeters),
        (1000, uv.UnitTypesLength.millimeters, 1, uv.UnitTypesLength.meters),
        (1000, uv.UnitTypesLength.millimeters, 3.28084, uv.UnitTypesLength.feet),
        (1000, uv.UnitTypesLength.millimeters, 39.3701, uv.UnitTypesLength.inch),
        (1000, uv.UnitTypesLength.millimeters, 0.000621371, uv.UnitTypesLength.miles),
        (100, uv.UnitTypesLength.centimeters, 1000, uv.UnitTypesLength.millimeters),
        (100, uv.UnitTypesLength.centimeters, 100, uv.UnitTypesLength.centimeters),
        (100, uv.UnitTypesLength.centimeters, 3.28084, uv.UnitTypesLength.feet),
        (100, uv.UnitTypesLength.centimeters, 39.3701, uv.UnitTypesLength.inch),
        (100, uv.UnitTypesLength.centimeters, 0.000621371, uv.UnitTypesLength.miles),
        (1, uv.UnitTypesLength.meters, 1000, uv.UnitTypesLength.millimeters),
        (1, uv.UnitTypesLength.meters, 100, uv.UnitTypesLength.centimeters),
        (1, uv.UnitTypesLength.meters, 3.28084, uv.UnitTypesLength.feet),
        (1, uv.UnitTypesLength.meters, 39.3701, uv.UnitTypesLength.inch),
        (1, uv.UnitTypesLength.meters, 0.000621371, uv.UnitTypesLength.miles),
        (1, uv.UnitTypesLength.inch, 0.0254, uv.UnitTypesLength.meters),
        (1, uv.UnitTypesLength.inch, 2.54, uv.UnitTypesLength.centimeters),
        (1, uv.UnitTypesLength.inch, 25.4, uv.UnitTypesLength.millimeters),
        (1, uv.UnitTypesLength.inch, 1 / 12, uv.UnitTypesLength.feet),
        (1, uv.UnitTypesLength.inch, 1.5783e-5, uv.UnitTypesLength.miles),
        (1, uv.UnitTypesLength.feet, 0.3048, uv.UnitTypesLength.meters),
        (1, uv.UnitTypesLength.feet, 30.48, uv.UnitTypesLength.centimeters),
        (1, uv.UnitTypesLength.feet, 304.8, uv.UnitTypesLength.millimeters),
        (1, uv.UnitTypesLength.feet, 12, uv.UnitTypesLength.inch),
        (1, uv.UnitTypesLength.feet, 0.000189394, uv.UnitTypesLength.miles),
        (1, uv.UnitTypesLength.miles, 1609.344, uv.UnitTypesLength.meters),
        (1, uv.UnitTypesLength.miles, 160934.4, uv.UnitTypesLength.centimeters),
        (1, uv.UnitTypesLength.miles, 1609344, uv.UnitTypesLength.millimeters),
        (1, uv.UnitTypesLength.miles, 5280, uv.UnitTypesLength.feet),
        (1, uv.UnitTypesLength.miles, 63360, uv.UnitTypesLength.inch),
    ]

    @pytest.mark.parametrize(
        "initial_value, initial_unit, expected_value, target_unit",
        TEST_LENGTH_CONVERSIONS,
    )
    def test_UnitFullLength_convert(
        self, initial_value, initial_unit, expected_value, target_unit
    ):
        _perform_conversion_test(
            uv.UnitfulLength, initial_value, initial_unit, expected_value, target_unit
        )


class TestUnitfulHeight:
    def test_unitfulHeight_convertMToFeet_correct(self):
        # Assert
        length = uv.UnitfulHeight(value=10, units=uv.UnitTypesLength.meters)

        # Act
        converted_length = length.convert(uv.UnitTypesLength.feet)

        # Assert
        assert round(converted_length, 4) == 32.8084

    def test_unitfulHeight_convertFeetToM_correct(self):
        # Assert
        length = uv.UnitfulHeight(value=10, units=uv.UnitTypesLength.feet)
        inverse_length = uv.UnitfulHeight(value=10, units=uv.UnitTypesLength.meters)

        # Act
        converted_length = length.convert(uv.UnitTypesLength.meters)
        inverse_converted_length = inverse_length.convert(uv.UnitTypesLength.feet)

        # Assert
        assert round(converted_length, 4) == 3.048
        assert round(inverse_converted_length, 4) == 32.8084

    def test_unitfulHeight_convertMToCM_correct(self):
        # Assert
        length = uv.UnitfulHeight(value=10, units=uv.UnitTypesLength.meters)

        # Act
        converted_length = length.convert(uv.UnitTypesLength.centimeters)

        # Assert
        assert round(converted_length, 4) == 1000

    def test_unitfulHeight_convertCMToM_correct(self):
        # Assert
        length = uv.UnitfulHeight(value=1000, units=uv.UnitTypesLength.centimeters)

        # Act
        converted_length = length.convert(uv.UnitTypesLength.meters)

        # Assert
        assert round(converted_length, 4) == 10

    def test_unitfulHeight_convertMToMM_correct(self):
        # Assert
        length = uv.UnitfulHeight(value=10, units=uv.UnitTypesLength.meters)

        # Act
        converted_length = length.convert(uv.UnitTypesLength.millimeters)

        # Assert
        assert round(converted_length, 4) == 10000

    def test_unitfulHeight_convertMMToM_correct(self):
        # Assert
        length = uv.UnitfulHeight(value=10000, units=uv.UnitTypesLength.millimeters)

        # Act
        converted_length = length.convert(uv.UnitTypesLength.meters)

        # Assert
        assert round(converted_length, 4) == 10

    def test_unitfulHeight_convertMToInches_correct(self):
        # Assert
        length = uv.UnitfulHeight(value=10, units=uv.UnitTypesLength.meters)

        # Act
        converted_length = length.convert(uv.UnitTypesLength.inch)

        # Assert
        assert round(converted_length, 4) == 393.7008

    def test_unitfulHeight_convertInchesToM_correct(self):
        # Assert
        length = uv.UnitfulHeight(value=1000, units=uv.UnitTypesLength.inch)

        # Act
        converted_length = length.convert(uv.UnitTypesLength.meters)

        # Assert
        assert round(converted_length, 4) == 25.4

    def test_unitfulHeight_convertMToMiles_correct(self):
        # Assert
        length = uv.UnitfulHeight(value=10, units=uv.UnitTypesLength.meters)

        # Act
        converted_length = length.convert(uv.UnitTypesLength.miles)

        # Assert
        assert round(converted_length, 4) == 0.0062

    def test_unitfulHeight_convertMilesToM_correct(self):
        # Assert
        length = uv.UnitfulHeight(value=1, units=uv.UnitTypesLength.miles)

        # Act
        converted_length = length.convert(uv.UnitTypesLength.meters)

        # Assert
        assert round(converted_length, 4) == 1609.344

    def test_unitfulHeight_setValue_negativeValue(self):
        # Assert
        with pytest.raises(ValueError):
            uv.UnitfulHeight(value=-10, units=uv.UnitTypesLength.meters)

    def test_unitfulHeight_setUnit_invalidUnits(self):
        # Assert
        with pytest.raises(ValueError) as excinfo:
            uv.UnitfulHeight(value=10, units="invalid_units")
        assert "UnitfulHeight\nunits\n  Input should be " in str(excinfo.value)


class TestUnitfulArea:
    def test_unitfulArea_convertM2ToCM2_correct(self):
        # Assert
        area = uv.UnitfulArea(value=10, units=uv.UnitTypesArea.m2)

        # Act
        converted_area = area.convert(uv.UnitTypesArea.cm2)

        # Assert
        assert round(converted_area, 4) == 100000

    def test_unitfulArea_convertCM2ToM2_correct(self):
        # Assert
        area = uv.UnitfulArea(value=100000, units=uv.UnitTypesArea.cm2)

        # Act
        converted_area = area.convert(uv.UnitTypesArea.m2)

        # Assert
        assert round(converted_area, 4) == 10

    def test_unitfulArea_convertM2ToMM2_correct(self):
        # Assert
        area = uv.UnitfulArea(value=10, units=uv.UnitTypesArea.m2)

        # Act
        converted_area = area.convert(uv.UnitTypesArea.mm2)

        # Assert
        assert round(converted_area, 4) == 10000000

    def test_unitfulArea_convertMM2ToM2_correct(self):
        # Assert
        area = uv.UnitfulArea(value=10000000, units=uv.UnitTypesArea.mm2)

        # Act
        converted_area = area.convert(uv.UnitTypesArea.m2)

        # Assert
        assert round(converted_area, 4) == 10

    def test_unitfulArea_convertM2ToSF_correct(self):
        # Assert
        area = uv.UnitfulArea(value=10, units=uv.UnitTypesArea.m2)

        # Act
        converted_area = area.convert(uv.UnitTypesArea.sf)

        # Assert
        assert round(converted_area, 4) == 107.64

    def test_unitfulArea_convertSFToM2_correct(self):
        # Assert
        area = uv.UnitfulArea(value=100, units=uv.UnitTypesArea.sf)

        # Act
        converted_area = area.convert(uv.UnitTypesArea.m2)

        # Assert
        assert round(converted_area, 4) == 9.2902

    def test_unitfulArea_setValue_negativeValue(self):
        # Assert
        with pytest.raises(ValueError):
            uv.UnitfulArea(value=-10, units=uv.UnitTypesArea.m2)

    def test_unitfulArea_setUnit_invalidUnits(self):
        # Assert
        with pytest.raises(ValueError) as excinfo:
            uv.UnitfulArea(value=10, units="invalid_units")
        assert "UnitfulArea\nunits\n  Input should be " in str(excinfo.value)


class TestUnitfulVolume:
    def test_unitfulVolume_convertM3ToCF_correct(self):
        # Assert
        volume = uv.UnitfulVolume(value=10, units=uv.UnitTypesVolume.m3)

        # Act
        converted_volume = volume.convert(uv.UnitTypesVolume.cf)

        # Assert
        pytest.approx(converted_volume, 4) == 353.1466

    def test_unitfulVolume_convertCFToM3_correct(self):
        # Assert
        volume = uv.UnitfulVolume(value=100, units=uv.UnitTypesVolume.cf)

        # Act
        converted_volume = volume.convert(uv.UnitTypesVolume.m3)

        # Assert
        assert round(converted_volume, 4) == 2.8317

    def test_unitfulVolume_setValue_negativeValue(self):
        # Assert
        with pytest.raises(ValueError):
            uv.UnitfulVolume(value=-10, units=uv.UnitTypesVolume.m3)

    def test_unitfulVolume_setUnit_invalidUnits(self):
        # Assert
        with pytest.raises(ValueError) as excinfo:
            uv.UnitfulVolume(value=10, units="invalid_units")
        assert "UnitfulVolume\nunits\n  Input should be " in str(excinfo.value)


class TestIUnitFullValue:
    """The tests below here test behaviour that is the same for all uv.IUnitFullValues, so we only need to test one of them."""

    TEST_INITIALIZE_ENTRIES = [
        (1, uv.UnitTypesLength.meters),
        (1, uv.UnitTypesLength.centimeters),
        (1, uv.UnitTypesLength.millimeters),
        (1, uv.UnitTypesLength.feet),
        (1, uv.UnitTypesLength.inch),
        (1, uv.UnitTypesLength.miles),
    ]

    @pytest.mark.parametrize("value, units", TEST_INITIALIZE_ENTRIES)
    def test_UnitFullValue_initialization(
        self, value: float, units: uv.UnitTypesLength
    ):
        """Equal for all uv.IUnitFullValues, so we only need to test one of them."""
        vup = uv.UnitfulLength(value, units)
        assert vup.value == float(value), f"Failed value: {vup}"
        assert vup.units == units, f"Failed units: {vup}"
        assert str(vup) == f"{float(value)} {units.value}", f"Failed string: {vup}"

    TEST_EQUALITY_ENTRIES = [
        (1, uv.UnitTypesLength.meters, 100, uv.UnitTypesLength.centimeters, True),
        (1, uv.UnitTypesLength.meters, 1, uv.UnitTypesLength.meters, True),
        (2, uv.UnitTypesLength.meters, 200, uv.UnitTypesLength.centimeters, True),
        (3, uv.UnitTypesLength.meters, 3, uv.UnitTypesLength.meters, True),
        (0, uv.UnitTypesLength.meters, 0, uv.UnitTypesLength.centimeters, True),
        (0, uv.UnitTypesLength.meters, 0, uv.UnitTypesLength.meters, True),
        (0, uv.UnitTypesLength.meters, 0, uv.UnitTypesLength.miles, True),
        (1, uv.UnitTypesLength.feet, 12, uv.UnitTypesLength.inch, True),
        (2, uv.UnitTypesLength.feet, 24, uv.UnitTypesLength.inch, True),
        (0, uv.UnitTypesLength.feet, 0, uv.UnitTypesLength.inch, True),
        (1, uv.UnitTypesLength.miles, 1609.34, uv.UnitTypesLength.meters, True),
        (2, uv.UnitTypesLength.miles, 3218.68, uv.UnitTypesLength.meters, True),
        (0, uv.UnitTypesLength.miles, 0, uv.UnitTypesLength.meters, True),
        (1, uv.UnitTypesLength.meters, 1, uv.UnitTypesLength.miles, False),
        (2, uv.UnitTypesLength.meters, 2, uv.UnitTypesLength.miles, False),
        (1, uv.UnitTypesLength.meters, 102, uv.UnitTypesLength.centimeters, False),
        (1, uv.UnitTypesLength.meters, 98, uv.UnitTypesLength.centimeters, False),
        (1, uv.UnitTypesLength.feet, 13, uv.UnitTypesLength.inch, False),
        (1, uv.UnitTypesLength.feet, 11, uv.UnitTypesLength.inch, False),
        (1, uv.UnitTypesLength.miles, 1590, uv.UnitTypesLength.meters, False),
        (1, uv.UnitTypesLength.miles, 1630, uv.UnitTypesLength.meters, False),
    ]

    @pytest.mark.parametrize(
        "value_a, unit_a, value_b, unit_b, expected_result", TEST_EQUALITY_ENTRIES
    )
    def test_UnitFullValue_equality(
        self, value_a, unit_a, value_b, unit_b, expected_result
    ):
        """
        The tests for ==, > and < are the same for all uv.IUnitFullValues and only have different results due to convert().

        If you add a new uv.IUnitFullValue, you should only add a test for the convert function.
        """
        length_a = uv.UnitfulLength(value_a, unit_a)
        length_b = uv.UnitfulLength(value_b, unit_b)

        assert (
            length_a == length_b
        ) == expected_result, f"Failed equality: {length_a} and {length_b}"

    TEST_LESSTHAN_ENTRIES = [
        (999, uv.UnitTypesLength.millimeters, 1, uv.UnitTypesLength.meters, True),
        (1, uv.UnitTypesLength.centimeters, 2, uv.UnitTypesLength.centimeters, True),
        (100, uv.UnitTypesLength.centimeters, 1.1, uv.UnitTypesLength.meters, True),
        (1, uv.UnitTypesLength.meters, 1001, uv.UnitTypesLength.millimeters, True),
        (1, uv.UnitTypesLength.meters, 101, uv.UnitTypesLength.centimeters, True),
        (1, uv.UnitTypesLength.feet, 1, uv.UnitTypesLength.meters, True),
        (11, uv.UnitTypesLength.inch, 1, uv.UnitTypesLength.feet, True),
        (1, uv.UnitTypesLength.miles, 1610, uv.UnitTypesLength.meters, True),
        (1, uv.UnitTypesLength.inch, 2.54, uv.UnitTypesLength.centimeters, False),
        (1000, uv.UnitTypesLength.millimeters, 1, uv.UnitTypesLength.meters, False),
        (1, uv.UnitTypesLength.miles, 1609, uv.UnitTypesLength.meters, False),
        (1, uv.UnitTypesLength.feet, 13, uv.UnitTypesLength.inch, True),
        (100, uv.UnitTypesLength.centimeters, 1, uv.UnitTypesLength.meters, False),
        (1, uv.UnitTypesLength.meters, 100, uv.UnitTypesLength.centimeters, False),
    ]

    @pytest.mark.parametrize(
        "value_a, unit_a, value_b, unit_b, expected_result", TEST_LESSTHAN_ENTRIES
    )
    def test_UnitFullValue_less_than(
        self, value_a, unit_a, value_b, unit_b, expected_result
    ):
        """
        The tests for ==, > and < are the same for all uv.IUnitFullValues and only have different results due to convert().

        If you add a new uv.IUnitFullValue, you should only add a test for the convert function.
        """
        length_a = uv.UnitfulLength(value_a, unit_a)
        length_b = uv.UnitfulLength(value_b, unit_b)
        assert (
            (length_a < length_b) is expected_result
        ), f"Failed less than: {length_a} and {length_b}. {length_a} {length_b.convert(length_a.units)}"

    TEST_GREATERTHAN_ENTRIES = [
        (2, uv.UnitTypesLength.centimeters, 1, uv.UnitTypesLength.centimeters, True),
        (1001, uv.UnitTypesLength.millimeters, 1, uv.UnitTypesLength.meters, True),
        (3, uv.UnitTypesLength.feet, 1, uv.UnitTypesLength.meters, False),
        (2, uv.UnitTypesLength.miles, 3000, uv.UnitTypesLength.meters, True),
    ]

    @pytest.mark.parametrize(
        "value_a, unit_a, value_b, unit_b, expected_result", TEST_GREATERTHAN_ENTRIES
    )
    def test_UnitFullValue_greater_than(
        self, value_a, unit_a, value_b, unit_b, expected_result
    ):
        """
        The tests for ==, > and < are the same for all uv.IUnitFullValues and only have different results due to convert().

        If you add a new uv.IUnitFullValue, you should only add a test for the convert function.
        """
        length_a = uv.UnitfulLength(value_a, unit_a)
        length_b = uv.UnitfulLength(value_b, unit_b)
        assert (
            (length_a > length_b) == expected_result
        ), f"Failed greater than: {length_a} and {length_b}. Result {(length_a > length_b)}"

    TEST_COMPARE_RAISE_TYPEERRORS = [
        ("inch"),
        (2),
        (3.0),
        uv.UnitfulTime(1, uv.UnitTypesTime.days),
        uv.UnitfulIntensity(1, uv.UnitTypesIntensity.mm_hr),
    ]
    TEST_COMPARE_OPERATIONS = [
        (lambda x: uv.UnitfulLength(1.0, uv.UnitTypesLength.meters) - x, "subtraction"),
        (lambda x: uv.UnitfulLength(1.0, uv.UnitTypesLength.meters) + x, "addition"),
        (lambda x: uv.UnitfulLength(1.0, uv.UnitTypesLength.meters) == x, "equals"),
        (lambda x: uv.UnitfulLength(1.0, uv.UnitTypesLength.meters) != x, "not equals"),
        (
            lambda x: uv.UnitfulLength(1.0, uv.UnitTypesLength.meters) > x,
            "greater than",
        ),
        (
            lambda x: uv.UnitfulLength(1.0, uv.UnitTypesLength.meters) >= x,
            "less than or equal",
        ),
        (lambda x: uv.UnitfulLength(1.0, uv.UnitTypesLength.meters) < x, "less than"),
        (
            lambda x: uv.UnitfulLength(1.0, uv.UnitTypesLength.meters) <= x,
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
        vup = uv.UnitfulLength(1, uv.UnitTypesLength.meters)
        result = vup * scalar
        assert result.value == 1 / scalar
        assert result.units == uv.UnitTypesLength.meters

    @pytest.mark.parametrize("scalar", [2, 0.5])
    def test_UnitFullValue_truedivision_scalar(self, scalar):
        vup = uv.UnitfulLength(1, uv.UnitTypesLength.meters)
        result = vup / scalar
        assert result.value == 1 / scalar
        assert result.units == uv.UnitTypesLength.meters

    @pytest.mark.parametrize(
        "value, unit, expected_value",
        [
            (2, uv.UnitTypesLength.meters, 0.5),
            (1, uv.UnitTypesLength.centimeters, 100),
            (10, uv.UnitTypesLength.meters, 0.1),
        ],
    )
    def test_UnitFullValue_truedivision_vup(self, value, unit, expected_value):
        vup1 = uv.UnitfulLength(1, uv.UnitTypesLength.meters)
        vup2 = uv.UnitfulLength(value, unit)
        result = vup1 / vup2
        assert isinstance(result, float)
        assert math.isclose(
            result, expected_value
        ), f"True division with unit conversion failed. Expected: {expected_value}, got: {result}"
