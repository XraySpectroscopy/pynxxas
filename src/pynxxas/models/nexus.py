"""NeXus data model_instance"""

from typing import Dict, Literal, List, Optional, Any, get_args

import pydantic

from . import units

# fmt: off
AtomicSymbol = Literal[
    "H", "He",
    "Li", "Be", "B", "C", "N", "O", "F", "Ne",
    "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar",
    "K", "Ca", "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn", "Ga", "Ge", "As", "Se", "Br", "Kr",
    "Rb", "Sr", "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn", "Sb", "Te", "I", "Xe",
    "Cs", "Ba", "La",
    "Ce", "Pr", "Nd", "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu",
    "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg", "Tl", "Pb", "Bi", "Po", "At", "Rn",
    "Fr", "Ra", "Ac",
    "Th", "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es", "Fm", "Md", "No", "Lr",
    "Rf", "Db", "Sg", "Bh", "Hs", "Mt", "Ds", "Rg", "Cn", "Nh", "Fl", "Mc", "Lv", "Ts", "Og"
]

XRayEdge = Literal[
    "K",
    "L1", "L2", "L3",
    "M1", "M2", "M3", "M4", "M5",
    "N1", "N2", "M3", "N4", "N5", "N6", "N7",
    "O1", "O2", "O3",
    "P1", "P2", "P3"
]
# fmt: on

XRayLines = Literal["K-L1", "K-L2", "K-L3", "K-M1", "K-M2", "K-M3"]

XasMode = Literal["transmission", "fy"]


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
    NX_class: Literal["NXinstrument"] = pydantic.Field(
        default="NXinstrument", alias="@NX_class"
    )
    name: Optional[NxInstrumentName] = None


class NxElement(NxClass, NxGroup, nx_class="NxElement"):
    NX_class: Literal["NXelement"] = pydantic.Field(
        default="NXelement", alias="@NX_class"
    )
    symbol: Optional[AtomicSymbol] = None
    atomic_number: Optional[int] = None

    @pydantic.model_validator(mode="after")
    def check_atomic_number(self) -> "NxXasModel":
        if self.symbol is not None and self.atomic_number is not None:
            atomic_number = get_args(AtomicSymbol).index(self.symbol) + 1
            if self.atomic_number != atomic_number:
                raise ValueError(
                    f"The atomic number of '{self.symbol}' is {atomic_number} not {self.atomic_number}"
                )
        return self


class NxXasMode(NxClass, NxGroup, nx_class="NxXasMode"):
    NX_class: Literal["NXxas_mode"] = pydantic.Field(
        default="NXxas_mode", alias="@NX_class"
    )
    name: Optional[XasMode] = None
    emission_lines: Optional[XRayLines] = None


class NxEdge(NxClass, NxGroup, nx_class="NxEdge"):
    NX_class: Literal["NXedge"] = pydantic.Field(default="NXedge", alias="@NX_class")
    name: Optional[XRayEdge] = None


class NxXasModel(NxClass, NxGroup, nx_class="NxXas"):
    NX_class: Literal["NXentry", "NXsubentry"] = pydantic.Field(
        default="NXentry", alias="@NX_class"
    )
    definition: Literal["NXxas"] = "NXxas"
    mode: NxXasMode
    element: NxElement
    edge: NxEdge
    calculated: Optional[bool] = None
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
        if self.energy is None or self.intensity is None:
            return False
        return bool(self.energy.size and self.intensity.size)
