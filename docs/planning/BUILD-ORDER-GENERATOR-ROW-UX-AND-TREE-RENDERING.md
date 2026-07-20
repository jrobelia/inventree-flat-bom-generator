# Build Order Generator — Row Interaction Model & Tree Rendering

> **Status:** Vision / ideas phase — companion to `BUILD-ORDER-GENERATOR-UX.md`
> and `PLUGIN-TRILOGY.md`. Reading order below is deliberate: Part 1 defines
> terms (what counts as an "opportunity," and what's already native),
> Part 2 states the actual MVP, Part 3 covers how the tree renders
> technically, Part 4 covers a natural extension (status viewer), and
> Part 5 parks detailed row-interaction design that's real thinking-work
> but explicitly deferred, not MVP.
>
> Most technical claims below are verified directly against source:
> `github.com/inventree/InvenTree` and `github.com/inventree/plugin-creator`
> (both cloned — including a pre-1.0 tag for historical comparison), plus
> `@inventreedb/ui@1.4.5` (pulled via `npm pack` and inspected). Anything
> not explicitly framed as "confirmed" should still be treated as
> **to-verify**, same convention as the parent doc.

---

## Part 1: BO Status Model — Existing, Draft/Opportunity, On-Order, Project-Code Hint

### Existing Status Is Unambiguous

- **Existing** = a BO record was actually created for this line. No judgment
call involved.
- **Draft / opportunity** = a required assembly line with no BO created yet
and not fully allocated. This is the "there's a decision to make here"
signal the MVP (Part 2) and tree rendering (Part 3) are built around, and
that the deferred row-interaction design (Part 5) also assumes.

### On-Order Netting — Bare Minimum, Already Native

Confirmed directly against source: `on_order` is already a real field on
`BuildLineTable` — column, filter, and a tooltip line ("On order: X"),
confirmed at `BuildLineTable.tsx` lines 240–286 and 509–511. This isn't
something the plugin needs to build; the netting math in Part 5's Row
Layout section (Required → minus allocated → minus netted stock/POs/
existing builds → Outstanding) just consumes this existing field. Bare
minimum, zero new work.

### Project-Code Match — a Hint Column, Not a New Workflow

There's a real question a plain `on_order` number can't answer: is that
incoming stock actually meant for *this* BO, or just coincidental stock on
order for something else entirely? `project_code` already exists as a
real, filterable field on both Build Orders and Purchase Orders (confirmed:
`ProjectCodeColumn`, `ProjectCodeFilter`, `HasProjectCodeFilter` in
`PurchaseOrderTable.tsx` / `PurchaseOrderFilters.tsx`) — so a plain
read-only comparison (does the PO's project code match this BO's?) is
available for free, no new backend work.

**Explicitly out of scope:** no "link this PO to this BO" action, no
allocation-of-PO step, no new interactive affordance. This stays read-only
context, not a workflow.

**Display decision — separate column, not a toggle.** Two options were
considered:

- *Toggle*, where turning it on filters the `on_order` column itself down
to only project-matched POs — rejected. This makes the row's Outstanding
math depend on a display setting: flip the toggle and the same row's
authoritative Outstanding number changes, because non-matched on-order
stock silently drops out of the calculation. A project-code match is a
*hint*, not proof, and shouldn't be able to move the number the row's
whole netting logic is built on.
- **Separate informational column** (chosen) — `on_order` stays untouched,
feeding Outstanding exactly as it does today. A second column shows "of
that on-order qty, N are same project code" — visible, comparable, never
authoritative. Keeps "what's truly outstanding" and "how confident are we
this incoming stock is meant for this BO" as two distinct questions,
never collapsed into one shifting number.
- No custom show/hide toggle needs to be built for this either —
`@inventreedb/ui` already ships a native column selector
(`TableColumnSelect`, confirmed in source), so hiding the column when it's
just noise is already solved infrastructure.

---

## Part 2: MVP Scope — Bulk BO Generation Across the Tree

> This is the actual point of the plugin. Everything else in this doc is
> either how it renders (Part 3), a natural extension of it (Part 4), or
> deferred detail kept for reference (Part 5).

### The Gap Is Real, and Narrower Than First Assumed

Confirmed directly against source: InvenTree **already has** a way to
create a child Build Order for a required assembly line. In
`BuildLineTable.tsx`'s per-row actions, a "Build Stock" row action (wrench
icon, shown when `canBuild = !consumable && user.hasAddRole(build) &&
part.assembly`) opens the create-Build-Order modal, pre-filled with:

```
{ part: record.part, parent: build.pk, quantity: record.quantity - record.allocated }
```

**But it's single-row only, and scoped to one BO's direct children.**
Confirmed directly against source — this is the exact bulk toolbar
InvenTree's demo server shows above the Required Parts table:

| Icon | Action | What it does |
|---|---|---|
| Wand | Auto Allocate Stock | auto-assigns existing stock to selected lines |
| Cart | Order Parts | opens `OrderPartsWizard` (full detail in Part 5) |
| Green arrow | Allocate Stock | opens a separate modal to assign stock to selected lines |
| Circle-minus | Deallocate Stock | removes existing allocations |
| Checkmark | Consume Stock | marks allocated stock as consumed |

All driven by `table.selectedRecords` — genuine bulk actions across
whatever's checked. **But there's no bulk "Build Stock" action in that
list.** And the table itself only ever shows one build's immediate
required lines — one level, not the whole nested picture.

**This is the actual pain point, precisely:** to build out a multi-level
tree of sub-assemblies today, a user has to: open a BO's Required Parts
table, find an assembly-type line, click "Build Stock" to create one child
BO, then **navigate into that new child BO's own page** and repeat the same
one-row action there for its children, and so on — one level, one row, one
navigation at a time, with no view of the whole nested requirement picture
at any point in the process. (Separately, and not independently verified
against current source: there's a recollection that InvenTree used to have
some flatter view of all child BOs at once that no longer exists — see
Part 3's historical note below, which found a related but not identical
precedent.)

### Confirmed Decision: Checkbox-Select, Matching the Native Bulk Feel

The checkbox-per-row + bulk-toolbar-action pattern from the native Required
Parts table (Part 2's icon table above) is the confirmed direction for BO
generation too — the plugin's tree should carry the same right-side
checkbox on every line and feel like an extension of the existing bulk
Allocate/Buy toolbar, not a separate paradigm.

### Checked and Not Found (In the Wrong Place) — Superseded Below

Originally searched global settings (`BUILDORDER_*` in
`common/setting/system.py`), the New Build Order form's field list
(`useBuildOrderFields`), and backend `build` models/serializers for
`child_build`/`create_child`/`auto_create` patterns — found nothing, and
concluded no such feature existed. **That search missed the right
location.** The actual mechanism isn't a setting or form field — it's a
built-in event-driven *plugin*, found afterward at
`plugin/builtin/events/`. See the correction immediately below for the
real, confirmed mechanism. Kept this note as a reminder that "not found"
claims are only as good as where you looked — the plugin directory wasn't
checked in the first pass.

### Correction: A Fuller Automation Path Exists — But It's Invisible, Not Visible

The above undersells what's already native. Confirmed directly against
source: there's a real, **built-in** (though optional, event-driven)
plugin, `AutoCreateBuildsPlugin` (`autocreatebuilds`,
`plugin/builtin/events/auto_create_builds.py`), which listens for
`BuildEvents.ISSUED` and, when a BO is issued, walks its non-consumable
assembly-type BOM lines and auto-creates a child BO for any with a
deficit, computed as:

```
required_quantity = build_quantity + minimum_stock + allocated_quantity
                     − stock_quantity − in_production_quantity
```

Same assembly-type-with-a-deficit precondition as the Existing/Draft
distinction in Part 1. **One notable divergence worth deciding on
deliberately:** this native formula never nets against on-order POs —
inbound purchase orders don't reduce the deficit at all here, unlike
Part 1's plan to net `on_order` into Outstanding. Worth choosing
explicitly whether this plugin's math should match that native
conservatism or intentionally diverge from it.

New child builds are created `PENDING`, not auto-issued — so on its own,
this plugin doesn't cascade. **But** a second built-in plugin,
`AutoIssueOrdersPlugin` (`autoiissueorders`), runs on a daily schedule and
auto-issues any `PENDING` build whose `target_date` matches today (or is
in the past, only if `ISSUE_BACKDATED_ORDERS` is enabled — off by
default). Child builds inherit their `target_date` directly from the
parent. So with **both** plugins enabled and the timing aligned, the
whole tree genuinely can cascade fully automatically, no human touching
anything — and if the timing doesn't align (child created after that
day's scheduled run, or its inherited date lands in the past without
backdating enabled), it just sits `PENDING` indefinitely.

**This changes what the actual differentiator is, and it's worth stating
precisely rather than assuming the gap above still stands unmodified.**
It isn't "can InvenTree auto-create child BOs across a tree" — it
genuinely can, if both optional event/schedule-driven plugins are
enabled. The real differentiator is **visible vs. invisible**: that native
path is a trust-the-background-job model — no view of the tree, no
review before creation, no chance to choose Build vs. Allocate vs. Buy
per line, timing-dependent cascade. This plugin's actual value is letting
a human **see** the whole flattened tree, the opportunities in it, and
make an informed, selective bulk decision before anything gets created —
not being the only way BOs can get auto-created at all.

### MVP Definition

The plugin's actual, narrow job: **replace that repeated one-row-at-a-time,
one-navigation-at-a-time loop with a single flat view and a single bulk
action.**

1. **A tight list of every descendant sub-assembly requirement, all levels,
one screen.** This is exactly the recursive tree designed in Part 3 below
— the "full computation, one call" traversal, with rollup badges — just
re-framed as the actual point of the plugin rather than one feature among
several.
2. **BO-opportunity identification on that list**, per the Existing/Draft
distinction defined in Part 1 above — an assembly line with no BO yet and
not fully allocated is a candidate.
3. **Checkbox multi-select across the whole flattened tree** — not just
one BO's direct children, but any combination of nodes at any depth.
4. **One bulk "Create Build Orders" action**, modeled directly on the
confirmed `OrderPartsWizard` UX (full breakdown in Part 5): a modal with
one row per selected node (part, quantity, editable), a single confirm
that creates all of them in one go — hitting the same
`part`/`parent`/`quantity` shape the native single-row "Build Stock"
action already uses per line, just orchestrated across many rows and
levels at once instead of one row with a page navigation in between.

### What This Demotes, Not Deletes

Given the native bulk toolbar above already solves Allocate and Buy once
real BOs exist (Order Parts via `OrderPartsWizard`, Allocate Stock via its
own modal), **building bespoke inline per-row Allocate/Buy controls inside
this plugin's tree is duplicating a solved problem**, not filling a gap.
The detailed row-level Allocate/Buy design in Part 5 is being kept as
thinking-work, not deleted — some of it (segmented bar, per-action
confirm, PO-selection flow) may still be worth a v2 — but it's
**deferred, not MVP**. The MVP interaction for those two axes is likely
just: create the BOs in bulk via this plugin, then use InvenTree's own
native bulk toolbar (which already operates on checkbox-selected rows) to
allocate or buy against the results — no reinvention needed.

---

## Part 3: Tree Rendering in InvenTree's Native React Tables

> **Correction (verified directly against source):** an earlier pass at
> this section assumed InvenTree's tables were built on
> `mantine-react-table` (TanStack Table v8), with tree rendering via a
> `subRows` prop and depth-based row indentation. **That was wrong.** The
> actual source — cloned directly from `github.com/inventree/InvenTree` and
> `github.com/inventree/plugin-creator`, plus the published
> `@inventreedb/ui` package pulled via `npm pack` — tells a materially
> different story, corrected below.

### Confirmed Foundation

InvenTree's core table wrapper (`src/frontend/src/components/tables/InvenTreeTable.tsx`,
~1,000 lines) is built on **`mantine-datatable`** (the `icflorescu` package),
not `mantine-react-table` / TanStack. Confirmed directly from its imports:
`DataTable`, `DataTableRowExpansionProps`, `useDataTableColumns`.

**There is no `subRows` / depth-indentation tree pattern anywhere in
InvenTree's own frontend.** Instead, every multi-level display in the app —
including the one directly relevant precedent, the live BOM viewer's
sub-assembly drill-down — uses **recursive composition of separate table
instances**, via `mantine-datatable`'s single-level `rowExpansion` detail-panel
API:

- `rowExpansion.expandable` decides per-row whether a row *can* expand.
- `rowExpansion.content` renders whatever React node should appear when a
row is expanded — and that content can itself be a whole other
`InvenTreeTable`, which in turn defines its own `rowExpansion`, recursing
as deep as the data goes.
- Expansion state is tracked per table instance (`tableState.expandedRecords`
/ `tableState.isRowExpanded(pk)`), not a single global tree-expansion state.

**The direct precedent: `BomTable.tsx` + `BomSubassemblyTable.tsx`.**

- The main `BomTable` gates sub-assembly display behind a user setting
(`SHOW_BOM_SUBASSEMBLY_LEVELS`) — off by default, so recursive drill-down
is opt-in.
- A row is expandable if `record.sub_part_detail?.assembly` is true.
- Expanding a row renders `<BomSubassemblyTable partId={record.sub_part} />`
— a **fresh, independent `InvenTreeTable`** that fires its own API call
scoped to that part's BOM, the moment the row expands.
- That nested table defines the *same* expansion logic again, recursing by
component composition, not by a single table walking a nested data
structure.
- Visually, nesting is **not column-aligned indentation.** Each expanded
level renders as its own `Paper` card, prefixed with a small
`IconCornerLeftUp` icon and wrapped in a flex-grow `Expand` div (which
just makes the nested table fill width — it does *not* add indent
padding). The "this is nested" cue is the card boundary and the
corner-arrow icon, not a padding-per-depth scheme.
- `RowExpansionIcon.tsx` — a small reusable chevron (`IconChevronRight` /
`IconChevronDown`) — is the shared expand/collapse affordance, also used
for unrelated single-level expansions (e.g. `BuildLineTable.tsx` uses the
same mechanism to show a *flat* list of stock allocations per build
line — one level, not a recursive tree).

**Divergence this creates from Part 2's MVP plan:** the native precedent
is **lazy, per-node, and opt-in** — each level's data loads only when a
row expands, behind a settings toggle defaulting to off. Part 2's plan
(full recursive traversal computed server-side, in one call, on panel
load) is a deliberate **departure** from the native BOM viewer, not an
extension of it — defensible, since "see the whole picture without
manually expanding everything" is this plugin's whole point, but worth
being explicit that it means a genuinely different loading model than
anything already proven in InvenTree's own table stack.

### Confirmed: Plugins Get the Real Thing, Not a Reimplementation

Checked by pulling `@inventreedb/ui@1.4.5` via `npm pack` and inspecting its
shipped source directly:

- The plugin-facing `InvenTreeTable` component is a **thin ~40-line proxy**
that calls `context.tables.renderTable(...)` on the plugin context, rather
than shipping its own copy of the table implementation.
- `context.tables.renderTable` is backed by the **exact same** ~1,000-line
`InvenTreeTable` the host app itself uses — same `mantine-datatable`
engine, same `rowExpansion` mechanics.
- `DataTableRowExpansionProps` is present in `@inventreedb/ui`'s shipped
types (`rowExpansion?: DataTableRowExpansionProps<T>`), confirming the
prop reaches plugins rather than being stripped at the boundary.
- `mantine-datatable` is a listed dependency of `@inventreedb/ui`
(`"mantine-datatable": "^9.2.0"`), separate from the short externalized-libs
list the plugin build excludes from bundling (`react`, `react-dom`,
`@mantine/core`, `@mantine/notifications`, lingui) — the plugin doesn't
need its own tree/table library; it gets the host's real rendering.

**Net effect:** this plugin can use `rowExpansion` exactly the way
`BomSubassemblyTable` does — nested `InvenTreeTable` instances via
`context.tables.renderTable`, recursing per node — as a fully supported
native pattern. The open question isn't "can we get a tree at all," it's
"do we adopt the native lazy-per-node loading model, or build eager loading
on top of the same expansion mechanism."

### Design Implication: Eager Data, Lazy Rendering

The path that keeps Part 2's "full computation up front" goal while still
reusing the native `rowExpansion` pattern:

- **Fetch eagerly, render lazily.** On panel load, one server-side call
computes the full tree and returns it as a single nested structure — but
rendering still uses `rowExpansion` / `isRowExpanded` per row, with
`content` reading from the already-fetched data for that branch rather
than firing a fresh API call per expand. Keeps "confidence from a
computed rollup badge, not from manually expanding everything," while
visually behaving like the native nested-card pattern.
- This means **not** literally reusing `BomSubassemblyTable`'s per-expand
refetch — the content renderer needs to slice into already-loaded data,
while keeping the same `rowExpansion` plumbing.
- **Rollup badges** render on the collapsed row itself, computed
server-side during that same eager traversal — available immediately,
independent of whether a row's ever been expanded.

### LCA-Merged Nodes in This Model

Proposed handling, adapted to the confirmed mechanism:

- The LCA node renders as a **real, expandable row** only at its canonical
position.
- Every other branch that also requires it renders a **non-expandable
reference row** — no chevron, no `rowExpansion` wired up, just "→ see
[Part] above, required 5 of 12" with a link to the canonical row —
rather than a second independent nested-table instance holding its own
separate expansion/staged-input state.

**Open question to add to the running list:** exact visual treatment for a
reference row vs. a real row — needs to read as clearly non-interactive.

### Indentation, Revisited

**Historical note, confirmed against source (pre-1.0, `0.9.0` tag,
pre-React frontend):** InvenTree's BOM viewer used to work this second way.
`templates/js/translated/bom.js` used a `bootstrap-table-treegrid` plugin —
one single flat table (`treeEnable: true`, `parentIdField: 'parentId'`) —
where expanding a row called `requestSubItems()`, fetched that node's
direct children, and **appended them into the same table**
(`table.bootstrapTable('append', response)`), rather than opening a
separate nested table instance the way current `BomSubassemblyTable` does.
Still lazy (one level per fetch, same as today), but architecturally one
continuous indented table rather than nested cards — which is likely the
"used to have this" recollection from Part 2 above. This means option 2
below isn't really a stylistic departure from InvenTree's house style so
much as a return to an earlier InvenTree pattern that the current React
frontend moved away from.

Since native precedent doesn't use padding-per-depth at all, "indentation"
is really a choice between two real options:

1. **Match native style** — nested `Paper` cards per level, corner-arrow
icon, no aligned columns. Consistent with the rest of the app, but harder
to scan a 6-level-deep tree at a glance since data columns aren't aligned
across nesting levels.
2. **Depart from native style** — build actual column-aligned indentation
(padding scaled to depth, data columns fixed to the right) inside each
nested table's row renderer — a deliberate departure, since nothing in
the native component library does this, but more scannable at depth.

This is a real design decision to make explicitly, not default into — worth
mocking both, since it's a UX call, not a technical constraint (both are
buildable on `rowExpansion`).

### To-Verify List (add to parent doc's Open Questions)

- [x] ~~Does `@inventreedb/ui` expose a pre-built tree/expanding table
component~~ — confirmed: plugins get the real `InvenTreeTable` /
`mantine-datatable` engine via `context.tables.renderTable`.
- [x] ~~Is InvenTree built on `mantine-react-table`~~ — confirmed no; it's
`mantine-datatable`, and tree display is recursive component composition,
not `subRows`/depth indentation.
- [ ] Decide: match native nested-card visual style vs. build genuine
column-aligned depth indentation as a deliberate departure.
- [ ] Reference-row visual treatment for LCA branches.
- [ ] Confirm eager-fetch-lazy-render approach doesn't fight any assumptions
baked into `mantine-datatable`'s `rowExpansion` about content being
computed fresh per expand.
- [ ] Spike: performance of many simultaneously-expanded nested
`InvenTreeTable` instances (each a real component instance, not a
virtualized row) at 50+ node scale.
- [x] ~~Buy's PO-selection UI: existing-open-PO picker vs. "+ create new
PO" inline, and does supplier or PO get chosen first~~ — confirmed via
`OrderPartsWizard.tsx`: supplier part is chosen first, Purchase Order
picker stays disabled until then and is filtered to that supplier's open
orders; both have an inline "+" to create new. Not directly reusable
(not exported to plugins) but the flow order and filter logic are now a
confirmed native pattern to replicate.

---

## Part 4: This Plugin as the BO Status Viewer / Plugin 4 Template

The parent doc already notes Plugin 4 (BO Hierarchy Display) is deferred,
on the bet that a read-only "existing-BOs-only" mode of this tree would
cover it without a separate plugin. Getting the tree-rendering foundation
right in Part 3 is what makes that bet pay off:

- The same nested `InvenTreeTable`/`rowExpansion` tree, same indentation
model, same rollup badges, same LCA-placement logic all apply whether
every node is Draft-and-editable or all nodes are Existing-and-read-only.
- A read-only mode is then just a **display flag**, not a separate
component: hide the Build/Allocate/Buy controls and Commit Decision
button, keep everything else (badges, indentation, rollups, LCA
handling, expand/collapse) identical.
- If this holds, the tree-rendering work here isn't just Part 2's
foundation — it's the reusable template for any future BO-hierarchy
view InvenTree needs, which raises the bar on getting indentation,
LCA display, and rollup badges right the first time rather than as a
v1.5 fix-up.

**Practical implication:** build the read-only/Existing-only toggle early
(even before full Allocate/Buy polish, which is deferred per Part 2) as a
way to validate the tree rendering foundation in isolation. Note this
read-only toggle is a variant *on top of* the Part 2 MVP (the mixed
Draft+Existing flat tree with bulk-select), not a replacement for it — the
flat tree itself, showing both statuses at once, is the actual MVP
deliverable; a pure read-only mode is a cheap bonus once that's built.

**Open note for further consideration, not yet resolved:** the shared
component assumption above may only hold for *visual rendering*, not fetch
strategy. Part 2's MVP wants eager, one-call, whole-tree fetching so
rollup badges and bulk-select work without manual expansion — right for a
bounded, mostly-Draft opportunity tree. A pure status-viewer over an
**already fully-built-out** tree could be much larger in practice (months
of completed nested builds), where eager-fetch-everything may be the wrong
default. The pre-1.0 treegrid precedent in Part 3 was lazy either way
(expand-to-fetch, one level at a time, appended into the same flat table) —
worth deciding later whether read-only mode should inherit that lazy
pattern instead of the MVP's eager one, even while reusing the same
flat-indented-table rendering. I.e.: same visual component, possibly
different fetch strategy, still an open fork rather than "hide the Draft
rows and done."

---

## Part 5: Row-Level Interaction Model (Deferred — Not MVP)

> Per Part 2: Allocate and Buy are already solved natively via InvenTree's
> own bulk toolbar once real BOs exist. The design below is kept as a
> v2/optional reference, not something to build for the MVP.

### Why Build, Allocate, and Buy Don't Deserve the Same UI Weight

The three Commit Decision actions differ in how much of a genuine *decision*
they require, and the row design should reflect that rather than treating
all three identically:

- **Build** — a pure quantity. The write is `{ part, parent, quantity }`,
nothing else to choose. Doesn't need a modal's real estate.
- **Allocate** — requires picking a specific `stock_item` (batch/lot), not
just a number. A real choice with consequences (which batch gets consumed).
- **Buy** — requires picking a supplier part (defaulted, overridable), a
quantity with pack-quantity rounding applied, **and which PO the line
gets added to.** Confirmed against source: InvenTree's native
`PurchaseOrderLineItemTable` always assumes it's rendered inside a
specific PO's page — `order` is a fixed field override, not a field the
user picks there — so that form can't be reused as-is.

There is, however, a real native precedent for exactly this three-part
decision: **`OrderPartsWizard.tsx`**, triggered from `BuildLineTable`'s
"Order Parts" bulk action (and from a single line's right-click "buy"
action). Per row it shows: a Supplier Part picker (filtered to the part,
autofilled to the primary supplier part), a Purchase Order picker
(**disabled until a supplier part is chosen**, then filtered to
`supplier: <that supplier>, outstanding: true`), and a Quantity field —
confirming supplier-first, PO-second is the native flow order, not an
arbitrary choice. Both pickers have an inline "+" to create a new
supplier part / new PO on the spot without leaving the row.

**Checked and confirmed not reusable as-is:** `OrderPartsWizard` is not
exported via `@inventreedb/ui` — its full export list has no wizard or
form-field-level component at that layer. This plugin can't import the
wizard directly; it can only rebuild equivalent UX using the primitives
it does have access to (`editApiForm`/`forms.create` with `'related
field'`-type inputs, replicating the same supplier→PO filter chain).

This asymmetry is the basis for the row design below.

### Row Layout

```
[Draft] Part Name                    Required: 20    Outstanding: 12
  ☑ Build 12   [✎]        [Allocate ▾]        [Buy ▾]
                                                       [Commit Decision]
```

- **Build checkbox, checked by default** at the node's current outstanding
qty. One click stages a Build at that predetermined quantity — the fast
path for "just build whatever's left."
- **Edit affordance (✎)** next to the checkbox flips the number into an
editable inline field, for the case where the user wants to build less
than the full outstanding because they're staging Allocate/Buy for the
rest.
- **Allocate ▾** and **Buy ▾** — expand inline (see "Modal vs. Inline"
below), rather than popping a modal, so tree context above/below the row
stays visible.
- **Commit Decision** — single button, fires whatever's staged across all
three (checked/edited Build qty + anything staged in the expanded
Allocate/Buy sections) as one write.

> **Note added later in discussion:** this checkbox + single Commit
> Decision button design was subsequently reconsidered — see the "Later
> Revision" note at the end of this Part 5. Kept here in its original form
> since the reasoning trail (why inline, why live recalculation) still
> applies to the revised design.

### Live Recalculation, Not Static Fields

The Build checkbox's number is not fixed at "full outstanding" — it's:

```
Build qty (default) = Outstanding − staged Allocate qty − staged Buy qty
```

recalculated live as the user works the Allocate/Buy sections, still fully
overridable by hand via the edit affordance. This prevents the row from
letting a user double-count the same outstanding units across actions, and
incidentally addresses one of the parent doc's open questions (what happens
when allocate + build + buy don't sum to the full outstanding) — a
live-recalculating default keeps the three roughly reconciled unless the
user deliberately overrides the number down.

### Modal vs. Inline — Resolved Direction

Decision: **inline over modal**, using the SDK's `editApiForm` (new in
1.4.2) rather than `forms.create` modals, for both Allocate and Buy — not
just Build.

Rationale:

- `editApiForm` renders the *same* underlying form (stock item picker,
supplier part selector, pack-qty rounding) as a React node inline in the
row, rather than as a separate overlay. The form's fields don't change —
only where it renders.
- Keeping the tree visible while deciding matters here specifically because
LCA-merged nodes require comparing sibling-branch quantities *while*
deciding how much to allocate — a modal would hide that context.
- One consistent interaction pattern across all three actions (expand a
section of the row, not "checkbox for one, modal for the other two") is
less for a user to learn.

**Known cost, accepted for now:** dynamic row height. A row expanding to
show a stock-batch table pushes every row below it down — more layout churn
in a deep tree than a modal would cause, since a modal floats above the
tree without disturbing row positions. Deep indentation (6+ levels, per the
large-tree note in the parent doc) also leaves less horizontal room for a
stock-batch table or supplier dropdown to breathe.

**Open sub-question, not yet resolved:** whether to cap how many rows can
have Allocate/Buy expanded simultaneously, to avoid visual noise when a
user is comparing two branches side by side.

### Later Revision: Checkbox Dropped, Per-Action Confirm Instead

After further discussion, the checkbox + single Commit Decision button
above was reconsidered:

- **A checkbox is the wrong control for Build.** It implies toggling
whether Build happens at all, when in the common case "build the full
outstanding qty" is just what happens if the user does nothing — a
checkbox falsely elevates inaction to the status of a choice.
- **Revised model:** Build becomes a **plain-text resting state** — "Build
12" with no widget — that live-shrinks as Allocate/Buy are staged, plus a
small edit affordance for the rare override case. Never needs a commit
step of its own, since doing nothing was always valid.
- **Allocate and Buy become fully independent actions**, each with its own
scoped "Confirm" button, rather than being bundled under one shared
Commit Decision button. This also resolves a separate concern: bundling a
one-click Build with two genuinely multi-field decisions (Allocate,
Buy) under a single button/label treated them as more symmetric than they
are.
- **A read-only segmented bar** (feedback only, not an input) shows the
Build/Allocate/Buy split of the outstanding qty visually — considered as
a draggable input control and deliberately rejected as too heavy for the
default/resting state of a dense tree row; kept as passive feedback only.
- **Open question this reopens:** with no single atomic commit, when does
a row flip from Draft to Existing? Possibly needs a third state ("2 of 3
actions done") rather than staying strictly binary — not yet resolved.

This revision was prototyped in an interactive mockup (`bo-tree-spike.jsx`)
alongside both indentation styles from the "Indentation, Revisited" section
in Part 3 — worth checking that file for the current state of this
interaction model rather than the checkbox version described above it.

---

## Superseded / Related Documents

- `PLUGIN-TRILOGY.md` — parent vision doc, Plugin 2 section
- `BUILD-ORDER-GENERATOR-UX.md` — parent flow spec this doc extends
