Data models
===========

Data from different data formats are represented in memory as a *Pydantic* models.
You can convert between different models and save/load models from file.

NeXus models
------------

Build an *NXxas* model instance in steps:

.. code-block:: python

    from pynxxas.models import NxXasModel

    nxxas_model = NxXasModel(
        mode={"name": "transmission"}, element={"symbol": "Fe"}, edge={"name": "K"}
    )
    nxxas_model.energy = [7, 7.1], "keV"
    nxxas_model.intensity = [10, 20]

Create an *NXxas* model instance from a dictionary and convert back to a dictionary:

.. code-block:: python

    data_in = {
        "@NX_class": "NXsubentry",
        "mode": {"name": "transmission"},
        "element": {"symbol": "Fe"},
        "edge": {"name": "K"},
        "energy": [[7, 7.1], "keV"],
        "intensity": [10, 20],
    }

    nxxas_model = NxXasModel(**data_in)
    data_out = nxxas_model.model_dump()
