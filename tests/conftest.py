import gc
import subprocess
from pathlib import Path

import pytest

import flood_adapt.config as FloodAdapt_config
from flood_adapt.api.startup import read_database


def make_db_fixture(scope, clean=True):
    """
    This fixture is used for testing in general.
    It functions as follows:
        1) Setup database controller
        2) Perform all tests in scope
        3) Optionally clean the database
    Scope can be one of the following: "function", "class", "module", "package", "session"

    Parameters
    ----------
    scope : str
        The scope of the fixture (e.g., "function", "class", "module", "package", "session")
    clean : bool, optional (default is True)
        Whether to clean the database after all tests in the scope have run.
        Clean means cleaning the contents of versioned files, and deleting unversioned files and folders after the tests

    Returns
    -------
    _db_fixture : pytest.fixture
        The database fixture
    """
    try:
        subprocess.run(["svn", "--version"], capture_output=True)
    except Exception:
        print(
            """
            Make sure to have the svn command line tools installed
            In case you have not already installed the TortoiseSVN, you can install the command line tools by following the steps below:
            In case you have already installed the TortoiseSVN and wondering how to upgrade to command line tools, here are the steps...
            Go to Windows Control Panel → Program and Features (Windows 7+)
            Locate TortoiseSVN and click on it.
            Select 'Change' from the options available.
            Click 'Next'
            Click 'Modify'
            Enable 'Command line client tools'
            Click 'Next'
            Click 'Install'
            Click 'Finish'
            """
        )
        exit(1)

    if scope not in ["function", "class", "module", "package", "session"]:
        raise ValueError(f"Invalid fixture scope: {scope}")

    @pytest.fixture(scope=scope)
    def _db_fixture(clean=clean):
        config_path = Path(__file__).parent.parent / "config.toml"
        FloodAdapt_config.load_config(config_path)
        FloodAdapt_config.set_database_name("charleston_test")

        database_path = FloodAdapt_config.get_database_root()
        database_name = FloodAdapt_config.get_database_name()

        dbs = read_database(database_path, database_name)
        yield dbs

        # Close all dangling connections
        gc.collect()

        if clean:
            subprocess.run(
                ["svn", "revert", "-R", database_path / database_name],
                capture_output=True,
            )
            subprocess.run(
                [
                    "svn",
                    "cleanup",
                    "--remove-unversioned",
                    database_path / database_name,
                ],
                capture_output=True,
            )

    return _db_fixture


# NOTE: to access the contents the fixtures in the test functions,
# the fixture name needs to be passed as an argument to the test function.
# the first line of your test needs to initialize the yielded variables:
# 'dbs = test_db_...'

test_db = make_db_fixture("function")
test_db_class = make_db_fixture("class")
test_db_module = make_db_fixture("module")
test_db_package = make_db_fixture("package")
test_db_session = make_db_fixture("session")

# NOTE: while developing, it is useful to have a fixture that does not clean the database to debug
# Should not be used in tests that are completed and pushed to the repository
test_db_no_clean = make_db_fixture("function", clean=False)
test_db_class_no_clean = make_db_fixture("class", clean=False)
test_db_module_no_clean = make_db_fixture("module", clean=False)
test_db_package_no_clean = make_db_fixture("package", clean=False)
test_db_session_no_clean = make_db_fixture("session", clean=False)
