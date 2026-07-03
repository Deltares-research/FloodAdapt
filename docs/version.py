import tomllib
from html import escape
from pathlib import Path

from flood_adapt import __version__
from flood_adapt.config.config import Settings

DOCS_DIR = Path(__file__).parent
REPO_ROOT = DOCS_DIR.parent


def _dep_spec(deps: list[str], name: str) -> str:
    for dep in deps:
        head, _, rest = dep.partition(" ")
        if head == name:
            return rest.strip()
    raise KeyError(f"{name!r} not found in dependencies")


pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
deps = pyproject["project"]["dependencies"]

values = {
    "version": __version__,
    "hydromt_sfincs": escape(_dep_spec(deps, "hydromt-sfincs")),
    "hydromt_fiat": escape(_dep_spec(deps, "hydromt-fiat")),
    "sfincs_exe": Settings.model_fields["sfincs_version"].default,
    "fiat_exe": Settings.model_fields["fiat_version"].default,
}

(DOCS_DIR / "_version.yml").write_text(
    "\n".join(f'{k}: "{v}"' for k, v in values.items()) + "\n"
)
