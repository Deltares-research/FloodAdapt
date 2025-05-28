set SCRIPT_DIR=%~dp0
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "Resolve-Path -Path '%SCRIPT_DIR:~0,-1%\..\FloodAdapt\flood_adapt\system\win-64\sfincs\sfincs.exe'"`) do set SFINCS_BIN_PATH=%%i
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "Resolve-Path -Path '%SCRIPT_DIR:~0,-1%\..\FloodAdapt\flood_adapt\system\win-64\fiat\fiat.exe'"`) do set FIAT_BIN_PATH=%%i
echo Set SFINCS_BIN_PATH to %SFINCS_BIN_PATH%
echo Set FIAT_BIN_PATH to %FIAT_BIN_PATH%
