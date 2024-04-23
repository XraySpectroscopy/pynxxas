import pint
import numpy
from pydantic import TypeAdapter


from ..models import units


def test_pydantic_quantity():
    ta = TypeAdapter(units.PydanticQuantity)
    _assert_quantity_equal(ta, 10)
    _assert_quantity_equal(ta, 10.5)
    _assert_quantity_equal(ta, 10.5, "eV")
    _assert_quantity_equal(ta, [10.5, 11.5])
    _assert_quantity_equal(ta, [10.5, 11.5], "eV")
    _assert_quantity_equal(ta, [10.5, 11.5], None)


def _assert_quantity_equal(ta: TypeAdapter, *args):
    expected = units.as_quantity(args)

    validated = ta.validate_python(args)
    assert isinstance(expected, pint.Quantity)
    numpy.testing.assert_equal(validated.magnitude, expected.magnitude)
    assert str(validated.units) == str(expected.units)

    validated = ta.validate_python(expected)
