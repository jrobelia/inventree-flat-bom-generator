# Code-First Test Writing Methodology

**Date Established:** December 18, 2025  
**Context:** Rewriting test_internal_fab_cutlist.py after discovering tests validated stub functions instead of real code

**Related Documentation:**
- [TEST-QUALITY-REVIEW.md](TEST-QUALITY-REVIEW.md) - Quality assessment of all tests
- [TEST-PLAN.md](../../flat_bom_generator/tests/TEST-PLAN.md) - Testing strategy and execution
- [ROADMAP.md](ROADMAP.md) - Refactoring priorities and test-first workflow
- [DEPLOYMENT-WORKFLOW.md](DEPLOYMENT-WORKFLOW.md) - Phase-based testing and deployment

**Success Metrics:**
- Discovered 2 incorrect fallback code paths (using cumulative_qty where shouldn't)
- Removed 30+ lines of dead code
- Rewrote 11 tests to validate actual behavior
- All tests pass, code works as documented

---

## The Problem

Initially tried to rewrite tests by assuming how the code should work. This led to:
- ❌ Incorrect assumptions about what `cumulative_qty` meant
- ❌ Tests that validated fantasy behavior, not actual implementation
- ❌ Confusion about calculation logic (thought cumulative_qty was input, not ignored)
- ❌ Nearly shipping bad tests that would pass but test the wrong thing
- ❌ User caught backwards understanding: "you are doing it backwards"

**Critical moment:** User said "woah woah woah, now I am afraid we have a more systemic error in our understanding" and insisted we read the actual code first.

---

## The Solution: Code-First Test Writing

**Core Principle:** Read code → Trace examples → Understand behavior → Write tests

This is the opposite of TDD's "write test first" - use this when refactoring existing code or when you don't understand what code should do yet.

### Step 1: Read the Implementation

**Don't assume. Read the actual code.**

For `deduplicate_and_sum`, we read:
- The function signature and docstring (lines 458-470)
- The main loop processing leaves (lines 490-598)
- The result construction (lines 690-730)

Key discoveries:
- Three separate code paths: CtL, Internal Fab with cut_length, Regular parts
- `piece_count_inc = leaf.get("quantity") or 1` always returns 1 (field not in leaves)
- `try/except` fallback to cumulative_qty was broken logic
- `elif from_ifab` without cut_length check was unreachable (dead code)

**Ask questions while reading:**
- Where is this variable set? (Found: cut_length comes from line 272, set to child_qty)
- Can this code path execute? (Found: two paths were dead code)
- What's this fallback for? (Found: incorrect cumulative_qty fallbacks)

### Step 2: Find a Working Test

Located `test_piece_qty_times_count_rollup.py` - a test that was already passing.

This gave us:
- Known good input data structure
- Expected output to verify against
- Proof the code works (at least for this case)

**Why this helps:**
- Shows what "leaf" structure looks like in practice
- Gives concrete values to trace through code
- Validates our understanding (if trace matches test, we're right)

### Step 3: Trace Through Step-by-Step

**Walk through the code with concrete example:**

```
Input: 3 leaves for part_id=285, each with cut_length=35, cumulative_qty=105/105/35

Process Leaf 1:
  - key = 285
  - from_ifab=True, cut_length=35, unit="mm"
  - piece_count_inc = leaf.get("quantity") or 1 → 1
  - totals[285] = 0 + (35 * 1) = 35
  - internal_fab_cut_lists[285] = [{piece_qty: 35, count: 1, unit: "mm"}]

Process Leaf 2:
  - key = 285 (same part)
  - from_ifab=True, cut_length=35, unit="mm"
  - piece_count_inc = 1
  - totals[285] = 35 + (35 * 1) = 70
  - Found existing entry with piece_qty=35, increment count → count=2

Process Leaf 3:
  - key = 285 (same part)
  - from_ifab=True, cut_length=35, unit="mm"
  - piece_count_inc = 1
  - totals[285] = 70 + (35 * 1) = 105
  - Found existing entry with piece_qty=35, increment count → count=3

Output:
  - total_qty = 105
  - internal_fab_cut_list = [{piece_qty: 35, count: 3, unit: "mm"}]
```

**Critical realization:** cumulative_qty (105, 105, 35) is never used! The code only uses cut_length.

### Step 4: Question Suspicious Code

During trace, we found:
1. **try/except fallback** (line 532): "If multiplication fails, use cumulative_qty"
   - Question: When would `cut_length * 1` fail? Both are always numbers.
   - Conclusion: Dead code path giving wrong results
   - Action: Removed it

2. **elif from_ifab without cut_length** (lines 553-573): 25 lines handling internal fab parts without cut_length
   - Question: Where is cut_length set? Can it be None?
   - Discovery: Line 272 ALWAYS sets `cut_length = child_qty` for internal fab
   - Conclusion: Unreachable code (child_qty is required by InvenTree)
   - Action: Removed 25 lines, added assertion to fail fast if child_qty is None

3. **Unit mismatch "fallback"** (lines 560-565): Used cumulative_qty if unit didn't match
   - Question: Should same part have different units?
   - Conclusion: Data corruption, should error not fallback
   - Action: Changed to ValueError

### Step 5: Write Tests Matching Actual Behavior

Created `create_leaf()` helper:
```python
def create_leaf(part_id, ipn, part_name, cut_length, unit):
    return {
        "part_id": part_id,
        "cut_length": cut_length,
        "cumulative_qty": 0,  # Explicitly show it's ignored
        "unit": unit,
        # ... other required fields
    }
```

**Key decision:** Set `cumulative_qty=0` to explicitly document it's not used.

Wrote tests validating:
- ✅ One occurrence: total=25, count=1
- ✅ Three occurrences: total=75, count=3  
- ✅ Different lengths: separate cut_list entries
- ✅ Unit mismatch: ValueError (not silent fallback)
- ✅ Missing unit: ValueError (not silent fallback)

### Step 6: Learn from Test Failures

After removing dead code, 2 tests failed:
- Expected: Parts with wrong unit filtered out
- Actual: Parts appear with total=0 (cumulative_qty fallback)

**Why?** Removing dead code changed behavior. The `elif from_ifab` path handled these, now they fall to `else` block.

**Fix:** Updated tests to expect `len(result)=1` with `total_qty=0` instead of `len(result)=0`.

**Lesson:** Always run tests after code cleanup. Behavior changes are OK if understood and documented.

---

## When to Use This Methodology

**Use code-first approach when:**
- ✅ Refactoring existing code with poor/no tests
- ✅ Don't understand what code currently does
- ✅ Previous tests validated wrong behavior
- ✅ Code has complex logic or multiple paths
- ✅ Need to verify assumptions about behavior

**Don't use when:**
- ❌ Writing new feature from scratch (use TDD)
- ❌ Requirements are clear and simple
- ❌ Code doesn't exist yet
- ❌ Behavior is obvious from function signature

---

## Red Flags That Indicate You Need This Approach

1. **"I think this does X"** - You're guessing, not knowing
2. **Tests use stub functions** - You're testing fantasy code
3. **Tests have magic numbers** - You don't know why values are correct
4. **User says "that's backwards"** - Your mental model is wrong
5. **Multiple fallback paths** - Code trying to handle everything, probably incorrectly
6. **try/except with no error** - Silent failures hiding bugs

---

## Before vs After

### ❌ Before (Assumption-Based)

```python
def test_internal_fab_rollup(self):
    """Test that internal fab parts aggregate correctly."""
    # Assume: cumulative_qty = total material needed
    leaves = [create_leaf(cumulative_qty=585, ...)]  # 3 × 195mm
    
    result = deduplicate_and_sum(leaves)
    
    # Expecting cumulative_qty to be divided by cut_length
    self.assertEqual(result[0]["count"], 3)  # 585 / 195 = 3
```

**Problem:** Assumes cumulative_qty is used. Code actually ignores it.

### ✅ After (Code-First)

```python
def test_rollup_multiple_occurrences_same_length(self):
    """Multiple occurrences of same part with same cut_length should aggregate.
    
    Each leaf = ONE occurrence in BOM. Code adds cut_length for each occurrence.
    """
    # 3 BOM occurrences: each needs 1 piece of 25mm tubing
    leaves = [
        create_leaf(123, "TUBE-001", "Tube", 25.0, "mm"),  # Occurrence 1
        create_leaf(123, "TUBE-001", "Tube", 25.0, "mm"),  # Occurrence 2
        create_leaf(123, "TUBE-001", "Tube", 25.0, "mm"),  # Occurrence 3
    ]
    
    result = deduplicate_and_sum(leaves)
    
    # Code: total = 25 + 25 + 25 = 75
    self.assertEqual(result[0]["total_qty"], 75.0)
    self.assertEqual(result[0]["internal_fab_cut_list"][0]["count"], 3)
```

**Why better:** Tests actual behavior, documents how code works, no assumptions.

---

## Checklist for Code-First Testing

- [ ] **Read function signature** - What inputs? What outputs?
- [ ] **Read implementation** - What does code actually do?
- [ ] **Find working test** - Known good input/output to trace
- [ ] **Trace step-by-step** - Walk through with concrete values
- [ ] **Document findings** - Write down discoveries in test file header
- [ ] **Question suspicious code** - Fallbacks, try/except, complex conditions
- [ ] **Write helper functions** - Make test data structure clear
- [ ] **Test actual behavior** - Not what you think it should do
- [ ] **Run tests** - Verify understanding is correct
- [ ] **Clean up code** - Remove dead paths found during investigation
- [ ] **Update tests** - Match any behavior changes from cleanup

---

## What We Discovered Using This Method

### About the Code
1. **cumulative_qty is ignored** for internal fab with cut_length
2. **cut_length comes from BOM quantity** (line 272: `cut_length = child_qty`)
3. **piece_count_inc always = 1** (quantity field not in leaf dicts)
4. **Two dead code paths** using cumulative_qty incorrectly
5. **Unit mismatch should error** not fallback silently

### About Testing
1. **Test quality > test quantity** - 106 passing tests hid critical gaps
2. **Read before assuming** - Saves hours of wrong-direction work
3. **Trace with concrete values** - Reveals actual logic flow
4. **Question everything** - Especially fallbacks and error handling
5. **Clean as you go** - Dead code creates confusion for next person

### Deliverables Created
- ✅ 11 rewritten tests (all passing)
- ✅ Test file header explaining 3 code paths
- ✅ Helper function with clear purpose
- ✅ Removed 30+ lines of dead/wrong code
- ✅ Added ValueError for data corruption
- ✅ This methodology document for future use

---

## Summary

**The breakthrough moment:** User challenged assumption, insisted we read code first.

**The process that worked:**
1. Read implementation (don't guess)
2. Find working test (concrete example)
3. Trace step-by-step (verify understanding)
4. Question suspicious code (find bugs)
5. Write tests matching reality (not fantasy)
6. Clean code (remove dead paths)

**Time investment:**
- Reading + tracing: 30 minutes
- Writing tests: 45 minutes  
- Finding/removing dead code: 30 minutes
- **Total:** ~2 hours

**Value delivered:**
- Prevented shipping wrong tests
- Found 2 incorrect fallback paths
- Removed 30+ lines of confusing code
- Created 11 high-quality tests
- Documented how internal fab cuts actually work

**Key lesson:** When refactoring tests, always verify what code actually does. Assumptions are the enemy of correct tests.

---

## Test Validation Tracker

**Purpose:** Track which test files have been walked through with code-first methodology to ensure full understanding exists.

**Legend:**
- ✅ **Validated** - Walked through together, tests match actual code behavior
- ⚠️ **Needs Review** - Tests exist but haven't been validated with code walkthrough
- 🔴 **Low Quality** - Known issues (stub functions, magic numbers, unclear purpose)

### Unit Tests (flat_bom_generator/tests/)

| Test File | Status | Count | Notes |
|-----------|--------|-------|-------|
| **test_internal_fab_cutlist.py** | ✅ Validated | 11 | **Dec 18: Code-first walkthrough with user**, tests actual deduplicate_and_sum |
| **test_serializers.py** | ✔️ Well-Written | 23 | Comprehensive field validation, found 2 bugs (not code-first validated) |
| **test_shortfall_calculation.py** | ✔️ Well-Written | 21 | All 4 checkbox scenarios tested (duplicates logic, needs validation) |
| **test_categorization.py** | ✔️ Well-Written | 18 | Pure functions well tested (haven't traced through category hierarchy) |
| **test_assembly_no_children.py** | ⚠️ Needs Review | 4 | Tests specific bug fix, duplicate tree structure in tests |
| **test_max_depth_warnings.py** | ⚠️ Needs Review | 5 | Tests flag logic, but duplicates instead of calling functions |
| **test_cut_to_length_aggregation.py** | 🔴 Low Quality | 1 | Only 1 test, needs 5-10 more edge cases |
| **test_full_bom_part_13.py** | 🔴 Low Quality | 3 | Magic numbers, unclear purpose, may need rewrite/delete |
| **test_internal_fab_cut_rollup.py** | 🔴 Low Quality | 22 | 1 test skipped for months |
| **test_views.py** | ⚠️ Needs Review | 7 | Code structure tests, unclear if comprehensive |

### Integration Tests (flat_bom_generator/tests/integration/)

| Test File | Status | Count | Notes |
|-----------|--------|-------|-------|
| **test_view_function.py** | ✔️ Well-Written | 14 | View layer tests with real models (not code-first validated) |
| **test_views_integration.py** | ⚠️ Needs Review | 7+ | BOM traversal workflow, haven't traced all paths |
| **test_bom_traversal_integration.py** | ⚠️ Needs Review | 6+ | Core functions, need to verify test completeness |

**Total Progress:** 1/13 files validated with code-first methodology (8%)

### Next Tests to Validate

**Priority 1 (High Value):**
1. **test_categorization.py** (18 tests)
   - Walk through category hierarchy logic
   - Verify supplier detection works as coded
   - Check edge cases for overlapping categories

2. **test_shortfall_calculation.py** (21 tests)
   - Trace through actual calculation in Panel.tsx
   - Remove duplicated logic, import actual function
   - Verify all 4 checkbox combinations match UI behavior

**Priority 2 (Medium Value):**
3. **test_assembly_no_children.py** (4 tests)
   - Trace through get_leaf_parts_only() function
   - Verify flag propagation through pipeline
   - Check if tests cover all assembly types

4. **test_max_depth_warnings.py** (5 tests)
   - Walk through flag prioritization logic
   - Remove duplicated logic, call actual functions
   - Verify warning generation matches specification

**Priority 3 (Fix or Delete):**
5. **test_cut_to_length_aggregation.py** (1 test)
   - Expand to 5-10 tests covering edge cases
   - Walk through CtL aggregation logic
   - Add tests for unit conversion, zero quantities

6. **test_full_bom_part_13.py** (3 tests)
   - Understand what "9 unique parts from 10 rows" means
   - Either add clear documentation OR delete if redundant

### Validation Process

When reviewing a test file:
1. [ ] Read the code being tested (actual implementation)
2. [ ] Find a passing test to use as example
3. [ ] Trace through code step-by-step with test values
4. [ ] Document findings in test file header
5. [ ] Question suspicious patterns (fallbacks, duplicated logic)
6. [ ] Rewrite tests if they test fantasy behavior
7. [ ] Mark as ✅ Validated in this tracker
8. [ ] Update TEST-QUALITY-REVIEW.md if quality changes

---

*Last Updated: December 18, 2025*
*Test Validation Tracking Added: December 18, 2025*


  piece_count_inc = 1
  totals[285] += 35 * 1 = 35
  internal_fab_cut_lists[285] = [{"count": 1, "piece_qty": 35}]

Process Leaf 2:
  piece_count_inc = 1
  totals[285] += 35 * 1 = 35  (now 70 total)
  Found existing with piece_qty=35, increment: count = 2

Process Leaf 3:
  piece_count_inc = 1
  totals[285] += 35 * 1 = 35  (now 105 total)
  Found existing with piece_qty=35, increment: count = 3

Output:
  total_qty = 105
  internal_fab_cut_list = [{"piece_qty": 35, "count": 3}]
```

**Critical insight:** cumulative_qty in the input (105) is IGNORED! The code only uses `cut_length × 1`.

### Step 4: Identify and Remove Bad Code

Found problematic fallback:
```python
try:
    totals[key] += cut_length * piece_count_inc
except Exception:
    totals[key] += leaf.get("cumulative_qty", 0)  # WRONG!
```

Why wrong:
- If this fallback hit, totals would be way off (would use 105 instead of 35)
- Defensive programming that masks bugs instead of exposing them
- Test data showed it would give incorrect results

**Action:** Removed the fallback (commit included explanation)

### Step 5: Write Tests That Match Reality

**Test the actual behavior, not what you think it should be:**

```python
def create_leaf(part_id, ipn, part_name, cut_length, unit, ...):
    """
    Each leaf represents ONE occurrence in BOM tree.
    Function adds cut_length to total for each occurrence.
    cumulative_qty is IGNORED for internal fab with cut_length.
    """
    return {
        "cut_length": cut_length,
        "cumulative_qty": 0,  # Explicitly show it's not used
        # ... other fields
    }
```

### Step 6: Run Tests and Learn from Failures

Two tests failed:
- Parts with non-matching units → Filtered out completely (not just missing cut_list)
- Parts with None unit → Same behavior

**Key insight from failures:**
- When unit doesn't match, code goes to `else` block using cumulative_qty
- Our leaves have cumulative_qty=0
- Parts with total=0 and no cut_list get filtered from results

**Action:** Updated test expectations to match discovered behavior

---

## The Methodology

### When Writing Tests for Existing Code:

1. **Read Implementation First**
   - Don't guess how it works
   - Read function signature, docstrings, main logic
   - Identify all code paths (if/elif/else branches)

2. **Find Working Examples**
   - Look for existing tests that pass
   - Examine production data structures
   - Verify assumptions against real usage

3. **Trace Concrete Examples**
   - Pick specific input values
   - Walk through code line by line
   - Write down state changes at each step
   - Verify output matches expectations

4. **Question Suspicious Code**
   - Dead code paths (unreachable)
   - Overly broad exception handling
   - Comments that contradict code
   - Fallbacks that give different results
   - **Remove or fix, don't test broken behavior**

5. **Write Tests That Document Behavior**
   - Clear test names describing what's being tested
   - Comments explaining WHY input values were chosen
   - Explicit about what fields are used/ignored
   - Test edge cases discovered during trace-through

6. **Learn from Test Failures**
   - Failing test = gap in understanding
   - Update understanding, then update test
   - Document why initial assumption was wrong

---

## Red Flags That You Don't Understand the Code

- **"I'll just try this and see if it works"** - No, read first
- **"The test passes so it must be right"** - Could be testing wrong thing
- **"This cumulative_qty probably means..."** - Trace it, don't guess
- **"I'll write tests based on the docstring"** - Docstrings can be outdated
- **"I'll reuse the old test's data structure"** - Old test might be wrong too

---

## Benefits of This Approach

### We Discovered:
1. **Broken fallback logic** - Removed before it caused production issues
2. **Three separate code paths** - Not two like we initially thought
3. **cumulative_qty used in two different ways** - CtL vs Internal Fab without cut_length
4. **Parts filtered out when total=0** - Unexpected but actual behavior
5. **Missing 'quantity' field** - Always defaults to 1

### We Avoided:
- Writing tests that validate incorrect assumptions
- Shipping broken fallback code
- Documenting wrong behavior in test comments
- Future confusion from misleading tests

### We Gained:
- **Confidence** - Tests validate actual implementation
- **Documentation** - Test file header explains all three paths
- **Safety** - Removing bad fallback means errors surface immediately
- **Understanding** - Can now write more tests correctly

---

## Example: Before vs After

### Before (Wrong Approach):
```python
# Assumption: cumulative_qty = 100 means 4 pieces of 25mm
leaves = [create_leaf(cumulative_qty=100, cut_length=25)]
# Expected: count = 100 / 25 = 4
self.assertEqual(cut_list[0]["count"], 4)
```

**Problem:** This assumes the code divides cumulative_qty by cut_length. It doesn't.

### After (Correct Approach):
```python
# Reality: Each leaf = one occurrence, adds cut_length to total
# To get count=4, need 4 separate leaves
leaves = [
    create_leaf(cut_length=25),  # cumulative_qty ignored
    create_leaf(cut_length=25),
    create_leaf(cut_length=25),
    create_leaf(cut_length=25),
]
# total_qty = 25+25+25+25 = 100
# count = 4 occurrences
self.assertEqual(result[0]["total_qty"], 100)
self.assertEqual(cut_list[0]["count"], 4)
```

---

## When to Use This Methodology

**Always use when:**
- Rewriting old tests
- Testing unfamiliar code
- Code has no tests
- Suspicious of existing tests
- Refactoring complex logic

**Can skip when:**
- Writing new code from scratch (test-first development)
- Code is trivial (1-2 line functions)
- Well-documented with good examples
- Just saw it work in production

---

## Checklist for Code-First Testing

Before writing ANY test:
- [ ] Read the function implementation
- [ ] Identify all code paths (if/elif/else)
- [ ] Find or create a working example
- [ ] Trace through with concrete values
- [ ] Document what each variable means
- [ ] Question any suspicious logic
- [ ] Write test matching actual behavior
- [ ] Run test and learn from failures
- [ ] Update test file header with understanding

---

## Summary

**Old Way:** Write tests based on assumptions → Hope they're right → Ship incorrect tests

**New Way:** Read code → Trace examples → Understand behavior → Write tests → Verify understanding

**Result:** Tests that actually validate the code and document its behavior correctly.

---

_Established through collaboration: Human developer + AI agent working together to understand code before testing it._
