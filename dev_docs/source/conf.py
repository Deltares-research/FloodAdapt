# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

import os
import sys
from pathlib import Path

ROOT_PATH = Path(__file__).resolve().parents[2]
DEV_DOCS_PATH = ROOT_PATH / "dev_docs"
SRC_PATH = ROOT_PATH / "flood_adapt"
MODULE_PATHS = [SRC_PATH / module for module in ["integrator", "object_model", "api"]]

for path in [ROOT_PATH, DEV_DOCS_PATH, SRC_PATH, *MODULE_PATHS]:
    assert path.exists(), f"Path does not exist: {path}"
    sys.path.insert(0, os.path.abspath(path))

# -- Project information -----------------------------------------------------

project = "FloodAdapt-API"
copyright = "2024, Adrichem"
author = "Adrichem"


# The full version, including alpha/beta/rc tags
def get_floodadapt_version():
    version = None
    with open(ROOT_PATH / "flood_adapt" / "__init__.py", "r") as f:
        for line in f:
            if line.startswith("__version__"):
                version = line.split("=")[1].strip().strip('"')
    assert version, "Could not find version in __init__.py"
    return version


release = get_floodadapt_version()


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ["sphinx.ext.autodoc", "sphinx.ext.napoleon"]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

autodoc_mock_imports = ["flood_adapt", "fiat_toolbox", "cht_cyclones", "hydromt_sfincs"]