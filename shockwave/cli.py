"""Shockwave command-line interface.

    shockwave analyze <symbol|file> [--max-hops N] [--format md|html|json|mermaid]
    shockwave diff <gitref>         [--max-hops N] [--format ...]

``--remote URL --token T`` switches from Orbit Local to Orbit Remote.
"""

from __future__ import annotations

import argparse
import subprocess
import sys

from . import blast_radius, report
from .orbit_client import LocalBackend, OrbitError, RemoteBackend


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="shockwave",
        description="Blast-radius impact analysis on the GitLab Orbit knowledge graph.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--max-hops", type=int, default=5)
    common.add_argument(
        "--format", choices=["md", "html", "json", "mermaid"], default="md"
    )
    common.add_argument("--out", help="write output to a file instead of stdout")
    common.add_argument("--orbit-bin", help="path to the orbit CLI")
    common.add_argument("--db", help="path to the Orbit Local DuckDB graph")
    common.add_argument("--remote", help="Orbit Remote base URL (default: Orbit Local)")
    common.add_argument("--token", help="GitLab access token for --remote")

    p_analyze = sub.add_parser("analyze", parents=[common], help="impact of a symbol/file")
    p_analyze.add_argument("seed", help="symbol name/fqn or file path")

    p_diff = sub.add_parser("diff", parents=[common], help="impact of a git diff")
    p_diff.add_argument("gitref", help="git ref to diff against (e.g. HEAD~1, main)")

    return parser


def _backend(args):
    if args.remote:
        if not args.token:
            raise OrbitError("--remote requires --token")
        return RemoteBackend(args.remote, args.token)
    return LocalBackend(orbit_bin=args.orbit_bin, db=args.db)


def _changed_files(gitref: str) -> list[str]:
    proc = subprocess.run(
        ["git", "diff", "--name-only", gitref],
        capture_output=True, text=True, encoding="utf-8", check=False,
    )
    if proc.returncode != 0:
        raise OrbitError(f"git diff failed:\n{proc.stderr.strip()}")
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _render(radius, fmt: str) -> str:
    return {
        "md": report.to_markdown,
        "html": report.to_html,
        "json": report.to_json,
        "mermaid": report.to_mermaid,
    }[fmt](radius)


def main(argv: list[str] | None = None) -> int:
    # Reports contain Unicode (emoji, ✅). Avoid Windows cp1252 crashes.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):  # pragma: no cover
            pass
    args = build_parser().parse_args(argv)
    try:
        backend = _backend(args)
        if args.command == "analyze":
            if args.remote:
                radius = blast_radius.compute_remote(backend, args.seed, max_hops=args.max_hops)
            else:
                radius = blast_radius.compute(backend, args.seed, max_hops=args.max_hops)
        elif args.command == "diff":
            files = _changed_files(args.gitref)
            if not files:
                print(f"No changed files vs {args.gitref}.", file=sys.stderr)
                return 0
            if args.remote:
                raise OrbitError("`diff --remote` is not supported yet; use `analyze <symbol> --remote`.")
            radius = blast_radius.compute_for_files(backend, files, max_hops=args.max_hops)
        else:  # pragma: no cover - argparse enforces
            raise OrbitError(f"unknown command {args.command}")

        output = _render(radius, args.format)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as fh:
                fh.write(output)
            print(f"Wrote {args.out}", file=sys.stderr)
        else:
            print(output)
        return 0
    except OrbitError as exc:
        print(f"shockwave: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
