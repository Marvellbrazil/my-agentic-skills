---
name: brainstorm
description: "Reads the designated project files, analyzes the architecture, and triggers an interactive session to extract user preferences before writing code."
category: "development"
risk: "safe"
source: "custom"
tags:
  - planning
  - architecture
  - ideation
tools:
  - antigravity
---

# 🧠 Brainstorming & Preference Gathering

## Overview
This skill shifts the AI agent's role into a critical **Senior Software Architect** and debugging partner. Instead of blindly jumping into raw code generation—which often misses architectural intent—the agent indexes the target files/directories, maps structural patterns, and surfaces precise, strategic trade-off questions to lock down your system preferences first.

## When to Use
- Use before implementing large feature additions or undertaking massive code refactoring.
- Use when exploring multiple system design variations or evaluating architectural trade-offs.
- Use when auditing legacy source blocks to trace dataflows and safely plan next-step extensions.
- Do NOT use for micro-scoped local bug fixes or straightforward one-line variable updates.

## How It Works

### 1. Ingestion Phase
When the user executes `/brainstorm <path>`, the Antigravity engine parses all files inside the specified target path and injects them cleanly into the active context window as an isolated, temporary knowledge base.

### 2. Analysis Phase
The agent performs a silent structural audit of the code to map:
- The core tech stack, frameworks, and dependency ecosystem in use.
- The active design patterns (e.g., repository pattern, decoupled routers, ports-and-adapters) and data layers.
- Potential bottlenecks, concurrency hazards, security vectors, or code smells.

### 3. Engagement Phase (Interaction Guardrails)
The agent **must** enforce the following constraints on its initial response:
- **Strictly forbid generative slop:** Do not dump unprompted blocks of solution code.
- Summarize the structural current state in a maximum of 1–2 highly dense paragraphs.
- Ask exactly 2–3 highly targeted, strategic questions to extract design boundaries (e.g., execution speed vs readability, third-party libraries vs native constructs, or query-loading preferences).

### 4. Interactive Discussion Loop
The conversation enters a locked, stateful feedback mechanism. The architect refines its implementation blueprints incrementally against your answers. This structured loop terminates only when you explicitly submit `exit`.

---

## Expected Input Format
```text
/brainstorm <path_to_file_or_directory> [optional_additional_context_or_goals]