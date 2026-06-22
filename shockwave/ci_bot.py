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
from .orbit_client import RemoteBackend, OrbitError, enable_os_trust

CODE_EXTENSIONS = (
    ".py", ".rb", ".js", ".ts", ".tsx", ".jsx", ".go", ".java", ".kt",
    ".rs", ".c", ".cc", ".cpp", ".h", ".hpp", ".cs", ".php",
)

# Hidden marker so re-runs update the same comment instead of duplicating it.
MARKER = "<!-- shockwave-blast-radius -->"
HEADER = f"{MARKER}\n## 🤖⚡ Shockwave — blast-radius review\n\n"
MAX_BODY = 60_000  # keep comments well under GitLab's note limit
FOOTER = (
    "\n\n---\n*Computed from the [GitLab Orbit](https://about.gitlab.com/gitlab-orbit/) "
    "knowledge graph by [Shockwave](https://gitlab.com/uthmannabeel-group/Shockwave-project). "
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
    code, other = [], 0
    for d in resp.json():
        if d.get("deleted_file"):
            continue
        path = d.get("new_path") or d.get("old_path") or ""
        if path.endswith(CODE_EXTENSIONS):
            code.append(path)
        elif path:
            other += 1
    return code, other


def _upsert_note(api: str, token: str, project_id: str, mr_iid: str, body: str) -> None:
    """Update Shockwave's existing comment if present, else create one."""
    import requests

    headers = {"PRIVATE-TOKEN": token}
    base = f"{api}/projects/{project_id}/merge_requests/{mr_iid}/notes"
    existing_id = None
    try:
        resp = requests.get(f"{base}?per_page=100", headers=headers, timeout=30)
        if resp.status_code == 200:
            for note in resp.json():
                if MARKER in (note.get("body") or ""):
                    existing_id = note["id"]
                    break
    except requests.RequestException:
        pass  # fall through to create

    if existing_id is not None:
        resp = requests.put(f"{base}/{existing_id}", headers=headers, json={"body": body}, timeout=30)
    else:
        resp = requests.post(base, headers=headers, json={"body": body}, timeout=30)
    if resp.status_code not in (200, 201):
        raise OrbitError(f"could not post MR note (HTTP {resp.status_code}): {resp.text}")


def main(argv: list[str] | None = None) -> int:
    try:
        enable_os_trust()
        server = _env("CI_SERVER_URL", "https://gitlab.com")
        api = os.environ.get("CI_API_V4_URL", f"{server}/api/v4")
        token = _env("GITLAB_TOKEN")
        project_id = _env("CI_PROJECT_ID")
        mr_iid = _env("CI_MERGE_REQUEST_IID")
        max_hops = int(os.environ.get("SHOCKWAVE_MAX_HOPS", "5"))

        files, other = _changed_files(api, token, project_id, mr_iid)
        if not files:
            if other:
                note = (
                    f"This MR changes **{other}** file(s) in languages Orbit doesn't "
                    f"index (config, docs, etc.). Shockwave analyzes the code graph, "
                    f"so **no impact was computed** — review non-code changes manually."
                )
                _upsert_note(api, token, project_id, mr_iid, HEADER + note + FOOTER)
                print("Shockwave: only non-code files changed; posted a note.")
            else:
                print("Shockwave: no files changed; skipping.")
            return 0

        backend = RemoteBackend(server, token)
        radius = blast_radius.compute_for_files_remote(backend, files, max_hops=max_hops)

        if not radius.affected:
            summary = (
                f"Changed {len(files)} code file(s); the Orbit graph shows **nothing "
                f"else depends on them** — low blast radius. ✅"
            )
            body = HEADER + summary + FOOTER
        else:
            body = HEADER + report.to_markdown(radius) + FOOTER

        if len(body) > MAX_BODY:
            body = body[:MAX_BODY] + "\n\n*…report truncated.*" + FOOTER

        _upsert_note(api, token, project_id, mr_iid, body)
        print(f"Shockwave: posted blast-radius review ({len(radius.affected)} affected).")
        return 0
    except OrbitError as exc:
        print(f"shockwave-bot: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
