---
name: pypi-release-openagentic-sdk
description: Publish the openagentic-sdk Python package to PyPI. Use when you need to bump the version, run verification, build sdist/wheel (including package data like *.txt/*.mjs), and upload via twine (using .pypirc or TWINE_* env vars). Includes an offline-friendly build path using --no-isolation and a wheel contents check.
---

# PyPI Release: openagentic-sdk

## Release checklist (this repo)

1) Decide the next version (usually patch: `X.Y.(Z+1)`).

2) Update version in all repo-managed places:
   - `pyproject.toml` `[project].version`
   - `openagentic_sdk/_version.py` `__version__`
   - `openagentic_cli/__init__.py` `__version__`
   - If present: any hardcoded OpenAPI/docs version strings (search for the old version)

3) Ensure package data is configured (avoid “missing .txt files after pip install”):
   - `pyproject.toml` `[tool.setuptools.package-data].openagentic_sdk` should include:
     - `tool_prompts/*.txt`
     - `opencode_prompts/*.txt`
     - `opencode_commands/*.txt`
     - `js_runner/*.mjs`

4) Verify locally:
   - `python -m unittest -q`

5) Build artifacts:
   - Preferred (normal environment): `python -m build`
   - If build isolation fails (e.g., no network for fetching build deps): `python -m build --no-isolation`

6) Verify artifacts:
   - `python -m twine check dist/*`
   - Verify wheel contains required resources:
     - `python skills/pypi-release-openagentic-sdk/scripts/check_wheel_data.py dist/openagentic_sdk-<VERSION>-py3-none-any.whl`

7) Upload:
   - If using `~/.pypirc`: `python -m twine upload --config-file ~/.pypirc dist/*`
   - Or env vars:
     - `TWINE_USERNAME=__token__`
     - `TWINE_PASSWORD=pypi-...`
     - `python -m twine upload dist/*`

8) Confirm on PyPI:
   - `https://pypi.org/project/openagentic-sdk/<VERSION>/`

## Notes

- Avoid committing tokens: keep `.pypirc` out of git (it should be in `.gitignore`).
- If you need to re-run `twine upload`, bump the version again (PyPI forbids overwriting an existing version).

