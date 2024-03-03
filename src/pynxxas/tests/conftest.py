import pytest
from ..nxdl import repo


@pytest.fixture(scope="session")
def repo_directory(tmpdir_factory) -> str:
    root = tmpdir_factory.mktemp("nexus_definitions")
    return repo._get_repo(localdir=str(root / "official_repo")).working_dir
