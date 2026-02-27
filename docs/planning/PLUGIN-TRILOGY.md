# InvenTree Assembly Plugin Suite

> **Status:** Vision / ideas phase -- capturing intent and open questions  
> **Last Updated:** February 27, 2026

---

## The Vision

Three (possibly four) plugins that turn InvenTree's BOM data into actionable
manufacturing and purchasing outputs. Each plugin answers a different question:

| Plugin | Question it answers | Output |
|--------|-------------------|--------|
| **Flat BOM Generator** | "What parts do I need to buy or how many can I build?" | Flat purchasing list with stock analysis |
| **Build Order Generator** | "What do I need to build?" | Tree of InvenTree Build Orders |
| **Purchase Order Generator** | "What do I need to buy for this BO tree?" | InvenTree Buy List with Purchase Orders grouped by default supplier |
| **BO Hierarchy Display** (maybe) | "Show me the build tree" | Visual tree of BO parent/child relationships |

All plugins share conventions (DRF serializers, React/Mantine/Vitest frontend,
panel-based UI) but are independent codebases. No shared library unless a third
plugin proves the need.

### Cross-Cutting Concern: Allocations and Project Tracking

Every plugin in this suite must be allocation-aware and project-aware:

- **Allocations** affect every stock calculation. "In stock" is meaningless
  without knowing how much is already spoken for (build orders, sales orders).
  Each plugin needs to let users choose whether to account for allocations and
  which allocations to consider (all, this BO tree only, none).
- **On-order parts belong to projects.** Knowing that 100 resistors are on order
  is only useful if you know whether they're earmarked for YOUR project or
  someone else's. Plugins that factor in on-order stock should respect project
  codes and let users filter by project.
- **The Flat BOM Generator already has toggles** for "Include Allocations in
  Build Margin" and "Include On Order in Build Margin." Future plugins should
  follow this pattern but go deeper -- filtering on-order by project and
  showing allocation breakdowns (allocated to which BO, which SO).

---

## Plugin 1: Flat BOM Generator

**Status:** v0.11.53 on `main`, deployed to staging, feature-complete for current scope.

**What it does:** Recursively flattens a nested BOM into a single purchasing-
focused table showing every leaf part with stock levels, build margin, and
warnings. Lives on the Part detail page as a panel.

**Allocation handling today:**
- Toggle to include/exclude allocations in build margin
- Toggle to include/exclude on-order in build margin
- Does NOT filter on-order by project (shows all on-order regardless)

**Remaining work:** See [FlatBOM ROADMAP.md](../FlatBOMGenerator/docs/ROADMAP.md)
for active items (mixed flag handling, UI overhaul, child row consistency).

---

## Plugin 2: Build Order Generator

**Status:** Not started. Next plugin to build.

**What it does:** Traverses the BOM tree for a top-level assembly and creates
InvenTree Build Order objects for every sub-assembly that needs building. The
output is real Build Orders in InvenTree, not just a display.

**Where it lives:** Part detail page (same as Flat BOM) or Build Order detail
page. Open question -- see below.

**Core idea:**
1. User selects a top-level assembly and a build quantity
2. Plugin traverses the BOM, identifies all sub-assemblies that need building
   (same classification rules as Flat BOM -- assemblies without external default
   suppliers get build orders)
3. Displays an interactive collapsible tree showing proposed build orders with
   cascaded quantities
4. User can adjust quantities, deselect nodes already in stock, review before
   committing
5. On confirm, plugin creates Build Order objects bottom-up (children first so
   their output can be allocated to parent builds)

**Key differences from Flat BOM:**
- Output is a tree, not a flat list -- parent/child BO relationships must be
  maintained
- Deduplication works differently: same sub-assembly in multiple branches gets
  summed quantities and placed at the lowest common ancestor in the tree
- Creates real InvenTree objects (Build Orders), not just a temporary display
- Traversal must preserve tree structure, not collapse to flat

**Allocation questions:**
- Should the preview show current stock for each sub-assembly?
- How to handle partial stock? (e.g., need 10, have 3 in stock -- build 7?)
- Should the user be able to choose "build all" vs "build net of stock"?
- Which allocations count? Only unallocated stock, or all stock?

**Open design questions:**
- Exact UX for lowest common ancestor placement and user override
- Whether to allow manual tree restructuring (move a BO to a different parent)
- How to handle re-generation (user already created some child BOs, runs again)
- Performance for large BOM trees (50+ assemblies)

---

## Plugin 3: Purchase Order Generator

**Status:** Not started. Most uncertain of the three.

**What it does:** Takes a list of parts that need purchasing and creates
InvenTree Purchase Orders grouped by supplier, with line items and project
codes.

**The big open question: Where does it live?**

| Option | Entry point | Input data | Pros | Cons |
|--------|------------|------------|------|------|
| **A: Part page** | Same panel as Flat BOM | Flat BOM output (shortfall parts) | Natural flow: generate flat BOM -> see shortfalls -> create POs | Disconnected from Build Orders and their project codes |
| **B: Build Order page** | Panel on BO detail page | BO tree's leaf parts | Tied to a real BO with a project code; can scope allocations to this BO tree | Requires Build Order Generator to exist first |
| **C: Feature inside Flat BOM** | Button in Flat BOM panel | Current flat BOM results | No separate plugin needed; shortest path to value | Bloats Flat BOM; Flat BOM is read-only today (no side effects) |
| **D: Standalone page** | Manufacturing index or custom page | User selects parts manually or from a saved list | Most flexible | Least integrated; poor UX discovery |

Leaning toward **Option B** (BO page context) because:
- Build Orders have project codes that should flow to Purchase Orders
- You know exactly what you're building and can scope allocations correctly
- Natural workflow: create BOs (Plugin 2) -> purchase parts for those BOs (Plugin 3)

But Option A has merit for early-stage planning (before any BOs exist).

**Could this be a feature of Plugin 2 instead of a separate plugin?** If the PO
generator only makes sense in the BO context, it might be a second tab or action
inside the Build Order Generator rather than its own plugin. Worth considering.

**Core workflow (regardless of where it lives):**
1. Show parts that need purchasing (shortfall from flat BOM or BO tree)
2. Group by default supplier
3. For each supplier: find existing pending PO with matching project code, or
   offer to create a new one
4. User reviews, adjusts suppliers if needed, confirms
5. Plugin creates PO line items with quantities and project references

**Allocation and project questions:**
- When calculating shortfall, which allocations to subtract? All? Only this
  project's BOs?
- On-order parts: should it detect that parts are already on order for THIS
  project and skip them?
- If a part has multiple supplier parts, how to choose? Default supplier?
  Lowest price? User picks?
- How to handle parts with no default supplier? (flag for manual handling)

---

## Plugin 4 (Maybe): BO Hierarchy Display

**Status:** Idea only. May not justify a standalone plugin.

**What it does:** Adds a tree view of Build Order parent/child relationships.
InvenTree's BO list page has List View and Calendar View -- this would add a
Tree View showing the hierarchy.

**Could fold into Plugin 2:** If the Build Order Generator already shows an
interactive tree preview, the hierarchy display might just be "show existing
BOs in the same tree format." Could be a mode toggle rather than a new plugin.

**Standalone justification:** Useful even without the generator -- any user with
manually-created BO hierarchies would benefit from a tree view. But is it
enough value for a full plugin?

**Decision:** Defer until Plugin 2 is built. If the tree component is good
enough, extend it to display existing BOs. Only create a separate plugin if
the scope clearly diverges.

---

## Shared Patterns (Not a Shared Library)

Each plugin is its own repo and codebase. Patterns to follow consistently:

**Backend:**
- DRF serializers for all API responses
- Plugin settings via `SettingsMixin` with frontend-surfaced controls
- Type hints on all functions, docstrings with examples
- Fixture-based integration testing

**Frontend:**
- React + Mantine + TypeScript
- Folder structure: `components/`, `hooks/`, `utils/`, `types/`, `columns/`
- Vitest for pure-function unit tests
- Panel-based UI via `UserInterfaceMixin`

**Conventions from Flat BOM worth carrying forward:**
- `visited.copy()` anti-cycle pattern for BOM traversal
- Allocation/on-order toggles as user-facing controls (not hidden settings)
- Child row pattern (`is_child_row`, `child_row_type`, `parent_row_part_id`)
  for expandable sub-rows
- Progressive disclosure for settings

**No shared library for now.** If a third plugin proves the need, extract BOM
traversal core into `inventree-bom-toolkit`. Until then, purpose-built
implementations are simpler and avoid premature abstraction.

---

## Open Questions (Running List)

### Architecture
- [ ] Does the PO Generator justify a standalone plugin, or is it a feature of
      the Build Order Generator?
- [ ] Should any plugin write to InvenTree data on a Part page, or should
      write-actions only happen in BO/PO contexts?

### Allocations
- [ ] How granular should allocation filtering be? (all / this project / this
      BO tree / none)
- [ ] Can we query "on order for project X" efficiently via InvenTree's API?
- [ ] Should Flat BOM gain project-aware on-order filtering before Plugin 3?

### Build Order Generator
- [ ] Where does it live? Part page or BO page?
- [ ] Exact algorithm for lowest common ancestor placement
- [ ] UX for partial stock handling (build net vs build all)
- [ ] How to handle re-runs when some child BOs already exist

### Purchase Order Generator
- [ ] Entry point: Part page, BO page, or inside another plugin?
- [ ] Supplier selection logic when multiple supplier parts exist
- [ ] How to detect "already on order for this project" to avoid duplicates

### BO Hierarchy Display
- [ ] Standalone plugin or feature of Build Order Generator?
- [ ] Can plugins add buttons to InvenTree's main toolbar? (UserInterfaceMixin
      research needed)

---

## Superseded Documents

The following older planning docs are archived for reference. They contain
useful implementation-level thinking but reflect an earlier understanding of
the suite:

- `archive/ASSEMBLY-BOM-PLUGIN-SUITE.md` -- Original 4-plugin suite spec (Dec 2025)
- `archive/BUILD_ORDER_BOM_PLAN.md` -- Early Build Order plugin implementation plan

---

_Last updated: February 27, 2026_
