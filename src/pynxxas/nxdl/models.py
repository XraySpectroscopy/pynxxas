"""NXDL models for v2024.02"""

# TODO: Generate pydantic models dynamically

from enum import Enum
from typing import Optional, Union, List, Any, Mapping, Dict

import pydantic


class Item(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid")


class EnumerationItem(Item):
    value: str = pydantic.Field(alias="@value")
    doc: Optional[str] = None


class Enumeration(Item):
    item: List[EnumerationItem]


class DimensionItem(Item):
    index: int = pydantic.Field(alias="@index")
    required: bool = pydantic.Field(alias="@required")
    value: Optional[str] = pydantic.Field(alias="@value", default=None)
    ref: Optional[str] = pydantic.Field(alias="@ref", default=None)


class Dimensions(Item):
    rank: Optional[Union[int, str]] = pydantic.Field(alias="@rank", default=None)
    doc: Optional[str] = None
    dim: List[DimensionItem] = pydantic.Field(default_factory=list)

    @pydantic.model_validator(mode="before")
    @classmethod
    def fix_doc(cls, data: Any) -> Any:
        if not isinstance(data, Mapping):
            return data
        doc = data.get("doc")
        if isinstance(doc, str):
            return data
        # NXstxm (v2024.02)
        # https://github.com/nexusformat/definitions/pull/1373
        return {k: v for k, v in data.items() if k != "doc"}


class Attribute(Item):
    name: str = pydantic.Field(alias="@name")
    type: str = pydantic.Field(alias="@type")
    doc: Optional[str] = None
    deprecated: Optional[str] = pydantic.Field(alias="@deprecated", default=None)
    recommended: Optional[bool] = pydantic.Field(alias="@recommended", default=None)
    optional: Optional[bool] = pydantic.Field(alias="@optional", default=None)

    dimensions: Optional[Dimensions] = None
    enumeration: Optional[Enumeration] = None


class NameType(str, Enum):
    specified = "specified"
    any = "any"


class OccursString(str, Enum):
    unbounded = "unbounded"


class Interpretation(str, Enum):
    scalar = "scalar"
    spectrum = "spectrum"
    image = "image"
    rgb_image = "rgb-image"
    rgba_image = "rgba-image"
    hsl_image = "hsl-image"
    hsla_image = "hsla-image"
    cmyk_image = "cmyk-image"
    vertex = "vertex"


class Field(Item):
    type: str = pydantic.Field(alias="@type")
    name: str = pydantic.Field(alias="@name")
    nameType: NameType = pydantic.Field(alias="@nameType")
    doc: Optional[str] = None
    deprecated: Optional[str] = pydantic.Field(alias="@deprecated", default=None)
    recommended: Optional[bool] = pydantic.Field(alias="@recommended", default=None)
    optional: Optional[bool] = pydantic.Field(alias="@optional", default=None)
    minOccurs: pydantic.NonNegativeInt = pydantic.Field(alias="@minOccurs", default=0)
    maxOccurs: Union[pydantic.NonNegativeInt, OccursString] = pydantic.Field(
        alias="@maxOccurs", default="unbounded"
    )

    units: Optional[str] = pydantic.Field(alias="@units", default=None)
    signal: Optional[int] = pydantic.Field(alias="@signal", default=None)
    axis: Optional[int] = pydantic.Field(alias="@axis", default=None)
    primary: Optional[int] = pydantic.Field(alias="@primary", default=None)
    axes: Optional[str] = pydantic.Field(alias="@axes", default=None)
    stride: Optional[bool] = pydantic.Field(alias="@stride", default=None)
    data_offset: Optional[bool] = pydantic.Field(alias="@data_offset", default=None)
    interpretation: Optional[Interpretation] = pydantic.Field(
        alias="@interpretation", default=None
    )

    attribute: List[Attribute] = pydantic.Field(default_factory=list)
    dimensions: Optional[Dimensions] = None
    enumeration: Optional[Enumeration] = None


class Group(Item):
    type: str = pydantic.Field(alias="@type")
    name: Optional[str] = pydantic.Field(alias="@name", default=None)
    doc: Optional[str] = None
    deprecated: Optional[str] = pydantic.Field(alias="@deprecated", default=None)
    recommended: Optional[bool] = pydantic.Field(alias="@recommended", default=None)
    optional: Optional[bool] = pydantic.Field(alias="@optional", default=None)
    minOccurs: pydantic.NonNegativeInt = pydantic.Field(alias="@minOccurs", default=0)
    maxOccurs: Union[pydantic.NonNegativeInt, OccursString] = pydantic.Field(
        alias="@maxOccurs", default="unbounded"
    )

    attribute: List[Attribute] = pydantic.Field(default_factory=list)
    field: List[Field] = pydantic.Field(default_factory=list)
    group: List["Group"] = pydantic.Field(default_factory=list)
    link: List["Link"] = pydantic.Field(default_factory=list)

    @pydantic.model_validator(mode="after")
    def default_name(self) -> "Group":
        if self.name is None:
            self.name = self.type[2:].upper()
        return self

    @pydantic.model_validator(mode="before")
    @classmethod
    def fix_doc(cls, data: Any) -> Any:
        if not isinstance(data, Mapping):
            return data
        doc = data.get("doc")
        if not doc:
            return data
        if isinstance(doc, list) and len(doc) == 1:
            data = dict(data)
            data["doc"] = doc[0]
        return data


class Link(Item):
    name: str = pydantic.Field(alias="@name")
    target: str = pydantic.Field(alias="@target")
    doc: Optional[str] = None


class Choice(Item):
    name: str = pydantic.Field(alias="@name")
    group: List[Group]


class Symbol(Item):
    name: str = pydantic.Field(alias="@name")
    doc: str


class Symbols(Item):
    doc: Optional[str] = None
    symbol: List[Symbol] = pydantic.Field(default_factory=list)


class XmlNamespace(Item):
    name: str
    attributes: Dict[str, str]
    prefix: Optional[str] = None


class Definition(Item):
    xmlns: List[XmlNamespace]

    name: str = pydantic.Field(alias="@name")
    type: str = pydantic.Field(alias="@type")
    category: str = pydantic.Field(alias="@category")
    ignoreExtraGroups: bool = pydantic.Field(alias="@ignoreExtraGroups")
    ignoreExtraFields: bool = pydantic.Field(alias="@ignoreExtraFields")
    ignoreExtraAttributes: bool = pydantic.Field(alias="@ignoreExtraAttributes")

    extends: Optional[str] = pydantic.Field(alias="@extends", default=None)
    deprecated: Optional[str] = pydantic.Field(alias="@deprecated", default=None)
    doc: Optional[str] = None

    symbols: Optional[Symbols] = None
    attribute: List[Attribute] = pydantic.Field(default_factory=list)
    field: List[Field] = pydantic.Field(default_factory=list)
    group: List[Group] = pydantic.Field(default_factory=list)
    link: List[Link] = pydantic.Field(default_factory=list)
    choice: List[Choice] = pydantic.Field(default_factory=list)

    @pydantic.model_validator(mode="before")
    @classmethod
    def parse_xmlns(cls, data: Any) -> Any:
        if not isinstance(data, Mapping):
            return data

        # The default XML namespace (no prefix):
        #   "@xmlns" = "http://..."
        #
        # Prefixes of other XML namespaces:
        #   "@xmlns:<prefix>" = "http://..."
        #
        # Namespace attributes:
        #   "@<prefix>:<attribute>" = "..."

        xmlns = dict()
        for key, value in data.items():
            if key.startswith("@xmlns"):
                _, _, prefix = key.partition(":")
                if not prefix:
                    prefix = None
                xmlns[prefix] = {"name": value, "prefix": prefix, "attributes": dict()}

        parsed = dict()
        for key, value in data.items():
            if key.startswith("@xmlns"):
                continue
            elif ":" in key and key.startswith("@"):
                prefix, _, attribute = key.partition(":")
                xmlns[prefix[1:]]["attributes"][attribute] = value
            else:
                parsed[key] = value
        parsed["xmlns"] = list(xmlns.values())

        return parsed
