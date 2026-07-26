#!/bin/bash
set -e

PLUGIN_NAME="FlatBOMGenerator"
MODULE_NAME="flat_bom_generator"

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

  if [ -z "${INVENTREE_PLUGIN_DIR:-}" ] || [ ! -d "$INVENTREE_PLUGIN_DIR" ]; then
    echo "ERROR: INVENTREE_PLUGIN_DIR is not set or does not exist." >&2
    echo "Plugins should be mounted under /workspace/plugins in the devcontainer." >&2
    exit 1
  fi

  case "$PWD" in
    "$INVENTREE_PLUGIN_DIR"/*) ;;
    *)
      echo "ERROR: Current directory ($PWD) is not under INVENTREE_PLUGIN_DIR ($INVENTREE_PLUGIN_DIR)." >&2
      echo "Run this script from a plugin directory inside the devcontainer." >&2
      exit 1
      ;;
  esac

  if [ ! -d "$MODULE_NAME" ]; then
    echo "ERROR: Plugin package directory '$MODULE_NAME' not found in $PWD." >&2
    echo "The plugin does not appear to be linked/scaffolded correctly." >&2
    exit 1
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

echo "=========================================="
echo "Running All Tests for $PLUGIN_NAME"
echo "=========================================="

preflight

# Code quality checks
echo ""
echo "Step 1: Running code quality checks..."
echo "----------------------------------------"

# Python linting and formatting
echo "Checking Python code with ruff..."
ruff check flat_bom_generator
ruff format --check flat_bom_generator

# Frontend linting
echo "Checking frontend code with biome..."
cd frontend
npm run lint
cd ..

echo "✓ Code quality checks passed"

# Unit tests
echo ""
echo "Step 2: Running Python unit tests..."
echo "----------------------------------------"
python -m pytest flat_bom_generator/tests/unit -v
echo "✓ Unit tests passed"

# Integration tests
echo ""
echo "Step 3: Running Python integration tests..."
echo "----------------------------------------"
PYTHONPATH="$INVENTREE_HOME/src/backend/InvenTree:$PYTHONPATH" \
DJANGO_SETTINGS_MODULE=InvenTree.settings \
python -m pytest flat_bom_generator/tests/integration -v
echo "✓ Integration tests passed"

# Frontend unit tests
echo ""
echo "Step 4: Running frontend unit tests..."
echo "----------------------------------------"
cd frontend
npm run test
cd ..
echo "✓ Frontend unit tests passed"

# E2E tests
echo ""
echo "Step 5: Running E2E tests with Playwright..."
echo "----------------------------------------"
echo "Note: Server and dataset were verified by preflight checks."
cd frontend
npm run build
npm run test:e2e
cd ..
echo "✓ E2E tests passed"

echo ""
echo "=========================================="
echo "All tests passed successfully!"
echo "=========================================="
