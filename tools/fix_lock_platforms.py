#!/usr/bin/env python
"""
Complete the platform-specific optional dependencies in package-lock.json.

A lock file generated on Windows records only the win32 variants of packages that ship
per-platform binaries (rollup, esbuild, sharp). npm then installs exactly those, and the
build fails on Linux with:

    Error: Cannot find module @rollup/rollup-linux-x64-gnu.
    npm has a bug related to optional dependencies (npm/cli#4828)

The dependency ranges are already declared — it is the resolved `packages` entries that are
missing. This copies the shape from the packages that *are* present, so the lock describes
every platform and `npm ci` works everywhere.

Run after switching machines or changing package managers:
    python tools/fix_lock_platforms.py
"""

import json
import re
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs"
LOCK = DOCS / "package-lock.json"

# npm records these as cpu/os pairs; anything not matching is a normal package.
PLATFORM = re.compile(r"-(win32|darwin|linux|android|freebsd)(-(x64|arm64|arm|ia32|"
                      r"loong64|ppc64|riscv64|s390x|loongarch64))?"
                      r"(-(gnu|musl|gnueabihf|musleabihf|eabi))?$")


def main():
    if not LOCK.exists():
        raise SystemExit(f"no lock file at {LOCK}")

    data = json.loads(LOCK.read_text(encoding="utf-8"))
    packages = data["packages"]

    # collect every optional dependency that some package declares
    declared: dict[str, dict] = {}
    for name, meta in packages.items():
        for dep, spec in (meta.get("optionalDependencies") or {}).items():
            declared.setdefault(dep, {"version": spec, "os": None, "cpu": None})

    # fill os/cpu from any entry we already have, then clone for the missing platforms
    known = {k: v for k, v in packages.items() if PLATFORM.search(k)}
    additions: dict[str, dict] = {}
    for name, meta in packages.items():
        for dep, spec in (meta.get("optionalDependencies") or {}).items():
            if f"node_modules/{dep}" in packages or f"node_modules/{dep}" in additions:
                continue
            # find a sibling variant already present to copy cpu from
            prefix = dep.rsplit("-", 1)[0]
            sample = next(
                (v for k, v in known.items()
                 if k.split("node_modules/")[-1].rsplit("-", 1)[0] == prefix),
                None,
            )
            entry = {
                "version": spec,
                "resolved": f"https://registry.npmjs.org/{dep}/-/{dep.split('/')[-1]}-{spec}.tgz",
                "cpu": (sample or {}).get("cpu"),
                "optional": True,
            }
            m = PLATFORM.search(dep)
            if m:
                entry["os"] = m.group(1)
            additions[f"node_modules/{dep}"] = entry

    packages.update(additions)
    added = len(additions)

    if added:
        LOCK.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"added {added} platform entries; lock now has {len(packages)} packages")
    missing = [k for k, v in packages.items() if not v.get("version")]
    if missing:
        raise SystemExit(f"still missing versions: {missing[:5]}")


if __name__ == "__main__":
    main()