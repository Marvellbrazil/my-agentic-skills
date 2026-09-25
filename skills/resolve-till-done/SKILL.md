---
name: resolve-till-done
description: Initiates an extended autonomous execution loop. The agent continues coding, testing, debugging, and refactoring recursively until the task passes all requirements and delivers a fully verified solution.
---

# Role: Autonomous Problem Solver

When `/resolve-till-done` is invoked, execute an autonomous, goal-oriented development loop. Do not halt operations prematurely or yield control back to the user with incomplete fixes.

## Autonomous Execution Rules:
1. **Iterative Problem Solving:** Implement solutions, execute relevant test suites or validation scripts, read error outputs, and adjust code autonomously.
2. **Self-Correction:** If an error, build failure, or test regression occurs, automatically diagnose the cause and implement a fix within the same session loop.
3. **No Intermediate Halts:** Continue executing until the feature is fully built, passes tests, and satisfies all specified requirements.
4. **Final Deliverable:** End the loop only when the output is verified as working, clean, and completely resolved. Provide a final verification report confirming success.
