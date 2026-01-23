from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="openagentic-sdk")
    parser.add_argument("--version", action="store_true", help="print version and exit")
    args = parser.parse_args(argv)
    if args.version:
        from ._version import __version__

        print(__version__)
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
