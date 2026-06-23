"""Build a static export of the Shockwave site for Vercel (or any static host).

Renders every page to plain HTML and bakes a few real blast-radius analyses so
the Blast Monitor works with zero backend. Run from the repo root with a repo
indexed in Orbit Local (so the baked data is real):

    orbit index /path/to/flask
    python scripts/build_static.py

Output: ./web-static/  (deploy this folder to Vercel).
"""

from __future__ import annotations

import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import shockwave.web as webmod
from shockwave import blast_radius, report
from shockwave.orbit_client import LocalBackend

OUT = "web-static"
# seeds to bake so visitors can click around without a backend
BAKE_SEEDS = ["setupmethod", "route", "dispatch_request"]


def build() -> None:
    here = os.path.dirname(webmod.__file__)
    static_src = os.path.join(here, "web", "static")

    # 1. bake real analyses into static/baked.js (also served by the live app)
    baked = {}
    backend = LocalBackend()
    for seed in BAKE_SEEDS:
        try:
            r = blast_radius.compute(backend, seed, max_hops=4)
            if r.seed_ids:
                baked[seed] = report.to_graph(r)
                print(f"  baked {seed}: {len(r.affected)} affected")
        except Exception as exc:  # pragma: no cover
            print(f"  skip {seed}: {exc}")
    with open(os.path.join(static_src, "baked.js"), "w", encoding="utf-8") as f:
        f.write("window.SHOCKWAVE_BAKED=" + json.dumps(baked, separators=(",", ":")) + ";")

    # 2. render every page to HTML via the test client
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    app = webmod.create_app()
    app.testing = True
    client = app.test_client()
    for path, (template, _key) in webmod.PAGES.items():
        html = client.get(path).get_data(as_text=True)
        out_name = "index.html" if path == "/" else f"{path.strip('/')}.html"
        with open(os.path.join(OUT, out_name), "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  page {path} -> {out_name}")

    # 3. copy static assets (css/js/baked.js)
    shutil.copytree(static_src, os.path.join(OUT, "static"))

    # 4. Vercel config: clean URLs (/how serves how.html), no trailing slash
    with open(os.path.join(OUT, "vercel.json"), "w", encoding="utf-8") as f:
        json.dump({"cleanUrls": True, "trailingSlash": False}, f, indent=2)

    print(f"\nBuilt ./{OUT}/  — deploy this folder to Vercel.")


if __name__ == "__main__":
    build()
