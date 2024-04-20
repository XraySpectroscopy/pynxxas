import sys
import logging
import argparse
from glob import glob

from ..io.xdi import read_xdi


def main(argv=None):
    if argv is None:
        argv = sys.argv

    parser = argparse.ArgumentParser(
        prog="nxxas_convert", description="Convert data to NXxas format"
    )

    parser.add_argument("--output", type=str, default=None, help="Path to HDF5 file")
    parser.add_argument(
        "patterns",
        type=str,
        nargs="+",
        help="Glob file name patterns",
    )

    args = parser.parse_args(argv[1:])
    logging.basicConfig()

    for pattern in args.patterns:
        for filename in glob(pattern):
            read_xdi(filename)


if __name__ == "__main__":
    sys.exit(main())
