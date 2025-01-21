"""File formats
"""

from typing import Generator

import pydantic

from . import xdi
from . import nexus
from .. import models
from .url_utils import UrlType


def load_models(url: UrlType) -> Generator[pydantic.BaseModel, None, None]:
    if xdi.is_xdi_file(url):
        yield from xdi.load_xdi_file(url)
    elif nexus.is_nexus_file(url):
        yield from nexus.load_nexus_file(url)
    else:
        raise NotImplementedError(f"File format not supported: {url}")


def save_model(model_instance: pydantic.BaseModel, url: UrlType) -> None:
    if isinstance(model_instance, models.NxXasModel):
        nexus.save_nexus_file(model_instance, url)
    elif isinstance(model_instance, models.XdiModel):
        xdi.save_xdi_file(model_instance, url)
    else:
        raise NotImplementedError(
            f"Saving of {type(model_instance).__name__} not implemented"
        )
