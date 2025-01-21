from pathlib import Path

import h5py
import numpy

THIS_DIRECTORY = Path(__file__).parent


def bliss2nexus(nxentry_in, expressions, metadata, nxroot_out, entry_name):
    root = create_nxclass(nxroot_out, entry_name, "NXentry")
    nxroot_out.attrs["default"] = entry_name

    inst = create_nxclass(root, "instrument", "NXinstrument")

    source = create_nxclass(inst, "source", "NXsource")
    source["type"] = "Synchrotron X-ray Source"
    source["probe"] = "x-ray"

    monochromator = create_nxclass(inst, "monochromator", "NXmonochromator")
    nxinstrument_input = nxentry_in["instrument"]
    dset = nxinstrument_input[metadata["energy"]]["data"]
    monochromator["energy"] = dset[()]
    energy_units = dset.attrs.get("units", "keV")
    monochromator.attrs["units"] = energy_units

    for name, expression in expressions.items():
        subroot = create_nxclass(root, name, "NXsubentry", default="plot")
        root.attrs["default"] = name
        subroot["definition"] = "NXxas"

        mode = expression["mode"]
        subroot["mode"] = mode

        subroot["energy"] = h5py.SoftLink(monochromator["energy"].name)

        if mode == "transmission":
            I0 = nxinstrument_input[expression["I0"]]["data"][()]
            It = nxinstrument_input[expression["It"]]["data"][()]
            subroot["intensity"] = numpy.log(I0 / It)
        elif mode == "fluorescence":
            I0 = nxinstrument_input[expression["I0"]]["data"][()]
            mca = nxinstrument_input[expression["mca"]]
            Ifluo = mca[expression["Ifluo"]][()]
            Lt = mca[expression["Lt"]][()]
            subroot["intensity"] = numpy.log(Ifluo / (I0 * Lt))
        else:
            raise NotImplementedError(mode)

        element = create_nxclass(subroot, "element", "NXelement")
        element["symbol"] = metadata["element"]

        edge = create_nxclass(subroot, "edge", "NXedge")
        edge["name"] = metadata["edge"]

        plot = create_nxclass(
            subroot, "plot", "NXdata", signal="intensity", axes="energy"
        )
        plot["title"] = expression.get("title", name)
        plot["energy"] = h5py.SoftLink(subroot["energy"].name)
        plot["intensity"] = h5py.SoftLink(subroot["intensity"].name)
        plot["energy"].attrs["long_name"] = f"Energy ({energy_units})"
        plot["intensity"].attrs["long_name"] = "Normalized mu(E)"


def create_nxclass(root, name, nx_class, **attrs):
    """Create NeXus class instance with attributes."""
    child = root.create_group(name, track_order=True)
    child.attrs["NX_class"] = nx_class
    for name, value in attrs.items():
        child.attrs[name] = value
    return child


def main(output_filename):
    with h5py.File(output_filename, "w", track_order=True) as nxroot_out:

        input_filename = THIS_DIRECTORY / "test_Assolution_Mauro_0001.h5"

        expressions = {
            "itrans": {
                "mode": "transmission",
                "I0": "p201_1_bkg_sub",
                "It": "p201_3_bkg_sub",
                "title": "Transmission",
            },
            "iref": {
                "mode": "transmission",
                "I0": "p201_3_bkg_sub",
                "It": "p201_5_bkg_sub",
                "title": "Standard",
            },
        }
        for mca_nr in range(16):
            expressions[f"fluo{mca_nr}"] = {
                "mode": "fluorescence",
                "I0": "p201_1_bkg_sub",
                "mca": f"xmapd16_det{mca_nr}",
                "Ifluo": "roi1",
                "Lt": "live_time",  # effective measurement time
                "title": f"Fluorescence #{mca_nr}",
            }
        metadata = {"element": "As", "edge": "K", "energy": "energy_enc"}

        with h5py.File(input_filename, "r") as nxroot_in:
            for entry_name in nxroot_in:
                if entry_name.endswith(".1"):
                    nxentry_in = nxroot_in[entry_name]
                    bliss2nexus(
                        nxentry_in, expressions, metadata, nxroot_out, entry_name
                    )


if __name__ == "__main__":
    main(THIS_DIRECTORY / ".." / ".." / "nxxas_examples" / f"{THIS_DIRECTORY.name}.h5")
