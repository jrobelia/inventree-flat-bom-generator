# Build Order Generator — UX & Flow Spec

> **Status:** Vision / ideas phase — companion to PLUGIN-TRILOGY.md, Plugin 2
> **Last Updated:** July 17, 2026

Detailed flow and business-logic thinking for Plugin 2 (Build Order Generator),
captured ahead of implementation. This doc assumes the shared conventions and
open questions already listed in `PLUGIN-TRILOGY.md` and expands on them.

Technical claims about InvenTree's frontend plugin API and Build/Purchase
Order source are verified against `reference/inventree-source` at stable
`1.4.2` and `plugin-creator` at `1.20.0` (both bumped July 17, 2026).

---

## The Problem

InvenTree only lets you create one child Build Order at a time, and there is
no view that shows the full set of child BOs a parent BO needs — either
already created or still outstanding. Users can't see the whole picture, or
act on it in one place.

## Where It Lives

**BO detail page**, not the Part page. A parent Build Order already has a
defined build quantity and project code, and only makes sense to plan a
sub-assembly tree against once it exists. A Part-page version would require
guessing a hypothetical quantity, duplicating what the BO already encodes.
Shown as a new panel, e.g. "Sub-Assembly Requirements."

**Every node in this tree is an assembly** — something with its own BOM that
could be built via a Build Order. Leaf/purchased parts (fasteners, raw
stock, off-the-shelf components) never become nodes here; sourcing those is
Plugin 3's job (Purchase Order Generator), which works off the full
flattened leaf-part list. That's why the Buy action on a node (see Making a
Decision, below) is the exception, not the rule: it only applies when an
assembly-level node itself happens to have a default supplier (e.g. a
sub-assembly bought complete from an outside vendor rather than built
in-house) — most nodes will only ever show Allocate and Build.

Three different "orders" show up repeatedly through the rest of this doc, so
it's worth naming them once up front instead of letting them blur together:
**BO creation order** (top-down, forced by the database — covered under Making
a Decision, since that's the moment it actually bites), **BO execution order**
(bottom-up, a plain fact of manufacturing — leaf sub-assemblies get built and
completed first, because a parent build needs their finished stock as an
input before it can be completed itself), and **BO review order** (entirely the
user's choice — covered under Reviewing the Tree).

---

## Opening the Panel: The Tree You See

### Existing vs. Draft Nodes

This distinction resolves several open questions at once and should drive the
UI directly. (Named "Existing" / "Draft" rather than "Actual" / "Proposed" —
mirrors language InvenTree already uses elsewhere, e.g. draft POs.)

- **Existing nodes** — a child Build Order already exists for this
sub-assembly. Required-parts data is pulled from that BO's real
`BuildLine`s (authoritative). Rendered as a linked, status-badged row;
traversal recurses into its real children.
- **Draft nodes** — no child BO exists yet. Requirement is computed
hypothetically from the part's BOM × cascaded quantity. Rendered as an
editable row with separate allocate/build/buy quantity fields where
applicable (see Commit Decision model below); nothing is written to
InvenTree until the user commits.

Every node in the tree is one or the other. This tells the user at a glance
what's already locked in vs. still just a plan, and gives a clean model for
how Draft nodes get promoted to Existing once a real decision is committed
(see Commit Decision model below).

**No Save Draft.** Considered and dropped — persisting in-progress Draft
edits in our own backend state reintroduces the exact staleness risk the
"transitory" principle below exists to avoid (a saved draft's numbers can
silently drift from live reality between visits). The Commit Decision model
solves the underlying problem (losing work to a refresh) a different way: by
writing each decision into real InvenTree data the moment it's made, so
there's never a meaningful window where a decision exists only in our
plugin's memory.

### Full Computation, Collapsible Display

Computation and disclosure are two separate decisions, not one tradeoff:

- **Computation:** full recursive traversal happens server-side, in one call,
on panel load — not lazily per-node as the user expands. This guarantees a
complete picture exists before the user looks at anything.
- **Disclosure:** the tree can still render collapsed by default. Collapsed
nodes show a rollup summary badge computed from their descendants (e.g. "6
sub-assemblies below · 4 need building · 2 covered"), so confidence comes
from the badge, not from manually expanding every branch.

**Transitory, not persisted.** Recompute fresh on every panel open (plus a
manual refresh action). Nothing is cached to disk in v1 — BO statuses and
stock levels change too often for a stale cached tree to be trustworthy.
Possible v2 optimization: cache the BOM *structure* (rarely changes)
separately from *live state* (BOs/stock, always fresh).

**Large-tree honesty:** if a tree is too large for full eager computation
(50+ assemblies, per the trilogy doc's stated concern), the UI must say so
explicitly (e.g. "stopped at depth 6, expand to compute further") rather than
silently truncating. Silent gaps would undermine the entire point of the
plugin — trustworthy completeness.

---

## Reviewing the Tree

### Review Order Is the User's Choice

The user can review and decide on nodes in whatever order makes sense to
them — e.g. leaf-first, since that's often where the more granular
build/buy/allocate decisions live. This is independent of how the underlying
records actually get created in the database (see the creation-order
constraint under Making a Decision, next); the tool has to accommodate free
review order while still enforcing correct creation order underneath.

### Lowest Common Ancestor (LCA) Placement

When the same sub-assembly appears in multiple branches, show it **once**, at
its LCA position, with a merged quantity and a badge like "also required by:
[Branch A, Branch B]" — expandable to see the per-branch breakdown. Showing
it twice with separate quantities would mislead the user into building it
twice.

**Combine by default; split as override.** Reducing the number of Build
Orders a user has to manage is a core goal of this plugin, not just an
allocation nicety — InvenTree's stock allocation is manual regardless of
which BO produced the stock (see Netting, below), so there is no functional
allocation cost to combining. The real tradeoff is production scheduling (see
due-date handling below), not efficiency, so combining should be the default
behavior:

- **Combine into single build order** (default) — one Draft BO for the full
merged quantity.
- **Split per branch** (override, available per node or as a global setting)
— separate Draft BOs per branch, for cases where a user has a specific
reason to keep them distinct (e.g. materially different due dates, or a
process reason to keep runs separate).

**Parent assignment for combined nodes.** A combined node's real BO can't
honestly be parented to any single consuming branch (e.g. if part C is
required by both B and D, it can't be a child of B *or* D specifically) — it
must be parented to their common ancestor (e.g. the top-level build, A). This
means the tree's *display* nesting (C shown under both the B and D branches
for readability) will diverge from the *actual* InvenTree parent link (C → A)
once created. This divergence must be called out explicitly in the UI (e.g.
a note on the merged node: "will be created as a child of [A], not [B] or
[D]") so it isn't confusing later when someone opens C's BO page directly and
sees it parented higher up than expected.

**Due-date conflicts.** A combined BO has a single target completion date,
but its consuming branches may have different need-by dates. Default the
combined BO's target date to the **earliest** of the branch need-dates (build
to the tightest constraint), and surface both branch dates side-by-side on
the merged node so the user sees the conflict before confirming, rather than
it being resolved silently. User can override the date directly on the node.

**Traceability of combined builds.** Combining branches into one BO does not
put serial/lot traceability at risk: InvenTree already tracks genealogy for
serialized/tracked stock independent of which BO produced it (a
`StockItem`'s `belongs_to` / "Installed In" link records what it's installed
into regardless of Build Order boundaries). So combine-by-default doesn't
need a serialization guard rail. For human readability, though, the combined
BO can still carry a short note listing which branches it was made for (e.g.
"Also required by: Branch A x5, Branch B x3") — a convenience for whoever's
reading the BO later, not a traceability requirement.

### Netting: What Reduces "Outstanding to Build"

Expose the toggles below as visible controls, consistent with Flat BOM
Generator's existing pattern (not hidden settings). Full stack, applied per
node:

```
Required
− Allocated stock (already assigned to this node's need)
− Unallocated stock on hand           [if "Net against stock" toggle on]
− Incoming qty on open Purchase Orders [if node is purchasable]
− Already-building (remaining output of Existing child BOs)
= Outstanding
```

- **Allocated stock always reduces outstanding**, regardless of the netting
toggle — it's not debatable "available" stock, it's already committed to
this exact need.
- **Net against stock** (on/off) — whether unallocated on-hand stock counts.
- **Which allocations/stock count** — all / this BO tree only / none.
- **Open POs** — for purchasable sub-assemblies, subtract incoming quantity
from open Purchase Orders so the plugin doesn't propose building something
already inbound. Scoped the same way as allocations (project-scoped by
default, per the cross-cutting concern in `PLUGIN-TRILOGY.md`).

Default: net against unallocated stock, scoped to this BO tree only, open
POs scoped to this project — least likely to surprise a user, while staying
overridable.

**Build / Allocate / Buy, together.** For any purchasable sub-assembly (has
a default supplier, not build-only), a node's outstanding qty can be split
across all three at once — some allocated from stock, some built, some
bought — rather than a single binary choice. This is handled by the Commit
Decision model, next, which writes each portion into real InvenTree data
(allocation, child BO, PO line) in a single action.

---

## Making a Decision: Commit Decision

This is the core interaction model, replacing any notion of a
batch-at-the-end "Create" button.

**Problem it solves:** a single decision on one node is often not a single
action. Example — a node requires 20, there are 10 in stock, 2 already on
order: the user might decide to allocate the 10, build 3 more, and buy 5
more. If only the "build 3" part gets captured (as a BO) and the rest lives
in the user's head or a note, a refresh or a day's gap loses two-thirds of
the decision — and re-deriving it costs real engineering time.

**Solution:** each node has a **Commit Decision** action that, in one click,
writes every part of the decision into real InvenTree data simultaneously.

### Creation Order Is Forced

A child BO's `parent` field is a foreign key to an already-existing Build
record: to create a node's BO with `parent = [ancestor]`, that ancestor must
already exist with a real ID. This isn't a workflow preference — it's a hard
technical dependency. Any node below the top level requires its immediate
parent to be created first.

Because review order is free (see above) but creation order isn't, the tool
has to reconcile the two: if a user reviews and commits a decision on a deep
node before its ancestor Draft nodes have been created, the tool auto-creates
any missing ancestors first (using their currently-set Draft qty/settings)
before creating the node itself — surfaced as a brief confirmation, e.g.
"This will also create: B (parent), since C requires it to exist first." The
user keeps reviewing in whatever order feels natural; the tool enforces
correct DB order underneath.

### The Three Actions

1. **Allocate** — any qty the user assigns from existing stock is allocated
immediately against the parent's real BuildLine for this part. Always
actionable, since (per the creation-order constraint above) the parent BO
already exists by the time this node is being reviewed.

> **InvenTree internals:** no generic "allocate to build line" action exists
> in the plugin SDK's fixed `stockActions` set, so this means our own simple
> form via the SDK's generic `forms.create`, pointed directly at the
> `build_item` (allocation) endpoint. Verified against InvenTree 1.4.2
> source: the internal Allocate action actually posts to a bulk action
> endpoint (`build/:id/allocate/`) with a multi-row table field, built for
> allocating many lines at once. For a single-node, single-row Commit
> Decision, creating one `BuildItem` directly against `build/item/`
> (`build_item_list`) is the simpler match — a plain create, not a
> reimplementation of the bulk table form. Note a real `BuildItem` also
> requires picking a specific source `stock_item`, not just a quantity,
> since allocation is always against a particular stock record/batch.

2. **Build** — any qty the user assigns to build creates (or tops up) the
node's real child BO, per the usual Draft → Existing conversion.

> **InvenTree internals:** implemented via the SDK's generic `forms.create`,
> pointed at `build_order_list`, pre-filled with `{ part, parent, quantity }`
> — the same pre-fill pattern InvenTree's own core UI uses internally, just
> via the public form-modal API rather than the internal one.

3. **Buy** — the rare case: an assembly-level node that itself has a default
supplier (e.g. a sub-assembly bought complete from an outside vendor rather
than built in-house). Any qty the user assigns to purchase is written as a
real PO line tagged with the parent build's **project code**. This is
explicitly the exception, not the rule — most nodes are build-only and will
never show a Buy option; general leaf-part purchasing is Plugin 3's job,
not this plugin's.

> **InvenTree internals:** implemented via the SDK's generic `forms.create`,
> pointed at the purchase-order-line-item endpoint, pre-filled with the
> node's part and quantity, plus a **supplier part** selector defaulting to
> the part's default supplier part (overridable — worth exposing as a
> dropdown directly in the Buy overlay rather than assuming). If the chosen
> supplier part has a `pack_quantity` set (a real field on `SupplierPart`,
> `company/models.py`), round the suggested quantity up to a whole pack
> rather than proposing an unbuyable fractional-of-a-pack amount. Assemblies
> typically don't carry pack quantities the way leaf/commodity parts do, so
> this will rarely trigger here — but it costs nothing to support, and it's
> the same logic Plugin 3 will need for leaf parts, so building it here
> primes that work. Verified against InvenTree 1.4.2 source: `project_code`
> is a genuine field directly on PO (and SO) line items
> (`AbstractLineItemSerializer.line_fields` in the backend serializer,
> surfaced in the frontend's `usePurchaseOrderLineItemFields`) — this is a
> real, settable field on `order/po-line/`, not something that has to be set
> one level up on the parent Purchase Order. (This field did not exist on PO
> line items in the older 1.1.7 baseline this doc was first written against
> — confirmed added sometime before 1.4.2.)

> **InvenTree internals — precedent and plugin boundary:** confirmed directly
> in the current source (`src/tables/build/BuildLineTable.tsx`): every
> required-parts line on the existing Build detail page already has
> **Allocate Stock**, **Order Stock** (Buy — via the shared
> `OrderPartsWizard`), and **Build Stock** (Build — via a generic
> create-Build-Order modal) actions, each pre-filled with that line's part
> and outstanding quantity. Build/Buy/Allocate as three parallel per-line
> actions is proven, native, currently-live InvenTree UX, not something new
> we're inventing — it's been continuously available since the pre-v1
> (legacy Django UI) version, just per-line, never something we're reviving
> from a gap.
>
> The catch: the specific components those actions use internally
> (`OrderPartsWizard`, `useAllocateStockToBuildForm`, the internal
> build-order create modal) live in the app's internal `src/` source tree,
> **not** in `@inventreedb/ui`, the actual published package plugins build
> against. That package's plugin context (`InvenTreePluginContext`) only
> exposes a generic `forms.create/edit/delete/bulkEdit` (any endpoint,
> standard styling) and a fixed `stockActions` set — not these specific rich
> components. So our plugin can't literally reuse `OrderPartsWizard`'s
> multi-part/supplier-picker wizard or the specialized multi-row allocation
> table; it gets the same underlying data/endpoints via a plainer generic
> form instead. Still native-styled and functionally correct, just less
> polished than the internal versions.

What's still genuinely missing from InvenTree today — and the entire reason
this plugin is worth building — is **visibility**: no tree, no cross-level
view, no rollup of what's still outstanding across the whole parent BO, no
LCA merging for reused sub-assemblies. The per-line action primitives were
never the problem; the missing picture always was.

**Optional future enhancement:** if the plain generic forms feel too bare
once this is built, we could build our own bespoke modals modeled on
`OrderPartsWizard` and the allocation table (same UX ideas, our own
components, since we can't import theirs) — supplier-part picking, batch
part selection, etc. Worth treating as a v2 polish pass rather than a v1
blocker; the generic SDK forms are enough to make Commit Decision fully
functional on day one.

**Net effect:** Allocate, Build, and Buy are all achievable through the
plugin SDK's generic form-modal capability, pre-filled the same way
InvenTree's own internal UI does it — just via plainer, non-specialized
modals rather than the rich internal components, unless we build our own
enhanced versions later.

> **InvenTree internals — inline forms (new in 1.4.2):** the plugin context's
> `forms` object now also exposes `editApiForm`, which renders a form
> directly as a React node rather than only as a modal trigger
> (`forms.create`/`forms.edit` return a modal-opener; `editApiForm` returns
> the form itself). This didn't exist in the 1.1.7 baseline this doc
> originally reasoned from. It's worth considering for v1, not just as a v2
> polish item: it would let each Draft node render its allocate/build/buy
> quantity fields directly inline in the tree row, closer to the "editable
> row with separate...quantity fields" vision described above, instead of
> Commit Decision always popping three separate modals.

Quantity already on order (informational only, already netted into
Outstanding) requires no action.

**What stays exposed to a refresh:** only whatever's typed into the node's
input fields but not yet committed — seconds of risk per node, not a whole
review session. Nothing of ours is ever the sole record of a decision.

### Bulk Commit (Future Refinement)

Per-node Commit Decision is right for a considered decision, but for a large
tree (50+ assemblies, per the large-tree honesty note above) clicking
through every node individually doesn't scale. Planned addition: a **bulk
commit** action scoped to a subtree — e.g. "Build everything outstanding,
net of stock, below this node" — that runs the same per-node Commit Decision
write path (Allocate/Build/Buy) across every Draft node at once, using each
node's already-computed netting result rather than prompting per node.

This is genuinely complicated to get right in one pass — it has to interact
correctly with LCA-merged nodes (a bulk run shouldn't double-commit a
combined node reached via two branches), auto-created ancestors (a bulk run
across a deep subtree may need to create several ancestor levels in one go,
not just one), and due-date conflicts on combined nodes (no user in the loop
to review the earliest-date default before it's applied). Expect this to
ship as a coarse first version — most likely "build everything outstanding,
no partial allocate/buy splits" — with per-node Commit Decision remaining
available for exceptions, and refine the bulk behavior across later
versions rather than fully specifying it now.

---

## After You Commit

**Auto-recompute:** after any Commit Decision, the tree recomputes in place
(no full page reload needed) so the committed node immediately reflects its
new state. A manual full refresh remains available as a fallback.

**Re-running after partial progress:** the panel always reflects live state
rather than requiring an explicit "resync." Existing child BOs and
allocations reduce "outstanding" automatically; previously committed nodes
simply render as Existing. The user only ever sees fresh Draft state for
whatever's still genuinely outstanding.

This applies to combined (LCA) nodes too: if demand increases later (e.g.
parent build qty changes), a subsequent Commit Decision on that node should
top up the **existing combined BO** rather than creating a second separate
one for the same part.

---

## Where This Plugin Stops

### Not Doing (Yet): Critical Path / Lead-Time Analysis

Surfacing the longest lead-time path through a tree (so a buried 12-week
purchased sub-assembly shows up as the real threat to a ship date, not just
an "outstanding" quantity) is out of scope for v1. InvenTree doesn't
currently surface the data needed: `SupplierPart` has a `lead_time` field in
the model source, but it's commented out and unused (`company/models.py`)
— there's no real lead-time value anywhere to compute a critical path from
today.

Worth flagging as a genuinely promising future direction, though, not just a
"someday if upstream adds it" wish: the field already exists in the model,
just dormant — turning it on is a re-enable (migration + serializer/form
exposure on `SupplierPart`), not a request for InvenTree to invent new
tracking from scratch. If it does get re-enabled (by us upstream, or by
InvenTree itself), the tree traversal this plugin already has to do (walking
every branch to compute quantities) is the natural place to also walk
lead times and surface a "longest path" rollup per node — most of the
plumbing would already exist. Revisit once `lead_time` is live; not worth
building our own parallel lead-time data just to get there sooner.

### Boundary With Plugin 3 (Purchase Order Generator)

Writing PO lines directly for the Buy action raises the question of overlap
with Plugin 3. They're not doing the same job:

- **Plugin 2's Buy action** — a single, in-the-moment, ad-hoc purchase
decision made while reviewing one node in the tree. One part, one quantity,
right now, via a generic pre-filled form.
- **Plugin 3** — a bulk, end-of-review sweep across everything still
outstanding across the whole tree (or Flat BOM's shortfall list), grouped by
supplier, matched to project codes, optimized for fewer total POs.

The one place they need to stay in sync: **Plugin 3 must see what Plugin 2
already bought ad-hoc**, so it doesn't re-propose a PO line for something
already committed mid-review. Since Commit Decision writes real PO lines
(not shadow state), this is automatic as long as Plugin 3's shortfall
calculation reads live open POs the same way Plugin 2's netting stack
already does — no special coordination code needed between the two plugins,
just both consistently reading live InvenTree data.

### Relationship to Plugin 4 (BO Hierarchy Display)

Deferred, per PLUGIN-TRILOGY.md. If this tree component is solid, an existing-BOs-only
read-only mode toggle should cover Plugin 4's use case without a separate
plugin.

---

## Open Questions (Running List)

### Tree / Data Model
- [ ] Exact visual treatment for Existing vs. Draft nodes (badge language, color)
- [ ] Rollup badge content — which stats matter most at a glance?

### LCA
- [x] Confirm no manual restructuring in v1; revisit if users request it
- [x] Combine vs. split default — resolved: combine by default, split as override
- [ ] Global setting vs. purely per-node override for combine/split — need both, or just one?
- [ ] UI treatment for the display-tree vs. actual-parent divergence on combined nodes
- [x] Traceability risk for serialized/tracked parts in combined builds —
resolved: not an issue, InvenTree tracks installed-item genealogy
(`StockItem.belongs_to`) independent of which BO produced the stock; a
human-readable note on the combined BO listing consuming branches is a
nice-to-have, not a requirement.

### Stock / Allocation / Purchasing
- [ ] Confirm default toggle states with real users before locking in
- [ ] Open PO scoping: is "this project" reliably queryable/performant via InvenTree's API?
- [ ] Build/Buy: does allocating Buy qty on a node need to also suppress its own
sub-tree (since a bought assembly's internal sub-assemblies are moot)?
- [ ] Buy overlay: what happens when a node's part has no default supplier
part at all — block Buy, or fall back to a plain supplier-less PO line the
user fills in later?

### Commit Decision Model
- [ ] What if allocate + build + buy quantities entered don't sum to the full
outstanding amount — block commit, warn, or allow partial commits freely?
- [x] Confirmed: `BuildLineTable.tsx`'s native Allocate/Order/Build actions
use internal-only components (`OrderPartsWizard`,
`useAllocateStockToBuildForm`, internal build-order modal) that live outside
`@inventreedb/ui` — not directly reusable by plugins. Our version uses the
plugin SDK's generic `forms.create` against the same underlying endpoints
instead (`build_order_list`, PO line-item endpoint, `build_item`).
- [x] Confirmed (InvenTree 1.4.2 source): allocation for a single Commit
Decision row should target `build_item_list` (`build/item/`) directly —
the internal Allocate action's `build/:id/allocate/` endpoint is a bulk,
multi-row action built for a different UI shape, not something a
single-row generic form needs to replicate. Still open: exact field/
permission requirements for a `build_item_list` create (e.g. required
`stock_item` selection, build role permissions).
- [ ] Decide whether v1 ships with plain generic forms for all three actions,
or invests early in a bespoke Buy/Build wizard modeled on `OrderPartsWizard`
(noted as an optional v2 enhancement — see Commit Decision Model), or uses
the newer `editApiForm` inline-form capability instead of modals for some/
all of the three actions
- [ ] If a Commit Decision auto-creates missing ancestor nodes, how much
confirmation detail does the user need before that cascades silently?
- [ ] Undo/reversal: if a user commits and immediately realizes it's wrong,
what's the correction path (edit the resulting BO/PO/allocation directly,
since our plugin doesn't own that data anymore once committed)?
- [ ] Bulk Commit: exact behavior when a subtree includes LCA-merged nodes
reached via multiple branches — commit once, or skip and flag for
individual review?
- [ ] Bulk Commit: does it respect each node's individual netting overrides,
or apply one blanket netting rule across the whole subtree run?
- [ ] Bulk Commit: how are due-date conflicts on combined nodes handled with
no per-node review step in the loop?
- [x] Confirmed (InvenTree 1.4.2 source): the generic PO line-item form can
pre-fill/set `project_code` directly — it's a genuine field on
`order/po-line/` itself (added since the 1.1.7 baseline this doc was first
written against), not something that has to be set on the parent Purchase
Order instead.

### Performance / Large Trees
- [ ] Define the depth/node-count threshold that triggers "stopped at depth N"
- [ ] Decide whether partial computation still allows selective BO creation

### Edge Cases (to expand)
- [ ] Optional / consumable BOM lines — excluded, shown-unchecked, or filterable?
- [ ] Substitute / variant parts in BOM — auto-pick, prompt, or flag for manual handling?
- [ ] Cycles in BOM data (shouldn't exist, but defensive handling — reuse
`visited.copy()` anti-cycle pattern from Flat BOM)
- [ ] Parent build quantity changes after child BOs already exist
- [ ] Child BO is cancelled — does it revert to Draft, or stay flagged separately?
- [ ] Child BO quantity is manually edited outside this plugin (drift from tree's assumption)
- [ ] Combined BO's due-date conflict: does the user get a persistent warning
if the earliest-branch-date default would still miss the other branch's need?
- [x] BOM revised after some child BOs already exist against the old
structure — not an issue: a Build's `BuildLine`s snapshot the required
quantity from the BOM at creation time (already how InvenTree works for any
Build, not something specific to this plugin), so this is the same accepted
risk as manually creating a BO today. Once you commit, you're locked in to
what the BOM said at that moment.

---

## Superseded / Related Documents

- `PLUGIN-TRILOGY.md` — parent vision doc, Plugin 2 section
