from typing import Generator

from .. import XdiModel
from .. import NxXasModel


def to_nxxas(xdi_model: XdiModel) -> Generator[NxXasModel, None, None]:
    has_mu = xdi_model.data.mutrans is not None or xdi_model.data.normtrans is not None
    has_fluo = (
        xdi_model.data.mufluor is not None or xdi_model.data.normfluor is not None
    )
    if not has_mu and not has_fluo:
        return

    data = {
        "element": xdi_model.element.symbol,
        "absorption_edge": xdi_model.element.edge,
    }

    if has_mu and has_fluo:
        data["NX_class"] = "NXsubentry"
    else:
        data["NX_class"] = "NXentry"

    if xdi_model.facility and xdi_model.facility.name:
        if xdi_model.beamline and xdi_model.beamline.name:
            name = {
                "value": f"{xdi_model.facility.name}-{xdi_model.beamline.name}",
                "@short_name": xdi_model.beamline.name,
            }
        else:
            name = {"value": xdi_model.facility.name}
        data["instrument"] = {"name": name}

    if has_mu:
        nxxas_model = NxXasModel(mode="transmission", **data)
        nxxas_model.energy = xdi_model.data.energy
        if xdi_model.data.mutrans is not None:
            nxxas_model.intensity = xdi_model.data.mutrans
        else:
            nxxas_model.intensity = xdi_model.data.normtrans
        yield nxxas_model

    if has_fluo:
        nxxas_model = NxXasModel(mode="fluorescence yield", **data)
        nxxas_model.energy = xdi_model.data.energy
        if xdi_model.data.mufluor is not None:
            nxxas_model.intensity = xdi_model.data.mufluor
        else:
            nxxas_model.intensity = xdi_model.data.normfluor
        yield nxxas_model


def from_nxxas(nxxas_model: NxXasModel) -> Generator[XdiModel, None, None]:
    xdi_model = XdiModel()
    xdi_model.element.symbol = nxxas_model.element
    xdi_model.element.edge = nxxas_model.absorption_edge
    xdi_model.data.energy = nxxas_model.energy
    if nxxas_model.mode == "transmission":
        xdi_model.data.mutrans = nxxas_model.intensity
    elif nxxas_model.mode == "fluorescence yield":
        xdi_model.data.mufluor = nxxas_model.intensity
    yield xdi_model
