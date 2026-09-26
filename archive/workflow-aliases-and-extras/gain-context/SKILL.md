---
name: gain-context
description: Conducts a deep-scan analysis of the repository to extract project architecture, directory layouts, coding conventions, scripts, and dependencies for persistent session awareness.
---

# Role: Project Context Analyzer

When `/gain-context` is triggered, perform a comprehensive inspection of the entire codebase to build a complete context model before taking operational steps.

## Analysis Checklist:
1. **Directory & Module Structure:** Map key directories, entry points, and domain boundaries.
2. **Ecosystem & Configuration:** Analyze manifest files (`package.json`, `composer.json`, `docker-compose.yml`, `tsconfig.json`, `Makefile`, etc.) to discover available scripts, runtime environments, and core dependencies.
3. **Coding Standards & Patterns:** Inspect existing code snippets to identify styling conventions, naming rules, state management patterns, and architectural paradigms (e.g., MVC, Modular, Decoupled).
4. **Environment & Tooling:** Identify testing frameworks, linters, and build configurations.

## Output Directive:
- Construct an internal context memory model.
- Present a concise **Project Profile Summary** back to the user highlighting key architectural decisions, conventions, and operational workflows detected, confirming readiness for future commands.
