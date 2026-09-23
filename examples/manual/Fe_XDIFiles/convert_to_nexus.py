from pathlib import Path

import h5py
import larch
import numpy
from larch.io import read_xdi
from larch.xafs import pre_edge

THIS_DIRECTORY = Path(__file__).parent


def xdi2nexus(
    filename, nxroot, pre_edge_kws, chemical_formula=None, entry_name="entry"
):
    dat = read_xdi(str(filename))

    dat.mu = dat.mutrans * 1.0
    dat.array_labels[dat.array_labels.index("mutrans")] = "mu"

    pre_edge(dat, **pre_edge_kws)
    pre_offset = dat.pre_edge_details.pre_offset
    pre_slope = dat.pre_edge_details.pre_slope
    nvict = dat.pre_edge_details.nvict

    root = create_nxclass(nxroot, entry_name, "NXentry", default="plot")
    nxroot.attrs["default"] = entry_name
    root["definition"] = "NXxas_trans"
    root["is_experimental"] = True
    root["start_time"] = dat.attrs["scan"]["start_time"]

    root["energy"] = dat.energy
    root["energy"].attrs["units"] = "eV"
    root["intensity"] = dat.norm
    root["intensity"].attrs["units"] = "a.u."

    element = create_nxclass(root, "element", "NXelement")
    element["symbol"] = dat.attrs["element"]["symbol"]

    edge = create_nxclass(root, "edge", "NXabsorption_edge")
    edge["name"] = dat.attrs["element"]["edge"]
    if "edge_energy" in dat.attrs["scan"]:
        words = dat.attrs["scan"]["edge_energy"].split(maxsplit=1)
        edge["energy"] = float(words[0])
        edge["energy"].attrs["units"] = words[1] if len(words) > 1 else "eV"

    plot = create_nxclass(
        root, "plot", "NXdata", signal="intensity", axes="energy", energy_indices=0
    )
    plot["energy"] = h5py.SoftLink(root["energy"].name)
    plot["intensity"] = h5py.SoftLink(root["intensity"].name)
    plot["energy"].attrs["units"] = "eV"
    plot["title"] = "Normalized mu(E)"

    names = {}

    # sample
    sample = create_nxclass(root, "sample", "NXsample")
    for aname, value in dat.attrs["sample"].items():
        if aname.lower() in ("prep", "notes"):
            sample["description"] = value
            continue
        if aname.lower() == "stoichiometry":
            chemical_formula = value
            continue
        sample[aname] = value
        if aname.lower() == "name":
            names["sample"] = value
    if chemical_formula is not None:
        sample["chemical_formula"] = chemical_formula

    preline = f"{pre_offset:.12g} {pre_slope:+.12g}*energy"
    if nvict != 0:
        preline = f"({preline})*energy**(-{nvict})"

    columns = ", ".join(dat.attrs["column"].values())

    notes = f'''\
"""Reproduce the intensity of an NXxas_trans entry from its raw_data.

raw_data/data holds the XDI columns in file order: {columns}.
Written with xraylarch {larch.__version__}. Value found at conversion:
The data of instrument/itrans is derived as i0 * exp(-mutrans).
"""

from larch import Group
from larch.xafs import pre_edge


def get_intensity(entry):
    """Return the normalized absorbance from an h5py NXentry group."""
    data = entry["raw_data/data"][()]
    parameters = {{
        name: field[()] for name, field in entry["processing/parameters"].items()
    }}
    group = Group()
    pre_edge(data[:, 0], data[:, 1], group=group, **parameters)
    return group.norm
'''

    process = create_nxclass(root, "processing", "NXprocess")
    process.attrs["NX_class"] = "NXprocess"
    process["program"] = "xraylarch"
    process["version"] = larch.__version__
    nts = create_nxclass(process, "note", "NXnote")
    nts["data"] = notes
    nts["type"] = "text/x-python"

    parameters = create_nxclass(process, "parameters", "NXparameters")
    for name, value in dat.callargs.pre_edge.items():
        if value is None:
            continue
        parameters[name] = value
        if name in ("e0", "pre1", "pre2", "norm1", "norm2"):
            parameters[name].attrs["units"] = "eV"

    collection = create_nxclass(root, "raw_data", "NXcollection")
    collection["data"] = dat.data.T
    collection["data"].attrs["labels"] = list(dat.attrs["column"].values())

    inst = create_nxclass(root, "instrument", "NXinstrument")

    source = create_nxclass(inst, "source", "NXsource")
    source["type"] = "Synchrotron X-ray Source"
    source["probe"] = "x-ray"

    if "facility" in dat.attrs:
        for aname, value in dat.attrs["facility"].items():
            if aname.lower() == "energy":
                words = value.split(maxsplit=1)
                en_value = float(words[0])
                source["energy"] = en_value
                if len(words) > 1:
                    source["energy"].attrs["units"] = words[1]
            elif aname.lower() == "name":
                source["name"] = value
                names["facility"] = value

    for aname, value in dat.attrs["beamline"].items():
        if aname.lower() == "name":
            inst["name"] = value
            names["beamline"] = value

    title_words = [
        names.get("sample", filename.name),
        names.get("facility", ""),
        names.get("beamline", ""),
    ]
    root["title"] = (" ".join(title_words)).strip()

    # mono
    def parse_mono_string(mono_name):
        mono_type = "Si"
        for k in "()[]":
            mono_name = mono_name.replace(k, " ")
        for k in ("SiC", "Si", "Ge", "C"):
            mono_name = mono_name.replace(k, f"{k} ")

        words = mono_name.split(maxsplit=1)
        if words[0] in ("SiC", "Si", "Ge", "C"):
            mono_type = words[0]

        try:
            refl = words[1]
            if len(refl) > 3:
                refl = refl.replace(" ", ",").split(",")
            else:
                refl = (refl[0], refl[1], refl[2])

            refl = [int(w.strip()) for w in refl]
        except (IndexError, ValueError):
            refl = (1, 1, 1)
        return mono_type, refl

    if "mono" in dat.attrs:
        mono = dat.attrs["mono"]
        monochromator = create_nxclass(inst, "monochromator", "NXmonochromator")
        monochromator["energy"] = h5py.SoftLink(root["energy"].name)

        crystal = create_nxclass(monochromator, "crystal", "NXcrystal")
        if "name" in mono:
            mono_type, refl = parse_mono_string(mono["name"])
            crystal["type"] = mono_type
            crystal["reflection"] = numpy.array(refl)
        if "d_spacing" in mono:
            crystal["d_spacing"] = float(mono["d_spacing"])
            crystal["d_spacing"].attrs["units"] = "angstrom"

    i0 = create_nxclass(inst, "i0", "NXdetector")
    i0["data"] = dat.i0
    i0["description"] = dat.attrs["detector"]["i0"]

    itrans = create_nxclass(inst, "itrans", "NXdetector")
    itrans["data"] = dat.i0 * numpy.exp(-dat.mutrans)
    itrans["description"] = dat.attrs["detector"]["i1"]

    print(f"done. Wrote group {entry_name} in file {nxroot.filename}")


def create_nxclass(root, name, nx_class, **attrs):
    """Create NeXus class instance with attributes."""
    child = root.create_group(name)
    child.attrs["NX_class"] = nx_class
    for attr_name, value in attrs.items():
        child.attrs[attr_name] = value
    return child


def main(output_filename):
    common = {"pre2": -50, "norm1": 150, "nnorm": 2}
    with h5py.File(output_filename, "w") as nxroot:
        xdi2nexus(
            THIS_DIRECTORY / "fe_metal_rt.xdi",
            nxroot,
            {**common, "pre1": -150, "norm2": 855, "nvict": 0},
            chemical_formula="Fe",
            entry_name="fe_metal",
        )
        xdi2nexus(
            THIS_DIRECTORY / "fe2o3_rt.xdi",
            nxroot,
            {**common, "pre1": -165, "norm2": 840, "nvict": 2},
            chemical_formula="Fe2 O3",
            entry_name="fe2o3",
        )
        xdi2nexus(
            THIS_DIRECTORY / "feo_rt1.xdi",
            nxroot,
            {**common, "pre1": -210, "norm2": 960, "nvict": 1},
            chemical_formula="Fe O",
            entry_name="feo",
        )


if __name__ == "__main__":
    main(THIS_DIRECTORY / f"{THIS_DIRECTORY.name}.nxs")
