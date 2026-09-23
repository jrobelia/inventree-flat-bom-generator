#!/bin/bash
set -e

PLUGIN_NAME="FlatBOMGenerator"
MODULE_NAME="flat_bom_generator"

# Optional control flags
# FAST=1          - skip integration, E2E, and frontend build
#                   (lint + unit tests only; fastest deterministic command)
# SKIP_LINT=1     - skip code-quality checks
# SKIP_UNIT=1     - skip Python unit tests
# SKIP_INTEGRATION=1 - skip Python integration tests
# SKIP_FRONTEND=1 - skip all frontend steps (lint, unit, build, E2E)
# SKIP_E2E=1      - skip Playwright E2E (frontend build still runs to catch TS errors)
# CI=1            - recognised by Playwright; test-all.sh sets CI=1 for E2E automatically
FAST="${FAST:-}"
SKIP_LINT="${SKIP_LINT:-}"
SKIP_UNIT="${SKIP_UNIT:-}"
SKIP_INTEGRATION="${SKIP_INTEGRATION:-}"
SKIP_FRONTEND="${SKIP_FRONTEND:-}"
SKIP_E2E="${SKIP_E2E:-}"

# FAST mode skips the slowest / most environment-dependent layers
if [ -n "$FAST" ]; then
  SKIP_INTEGRATION=1
  SKIP_E2E=1
fi

preflight() {
  echo ""
  echo "=========================================="
  echo "Preflight checks"
  echo "=========================================="

  if [ -z "${INVENTREE_HOME:-}" ] || [ ! -d "$INVENTREE_HOME" ]; then
    echo "ERROR: INVENTREE_HOME is not set or does not exist." >&2
    echo "This script must be run inside the InvenTree Plugin AI Toolkit devcontainer." >&2
    exit 1
  fi

  if [ -z "${TOOLKIT_PLUGINS_DIR:-}" ] || [ ! -d "$TOOLKIT_PLUGINS_DIR" ]; then
    echo "ERROR: TOOLKIT_PLUGINS_DIR is not set or does not exist." >&2
    echo "Plugins should be mounted under /workspace/plugins in the devcontainer." >&2
    exit 1
  fi

  case "$PWD" in
    "$TOOLKIT_PLUGINS_DIR"/*) ;;
    *)
      echo "ERROR: Current directory ($PWD) is not under TOOLKIT_PLUGINS_DIR ($TOOLKIT_PLUGINS_DIR)." >&2
      echo "Run this script from a plugin directory inside the devcontainer." >&2
      exit 1
      ;;
  esac

  if [ ! -d "$MODULE_NAME" ]; then
    echo "ERROR: Plugin package directory '$MODULE_NAME' not found in $PWD." >&2
    echo "The plugin does not appear to be linked/scaffolded correctly." >&2
    exit 1
  fi

  # Only check server and dataset if a test layer actually needs them.
  if [ -n "$SKIP_INTEGRATION" ] && [ -n "$SKIP_E2E" ]; then
    echo "Skipping server/dataset checks (integration and E2E are both skipped)."
    echo "Preflight checks passed"
    return 0
  fi

  SERVER_URL="${INVENTREE_SERVER_URL:-http://localhost:8001}"
  echo "Checking InvenTree server at $SERVER_URL ..."

  if ! INVENTREE_SERVER_URL="$SERVER_URL" python - <<'PY'
import os, sys, urllib.request
url = os.environ['INVENTREE_SERVER_URL'].rstrip('/') + '/api/system/health/'
try:
    with urllib.request.urlopen(url, timeout=5) as response:
        if response.status == 200:
            sys.exit(0)
        print(f"ERROR: InvenTree server returned status {response.status} at {url}", file=sys.stderr)
        sys.exit(1)
except Exception as e:
    print(f"ERROR: Could not reach InvenTree server at {url}: {e}", file=sys.stderr)
    sys.exit(1)
PY
  then
    echo "Start the server with: cd /workspace/reference/inventree-source && invoke dev.server" >&2
    exit 1
  fi

  echo "Checking InvenTree dataset..."

  if ! INVENTREE_HOME="$INVENTREE_HOME" python - <<'PY'
import os, sys
sys.path.insert(0, os.path.join(os.environ['INVENTREE_HOME'], 'src', 'backend', 'InvenTree'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
try:
    import django
    django.setup()
    from part.models import Part
    count = Part.objects.count()
    if count == 0:
        print("ERROR: No Part records found. The server is running but the dataset is empty.", file=sys.stderr)
        print("Load data with 'invoke dev.setup-test -i' once demo-data import is debugged, or use your own fixtures.", file=sys.stderr)
        sys.exit(1)
except Exception as e:
    print(f"ERROR: Could not check dataset: {e}", file=sys.stderr)
    sys.exit(1)
PY
  then
    exit 1
  fi

  echo "Preflight checks passed"
}

has_frontend_dir() {
  [ -d "frontend" ] && [ -f "frontend/package.json" ]
}

has_user_interface_mixin() {
  local core_file="$MODULE_NAME/core.py"
  [ -f "$core_file" ] && grep -q "UserInterfaceMixin" "$core_file"
}

should_run_frontend() {
  if [ -n "$SKIP_FRONTEND" ]; then
    return 1
  fi
  if ! has_frontend_dir; then
    return 1
  fi
  # If the plugin claims to have a UI but the frontend directory is missing, warn but do not fail.
  if has_user_interface_mixin; then
    return 0
  fi
  # Some plugins may have a frontend directory without UserInterfaceMixin (e.g. shared assets).
  # Run frontend checks only if the package has test/build scripts.
  if grep -qE '"test"|"build"|"lint"' frontend/package.json 2>/dev/null; then
    return 0
  fi
  return 1
}

if has_user_interface_mixin && ! has_frontend_dir; then
  echo ""
  echo "WARNING: $MODULE_NAME/core.py imports UserInterfaceMixin but no frontend/ directory was found." >&2
  echo "Skipping frontend steps. If this plugin should have a UI, scaffold the frontend package." >&2
fi

echo "=========================================="
echo "Running All Tests for $PLUGIN_NAME"
echo "=========================================="

preflight

# Code quality checks
if [ -z "$SKIP_LINT" ]; then
  echo ""
  echo "Step 1: Running code quality checks..."
  echo "----------------------------------------"

  echo "Checking Python code with ruff..."
  # EXE002 is ignored because plugin code lives on the Windows /workspace bind
  # mount, which reports all .py files as executable and cannot be chmod'd.
  ruff check --ignore EXE002 "$MODULE_NAME"
  ruff format --check "$MODULE_NAME"

  if should_run_frontend; then
    echo "Checking frontend code..."
    cd frontend
    npm run lint
    cd ..
  fi

  echo "✓ Code quality checks passed"
fi

# Unit tests
if [ -z "$SKIP_UNIT" ]; then
  echo ""
  echo "Step 2: Running Python unit tests..."
  echo "----------------------------------------"
  python -m pytest "$MODULE_NAME/tests/unit" -v
  echo "✓ Unit tests passed"

  if should_run_frontend; then
    echo ""
    echo "Step 3: Running frontend unit tests..."
    echo "----------------------------------------"
    cd frontend
    npm run test
    cd ..
    echo "✓ Frontend unit tests passed"
  fi
fi

# Integration tests
if [ -z "$SKIP_INTEGRATION" ]; then
  echo ""
  echo "Step 4: Running Python integration tests..."
  echo "----------------------------------------"
  PYTHONPATH="$INVENTREE_HOME/src/backend/InvenTree:$PYTHONPATH" \
  DJANGO_SETTINGS_MODULE=InvenTree.settings \
  python -m pytest "$MODULE_NAME/tests/integration" -v
  echo "✓ Integration tests passed"
fi

# Frontend build and E2E tests
if should_run_frontend; then
  if [ -z "$FAST" ]; then
    echo ""
    echo "Step 5: Building frontend..."
    echo "----------------------------------------"
    cd frontend
    npm run build
    cd ..
    echo "✓ Frontend build passed"
  fi

  if [ -z "$SKIP_E2E" ] && [ -z "$FAST" ]; then
    echo ""
    echo "Step 6: Running E2E tests with Playwright..."
    echo "----------------------------------------"
    echo "Note: Server and dataset were verified by preflight checks."
    echo "Reports and artifacts will be written to frontend/playwright-report/ and frontend/test-results/."
    cd frontend
    CI=1 npm run test:e2e
    cd ..
    echo "✓ E2E tests passed"
  fi
fi

echo ""
echo "=========================================="
echo "All tests passed successfully!"
echo "=========================================="
