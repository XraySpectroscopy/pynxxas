"""NeXus data model_instance"""

from typing import Any, Dict, List, Literal, Optional

try:
    from enum import StrEnum
except ImportError:
    from strenum import StrEnum

import periodictable
import pydantic

from . import units


class NxGroup(pydantic.BaseModel, extra="allow"):
    pass


class NxField(pydantic.BaseModel):
    value: Any


class NxClass:
    _NXCLASSES: Dict[str, "NxClass"] = dict()

    def __init_subclass__(cls, nx_class: str, **kwargs):
        super().__init_subclass__(**kwargs)
        NxClass._NXCLASSES[nx_class] = cls


class NxLinkModel(pydantic.BaseModel):
    target_name: str
    target_filename: Optional[str] = None


class NxDataModel(NxClass, NxGroup, nx_class="NxData"):
    NX_class: Literal["NXdata"] = pydantic.Field(default="NXdata", alias="@NX_class")
    signal: Literal["intensity"] = pydantic.Field(default="intensity", alias="@signal")
    axes: List[str] = pydantic.Field(default=["energy"], alias="@axes")
    energy: NxLinkModel
    intensity: NxLinkModel


class NxInstrumentName(NxField):
    value: Optional[str]
    short_name: Optional[str] = pydantic.Field(alias="@short_name")


class NxInstrument(NxClass, NxGroup, nx_class="NxInstrument"):
    NX_class: Literal["NxInstrument"] = pydantic.Field(
        default="NxInstrument", alias="@NX_class"
    )
    name: Optional[NxInstrumentName] = None


class NxEntryClass(StrEnum):
    NXentry = "NXentry"
    NXsubentry = "NXsubentry"


class NxXasMode(StrEnum):
    transmission = "transmission"
    fluorescence_yield = "fluorescence yield"


ChemicalElement = StrEnum(
    "ChemicalElement", {el.symbol: el.symbol for el in periodictable.elements}
)

XRayAbsorptionEdge = StrEnum(
    "XRayAbsorptionEdge", {s: s for s in ("K", "L1", "L2", "L3")}
)

XRayEmissionLines = StrEnum(
    "XRayEmissionLines",
    {s: s for s in ("K-L1", "K-L2", "K-L3", "K-M1", "K-M2", "K-M3")},
)


class NxXasModel(NxClass, NxGroup, nx_class="NXxas"):
    NX_class: NxEntryClass = pydantic.Field(alias="@NX_class", default="NXentry")
    definition: Literal["NXxas"] = "NXxas"
    mode: NxXasMode
    element: ChemicalElement
    absorption_edge: XRayAbsorptionEdge
    emission_lines: Optional[XRayEmissionLines] = None
    energy: units.PydanticQuantity = units.as_quantity([])
    intensity: units.PydanticQuantity = units.as_quantity([])
    title: Optional[str] = None
    plot: Optional[NxDataModel] = None
    instrument: Optional[NxInstrument] = None

    @pydantic.model_validator(mode="after")
    def set_title(self) -> "NxXasModel":
        if self.element is not None and self.absorption_edge is not None:
            title = f"{self.element} {self.absorption_edge}"
            if self.instrument is not None and self.instrument.name is not None:
                title = f"{self.instrument.name.value}: {title}"
            self.title = f"{title} ({self.mode})"
        if self.plot is None:
            energy = NxLinkModel(target_name="../energy")
            intensity = NxLinkModel(target_name="../intensity")
            self.plot = NxDataModel(energy=energy, intensity=intensity)
        return self

    def has_data(self) -> bool:
        return bool(self.energy.size and self.intensity.size)
