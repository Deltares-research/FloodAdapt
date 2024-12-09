@echo off
:: This is a batch script to install Rust & cargo on Windows.
:: It checks if cargo and rustc are already installed, and if not, downloads and installs Rust.
:: It also adds Rust to the PATH if it is not already there.
::
:: Currently, this script is required due to hydromt-sfincs requiring it, but not installing it.

:: Check if rust and cargo are available
cargo --version >nul 2>&1
IF %ERRORLEVEL% EQU 0 (

    rustc --version >nul 2>&1
    IF %ERRORLEVEL% EQU 0 (
        echo cargo and rustc are already installed.
        exit /b
    )
)

:: Install Rust
IF EXIST "%USERPROFILE%\.cargo\bin" (
    echo Rust is installed, but cargo and rustc were not found. Please check your PATH.
) ELSE (
    echo Rust is not installed, downloading and installing...
    curl -L https://static.rust-lang.org/rustup/dist/x86_64-pc-windows-msvc/rustup-init.exe -o rustup-init.exe
    rustup-init.exe -y
    del rustup-init.exe
    echo Rust has been installed.
)

:: Edit PATH
echo %PATH% | findstr /i "%USERPROFILE%\.cargo\bin" >nul
IF %ERRORLEVEL% EQU 0 (
    echo Rust is already in the PATH.
) ELSE (
    echo Adding Rust to PATH...
    setx PATH "%PATH%;%USERPROFILE%\.cargo\bin"
    set PATH=%PATH%
)

:: Verify
cargo --version
rustc --version
