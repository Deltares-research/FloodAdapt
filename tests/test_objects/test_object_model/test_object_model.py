import pytest

from flood_adapt.objects.object_model import Object


def test_name_length():
    with pytest.raises(ValueError, match="Name must be at least one character long."):
        Object(name="")


@pytest.mark.parametrize(
    "char",
    [
        " ",
        "@",
        "#",
        "$",
        "%",
        "^",
        "&",
        "*",
        "(",
        ")",
        "!",
        "+",
        "=",
        "{",
        "}",
        "[",
        "]",
        "|",
        "\\",
        ";",
        ":",
        "'",
        '"',
        "<",
        ">",
        ",",
        ".",
        "/",
        "?",
    ],
)
def test_name_invalid_characters(char):
    with pytest.raises(ValueError) as e:
        Object(name=f"InvalidName{char}")
    assert (
        "Name can only contain letters, numbers, underscores (_), and hyphens (-)."
        in str(e.value)
    )


def test_name_validation():
    # Valid names
    valid_names = ["valid_name", "valid-name", "validName123"]
    for name in valid_names:
        obj = Object(name=name)
        assert obj.name == name
