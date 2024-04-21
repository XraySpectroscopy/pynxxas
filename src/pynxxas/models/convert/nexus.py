from typing import Generator
from .. import NxXasModel


def to_nxxas(nxxas_model: NxXasModel) -> Generator[NxXasModel, None, None]:
    yield nxxas_model


def from_nxxas(nxxas_model: NxXasModel) -> Generator[NxXasModel, None, None]:
    yield nxxas_model
