import sys
import logging
import argparse

from .. import nxdl


def main(argv=None):
    if argv is None:
        argv = sys.argv

    parser = argparse.ArgumentParser(
        prog="nxdl-validate", description="Validate NXDL definitions"
    )

    parser.add_argument("--url", type=str, default=None, help="NXDL repository URL")
    parser.add_argument(
        "--dir", type=str, default=None, help="Local directory of the NXDL repository"
    )
    parser.add_argument(
        "definitions", type=str, nargs="*", help="NXDL definitions to validate"
    )

    args = parser.parse_args(argv[1:])
    logging.basicConfig()

    definitions = args.definitions
    repo_options = {"localdir": args.dir, "url": args.url, "reset": not args.dir}

    if not definitions:
        definitions = nxdl.get_nxdl_definition_names(**repo_options)

    for name in definitions:
        _ = nxdl.load_definition(name, **repo_options)


if __name__ == "__main__":
    sys.exit(main())
