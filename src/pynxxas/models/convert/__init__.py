from typing import Type, Generator
import pydantic

from . import xdi
from . import nexus
from .. import XdiModel
from .. import NxXasModel


def convert_model(
    instance: pydantic.BaseModel, model_type: Type[pydantic.BaseModel]
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
