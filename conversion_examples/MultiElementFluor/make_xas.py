import json
from pathlib import Path

import numpy
from nexusformat import nexus
from larch.xafs import pre_edge
from larch.io import read_xdi, read_ascii, write_ascii
from larch.utils import gformat


THIS_DIRECTORY = Path(__file__).parent


def xdi2nexus(
    filename,
    nxroot,
    entry_name="entry",
    nchans=4,
    chan1=14,
    icr1=None,
    ocr1=None,
    data_mode="fluorescence",
    metadata=None,
):

    asc = read_ascii(filename)
    dat = read_xdi(str(filename))

    meta = {}
    for kf, vf in dat.attrs.items():
        meta[kf.lower()] = {}
        for k, v in vf.items():
            meta[kf.lower()][k.lower()] = v

    if metadata is not None:
        for kf, vf in metadata.items():
            if kf not in meta:
                meta[kf.lower()] = {}
            for k, v in vf.items():
                meta[kf.lower()][k.lower()] = v

    dat.energy = dat.Energy * 1.0
    dat.i0 = dat.I0 * 1.0

    dat.ifluor = dat.i0 * 0.0
    fluor_str = []

    for ichan in range(nchans):
        c = 1.0 * dat.data[ichan + chan1 - 1, :]
        s = f"col{ichan+chan1+2}"
        if icr1 is not None:
            c *= dat.data[ichan + icr1 - 1, :]
            s = f"{s}*col{ichan+icr1+2}"
        if ocr1 is not None:
            c /= dat.data[ichan + ocr1 - 1, :]
            s = f"{s}/col{ichan+ocr1+2}"
        dat.ifluor += c
        fluor_str.append(s)
    fluor_str = "+".join(fluor_str)

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

    root = nxroot[entry_name] = nexus.NXentry()

    root["definition"] = "NXxas"
    root["mode"] = "fluorescence"
    root["element"] = meta["element"]["symbol"]
    root["absorption_edge"] = meta["element"]["edge"]
    root["energy"] = dat.energy
    root["energy"].attrs["units"] = "eV"
    root["intensity"] = dat.norm
    root.attrs["default"] = "plot"

    plot = root["plot"] = nexus.NXdata()
    plot["energy"] = root["energy"]
    plot["intensity"] = root["intensity"]
    plot.attrs["signal"] = "intensity"
    plot.attrs["axes"] = "energy"
    plot["energy"].attrs["units"] = "eV"
    plot["energy"].attrs["long_name"] = "Energy (eV)"
    plot["intensity"].attrs["long_name"] = "Normalized mu(E)"

    names = {}
    #  sample
    sample = root["sample"] = nexus.NXsample()
    for aname, value in meta["sample"].items():
        setattr(sample, aname, value)
        if aname.lower() == "name":
            names["sample"] = value
    sample["prep"] = "unknown sample"

    #  process
    kwargs = []
    for k, v in dat.callargs.pre_edge.items():
        if v is not None:
            kwargs.append(f"{k}={v}")

    kwargs = ", ".join(kwargs)

    preline = f"pre_edge = {gformat(pre_offset, 12)} + {gformat(pre_slope, 12)}*energy"
    if nvict != 0:
        preline = f"({preline})*energy(-{dat.nvict})"

    dtc = "no deadtime correction with file"
    if icr1 is not None or ocr1 is not None:
        dtc = "with deadtime corection from columns in the data"
    nd = len(coldata)
    proc = [
        "processing done with xraylarch version 0.9.80",
        f"larch.xafs.pre_edge(data, {kwargs})",
        f"using col1..col{nd} for {nd} from arrays in rawdata",
        "energy = col1    # column 1: energy (eV)",
        "i0     = col4    # column 4: incident beam intensity",
        f"# fluorescence: sum {nchans} channels, {dtc}",
        f"ifluor = {fluor_str}",
        "mu  = iflour/i0  ",
        f"edge_step = {gformat(dat.edge_step, 12)}",
        preline,
        "intensity = norm = (mu - pre_edge) /edge_step",
    ]

    notes = "\n".join(proc)

    header = ["XDI/1.1", "Column.1: energy eV", "Column.2: norm"]
    collabel = ["energy", "norm"]
    for i, label in enumerate(array_labels[2:]):
        header.append(f"Column.{i+3}: {label}")
        collabel.append(label)
    collabel = " ".join(collabel)

    end_header = []
    target = header
    for j in asc.header[4:]:
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

    root["process"] = nexus.NXprocess(
        program="xraylarch", version="0.9.80", notes=notes
    )

    # rawdata
    root["rawdata"] = numpy.array(coldata).T
    root["rawdata"].attrs["array_labels"] = json.dumps(array_labels)

    root["reference"] = "None"

    # scan
    scan = root["scan"] = nexus.NXcollection()
    scan.headers = json.dumps(meta)
    scan.data_collector = "Tony Lanzirotti"
    scan.filename = filename.name

    for key, val in meta["scan"].items():
        setattr(scan, key, val)
    if getattr(dat, "comments", None) is not None:
        scan.comments = dat.comments

    inst = root["instrument"] = nexus.NXinstrument()

    source = inst["source"] = nexus.NXsource(
        type="Synchrotron X-ray Source", probe="x-ray"
    )

    if "facility" in meta:
        for aname, value in meta["facility"].items():
            if aname.lower() == "energy":
                words = value.split(maxsplit=1)
                en_value = float(words[0])
                source.energy = en_value
                if len(words) > 1:
                    source.energy.attrs["units"] = words[1]
            else:
                setattr(source, aname, value)
                if aname.lower() == "name":
                    names["facility"] = value

    bl = inst["beamline"] = nexus.NXcollection()
    for aname, value in meta["beamline"].items():
        setattr(bl, aname, value)
        if aname.lower() == "name":
            names["beamline"] = value

    title_words = [
        names.get("sample", filename.name),
        names.get("facility", ""),
        names.get("beamline", ""),
    ]
    root["title"] = (" ".join(title_words)).strip()

    mono_meta = meta.get("monochromator", meta.get("mono", {}))
    d_spacing = mono_meta.get("d_spacing", 3.14770)
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

    mono_type, refl = parse_mono_string(mono_name)
    mono_crystal = nexus.NXcrystal(
        type=mono_type, reflection=numpy.array(refl), d_spacing=d_spacing
    )

    inst["monochromator"] = nexus.NXmonochromator(
        energy=root["energy"], crystal=mono_crystal
    )

    inst["i0"] = nexus.NXdetector(data=dat.i0, description="Ion Chamber")
    inst["ifluor"] = nexus.NXdetector(
        data=dat.ifluor, description="ME-4 Fluorescence Detector"
    )

    outfile = filename.parent / (filename.stem + "_new" + filename.suffix)

    write_ascii(outfile, *coldata, header=header, label=collabel)

    print(f"done. Wrote group {entry_name} and file {outfile}")


def main(output_filename):
    nxroot = nexus.nxopen(output_filename, "w")

    metadata = {
        "sample": {"name": "apophyllite"},
        "element": {"symbol": "V", "edge": "K"},
        "mono": {"crystal": "Si 111", "d_spacing": 3.13477},
        "facility": {"name": "APS", "beamline": "13-ID-E"},
        "detector": {"i0": "20 cm, He", "ifluor": "Vortex ME-4"},
    }

    call_kws = dict(nchans=4, chan1=14, icr1=22, ocr1=None, metadata=metadata)

    for fname in (
        "V_XANES_ap1.001",
        "V_XANES_ap2.001",
        "V_XANES_ap3.001",
        "V_XANES_ap4.001",
        "V_XANES_ap5.001",
        "V_XANES_ap6.001",
        "V_XANES_ap7.001",
        "V_XANES_ap8.001",
        "V_XANES_ap9.001",
        "V_XANES_ap10.001",
        "V_XANES_ap11.001",
        "V_XANES_ap12.001",
    ):
        entry_name = fname.replace(".001", "")

        xdi2nexus(
            THIS_DIRECTORY / fname,
            nxroot,
            entry_name=entry_name,
            **call_kws,
        )


if __name__ == "__main__":
    main(THIS_DIRECTORY / ".." / ".." / "converted" / "V_XANES_nexus.h5")
