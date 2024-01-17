@echo off
REM This script is called by the updateSVN fixture in conftest.py
REM Make sure that the database.toml contains the line: database_root="the/path/to/the/root/of/the/database"
svn update %1
