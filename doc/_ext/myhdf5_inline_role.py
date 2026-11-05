import contextlib
import importlib.util
import io
import os
import re
from glob import glob
from pathlib import Path

from docutils import nodes
from sphinx.util import logging

from pynxxas.io.convert import convert_files

logger = logging.getLogger(__name__)


def setup(app):
    app.add_role("myhdf5", myhdf5_role)
    app.connect("html-page-context", inject_dynamic_url_js)
    app.connect("config-inited", generate_example_nxxas_data)


def myhdf5_role(name, rawtext, text, lineno, inliner, options=None, content=None):
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

    # Relative path from this page to _static, for example "../_static/".
    static_path = context["pathto"]("_static/", 1)

    script = f"""
    <script>
    document.addEventListener("DOMContentLoaded", function() {{
        var links = document.querySelectorAll("a.myhdf5");
        // Resolve against the page URL so that "#anchor", "?query" and subpages work.
        var staticURL = new URL("{static_path}", window.location.href).href;
        var resourceURL = encodeURIComponent(staticURL);
        links.forEach(function(link) {{
            var href = link.getAttribute("href");
            link.setAttribute("href", href.replace("placeholder", resourceURL));
        }});
    }});
    </script>
    """

    context["body"] += script


def generate_example_nxxas_data(app, config):
    try:
        static_dir = Path(app.srcdir) / "_static"
        examples_dir = Path(app.srcdir) / ".." / "examples"

        output_filename = static_dir / "auto" / "converted.nxs"
        with _convert(output_filename, static_dir):
            convert_files(
                [str(examples_dir / "auto" / "*.xdi")],
                str(output_filename),
                "nexus",
                overwrite=True,
            )

        script_paths = sorted(
            glob(str(examples_dir / "manual" / "*" / "convert_to_nexus.py"))
        )
        for script_path in script_paths:
            module_name = os.path.basename(os.path.dirname(script_path))
            output_filename = static_dir / "manual" / module_name / f"{module_name}.nxs"
            with _convert(output_filename, static_dir):
                module = import_file(module_name, script_path)
                module.main(output_filename)
    except Exception:
        logger.exception("NeXus file generation failed.")
        raise


@contextlib.contextmanager
def _convert(output_filename, static_dir):
    """Log one line for each conversion."""
    label = f"{output_filename.relative_to(static_dir)!s:<50}"
    output_filename.parent.mkdir(parents=True, exist_ok=True)
    try:
        # The conversion scripts print one line for each file they write.
        with contextlib.redirect_stdout(io.StringIO()):
            yield
    except Exception:
        logger.info("%s FAILED", label)
        raise
    logger.info("%s done", label)


def import_file(module_name, script_path):
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
