---
name: optimalize
description: Analyzes the codebase for performance, memory, and structural optimizations. Before applying changes, it interviews ("grills") the user to confirm their preference among trade-offs.
---

# Role: Performance Optimization Specialist

When `/optimalize` is triggered, evaluate the project's source code for performance, memory, and structural efficiency enhancements.

## Execution Workflow:
1. **Optimization Analysis (Excluding `vendor/`, `node_modules/`, `packages/`):**
   - Identify memory leaks, $O(n^2)$ complexity bottlenecks, redundant database queries, unmemoized renders, or unindexed lookups.
2. **Interactive Preference Grill (Mandatory Step):**
   - **Do not apply fixes immediately.** Present optimization strategies to the user using an interactive Q&A approach (e.g., `/grill-me` style).
   - Lay out available options, comparing trade-offs (e.g., Memory Overhead vs. Compute Speed, Code Readability vs. Micro-optimization, Client-side vs. Server-side processing).
   - Ask clarifying questions to determine the user's specific architectural goals and constraints.
3. **Execution:** Once the user selects their preferred approach, implement the optimization cleanly across the codebase.
