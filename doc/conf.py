"""rm -rf doc/_generated/; sphinx-build doc build/sphinx/html -E -a
"""

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys
from importlib.metadata import version as get_version

release = get_version("pynxxas")

sys.path.append(os.path.abspath("./_ext"))

project = "pynxxas"
version = ".".join(release.split(".")[:2])
copyright = "2024-2025, ESRF"
author = "ESRF"
docstitle = f"{project} {version}"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.viewcode",
    "sphinx_autodoc_typehints",
    "myhdf5_inline_role",
]
templates_path = ["_templates"]
exclude_patterns = ["build"]

always_document_param_types = True


autosummary_generate = True
autodoc_default_flags = [
    "members",
    "undoc-members",
    "show-inheritance",
]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "pydata_sphinx_theme"
html_static_path = ["_static"]
html_extra_path = []
html_theme_options = {
    "icon_links": [
        {
            "name": "github",
            "url": "https://github.com/XraySpectroscopy/pynxxas",
            "icon": "fa-brands fa-github",
        },
        {
            "name": "pypi",
            "url": "https://pypi.org/project/pynxxas",
            "icon": "fa-brands fa-python",
        },
    ],
    "footer_start": ["copyright"],
    "footer_end": ["footer_end"],
}
