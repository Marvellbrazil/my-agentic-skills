---
name: clean
description: Scans the repository for code smells, dead code, formatting inconsistencies, and clutter across all user source files, outputting refactored and maintainable code.
---

# Role: Code Hygiene & Refactoring Agent

When `/clean` is invoked, perform a thorough cleanup scan across all project files.

## Scanning Scope & Rules:
1. **Exclusion List:** Strictly skip generated files, vendor/package directories (e.g., `vendor/`, `node_modules/`, `.next/`, `dist/`, `build/`).
2. **Dead Code Elimination:** Identify and remove unused variables, dead functions, obsolete imports, and commented-out code blocks.
3. **Refactoring & Standardization:**
   - Simplify overly complex conditional branching and nested logic.
   - Standardize formatting, indentation, and variable naming conventions.
   - Improve variable/function names for immediate clarity.
4. **Output:** Provide clean, refactored, maintainable source code files while ensuring zero functional regressions.
