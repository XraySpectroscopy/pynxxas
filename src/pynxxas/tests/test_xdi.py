from ..io import xdi


def test_is_xdi(xdi_file):
    assert xdi.is_xdi_file(xdi_file)


def test_read_xdi(xdi_file):
    model = xdi.read_xdi(xdi_file)

    # Fields
    assert model.facility.energy.magnitude == 7
    assert str(model.facility.energy.units) == "GeV"

    # User ccomments
    comments = [
        "room temperature",
        "measured at beamline 13-ID-C",
        "vert slits = 0.3 x 0.3mm (at ~50m)",
    ]
    assert model.comments == comments

    # XAS data
    assert model.data.energy.magnitude.tolist() == [7509, 7519]
    assert str(model.data.energy.units) == "eV"

    assert model.data.mutrans.magnitude.tolist() == [-0.51329170, -0.78493490]
    assert str(model.data.mutrans.units) == ""

    assert model.data.i0.magnitude.tolist() == [165872.70, 161255.70]
    assert str(model.data.i0.units) == ""
