import pint
import pydantic
from pydantic_core import core_schema
from pydantic.json_schema import JsonSchemaValue

from typing import Any, Sequence, Union, List, Annotated

_REGISTRY = pint.UnitRegistry()
_REGISTRY.formatter.default_format = "~"  # unit symbols instead of full unit names


def as_quantity(value: Union[str, pint.Quantity, Sequence]) -> pint.Quantity:
    if isinstance(value, pint.Quantity):
        return value
    if (
        isinstance(value, Sequence)
        and len(value) == 2
        and (isinstance(value[1], str) or value[1] is None)
    ):
        value, units = value
    else:
        units = None
    return _REGISTRY.Quantity(value, units)


def as_units(value: Union[str, pint.Unit]) -> pint.Unit:
    if isinstance(value, pint.Unit):
        return value
    return _REGISTRY.parse_units(value)


class _QuantityPydanticAnnotation:
    # https://docs.pydantic.dev/latest/concepts/types/#handling-third-party-types

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: pydantic.GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        def serialize(value: Any) -> List:
            value = as_quantity(value)
            return [value.magnitude.tolist(), str(value.units)]

        json_schema = core_schema.chain_schema(
            [
                core_schema.no_info_plain_validator_function(as_quantity),
            ]
        )

        return core_schema.json_or_python_schema(
            json_schema=json_schema,
            python_schema=core_schema.union_schema(
                [
                    # check if it's an instance first before doing any further work
                    core_schema.is_instance_schema(pint.Quantity),
                    json_schema,
                ]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(serialize),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        _core_schema: core_schema.CoreSchema,
        handler: pydantic.GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        return handler(
            core_schema.union_schema(
                [
                    core_schema.float_schema(),
                    core_schema.list_schema(core_schema.float_schema()),
                ]
            )
        )


PydanticQuantity = Annotated[pint.Quantity, _QuantityPydanticAnnotation]
