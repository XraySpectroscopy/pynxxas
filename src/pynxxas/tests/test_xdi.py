from ..io import xdi


def test_is_xdi(xdi_file):
    assert xdi.is_xdi_file(xdi_file)


def test_load_xdi_file(xdi_file):
    models = list(xdi.load_xdi_file(xdi_file))
    assert len(models) == 1
    model_instance = models[0]

    # Fields
    assert model_instance.facility.energy.magnitude == 7
    assert str(model_instance.facility.energy.units) == "GeV"

    # User ccomments
    comments = [
        "room temperature",
        "measured at beamline 13-ID-C",
        "vert slits = 0.3 x 0.3mm (at ~50m)",
    ]
    assert model_instance.comments == comments

    # XAS data
    assert model_instance.data.energy.magnitude.tolist() == [7509, 7519]
    assert str(model_instance.data.energy.units) == "eV"

    assert model_instance.data.mutrans.magnitude.tolist() == [-0.51329170, -0.78493490]
    assert str(model_instance.data.mutrans.units) == ""

    assert model_instance.data.i0.magnitude.tolist() == [165872.70, 161255.70]
    assert str(model_instance.data.i0.units) == ""
