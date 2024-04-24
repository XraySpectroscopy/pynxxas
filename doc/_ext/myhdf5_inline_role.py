import re
import os
from docutils import nodes
from pynxxas.io.convert import convert_files


def setup(app):
    app.add_role("myhdf5", myhdf5_role)
    app.connect("html-page-context", inject_dynamic_url_js)
    app.connect("config-inited", generate_example_nxxas_data)


def myhdf5_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    matches = re.match(r"(\S+)\s*<([^<>]+)>", text)
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
    output_filename = os.path.join(app.srcdir, "_static", "example_nxxas_data.h5")
    file_pattern1 = os.path.join(app.srcdir, "..", "xdi_files", "*")
    file_pattern2 = os.path.join(app.srcdir, "..", "xas_beamline_data", "*")
    convert_files([file_pattern1, file_pattern2], output_filename, "nexus")
