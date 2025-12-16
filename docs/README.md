# Documentation & Planning

This folder contains research, architectural documentation, and planning documents for the Flat BOM Generator plugin.

## Files

### Reference Documentation
- **[Flat BOM Generator Table.csv](Flat%20BOM%20Generator%20Table.csv)** - Example output format
  - Shows expected flat BOM structure
  - Reference for CSV export format
  - Documents all output columns

### Architecture Documentation
- **[ARCHITECTURE-WARNINGS.md](ARCHITECTURE-WARNINGS.md)** - Warning system architecture patterns and data flow
  - Flag prioritization pattern
  - Summary vs per-item warning strategy
  - Data flow lifecycle (CREATE → PROPAGATE → PRESERVE → CONSUME)

### Research & Roadmaps
- **[BOM-ERROR-WARNINGS-RESEARCH.md](BOM-ERROR-WARNINGS-RESEARCH.md)** - Complete research on all warning types
  - Unit mismatches
  - Inactive parts
  - Missing suppliers
  - BOM structure issues
  
- **[WARNINGS-ROADMAP.md](WARNINGS-ROADMAP.md)** - Implementation roadmap for warning system
  - Priority ranking
  - Implementation status
  - Testing strategy

### Development Plans
- **[REFAC-PANEL-PLAN.md](REFAC-PANEL-PLAN.md)** - Refactoring plan for plugin
  - Testing strategy
  - Progress log with dates
  - Known issues
  - Incremental improvement approach
  
- **[PYPI-PUBLISHING-PLAN.md](PYPI-PUBLISHING-PLAN.md)** - Plan for publishing to PyPI
  - Package preparation
  - Distribution strategy

## For AI Agents

When working on this plugin:
1. Check **REFAC-PANEL-PLAN.md** for current refactoring progress
2. Reference **ARCHITECTURE-WARNINGS.md** for warning system patterns
3. Consult **BOM-ERROR-WARNINGS-RESEARCH.md** for implementing new warnings

## For Developers

These documents track the evolution of the plugin from initial development to production-ready code. They capture lessons learned and architectural patterns discovered during development.
