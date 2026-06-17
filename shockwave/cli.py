"""Shockwave command-line interface.

    shockwave analyze <symbol|file> [--max-hops N] [--format md|html|json]
    shockwave diff <gitref>         [--max-hops N] [--format md|html|json]

``--remote URL --token T`` switches from Orbit Local to Orbit Remote.

NOTE: skeleton — implemented in the core-engine task.
"""

from __future__ import annotations

import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="shockwave",
        description="Blast-radius impact analysis on the GitLab Orbit knowledge graph.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--max-hops", type=int, default=5)
    common.add_argument("--format", choices=["md", "html", "json"], default="md")
    common.add_argument("--remote", help="Orbit Remote base URL (default: Orbit Local)")
    common.add_argument("--token", help="GitLab access token for --remote")

    p_analyze = sub.add_parser("analyze", parents=[common], help="impact of a symbol/file")
    p_analyze.add_argument("seed", help="symbol name/fqn or file path")

    p_diff = sub.add_parser("diff", parents=[common], help="impact of a git diff")
    p_diff.add_argument("gitref", help="git ref to diff against (e.g. HEAD~1, main)")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    raise SystemExit("shockwave: not yet implemented")  # TODO: core-engine task


if __name__ == "__main__":
    sys.exit(main())
