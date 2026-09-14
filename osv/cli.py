"""Command line interface for OpenSurgicalVision."""

import argparse
import sys
from osv import __version__


def main() -> int:
    parser = argparse.ArgumentParser(
        description="OpenSurgicalVision CLI — Benchmark, datasets & models for surgical AI"
    )
    parser.add_argument("--version", action="version", version=f"osv {__version__}")
    parser.add_argument("--info", action="store_true", help="Print project status and disclaimer")

    args = parser.parse_args()

    if args.info or len(sys.argv) == 1:
        print(f"OpenSurgicalVision (OSV) v{__version__}")
        print("=" * 60)
        print("DISCLAIMER: RESEARCH USE ONLY — NOT FOR CLINICAL USE")
        print("License: Apache-2.0 (Code), CC BY-NC-SA 4.0 (Annotations)")
        print("Repository: https://github.com/opensurgicalvision/osv")
        print("=" * 60)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
