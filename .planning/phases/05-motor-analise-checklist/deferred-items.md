# Deferred Items — Phase 05

Out-of-scope discoveries logged during execution of 05-15 (not fixed, tracked here per executor scope-boundary rule).

## sysdoc.py `VERSION` constant lags pyproject.toml

- **Found during:** 05-15, Task 2 (CHANGELOG 1.5.0 research)
- **File:** `sysdoc.py` line 41 — `VERSION = "1.4.0"`
- **Issue:** `pyproject.toml` already declares `version = "1.5.0"`, but the `sysdoc.py` module constant (surfaced by `sysdoc --version`) was not bumped alongside it. Pre-existing drift, not introduced by 05-15.
- **Why not fixed here:** `sysdoc.py` is not in 05-15's `files_modified` list, and bumping a version constant used across the CLI's `--version` output and packaging is code, not documentation — out of this plan's scope (documentation-only plan per its `<files>` declarations).
- **Recommended follow-up:** a future code-touching plan (or a fast-follow chore commit) should bump `sysdoc.py`'s `VERSION` to `"1.5.0"` to match `pyproject.toml` before/at the 1.5.0 release is considered final.
