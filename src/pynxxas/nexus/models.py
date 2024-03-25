"""NeXus model"""

import pydantic
from typing import Union

from ..nxdl import models as nxdl_models
from ..nxdl import load_definition as load_nxdl_definition


def load_model(name: str, **repo_options) -> pydantic.BaseModel:
    return _NexusModelCreator(repo_options).create(name)


class _NexusModelCreator:
    def __init__(self, repo_options: dict) -> None:
        self._repo_options = repo_options
        self._definitions = dict()

    def create(self, name: str):
        self._create_group(self._get_definition(name))

    def _create_group(
        self,
        nxclass: Union[nxdl_models.Definition, nxdl_models.Group],
        *args,
        indent=0,
    ):
        if isinstance(nxclass, nxdl_models.Definition):
            nxclass_parent = self._get_definition(nxclass.extends)
            assert nxclass_parent.type == "group"
        else:
            nxclass_parent = self._get_definition(nxclass.type)

        # nxclass inherits from nxclass_parent while overwriting attributes,
        # fields and groups.

        # TODO: use pydantic.create_model to create a merged model
        #       from nxclass and nxclass_parent
        # Circular sub-groups: NXgeometry <-> NXtranslation

        self._print(indent, nxclass.name, nxclass.type, *args)
        indent += 1
        if indent > 5:
            return  # circular dependencies

        base_attributes = {attr.name: attr for attr in nxclass_parent.attribute}
        overwrite_attributes = {attr.name: attr for attr in nxclass.attribute}
        attributes = {**base_attributes, **overwrite_attributes}

        base_fields = {field.name: field for field in nxclass_parent.field}
        overwrite_fields = {field.name: field for field in nxclass.field}
        fields = {**base_fields, **overwrite_fields}

        base_groups = {group.name: group for group in nxclass_parent.group}
        overwrite_groups = {group.name: group for group in nxclass.group}
        groups = {**base_groups, **overwrite_groups}

        for attr in attributes.values():
            occurs = _occurs(1, 1, attr.optional, attr.recommended)
            self._print(indent, attr.name, attr.type, occurs)

        for field in fields.values():
            occurs = _occurs(
                field.minOccurs, field.maxOccurs, field.optional, field.recommended
            )
            self._print(indent, field.name, field.type, occurs)

        for group in groups.values():
            occurs = _occurs(
                group.minOccurs, group.maxOccurs, group.optional, group.recommended
            )
            self._create_group(group, occurs, indent=indent)

    def _print(self, indent: int, *args):
        print(" " * indent, *args)

    def _get_definition(self, name: str) -> nxdl_models.Definition:
        definition = self._definitions.get(name)
        if definition:
            return definition
        definition = load_nxdl_definition(name, **self._repo_options)
        self._definitions[name] = definition
        return definition


def _occurs(minOccurs, maxOccurs, optional, recommended):
    optional = optional or recommended
    if optional:
        minOccurs = 0
    if not isinstance(maxOccurs, int):
        maxOccurs = float("inf")
    return f"[{minOccurs}, {maxOccurs}]"
