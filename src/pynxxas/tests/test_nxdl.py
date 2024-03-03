from ..nxdl import repo
from ..nxdl import load_definition


def test_nxdl_models(repo_directory):
    names = repo.get_nxdl_definition_names(localdir=repo_directory)
    for name in names:
        assert load_definition(name)
