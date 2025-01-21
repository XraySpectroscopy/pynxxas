import json
from pathlib import Path

import h5py
import numpy
from larch.xafs import pre_edge
from larch.io import read_xdi, read_ascii, write_ascii
from larch.utils import gformat

THIS_DIRECTORY = Path(__file__).parent


def xdi2nexus(filename, nxroot, entry_name="entry", data_mode="transmission"):
    asc = read_ascii(filename)
    dat = read_xdi(str(filename))

    dat.energy
    dat.mu = dat.mutrans * 1.0
    dat.itrans = (dat.itrans * 100.0).astype("int32") / 100.0  # round
    dat.array_labels[dat.array_labels.index("mutrans")] = "mu"

    pre_edge(dat, pre1=-150, pre2=-50, norm1=150, norm2=750)
    pre_offset = dat.pre_edge_details.pre_offset
    pre_slope = dat.pre_edge_details.pre_slope
    nvict = dat.pre_edge_details.nvict

    rawdata = numpy.zeros((len(dat.energy), 4), dtype="float64")
    rawdata[:, 0] = dat.energy
    rawdata[:, 1] = dat.norm
    rawdata[:, 2] = (dat.itrans * 10.0).astype("int32") / 10.0
    rawdata[:, 3] = dat.i0 * 1.0

    root = create_nxclass(nxroot, entry_name, "NXentry", default="plot")
    nxroot.attrs["default"] = entry_name
    root["definition"] = "NXxas"

    root["mode"] = "transmission"

    root["energy"] = dat.energy
    root["energy"].attrs["units"] = "eV"
    root["intensity"] = dat.norm

    element = create_nxclass(root, "element", "NXelement")
    element["symbol"] = dat.attrs["element"]["symbol"]

    edge = create_nxclass(root, "edge", "NXedge")
    edge["name"] = dat.attrs["element"]["edge"]

    plot = create_nxclass(root, "plot", "NXdata", signal="intensity", axes="energy")
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
        "using 'data' from arrays in rawdata",
        "energy = data[:,0]      # column 1: energy (eV)",
        "itrans = data[:, 2]     # column 3: transmitted beam intensity",
        "i0 = data[:, 3]         # column 4: incident beam intensity",
        "mu = -log(itrans/i0)    # absorbance",
        f"edge_step = {gformat(dat.edge_step, 12)}",
        preline,
        "intensity = norm = (mu - pre_edge) /edge_step",
    ]

    notes = "\n".join(proc)

    header = [
        "XDI/1.1",
        "Column.1: energy eV",
        "Column.2: norm",
        "Column.3: itrans",
        "Column.4: i0",
    ]
    end_header = []
    target = header
    for j in asc.header[4:]:
        if j.startswith("#"):
            j = j[1:].strip()
        if "---" in j:
            break
        if "///" in j:
            target = end_header
        target.append(j)

    header.append("Process.program: xraylarch")
    header.append("Process.version: 0.9.80")
    header.append(f"Process.command: pre_edge(data, {kwargs})")
    for i, p in enumerate(proc[3:]):
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
    array_labels = json.dumps(["energy", "intensity", "itrans", "i0"])
    root["rawdata"] = rawdata.T
    root["rawdata"].attrs["array_labels"] = array_labels

    root["reference"] = "None"

    # scan
    scan = create_nxclass(root, "scan", "NXparameters")
    scan["headers"] = json.dumps(dat.attrs)
    scan["data_collector"] = "Matthew Newville"
    scan["filename"] = filename.name

    for key, val in dat.attrs["scan"].items():
        scan[key] = val
    if getattr(dat, "comments", None) is not None:
        scan["comments"] = dat.comments

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
    crystal["d_spacing"] = d_spacing

    i0 = create_nxclass(inst, "i0", "NXdetector")
    i0["data"] = dat.i0
    i0["description"] = dat.attrs["detector"]["i0"]

    itrans = create_nxclass(inst, "itrans", "NXdetector")
    itrans["data"] = dat.itrans
    itrans["description"] = dat.attrs["detector"]["i1"]

    outfile = filename.parent / (filename.stem + "_new.xdi")
    write_ascii(
        outfile,
        dat.energy,
        dat.norm,
        dat.itrans,
        dat.i0,
        header=header,
        label="energy           norm             itrans           i0",
    )

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
        xdi2nexus(THIS_DIRECTORY / "fe_metal_rt.xdi", nxroot, entry_name="fe_metal")
        xdi2nexus(THIS_DIRECTORY / "fe2o3_rt.xdi", nxroot, entry_name="fe2o3")
        xdi2nexus(THIS_DIRECTORY / "feo_rt1.xdi", nxroot, entry_name="feo")


if __name__ == "__main__":
    main(THIS_DIRECTORY / ".." / ".." / "converted" / "fe_xas_nexus.h5")
