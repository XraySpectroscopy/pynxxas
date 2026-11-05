from collections.abc import Generator

import pydantic

from .. import NxXasModel, XdiModel
from . import nexus, xdi


def convert_model(
    instance: pydantic.BaseModel, model_type: type[pydantic.BaseModel]
) -> Generator[pydantic.BaseModel, None, None]:
    if isinstance(instance, model_type):
        yield instance

    mod_from = _CONVERT_MODULE.get(type(instance))
    mod_to = _CONVERT_MODULE.get(model_type)
    if mod_from is None or mod_to is None:
        raise NotImplementedError(
            f"Conversion from {type(instance).__name__} to {model_type.__name__} is not implemented"
        )

    for nxxas_model in mod_from.to_nxxas(instance):
        yield from mod_to.from_nxxas(nxxas_model)


_CONVERT_MODULE = {XdiModel: xdi, NxXasModel: nexus}
