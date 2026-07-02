"""Tests for flood_adapt.misc.sfincs_download."""

import platform
import sys
from pathlib import Path

import pytest

from flood_adapt.misc.sfincs_download import (
    _SFINCS_DOWNLOAD_URLS,
    _get_default_destination,
    _get_default_download_url,
    download_sfincs_binary,
    main,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_urlretrieve(url: str, dest: Path | str) -> None:
    """Write a small placeholder file instead of actually downloading."""
    Path(dest).write_bytes(b"fake-sfincs-binary")


# ---------------------------------------------------------------------------
# _get_default_download_url
# ---------------------------------------------------------------------------


class TestGetDefaultDownloadUrl:
    def test_env_variable_overrides(self, monkeypatch):
        custom = "https://example.com/sfincs"
        monkeypatch.setenv("SFINCS_DOWNLOAD_URL", custom)
        assert _get_default_download_url() == custom

    def test_known_platform_returns_url(self, monkeypatch):
        # Pick a known (system, machine) pair to test against
        system, machine = next(iter(_SFINCS_DOWNLOAD_URLS))
        monkeypatch.setattr(platform, "system", lambda: system)
        monkeypatch.setattr(platform, "machine", lambda: machine)
        monkeypatch.delenv("SFINCS_DOWNLOAD_URL", raising=False)
        url = _get_default_download_url()
        assert url == _SFINCS_DOWNLOAD_URLS[(system, machine)]

    def test_unknown_platform_raises(self, monkeypatch):
        monkeypatch.setattr(platform, "system", lambda: "Haiku")
        monkeypatch.setattr(platform, "machine", lambda: "m68k")
        monkeypatch.delenv("SFINCS_DOWNLOAD_URL", raising=False)
        with pytest.raises(RuntimeError, match="No pre-built SFINCS binary"):
            _get_default_download_url()


# ---------------------------------------------------------------------------
# _get_default_destination
# ---------------------------------------------------------------------------


class TestGetDefaultDestination:
    def test_windows_path(self, monkeypatch):
        monkeypatch.setattr(platform, "system", lambda: "Windows")
        dest = _get_default_destination()
        assert "FloodAdapt" in str(dest)

    def test_linux_path(self, monkeypatch):
        monkeypatch.setattr(platform, "system", lambda: "Linux")
        dest = _get_default_destination()
        assert "FloodAdapt" in str(dest)

    def test_other_path(self, monkeypatch):
        monkeypatch.setattr(platform, "system", lambda: "Darwin")
        dest = _get_default_destination()
        assert "floodadapt" in str(dest)


# ---------------------------------------------------------------------------
# download_sfincs_binary
# ---------------------------------------------------------------------------


class TestDownloadSfincsBinary:
    @pytest.fixture(autouse=True)
    def _patch_urlretrieve(self, monkeypatch):
        monkeypatch.setattr(
            "flood_adapt.misc.sfincs_download.urllib.request.urlretrieve",
            _fake_urlretrieve,
        )

    def test_download_accept_license_flag(self, tmp_path):
        dest = download_sfincs_binary(
            destination=tmp_path,
            url="https://example.com/sfincs_fake",
            accept_license=True,
        )
        assert dest.exists()
        assert dest.name == "sfincs_fake"
        assert dest.stat().st_size > 0

    def test_skip_download_if_exists(self, tmp_path, capsys):
        url = "https://example.com/sfincs_fake"
        existing = tmp_path / "sfincs_fake"
        existing.write_bytes(b"already-there")

        result = download_sfincs_binary(
            destination=tmp_path,
            url=url,
            accept_license=True,
        )
        captured = capsys.readouterr()
        assert "already exists" in captured.out
        assert result == existing.resolve()

    def test_force_redownload(self, tmp_path):
        url = "https://example.com/sfincs_fake"
        existing = tmp_path / "sfincs_fake"
        existing.write_bytes(b"old-content")

        result = download_sfincs_binary(
            destination=tmp_path,
            url=url,
            accept_license=True,
            force=True,
        )
        assert result.read_bytes() == b"fake-sfincs-binary"

    def test_license_decline_exits(self, tmp_path, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "n")
        with pytest.raises(SystemExit):
            download_sfincs_binary(
                destination=tmp_path,
                url="https://example.com/sfincs_fake",
                accept_license=False,
            )

    def test_license_accept_interactively(self, tmp_path, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "y")
        dest = download_sfincs_binary(
            destination=tmp_path,
            url="https://example.com/sfincs_fake",
            accept_license=False,
        )
        assert dest.exists()

    def test_eof_on_input_treated_as_decline(self, tmp_path, monkeypatch):
        def raise_eof(_):
            raise EOFError

        monkeypatch.setattr("builtins.input", raise_eof)
        with pytest.raises(SystemExit):
            download_sfincs_binary(
                destination=tmp_path,
                url="https://example.com/sfincs_fake",
                accept_license=False,
            )

    def test_download_failure_raises(self, tmp_path, monkeypatch):
        def bad_urlretrieve(url, dest):
            raise OSError("network error")

        monkeypatch.setattr(
            "flood_adapt.misc.sfincs_download.urllib.request.urlretrieve",
            bad_urlretrieve,
        )
        with pytest.raises(RuntimeError, match="Failed to download"):
            download_sfincs_binary(
                destination=tmp_path,
                url="https://example.com/sfincs_fake",
                accept_license=True,
            )

    @pytest.mark.skipif(sys.platform == "win32", reason="chmod test not relevant on Windows")
    def test_binary_made_executable_on_unix(self, tmp_path, monkeypatch):
        monkeypatch.setattr(platform, "system", lambda: "Linux")
        dest = download_sfincs_binary(
            destination=tmp_path,
            url="https://example.com/sfincs_linux_fake",
            accept_license=True,
        )
        # Check execute bit is set
        assert dest.stat().st_mode & 0o111


# ---------------------------------------------------------------------------
# CLI (main)
# ---------------------------------------------------------------------------


class TestMain:
    @pytest.fixture(autouse=True)
    def _patch_urlretrieve(self, monkeypatch):
        monkeypatch.setattr(
            "flood_adapt.misc.sfincs_download.urllib.request.urlretrieve",
            _fake_urlretrieve,
        )

    def test_main_with_accept_license_flag(self, tmp_path):
        main(
            [
                "--destination",
                str(tmp_path),
                "--url",
                "https://example.com/sfincs_fake",
                "--accept-license",
            ]
        )
        assert (tmp_path / "sfincs_fake").exists()

    def test_main_force_flag(self, tmp_path):
        url = "https://example.com/sfincs_fake"
        (tmp_path / "sfincs_fake").write_bytes(b"old")
        main(
            [
                "--destination",
                str(tmp_path),
                "--url",
                url,
                "--accept-license",
                "--force",
            ]
        )
        assert (tmp_path / "sfincs_fake").read_bytes() == b"fake-sfincs-binary"

    def test_main_license_declined_exits(self, tmp_path, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "no")
        with pytest.raises(SystemExit):
            main(
                [
                    "--destination",
                    str(tmp_path),
                    "--url",
                    "https://example.com/sfincs_fake",
                ]
            )
