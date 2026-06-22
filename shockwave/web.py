"""Shockwave — local web app: a multi-page product site + the Blast Monitor.

Run:  shockwave-web   (then open http://127.0.0.1:7777)
Needs the optional web extra:  pip install -e .[web]
"""

from __future__ import annotations

import os
import sys

from . import blast_radius, report
from .orbit_client import LocalBackend, RemoteBackend, OrbitError, enable_os_trust

PAGES = {
    "/": ("home.html", "home"),
    "/how": ("how.html", "how"),
    "/features": ("features.html", "features"),
    "/surfaces": ("surfaces.html", "surfaces"),
    "/docs": ("docs.html", "docs"),
    "/app": ("app.html", "app"),
}


def create_app():
    from flask import Flask, request, jsonify, render_template

    here = os.path.dirname(__file__)
    app = Flask(
        __name__,
        template_folder=os.path.join(here, "web", "templates"),
        static_folder=os.path.join(here, "web", "static"),
        static_url_path="/static",
    )

    def make_view(template: str, key: str):
        def view():
            return render_template(template, active=key)
        return view

    for path, (template, key) in PAGES.items():
        app.add_url_rule(path, key, make_view(template, key))

    @app.post("/api/analyze")
    def analyze():
        # POST + token in the body (or X-Orbit-Token header) so secrets never
        # land in URLs, server logs, or browser history.
        enable_os_trust()
        data = request.get_json(silent=True) or {}
        seed = (data.get("seed") or "").strip()
        if not seed:
            return jsonify({"error": "Enter a function, class, or file to analyze."}), 400
        try:
            hops = max(1, min(8, int(data.get("hops", 4))))
        except (ValueError, TypeError):
            hops = 4
        kind = data.get("backend", "local")
        try:
            if kind == "remote":
                url = data.get("url") or "https://gitlab.com"
                token = data.get("token") or request.headers.get("X-Orbit-Token") or os.environ.get("GITLAB_TOKEN", "")
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
    print(f"Shockwave  →  http://127.0.0.1:{port}")
    create_app().run(host="127.0.0.1", port=port, debug=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
