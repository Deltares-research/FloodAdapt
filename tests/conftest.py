import os
import shutil
from pathlib import Path

import pytest


def get_file_structure(path: str) -> list:
    """Get the file structure of a directory and store it in a list"""
    file_structure = []

    # Walk through the directory
    for root, dirs, files in os.walk(path):
        relative_path = os.path.relpath(root, path)
        file_structure.append(relative_path)
    return file_structure

def remove_files_and_folders(path, file_structure):
    """Remove all files and folders that are not present in the file structure"""

    # Walk through the directory
    for root, dirs, files in os.walk(path):
        relative_path = os.path.relpath(root, path)
        # If the relative path is not in the file structure, remove it
        if relative_path not in file_structure:
            try:
                shutil.rmtree(root)
            except PermissionError:
                print(f"PermissionError: {root}")


            
@pytest.fixture
def cleanup_database():
    """Cleanup the database after each test"""

    # Get the database file structure before the test
    test_database_path = Path().absolute() / "tests" / "test_database"
    test_site_name = "charleston"
    database_path = str(test_database_path.joinpath(test_site_name))
    file_structure = get_file_structure(database_path)
    
    # Run the test
    yield
    
    # Remove all files and folders that were not present before the test
    remove_files_and_folders(database_path, file_structure)
    