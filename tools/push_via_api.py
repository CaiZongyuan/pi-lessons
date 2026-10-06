#!/usr/bin/env python
"""
Push files to GitHub through the API when git-over-https is blocked.

A proxy in front of this machine refuses CONNECT to github.com while api.github.com still
answers, so `git push` fails but `gh api` works. This uploads individual files through the
contents API.

It is a workaround, not a replacement for git: the local history stays authoritative and
`git push` should be used once the network allows it. Files are uploaded as they are on
disk, so the remote content matches the working tree.

    python tools/push_via_api.py "commit message" path/to/file [more files ...]
"""

import base64
import json
import subprocess
import sys
from pathlib import Path

REPO = "CaiZongyuan/pi-lessons"
BRANCH = "main"
ROOT = Path(__file__).resolve().parent.parent
PAYLOAD = ROOT / ".gh-payload.json"


def api(*args, payload=None):
    """Call `gh api`.

    `gh api` only accepts `--input` after the path argument, and the verb must come right
    after `api` — hence the ordering. JSON cannot be passed as a positional argument
    (it overflows the command line), so it goes through a temp file, always cleaned up.
    """
    try:
        cmd = ["gh", "api", *args]
        if payload is not None:
            PAYLOAD.write_text(json.dumps(payload), encoding="utf-8")
            cmd += ["--input", str(PAYLOAD)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f"gh api failed for {' '.join(args[:4])}:\n{r.stderr[:400]}")
        return json.loads(r.stdout) if r.stdout.strip() else {}
    finally:
        if PAYLOAD.exists():
            PAYLOAD.unlink()


def push(path: Path, message: str) -> None:
    rel = path.relative_to(ROOT).as_posix()
    try:
        sha = api(f"repos/{REPO}/contents/{rel}?ref={BRANCH}")["sha"]
    except SystemExit:
        sha = None

    api("-X", "PUT", f"repos/{REPO}/contents/{rel}", payload={
        "message": message,
        "content": base64.b64encode(path.read_bytes()).decode(),
        "branch": BRANCH,
        **({"sha": sha} if sha else {}),
    })
    print(f"pushed {rel}{' (updated)' if sha else ' (new)'}")


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    message, *files = sys.argv[1:]
    for rel in files:
        push(ROOT / rel, message)


if __name__ == "__main__":
    main()