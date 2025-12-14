# Refactor Plan: FlatBOMGenerator Panel.tsx

## Goal
Refactor and optimize the large, complex `Panel.tsx` file by breaking it into logical, reusable components and hooks, improving code organization, and applying Mantine/React best practices. This will make the codebase easier to maintain, test, and extend, especially for users with limited frontend experience.

## Steps

### 1. Identify and Extract Logical Components
- Break out the DataTable, CSV export button, and settings controls into separate components in a new `components/` folder.
- Extract repeated logic (e.g., data fetching, filtering, CSV export) into custom hooks in a new `hooks/` folder.

### 2. Propose File/Folder Structure for frontend/src
- Create `components/` for UI elements (e.g., DataTable, SettingsPanel, ExportButton).
- Create `hooks/` for custom logic (e.g., useBOMData, useCSVExport).
- Keep `Panel.tsx` as a high-level container that composes these pieces.
- Example:
  - `src/components/DataTable.tsx`
  - `src/components/SettingsPanel.tsx`
  - `src/components/ExportButton.tsx`
  - `src/hooks/useBOMData.ts`
  - `src/hooks/useCSVExport.ts`
  - `src/Panel.tsx`

### 3. Apply Mantine DataTable and State Management Best Practices
- Use Mantine’s DataTable with memoized columns and rows for performance.
- Manage state with React’s `useState`/`useReducer` or a simple context if state is shared.
- Use Mantine’s form components for settings, and keep form state local to the settings component.

### 4. Improve Performance and Testability
- Memoize expensive computations (e.g., filtered/sorted data) with `useMemo`.
- Use `React.memo` for pure components.
- Write simple unit tests for hooks and components (e.g., test data fetching, CSV export logic).
- Avoid unnecessary re-renders by lifting state only when needed.

### 5. Plan for Future Extensibility
- Document component props and hook return values with TypeScript types and JSDoc.
- Keep business logic in hooks, UI in components.
- Use clear naming and folder structure to make adding new features (e.g., new export formats, settings) straightforward.

## Further Considerations
1. Should settings be global (context) or local (component state)? Recommend local unless needed elsewhere.
2. Consider splitting DataTable into smaller subcomponents if it has custom cells, toolbars, or filters.
3. Recommend starting with one component/hook at a time, testing after each extraction for confidence.
