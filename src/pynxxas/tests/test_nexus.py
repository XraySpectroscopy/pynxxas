from ..models import NxXasModel


def test_nxxas():
    data = {
        "@NX_class": "NXsubentry",
        "definition": "NXxas",
        "mode": {
            "@NX_class": "NXxas_mode",
            "name": "transmission",
        },
        "element": {
            "@NX_class": "NXelement",
            "symbol": "Fe",
        },
        "edge": {
            "@NX_class": "NXedge",
            "name": "K",
        },
        "energy": [[7, 7.1], "keV"],
        "intensity": [10, 20],
    }
    model_instance = NxXasModel(**data)

    expected = _expected_content("NXsubentry", [[7.0, 7.1], "keV"], [[10, 20], ""])
    assert model_instance.model_dump() == expected


def test_nxxas_defaults():
    data = {
        "mode": {"name": "transmission"},
        "element": {"symbol": "Fe"},
        "edge": {"name": "K"},
    }
    model_instance = NxXasModel(**data)

    expected = _expected_content("NXentry", [[], ""], [[], ""])
    assert model_instance.model_dump() == expected


def test_nxxas_fill_data():
    data = {
        "mode": {
            "@NX_class": "NXxas_mode",
            "name": "transmission",
        },
        "element": {
            "@NX_class": "NXelement",
            "symbol": "Fe",
        },
        "edge": {
            "NX_class": "NXedge",
            "name": "K",
        },
    }
    model_instance = NxXasModel(**data)
    model_instance.energy = [7, 7.1], "keV"
    model_instance.intensity = [10, 20]

    expected = _expected_content("NXentry", [[7, 7.1], "keV"], [[10, 20], ""])
    assert model_instance.model_dump() == expected


def _expected_content(nx_class, energy, intensity):
    return {
        "NX_class": nx_class,
        "definition": "NXxas",
        "mode": {
            "NX_class": "NXxas_mode",
            "name": "transmission",
            "emission_lines": None,
        },
        "element": {
            "NX_class": "NXelement",
            "symbol": "Fe",
            "atomic_number": None,
        },
        "edge": {
            "NX_class": "NXedge",
            "name": "K",
        },
        "energy": energy,
        "intensity": intensity,
        "title": "Fe K (transmission)",
        "instrument": None,
        "calculated": False,
        "plot": {
            "NX_class": "NXdata",
            "axes": [
                "energy",
            ],
            "energy": {
                "target_filename": None,
                "target_name": "../energy",
            },
            "intensity": {
                "target_filename": None,
                "target_name": "../intensity",
            },
            "signal": "intensity",
        },
    }
