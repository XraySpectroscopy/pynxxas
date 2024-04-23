"""NeXus/HDF5 file format
"""

from typing import Generator, Any, Tuple

try:
    from enum import StrEnum
except ImportError:
    from strenum import StrEnum


import h5py
import pint
import pydantic

from . import url_utils
from . import hdf5_utils
from ..models import nexus


def is_nexus_file(url: url_utils.UrlType) -> bool:
    filename = url_utils.as_url(url).path
    with open(filename, "rb") as file:
        try:
            with h5py.File(file, mode="r"):
                return True
        except Exception:
            return False


def load_nexus_file(url: url_utils.UrlType) -> Generator[nexus.NxGroup, None, None]:
    raise NotImplementedError(f"File format not supported: {url}")


def save_nexus_file(nxgroup: nexus.NxXasModel, url: url_utils.UrlType) -> None:
    if not isinstance(nxgroup, nexus.NxXasModel):
        raise TypeError(f"nxgroup is not of type NxXasModel ({type(nxgroup)})")
    if not nxgroup.has_data():
        return
    filename = url_utils.as_url(url).path
    url = url_utils.as_url(url)

    with h5py.File(filename, mode="a", track_order=True) as nxroot:
        nxparent = _prepare_nxparent(nxgroup, url, nxroot)
        _save_nxgroup(nxgroup, nxparent)


def _save_nxgroup(nxgroup: nexus.NxGroup, nxparent: h5py.Group) -> None:
    if not isinstance(nxgroup, nexus.NxGroup):
        raise TypeError(f"nxgroup is not of type NxGroup ({type(nxgroup)})")
    for field_name, field, field_value in _iter_model_fields(nxgroup):
        if field_value is None:
            continue
        elif isinstance(field_value, nexus.NxGroup):
            nxchild = nxparent.require_group(field_name)
            _save_nxgroup(field_value, nxchild)
            if isinstance(field_value, nexus.NxDataModel):
                _set_default(nxchild)
        elif field.alias and field.alias.startswith("@"):
            try:
                _save_attribute(nxparent, field_name, field_value)
            except Exception as e:
                raise ValueError(
                    f"{field_name} = {field_value} ({type(field_value)}) cannot be saved as an HDF5 attribute"
                ) from e
        else:
            try:
                _save_dataset(nxparent, field_name, field_value)
            except Exception as e:
                raise ValueError(
                    f"{field_name} = {field_value} ({type(field_value)}) cannot be saved as an HDF5 dataset"
                ) from e


def _iter_model_fields(
    model: pydantic.BaseModel,
) -> Generator[Tuple[str, pydantic.Field, Any], None, None]:
    for field_name, field in model.__fields__.items():
        field_value = getattr(model, field_name)
        yield field_name, field, field_value


def _save_dataset(nxparent: h5py.Group, field_name: str, field_value: Any) -> None:
    if isinstance(field_value, nexus.NxField):
        nxparent[field_name] = field_value.value
        for attr_name, attr, attr_value in _iter_model_fields(field_value):
            if attr.alias and attr.alias.startswith("@"):
                nxparent[field_name].attrs[attr_name] = attr_value
    elif isinstance(field_value, StrEnum):
        nxparent[field_name] = str(field_value)
    elif isinstance(field_value, pint.Quantity):
        if field_value.size:
            nxparent[field_name] = field_value.magnitude
            units = str(field_value.units)
            if units:
                nxparent[field_name].attrs["units"] = units
    elif isinstance(field_value, nexus.NxLinkModel):
        link = hdf5_utils.create_hdf5_link(
            nxparent, field_value.target_name, field_value.target_filename
        )
        nxparent[field_name] = link
    else:
        nxparent[field_name] = field_value


def _save_attribute(nxparent: h5py.Group, field_name: str, field_value: Any) -> None:
    if isinstance(field_value, StrEnum):
        nxparent.attrs[field_name] = str(field_value)
    else:
        nxparent.attrs[field_name] = field_value


def _set_default(h5group: h5py.Group) -> None:
    while h5group.name != "/":
        h5group.parent.attrs["default"] = h5group.name.split("/")[-1]
        h5group = h5group.parent


def _prepare_nxparent(
    nxgroup: nexus.NxGroup,
    url: url_utils.ParsedUrlType,
    nxroot: h5py.File,
) -> h5py.Group:
    """Creates and returns the parent group of `nxgroup`"""
    internal_path = url_utils.as_url(url).internal_path
    parts = [s for s in internal_path.split("/") if s]
    nparts = len(parts)

    if nxgroup.NX_class == "NXroot":
        if nparts != 0:
            raise ValueError(
                f"NXroot URL cannot have an internal path ({internal_path})"
            )
        nxclasses = []
    elif nxgroup.NX_class == "NXentry":
        if nparts != 1:
            raise ValueError(
                f"NXentry URL must have an internal path of 1 level deep ({internal_path})"
            )
        nxclasses = ["NXentry"]
    elif nxgroup.NX_class == "NXsubentry":
        if nparts != 2:
            raise ValueError(
                f"NXsubentry URL must have an internal path of 2 levels deep ({internal_path})"
            )
        nxclasses = ["NXentry", "NXsubentry"]
    else:
        nxclasses = ["NXentry"] + ["NXsubentry"] * (len(parts) - 1)

    nxroot.attrs.setdefault("NX_class", "NXroot")

    nxparent = nxroot
    for part, nxclass in zip(parts, nxclasses):
        nxparent = nxparent.require_group(part)
        nxparent.attrs.setdefault("NX_class", nxclass)

    return nxparent
