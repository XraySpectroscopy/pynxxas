import logging
import pathlib
from glob import glob
from contextlib import contextmanager
from typing import Iterator, Generator

import pydantic

from .. import io
from .. import models
from ..models import convert

logger = logging.getLogger(__name__)


def convert_files(
    file_patterns: Iterator[str],
    output_filename: str,
    output_format: str,
    interactive: bool = False,
) -> int:
    model_type = models.MODELS[output_format]

    output_filename = pathlib.Path(output_filename)
    if output_filename.exists():
        if interactive:
            result = input(f"Overwrite {output_filename}? (y/[n])")
            if not result.lower() in ("y", "yes"):
                return 1
        output_filename.unlink()
    output_filename.parent.mkdir(parents=True, exist_ok=True)

    state = {"return_code": 0, "scan_number": 0, "filename": None}
    scan_number = 0
    for model_in in _iter_load_models(file_patterns, state):
        scan_number += 1
        for model_out in _iter_convert_model(model_in, model_type, state):
            if output_format == "nexus":
                output_url = f"{output_filename}?path=/dataset{scan_number:02}"
                if model_out.NX_class == "NXsubentry":
                    output_url = f"{output_url}/{model_out.mode.replace(' ', '_')}"
            else:
                basename = f"{output_filename.stem}_{scan_number:02}"
                if model_out.NX_class == "NXsubentry":
                    basename = f"{basename}_{model_out.mode.replace(' ', '_')}"
                output_url = output_filename.parent / basename + output_filename.suffix

            with _handle_error("saving", state):
                io.save_model(model_out, output_url)

    return state["return_code"]


def _iter_load_models(
    file_patterns: Iterator[str], state: dict
) -> Generator[pydantic.BaseModel, None, None]:
    for file_pattern in file_patterns:
        for filename in glob(file_pattern):
            filename = pathlib.Path(filename).absolute()
            state["filename"] = filename
            it_model_in = io.load_models(filename)
            while True:
                with _handle_error("loading", state):
                    try:
                        yield next(it_model_in)
                    except StopIteration:
                        break


def _iter_convert_model(
    model_in: Iterator[pydantic.BaseModel], model_type: str, state: dict
) -> Generator[pydantic.BaseModel, None, None]:
    it_model_out = convert.convert_model(model_in, model_type)
    while True:
        with _handle_error("converting", state):
            try:
                yield next(it_model_out)
            except StopIteration:
                break


@contextmanager
def _handle_error(action: str, state: dict) -> Generator[None, None, None]:
    try:
        yield
    except NotImplementedError as e:
        state["return_code"] = 1
        logger.warning("Error when %s '%s': %s", action, state["filename"], e)
    except Exception:
        state["return_code"] = 1
        logger.error("Error when %s '%s'", action, state["filename"], exc_info=True)
