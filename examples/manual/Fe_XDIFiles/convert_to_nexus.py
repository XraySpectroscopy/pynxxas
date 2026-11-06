import contextlib
import io
import json
from pathlib import Path

import h5py
import numpy
from larch.io import read_ascii
from larch.io import read_xdi
from larch.io import write_ascii
from larch.utils import gformat
from larch.xafs import pre_edge

THIS_DIRECTORY = Path(__file__).parent

# XDI header key of the description of each ion chamber column
DETECTOR_KEYS = {"I0": "i0", "It": "i1", "Ir": "i2"}


def xdi2nexus(filename, nxroot, detectors):
    """Write one XDI file as an NXxas_trans entry.

    ``detectors`` maps each NXdetector name (i0, itrans, iref) to the column of
    the ion chamber in the XDI file. The xmu column is ln(i0/itrans).
    """
    entry_name = filename.stem
    asc = read_ascii(filename)
    dat = read_xdi(str(filename))

    dat.mu = dat.xmu * 1.0

    pre_edge(dat, pre1=-150, pre2=-50, norm1=150, norm2=750)
    pre_offset = dat.pre_edge_details.pre_offset
    pre_slope = dat.pre_edge_details.pre_slope
    nvict = dat.pre_edge_details.nvict

    root = create_nxclass(nxroot, entry_name, "NXentry", default="plot")
    nxroot.attrs["default"] = entry_name
    root["definition"] = "NXxas_trans"

    root["energy"] = dat.energy
    root["energy"].attrs["units"] = "eV"
    root["intensity"] = dat.norm
    root["intensity"].attrs["units"] = ""
    root["intensity"].attrs["type"] = "absorbance"
    root["intensity"].attrs["provenance"] = "measured"

    element = create_nxclass(root, "element", "NXelement")
    element["symbol"] = dat.attrs["element"]["symbol"]

    edge = create_nxclass(root, "edge", "NXabsorption_edge")
    edge["name"] = dat.attrs["element"]["edge"]

    plot = create_nxclass(
        root, "plot", "NXdata", signal="intensity", axes="energy", energy_indices=0
    )
    plot["energy"] = h5py.SoftLink(root["energy"].name)
    plot["intensity"] = h5py.SoftLink(root["intensity"].name)
    plot["energy"].attrs["units"] = "eV"
    plot["energy"].attrs["long_name"] = "Energy (eV)"
    plot["intensity"].attrs["long_name"] = "Normalized mu(E)"

    names = {}

    # sample
    sample = create_nxclass(root, "sample", "NXsample")
    for aname, value in dat.attrs["sample"].items():
        sample[aname] = value
        if aname.lower() == "name":
            names["sample"] = value

    # process
    kwargs = ", ".join([f"{k}={v}" for k, v in dat.callargs.pre_edge.items()])

    preline = f"pre_edge = {gformat(pre_offset, 12)} + {gformat(pre_slope, 12)}*energy"
    if nvict != 0:
        preline = f"({preline})*energy(-{dat.nvict})"

    proc = [
        "processing done with xraylarch version 0.9.80",
        f"larch.xafs.pre_edge(data, {kwargs})",
        "using the XDI columns in raw_data",
        "energy = raw_data/energy    # energy (eV)",
        f"mu = raw_data/xmu          # absorbance ln({detectors['i0']}/{detectors['itrans']})",
        f"edge_step = {gformat(dat.edge_step, 12)}",
        preline,
        "intensity = norm = (mu - pre_edge) /edge_step",
    ]

    notes = "\n".join(proc)

    columns = ["energy eV", "norm", *detectors]
    header = ["XDI/1.1"]
    header += [f"Column.{i + 1}: {name}" for i, name in enumerate(columns)]
    end_header = []
    target = header
    # Skip the XDI version line and the columns of the original file.
    for j in asc.header[1:]:
        if j.startswith("#"):
            j = j[1:].strip()
        if "---" in j:
            break
        if "///" in j:
            target = end_header
        if not j.startswith("Column."):
            target.append(j)

    header.append("Process.program: xraylarch")
    header.append("Process.version: 0.9.80")
    header.append(f"Process.command: pre_edge(data, {kwargs})")
    for i, p in enumerate(proc[3:]):
        header.append(f"Process.step{i + 1:d}: {p}")
    for j in end_header:
        if j.startswith("#"):
            j = j[1:].strip()
        header.append(j)

    process = create_nxclass(root, "processing", "NXprocess")
    process.attrs["NX_class"] = "NXprocess"
    process["program"] = "xraylarch"
    process["version"] = "0.9.80"
    nts = create_nxclass(process, "note", "NXnote")
    nts["data"] = notes
    nts["type"] = "text/plain"

    # raw_data: the columns of the XDI file without modification
    raw_data = create_nxclass(root, "raw_data", "NXcollection")
    labels = [name.split()[0] for name in dat.attrs["column"].values()]
    for label, units, column in zip(labels, dat.array_units, dat.data, strict=True):
        raw_data[label] = column
        if units:
            raw_data[label].attrs["units"] = units

    # scan
    scan = create_nxclass(root, "scan", "NXparameters")
    scan["headers"] = json.dumps(dat.attrs)
    scan["filename"] = filename.name

    for key, val in dat.attrs["scan"].items():
        scan[key] = val
    if getattr(dat, "comments", None) is not None:
        scan["comments"] = dat.comments

    inst = create_nxclass(root, "instrument", "NXinstrument")

    # NXsource requires a name: write it only when the XDI file gives the facility.
    if "facility" in dat.attrs:
        source = create_nxclass(inst, "source", "NXsource")
        source["type"] = "Synchrotron X-ray Source"
        source["probe"] = "x-ray"
        for aname, value in dat.attrs["facility"].items():
            if aname.lower() == "energy":
                words = value.split(maxsplit=1)
                en_value = float(words[0])
                source["energy"] = en_value
                if len(words) > 1:
                    source["energy"].attrs["units"] = words[1]
            else:
                source[aname] = value
                if aname.lower() == "name":
                    names["facility"] = value

    bl = create_nxclass(inst, "beamline", "NXparameters")
    for aname, value in dat.attrs["beamline"].items():
        bl[aname] = value
        if aname.lower() == "name":
            names["beamline"] = value

    title_words = [
        names.get("sample", filename.name),
        names.get("facility", ""),
        names.get("beamline", ""),
    ]
    root["title"] = (" ".join(title_words)).strip()

    # mono
    d_spacing = dat.attrs["mono"].get("d_spacing", 3.13550)
    mono_name = dat.attrs["mono"].get("name", "Si 111")

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
        except Exception:
            refl = (1, 1, 1)
        return mono_type, refl

    monochromator = create_nxclass(inst, "monochromator", "NXmonochromator")
    monochromator["energy"] = h5py.SoftLink(root["energy"].name)

    crystal = create_nxclass(monochromator, "crystal", "NXcrystal")
    mono_type, refl = parse_mono_string(mono_name)
    crystal["type"] = mono_type
    crystal["reflection"] = numpy.array(refl)
    crystal["reflection"].attrs["units"] = ""
    crystal["d_spacing"] = float(d_spacing)
    crystal["d_spacing"].attrs["units"] = "angstrom"

    for name, column in detectors.items():
        detector = create_nxclass(inst, name, "NXdetector")
        detector["data"] = getattr(dat, column)
        detector["data"].attrs["units"] = dat.array_units[
            dat.array_labels.index(column)
        ]
        detector["description"] = dat.attrs["detector"][DETECTOR_KEYS[column]]

    outfile = filename.parent / (filename.stem + "_new.xdi")
    # write_ascii always prints the name of the file that it writes.
    with contextlib.redirect_stdout(io.StringIO()):
        write_ascii(
            outfile,
            dat.energy,
            dat.norm,
            *(getattr(dat, column) for column in detectors.values()),
            header=header,
            label="".join(f"{name:<17}" for name in ["energy", "norm", *detectors]),
        )

    print(f"Wrote group {entry_name} in file {Path(nxroot.file.filename).name}")


def create_nxclass(root, name, nx_class, **attrs):
    """Create NeXus class instance with attributes."""
    child = root.create_group(name)
    child.attrs["NX_class"] = nx_class
    for name, value in attrs.items():
        child.attrs[name] = value
    return child


def main(output_filename):
    with h5py.File(output_filename, "w") as nxroot:
        sample = {"i0": "I0", "itrans": "It", "iref": "Ir"}
        # The Fe foil is the reference sample: It is the beam on the foil.
        foil = {"i0": "It", "itrans": "Ir"}
        xdi2nexus(THIS_DIRECTORY / "Fe-K-IronFoil.xdi", nxroot, foil)
        xdi2nexus(THIS_DIRECTORY / "Fe-Hematite.xdi", nxroot, sample)
        xdi2nexus(THIS_DIRECTORY / "Fe-Wustite.xdi", nxroot, sample)


if __name__ == "__main__":
    main(THIS_DIRECTORY / f"{THIS_DIRECTORY.name}.nxs")
