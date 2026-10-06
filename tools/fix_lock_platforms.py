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


def resolve_version(spec: str) -> str | None:
    """Turn a dependency range into a concrete version.

    `optionalDependencies` in a lock file may hold either an exact version or a range
    (`~2.3.2`). npm rejects a range where a version is expected — "Invalid Version:
    ~2.3.2" — so a range is resolved against whatever the lock already pinned for the same
    package on another platform.
    """
    spec = (spec or "").strip()
    if re.fullmatch(r"\d+\.\d+\.\d+([-+].*)?", spec):
        return spec
    base = spec.lstrip("^~>=< ")
    m = re.match(r"(\d+\.\d+\.\d+)", base)
    return m.group(1) if m else None


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
    # name -> pinned version, so a range can be resolved from a sibling platform entry
    pinned: dict[str, str] = {}
    for key, meta in packages.items():
        name = key.split("node_modules/")[-1]
        v = meta.get("version")
        if v and re.fullmatch(r"\d+\.\d+\.\d+([-+].*)?", str(v)):
            pinned.setdefault(name, str(v))

    additions: dict[str, dict] = {}
    skipped: list[str] = []
    for name, meta in packages.items():
        for dep, spec in (meta.get("optionalDependencies") or {}).items():
            key = f"node_modules/{dep}"
            if key in packages or key in additions:
                continue
            version = resolve_version(spec) or pinned.get(dep)
            if not version:
                skipped.append(dep)
                continue
            prefix = dep.rsplit("-", 1)[0]
            sample = next(
                (v for k, v in known.items()
                 if k.split("node_modules/")[-1].rsplit("-", 1)[0] == prefix),
                None,
            )
            entry = {
                "version": version,
                "resolved": (f"https://registry.npmjs.org/{dep}/-/"
                             f"{dep.split('/')[-1]}-{version}.tgz"),
                "cpu": (sample or {}).get("cpu"),
                "optional": True,
            }
            m = PLATFORM.search(dep)
            if m:
                entry["os"] = m.group(1)
            additions[key] = entry

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