pynxxas
=======

Library for reading and writing XAS data in `NeXus format <https://www.nexusformat.org/>`_.

The example files below show the NeXus files that pynxxas writes. Each link opens the file in the `myhdf5 <https://myhdf5.hdfgroup.org/>`_ web viewer.

The ``nxxas-convert`` command, which comes with pynxxas, converts these files with no custom code (see :doc:`howtoguides/convert_files`):

- :myhdf5:`XAS reference spectra (XDI files) <auto/converted.nxs>`

A custom script converts each of these files:

- :myhdf5:`Fe XAS NSLS-II BMM (transmission) <manual/Fe_XDIFiles/Fe_XDIFiles.nxs>`
- :myhdf5:`Fe XAS KEK (fluorescence) <manual/KEK_PFdata/KEK_PFdata.nxs>`
- :myhdf5:`V XANES APS (multi-detector fluorescence) <manual/MultiElementFluor/MultiElementFluor.nxs>`
- :myhdf5:`As XANES ESRF (transmission + reference + multi-detector fluorescence) <manual/BlissMultiModal/BlissMultiModal.nxs>`

.. toctree::
    :hidden:

    howtoguides
    tutorials
    api
