"""Shockwave Blast Monitor — a small local web UI for the blast map.

Run:  shockwave-web   (then open http://127.0.0.1:7777)
Needs the optional web extra:  pip install -e .[web]
"""

from __future__ import annotations

import os
import sys

from . import blast_radius, report
from .orbit_client import LocalBackend, RemoteBackend, OrbitError, enable_os_trust


def create_app():
    from flask import Flask, request, jsonify, send_from_directory

    here = os.path.dirname(__file__)
    app = Flask(__name__, static_folder=os.path.join(here, "web"), static_url_path="")

    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.get("/app")
    def monitor():
        return send_from_directory(app.static_folder, "app.html")

    @app.get("/api/analyze")
    def analyze():
        enable_os_trust()
        seed = (request.args.get("seed") or "").strip()
        if not seed:
            return jsonify({"error": "Enter a function, class, or file to analyze."}), 400
        try:
            hops = max(1, min(8, int(request.args.get("hops", "4"))))
        except ValueError:
            hops = 4
        kind = request.args.get("backend", "local")
        try:
            if kind == "remote":
                url = request.args.get("url") or "https://gitlab.com"
                token = request.args.get("token") or os.environ.get("GITLAB_TOKEN", "")
                if not token:
                    return jsonify({"error": "Remote analysis needs a GitLab token."}), 400
                radius = blast_radius.compute_remote(RemoteBackend(url, token), seed, max_hops=hops)
            else:
                radius = blast_radius.compute(LocalBackend(), seed, max_hops=hops)
        except OrbitError as exc:
            return jsonify({"error": str(exc)}), 502
        if not radius.seed_ids:
            return jsonify({"error": f"No definition matched '{seed}' in the indexed graph."}), 404
        return jsonify(report.to_graph(radius))

    return app


def main(argv: list[str] | None = None) -> int:
    try:
        import flask  # noqa: F401
    except ImportError:
        print("Shockwave web needs Flask: pip install -e .[web]", file=sys.stderr)
        return 1
    port = int(os.environ.get("SHOCKWAVE_PORT", "7777"))
    print(f"Shockwave Blast Monitor  →  http://127.0.0.1:{port}")
    create_app().run(host="127.0.0.1", port=port, debug=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
