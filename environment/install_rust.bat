@echo off
:: This is a batch script to install Rust & cargo on Windows.
:: It checks if cargo and rustc are already installed, and if not, downloads and installs Rust.
:: It also adds Rust to the PATH if it is not already there.
::
:: Currently, this script is required due to hydromt-sfincs requiring it, but not installing it.

:: The default installation directory on Windows
SET INSTALL_DIR="%USERPROFILE%\.cargo\bin"

:: Check if rust and cargo are available as is
cargo --version >nul 2>&1 && rustc --version >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    echo cargo and rustc are already installed.
    exit /b
)

IF EXIST "%INSTALL_DIR%" (
    :: Add to PATH if install dir does exists
    echo Rust installation dir exists, but could not find rust in PATH, skipping re-install. Please check your PATH.
    echo "%PATH%"
) ELSE (
    :: Full install if install dir doesnt exist
    echo Rust is not installed, downloading and installing...
    curl -L https://static.rust-lang.org/rustup/dist/x86_64-pc-windows-msvc/rustup-init.exe -o rustup-init.exe
    rustup-init.exe -y
    del rustup-init.exe
    echo Rust has been installed.
)

:: Edit PATH
cargo --version >nul 2>&1 && rustc --version >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    echo Rust and cargo already in the PATH.
) ELSE (
    echo Add Rust to PATH for this session...
    SET "PATH=%INSTALL_DIR%;%PATH%"

    :: Verify
    cargo --version
    rustc --version

    :: Display instructions
    echo.
    echo If you want to add it to your path permanently, you can do so by running the following command in your terminal:
    echo.
    echo SETX PATH "%%INSTALL_DIR%%;%%PATH%%"
    echo.
    echo Where %%INSTALL_DIR%% is the path to the cargo bin directory. default: %%USERPROFILE%%\.cargo\bin, which expands to %INSTALL_DIR%
)
