"""XAS Data Interchange (XDI) data model_instance"""

import datetime
from collections.abc import Mapping
from typing import Any

import pydantic

from . import units


class XdiBaseModel(pydantic.BaseModel, extra="allow"):
    pass


class XdiFacilityNamespace(XdiBaseModel):
    name: str | None = None
    energy: units.PydanticQuantity | None = None
    current: units.PydanticQuantity | None = None
    xray_source: str | None = None


class XdiBeamlineNamespace(XdiBaseModel):
    name: str | None = None
    collimation: str | None = None
    focusing: str | None = None
    harmonic_rejection: str | None = None


class XdiMonoNamespace(XdiBaseModel):
    name: str | None = None
    d_spacing: units.PydanticQuantity | None = None


# common alternate spellings of XDI arrays
XDI_ARRAY_ALIASES = {
    "monitor": "i0",
    "i1": "itrans",
    "itransmission": "itrans",
    "if": "ifluor",
    "ifl": "ifluor",
    "ifluo": "ifluor",
    "ifluorescence": "ifluor",
    "iref": "irefer",
    "ir": "irefer",
}


class XdiDetectorNamespace(XdiBaseModel):
    i0: str | None = None
    itrans: str | None = None
    ifluor: str | None = None
    irefer: str | None = None

    @pydantic.model_validator(mode="before")
    @classmethod
    def resolve_aliases(cls, data: Any) -> Any:
        if not isinstance(data, Mapping):
            return data
        data = dict(data)
        for alias, target in XDI_ARRAY_ALIASES.items():
            if alias in data:
                data[target] = data[alias]
        return data


class XdiSampleNamespace(XdiBaseModel):
    name: str | None = None
    id: str | None = None
    stoichiometry: str | None = None
    prep: str | None = None
    experimenters: str | None = None
    temperature: units.PydanticQuantity | None = None
    pressure: units.PydanticQuantity | None = None
    ph: units.PydanticQuantity | None = None
    eh: units.PydanticQuantity | None = None
    volume: units.PydanticQuantity | None = None
    porosity: units.PydanticQuantity | None = None
    density: units.PydanticQuantity | None = None
    concentration: units.PydanticQuantity | None = None
    resistivity: units.PydanticQuantity | None = None
    viscosity: units.PydanticQuantity | None = None
    electric_field: units.PydanticQuantity | None = None
    magnetic_field: units.PydanticQuantity | None = None
    magnetic_moment: units.PydanticQuantity | None = None
    crystal_structure: units.PydanticQuantity | None = None
    opacity: units.PydanticQuantity | None = None
    electrochemical_potential: units.PydanticQuantity | None = None


class XdiScanNamespace(XdiBaseModel):
    start_time: datetime.datetime | None = None
    end_time: datetime.datetime | None = None
    edge_energy: units.PydanticQuantity | None = None


class XdiElementNamespace(XdiBaseModel):
    symbol: str | None = None
    edge: str | None = None
    reference: str | None = None
    ref_edge: str | None = None


class XdiData(XdiBaseModel):
    energy: units.PydanticQuantity | None = None
    angle: units.PydanticQuantity | None = None
    i0: units.PydanticQuantity | None = None
    itrans: units.PydanticQuantity | None = None
    ifluor: units.PydanticQuantity | None = None
    irefer: units.PydanticQuantity | None = None
    mutrans: units.PydanticQuantity | None = None
    mufluor: units.PydanticQuantity | None = None
    murefer: units.PydanticQuantity | None = None
    normtrans: units.PydanticQuantity | None = None
    normfluor: units.PydanticQuantity | None = None
    normrefer: units.PydanticQuantity | None = None
    k: units.PydanticQuantity | None = None
    chi: units.PydanticQuantity | None = None
    chi_mag: units.PydanticQuantity | None = None
    chi_pha: units.PydanticQuantity | None = None
    chi_re: units.PydanticQuantity | None = None
    chi_im: units.PydanticQuantity | None = None
    r: units.PydanticQuantity | None = None
    chir_mag: units.PydanticQuantity | None = None
    chir_pha: units.PydanticQuantity | None = None
    chir_re: units.PydanticQuantity | None = None
    chir_im: units.PydanticQuantity | None = None


class XdiModel(XdiBaseModel):
    element: XdiElementNamespace = XdiElementNamespace()
    scan: XdiScanNamespace = XdiScanNamespace()
    mono: XdiMonoNamespace = XdiMonoNamespace()
    beamline: XdiBeamlineNamespace = XdiBeamlineNamespace()
    facility: XdiFacilityNamespace = XdiFacilityNamespace()
    detector: XdiDetectorNamespace = XdiDetectorNamespace()
    sample: XdiSampleNamespace = XdiSampleNamespace()
    comments: list[str] = []
    data: XdiData = XdiData()
