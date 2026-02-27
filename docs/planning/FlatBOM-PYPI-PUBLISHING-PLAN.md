# PyPI Publishing Plan for FlatBOMGenerator

**Status:** Optional - Git-based installation already works perfectly  
**Last Updated:** 2025-12-11  
**Package Name:** inventree-flat-bom-generator  
**Current Version:** 0.1.0  

---

## Do You Need PyPI?

**Current Installation Method (Works Great):**
```bash
pip install git+https://github.com/jrobelia/inventree-flat-bom-generator.git
```

**Advantages of Current Method:**
- ✅ Already working in production
- ✅ No extra setup needed
- ✅ Direct from GitHub (always latest)
- ✅ Version pinning available: `pip install git+https://...@v0.1.0`
- ✅ Works with InvenTree plugin discovery

**PyPI Advantages:**
- 📦 Shorter install command: `pip install inventree-flat-bom-generator`
- 🔍 Discoverable in PyPI search
- 📊 Download statistics
- 🌐 Wider visibility in Python community

**Verdict:** PyPI is nice-to-have, not required. Only publish if you want:
1. Easier discovery by other InvenTree users
2. Professional appearance for portfolio
3. Download statistics tracking

---

## Prerequisites (One-Time Setup)

### 1. PyPI Account
1. Create account at https://pypi.org/account/register/
2. Verify email address
3. Enable 2FA (required for publishing)
4. Create API token:
   - Go to https://pypi.org/manage/account/token/
   - Create token with scope "Entire account" or specific to this project
   - Save token securely (you'll only see it once)

### 2. TestPyPI Account (Recommended for Testing)
1. Create account at https://test.pypi.org/account/register/
2. Create separate API token
3. Use for testing before real PyPI upload

### 3. Configure Tokens Locally
Create/edit `~/.pypirc`:
```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YOUR-ACTUAL-TOKEN-HERE

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-YOUR-TEST-TOKEN-HERE
```

**Security Note:** Never commit `.pypirc` to git!

---

## Pre-Publishing Checklist

Before each release, verify:

### 1. Metadata in `pyproject.toml`
- [x] Package name: `inventree-flat-bom-generator`
- [x] Version number (update for each release)
- [x] Description, author, license
- [x] GitHub repository URL
- [x] Entry points configured correctly
- [x] Dependencies listed accurately

### 2. Code Quality
```powershell
# Run from FlatBOMGenerator directory
cd plugins/FlatBOMGenerator

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Check code formatting
pre-commit run --all-files

# Run tests (when available)
# pytest
```

### 3. Documentation
- [x] README.md is complete and accurate
- [x] Installation instructions work
- [ ] CHANGELOG.md updated (create if doesn't exist)
- [ ] Version number in all files matches

### 4. Clean Build Environment
```powershell
# Remove old build artifacts
if (Test-Path dist) { Remove-Item -Recurse -Force dist }
if (Test-Path build) { Remove-Item -Recurse -Force build }
if (Test-Path *.egg-info) { Remove-Item -Recurse -Force *.egg-info }
```

---

## Publishing Process

### Step 1: Update Version Number
Edit `pyproject.toml`:
```toml
[project]
version = "0.1.1"  # Increment according to semantic versioning
```

### Step 2: Build Frontend
```powershell
# From toolkit root
.\scripts\Build-Plugin.ps1 -Plugin "FlatBOMGenerator"
```

Verify `flat_bom_generator/static/Panel.js` exists.

### Step 3: Build Distribution Packages
```powershell
# Activate virtual environment
cd plugins/FlatBOMGenerator
.\.venv\Scripts\Activate.ps1

# Install build tools (if not already installed)
pip install --upgrade build twine

# Build packages
python -m build
```

This creates:
- `dist/inventree_flat_bom_generator-0.1.1.tar.gz` (source)
- `dist/inventree_flat_bom_generator-0.1.1-py3-none-any.whl` (wheel)

### Step 4: Test Upload to TestPyPI (Optional but Recommended)
```powershell
# Upload to TestPyPI
python -m twine upload --repository testpypi dist/*

# Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ inventree-flat-bom-generator
```

### Step 5: Upload to Real PyPI
```powershell
# Upload to PyPI (irreversible!)
python -m twine upload dist/*
```

You'll be prompted for credentials (use `__token__` as username, token as password) or it will use `.pypirc`.

### Step 6: Verify Installation
```powershell
# Test installation from PyPI
pip install inventree-flat-bom-generator

# Verify plugin loads
python -c "from flat_bom_generator.core import FlatBOMGenerator; print('Plugin loaded successfully')"
```

---

## Version Management Strategy

### Semantic Versioning (MAJOR.MINOR.PATCH)
- **MAJOR (1.0.0)**: Breaking changes, incompatible API changes
- **MINOR (0.2.0)**: New features, backward-compatible
- **PATCH (0.1.1)**: Bug fixes, backward-compatible

### Current Status
- **0.1.0**: Initial release (not published to PyPI yet)
- **Next**: 0.1.1 for bug fixes, 0.2.0 for new features

### Files to Update for Each Version
1. `pyproject.toml` → `version = "X.Y.Z"`
2. `CHANGELOG.md` → Add release notes (create if doesn't exist)
3. Git tag: `git tag vX.Y.Z`

---

## GitHub Release Integration

### Manual GitHub Release Process
1. Tag the commit:
   ```powershell
   git tag v0.1.1
   git push origin v0.1.1
   ```

2. Create GitHub release:
   - Go to https://github.com/jrobelia/inventree-flat-bom-generator/releases/new
   - Select tag `v0.1.1`
   - Title: "v0.1.1 - Brief Description"
   - Description: Copy from CHANGELOG.md
   - Attach build artifacts (optional): Upload `dist/*.whl` and `dist/*.tar.gz`

### Automated Publishing with GitHub Actions (Future Enhancement)
Create `.github/workflows/publish-to-pypi.yml`:
```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '20'
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Build frontend
        run: |
          cd frontend
          npm ci
          npm run build
      
      - name: Build package
        run: |
          pip install build
          python -m build
      
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          password: ${{ secrets.PYPI_API_TOKEN }}
```

**Note:** Requires adding `PYPI_API_TOKEN` to GitHub repository secrets.

---

## Post-Publishing Checklist

After successful PyPI upload:

1. **Update README.md** - Add PyPI badge:
   ```markdown
   [![PyPI version](https://badge.fury.io/py/inventree-flat-bom-generator.svg)](https://pypi.org/project/inventree-flat-bom-generator/)
   ```

2. **Update Installation Instructions** - Add PyPI method:
   ```markdown
   # From PyPI (recommended)
   pip install inventree-flat-bom-generator
   
   # From GitHub (development)
   pip install git+https://github.com/jrobelia/inventree-flat-bom-generator.git
   ```

3. **Announce Release**:
   - InvenTree forum/community
   - GitHub repository description
   - Social media (optional)

4. **Monitor PyPI Page**: https://pypi.org/project/inventree-flat-bom-generator/
   - Check download statistics
   - Verify metadata displays correctly
   - Test installation from PyPI

---

## Troubleshooting

### Common Issues

**"Package already exists"**
- Cannot re-upload same version to PyPI (immutable)
- Solution: Increment version number in `pyproject.toml`

**"Invalid distribution"**
- Missing required metadata in `pyproject.toml`
- Solution: Run `python -m build` again after fixing metadata

**"Authentication failed"**
- Wrong token or `.pypirc` misconfigured
- Solution: Verify token at https://pypi.org/manage/account/token/

**"Frontend assets missing"**
- `static/Panel.js` not included in build
- Solution: Run `Build-Plugin.ps1` before `python -m build`

**"Entry point not found" after installation**
- Entry points in `pyproject.toml` misconfigured
- Solution: Verify `[project.entry-points."inventree_plugins"]` section

---

## Current Status & Recommendations

### ✅ Ready for PyPI
Your plugin is technically ready to publish:
- Entry points configured correctly
- Package metadata complete
- Frontend builds successfully
- Installation works via Git

### 🤔 Should You Publish Now?
**Recommended: Wait until you have:**
1. At least one external user/tester besides yourself
2. Stable feature set (not changing daily)
3. Basic documentation complete
4. Time to respond to PyPI user questions

**Current Recommendation:**
- Keep using Git-based installation for now
- Publish to PyPI when plugin is stable and you want wider adoption
- No rush - Git installation works perfectly

### 📋 Before First PyPI Release
Create these files:
- `CHANGELOG.md` - Version history
- Update README.md with more usage examples
- Consider adding screenshots/GIFs to README
- Write CONTRIBUTING.md if accepting contributions

---

## Quick Reference Commands

### Build and Publish
```powershell
# 1. Update version in pyproject.toml
# 2. Build frontend
.\scripts\Build-Plugin.ps1 -Plugin "FlatBOMGenerator"

# 3. Build packages
cd plugins\FlatBOMGenerator
.\.venv\Scripts\Activate.ps1
python -m build

# 4. Upload to PyPI
python -m twine upload dist/*

# 5. Tag release
git tag v0.1.1
git push origin v0.1.1
```

### Test Installation
```powershell
# From PyPI
pip install inventree-flat-bom-generator

# From GitHub
pip install git+https://github.com/jrobelia/inventree-flat-bom-generator.git

# From local (editable)
pip install -e .
```

---

**Remember:** PyPI is optional. Your current Git-based installation method is production-ready and works great. Publish to PyPI when you're ready for wider distribution, not before.
