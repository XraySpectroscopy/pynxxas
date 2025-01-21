import pytest
from ..models import NxXasModel
from ..io.xdi import load_xdi_file


@pytest.fixture()
def xdi_file(tmp_path):
    filename = tmp_path / "data.xdi"
    with open(filename, "w") as fh:
        fh.write(_XDI_CONTENT)
    return filename


@pytest.fixture()
def xdi_model(xdi_file):
    return next(load_xdi_file(xdi_file))


@pytest.fixture()
def nxxas_model():
    return NxXasModel(**_NXXAS_CONTENT)


_NXXAS_CONTENT = {
    "edge": "K",
    "mode": {
        "@NX_class": "NXxas_mode",
        "name": "transmission",
    },
    "element": {
        "@NX_class": "NXelement",
        "symbol": "Co",
    },
    "energy": [[7509, 7519], "eV"],
    "intensity": [[-0.51329170, -0.78493490], ""],
}

_XDI_CONTENT = """
# XDI/1.0 GSE/1.0
# Column.1: energy eV
# Column.2: mutrans
# Column.3: i0
# Element.edge: K
# Element.symbol: Co
# Scan.edge_energy: 7709.0
# Mono.name: Si 111
# Mono.d_spacing: 3.13555
# Beamline.name: 13-ID-C
# Beamline.collimation: none
# Beamline.harmonic_rejection: detuned
# Facility.name: APS
# Facility.energy: 7.00 GeV
# Facility.xray_source: APS undulator A
# Scan.start_time: 2001-06-26T21:21:20
# Detector.I0: 10cm  N2
# Detector.I1: 10cm  N2
# Sample.name: Co metal foil
# Sample.prep: standard foil (Joe Wong boxed set)
# ///
# room temperature
# measured at beamline 13-ID-C
# vert slits = 0.3 x 0.3mm (at ~50m)
#----
#   energy      mutrans          i0
  7509.0000      -0.51329170        165872.70
  7519.0000      -0.78493490        161255.70
"""
