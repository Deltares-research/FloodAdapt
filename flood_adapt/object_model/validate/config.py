from pathlib import Path
from typing import Optional


def validate_existence_config_file(
    config_file_path: str = None,
) -> Optional[bool]:  # Is it necessary to make the bool Optional?
    """Validates that a (config) file exists.

    Args:
        config_file_path (str, optional): A path to a (configuration) file. Defaults to None.

    Raises:
        FileNotFoundError: The file cannot be found.

    Returns:
        Optional[bool]: Returns True if the file is found.
    """
    if config_file_path:
        if Path(config_file_path).is_file():
            return True

    raise FileNotFoundError(
        "Cannot find configuration file {}.".format(config_file_path)
    )


def validate_content_config_file(
    config: dict, config_file_path: str, mandatory_keys: list
) -> Optional[bool]:  # Is it necessary to make the bool Optional?
    """Validates that certain keys are in a config file.

    Args:
        config (dict): A dictionary of key-value pairs to configure the Object Data Model.
        config_file_path (str): The path to the configuration file from with the config (dict) is created.
        mandatory_keys (list): A list of mandatory keys within the configuration dictionary.

    Raises:
        ValueError: Raised when one or multiple mandatory keys are not found.

    Returns:
        Optional[bool]: Returns True if all mandatory keys are in the dictionary.
    """
    not_found_in_config = []
    for mandatory_key in mandatory_keys:
        if mandatory_key not in config.keys():
            not_found_in_config.append(mandatory_key)

    if not_found_in_config:
        raise ValueError(
            "Cannot find mandatory key(s) '{}' in configuration file {}.".format(
                ", ".join(not_found_in_config), config_file_path
            )
        )
    else:
        return True
