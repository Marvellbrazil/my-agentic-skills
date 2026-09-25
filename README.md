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
| I18n | `/i18n` | Internationalizes a project across language tags, date/time/time-zone/calendar formats, numbers and currency, RTL and BiDi, pluralization and ICU messages, collation and sorting, Unicode text processing, cultural adaptation, and localization QA. Scopable to selected aspects or languages. |
| S13n | `/s13n` | Standardizes a project: detects where the same concern is solved in divergent ways across files, asks which variant is canonical when the repo does not already answer it, then normalizes the code and adds a lint guard so the divergence cannot return. |
| Summarize | `/summarize` | Produces a structured execution summary of the session: actions taken, issues with root causes, changes made, verification evidence, known gaps, and ordered follow-up. |
| Conventional Commit | `/conventional-commit` | Commits staged work following the Conventional Commits spec, splitting a large working tree into atomic commits. Scopes only when the change is localized, `!` only for a real breaking point. Never adds a co-author trailer. |
| Conventional Commit With Coauthor | `/conventional-commit-with-coauthor` | Same as Conventional Commit, but appends a co-author trailer crediting the agent — resolved from a real identity, never fabricated. Omits the trailer when no agent identity exists. |
| Ping | `/ping` | Health-checks the session and replies `pong` with measured tool round-trip latency, host facts, and clock skew. Reports failures instead of inventing numbers. |

## Active Skills Index

The primary collection of 61 active skills maintained in `skills/`, organized by concern:

### Core Workflow & Lifecycle

| Skill Name | Command | Description |
| --- | --- | --- |
| Brainstorm | `/brainstorm` | Reads the designated project files, analyzes the architecture, and triggers an interactive session to extract user preferences before writing code. |
| Explore | `/explore` | Explores a codebase to build a complete, evidence-backed model of the project — architecture, module boundaries, entry points, data flow, conventions... |
| Handoff | `/handoff` | Compact the current conversation into a handoff document for another agent to pick up. |
| Implement | `/implement` | Implement a piece of work based on a spec or set of tickets. |
| Ping | `/ping` | Health-checks the agent session and reports a "pong" with measured tool round-trip latency, host facts, and clock skew. |
| Prototype | `/prototype` | Build a throwaway prototype to answer a design question. |
| Research | `/research` | Investigate a question against high-trust primary sources and capture the findings as a Markdown file in the repo. |
| Resolve Till Done | `/resolve-till-done` | Initiates an extended autonomous execution loop. |
| Retro | `/retro` | Conduct a retrospective on a coding session. |
| Summarize | `/summarize` | Produces a structured execution summary of the current session — every action taken, issues found with their root causes, the solutions implemented... |
| Technical Change Tracker | `/technical-change-tracker` | Track code changes with structured JSON records, state machine enforcement, and AI session handoff for bot continuity |
| Triage | `/triage` | Move issues and external PRs through a state machine of triage roles, categorise, verify, grill if needed, and write agent-ready briefs. |

### Git & Version Control

| Skill Name | Command | Description |
| --- | --- | --- |
| Conventional Commit | `/conventional-commit` | Commits staged work using the Conventional Commits specification, splitting a large working tree into multiple atomic commits with short imperative subjects... |
| Conventional Commit With Coauthor | `/conventional-commit-with-coauthor` | Commits staged work using the Conventional Commits specification and appends a co-author trailer crediting the agent, splitting a large working tree into... |
| Git Guardrails Claude Code | `/git-guardrails-claude-code` | Set up Claude Code hooks to block dangerous git commands (push, reset --hard, clean, branch -D, etc.) before they execute. |
| PR | `/pr` | Use when writing a PR body. |
| Resolving Merge Conflicts | `/resolving-merge-conflicts` | Use when you need to resolve an in-progress git merge/rebase conflict. |
| Setup Pre Commit | `/setup-pre-commit` | Set up Husky pre-commit hooks with lint-staged (Prettier), type checking, and tests in the current repo. |

### Standards, Hygiene & Refactoring

| Skill Name | Command | Description |
| --- | --- | --- |
| Clean | `/clean` | Scans the repository for code smells, dead code, formatting inconsistencies, and clutter across all user source files, outputting refactored and maintainable... |
| Full Output Enforcement | `/full-output-enforcement` | Overrides default LLM truncation behavior. |
| I18n | `/i18n` | Internationalizes a project across language tags and negotiation, dates/times/time zones/calendars, numbers and currency, bidirectional text and RTL layout... |
| Modularize | `/modularize` | Restructures monolithic files and tightly coupled functions into modular, decoupled components adhering to the Single Responsibility Principle (SRP). |
| No Comment | `/no-comment` | No comments were writed while writing the code |
| Optimalize | `/optimalize` | Analyzes the codebase for performance, memory, and structural optimizations. |
| Performance Optimizer | `/performance-optimizer` | Identifies and fixes performance bottlenecks in code, databases, and APIs. |
| S13n | `/s13n` | Standardizes a project by detecting where the same concern is solved in divergent ways across files, asking the user which variant is canonical when the... |

### Code Review, Testing & Bug Hunting

| Skill Name | Command | Description |
| --- | --- | --- |
| BDD | `/bdd` | Executes development tasks using Behavior-Driven Development methodologies, establishing human-readable business specs (Gherkin syntax) prior to implementation. |
| Brooks Lint | `/brooks-lint` | AI code reviewer grounded in classic software engineering books for catching design smells, coupling issues, and architectural risks. |
| Bug Hunter | `/bug-hunter` | Systematically finds and fixes bugs using proven debugging techniques. |
| Code Review | `/code-review` | Review the changes since a fixed point (commit, branch, tag, or merge-base) along two axes: Standards (does the code follow this repo's documented coding... |
| Codebase Audit Pre Push | `/codebase-audit-pre-push` | Deep audit before GitHub push: removes junk files, dead code, security holes, and optimization issues. |
| Diagnosing Bugs | `/diagnosing-bugs` | Diagnosis loop for hard bugs and performance regressions. |
| Logic Lens | `/logic-lens` | AI-powered Claude Code skill that performs deep code review using formal logic and reasoning frameworks to detect bugs, anti-patterns, and security risks... |
| TDD | `/tdd` | Test-driven development. |

### Architecture & System Design

| Skill Name | Command | Description |
| --- | --- | --- |
| API Endpoint Builder | `/api-endpoint-builder` | Builds production-ready REST API endpoints with validation, error handling, authentication, and documentation. |
| Codebase Design | `/codebase-design` | Shared vocabulary for designing deep modules. |
| Composition Patterns | `/composition-patterns` | --- |
| DDD | `/ddd` | Enforces Domain-Driven Design principles across all implementation tasks, structuring code around Ubiquitous Language, Bounded Contexts, Aggregates, Entities... |
| Domain Modeling | `/domain-modeling` | Build and sharpen a project's domain model. |
| Frontend API Integration Patterns | `/frontend-api-integration-patterns` | Production-ready patterns for integrating frontend applications with backend APIs, including race condition handling, request cancellation, retry strategies... |
| Improve Codebase Architecture | `/improve-codebase-architecture` | Scan a codebase for deepening opportunities, present them as a visual HTML report, then grill through whichever one you pick. |

### Frontend Craft & Design Systems

| Skill Name | Command | Description |
| --- | --- | --- |
| Design It | `/design-it` | Routes frontend design tasks to 48 specific UI styles. |
| Design Taste Frontend | `/design-taste-frontend` | Anti-slop frontend skill for landing pages, portfolios, and redesigns. |
| Emil Design Eng | `/emil-design-eng` | Use when designing or reviewing polished product UI with Emil Kowalski-inspired animation, interaction, and component craft guidance. |
| GPT Taste | `/gpt-taste` | Elite UX/UI & Advanced GSAP Motion Engineer. |
| High End Visual Design | `/high-end-visual-design` | Teaches the AI to design like a high-end agency. |

### Anti-Slop, Writing & Token Compression

| Skill Name | Command | Description |
| --- | --- | --- |
| Antislop | `/antislop` | Anti Slop: Rules for AI Coding Agents. |
| Antislop Code | `/antislop-code` | Code comment hygiene for AI coding agents: remove generic AI-slop comments, keep the valuable ones, never touch the code. |
| Caveman | `/caveman` | Ultra-compressed communication mode. |
| Unslop | `/unslop` | Cut AI tells from any writing. |
| Writing For Agents | `/writing-for-agents` | Writing documents for agents. |
| Writing Guidelines | `/writing-guidelines` | Review docs/prose for Writing Guidelines compliance. |

### Framework Best Practices

| Skill Name | Command | Description |
| --- | --- | --- |
| Astro | `/astro` | Build content-focused websites with Astro — zero JS by default, islands architecture, multi-framework components, and Markdown/MDX support. |
| Hono | `/hono` | Build ultra-fast web APIs and full-stack apps with Hono — runs on Cloudflare Workers, Deno, Bun, Node.js, and any WinterCG-compatible runtime. |
| React Best Practices | `/react-best-practices` | React and Next.js performance optimization guidelines from Vercel Engineering. |
| React Native Skills | `/react-native-skills` | --- |

### Security & Essential Utilities

| Skill Name | Command | Description |
| --- | --- | --- |
| Context7 MCP | `/context7-mcp` | This skill should be used when the user asks about libraries, frameworks, API references, or needs code examples. |
| Credentials | `/credentials` | Instructions for handling API keys and credentials safely, verifying their presence, and prompting the user to add them if missing using a safe protocol. |
| jq | `/jq` | Expert jq usage for JSON querying, filtering, transformation, and pipeline integration. |
| Security Audit | `/security-audit` | Security guidance and vulnerability review for codebases, APIs, services, CLI tools, libraries, and daemons. |
| Vulnr | `/vulnr` | Conducts a static security code audit across the project to identify potential security vulnerabilities, summarizes findings, interviews the user regarding... |

## Archived & Specialized Skills

To keep the core developer experience fast, uncluttered, and maintainable, 95 specialized
and niche skills have been organized into the `archive/` directory:

| Category | Scope |
| --- | --- |
| Bioinformatics & Science (`archive/bioinformatics/`) | 35 skills covering molecular biology, genetics, clinical trials, and chemical structures (AlphaFold, ChEMBL, PDB, Ensembl, PubMed, BLAST, etc.). |
| Specialized Frameworks & Presets (`archive/specialized-frameworks/`) | 17 framework guides, asset generators, and standalone UI presets (SvelteKit, Fumadocs, Rayden, Stitch, etc.). Note: 48 visual styles are bundled directly under `/design-it`. |
| Niche Tools & Utilities (`archive/niche-tools/`) | 13 environment-specific CLI tools, multiplexers, and generators (tmux, uv, Android CLI, python-pptx, etc.). |
| Writing & Tone Variations (`archive/writing-variations/`) | 13 sub-variants of antislop, caveman, and prose composition (writing-beats, cavecrew, antislop-human, etc.). Core discipline is maintained by `antislop` and `caveman`. |
| Workflow Aliases & Experimental (`archive/workflow-aliases-and-extras/`) | 17 conversational wrappers, setup assistants, and specialized dispatchers (grill-me, to-spec, to-tickets, etc.). |

> **Note on UI Styles**: The 48 standalone UI aesthetic skills have been consolidated under
> `/design-it`. Run `/design-it <style>` (e.g. `/design-it brutalism` or `/design-it bento-ui`)
> to invoke any of the 48 visual design presets without cluttering the global skill list.

## Repository Layout

```text
.
├── .github/workflows/
│   └── skill-scan.yml            # Automated SkillSpector security gate
├── scripts/
│   └── scan-skills.sh            # Parallel batch scanner for skills
├── skills/                       # 61 Main Active Skills
│   ├── explore/
│   ├── i18n/
│   │   ├── SKILL.md
│   │   └── references/           # 9 domain reference modules
│   ├── s13n/
│   │   ├── SKILL.md
│   │   └── references/           # 17 language & standard modules
│   └── ...
├── archive/                      # 95 Archived / Specialized Skills
│   ├── bioinformatics/           # 35 scientific databases & tools
│   ├── niche-tools/              # 13 CLI wrappers & utilities
│   ├── specialized-frameworks/   # 17 framework guides & generators
│   ├── workflow-aliases-and-extras/# 17 aliases & dispatchers
│   └── writing-variations/       # 13 writing tone sub-variants
└── README.md
```

## License

See [MIT](LICENSE).

