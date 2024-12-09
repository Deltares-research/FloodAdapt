@echo off
:: This is a batch script to install Rust & cargo on Windows.
:: It checks if cargo and rustc are already installed, and if not, downloads and installs Rust.
:: It also adds Rust to the PATH if it is not already there.
::
:: Currently, this script is required due to hydromt-sfincs requiring it, but not installing it.

:: Check if rust and cargo are available as is
cargo --version >nul 2>&1 && rustc --version >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    echo cargo and rustc are already installed.
    exit /b
)

IF EXIST "%USERPROFILE%\.cargo\bin" (
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
    SET PATH="%USERPROFILE%\.cargo\bin;%PATH%"
    SETX PATH "%USERPROFILE%\.cargo\bin;%PATH%"

    echo Added Rust to PATH...
    echo "%PATH%"

    :: Verify
    cargo --version
    rustc --version
)
