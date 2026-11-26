"""Convert the SLS Debye transmission scan S04301 to NXxas_trans."""

import datetime
from inspect import getsource
from pathlib import Path
from zoneinfo import ZoneInfo

import h5py
import numpy

THIS_DIRECTORY = Path(__file__).parent

NIDAQ = "entry/collection/devices/nidaq"
METADATA = "entry/collection/metadata"
# Channels of the DAQ, from the nidaq_smpl_abs_* and nidaq_ref_abs_* settings:
# the sample absorbance is ln(AI0/AI2) and the reference absorbance is ln(AI2/AI4).
DETECTORS = {
    "i0": ("nidaq_ai0_mean", "ic0"),
    "itrans": ("nidaq_ai2_mean", "ic1"),
    "iref": ("nidaq_ai4_mean", "ic2"),
}
RAW_FIELDS = [
    "nidaq_energy",
    "nidaq_enc",
    "nidaq_rle",
    "nidaq_xas_timestamp",
    "nidaq_ai0_mean",
    "nidaq_ai0_std_dev",
    "nidaq_ai2_mean",
    "nidaq_ai2_std_dev",
    "nidaq_ai4_mean",
    "nidaq_ai4_std_dev",
    "nidaq_smpl_abs",
    "nidaq_ref_abs",
]


def write_field(group, name, value, units=None):
    """Create a dataset and optionally attach a units attribute."""
    dataset = group.create_dataset(name, data=value)
    if units is not None:
        dataset.attrs["units"] = units
    return dataset


def create_nx_group(parent, name, nx_class):
    """Create a group with an NX_class attribute."""
    group = parent.create_group(name, track_order=True)
    group.attrs["NX_class"] = nx_class
    return group


def read_string(group, name):
    return group[name][()].decode()


def energy_grid(energies):
    """Return the sorted measured energies and a function to align a channel."""
    valid = energies != 0  # The DAQ pads each sweep with zero energy.
    sweeps, _ = numpy.nonzero(valid)
    grid, bins = numpy.unique(energies[valid], return_inverse=True)
    shape = (energies.shape[0], grid.size)
    if numpy.unique(sweeps * grid.size + bins).size != bins.size:
        raise ValueError("A sweep contains multiple measurements at the same energy.")

    def on_grid(values):
        result = numpy.full(shape, numpy.nan, dtype=values.dtype)
        result[sweeps, bins] = values[valid]
        return result

    return grid, on_grid


def debye2nexus(nxroot_in, nxroot_out, entry_name):
    nidaq = nxroot_in[NIDAQ]
    metadata = nxroot_in[METADATA]
    energies = nidaq["nidaq_energy/value"][()]
    grid, on_grid = energy_grid(energies)

    sample_name = read_string(metadata, "sample_name")
    element = read_string(metadata, "Element")
    edge = read_string(metadata, "Edge")
    scan_number = metadata["bec/scan_number"][()]

    entry = create_nx_group(nxroot_out, entry_name, "NXentry")
    entry.attrs["default"] = "data"
    nxroot_out.attrs["default"] = entry_name

    write_field(entry, "definition", "NXxas_trans")
    write_field(
        entry, "title", f"{sample_name}, {element} {edge} edge, scan {scan_number}"
    )
    write_field(entry, "entry_identifier_uuid", read_string(metadata, "bec/scan_id"))
    zone = ZoneInfo("Europe/Zurich")
    start = datetime.datetime.fromisoformat(
        read_string(metadata, "start_time")
    ).replace(tzinfo=zone)
    end = datetime.datetime.fromisoformat(read_string(metadata, "end_time")).replace(
        tzinfo=zone
    )
    write_field(entry, "start_time", start.isoformat())
    write_field(entry, "end_time", end.isoformat())

    energy_field = write_field(entry, "energy", grid, units="eV")
    energy_field.attrs["long_name"] = "Energy (eV)"
    intensity_field = write_field(
        entry,
        "intensity",
        on_grid(nidaq["nidaq_smpl_abs/value"][()]),
        units="",
    )
    intensity_field.attrs["type"] = "absorbance"
    intensity_field.attrs["provenance"] = "measured"
    intensity_field.attrs["long_name"] = "ln(I0/I)"

    element_group = create_nx_group(entry, "element", "NXelement")
    write_field(element_group, "symbol", element)

    edge_group = create_nx_group(entry, "edge", "NXabsorption_edge")
    write_field(edge_group, "name", edge)

    sample = create_nx_group(entry, "sample", "NXsample")
    write_field(sample, "name", sample_name)

    instrument_in = nxroot_in["entry/instrument"]
    instrument = create_nx_group(entry, "instrument", "NXinstrument")
    write_field(instrument, "name", read_string(instrument_in, "source/beamline_name"))

    source = create_nx_group(instrument, "source", "NXsource")
    write_field(source, "type", "Synchrotron X-ray Source")
    write_field(source, "name", read_string(instrument_in, "source/facility_name"))
    write_field(source, "probe", "x-ray")

    monochromator = create_nx_group(instrument, "monochromator", "NXmonochromator")
    crystal = create_nx_group(monochromator, "crystal", "NXcrystal")
    bragg = nxroot_in["entry/collection/devices/mo1_bragg"]
    write_field(
        crystal,
        "d_spacing",
        bragg["mo1_bragg_crystal_current_d_spacing/value"][()],
        units="angstrom",
    )
    xtal = read_string(bragg, "mo1_bragg_crystal_current_xtal_string/value")
    material, reflection = xtal[:2], xtal[2:]
    write_field(crystal, "type", material)
    write_field(crystal, "reflection", [int(index) for index in reflection], units="")

    description = read_string(nxroot_in["entry/mode/Sample_Transmission"], "Detector")
    config = nxroot_in["entry/collection/configuration"]
    for name, (channel, chamber) in DETECTORS.items():
        detector = create_nx_group(instrument, name, "NXdetector")
        write_field(detector, "description", description)
        # The DAQ reads the amplifier outputs as voltages (nidaq_readout_range).
        write_field(detector, "data", on_grid(nidaq[f"{channel}/value"][()]), units="V")
        write_field(detector, "local_name", chamber)
        write_field(detector, "type", "ion chamber")
        write_field(
            detector,
            "gain_setting",
            read_string(config[chamber], f"{chamber}_amp_cGain_ENUM_string/value"),
        )

    data = create_nx_group(entry, "data", "NXdata")
    data.attrs["signal"] = "intensity"
    data.attrs["axes"] = ["time", "energy"]
    data.attrs["time_indices"] = 0
    times = nidaq["nidaq_xas_timestamp/value"][()]
    if times.shape != (energies.shape[0],):
        raise ValueError("Expected one timestamp per energy sweep.")
    time = write_field(data, "time", times - start.timestamp(), units="s")
    time.attrs["long_name"] = "Sweep time since entry start (s)"
    data.attrs["energy_indices"] = 1
    for name in ("energy", "intensity"):
        # NeXus identifies a hard link by the target attribute.
        entry[name].attrs["target"] = entry[name].name
        data[name] = entry[name]

    raw_data = create_nx_group(entry, "raw_data", "NXcollection")
    for name in RAW_FIELDS:
        write_field(raw_data, name, nidaq[f"{name}/value"][()])

    process = create_nx_group(entry, "processing", "NXprocess")
    write_field(
        process, "date", datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    note = create_nx_group(process, "note", "NXnote")
    write_field(note, "type", "text/plain")
    filename = Path(nxroot_out.filename).name
    script = f"""# Run with Python in the directory containing {filename}.
# Reproduce the energy axis and sample absorbance from the stored DAQ arrays.
import h5py
import numpy

{getsource(energy_grid)}
with h5py.File({filename!r}, "r") as nxfile:
    raw = nxfile[{raw_data.name!r}]
    energy, on_grid = energy_grid(raw["nidaq_energy"][()])
    # The DAQ recorded the sample absorbance as ln(AI0/AI2) from mean amplifier voltages.
    # Align the recorded values without applying a gain correction.
    intensity = on_grid(raw["nidaq_smpl_abs"][()])
"""
    write_field(note, "data", script)


def main(output_filename):
    input_filename = THIS_DIRECTORY / "S04301_master.h5"
    with (
        h5py.File(input_filename, "r") as nxroot_in,
        h5py.File(output_filename, "w", track_order=True) as nxroot_out,
    ):
        debye2nexus(nxroot_in, nxroot_out, "S04301")


if __name__ == "__main__":
    main(THIS_DIRECTORY / f"{THIS_DIRECTORY.name}.nxs")
