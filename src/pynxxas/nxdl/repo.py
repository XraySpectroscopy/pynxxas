"""NXDL repository"""

import os
import logging
import tempfile
import urllib.parse
import urllib.request
from glob import glob
from functools import lru_cache
from typing import Optional

import git
import xmlschema

DEFAULT_URL = "https://github.com/nexusformat/definitions.git"


@lru_cache(maxsize=1)
def get_nxdl_schema(**repo_options):
    """Returns the NDXL schema"""
    repo = _get_repo(**repo_options)
    schema_file = os.path.join(repo.working_dir, "nxdl.xsd")
    # Lax because of: https://github.com/nexusformat/definitions/issues/1368
    return xmlschema.XMLSchema(schema_file, validation="lax")


@lru_cache(maxsize=1)
def get_nxdl_definition_names(**repo_options):
    """Returns all NXDL file names from the repo"""
    working_dir = _get_repo(**repo_options).working_dir
    pattern = os.path.join(working_dir, "*", "*.nxdl.xml")
    return [
        os.path.basename(filename).replace(".nxdl.xml", "")
        for filename in glob(pattern)
    ]


def get_nxdl_definition(name: str, **repo_options) -> dict:
    """Load the content of an NXDL file"""
    schema = get_nxdl_schema(**repo_options)
    base_url = urllib.parse.urlparse(schema.base_url)
    assert base_url.scheme == "file"
    path = urllib.request.url2pathname(base_url.path)
    for dirname in ("base_classes", "applications", "contributed_definitions"):
        xml_file = os.path.join(path, dirname, f"{name}.nxdl.xml")
        if os.path.exists(xml_file):
            break
    else:
        raise ValueError(f"NXDL class '{name}' does not exist in '{base_url}'")
    return schema.to_dict(xml_file, process_namespaces=True, use_defaults=True)


@lru_cache(maxsize=1)
def _get_repo(
    nxdl_version: Optional[str] = None,
    localdir: Optional[str] = None,
    url: Optional[str] = None,
    branch: Optional[str] = None,
    reset: Optional[bool] = True,
) -> git.Repo:
    """Git repository with NeXus definition files (*.nxdl.xml)"""
    if not localdir:
        localdir = os.path.join(tempfile.gettempdir(), "nexus_definitions")
    if not url:
        url = DEFAULT_URL
    if not branch:
        branch = "main"
    remote = "origin"

    if os.path.exists(localdir):
        repo = git.Repo(localdir)
        origin = repo.remotes[remote]
        if reset:
            origin.set_url(url)
        origin.fetch()
    else:
        logging.warning("cloning '%s' in '%s' ...", url, localdir)
        repo = git.Repo.clone_from(url, localdir)

    if reset:
        if nxdl_version:
            repo.git.checkout(f"v{nxdl_version}")
        else:
            repo.git.checkout(branch)
            repo.git.reset(f"{remote}/{branch}", hard=True)

    logging.info("NXDL repository '%s' in '%s'", url, localdir)
    return repo
