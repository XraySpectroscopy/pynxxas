from ..models import NxXasModel


def test_nxxas():
    data = {
        "@NX_class": "NXsubentry",
        "definition": "NXxas",
        "mode": "transmission",
        "element": "Fe",
        "absorption_edge": "K",
        "energy": [[7, 7.1], "keV"],
        "intensity": [10, 20],
    }
    model_instance = NxXasModel(**data)

    expected = _expected_content("NXsubentry", [[7, 7.1], "keV"], [[10, 20], ""])
    assert model_instance.model_dump() == expected


def test_nxxas_defaults():
    data = {
        "mode": "transmission",
        "element": "Fe",
        "absorption_edge": "K",
    }
    model_instance = NxXasModel(**data)

    expected = _expected_content("NXentry", [[], ""], [[], ""])
    assert model_instance.model_dump() == expected


def test_nxxas_fill_data():
    data = {
        "mode": "transmission",
        "element": "Fe",
        "absorption_edge": "K",
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
        "mode": "transmission",
        "element": "Fe",
        "absorption_edge": "K",
        "energy": energy,
        "intensity": intensity,
        "title": "Fe K (transmission)",
        "instrument": None,
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
