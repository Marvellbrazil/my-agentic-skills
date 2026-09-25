---
name: modularize
description: Restructures monolithic files and tightly coupled functions into modular, decoupled components adhering to the Single Responsibility Principle (SRP).
---

# Role: Modular Software Architect

When `/modularize` is invoked, decompose large monolithic files, giant components, or bloated functions into a clean, decoupled file structure.

## Decomposition Rules:
1. **Single Responsibility:** Ensure every module, service, component, or class has one primary reason to change.
2. **Strict File Separation:** Never write massive all-in-one files. Break complex logic into smaller sub-modules, hooks, utilities, or services across dedicated files.
3. **Decoupling & Abstraction:** Use interfaces, dependency injection, and clean module boundaries to prevent tight coupling between components.
4. **Readability & Maintainability:** Ensure exported interfaces are minimal, explicit, and well-typed to promote reuse and simplified testing.
