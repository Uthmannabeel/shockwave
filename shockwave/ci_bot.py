"""Shockwave merge-request bot.

Runs inside GitLab CI on a ``merge_request_event``: it reads the MR's changed
files, computes their blast radius against the **live Orbit Remote** graph, and
posts a review comment (summary, untested hotspots, and suggested test stubs)
back on the merge request.

All inputs come from GitLab CI predefined variables plus one secret:
``GITLAB_TOKEN`` (a masked CI variable, ``api`` scope) — used both to query
Orbit and to post the note.
"""

from __future__ import annotations

import os
import sys

from . import blast_radius, report
from .orbit_client import RemoteBackend, OrbitError

CODE_EXTENSIONS = (
    ".py", ".rb", ".js", ".ts", ".tsx", ".jsx", ".go", ".java", ".kt",
    ".rs", ".c", ".cc", ".cpp", ".h", ".hpp", ".cs", ".php",
)

HEADER = "## 🤖⚡ Shockwave — blast-radius review\n\n"
FOOTER = (
    "\n\n---\n*Computed from the [GitLab Orbit](https://about.gitlab.com/gitlab-orbit/) "
    "knowledge graph by [Shockwave](https://github.com/Uthmannabeel/shockwave). "
    "Indexed facts, not guesses.*"
)


def _env(name: str, default: str | None = None) -> str:
    val = os.environ.get(name, default)
    if val is None:
        raise OrbitError(f"missing required CI variable: {name}")
    return val


def _changed_files(api: str, token: str, project_id: str, mr_iid: str) -> list[str]:
    import requests

    url = f"{api}/projects/{project_id}/merge_requests/{mr_iid}/diffs?per_page=100"
    resp = requests.get(url, headers={"PRIVATE-TOKEN": token}, timeout=30)
    if resp.status_code != 200:
        raise OrbitError(f"could not list MR diffs (HTTP {resp.status_code}): {resp.text}")
    files = []
    for d in resp.json():
        if d.get("deleted_file"):
            continue
        path = d.get("new_path") or d.get("old_path") or ""
        if path.endswith(CODE_EXTENSIONS):
            files.append(path)
    return files


def _post_note(api: str, token: str, project_id: str, mr_iid: str, body: str) -> None:
    import requests

    url = f"{api}/projects/{project_id}/merge_requests/{mr_iid}/notes"
    resp = requests.post(url, headers={"PRIVATE-TOKEN": token}, json={"body": body}, timeout=30)
    if resp.status_code not in (200, 201):
        raise OrbitError(f"could not post MR note (HTTP {resp.status_code}): {resp.text}")


def main(argv: list[str] | None = None) -> int:
    try:
        server = _env("CI_SERVER_URL", "https://gitlab.com")
        api = os.environ.get("CI_API_V4_URL", f"{server}/api/v4")
        token = _env("GITLAB_TOKEN")
        project_id = _env("CI_PROJECT_ID")
        mr_iid = _env("CI_MERGE_REQUEST_IID")
        max_hops = int(os.environ.get("SHOCKWAVE_MAX_HOPS", "5"))

        files = _changed_files(api, token, project_id, mr_iid)
        if not files:
            print("Shockwave: no code files changed; skipping.")
            return 0

        backend = RemoteBackend(server, token)
        radius = blast_radius.compute_for_files_remote(backend, files, max_hops=max_hops)

        if not radius.affected:
            summary = (
                f"Changed {len(files)} file(s); the Orbit graph shows **nothing "
                f"else depends on them** — low blast radius. ✅"
            )
            body = HEADER + summary + FOOTER
        else:
            body = HEADER + report.to_markdown(radius) + FOOTER

        _post_note(api, token, project_id, mr_iid, body)
        print(f"Shockwave: posted blast-radius review ({len(radius.affected)} affected).")
        return 0
    except OrbitError as exc:
        print(f"shockwave-bot: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
