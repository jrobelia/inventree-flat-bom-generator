# InvenTree 1.1.7 → 1.6.3 Upgrade Review

**Status:** Research complete — pending maintainer triage
**Created:** October 2026
**Scope:** Flat BOM Generator plugin compatibility and adoption opportunities when moving the InvenTree backend from the documented "1.1.7 baseline" to tag `1.6.3`
**Evidence:** Local `git diff`/`git log`/`git tag --contains` against `reference\inventree-source` (full clone, all tags 1.0.0–1.6.3)
**Note on dates:** 1.1.7 was tagged 2025-12-17; 1.6.3 was tagged 2026-10-27. Intermediate releases: 1.2.0 (2026-02), 1.3.0 (2026-04), 1.4.0 (2026-06), 1.5.0 (2026-08), 1.6.0 (2026-10). API version went 421 → 561.

---

## 1. Summary Table

| # | Change | First release | Plugin impact |
|---|--------|---------------|---------------|
| 1 | `BomItem.piece_count` (cut-to-length: total = `quantity × piece_count`) | **1.6.0** | **MUST-ADOPT** — plugin ignores it; undercounts any line with `piece_count > 1` |
| 2 | `BomItem.raw_amount` — `quantity` now derived via unit conversion in `clean()` | **1.4.0** | Behavioral — reads still work; fixtures/tests write `quantity=` only (still OK via fallback); zero-qty now rejected on save |
| 3 | `Part.consumable` + `BomItem.is_consumable`/`consumable_filter` | **1.5.0** | **MUST-ADOPT** — plugin reads line flag only; misses part-level consumable parts |
| 4 | `Part.default_supplier` removed → `SupplierPart.primary` | **1.3.0** | Already aligned (plugin uses `primary=True`) — but "Compatible with 1.1.6+" doc claim is now false |
| 5 | Notes refactor — `notes` field removed from Part/StockItem/Build/etc. | **1.6.0** | Runtime unaffected (`bom_item.note` survives); test fixture sets `notes:` on StockItem — verify loaddata |
| 6 | StockItem MPTT removal (`tree_id`/`lft`/`rght`/`level`/`parent` gone) | **1.5.0** | Already handled (plugin commit `d7ebf3f`) |
| 7 | Parameter model refactor (`PartParameter` → generic `Parameter`) | **1.2.0** | None — plugin doesn't use parameters |
| 8 | New `bom` ruleset (BOM permissions split from `part` role) | **1.4.0** | None — data migration clones part→bom rulesets; plugin view is `IsAuthenticated` only |
| 9 | PUI Mantine 8 → 9 (host-provided `window.MantineCore`/`MantineNotifications`) | **1.4.0** | **BREAKING RISK** — panel externalizes `@mantine/*`; built against Mantine 8 APIs, will run against Mantine 9 |
| 10 | `plugin_static_file` rewrite (StaticFilesStorage + vite manifest + `check_exists`/`check_hash`) | **1.6.0-ish** | Compatible — plugin already ships `static/Panel.js` + `.vite/manifest.json` |
| 11 | `Part.maximum_stock` | 1.4.0 | Nice-to-have (over-stock planning signal) |
| 12 | `Part.net_stock` / `quantity_to_order` properties | ≤1.6.3 | Nice-to-have — richer shortage math than `in_stock − allocated` |
| 13 | `Company.is_internal` + `INVENTREE_DEFAULT_INTERNAL_COMPANY` + `Company.get_internal_company()` | **1.6.0** | Nice-to-have — could replace manual internal-supplier settings |
| 14 | New UI features: `route` (custom pages), `primary_action`; `AllocateMixin`; `checkPluginVersion` | route 1.6.0, primary_action 1.4.0, AllocateMixin 1.6.0 | Nice-to-have — panel → full page; allocation hooks |
| 15 | `get_bom_items(include_inherited=True)` is upstream default; plugin filters `BomItem.objects.filter(part=…)` | pre-existing | Pre-existing gap — variant assemblies lose inherited lines (same at 1.1.7) |
| 16 | `get_required_quantity` = `qty × piece_count × build + attrition + setup + rounding` | attrition/setup/rounding pre-1.1.7; piece_count 1.6.0 | **MUST-ADOPT for piece_count**; decide on setup/attrition/rounding divergence |
| 17 | BomItem API: `substitutes` off by default (`?substitutes=true`), `quantity` excluded from import, bulk-update, `sub_part_active` filter | v433/v485/v483/v447 | Informational — plugin uses ORM, not REST |
| 18 | Python floor: 1.5.0 dropped Python 3.11 | 1.5.0 | Packaging — plugin declares `>=3.9`; should declare `>=3.12` |
| 19 | `get_setting(key, cache, backup_value)` — 2nd positional is `cache` | unchanged | Pre-existing latent bug — `get_setting("CUTLIST_UNITS_FOR_INTERNAL_FAB", "mm,in,cm")` passes truthy `cache` |
| 20 | `check_part_lock` gated by `PART_ENABLE_LOCKING`; `part_bomitem` moves to `bom` role | 1.4.0 | None — plugin doesn't write BOMs |
| 21 | `Part.image` still `StdImageField` (variations `{preview, thumbnail}`); `remote_image` removed | image alter 1.1.x; remote_image 1.4.0 | None — `part_obj.image.thumbnail.url` still valid |
| 22 | `stock_entries` external filter → `location__external`; `StockItem.external` field removed | ≤1.6.3 | None — plugin uses aggregates only |
| 23 | `TransferOrder` model; `consumed_by`/`belongs_to`/`install_into` unchanged; allocation_count still excludes transfer orders | 1.4.0 | Informational |
| 24 | API throttling on by default (20/min anon, 20/s auth) | 1.4.0 | None — auth-only endpoint, one request per load |
| 25 | Squashed pre-1.0 migrations — upgrade path must go through 1.0.0 first | 1.6.0 | Operational note — host is on 1.1.7 already, fine |

---

## 2. Per-Change Detail

### 2.1 `BomItem.piece_count` — NEW (1.6.0) — MUST-ADOPT

**Upstream evidence:**
- Commit `ee4ad7fd1` "feat: add piece_count and piece_size fields to BomItem for cut-to-length parts (#12422)" — first tag containing it: **1.6.0** (`git tag --contains ee4ad7fd1 | sort -V` → 1.6.0). The CHANGELOG lists PR #12422 under the 1.5.0 section, but `piece_count` does **not** exist at tag 1.5.0 (merged 2026-08-15, four days after the 1.5.0 cut) — trust the tag.
- Migration `part/migrations/0153_bomitem_piece_count_bomitem_piece_size.py` — despite the filename, it adds **only** `piece_count` (`PositiveIntegerField`, `default=1`, `MinValueValidator(1)`). `piece_size` was dropped during PR review and does **not** exist at 1.6.3.
- Model at `src/backend/InvenTree/part/models.py` (~line 4083 at 1.6.3): *"Number of pieces required (for cut-to-length items). Total material = quantity x piece_count."*
- Consumed by `BomItem.get_required_quantity` (`part/models.py` ~line 4319): `required = self.quantity * self.piece_count * build_quantity`, then attrition, `setup_quantity`, `rounding_multiple`. Used by build line creation at `build/models.py:2126` and `:2141`.
- Also in `hash_fields()` (~line 4133) with backward-compat skip when `== 1` (commit `ff732d01a`), and in `BomItemSerializer` (`part/serializers.py` ~line 1664, 1714). API v532.
- Semantics: **`quantity` = per-piece size/length; `piece_count` = number of pieces** — i.e. exactly the plugin's `cut_length`/`piece_count_inc` concept, now native.

**What the plugin does today:**
- `bom_traversal.py:53` reads only `bom_item.quantity`; `piece_count` is never read anywhere (grep confirmed).
- `bom_traversal.py:224`: `child_cumulative_qty = parent_qty * child_qty` — for a line with `piece_count=10, quantity=200mm`, upstream needs `10 × 200mm` but the plugin reports `1 × 200mm` per parent → **undercounts material by factor `piece_count`**.
- `bom_traversal.py:545–557`: Internal-Fab path computes `piece_count_inc = leaf.get("quantity") or 1` — `quantity` is never set on leaf dicts, so this is always 1 (the code comment even admits it). This is exactly the slot where `bom_item.piece_count` belongs.
- `deduplicate_and_sum` CtL branch (`bom_traversal.py:523–538`) already models `cut_list[{quantity, length}]` — maps 1:1 to `piece_count` × `quantity`.

**Action:** include `piece_count` in the `get_bom_items` item dict (`bom_traversal.py:53` region), multiply `child_qty = quantity × piece_count` for total-material math while keeping `quantity` as the per-piece `cut_length`, and surface `piece_count` in the flat-BOM row/serializer so cut lists show piece counts natively.

---

### 2.2 `BomItem.raw_amount` — `quantity` is now derived (1.4.0) — BEHAVIORAL

**Upstream evidence:**
- Commit `bb2a72a6f` "Support physical units for BOM lines (#11631)" — first tag **1.4.0**. API v485.
- Migration `part/migrations/0149_bomitem_raw_amount.py`: adds `raw_amount` (`CharField(max_length=25)`, initially `blank=True`), backfills it from `quantity` via `str(normalize(Decimal(item.quantity)))` for all existing rows (asserts none left empty), then `AlterField` to `blank=False`.
- Model at 1.6.3: `raw_amount = models.CharField(max_length=25, blank=False, null=False, verbose_name='Amount')` (~line 4020). `quantity` (`DecimalField`) is **recalculated in `clean()`** by `recalculate_quantity()` (~line 3863): `convert_physical_value(self.raw_amount, self.sub_part.units)` → quantized to `0.00001`. Fallback: if `raw_amount` is `''`/`None`, it is set from `self.quantity` first — so ORM objects created with `quantity=` only still work.
- New validations inside `recalculate_quantity`:
  - `quantity <= 0` rejected unless global setting `PART_BOM_ALLOW_ZERO_QUANTITY` (at 1.1.7, `quantity=0` was allowed by `MinValueValidator(0)`).
  - `raw_amount` with units on a sub_part that has no `units` → ValidationError.
- `BomItem.save()` calls `self.clean()` (unchanged pattern), so any save re-derives `quantity` from `raw_amount`.
- New write API: `BomItem.set_quantity(q)` sets `raw_amount` then recalculates.
- Serializer (`part/serializers.py` ~1660–1694): `raw_amount` is the writable field; `import_exclude_fields = ['quantity', 'validated', 'substitutes']` — CSV/API **imports can no longer write `quantity` directly**.

**What the plugin does today:**
- Reads `float(bom_item.quantity)` (`bom_traversal.py:53`) — still valid and now normalized to ≤5dp in `sub_part.units`. No action needed for reads.
- Integration tests create `BomItem.objects.create(part=…, sub_part=…, quantity=N)` (`test_views_integration.py:128–151`, `test_substitute_enrichment.py:255`) — works via the `raw_amount` fallback, but should set `raw_amount=` for fidelity.
- YAML fixtures (`complex_bom.yaml`, `get_bom_items.yaml`, `warning_scenarios.yaml`) set `quantity:` but not `raw_amount:` — loaddata bypasses `clean()` so rows insert with `raw_amount=''` (column is NOT NULL but `''` is legal). Reads are unaffected; any later `.save()` back-fills from `quantity`. Recommend adding `raw_amount:` to fixtures anyway.
- The plugin's unit-mismatch warning (`categorization.py:_check_unit_mismatch`) compares note-embedded units vs `part.units`; upstream now normalizes `quantity` to `sub_part.units` via `raw_amount` — worth considering surfacing `raw_amount` in warnings/UI since it may carry units users typed.

---

### 2.3 `Part.consumable` + effective-consumable semantics (1.5.0) — MUST-ADOPT

**Upstream evidence:**
- Commit `e6a12564f` "[feature] Consumable part (#12295)" — first tag **1.5.0**. Migration `part/0151_part_consumable.py`. API v516.
- `Part.consumable = models.BooleanField(default=False)` — `part/models.py:1340`.
- `BomItem.is_consumable` property (`part/models.py:4231`): `return self.consumable or self.sub_part.consumable`.
- `BomItem.consumable_filter(consumable, prefix)` static helper for queryset filtering (~line 4240).
- Build app now uses the *effective* flag everywhere: `build/models.py:1292` (`consumable_filter(prefix='bom_item__')`), `:1602`, `:1703–1713`, `:1858`, `:2007`, `:2046`, `:2072`, `:2302` — auto-allocation skips lines where the *part* is consumable even if the line isn't flagged.

**What the plugin does today:**
- `bom_traversal.py:58` reads `bom_item.consumable` (line flag only) and aggregates "consumable iff consumable in ALL appearances" (`deduplicate_and_sum` ~line 602–617, 719–722). A BOM line whose `sub_part.consumable=True` will show `consumable=False` in the flat BOM while upstream treats it as consumable → flag/ordering divergence.

**Action:** read `bom_item.is_consumable` (property, zero cost) instead of `.consumable` at `bom_traversal.py:58`.

---

### 2.4 `Part.default_supplier` → `SupplierPart.primary` (1.3.0) — ALIGNED, but doc claim broke

**Upstream evidence:**
- Commit `3910cc5a5` "Supplier Part Updates (#11303)" — first tag **1.3.0**. Migration `part/0147_remove_part_default_supplier.py` + `company/0079_*` (adds `primary` + data migration). API v456.
- `SupplierPart.primary = models.BooleanField` (`company/models.py` ~line 837); `SupplierPart.save()` enforces single-primary per part and auto-marks a lone SupplierPart as primary.
- `Part.default_supplier` FK and `Part.get_default_supplier()` removed.

**What the plugin does today:**
- Already uses the new field: `SupplierPart.objects.filter(part_id__in=…, primary=True)` (`bom_traversal.py:37`) and `.filter(part=part, primary=True)` (`bom_traversal.py:150`); fixture `get_bom_items.yaml:137` sets `primary: true`. Plugin commit `33bb008` restored this semantics — **compatible with ≥1.3.0**.
- Consequence: `docs\ARCHITECTURE.md:526` ("Compatible with 1.1.6+") is now wrong. On 1.1.7–1.2.x, `filter(primary=True)` raises `FieldError` → caught by the broad `except` in `get_bom_items` (`bom_traversal.py:67–69`) → returns `[]` → **every assembly silently reports "no BOM items"**. Effective minimum is 1.3.0.

**Action:** set `MIN_VERSION = '1.3.0'` in `core.py` (lines 24–26 are commented placeholders) — or `'1.6.0'` once `piece_count`/`is_consumable` are adopted — and fix the doc claim.

---

### 2.5 Notes refactor (1.6.0) — LOW RISK at runtime, fixture check needed

**Upstream evidence:**
- Commit `02da01dfe` "[Refactor] Notes (#11971)" — first tag **1.6.0**. API v537: *"Removes direct 'notes' field from any models which previously supported markdown notes; adds generic Note model attached via generic FK."*
- Migrations: `part/0154_remove_part_notes.py`, `stock/0128_remove_stockitem_notes.py`, `build/0060_remove_build_notes.py`, plus `common/0052_*` (generic `Note`/`NotesImage` models).
- `Part` now mixes in `InvenTreeNoteMixin` (`InvenTree/models.py:685`); `part.notes` returns a **related QuerySet of Note objects**, not a markdown string.
- **`BomItem.note` (singular, `CharField(max_length=500)`) is untouched** — still present at `part/models.py` ~line 4101.

**What the plugin does today:**
- Runtime reads only `bom_item.note` (`bom_traversal.py:55–56`) — unaffected.
- Fixture `substitute_enrichment.yaml:202,220,238` sets `notes: ''` on `stock.StockItem` rows — that field no longer exists at 1.6.3. Whether loaddata errors or warns depends on the Django version in the devcontainer (recent Django skips unknown fixture fields) — **verify on first 1.6.3 test run; remove the key if it errors.**

---

### 2.6 StockItem MPTT removal (1.5.0) — ALREADY HANDLED

- Commit `766a8b41d` (#12360) — first tag **1.5.0**. Migrations `stock/0124_alter_mptt_fields.py`, `0125_remove_mptt_fields.py`. API v521.
- `parent`, `tree_id`, `lft`, `rght`, `level` removed from StockItem; `belongs_to`, `consumed_by`, `install_into`/`installed_item` remain (`stock/models.py:1201`, `:1266`, `:1923`).
- Plugin already dropped tree fields from its fixture (commit `d7ebf3f`). `Part`/`PartCategory` are still MPTT (`InvenTreeTree`), so `tree_id`/`lft`/`rght`/`level` in `part.part`/`part.partcategory` fixture rows remain valid.

### 2.7 Parameter refactor (1.2.0) — NO IMPACT

- #10699 — `PartParameter`/`PartParameterTemplate`/`ManufacturerPartParameter` replaced by generic `Parameter`/`ParameterTemplate` attachable to any model (migrations `part/0144–0146`, API v430). Plugin doesn't use parameters. Its `model: part.partcategory` plugin-settings pickers are unaffected.

### 2.8 New `bom` ruleset (1.4.0) — NO PLUGIN IMPACT

- Commit `2b6952eab` (#11825) — first tag **1.4.0**. `users/ruleset.py:29` `BOM = 'bom'`; `:115` maps `part_bomitem`/`part_bomitemsubstitute` models to it. Data migration `part/0148_auto_20260427_2233.py` clones each group's `part` ruleset into a `bom` ruleset — permission continuity is automatic.
- `part/api.py:619` — `PartValidateBOM` endpoint requires `role_required = 'bom'`. The plugin's `FlatBOMView` uses only `permissions.IsAuthenticated` (`views.py:216`) and pure ORM — unaffected. Side note: users now need `bom` ruleset to use BOM APIs; admin should verify roles post-upgrade.

### 2.9 PUI: Mantine 8 → 9 — FRONTEND BREAKING RISK

- `@mantine/*`: `^8.2.7` at 1.1.7–1.3.0 → `^9.2.1` at 1.4.0 → `^9.7.1` at 1.6.3 (`src/frontend/package.json`). `mantine-datatable` `^8.2.0` → `^9.2.2`. React `^19.1.1` → `^19.2.7` (minor, fine). Lingui `^5.3.1` → `^5.9.x`.
- Host globals confirmed at 1.6.3 (`src/frontend/src/main.tsx:126–132`): `window.React`, `ReactDOM`, `ReactDOMClient`, `MantineCore`, `MantineNotifications`, `LinguiCore`, `LinguiReact` — all still exposed.
- **Risk:** the plugin externalizes `@mantine/core`, `@mantine/hooks`? (no — `@mantine/core`, `@mantine/notifications`, `react`, `react-dom`, `ReactDom`, `@lingui/core`, `@lingui/react` per `frontend/vite.config.ts:11–19`) to host globals. The panel was built against Mantine 8 APIs and will now receive Mantine 9 components — a major-version jump with breaking component/style changes (e.g., `sx`/`styles` removal, notification API, compound component changes). The panel will load (globals exist) but may render incorrectly or crash at runtime.
- **Action:** rebuild the frontend against Mantine 9 types (`@mantine/* ^9`, `mantine-datatable ^9` if used), fix API drift, re-run Vitest/Playwright. `frontend/package.json:19–26` currently declares `>= 8.2.7` — bump to `^9`.

### 2.10 `plugin_static_file` rewrite — COMPATIBLE

- `plugin/plugin.py:630` at 1.6.3: signature `plugin_static_file(*args, check_exists=True, check_hash=True)`. Now resolves through `StaticFilesStorage` (collected static tree), tries `hashed_file_lookup` first — reads `plugins/<slug>/.vite/manifest.json` (vite manifest, "as generated by the plugin creator framework") and maps `file.js|jsx|tsx` → hashed output (`plugin/plugin.py:586–617`). Logs an error if the file isn't found but still returns the URL.
- Static collection: `plugin/staticfiles.py` `_copy_plugin_static_files` copies `<pkg>/static/**` → `plugins/<slug>/` — same mechanism as 1.1.7 (file existed then too).
- **Plugin ships `flat_bom_generator/static/Panel.js` + `static/.vite/manifest.json`** (entry `src/Panel.tsx` → `file: Panel.js`) — fully compatible; `check_exists`/`check_hash` both succeed.
- `core.py:127` appends `?v={PLUGIN_VERSION}` *after* the `:function` — the PUI (`src/frontend/src/components/plugins/PluginSource.tsx:46`) splits on `:` in `url.pathname`, so `?v=` lands in the query string — still a working cache-buster.

### 2.11 Part model new fields/properties — NICE-TO-HAVE

- `Part.maximum_stock` (1.4.0, #11914, migration 0150, API v486) — `part/models.py:1269`.
- `Part.consumable` — see §2.3.
- `Part.net_stock` property (`part/models.py:1575`): `total_stock − allocation_count + on_order`, **can go negative** — a better shortage signal than the plugin's `max(total − allocated, 0)` (`views.py:442`).
- `Part.quantity_to_order` (~line 1546): `required − max(total_stock, minimum_stock) − on_order − quantity_being_built`, floored at 0 — upstream's own "how much to order" math.
- `required_order_quantity`, `quantity_being_built`, `get_installed_part_options` — exist at both versions.
- `allocation_count` (`:1849`) — semantics unchanged (build + sales; transfer orders still commented out). `available_stock` (`:1408`) unchanged. `on_order` (`:2490`) — same pack-quantity-aware computation via `SupplierPart.base_quantity`.
- `Part.get_descendants`/`PartCategory.get_descendants` — MPTT intact at 1.6.3 (used at `views.py:188`, `bom_traversal.py` category logic).
- `check_add_to_bom` (`:675`) — same contract; now reads `tree_id` from DB rather than trusting in-memory values.

### 2.12 `get_bom_items` vs plugin's direct filter — PRE-EXISTING GAP (unchanged)

- `Part.get_bom_items(include_inherited=True, include_virtual=True)` (`part/models.py:1952`) — **defaults include inherited lines from parent (variant) parts**; identical signature at 1.1.7.
- Plugin uses `BomItem.objects.filter(part=part)` (`bom_traversal.py:29`) ≡ `include_inherited=False`. A *variant* assembly flattened by the plugin misses parent-inherited lines; upstream builds/BOM views include them. Same behavior at 1.1.7 — flag as a decision point (honor `inherited` + `allow_variants`?), not a new break.

### 2.13 Company internals — NICE-TO-HAVE (1.6.0)

- `Company.is_internal` (`company/models.py:250`), `Company.get_internal_company()` (~line 145), global setting `INVENTREE_DEFAULT_INTERNAL_COMPANY` (`common/setting/system.py:276`) — commit `9b8fdeb06` (#13017), first tag **1.6.0**, API v556.
- The plugin's `PRIMARY_INTERNAL_SUPPLIER`/`ADDITIONAL_INTERNAL_SUPPLIERS` settings (`core.py:34–45`, resolved in `views.py:51–116`) could default to the native internal company — simpler config for the common case.

### 2.14 Plugin-interface changes — ALL COMPATIBLE + new capabilities

- Mixins identical at both tags: `plugin.mixins` re-exports `SettingsMixin`, `UrlsMixin`, `UserInterfaceMixin` at both 1.1.7 and 1.6.3. `UrlsMixin` file diff is empty. `get_setting(key, cache=False, backup_value=None)` identical signature at both versions (`SettingsMixin.py:77`).
- `get_ui_panels(request, context, **kwargs)` signature and `context` keys (`target_model`, `target_id`) unchanged (`plugin/base/ui/mixins.py:136`; `base/ui/tests.py:124`). Panel dict keys `key/title/description/icon/source` still accepted — server fills `feature_type`/`plugin_name` (`plugin/base/ui/api.py:30–60`). `ENABLE_PLUGINS_INTERFACE`/`ENABLE_PLUGINS_URL` still gate UI/URL features (`common/setting/system.py:1208–1248`).
- `registry.get_plugin(slug, active=True, with_mixin=None)` identical (`registry.py:193`). `MIN_VERSION`/`MAX_VERSION` enforced at `registry.py:911` — plugin currently has them commented out (`core.py:25–26`).
- **New at 1.6.3** (adoption candidates): `route` UI feature — register a full custom page (1.6.0, #12900); `primary_action` buttons (1.4.0, #9570); `AllocateMixin` — customize auto stock allocation for builds/sales (1.6.0, #12914); `checkPluginVersion`/`INVENTREE_REACT_VERSION` in `@inventreedb/ui` context lib. `get_ui_dashboard_items`, `get_ui_navigation_items`, `get_ui_template_editors/previews`, `get_ui_spotlight_actions` already existed at 1.1.7.
- `InvenTreePluginContext` (`src/frontend/lib/types/Plugins.tsx`) still provides `api`, `id`, `instance`, `reloadInstance` — the fields `Panel.tsx` consumes (`context.api`, `context.id`, `context.instance`).
- `InvenTreePlugin` meta attrs (`TITLE/NAME/SLUG/DESCRIPTION/VERSION/AUTHOR/LICENSE`) unchanged; entry-point group `inventree_plugins` unchanged (`plugin/helpers.py:122`).

### 2.15 Build/stock allocation math — informational

- `BuildLine.quantity` is set from `bom_item.get_required_quantity(self.quantity)` (`build/models.py:2141`) — now includes `piece_count`, `attrition`, `setup_quantity`, `rounding_multiple` → the plugin's totals will diverge from real build requirements wherever those fields are used (piece_count is new; the other three predate 1.1.7, so divergence already existed).
- `is_consumable`/`consumable_filter` now drive auto-allocation skips (§2.3).
- `TransferOrder` model added (1.4.0, API v492); `Part.allocation_count` still excludes transfer-order allocations (commented at `part/models.py:1855–1858`).
- `StockItem.creation_date`, `status` codes unchanged (`StockStatus.OK = 10`, fixture `status: 10` valid); `review_needed` removed (1.4.0) — not used by plugin fixtures.
- Build-output and auto-allocate API calls now offload to background tasks returning task IDs (API v465, v466, v494) — only relevant if the plugin later drives builds via API.

### 2.16 API surface — informational (plugin uses ORM)

- `BomItemSerializer` (`part/serializers.py` ~1640): fields now include `raw_amount`, `piece_count`; `substitutes` is an `OptionalField` excluded by default (`?substitutes=true`, API v433); `import_exclude_fields` drops `quantity`.
- `BomList` (`part/api.py:1456`): gained `BulkUpdateMixin` (v483) + `DataExportViewMixin`; `BomFilter.sub_part_active` filter (v447); expanded ordering fields.
- `PartSerializer`: `default_supplier`, `notes`, `remote_image` removed; `consumable`, `maximum_stock` added.
- New "bom" ruleset on BOM-writing endpoints (§2.8). API version 421 → 561; ~140 bumps in range, mostly additive (full list in `InvenTree/api_version.py`).

### 2.17 Packaging/runtime

- InvenTree 1.5.0 dropped Python 3.11 (#12223); 1.2.0 dropped 3.9/3.10. Plugin `pyproject.toml:20` declares `requires-python = ">=3.9"` — bump to `>=3.12`.
- Squashed migrations for pre-1.0 installs (1.6.0, #12830) — only affects hosts upgrading from <1.0.0; the 1.1.7 host is fine.

---

## 3. Things the Plugin Should Adopt

Ranked by impact:

1. **`piece_count` multiplication (1.6.0).** Read `bom_item.piece_count` in `get_bom_items` (`bom_traversal.py:53` region); compute `line_total_qty = quantity × piece_count` for cumulative/total math while keeping `quantity` as the per-piece `cut_length`. Add `piece_count` to `FlatBOMItemSerializer` and the cut-list/`internal_fab_cut_list` entries — this *is* the native cut-to-length model the plugin was designed around (cables, tubing, cut lists). Update the Internal-Fab `piece_count_inc` slot (`bom_traversal.py:545–557`) which is hardwired to 1 today.
2. **Effective consumable flag (1.5.0).** Use `bom_item.is_consumable` instead of `bom_item.consumable` at `bom_traversal.py:58` so `Part.consumable` parts are honored, matching build/auto-allocation behavior upstream.
3. **`MIN_VERSION`/`MAX_VERSION`.** Declare `MIN_VERSION = '1.3.0'` (required by `SupplierPart.primary`) now, and `'1.6.0'` once `piece_count`/`is_consumable` are adopted. `core.py:25–26` already has the commented slots; registry enforces them (`registry.py:911`) and logs a clear registry error instead of silent empty-BOM failure.
4. **Better shortage math.** Consider `part.net_stock` (can be negative → real shortage number) and/or `part.quantity_to_order` instead of hand-rolled `total_stock − allocation_count` at `views.py:437–442`. At minimum expose `net_stock` alongside `available`.
5. **`raw_amount` awareness.** Surface `bom_item.raw_amount` in the BOM detail/UI (it may carry typed units like "250 mm"), add it to fixtures, and switch test `BomItem.objects.create(quantity=N)` calls to `raw_amount=str(N)` for fidelity.
6. **`Company.is_internal` / `INVENTREE_DEFAULT_INTERNAL_COMPANY` (1.6.0).** Default `PRIMARY_INTERNAL_SUPPLIER` to `Company.get_internal_company()` when the plugin setting is unset (`views.py:51–116`).
7. **Decide on `inherited`/`allow_variants`.** If variant-part flattening matters, switch `BomItem.objects.filter(part=part)` to `part.get_bom_items(include_inherited=…)` and honor `allow_variants`/`get_valid_parts_for_allocation()` for substitute/variant stock display.
8. **Optional: new UI surface.** `route` feature (1.6.0) could host a dedicated flat-BOM page instead of only a part panel; `primary_action` (1.4.0) could add "Generate Flat BOM" buttons; `AllocateMixin` (1.6.0) for future allocation-aware planning.
9. **Optional: setup/attrition/rounding awareness.** `get_required_quantity` semantics now cover `quantity × piece_count` plus `setup_quantity`, `attrition%`, `rounding_multiple` (all pre-1.1.7 except piece_count). The plugin reports procurement totals, not per-build requirements — document the divergence or offer a "build-quantity" mode that uses `get_required_quantity` per line.

---

## 4. Breaking / Behavioral Risks

1. **Frontend Mantine 8→9 (highest risk):** panel externalizes `MantineCore`/`MantineNotifications`/`React` globals — all still exposed (`main.tsx:126–132`) but now **Mantine 9**. Rebuild against Mantine 9 types and re-run component/E2E tests before shipping to 1.6.3. Bump `frontend/package.json` Mantine pins to `^9`.
2. **`piece_count` undercount:** any user BOM line with `piece_count>1` silently under-reports total material (and piece counts) — wrong procurement/cut lists, hard to notice.
3. **`Part.consumable` flag missed:** consumable-flagged parts look non-consumable in flat BOM output.
4. **Doc claim false:** "Compatible with 1.1.6+" — actual floor is 1.3.0 (SupplierPart.primary). On <1.3.0 the failure is **silent** (`FieldError` swallowed → empty BOM). Even though the deployment target is 1.6.3, fix the metadata so nobody installs it on 1.1.x/1.2.x.
5. **Zero-quantity BOM lines now rejected on `save()`** unless `PART_BOM_ALLOW_ZERO_QUANTITY` — plugin tests/fixtures only use positive quantities, but any zero-qty fixture/test data or user workflow that relied on `quantity=0` will now fail validation.
6. **Fixture `notes:` on StockItem** (`substitute_enrichment.yaml:202,220,238`) — field removed in 1.6.0; verify loaddata tolerates unknown fields (likely skipped) or strip the key.
7. **`get_setting` positional bug (pre-existing):** `plugin.get_setting("CUTLIST_UNITS_FOR_INTERNAL_FAB", "mm,in,cm")` (`views.py:277`, `:671`) passes `"mm,in,cm"` as `cache` (truthy → caches; also *not* a backup value — the real default comes only from `SETTINGS` default). Similarly `get_setting("ADDITIONAL_INTERNAL_SUPPLIERS", "")` passes `cache=""` (harmless) and the `SHOW_*` calls pass `cache=False` (harmless). Switch all second-positional defaults to `backup_value=` kwarg — same signature at both versions, so it's a latent bug today too.
8. **`substitutes`/`quantity` API contract:** if any external tooling imports BOM data via API/CSV, `quantity` is no longer writable (`import_exclude_fields`) — must write `raw_amount`. `?substitutes=true` now required to see substitutes on BomItem API.
9. **`Part.notes`/`StockItem.notes`/`Build.notes` gone:** any future feature touching model notes must use the `common.Note` generic model / `/api/note/` endpoints.
10. **Validation on `raw_amount`:** BOM lines whose `raw_amount` has units need `sub_part.units` set, else `clean()` rejects — data created pre-1.4.0 was migrated, but new programmatic writes must respect it.

---

## 5. Open Questions for the Maintainer

1. **piece_count semantics in flat-BOM output:** for a line `quantity=200mm, piece_count=10`, should the flat BOM show total material (2000mm), piece count (10 × 200mm rows in cut list), or both? How does it interact with the existing CtL note-parsing path — should note-parsed lengths and `piece_count` coexist, or should `piece_count` become the canonical mechanism with notes as fallback?
2. **Inherited BOM lines:** is flattening variant assemblies in scope? Upstream `get_bom_items` includes `inherited=True` lines from parent parts by default; the plugin never has. Deliberate simplification or adoption candidate?
3. **Consumable semantics:** should flat-BOM "consumable" mean effective (`is_consumable`) or line-only? Recommend effective to match builds.
4. **Minimum version floor:** set `MIN_VERSION = '1.3.0'` (SupplierPart.primary) or jump straight to `'1.6.0'` once piece_count work lands? Should `ARCHITECTURE.md`'s "1.1.6+" be corrected now?
5. **Fixture hygiene:** add `raw_amount:` to bomitem fixture rows and drop `notes:` from StockItem rows — confirm loaddata behavior on the devcontainer's Django first.
6. **Internal-company adoption:** keep the plugin's supplier-ID settings as override, or default to `INVENTREE_DEFAULT_INTERNAL_COMPANY`/`Company.is_internal` when unset?
7. **`get_setting` defaults:** fix `backup_value=` usage everywhere as part of this upgrade, or log as separate issue?
8. **Mantine 9 migration scope:** rebuild-only, or take the opportunity to adopt `mantine-datatable ^9` / new UI features (`route` full page, `primary_action`) at the same time?
9. **Shortage math:** does "production planning" want `net_stock`/`quantity_to_order` (can be negative, upstream's order-suggestion basis) or keep `available_stock` (floored at 0)?
10. **API-version awareness:** plugin's endpoint is custom and unaffected by the 421→561 bump, but should the plugin record `MIN_VERSION`/`MAX_VERSION` anyway for install-time safety?

---

*Methodology: all findings verified via `git log`/`git diff`/`git show`/`git tag --contains` between tags `1.1.7` and `1.6.3` in the vendored `reference\inventree-source` clone; commit SHAs, migration numbers, and 1.6.3 file:line references cited inline.*
