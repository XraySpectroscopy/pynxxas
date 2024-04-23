import os
from typing import Optional, Union

import h5py


def create_hdf5_link(
    h5group: h5py.Group,
    target_name: str,
    target_filename: Optional[str],
    absolute: bool = False,
) -> Union[h5py.SoftLink, h5py.ExternalLink]:
    """Create HDF5 soft link (supports relative down paths) or external link (supports relative paths)."""
    this_name = h5group.name
    this_filename = h5group.file.filename

    target_filename = target_filename or this_filename

    if os.path.isabs(target_filename):
        rel_target_filename = os.path.relpath(target_filename, this_filename)
    else:
        rel_target_filename = target_filename
        target_filename = os.path.abs(os.path.join(this_filename, target_filename))

    if "." not in target_name:
        rel_target_name = os.path.relpath(target_name, this_name)
    else:
        rel_target_name = target_name
        target_name = os.path.abspath(os.path.join(this_name, target_name))

    # Internal link
    if rel_target_filename == ".":
        if absolute or ".." in rel_target_name:
            # h5py.SoftLink does not support relative links upwards
            return h5py.SoftLink(target_name)
        return h5py.SoftLink(rel_target_name)

    # External link
    if absolute:
        return h5py.ExternalLink(target_filename, target_name)
    return h5py.ExternalLink(rel_target_filename, target_name)
