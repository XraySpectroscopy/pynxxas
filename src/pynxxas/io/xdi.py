"""XAS Data Interchange (XDI) file format
"""

import re
import datetime
from typing import Union, Tuple, Optional, Generator

import pint
import numpy

from . import url_utils
from ..models import units
from ..models.xdi import XdiModel


def is_xdi_file(url: url_utils.UrlType) -> bool:
    filename = url_utils.as_url(url).path
    with open(filename, "r") as file:
        try:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                return line.startswith("# XDI")
        except Exception:
            return False


def load_xdi_file(url: url_utils.UrlType) -> Generator[XdiModel, None, None]:
    """Specs described in

    https://github.com/XraySpectroscopy/XAS-Data-Interchange/blob/master/specification/spec.md
    """
    filename = url_utils.as_url(url).path
    content = {"comments": [], "column": dict(), "data": dict()}

    with open(filename, "r") as file:
        # Version: first non-empty line
        for line in file:
            line = line.strip()
            if not line:
                continue
            if not line.startswith("# XDI"):
                raise ValueError(f"XDI file does not start with '# XDI': '{filename}'")
            break

        # Fields and comments: lines starting with "#"
        is_comment = False
        for line in file:
            line = line.strip()

            if not line.startswith("#"):
                raise ValueError(f"Invalid XDI header line: '{line}'")

            if _XDI_HEADER_END_REGEX.match(line):
                break

            if _XDI_FIELDS_END_REGEX.match(line):
                # Next lines in the header are user comments
                is_comment = True
                continue

            if is_comment:
                match_comment = _XDI_COMMENT_REGEX.match(line)
                if not match_comment:
                    continue
                (comment,) = match_comment.groups()
                content["comments"].append(comment)
                continue

            match_namespace = _XDI_FIELD_REGEX.match(line)
            if match_namespace:
                key, value = match_namespace.groups()
                value = _parse_xdi_value(value)
                key_parts = key.split(".")
                if len(key_parts) > 1:
                    namespace, key = key_parts
                    namespace = namespace.lower()
                    key = key.lower()
                    key = _parse_xdi_value(key)
                    if namespace not in content:
                        content[namespace] = {}
                    content[namespace][key] = value
                else:
                    key = key_parts[0]
                    key = _parse_xdi_value(key)
                    content[key] = value

    # Data
    table = numpy.loadtxt(filename, dtype=float)
    columns = [
        name
        for _, name in sorted(content.pop("column").items(), key=lambda tpl: tpl[0])
    ]
    for name, array in zip(columns, table.T):
        name, quant = _parse_xdi_column_name(name)
        content["data"][name] = array, quant

    yield XdiModel(**content)


def save_xdi_file(model_instance: XdiModel, url: url_utils.UrlType) -> None:
    raise NotImplementedError(
        f"Saving of {type(model_instance).__name__} not implemented"
    )


_XDI_FIELD_REGEX = re.compile(r"#\s*([\w.]+):\s*(.*)")
_XDI_COMMENT_REGEX = re.compile(r"#\s*(.*)")
_XDI_HEADER_END_REGEX = re.compile(r"#\s*-")
_XDI_FIELDS_END_REGEX = re.compile(r"#\s*///")
_NUMBER_REGEX = re.compile(r"(?=.)([+-]?([0-9]*)(\.([0-9]+))?)([eE][+-]?\d+)?\s+\w+")
_SPACES_REGEX = re.compile(r"\s+")


def _parse_xdi_value(
    value: str,
) -> Union[str, datetime.datetime, pint.Quantity, Tuple[str, pint.Quantity]]:
    # Dimensionless integral number
    try:
        return units.as_quantity(int(value))
    except ValueError:
        pass

    # Dimensionless decimal number
    try:
        return units.as_quantity(float(value))
    except ValueError:
        pass

    # Date and time
    try:
        return datetime.datetime.fromisoformat(value)
    except ValueError:
        pass

    # Number with units
    if _NUMBER_REGEX.match(value):
        try:
            return units.as_quantity(value)
        except pint.UndefinedUnitError:
            pass

    return value


def _parse_xdi_column_name(
    name: str,
) -> Union[Tuple[str, Optional[str]]]:
    parts = _SPACES_REGEX.split(name)
    if len(parts) == 1:
        return name, None
    try:
        units.as_units(parts[-1])
    except pint.UndefinedUnitError:
        return name, None
    name = " ".join(parts[:-1])
    return name, parts[-1]
