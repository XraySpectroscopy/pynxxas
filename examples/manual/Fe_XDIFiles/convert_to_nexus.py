import contextlib
import io
import re
from pathlib import Path

import h5py
import larch
import numpy
from larch.io import read_ascii
from larch.io import read_xdi
from larch.io import write_ascii
from larch.xafs import pre_edge

THIS_DIRECTORY = Path(__file__).parent

PRE_EDGE = {"pre1": -150, "pre2": -50, "norm1": 150, "norm2": 750}

# XDI header key of the description of each ion chamber column
DETECTOR_KEYS = {"I0": "i0", "It": "i1", "Ir": "i2"}


def xdi2nexus(filename, nxroot, detectors):
    """Write one XDI file as an NXxas_trans entry.

    ``detectors`` maps each NXdetector name (i0, itrans, iref) to the column of
    the ion chamber in the XDI file. The absorbance is ln(i0/itrans).
    """
    entry_name = filename.stem
    asc = read_ascii(filename)
    dat = read_xdi(str(filename))

    i0, itrans = detectors["i0"], detectors["itrans"]
    dat.mu = numpy.log(getattr(dat, i0) / getattr(dat, itrans))

    pre_edge(dat, **PRE_EDGE)

    root = create_nxclass(nxroot, entry_name, "NXentry", default="plot")
    root["definition"] = "NXxas_trans"
    scan = dat.attrs["scan"]
    for key in ("start_time", "end_time"):
        if key in scan:
            root[key] = scan[key]

    # XDI metadata that the NXentry base class defines
    root["run_cycle"] = dat.attrs["facility"]["cycle"]
    user = create_nxclass(root, "user", "NXuser")
    user["name"] = scan["experimenters"]

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

    sample_name = dat.attrs["sample"]["name"]
    sample = create_nxclass(root, "sample", "NXsample")
    sample["name"] = sample_name
    sample["description"] = dat.attrs["sample"]["prep"]
    x_value, x_units = dat.attrs["sample"]["x"].split()
    sample["x_translation"] = float(x_value)
    sample["x_translation"].attrs["units"] = x_units

    # The note is a script that computes intensity from raw_data. It runs in
    # Python and in larch, so it has no "with" block.
    nxfile = Path(nxroot.file.filename).name
    pre_edge_args = ", ".join(f"{key}={value}" for key, value in PRE_EDGE.items())
    # The processing steps also go into the XDI header, without the read steps.
    steps = [
        "mu = numpy.log(i0 / itrans)",
        "dat = Group(energy=energy, mu=mu)",
        f"pre_edge(dat, {pre_edge_args})",
        "intensity = dat.norm",
    ]
    script = [
        "# Compute intensity from raw_data.",
        f"# Run it with Python or larch in the folder of {nxfile}.",
        "",
        "import h5py",
        "import numpy",
        "from larch import Group",
        "from larch.xafs import pre_edge",
        "",
        f"nxfile = h5py.File('{nxfile}', 'r')",
        f"entry = nxfile['{entry_name}']",
        "energy = entry['raw_data/energy'][()]",
        f"i0 = entry['raw_data/{i0}'][()]",
        f"itrans = entry['raw_data/{itrans}'][()]",
        "nxfile.close()",
        "",
        *steps,
    ]
    notes = "\n".join(script)

    columns = [
        "energy eV",
        "norm",
        *(
            f"{name} {dat.array_units[dat.array_labels.index(column)]}"
            for name, column in detectors.items()
        ),
    ]
    # Keep the application tokens of the original version line.
    applications = asc.header[0].lstrip("#").split()[1:]
    header = [" ".join(["XDI/1.1", *applications])]
    header += [f"Column.{i + 1}: {name}" for i, name in enumerate(columns)]
    header += [
        f"Detector.I{i}: {dat.attrs['detector'][DETECTOR_KEYS[column]]}"
        for i, column in enumerate(detectors.values())
    ]
    end_header = []
    target = header
    # Skip the version line, columns, and detectors of the original file.
    for j in asc.header[1:]:
        if j.startswith("#"):
            j = j[1:].strip()
        if "---" in j:
            break
        if "///" in j:
            target = end_header
        if not j.startswith(("Column.", "Detector.")):
            target.append(j)

    header.append("Process.program: xraylarch")
    header.append(f"Process.version: {larch.__version__}")
    header.append(f"Process.command: pre_edge(dat, {pre_edge_args})")
    for i, p in enumerate(steps):
        header.append(f"Process.step{i + 1:d}: {p}")
    for j in end_header:
        if j.startswith("#"):
            j = j[1:].strip()
        header.append(j)

    process = create_nxclass(root, "processing", "NXprocess")
    process["program"] = "xraylarch"
    process["version"] = larch.__version__
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

    inst = create_nxclass(root, "instrument", "NXinstrument")

    # NXsource requires a name: write it only when the XDI file gives the facility.
    facility = dat.attrs.get("facility", {}).get("name", "")
    if facility:
        source = create_nxclass(inst, "source", "NXsource")
        source["type"] = "Synchrotron X-ray Source"
        source["name"] = facility
        source["probe"] = "x-ray"
        # XDI specification: the facility energy is in GeV and the current in mA.
        source["energy"] = float(dat.attrs["facility"]["energy"])
        source["energy"].attrs["units"] = "GeV"
        source["current"] = float(dat.attrs["facility"]["current"])
        source["current"].attrs["units"] = "mA"
        source["top_up"] = dat.attrs["facility"]["mode"] == "top-off"

    beamline = dat.attrs.get("beamline", {}).get("name", "")
    root["title"] = " ".join([sample_name, facility, beamline]).strip()
    inst["name"] = beamline

    xray_source = dat.attrs["beamline"]["xray_source"]
    if "wiggler" in xray_source:
        wiggler = create_nxclass(inst, "wiggler", "NXinsertion_device")
        wiggler["type"] = "wiggler"
        if "three-pole" in xray_source:
            wiggler["poles"] = 3

    # Mirrors: the XDI text in the description, the pitch as the incident angle
    for name, key in [
        ("collimating_mirror", "collimation"),
        ("harmonic_rejection_mirror", "harmonic_rejection"),
    ]:
        text = dat.attrs["beamline"][key]
        mirror = create_nxclass(inst, name, "NXmirror")
        mirror["description"] = text
        pitch = re.search(r"pitch = ([\d.]+) mrad", text)
        if pitch:
            mirror["incident_angle"] = float(pitch.group(1))
            mirror["incident_angle"].attrs["units"] = "mrad"

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
        detector["type"] = "ion chamber"
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
        nxroot.attrs["default"] = "Fe-K-IronFoil"


if __name__ == "__main__":
    main(THIS_DIRECTORY / f"{THIS_DIRECTORY.name}.nxs")
