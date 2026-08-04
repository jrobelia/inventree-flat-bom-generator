---
name: Testing the InvenTree Flat BOM Generator plugin
description: |
  How to verify the flat-bom-generator plugin locally on a Windows host when
  the InvenTree devcontainer is not available, plus the preconditions for the
  full test-all.sh / Playwright suite.
---

# Testing the InvenTree Flat BOM Generator plugin

## One-liner

Run the backend unit tests, frontend lint/unit/build, and the mocked traversal
script. Full `test-all.sh` and Playwright E2E need a running InvenTree dev server.

## Commands

From the repo root:

```powershell
python -m unittest discover -s flat_bom_generator/tests/unit -t .
cd frontend
npm run lint
npm run test
npm run build
```

To verify the core BOM traversal logic without a full InvenTree install, run the
standalone mocked traversal script at:

```
C:\Users\Administrator\test_flat_bom_traversal.py
```

## InvenTree dev environment

- `test-all.sh` is designed for an InvenTree devcontainer. It expects
  `INVENTREE_HOME` and `INVENTREE_PLUGIN_DIR` and a running server.
- Playwright E2E (`frontend/e2e/`, `playwright.config.cjs`) expects a server at
  `http://localhost:8001`.
- If those are not available, fall back to the unit/lint/build checks above and
the mocked traversal script.

## Common pitfalls

- On Windows, `python -c` invocations may not put the current directory on
  `sys.path`; use `python -m unittest ... -t .` or set `PYTHONPATH`.
- `ruff` may not be installed on the host; install it if you want to run the
  `test-all.sh` lint steps outside the devcontainer.
- Containerized integration tests fail with `AppRegistryNotReady` unless run
  through `python manage.py test` or `invoke test` inside the InvenTree
  devcontainer, because they import `part.models` and `company.models` eagerly.

## Devin Secrets Needed

None for the fallback test suite. The full E2E suite may need InvenTree admin
credentials if a dev server is running; they are read from `frontend/e2e/config/servers.json`.
