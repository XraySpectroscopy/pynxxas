import pydantic
from .repo import get_nxdl_definition_names  # noqa F401
from .repo import get_nxdl_definition as _get_nxdl_definition
from .models import Definition as _Definition


def load_definition(name: str, **repo_options) -> _Definition:
    """Every NeXus definition is defined in an XML file using the
    NXDL schema with a 'definition' root element."""
    xml_content = _get_nxdl_definition(name, **repo_options)
    try:
        return _Definition(**xml_content)
    except pydantic.ValidationError as e:
        raise ValueError(f"NeXus definition '{name}' is invalid") from e
