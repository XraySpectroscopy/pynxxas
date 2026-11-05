## Getting started

Requirements are listed in `setup.cfg` and can be installed with

```bash
pip install [--user] .[dev]
```

## Make a contribution

Before making a merge request make sure the following is done on your branch

1. Update HDF5 repository examples
2. Linting
3. Testing

### Update HDF5 repository examples

To be sure all HDF5 files are compliant with the latest standard

```bash
pip install -e .[dev]
./examples/convert_to_nexus.sh
```

### Linting

Use [ruff](https://docs.astral.sh/ruff/) to lint and format the code. The configuration is in `pyproject.toml`.

```bash
ruff check .
ruff format .
```

Add `# noqa: E123` to a line to ignore a specific linting error.

### Testing

Tests make use [pytest](https://docs.pytest.org/en/stable/index.html) and can be run as follows

```bash
pytest .
```

Testing an installed project is done like this

```bash
pytest --pyargs <project_name>
```
