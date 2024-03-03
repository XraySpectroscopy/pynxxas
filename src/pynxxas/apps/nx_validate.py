import sys
import logging
import argparse

from .. import nexus


def main(argv=None):
    if argv is None:
        argv = sys.argv

    parser = argparse.ArgumentParser(
        prog="nx-validate", description="Validate NeXus instances"
    )

    parser.add_argument("--url", type=str, default=None, help="NXDL repository URL")
    parser.add_argument(
        "--dir", type=str, default=None, help="Local directory of the NXDL repository"
    )
    parser.add_argument(
        "instances",
        type=str,
        nargs="+",
        help="NeXus instances to validate (e.g. HDF5 files)",
    )

    args = parser.parse_args(argv[1:])
    logging.basicConfig()

    instances = args.instances
    repo_options = {"localdir": args.dir, "url": args.url, "reset": not args.dir}

    for instance in instances:
        # TODO: Load instance content and validate with model
        name = instance
        _ = nexus.load_model(name, **repo_options)


if __name__ == "__main__":
    sys.exit(main())
