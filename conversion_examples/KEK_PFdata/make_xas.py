import json
from pathlib import Path

import h5py
import numpy
from larch.xafs import pre_edge
from larch.io import read_ascii, write_ascii
from larch.utils import gformat

THIS_DIRECTORY = Path(__file__).parent

PLANCK_HC = 12398.419843320027
DEG2RAD = 0.017453292519943295


def kekpf2nexus(filename, nxroot, entry_name="entry", metadata=None):

    dat = read_ascii(filename, labels="angle_drive, angle_read, time, i0, ifluor")

    meta = {}
    if metadata is not None:
        for kf, vf in metadata.items():
            if kf not in meta:
                meta[kf.lower()] = {}
            for k, v in vf.items():
                meta[kf.lower()][k.lower()] = v

    monod = meta["monochromator"]["d_spacing"]

    dat.energy = PLANCK_HC / (2 * monod * numpy.sin(DEG2RAD * (dat.data[0, :])))
    dat.mu = dat.ifluor / dat.i0

    pre_edge(dat, pre1=-150, pre2=-50, norm1=150, norm2=750)
    pre_offset = dat.pre_edge_details.pre_offset
    pre_slope = dat.pre_edge_details.pre_slope
    nvict = dat.pre_edge_details.nvict

    coldata = []
    coldata.append(dat.energy)
    coldata.append(dat.norm * 1.0)
    coldata.append(dat.ifluor * 1.0)
    coldata.append(dat.i0 * 1.0)

    array_labels = ["energy", "intensity", "ifluor", "i0"]
    ndat, npts = dat.data.shape
    for i in range(ndat):
        label = dat.array_labels[i].lower()
        if label not in array_labels:
            array_labels.append(label)
            coldata.append(dat.data[i, :])

    root = create_nxclass(nxroot, entry_name, "NXentry", default="plot")
    nxroot.attrs["default"] = entry_name
    root["definition"] = "NXxas"

    root["mode"] = "fluorescence"

    root["energy"] = dat.energy
    root["energy"].attrs["units"] = "eV"
    root["intensity"] = dat.norm

    element = create_nxclass(root, "element", "NXelement")
    element["symbol"] = meta["element"]["symbol"]

    edge = create_nxclass(root, "edge", "NXedge")
    edge["name"] = meta["element"]["edge"]

    plot = create_nxclass(root, "plot", "NXdata", signal="intensity", axes="energy")
    plot["energy"] = h5py.SoftLink(root["energy"].name)
    plot["intensity"] = h5py.SoftLink(root["intensity"].name)
    plot["energy"].attrs["units"] = "eV"
    plot["energy"].attrs["long_name"] = "Energy (eV)"
    plot["intensity"].attrs["long_name"] = "Normalized mu(E)"

    names = {}

    # sample
    sample = create_nxclass(root, "sample", "NXsample")
    for aname, value in meta["sample"].items():
        sample[aname] = value
        if aname.lower() == "name":
            names["sample"] = value

    sample["prep"] = "unknown sample"

    # process
    kwargs = []
    for k, v in dat.callargs.pre_edge.items():
        if v is not None:
            kwargs.append(f"{k}={v}")

    kwargs = ", ".join(kwargs)

    preline = f"pre_edge = {gformat(pre_offset, 12)} + {gformat(pre_slope, 12)}*energy"
    if nvict != 0:
        preline = f"({preline})*energy(-{dat.nvict})"

    proc = [
        "processing done with xraylarch version 0.9.80",
        f"larch.xafs.pre_edge(data, {kwargs})",
        "energy = col1    # column 1: energy (eV)",
        "ifluor = col3    # column 3: fluorescence intensity",
        "i0     = col4    # column 4: incident beam intensity",
        "mu  = iflour/i0  ",
        f"edge_step = {gformat(dat.edge_step, 12)}",
        preline,
        "intensity = norm = (mu - pre_edge) /edge_step",
    ]

    notes = "\n".join(proc)

    header = ["XDI/1.1", "Column.1: energy eV", "Column.2: norm"]
    collabel = ["energy          ", "norm            "]
    for i, label in enumerate(array_labels[2:]):
        header.append(f"Column.{i+3}: {label}")
        collabel.append(label + " " * (1 + max(1, 15 - len(label))))

    collabel = " ".join(collabel)

    end_header = []
    target = header
    for j in dat.header[4:]:
        if j.startswith("#"):
            j = j[1:].strip()
        if "---" in j:
            break
        if "///" in j:
            target = end_header
        if j.startswith("Mono."):
            j = j.replace("Mono.", "Monochromator.")
        if "Monochromator.dspa" in j:
            j = j.replace("dspacing", "d_spacing")

        if not j.startswith("Column."):
            target.append(j)

    header.append("Process.program: xraylarch")
    header.append("Process.version: 0.9.80")
    header.append(f"Process.command: pre_edge(data, {kwargs})")
    for i, p in enumerate(proc[2:]):
        header.append(f"Process.step{i+1:d}: {p}")
    for j in end_header:
        if j.startswith("#"):
            j = j[1:].strip()
        header.append(j)

    process = create_nxclass(root, "process", "NXprocess")
    process.attrs["NX_class"] = "NXprocess"
    process["program"] = "xraylarch"
    process["version"] = "0.9.80"
    nts = create_nxclass(process, "notes", "NXnote")
    nts["data"] = notes
    nts["type"] = "text/plain"

    # rawdata
    root["rawdata"] = numpy.array(coldata).T
    root["rawdata"].attrs["array_labels"] = json.dumps(array_labels)

    root["reference"] = "None"

    # scan
    scan = create_nxclass(root, "scan", "NXparameters")
    scan["headers"] = json.dumps(meta)
    scan["data_collector"] = "KEK PF BL9A"
    scan["filename"] = filename.name

    if "scan" in meta:
        for key, val in meta["scan"].items():
            scan[key] = val
        if getattr(dat, "comments", None) is not None:
            scan["comments"] = dat.comments

    inst = create_nxclass(root, "instrument", "NXinstrument")

    source = create_nxclass(inst, "source", "NXsource")
    source["type"] = "Synchrotron X-ray Source"
    source["probe"] = "x-ray"

    if "facility" in meta:
        for aname, value in meta["facility"].items():
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

    if "beamline" in meta:
        bl = create_nxclass(inst, "beamline", "NXparameters")
        for aname, value in meta["beamline"].items():
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
    mono_meta = meta.get("monochromator", meta.get("mono", {}))
    d_spacing = mono_meta.get("d_spacing", 3.13551)
    mono_name = mono_meta.get("name", "Si 111")

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
    crystal["d_spacing"] = d_spacing

    i0 = create_nxclass(inst, "i0", "NXdetector")
    i0["data"] = dat.i0
    i0["description"] = "Ion Chamber"

    ifluor = create_nxclass(inst, "ifluor", "NXdetector")
    ifluor["data"] = dat.ifluor
    ifluor["description"] = "Ion Chamber"

    outfile = filename.parent / (filename.stem + "_new" + filename.suffix)

    write_ascii(outfile, *coldata, header=header, label=collabel)

    print(f"done. Wrote group {entry_name} in file {outfile}")


def create_nxclass(root, name, nx_class, **attrs):
    """Create NeXus class instance with attributes."""
    child = root.create_group(name)
    child.attrs["NX_class"] = nx_class
    for name, value in attrs.items():
        child.attrs[name] = value
    return child


def main(output_filename):
    with h5py.File(output_filename, "w") as nxroot:

        metadata = {
            "sample": {"name": "fe010"},
            "element": {"symbol": "Fe", "edge": "K"},
            "monochromator": {"crystal": "Si 111", "d_spacing": 3.1551},
            "facility": {"name": "Photon Factory", "beamline": "BL9A"},
            "detector": {"i0": "20 cm, He", "ifluor": "Vortex ME-4"},
        }

        kekpf2nexus(
            THIS_DIRECTORY / "PF9A_2022.dat",
            nxroot,
            entry_name="fe010",
            metadata=metadata,
        )


if __name__ == "__main__":
    main(THIS_DIRECTORY / ".." / ".." / "nxxas_examples" / f"{THIS_DIRECTORY.name}.h5")
