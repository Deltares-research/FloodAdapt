import pytest

from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulArea,
    UnitfulHeight,
    UnitfulVolume,
    UnitTypesArea,
    UnitTypesLength,
    UnitTypesVolume,
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
        assert round(converted_volume, 4) == 353.1466

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
