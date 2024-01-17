@echo off
REM Check that the script is called with exactly one argument
IF "%~1"=="" (
    echo Error: This script requires exactly one argument: the database_root.
    exit /b
) ELSE IF NOT "%~2"=="" (
    echo Error: This script requires exactly one argument: the database_root.
    exit /b
)

REM This script is called by the updateSVN fixture in conftest.py
REM Make sure that the database.toml contains the line: database_root="the/path/to/the/root/of/the/database"

REM Also, make sure to have the svn command line tools installed
REM In case you have not already installed the TortoiseSVN, you can install the command line tools by following the steps below:
REM In case you have already installed the TortoiseSVN and wondering how to upgrade to command line tools, here are the steps...
REM Go to Windows Control Panel → Program and Features (Windows 7+)
REM Locate TortoiseSVN and click on it.
REM Select 'Change' from the options available.
REM Click 'Next'
REM Click 'Modify'
REM Enable 'Command line client tools'
REM Click 'Next'
REM Click 'Install'
REM Click 'Finish'


svn update %1
