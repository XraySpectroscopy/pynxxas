Validate NXDL definitions
=========================

Validate all NXDL definitions from the official NeXus repository

.. code:: bash

    nxdl_validate

Validate one or more specific NXDL definitions from the official NeXus repository

.. code:: bash

    nxdl_validate NXentry NXtomo

Validate from another NeXus repository

.. code:: bash

    nxdl_validate --url https://github.com/XraySpectroscopy/nexus_definitions.git NXxas_new

Validate from a local NeXus repository

.. code:: bash

    nxdl_validate --dir /home/${USER}/projects/definitions NXsample NXfluo NXmx
