# FlatBOMGenerator Refactor & Optimization Plan

> **Personal Note:**
> I am not certain of my current test quality and am very new to unit testing and refactoring. This plan should assume a learning approach, with extra care for incremental testing, clear documentation, and opportunities to improve test coverage and code quality as I go.

---

## Practical Advice for Unit Testing & Refactoring (Beginner)

1. **Start Small and Isolate Changes**
  - Refactor one small section at a time (e.g., a single function or component).
  - After each change, run your tests to confirm nothing broke.

2. **Write Tests Before and After Refactoring**
  - If a function isn’t tested, write a simple test for its current behavior before changing it.
  - After refactoring, make sure the test still passes.

3. **Use Descriptive Test Names**
  - Name tests after what they check, e.g., `test_flatten_bom_handles_duplicates`.

4. **Focus on “Pure” Functions First**
  - Functions that don’t depend on external state (like database or network) are easiest to test and refactor.

5. **Don’t Aim for Perfection**
  - Incremental improvement is better than a big rewrite. It’s okay if your first tests are basic.

6. **Use Assertions Effectively**
  - Assert expected outputs, but also check for error cases and edge conditions.

7. **Keep Tests Close to Code**
  - Place test files in a `tests/` folder next to the code they cover.

8. **Learn by Example**
  - Look at existing tests in your project or in open-source plugins for patterns.

9. **Use Version Control**
  - Commit after every small, working change. This makes it easy to revert if something breaks.

10. **Ask for Feedback**
   - Don’t hesitate to ask for code reviews or advice as you go.

---

## Goals
- Achieve a semi-professional, maintainable codebase
- Reduce file/component complexity (especially Panel.tsx)
- Improve separation of concerns and code readability
- Adopt modern React/TypeScript patterns (hooks, context, modularization)
- Ensure backend logic is clear, testable, and efficient
- Maintain or improve test coverage
- Document all major changes and rationale

## Step 1: Code Review
- Review frontend (Panel.tsx, related components, hooks, API logic)
- Review backend (core.py, bom_traversal.py, views.py, categorization.py)
- Identify:
  - Long files/components (over 300 lines)
  - Repeated or tightly coupled logic
  - Unclear responsibilities or “God objects”
  - Outdated patterns or tech debt
  - Missing/unclear documentation

## Step 2: Outline Refactor Targets
- List pain points and desired outcomes for each major file/module
- Example (Panel.tsx):
  - Split into smaller presentational and container components
  - Move API/data logic to custom hooks
  - Extract table logic, summary, and controls into separate files
  - Add/clarify prop and state types
- Example (bom_traversal.py):
  - Clarify function responsibilities
  - Add docstrings and type hints
  - Split large functions if needed

## Step 3: Plan Refactor Steps
- For each target area:
  - Define what to split, move, or rewrite
  - Choose new structure/pattern (e.g., hooks, context, services)
  - Plan how to test and validate after each step
- Prioritize high-impact, low-risk changes first
- Commit after each logical step

## Step 4: Incremental Refactor & Test
- Refactor one area at a time
- Run tests and check UI after each change
- Document changes in code and this plan

## Step 5: Final Review & Documentation
- Review for code clarity, maintainability, and test coverage
- Update README and developer docs
- Summarize lessons learned and future improvement ideas

---
## Testing Strategy

### Current Approach: Python unittest
We're using **Python's `unittest.TestCase`** for pure logic testing.

**Why**: 
- No database dependencies yet
- Testing pure Python functions (regex, calculations, string manipulation)
- Can run anywhere without InvenTree environment
- Simple and lightweight for learning

**When to Migrate to Django Tests**:
When we need to test functions that:
- Access database models (Part, BomItem, Company)
- Call Django ORM queries
- Use InvenTree-specific features

### InvenTree's Testing Pattern (Reference)

**Base Classes** (from InvenTree source):
- `InvenTreeTestCase` - For Django model/DB tests
- `InvenTreeAPITestCase` - For API endpoint tests
- Uses fixtures: `fixtures = ['category', 'part', 'bom', 'location']`
- Has `setUpTestData()` classmethod for test data setup

**Example Pattern from InvenTree**:
```python
from django.test import TestCase
from part.models import Part, BomItem

class BomItemTest(TestCase):
    fixtures = ['category', 'part', 'bom']
    
    def setUp(self):
        super().setUp()
        self.bob = Part.objects.get(id=100)
        
    def test_has_bom(self):
        self.assertTrue(self.bob.has_bom)
        self.assertEqual(self.bob.bom_count, 4)
```

**Our Current Tests Are Valid**: InvenTree uses both approaches - pure `unittest.TestCase` for logic, Django tests for models.

---

## Progress Log

### 2025-12-14: First Refactor (categorization.py)

**Target:** `_extract_length_from_notes()` function

**What We Did:**
1. Created comprehensive unit test suite (`test_categorization.py`) with 15 test cases
2. Tested all documented use cases and edge cases (empty, None, floats, integers, units, etc.)
3. Refactored: Moved inline `import re` to module level for better performance
4. Verified all tests pass (15/15 OK)
5. Committed with descriptive message
6. Reviewed InvenTree testing patterns - confirmed our approach is valid for pure functions

**What We Learned:**
- Start with a small, pure function (no external dependencies)
- Write tests first to establish baseline behavior
- Make small, incremental changes
- Run tests after each change to verify nothing broke
- Commit immediately after success
- Our `unittest.TestCase` approach matches InvenTree's pattern for pure logic tests

**Next Steps:**
- Continue with more pure functions (no DB dependencies)
- When we need to test functions with database access, we'll migrate to `InvenTreeTestCase`
- Focus on clear, well-tested functions that are easy to understand

### 2025-12-14: Second Refactor (categorization.py - categorize_part)

**Target:** `categorize_part()` function

**What We Did:**
1. Discovered unused ASSEMBLY_CATEGORY setting during test planning
2. Removed ASSEMBLY_CATEGORY from plugin settings, views, and docstrings
3. Clarified that assembly detection uses `Part.assembly` flag only
4. Created 12 comprehensive unit tests for `categorize_part()` covering:
   - All 8 category types (TLA, Internal Fab, Purchased Assy, CtL, Coml, Fab, Assy, Other)
   - Priority order verification
   - Edge cases (empty defaults, category hierarchies)
   - Fallback behavior
5. All 27 tests pass (15 + 12 new)
6. Committed both cleanup and tests separately

**What We Learned:**
- Reviewing code before testing reveals opportunities for cleanup
- Removing unused code makes testing clearer and simpler
- Complex functions with many conditionals need tests for each path
- Good test names document the expected behavior
- Testing reveals what the code actually does vs. what comments say

**Next Steps:**
- Update refactor plan with completed work
- Consider frontend testing or more backend functions
- Look for other cleanup opportunities revealed by testing

---
**Tips:**
- Ask for advice or code review at any step
- Don’t try to do everything at once—small, tested steps are best
- Use this plan as a living document: update as you go

---

_Last updated: 2025-12-14_
