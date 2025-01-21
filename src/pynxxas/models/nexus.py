"""NeXus data model_instance"""

from typing import Dict, Literal, List, Optional, Any

try:
    from enum import StrEnum
except ImportError:
    from strenum import StrEnum

import pydantic
import periodictable

from . import units

# fmt: off
ATOMIC_SYMBOLS = [e.symbol for e in periodictable.elements][1:]

XRAY_EDGES = ("K", "L1", "L2", "L3", "M1", "M2", "M3", "M4", "M5",
              "N1", "N2", "M3", "N4", "N5", "N6", "N7",
              "O1", "O2", "O3", "P1", "P2", "P3")

XRAY_LINES = ("K-L1", "K-L2", "K-L3", "K-M1", "K-M2", "K-M3")

XAS_MODES = ("transmission", "fy")
# fmt: on

AtomicSymbol = StrEnum("AtomicSymbol", {s: s for s in ATOMIC_SYMBOLS})
XRayEdge = StrEnum("XRayEdge", {s: s for s in XRAY_EDGES})
XRayLines = StrEnum("XRayLines", {s: s for s in XRAY_LINES})
XasMode = StrEnum("XRayMode", {s: s for s in XAS_MODES})


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


class NxDataModel(NxClass, NxGroup, nx_class="NXdata"):
    NX_class: Literal["NXdata"] = pydantic.Field(default="NXdata", alias="@NX_class")
    signal: Literal["intensity"] = pydantic.Field(default="intensity", alias="@signal")
    axes: List[str] = pydantic.Field(default=["energy"], alias="@axes")
    energy: NxLinkModel
    intensity: NxLinkModel


class NxInstrumentName(NxField):
    value: Optional[str]
    short_name: Optional[str] = pydantic.Field(alias="@short_name")


class NxInstrument(NxClass, NxGroup, nx_class="NXinstrument"):
    NX_class: Literal["NXinstrument"] = pydantic.Field(
        default="NXinstrument", alias="@NX_class"
    )
    name: Optional[NxInstrumentName] = None


class NxElement(NxClass, NxGroup, nx_class="NXelement"):
    NX_class: Literal["NXelement"] = pydantic.Field(
        default="NXelement", alias="@NX_class"
    )
    symbol: Optional[AtomicSymbol] = None
    atomic_number: Optional[int] = None


class NxEntryClass(StrEnum):
    NXentry = "NXentry"
    NXsubentry = "NXsubentry"


class NxXasMode(NxClass, NxGroup, nx_class="NXxas_mode"):
    NX_class: Literal["NXxas_mode"] = pydantic.Field(
        default="NXxas_mode", alias="@NX_class"
    )
    name: Optional[XasMode] = None
    emission_lines: Optional[XRayLines] = None


class NxEdge(NxClass, NxGroup, nx_class="NXedge"):
    NX_class: Literal["NXedge"] = pydantic.Field(default="NXedge", alias="@NX_class")
    name: Optional[XRayEdge] = None


class NxXasModel(NxClass, NxGroup, nx_class="NXxas"):
    NX_class: NxEntryClass = pydantic.Field(default="NXentry", alias="@NX_class")
    definition: Literal["NXxas"] = "NXxas"
    mode: NxXasMode
    element: NxElement
    edge: NxEdge
    calculated: bool = False
    energy: units.PydanticQuantity = units.as_quantity([])
    intensity: units.PydanticQuantity = units.as_quantity([])
    title: Optional[str] = None
    plot: Optional[NxDataModel] = None
    instrument: Optional[NxInstrument] = None

    @pydantic.model_validator(mode="after")
    def set_title(self) -> "NxXasModel":
        if self.element is not None and self.edge is not None:
            title = f"{self.element.symbol} {self.edge.name}"
            if self.instrument is not None and self.instrument.name is not None:
                title = f"{self.instrument.name.value}: {title}"
            self.title = f"{title} ({self.mode.name})"
        if self.plot is None:
            energy = NxLinkModel(target_name="../energy")
            intensity = NxLinkModel(target_name="../intensity")
            self.plot = NxDataModel(energy=energy, intensity=intensity)
        return self

    def has_data(self) -> bool:
        return bool(self.energy.size and self.intensity.size)
