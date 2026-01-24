from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _iter_example_scripts(repo_root: Path) -> list[Path]:
    example_dir = repo_root / "example"
    scripts = sorted(p for p in example_dir.glob("*.py") if p.is_file())

    # Skip helper modules (not intended to be executed directly).
    skip = {"_common.py", "auth.py"}
    return [p for p in scripts if p.name not in skip]


def main(argv: list[str] | None = None) -> int:
    argv = list(argv or [])
    repo_root = _repo_root()

    offline = True
    if "--online" in argv:
        offline = False
        argv = [a for a in argv if a != "--online"]
    if "--offline" in argv:
        offline = True
        argv = [a for a in argv if a != "--offline"]

    only: str | None = None
    if "--only" in argv:
        i = argv.index("--only")
        try:
            only = argv[i + 1]
        except IndexError:
            print("error: --only requires a value (substring match against filename)")
            return 2
        argv = argv[:i] + argv[i + 2 :]
    if argv:
        print(f"error: unknown args: {argv}")
        return 2

    scripts = _iter_example_scripts(repo_root)
    if not scripts:
        print("No example scripts found.")
        return 1

    env = dict(os.environ)
    if offline:
        env.setdefault("OPENAGENTIC_SDK_EXAMPLE_OFFLINE", "1")
        env.setdefault("OPENAGENTIC_SDK_EXAMPLE_PERMISSION_MODE", "bypass")
        env.setdefault("OPENAGENTIC_SDK_EXAMPLE_INTERACTIVE", "0")
    env.setdefault("OA_PROVIDER", "rightcode")  # avoid OPENAI_API_KEY requirement in example/53
    env.setdefault("PYTHONUNBUFFERED", "1")

    python = sys.executable
    failures: list[tuple[Path, int, str]] = []

    if only:
        scripts = [s for s in scripts if only in s.name]
        if not scripts:
            print(f"No scripts matched --only {only!r}")
            return 1

    for i, script in enumerate(scripts, start=1):
        rel = script.relative_to(repo_root)
        mode = "offline" if offline else "online"
        print(f"[{i}/{len(scripts)}] ({mode}) {rel}", flush=True)
        proc = subprocess.run(
            [python, str(rel)],
            cwd=repo_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if proc.returncode != 0:
            out = (proc.stdout or "").strip()
            tail = "\n".join(out.splitlines()[-80:])
            failures.append((rel, proc.returncode, tail))

    if failures:
        print("\nFAILURES:")
        for rel, code, tail in failures:
            print(f"\n--- {rel} (exit {code}) ---")
            print(tail)
        return 2

    print(f"\nOK: {len(scripts)}/{len(scripts)} examples exited 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
