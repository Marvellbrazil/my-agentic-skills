# my-agentic-skills

A curated, production-grade collection of agentic skills for Claude Code and AI coding agents.
Each active skill in `skills/` is self-contained in `SKILL.md` and designed for daily software
engineering, architecture, code quality, testing, and git operations.

Specialized vertical domains (bioinformatics, niche CLI tools, experimental variants) are
preserved in `archive/` to keep the primary distribution lightweight and focused.

## Installation

Install all active skills directly using the skills CLI:

```bash
npx skills add https://github.com/Marvellbrazil/my-agentic-skills
```

To install a specific skill:

```bash
npx skills add https://github.com/Marvellbrazil/my-agentic-skills --skill explore
```

## Security Scanning

Every active skill in this repository is continuously scanned for prompt injection, data
exfiltration, privilege escalation, and supply-chain risks with
[NVIDIA SkillSpector](https://github.com/NVIDIA/skillspector).

The automated gate runs via [`.github/workflows/skill-scan.yml`](.github/workflows/skill-scan.yml)
on every push and pull request touching `skills/`. It uploads SARIF reports to GitHub
Code Scanning, publishes a summary table to the run summary, and enforces a strict risk threshold.

Run the scan locally using `uv`:

```bash
# Install SkillSpector from git (not published on PyPI)
uv tool install git+https://github.com/NVIDIA/skillspector.git

# Scan all active skills using the parallel batch runner
bash scripts/scan-skills.sh skills
```

## Featured Skills

| Skill Name | Command | Description |
| --- | --- | --- |
| Explore | `/explore` | Read-only deep exploration of a codebase: architecture, module boundaries, entry points, data flow, conventions, standards, tooling, and CI gates, returned as a structured profile for context gaining and planning. |
| Internationalization | `/i18n` | Internationalizes a project across language tags, date/time/time-zone/calendar formats, numbers and currency, RTL and BiDi, pluralization and ICU messages, collation and sorting, Unicode text processing, cultural adaptation, and localization QA. Scopable to selected aspects or languages. |
| Standardization | `/s13n` | Standardizes a project: detects where the same concern is solved in divergent ways across files, asks which variant is canonical when the repo does not already answer it, then normalizes the code and adds a lint guard so the divergence cannot return. |
| Enhance | `/enhance` | Rewrites a raw prompt into a precise, executable specification before any work begins — surfaces blocking ambiguities, asks only the questions that change the outcome, and returns a copy-pasteable enhanced prompt with a change log. Never executes the task. |
| Explain | `/explain` | Teaches how a piece of code works: traces the flow from entry to outcome, builds a mental model with analogies and diagrams, and connects it to where the same pattern applies. Read-only. |
| Data Dummer | `/data-dummer` | Generates seed, fixture, and factory data that satisfies the real schema — dependency-ordered, locale-aware, deterministic, and idempotent. Reads the ORM or migrations before writing a line. |
| Bring Me Ideas | `/bring-me-ideas` | Researches a codebase and proposes ranked next-feature ideas, each answered in full 5W+1H form with evidence from the actual project. Read-only. |
| Summarize | `/summarize` | Produces a structured execution summary of the session: actions taken, issues with root causes, changes made, verification evidence, known gaps, and ordered follow-up. |
| Conventional Commit | `/conventional-commit` | Commits staged work following Conventional Commits, landing one commit per concern so the commit count follows the working tree, with a short subject message only (no multi-line body by default). Scopes only when localized, `!` only for a real breaking point. Never adds a co-author trailer. |
| Conventional Commit With Coauthor | `/conventional-commit-with-coauthor` | Same as Conventional Commit, one commit per concern with a short subject message, and appends a co-author trailer crediting the agent on every commit — resolved from a real identity, never fabricated. |
| Production Ready | `/production-ready` | Prepares and hardens projects for production: audits financial cost loopholes (unbounded queries, API spend runaways, missing timeouts), implements dynamic `.env` configuration, health probes, and graceful shutdown. |
| To-do List for Agents | `/todolist` | Shared daily planning and task tracking via an ephemeral root `TODOLIST.md`. Keeps user and agent aligned, prevents rabbit-hole traps, and automatically deletes itself upon full completion. |
| No Config | `/no-config` | Removes agent-facing configuration from a project — rules files, agent directories, and agent-generated docs — while preserving genuine project documentation. Inventories and confirms before deleting. |
| Ping | `/ping` | Health-checks the session and replies `pong` with measured tool round-trip latency, host facts, and clock skew. Reports failures instead of inventing numbers. |

## Active Skills Index

The primary collection of 92 active skills maintained in `skills/`, organized by concern:

### Core Workflow & Lifecycle

| Skill Name | Command | Description |
| --- | --- | --- |
| Brainstorm | `/brainstorm` | Reads the designated project files, analyzes the architecture, and triggers an interactive session to extract user preferences before writing code. |
| Bring Me Ideas | `/bring-me-ideas` | Researches a codebase and proposes ranked next-feature ideas, each answered in full 5W+1H form (what problem, who benefits, when it matters, where it lives in... |
| Doubt Driven Development | `/doubt-driven-development` | Subjects every non-trivial decision to a fresh-context adversarial review before it stands. |
| Enhance | `/enhance` | Rewrites a user's raw prompt into a precise, unambiguous specification before any work begins — surfacing what is missing, asking only the questions that... |
| Explain | `/explain` | Teaches how a piece of code works — tracing the flow from entry to outcome, building a mental model with analogies, drawing a diagram, and connecting it to... |
| Explore | `/explore` | Explores a codebase to build a complete, evidence-backed model of the project — architecture, module boundaries, entry points, data flow, conventions... |
| Handoff | `/handoff` | Compact the current conversation into a handoff document for another agent to pick up. |
| Idea Refine | `/idea-refine` | Refines raw ideas into sharp, actionable concepts through structured divergent and convergent thinking. |
| Implement | `/implement` | Implement a piece of work based on a spec or set of tickets. |
| Incremental Implementation | `/incremental-implementation` | Delivers changes incrementally in thin, verifiable slices. |
| Interview Me | `/interview-me` | Extracts what the user actually wants instead of what they think they should want. |
| Ping | `/ping` | Health-checks the agent session and reports a "pong" with measured tool round-trip latency, host facts, and clock skew. |
| Planning And Task Breakdown | `/planning-and-task-breakdown` | Breaks work into ordered tasks. |
| Prototype | `/prototype` | Build a throwaway prototype to answer a design question. |
| Research | `/research` | Investigate a question against high-trust primary sources and capture the findings as a Markdown file in the repo. |
| Resolve Till Done | `/resolve-till-done` | Initiates an extended autonomous execution loop. |
| Retro | `/retro` | Conduct a retrospective on a coding session. |
| Shipping And Launch | `/shipping-and-launch` | Prepares production launches. |
| Skill Ship | `/skill-ship` | Ships changed skills from this repository in one ordered pass — runs the SkillSpector security gate, regenerates the README skill index and counts, syncs... |
| Source Driven Development | `/source-driven-development` | Grounds every implementation decision in official documentation. |
| Spec Driven Development | `/spec-driven-development` | Creates specs before coding. |
| Summarize | `/summarize` | Produces a structured execution summary of the current session — every action taken, issues found with their root causes, the solutions implemented... |
| Technical Change Tracker | `/technical-change-tracker` | Track code changes with structured JSON records, state machine enforcement, and AI session handoff for bot continuity |
| To-do List for Agents | `/todolist` | Shared daily planning and task tracking via an ephemeral root `TODOLIST.md`, preventing rabbit-hole traps and automatically deleting upon completion. |
| Triage | `/triage` | Move issues and external PRs through a state machine of triage roles, categorise, verify, grill if needed, and write agent-ready briefs. |

### Git & Version Control

| Skill Name | Command | Description |
| --- | --- | --- |
| CI/CD and Automation | `/ci-cd-and-automation` | Automates CI/CD pipeline setup. |
| Conventional Commit | `/conventional-commit` | Commits staged work using the Conventional Commits specification, landing one commit per concern with a short message and no body by default... |
| Conventional Commit With Coauthor | `/conventional-commit-with-coauthor` | Commits staged work using the Conventional Commits specification, one commit per concern with a short message, and appends a co-author trailer crediting the agent... |
| Git Guardrails Claude Code | `/git-guardrails-claude-code` | Set up Claude Code hooks to block dangerous git commands (push, reset --hard, clean, branch -D, etc.) before they execute. |
| Git Workflow And Versioning | `/git-workflow-and-versioning` | Structures git workflow practices. |
| PR | `/pr` | Use when writing a PR body. |
| Resolving Merge Conflicts | `/resolving-merge-conflicts` | Use when you need to resolve an in-progress git merge/rebase conflict. |
| Setup Pre Commit | `/setup-pre-commit` | Set up Husky pre-commit hooks with lint-staged (Prettier), type checking, and tests in the current repo. |

### Standards, Hygiene & Refactoring

| Skill Name | Command | Description |
| --- | --- | --- |
| Code Simplification | `/code-simplification` | Simplifies code for clarity. |
| Constraint Driven Development | `/constraint-driven-development` | Establishes a project's quality bar as a written contract and stops agents quietly lowering it. |
| Full Output Enforcement | `/full-output-enforcement` | Overrides default LLM truncation behavior. |
| Internationalization | `/i18n` | Internationalizes a project across language tags and negotiation, dates/times/time zones/calendars, numbers and currency, bidirectional text and RTL layout... |
| Modularize | `/modularize` | Restructures monolithic files and tightly coupled functions into modular, decoupled components adhering to the Single Responsibility Principle (SRP). |
| No Comment | `/no-comment` | No comments were writed while writing the code |
| No Config | `/no-config` | Removes agent-facing configuration artifacts from a project — rules files (AGENTS.md, CLAUDE.md, GEMINI.md, .cursorrules), agent directories (.claude/... |
| Performance Optimization | `/performance-optimization` | Optimizes application performance across frontend, backend, queries, and databases. |
| Standardization | `/s13n` | Standardizes a project by detecting where the same concern is solved in divergent ways across files, asking the user which variant is canonical when the... |

### Code Review, Testing & Bug Hunting

| Skill Name | Command | Description |
| --- | --- | --- |
| BDD | `/bdd` | Executes development tasks using Behavior-Driven Development methodologies, establishing human-readable business specs (Gherkin syntax) prior to implementation. |
| Brooks Lint | `/brooks-lint` | AI code reviewer grounded in classic software engineering books for catching design smells, coupling issues, and architectural risks. |
| Browser Testing With Devtools | `/browser-testing-with-devtools` | Tests in real browsers via Chrome DevTools MCP. |
| Code Review And Quality | `/code-review-and-quality` | Conducts multi-axis code review. |
| Codebase Audit Pre Push | `/codebase-audit-pre-push` | Deep audit before GitHub push: removes junk files, dead code, security holes, and optimization issues. |
| Data Dummer | `/data-dummer` | Generates seed, fixture, and factory data that satisfies the project's real schema — reading the ORM or migrations first, respecting foreign keys and... |
| Debugging And Error Recovery | `/debugging-and-error-recovery` | Guides systematic root-cause debugging. |
| Diagnosing Bugs | `/diagnosing-bugs` | Diagnosis loop for hard bugs and performance regressions. |
| Logic Lens | `/logic-lens` | AI-powered Claude Code skill that performs deep code review using formal logic and reasoning frameworks to detect bugs, anti-patterns, and security risks... |
| TDD | `/tdd` | Drives development with tests using the red-green-refactor loop. Test first, make it pass, clean up, and guard regressions. |

### Architecture, API & System Design

| Skill Name | Command | Description |
| --- | --- | --- |
| API And Interface Design | `/api-and-interface-design` | Guides stable API and interface design. |
| API Endpoint Builder | `/api-endpoint-builder` | Builds production-ready REST API endpoints with validation, error handling, authentication, and documentation. |
| Codebase Design | `/codebase-design` | Shared vocabulary for designing deep modules. |
| Composition Patterns | `/composition-patterns` | React composition patterns that scale. |
| DDD | `/ddd` | Enforces Domain-Driven Design principles across all implementation tasks, structuring code around Ubiquitous Language, Bounded Contexts, Aggregates, Entities... |
| Deprecation And Migration | `/deprecation-and-migration` | Manages deprecation and migration. |
| Documentation and ADRs | `/documentation-and-adrs` | Records decisions and documentation. |
| Domain Modeling | `/domain-modeling` | Build and sharpen a project's domain model. |
| Frontend API Integration Patterns | `/frontend-api-integration-patterns` | Production-ready patterns for integrating frontend applications with backend APIs, including race condition handling, request cancellation, retry strategies... |
| Improve Codebase Architecture | `/improve-codebase-architecture` | Scan a codebase for deepening opportunities, present them as a visual HTML report, then grill through whichever one you pick. |
| Production Ready | `/production-ready` | Prepares and hardens projects for production: audits financial cost loopholes, implements dynamic `.env` configuration, health probes, and graceful shutdown. |

### Frontend Craft & UI Systems

| Skill Name | Command | Description |
| --- | --- | --- |
| Design It | `/design-it` | Routes frontend design tasks to 48 specific UI styles. |
| Design Taste Frontend | `/design-taste-frontend` | Anti-slop frontend skill for landing pages, portfolios, and redesigns. |
| Emil Design Eng | `/emil-design-eng` | Use when designing or reviewing polished product UI with Emil Kowalski-inspired animation, interaction, and component craft guidance. |
| Frontend UI Engineering | `/frontend-ui-engineering` | Builds production-quality, accessible, responsive user-facing UIs. |
| GPT Taste | `/gpt-taste` | Elite UX/UI & Advanced GSAP Motion Engineer. |
| High End Visual Design | `/high-end-visual-design` | Teaches the AI to design like a high-end agency. |
| Web Perf | `/web-perf` | Analyzes web performance using Chrome DevTools MCP. |

### Anti-Slop, Writing & Token Compression

| Skill Name | Command | Description |
| --- | --- | --- |
| Anti-Slop | `/anti-slop` | Comprehensive toolkit for detecting and eliminating "AI slop" - generic, low-quality AI-generated patterns in natural language, code, and design. |
| Antislop | `/antislop` | Anti Slop: Rules for AI Coding Agents. |
| Antislop Code | `/antislop-code` | Code comment hygiene for AI coding agents: remove generic AI-slop comments, keep the valuable ones, never touch the code. |
| Caveman | `/caveman` | Ultra-compressed communication mode. |
| Context Engineering | `/context-engineering` | Optimizes agent context setup. |
| Writing For Agents | `/writing-for-agents` | Writing documents for agents. |
| Writing Guidelines | `/writing-guidelines` | Review docs/prose for Writing Guidelines compliance. |

### Frameworks & Edge Ecosystem

| Skill Name | Command | Description |
| --- | --- | --- |
| Astro | `/astro` | Build content-focused websites with Astro — zero JS by default, islands architecture, multi-framework components, and Markdown/MDX support. |
| Cloudflare | `/cloudflare` | Comprehensive Cloudflare platform skill covering Workers, Pages, storage (KV, D1, R2), AI (Workers AI, Vectorize, Agents SDK), feature flags (Flagship)... |
| Hono | `/hono` | Build ultra-fast web APIs and full-stack apps with Hono — runs on Cloudflare Workers, Deno, Bun, Node.js, and any WinterCG-compatible runtime. |
| React Best Practices | `/react-best-practices` | React and Next.js performance optimization guidelines from Vercel Engineering. |
| React Native Skills | `/react-native-skills` | React Native and Expo best practices for building performant mobile apps. |
| Workers Best Practices | `/workers-best-practices` | Reviews and authors Cloudflare Workers code against production best practices. |
| Wrangler | `/wrangler` | Cloudflare Workers CLI for deploying, developing, and managing Workers, KV, R2, D1, Vectorize, Hyperdrive, Workers AI, Containers, Queues, Workflows... |

### Security & Developer Tooling

| Skill Name | Command | Description |
| --- | --- | --- |
| Context7 MCP | `/context7-mcp` | This skill should be used when the user asks about libraries, frameworks, API references, or needs code examples. |
| Credentials | `/credentials` | Instructions for handling API keys and credentials safely, verifying their presence, and prompting the user to add them if missing using a safe protocol. |
| Find Skills | `/find-skills` | Helps users discover and install agent skills when they ask questions like "how do I do X", "find a skill for X", "is there a skill that can...", or express... |
| jq | `/jq` | Expert jq usage for JSON querying, filtering, transformation, and pipeline integration. |
| Observability And Instrumentation | `/observability-and-instrumentation` | Instruments code so production behavior is visible and diagnosable. |
| Security And Hardening | `/security-and-hardening` | Hardens code against vulnerabilities. |
| Security Audit | `/security-audit` | Security guidance and vulnerability review for codebases, APIs, services, CLI tools, libraries, and daemons. |
| Using Agent Skills | `/using-agent-skills` | Discovers and invokes agent skills. |

## Archived & Specialized Skills

To keep the core developer experience fast, uncluttered, and maintainable, 106 specialized
and niche skills have been organized into the `archive/` directory:

| Category | Scope |
| --- | --- |
| Bioinformatics & Science (`archive/bioinformatics/`) | 35 skills covering molecular biology, genetics, clinical trials, and chemical structures (AlphaFold, ChEMBL, PDB, Ensembl, PubMed, BLAST, etc.). |
| Specialized Frameworks & Presets (`archive/specialized-frameworks/`) | 24 framework guides, asset generators, and Cloudflare product plugins (SvelteKit, Durable Objects, Agents SDK, Turnstile, etc.). Note: 48 visual styles are bundled directly under `/design-it`. |
| Niche Tools & Utilities (`archive/niche-tools/`) | 16 environment-specific CLI tools, GUI automation, and multiplexers (tmux, uv, Android CLI, Computer Use, Orca CLI, Orchestration, etc.). |
| Writing & Tone Variations (`archive/writing-variations/`) | 13 sub-variants of antislop, caveman, and prose composition (writing-beats, cavecrew, antislop-human, etc.). Core discipline is maintained by `antislop`, `anti-slop`, and `caveman`. |
| Workflow Aliases & Experimental (`archive/workflow-aliases-and-extras/`) | 18 conversational wrappers, setup assistants, and specialized dispatchers (grill-me, gain-context, to-spec, to-tickets, etc.). |

> **Note on UI Styles**: The 48 standalone UI aesthetic skills have been consolidated under
> `/design-it`. Run `/design-it <style>` (e.g. `/design-it brutalism` or `/design-it bento-ui`)
> to invoke any of the 48 visual design presets without cluttering the global skill list.

## Repository Layout

```text
.
├── .github/workflows/
│   └── skill-scan.yml            # Automated SkillSpector security gate
├── scripts/
│   ├── gen-readme.py             # Regenerates the skill index and counts
│   └── scan-skills.sh            # Parallel batch scanner for skills
├── skills/                       # 92 Main Active Skills
│   ├── explore/
│   ├── i18n/
│   │   ├── SKILL.md
│   │   └── references/           # 9 domain reference modules
│   ├── production-ready/
│   │   ├── SKILL.md
│   │   └── references/           # 4 production hardening modules
│   ├── s13n/
│   │   ├── SKILL.md
│   │   └── references/           # 17 language & standard modules
│   ├── todolist/
│   │   └── SKILL.md
│   └── ...
├── archive/                      # 106 Archived / Specialized Skills
│   ├── bioinformatics/           # 35 scientific databases & tools
│   ├── niche-tools/              # 16 CLI wrappers & GUI tools
│   ├── specialized-frameworks/   # 24 framework guides & cloud plugins
│   ├── workflow-aliases-and-extras/# 18 aliases & dispatchers
│   └── writing-variations/       # 13 writing tone sub-variants
└── README.md
```

## License

See [LICENSE](LICENSE).
It is open-sourced guys, feels free to use :DD

