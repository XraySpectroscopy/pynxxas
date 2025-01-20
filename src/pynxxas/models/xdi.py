"""XAS Data Interchange (XDI) data model_instance
"""

import datetime
from typing import Optional, List, Any, Mapping

import pydantic

from . import units


class XdiBaseModel(pydantic.BaseModel, extra="allow"):
    pass


class XdiFacilityNamespace(XdiBaseModel):
    name: Optional[str] = None
    energy: Optional[units.PydanticQuantity] = None
    current: Optional[units.PydanticQuantity] = None
    xray_source: Optional[str] = None


class XdiBeamlineNamespace(XdiBaseModel):
    name: Optional[str] = None
    collimation: Optional[str] = None
    focusing: Optional[str] = None
    harmonic_rejection: Optional[str] = None


class XdiMonoNamespace(XdiBaseModel):
    name: Optional[str] = None
    d_spacing: Optional[units.PydanticQuantity] = None


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
    i0: Optional[str] = None
    itrans: Optional[str] = None
    ifluor: Optional[str] = None
    irefer: Optional[str] = None

    @pydantic.model_validator(mode="before")
    @classmethod
    def resolve_aliases(cls, data: Any) -> Any:
        if not isinstance(data, Mapping):
            return data
        data = dict(data)
        for alias, target in XDI_ARRAY_ALIASES.items():
            if alias in data:
                print("resolve aliase ", alias, target)
                data[target] = data[alias]
        return data


class XdiSampleNamespace(XdiBaseModel):
    name: Optional[str] = None
    id: Optional[str] = None
    stoichiometry: Optional[str] = None
    prep: Optional[str] = None
    experimenters: Optional[str] = None
    temperature: Optional[units.PydanticQuantity] = None
    pressure: Optional[units.PydanticQuantity] = None
    ph: Optional[units.PydanticQuantity] = None
    eh: Optional[units.PydanticQuantity] = None
    volume: Optional[units.PydanticQuantity] = None
    porosity: Optional[units.PydanticQuantity] = None
    density: Optional[units.PydanticQuantity] = None
    concentration: Optional[units.PydanticQuantity] = None
    resistivity: Optional[units.PydanticQuantity] = None
    viscosity: Optional[units.PydanticQuantity] = None
    electric_field: Optional[units.PydanticQuantity] = None
    magnetic_field: Optional[units.PydanticQuantity] = None
    magnetic_moment: Optional[units.PydanticQuantity] = None
    crystal_structure: Optional[units.PydanticQuantity] = None
    opacity: Optional[units.PydanticQuantity] = None
    electrochemical_potential: Optional[units.PydanticQuantity] = None


class XdiScanNamespace(XdiBaseModel):
    start_time: Optional[datetime.datetime] = None
    end_time: Optional[datetime.datetime] = None
    edge_energy: Optional[units.PydanticQuantity] = None


class XdiElementNamespace(XdiBaseModel):
    symbol: Optional[str] = None
    edge: Optional[str] = None
    reference: Optional[str] = None
    ref_edge: Optional[str] = None


class XdiData(XdiBaseModel):
    energy: Optional[units.PydanticQuantity] = None
    angle: Optional[units.PydanticQuantity] = None
    i0: Optional[units.PydanticQuantity] = None
    itrans: Optional[units.PydanticQuantity] = None
    ifluor: Optional[units.PydanticQuantity] = None
    irefer: Optional[units.PydanticQuantity] = None
    mutrans: Optional[units.PydanticQuantity] = None
    mufluor: Optional[units.PydanticQuantity] = None
    murefer: Optional[units.PydanticQuantity] = None
    normtrans: Optional[units.PydanticQuantity] = None
    normfluor: Optional[units.PydanticQuantity] = None
    normrefer: Optional[units.PydanticQuantity] = None
    k: Optional[units.PydanticQuantity] = None
    chi: Optional[units.PydanticQuantity] = None
    chi_mag: Optional[units.PydanticQuantity] = None
    chi_pha: Optional[units.PydanticQuantity] = None
    chi_re: Optional[units.PydanticQuantity] = None
    chi_im: Optional[units.PydanticQuantity] = None
    r: Optional[units.PydanticQuantity] = None
    chir_mag: Optional[units.PydanticQuantity] = None
    chir_pha: Optional[units.PydanticQuantity] = None
    chir_re: Optional[units.PydanticQuantity] = None
    chir_im: Optional[units.PydanticQuantity] = None


class XdiModel(XdiBaseModel):
    element: XdiElementNamespace = XdiElementNamespace()
    scan: XdiScanNamespace = XdiScanNamespace()
    mono: XdiMonoNamespace = XdiMonoNamespace()
    beamline: XdiBeamlineNamespace = XdiBeamlineNamespace()
    facility: XdiFacilityNamespace = XdiFacilityNamespace()
    detector: XdiDetectorNamespace = XdiDetectorNamespace()
    sample: XdiSampleNamespace = XdiSampleNamespace()
    comments: List[str] = list()
    data: XdiData = XdiData()
