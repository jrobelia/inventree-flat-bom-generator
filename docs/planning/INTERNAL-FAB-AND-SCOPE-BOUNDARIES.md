# Internal Fab & Scope Boundaries — Addendum

> **Status:** Vision / ideas phase — companion to `PLUGIN-TRILOGY.md` and
> `BUILD-ORDER-GENERATOR-UX.md`
> **Last Updated:** July 19, 2026

Captures a scope-boundary discussion: how to handle features that are useful
to our shop specifically (internal fab / cut-to-length) without muddying
plugins meant for general public use. Resolves an open question from a prior
handoff doc that proposed a `cf_fab_method` metadata flag and event-driven
"Internal PO" automation — that approach is **rejected** in favor of the
lighter-weight design below, which requires no new metadata, no new object
type, and no company-specific settings in Plugin 2 at all.

---

## The Framing Behind This Whole Document

Every distinction in this doc — assembly vs. leaf, purchasable vs. not,
internal supplier vs. external — ultimately serves one goal: **keeping the
number of individual Build Orders manageable.** If every assembly in a BOM
became its own BO regardless of whether it had a supplier, the planner
would be buried in BOs for things that don't need one — anything already
sourced from a vendor (internal or external) doesn't need to be built by
us, so it shouldn't generate a BO candidate at all.

That single goal is what drives:
- Plugin 1 deciding whether to explode a node (only nodes with no supplier
  committed need their material shown, since only those are BO candidates)
- Plugin 2 only ever showing assemblies with no default supplier as
  something it might build
- Plugin 3 owning what happens to everything that *did* have a supplier —
  routing it to a real PO or an internal one

Keep this in mind when evaluating any future feature idea against this
doc: if a proposal doesn't reduce or manage BO volume, it's probably solving
a different problem than the one this document is about.

---

## Plugin 1 (Flat BOM Generator): Two Independent Flags, Not a New Category

**Background:** Plugin 1 currently has cut-to-length and internal-fab logic
implemented as settings, off by default, using an internal-fab supplier
list. Working through this, "internal fab" isn't actually a distinct
category Plugin 1 needs to name — it's the outcome of two independent,
already-meaningful facts landing on "yes" at the same time:

1. **Does the node get its own purchase-list line?** — Yes if it has a
   default supplier actually set (assembly or not; internal or external).
   No if no default supplier is set, regardless of the InvenTree
   `purchasable` flag — that flag alone doesn't commit to a source.
2. **Does the node get exploded (its own BOM shown as leaf material)?** —
   Yes if no default supplier is set (a plain build assembly, whether or
   not it's flagged purchasable), *or* if a default supplier is set but
   it's on the internal-supplier list. No if a default supplier is set and
   it's an outside vendor.

Walking through all four combinations of assembly vs. default-supplier-set:

| Assembly? | Default supplier set? | Purchase line? | Explode? | Case |
|---|---|---|---|---|
| No | No | — | — | Not currently a defined case; flag if it comes up in practice |
| No | Yes | Yes | No | Ordinary leaf part |
| Yes | No | No | Yes | Plain build assembly (may or may not be flagged purchasable) — only its leaf material appears; the assembly itself is a Build Order concern (Plugin 2), not a purchase-list line |
| Yes | Yes, external vendor | Yes | No | Bought-complete assembly — one line, no explosion, since we're not the ones sourcing its material |
| Yes | Yes, internal supplier | Yes | Yes | The "hybrid" case — gets *both* a purchase line (pointed at the internal supplier, so Plugin 3 knows to generate an internal PO rather than a real one) *and* explosion (since we're the ones producing it and need its raw material) |

**Why this matters:** the assembly-with-external-supplier and plain-build-
assembly cases explode identically or not at all in a way that's easy to
reason about independently. The internal-supplier case is the one cell
where both flags are true simultaneously — that's the entire reason it felt
like it needed a name. It doesn't; it's just this table's overlap case.

**Correction to earlier note in this doc:** an earlier version of this
addendum suggested the internal-supplier list might be removable from
Plugin 1 as redundant with "has default supplier." That was wrong — the
list is load-bearing for the *explode* decision in the overlap case (row 5
above), not just for Plugin 3's PO-routing decision. Without it, Plugin 1
can't tell row 4 (don't explode) from row 5 (do explode), since both are
"assembly + purchasable."

**On the README/settings question:** this reframes what the "internal fab
setting" actually is — not an optional workflow bolt-on, but the mechanism
that resolves a real ambiguity in the assembly × purchasable grid. Whether
that still belongs in an "Optional" README section or gets promoted to
documented core behavior (since *some* answer to row 5 is required for
correct purchase-list output, even if the specific supplier list is company-
specific) is worth deciding — but it's no longer accurate to describe it as
pure bloat.

---

## Plugin 2 (Build Order Generator): No Internal-Fab Awareness Needed

**Terminology correction:** "purchasable" and "has a default supplier" are
not the same condition. InvenTree's `purchasable` flag just marks a part as
*capable* of being bought; a part can be purchasable with no default
supplier ever assigned. The operative condition for all of the logic below
is **default supplier set, yes or no** — not the purchasable flag by itself.

**Key realization:** Plugin 2's rule is a single check on that condition,
and it does not distinguish internal from external suppliers at all — that
distinction doesn't exist for Plugin 2:

- **Has a default supplier (internal or external):** skipped as a BO
  candidate. Never shown as something Plugin 2 might build. Whether
  Plugin 3 later routes it to a real PO or an internal one is entirely
  Plugin 3's concern.
- **No default supplier set** — whether or not the part is flagged
  purchasable — **added to the potential BO list.** No vendor has actually
  been committed to source it, so it remains something Plugin 2 might
  build. A purchasable-but-supplierless assembly is still a build
  candidate, not skipped.

This is a genuine simplification, not a coincidence: the underlying reason
*any* of this three-way split (Plugin 1 explode logic / Plugin 2 BO
candidacy / Plugin 3 supplier routing) exists at all is that **too many
individual Build Orders would be unmanageable.** Any assembly with a default
supplier actually set — internal or external — is deliberately kept out of
the BO pipeline for that reason, and handled instead as a purchase-list line
(Plugin 1) routed to the right kind of PO (Plugin 3). Plugin 2 only ever
sees the assemblies left over: the ones with no supplier committed, where a
BO is the only real option regardless of the purchasable flag's state.

### New Feature: "Show Build Candidates Only" Toggle

Instead, the useful addition is a **generic display filter**, applicable to
any user regardless of whether they have an internal-fab concept at all:

- **Off (default):** current behavior unchanged. Leaf nodes with a default
  supplier still render in the tree, with the Buy action available (the
  existing exception-case behavior).
- **On:** leaf nodes with a default supplier are hidden from the tree
  entirely — not shown as leaves, not shown as Buy candidates. The tree
  displays only assemblies that are genuine build candidates (no default
  supplier, or a supplier that's been excluded from consideration).

**Nature of the change:** this is a pure **rendering/disclosure** change, not
a computation change. Per the existing "Full Computation, Collapsible
Display" principle, the full recursive traversal still runs exactly as
today — every node is still computed. The toggle only changes which already-
computed nodes are *displayed*. This keeps it consistent with the doc's
existing separation of computation from disclosure (the same separation
already used for collapsed-node rollup badges).

**Where it lives:** Either as a control directly on the tree panel (since
it's filtering an already-rendered result set, not re-triggering computation)
or as a persistent user setting — either is fine given it's cheap to toggle
and doesn't require a recompute.

**Naming:** deliberately generic — "Show build candidates only" or similar —
not "hide internal fab parts" or anything fab-specific. This keeps the
feature legible and useful to any user filtering out purchased leaves,
whether or not their org has an internal-fab concept.

**Interaction with rollup badges:** when the toggle is on, a collapsed
node's rollup summary (e.g. "6 sub-assemblies below · 4 need building · 2
covered") should reflect the filtered view — purchased leaves excluded from
the counts — so the badge stays consistent with what's actually shown when
expanded. *(Open question — see below.)*

**Effect on Buy action:** unaffected when toggle is off. When on, Buy simply
never surfaces for hidden nodes, same as if the user just didn't expand that
branch.

---

## Plugin 3 (Purchase Order Generator): Internal-Fab as a Supplier Bucket

This is where company-specific behavior actually belongs, and it requires no
new mechanism — it falls directly out of Plugin 3's existing stated purpose:
group shortfall parts by default supplier, generate POs per supplier.

**How it works:** the internal-fab supplier list is just an internal
"supplier" record (or set of records) representing our own shop. Parts whose
default supplier matches get grouped under that supplier bucket automatically
by Plugin 3's existing group-by-supplier logic — no special-casing needed at
the grouping step itself.

**What's genuinely company-specific:** what Plugin 3 *does* with that one
supplier bucket once grouped. Rather than generating a real PO to send to an
external vendor, a company-specific extension (or a setting scoped to
Plugin 3, following the same off-by-default pattern as Plugin 1) writes an
internal-only PO line — the "Internal PO" bridge concept from the earlier
handoff doc — tagged with the parent build's `project_code`, using the same
PO-line data model as a real purchase, just pointed at an internal "vendor"
rather than a real one. This gives BOM material consumption and quantity
tracking without needing a new InvenTree object type (a native Work Order
concept InvenTree doesn't have) and without touching Plugins 1 or 2 at all.

**Why this is the right owner:** Plugin 3 is inherently the "do something
per-supplier" plugin already. Concentrating all internal-fab-specific logic
here — rather than spreading a supplier list and special-case branches across
Plugin 1's traversal and Plugin 2's tree — means the concept exists in
exactly one place (see closing note below on why this matters).

**Cascading material requirement:** an internal-fab PO isn't the end of the
chain — it also implies a downstream material requirement. If a part is
internally fabbed (e.g. a 3D print or cut-to-length tube), generating its
internal PO should also trigger a check of *that part's own BOM* (raw
filament, stock tubing, etc.) for deficits, and generate a real external PO
for the underlying material where needed. In other words, the internal
supplier bucket doesn't just close the loop on the assembly-level part — it
opens a second-level requirement one BOM layer down, which still needs to
flow through Plugin 3's normal supplier-grouping/PO-generation logic like
any other shortfall. This should fall out of the existing recursive
netting/traversal engine rather than needing special-case code — the
internal-fab part's own BOM is just another node to net and group, the same
as everything else Plugin 3 already handles.

**Boundary with Plugin 2 (unchanged from existing doc):** Plugin 2's ad-hoc
Buy action and Plugin 3's bulk sweep already need to stay in sync by both
reading live open POs. Internal-fab "POs" are just another line in that same
open-PO set — no special coordination code needed, same as the existing
boundary note in `BUILD-ORDER-GENERATOR-UX.md`.

---

## Rejected Approach (from prior handoff doc)

For reference, the following ideas from an earlier handoff conversation are
explicitly **not** being pursued, superseded by the design above:

- `cf_fab_method` custom field with three-way dispatch (`BUILD` /
  `INTERNAL_FAB` / `PURCHASED`) evaluated inside a forked
  `AutoCreateBuildsPlugin` listening for `BuildEvents.ISSUED`. Rejected:
  event-driven automation contradicts the human-in-the-loop Commit Decision
  model that is the core design principle of Plugin 2.
- A dedicated `Internal_Fab_Batch` object with a "Release Batch" control.
  Rejected: this duplicates work already planned as "Bulk Commit" in
  `BUILD-ORDER-GENERATOR-UX.md`; no separate batch object is needed.
- A "Modular Monolith" shared repo for all three plugins. Rejected: conflicts
  with `PLUGIN-TRILOGY.md`'s explicit "no shared library until a third
  plugin proves the need" stance; nothing here changes that calculus.
- A fourth Commit Decision action ("Work Order" / internal PO) inside
  Plugin 2 itself. Rejected in favor of the simpler realization that Plugin 2
  doesn't need to distinguish internal-fab suppliers from any other
  supplier — the display filter above is sufficient, and the actual
  sourcing decision belongs in Plugin 3.

---

## Considered and Declined: Forking Native Automation (Hybrid Model)

A separate handoff proposed forking InvenTree's built-in `AutoCreateBuildsPlugin`
(triggered on `BuildEvents.ISSUED`) to add project-aware netting and a
purchasable guardrail, with a "hybrid model": the fork creates real Build
Orders in the background (framed as "Draft"), and a read-only tree viewer
(originally Plugin 4's concept) lets a human review afterward.

**Declined**, for reasons distinct from the earlier rejected approach above:

- The background-created "Draft" BOs are real database objects the moment
  the signal fires, not unsaved state — reversing one means cancelling/
  cleaning up real records, not discarding a form. This is a materially
  different (and weaker) safety property than Plugin 2's Commit Decision
  model, where nothing is written until a human acts.
- LCA merging would have to happen as post-hoc cleanup (human notices two
  branches got separate BOs for the same sub-assembly, manually
  consolidates) rather than being prevented before creation, as Plugin 2
  already does.
- It would require a second, independent implementation of netting/
  traversal logic living in the forked plugin, separate from Plugin 2's
  engine — a drift risk, and each could disagree with the other.
- The core problem this proposal itself names — lack of visibility — is
  better solved by visibility-first design (Plugin 2's tree, seen before
  anything is created) than by an invisible background process with a
  viewer bolted on after.

**What we're doing instead:** Plugin 2's existing "Bulk Commit" concept
(scoped subtree, one action across multiple Draft nodes, modeled on
InvenTree's native checkbox + bulk-action-button table pattern) already
gets most of the speed benefit without any of the above risk, using the
same traversal/netting/LCA engine as the rest of the plugin. No fork needed.

---

## Open Questions (Running List)

- [ ] "Show build candidates only" toggle: does the rollup badge math need to
      change, or is it acceptable for badges to always reflect the
      unfiltered full computation regardless of display toggle state?
- [ ] Plugin 3: does the internal-fab supplier bucket need its own explicit
      setting to enable "write internal PO instead of real PO," or is
      matching against the supplier list itself sufficient signal?
- [ ] Plugin 1 README split: confirm final section headers and whether
      cut-to-length and internal-fab should be documented as one "Optional"
      section or two separate ones (they may have different audiences).
- [ ] Should "Show build candidates only" default state ever be true for
      internal-fab-heavy trees, or should default always be off regardless
      of context (leaning off, to keep behavior predictable across users)?

---

## Note: Where Public vs. Company-Specific Logic Should Live

Worth keeping in mind for future additions: public/general-purpose
functionality and company-specific workflow tend to separate cleanly by
**which plugin owns the decision**, rather than by settings toggles buried
inside a generalist plugin. Where a feature turns out to be company-specific
after the fact (as happened in Plugin 1), the fix isn't necessarily to
extract it into its own plugin — sometimes it's cheaper and more honest to
just make the plugin's README clear about what's core vs. optional, and
reserve extraction for cases where the logic doesn't hinge on core
traversal the way Plugin 1's did.

---

## Superseded / Related Documents

- `PLUGIN-TRILOGY.md` — parent vision doc
- `BUILD-ORDER-GENERATOR-UX.md` — Plugin 2 detailed spec; this addendum adds
  the "Show build candidates only" toggle under "Opening the Panel" and
  clarifies the Buy-action boundary with Plugin 3
- Prior handoff doc (MRP/BOM Automation & Internal Fab Workflow) — largely
  superseded by this addendum; see "Rejected Approach" above for what was
  dropped and why
