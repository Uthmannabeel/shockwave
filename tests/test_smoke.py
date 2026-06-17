"""Smoke tests for the scaffold. Real algorithm tests land with the engine."""

import shockwave
from shockwave import schema
from shockwave.cli import build_parser


def test_version():
    assert shockwave.__version__


def test_parser_analyze():
    args = build_parser().parse_args(["analyze", "process_payment", "--max-hops", "3"])
    assert args.command == "analyze"
    assert args.seed == "process_payment"
    assert args.max_hops == 3


def test_blast_edge_kinds():
    assert schema.CALLS in schema.BLAST_EDGE_KINDS
