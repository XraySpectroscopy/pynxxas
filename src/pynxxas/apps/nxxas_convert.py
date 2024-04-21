import sys
import logging
import argparse

from .. import models
from ..io.convert import convert_files

logger = logging.getLogger(__name__)


def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv

    parser = argparse.ArgumentParser(
        prog="nxxas_convert", description="Convert data to NXxas format"
    )

    parser.add_argument(
        "--output-format",
        type=str,
        default="nexus",
        choices=list(models.MODELS),
        help="Output format",
    )

    parser.add_argument(
        "file_patterns",
        type=str,
        nargs="*",
        help="Files to convert",
    )

    parser.add_argument(
        "output_filename", type=str, help="Convert destination filename"
    )

    args = parser.parse_args(argv[1:])
    logging.basicConfig()

    convert_files(
        args.file_patterns, args.output_filename, args.output_format, interactive=True
    )


if __name__ == "__main__":
    sys.exit(main())
