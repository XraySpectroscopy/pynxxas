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
./nxxas_examples/generate.sh
```

### Linting

The configuration for [black](https://black.readthedocs.io/en/stable/) and [flake8](https://flake8.pycqa.org/en/latest/index.html) can be modified in `setup.cfg`.

Comment lines with `# noqa: E123` to ignore certain linting errors.

### Testing

Tests make use [pytest](https://docs.pytest.org/en/stable/index.html) and can be run as follows

```bash
pytest .
```

Testing an installed project is done like this

```bash
pytest --pyargs <project_name>
```
