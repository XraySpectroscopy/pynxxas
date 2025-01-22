import os
import re
import logging
from glob import glob
import importlib.util
from pathlib import Path

from docutils import nodes
from pynxxas.io.convert import convert_files


def setup(app):
    app.add_role("myhdf5", myhdf5_role)
    app.connect("html-page-context", inject_dynamic_url_js)
    app.connect("config-inited", generate_example_nxxas_data)


def myhdf5_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    matches = re.match(r"^(.*?)\s*<([^<>]+)>$", text)
    if not matches:
        raise ValueError(f"Invalid 'myhdf5' directive text: '{text}'")
    display_text = matches.group(1)
    filename = matches.group(2)

    url_template = f"https://myhdf5.hdfgroup.org/view?url=placeholder{filename}"

    link = f'<a class="myhdf5" href="{url_template}">{display_text}</a>'

    node = nodes.raw("", link, format="html")
    return [node], []


def inject_dynamic_url_js(app, pagename, templatename, context, doctree):
    if app.builder.name != "html" or doctree is None:
        return

    script = """
    <script>
    document.addEventListener("DOMContentLoaded", function() {
        var links = document.querySelectorAll("a.myhdf5");
        var currentURL = window.location.href.replace("index.html", "");
        var resourceURL = encodeURIComponent(currentURL + "_static/");
        links.forEach(function(link) {
            var href = link.getAttribute("href");
            link.setAttribute("href", href.replace("placeholder", resourceURL));
        });
    });
    </script>
    """

    context["body"] += script


def generate_example_nxxas_data(app, config):
    try:
        repo_root = Path(app.srcdir)
        output_filename = repo_root / "_static" / "generic.h5"
        file_pattern1 = repo_root / ".." / "xdi_files" / "*"
        file_pattern2 = repo_root / ".." / "xas_beamline_data" / "*"
        convert_files(
            [str(file_pattern1), str(file_pattern2)], str(output_filename), "nexus"
        )

        script_paths = glob(
            str(repo_root / ".." / "conversion_examples" / "*" / "make_xas.py")
        )
        for script_path in script_paths:
            module_name = os.path.basename(os.path.dirname(script_path))
            module = import_file(module_name, script_path)

            output_filename = repo_root / "_static" / f"{module_name}.h5"
            module.main(output_filename)
    except Exception:
        logging.exception("HDF5 file generate failed")
        raise


def import_file(module_name, script_path):
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
