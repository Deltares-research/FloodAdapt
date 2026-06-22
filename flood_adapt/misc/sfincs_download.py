"""Utility for downloading the SFINCS binary with license acceptance."""

import argparse
import platform
import sys
import urllib.request
from pathlib import Path

_SFINCS_LICENSE_URL = "https://raw.githubusercontent.com/Deltares/SFINCS/main/LICENSE"

_SFINCS_LICENSE_TEXT = """\
SFINCS (Super-Fast INundation of CoastS) is developed by Deltares.

The SFINCS binary is provided under the terms of the GNU Lesser General
Public License v2.1 (LGPL-2.1).

Full license text: https://raw.githubusercontent.com/Deltares/SFINCS/main/LICENSE
SFINCS repository:  https://github.com/Deltares/SFINCS

By accepting these terms you agree to:
  1. Use SFINCS in accordance with the LGPL-2.1 license.
  2. Acknowledge Deltares as the developer of SFINCS in any publications or
     products that use results generated with SFINCS.
  3. Not use SFINCS or its outputs for any unlawful purpose.

For commercial licensing inquiries, contact: floodadapt@deltares.nl
"""

# Map (system, machine) → download URL.
# Override via the SFINCS_DOWNLOAD_URL environment variable if needed.
_SFINCS_DOWNLOAD_URLS: dict[tuple[str, str], str] = {
    ("Windows", "AMD64"): (
        "https://github.com/Deltares/SFINCS/releases/latest/download/sfincs_win64.exe"
    ),
    ("Linux", "x86_64"): (
        "https://github.com/Deltares/SFINCS/releases/latest/download/sfincs_linux64"
    ),
}


def _get_default_download_url() -> str:
    """Return the default SFINCS download URL for the current platform."""
    import os

    env_url = os.environ.get("SFINCS_DOWNLOAD_URL")
    if env_url:
        return env_url

    system = platform.system()
    machine = platform.machine()
    url = _SFINCS_DOWNLOAD_URLS.get((system, machine))
    if url is None:
        raise RuntimeError(
            f"No pre-built SFINCS binary is available for {system}/{machine}. "
            "Please download SFINCS manually from https://github.com/Deltares/SFINCS/releases "
            "or set the SFINCS_DOWNLOAD_URL environment variable to a custom URL."
        )
    return url


def _get_default_destination() -> Path:
    """Return the default destination directory for the SFINCS binary."""
    system = platform.system()
    if system == "Windows":
        base = Path.home() / "AppData" / "Local" / "FloodAdapt" / "sfincs"
    elif system == "Linux":
        base = Path.home() / ".local" / "share" / "FloodAdapt" / "sfincs"
    else:
        base = Path.home() / ".floodadapt" / "sfincs"
    return base


def download_sfincs_binary(
    destination: Path | None = None,
    url: str | None = None,
    accept_license: bool = False,
    force: bool = False,
) -> Path:
    """Download the SFINCS binary after the user accepts the license terms.

    Parameters
    ----------
    destination : Path, optional
        Directory where the SFINCS binary will be saved.
        Defaults to a platform-specific application-data directory.
    url : str, optional
        URL from which to download the SFINCS binary.
        Defaults to the official Deltares/SFINCS GitHub release for the
        current platform.  Can also be set via the ``SFINCS_DOWNLOAD_URL``
        environment variable.
    accept_license : bool, default False
        When *True* the license is accepted non-interactively (useful for
        automated/scripted installations).  When *False* (the default) the
        license text is printed and the user is prompted to confirm acceptance.
    force : bool, default False
        Re-download even if the binary already exists at *destination*.

    Returns
    -------
    Path
        Absolute path to the downloaded SFINCS binary.

    Raises
    ------
    RuntimeError
        If the current platform has no pre-built binary available and no
        custom *url* was provided.
    SystemExit
        If the user declines the license.
    """
    dest_dir = Path(destination) if destination is not None else _get_default_destination()
    download_url = url if url is not None else _get_default_download_url()

    # Determine filename from URL
    binary_name = Path(download_url).name
    dest_path = dest_dir / binary_name

    if dest_path.exists() and not force:
        print(f"SFINCS binary already exists at: {dest_path}")
        print("Use --force to re-download.")
        return dest_path.resolve()

    # --- License acceptance ---
    if not accept_license:
        print(_SFINCS_LICENSE_TEXT)
        try:
            answer = input("Do you accept the license terms? [y/N]: ").strip().lower()
        except EOFError:
            answer = ""
        if answer not in ("y", "yes"):
            print("License not accepted. Download cancelled.")
            sys.exit(1)

    # --- Download ---
    dest_dir.mkdir(parents=True, exist_ok=True)
    print(f"Downloading SFINCS binary from:\n  {download_url}")
    print(f"Saving to:\n  {dest_path}")

    try:
        urllib.request.urlretrieve(download_url, dest_path)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to download SFINCS binary from {download_url}: {exc}"
        ) from exc

    # Make the binary executable on Unix-like systems
    if platform.system() != "Windows":
        dest_path.chmod(dest_path.stat().st_mode | 0o111)

    print(f"\nSFINCS binary downloaded successfully to:\n  {dest_path}")
    print(
        "\nTo use it with FloodAdapt, set the path in your Settings:\n"
        f"  Settings(SFINCS_BIN_PATH='{dest_path}', USE_BINARIES=True)"
    )
    return dest_path.resolve()


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for downloading the SFINCS binary."""
    parser = argparse.ArgumentParser(
        description=(
            "Download the SFINCS binary and accept the license terms. "
            "After downloading, configure FloodAdapt by setting the "
            "SFINCS_BIN_PATH environment variable or passing the path to "
            "Settings(SFINCS_BIN_PATH=...)."
        )
    )
    parser.add_argument(
        "--destination",
        "-d",
        type=Path,
        default=None,
        help=(
            "Directory where the SFINCS binary will be saved. "
            "Defaults to a platform-specific application-data directory."
        ),
    )
    parser.add_argument(
        "--url",
        "-u",
        type=str,
        default=None,
        help=(
            "Custom URL from which to download the SFINCS binary. "
            "Overrides the default Deltares/SFINCS GitHub release URL."
        ),
    )
    parser.add_argument(
        "--accept-license",
        action="store_true",
        default=False,
        help=(
            "Accept the SFINCS license non-interactively. "
            "Only use this flag if you have read and agreed to the license terms."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Re-download even if the binary already exists at the destination.",
    )
    args = parser.parse_args(argv)

    download_sfincs_binary(
        destination=args.destination,
        url=args.url,
        accept_license=args.accept_license,
        force=args.force,
    )


if __name__ == "__main__":
    main()
