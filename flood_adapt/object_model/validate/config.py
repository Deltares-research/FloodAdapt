from pathlib import Path
from typing import Optional


def validate_existence_config_file(config_file_path: str = None) -> Optional[bool]:  # Is it necessary to make the bool Optional?
    if config_file_path:
        if Path(config_file_path).is_file():
            return True
    
    raise FileNotFoundError("Cannot find projection configuration file {}.".format(config_file_path))


def validate_content_config_file(config: dict, config_file_path: str, mandatory_keys: list) -> Optional[bool]:  # Is it necessary to make the bool Optional?
    not_found_in_config = []
    for mandatory_key in mandatory_keys:
        if mandatory_key not in config.keys():
            not_found_in_config.append(mandatory_key)
    
    if not_found_in_config:
        raise ValueError("Cannot find mandatory key(s) '{}' in configuration file {}.".format(', '.join(not_found_in_config), config_file_path))
    else:
        return True
