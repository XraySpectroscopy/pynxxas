from .. import models
from ..models import convert


def test_xdi_to_xdi(xdi_model):
    xdi_model = next(convert.convert_model(xdi_model, models.XdiModel))
    _assert_model(xdi_model)


def test_nxxas_to_nxxas(nxxas_model):
    nxxas_model = next(convert.convert_model(nxxas_model, models.NxXasModel))
    _assert_model(nxxas_model)


def test_xdi_to_nexus(xdi_model):
    nxxas_model = next(convert.convert_model(xdi_model, models.NxXasModel))
    _assert_model(nxxas_model)


def test_nexus_to_xdi(nxxas_model):
    xdi_model = next(convert.convert_model(nxxas_model, models.XdiModel))
    _assert_model(xdi_model)


def _assert_xdi_model(xdi_model: models.XdiModel):
    xdi_model.element.symbol = "Co"
    assert str(xdi_model.data.energy.units) == "eV"

    assert xdi_model.data.energy.magnitude.tolist() == [7509, 7519]
    assert str(xdi_model.data.energy.units) == "eV"

    assert xdi_model.data.mutrans.magnitude.tolist() == [-0.51329170, -0.78493490]
    assert str(xdi_model.data.mutrans.units) == ""


def _assert_nxxas_model(xdi_model: models.NxXasModel):
    xdi_model.element = "Co"
    assert str(xdi_model.energy.units) == "eV"

    assert xdi_model.energy.magnitude.tolist() == [7509, 7519]
    assert str(xdi_model.energy.units) == "eV"

    assert xdi_model.intensity.magnitude.tolist() == [-0.51329170, -0.78493490]
    assert str(xdi_model.intensity.units) == ""


_ASSERT_MODEL = {
    models.XdiModel: _assert_xdi_model,
    models.NxXasModel: _assert_nxxas_model,
}


def _assert_model(model_instance):
    _ASSERT_MODEL[type(model_instance)](model_instance)
