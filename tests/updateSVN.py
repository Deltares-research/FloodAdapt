import subprocess
import sys
from pathlib import Path

if len(sys.argv) != 2:
    print("Error: This script requires exactly one argument: the database_root.")
    sys.exit(1)

database_root = sys.argv[1]

if not Path(database_root).is_dir():
    print(f"Error: {database_root} is not a directory")
    sys.exit(1)

try:
    subprocess.run(["svn", "update", database_root])
except Exception:
    print(
        """
        Error: Could not update the database.
        This script is called by the updateSVN fixture in conftest.py
        Make sure that the database.toml contains the line: database_root="the/path/to/the/root/of/the/database"
        Also, make sure to have the svn command line tools installed
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
