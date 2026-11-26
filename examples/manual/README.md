# Manual conversion examples

These examples convert beamline data by hand to NeXus (NXxas). Each folder has
the original data files and a `convert_to_nexus.py` script. The scripts are a
proof of principle for discussion about the formats, and they drive the
development of pynxxas and NXxas. They are guides, not tools for real use. The
plan is to move the reading of text files and the basic processing (pre-edge
subtraction and normalization) into pynxxas, so that the conversion does not
need xraylarch.

| Example           | Data                                           | `intensity`    | `energy` |
| ----------------- | ---------------------------------------------- | -------------- | -------- |
| Fe_XDIFiles       | 3 XDI files, Fe K edge, transmission           | normalized     | eV       |
| KEK_PFdata        | 1 file, fluorescence                           | normalized     | eV       |
| MultiElementFluor | 12 XDI-like files, V K edge, fluorescence      | normalized     | eV       |
| BlissMultiModal   | HDF5, As K edge, transmission and fluorescence | not normalized | keV      |
| SLS_Debye         | HDF5, Ni K edge, time-resolved transmission    | absorbance     | eV       |

## Fe_XDIFiles

Fe foil, hematite (Fe2O3) and wustite (FeO), measured at NSLS-II BMM (06BM)
with I0, It, and Ir. The script writes the three XDI files to one NeXus file.

- The Fe foil is in the reference position, so its absorbance is ln(It/Ir).
- The NXcollection group `raw_data` holds the columns of the original XDI file
  without changes, one dataset for each column.

Source, without changes: the BMM standards library of the National Institute of
Standards and Technology (NIST),
<https://github.com/bruceravel/bmm-standards/tree/main/Data/Fe>.

## KEK_PFdata

Fluorescence XAFS from Photon Factory, KEK, recorded as a function of angle.

## MultiElementFluor

V K-edge fluorescence XAFS, measured with a 4-element detector. The original
files have the columns "V Ka" and "Dead-time Correction Factor" for MCAs 1 to
4. The script sums the dead-time corrected channels to make `ifluor`.

## BlissMultiModal

As K-edge EXAFS in transmission and fluorescence, with several channels
recorded at the same time. The script does not use xraylarch. `intensity` is
log(I0/It) for transmission and log(Ifluo/(I0*Lt)) for fluorescence.

| HDF5 dataset     | Content                                        |
| ---------------- | ---------------------------------------------- |
| `energy_enc`     | energy in keV                                  |
| `p201_1_bkg_sub` | I0                                             |
| `p201_3_bkg_sub` | I1                                             |
| `p201_5_bkg_sub` | I2                                             |
| `xmapd16_det<i>` | MCA, with "roi1" as the fluorescence signal    |

## SLS_Debye

Ni K-edge transmission QEXAFS of NiO at the Swiss Light Source.
Run `python examples/manual/SLS_Debye/convert_to_nexus.py` from the repository
root to convert `S04301_master.h5` to `SLS_Debye.nxs` in the same folder.
The default plot shows 20 sweeps against elapsed time and energy. It uses
the recorded sample absorbance, with simultaneous reference absorbance as
an auxiliary signal. The original transmission arrays are in `raw_data`.
