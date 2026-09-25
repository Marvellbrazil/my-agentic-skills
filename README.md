# my-agentic-skills

A collection of agentic skills for Claude Code and other AI coding agents.
Each skill is a self-contained `SKILL.md` that teaches an agent a specific
workflow, standard, or domain. Skills with deep reference material ship a
`references/` directory that the agent loads on demand.

## Installation

```bash
npx skills add https://github.com/Marvellbrazil/my-agentic-skills
```

## Security Scanning

Every skill in this repository is scanned for prompt injection, data
exfiltration, privilege escalation, supply-chain, and other malicious patterns
by [NVIDIA SkillSpector](https://github.com/NVIDIA/skillspector) before it can
be trusted.

The scan runs automatically via
[`.github/workflows/skill-scan.yml`](.github/workflows/skill-scan.yml) on every
push and pull request that touches `skills/`, plus a weekly scheduled run. It
uploads SARIF reports to GitHub code scanning, publishes a summary to the job
summary, and fails the build when any skill exceeds the risk threshold.

Run the same scan locally with `uv`:

```bash
# Install SkillSpector (not published on PyPI — install from git)
uv tool install git+https://github.com/NVIDIA/skillspector.git

# Scan every skill and write JSON + SARIF reports to skillspector-reports/
bash scripts/scan-skills.sh skills
```

`scripts/scan-skills.sh` exists because `skillspector scan --recursive` has a
**hardcoded cap of 32 skills per invocation** with no CLI flag or environment
variable to raise it. Pointed at this repository, a single `--recursive` run
scans 32 of the 204 skills and reports the rest as omitted. The script shards the
skill directories into batches, scans them concurrently, and aggregates the
per-batch reports into `skillspector-reports/summary.md`.

Tune it with `BATCH_SIZE` (default 30, must stay under the 32 cap) and `JOBS`
(default 4, the number of concurrent scans):

```bash
BATCH_SIZE=30 JOBS=8 bash scripts/scan-skills.sh skills
```

Scan a single skill directly when iterating on one:

```bash
skillspector scan skills/i18n --no-llm
skillspector scan skills/i18n --no-llm --format json | jq '.risk_assessment'
```

`--no-llm` runs static analysis only, which needs no API key. Drop the flag to
add LLM semantic analysis; configure a provider with `SKILLSPECTOR_PROVIDER` and
the matching credential variable.

## Featured Skills

| Skill Name                        | Command                              | Description                                                                                                                                                                                                                                                                                      |
| --------------------------------- | ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Explore                           | `/explore`                           | Read-only deep exploration of a codebase: architecture, module boundaries, entry points, data flow, conventions, standards, tooling, and CI gates, returned as a structured profile for context gaining and planning.                                                                            |
| I18n                              | `/i18n`                              | Internationalizes a project across language tags, date/time/time-zone/calendar formats, numbers and currency, RTL and BiDi, pluralization and ICU messages, collation and sorting, Unicode text processing, cultural adaptation, and localization QA. Scopable to selected aspects or languages. |
| S13n                              | `/s13n`                              | Standardizes a project: detects where the same concern is solved in divergent ways across files, asks which variant is canonical when the repo does not already answer it, then normalizes the code and adds a lint guard so the divergence cannot return.                                       |
| Summarize                         | `/summarize`                         | Produces a structured execution summary of the session: actions taken, issues with root causes, changes made, verification evidence, known gaps, and ordered follow-up.                                                                                                                          |
| Conventional Commit               | `/conventional-commit`               | Commits staged work following the Conventional Commits spec, splitting a large working tree into atomic commits. Scopes only when the change is localized, `!` only for a real breaking point. Never adds a co-author trailer.                                                                   |
| Conventional Commit With Coauthor | `/conventional-commit-with-coauthor` | Same as Conventional Commit, but appends a co-author trailer crediting the agent — resolved from a real identity, never fabricated. Omits the trailer when no agent identity exists.                                                                                                             |
| Ping                              | `/ping`                              | Health-checks the session and replies `pong` with measured tool round-trip latency, host facts, and clock skew. Reports failures instead of inventing numbers.                                                                                                                                   |

## Full Skill Index

Every skill in this repository, grouped by purpose. The command is derived from
the skill directory name.

### Internationalization

| Skill Name | Command | Description                                                                                                                                             |
| ---------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| I18n       | `/i18n` | Internationalizes a project across language tags and negotiation, dates/times/time zones/calendars, numbers and currency, bidirectional text and RTL... |

### Git & Commits

| Skill Name                        | Command                              | Description                                                                                                                                             |
| --------------------------------- | ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Caveman Commit                    | `/caveman-commit`                    | Ultra-compressed commit message generator.                                                                                                              |
| Conventional Commit               | `/conventional-commit`               | Commits staged work using the Conventional Commits specification, splitting a large working tree into multiple atomic commits with short imperative...  |
| Conventional Commit With Coauthor | `/conventional-commit-with-coauthor` | Commits staged work using the Conventional Commits specification and appends a co-author trailer crediting the agent, splitting a large working tree... |
| Git Guardrails Claude Code        | `/git-guardrails-claude-code`        | Set up Claude Code hooks to block dangerous git commands (push, reset --hard, clean, branch -D, etc.) before they execute.                              |
| PR                                | `/pr`                                | Use when writing a PR body.                                                                                                                             |
| Resolving Merge Conflicts         | `/resolving-merge-conflicts`         | Use when you need to resolve an in-progress git merge/rebase conflict.                                                                                  |
| Setup Pre Commit                  | `/setup-pre-commit`                  | Set up Husky pre-commit hooks with lint-staged (Prettier), type checking, and tests in the current repo.                                                |

### Security

| Skill Name     | Command           | Description                                                                                                                                          |
| -------------- | ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| Credentials    | `/credentials`    | Instructions for handling API keys and credentials safely, verifying their presence, and prompting the user to add them if missing using a safe...   |
| Security Audit | `/security-audit` | Security guidance and vulnerability review for codebases, APIs, services, CLI tools, libraries, and daemons.                                         |
| Vulnr          | `/vulnr`          | Conducts a static security code audit across the project to identify potential security vulnerabilities, summarizes findings, interviews the user... |

### Core Workflow

| Skill Name               | Command                     | Description                                                                                                                                              |
| ------------------------ | --------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Ask Matt                 | `/ask-matt`                 | Ask which skill or flow fits your situation.                                                                                                             |
| Brainstorm               | `/brainstorm`               | Reads the designated project files, analyzes the architecture, and triggers an interactive session to extract user preferences before writing code.      |
| Claude Handoff           | `/claude-handoff`           | Hand the current conversation off to a fresh background agent that picks up the work immediately.                                                        |
| Explore                  | `/explore`                  | Explores a codebase to build a complete, evidence-backed model of the project — architecture, module boundaries, entry points, data flow...              |
| Grill Me                 | `/grill-me`                 | A relentless interview to sharpen a plan or design.                                                                                                      |
| Grill With Docs          | `/grill-with-docs`          | A relentless interview to sharpen a plan or design, which also creates docs (ADR's and glossary) as we go.                                               |
| Grilling                 | `/grilling`                 | Grill the user relentlessly about a plan, decision, or idea.                                                                                             |
| Handoff                  | `/handoff`                  | Compact the current conversation into a handoff document for another agent to pick up.                                                                   |
| Implement                | `/implement`                | Implement a piece of work based on a spec or set of tickets.                                                                                             |
| Implement Spec           | `/implement-spec`           | Implement a specification in code.                                                                                                                       |
| Loop Me                  | `/loop-me`                  | Grill me about specs for the workflows I want to build, within this workspace.                                                                           |
| Prototype                | `/prototype`                | Build a throwaway prototype to answer a design question.                                                                                                 |
| Research                 | `/research`                 | Investigate a question against high-trust primary sources and capture the findings as a Markdown file in the repo.                                       |
| Resolve Till Done        | `/resolve-till-done`        | Initiates an extended autonomous execution loop.                                                                                                         |
| Retro                    | `/retro`                    | Conduct a retrospective on a coding session.                                                                                                             |
| Scaffold Exercises       | `/scaffold-exercises`       | Create exercise directory structures with sections, problems, solutions, and explainers that pass linting.                                               |
| Setup Matt Pocock Skills | `/setup-matt-pocock-skills` | Configure this repo for the engineering skills: set up its issue tracker, triage label vocabulary, and domain doc layout.                                |
| Squirrel                 | `/squirrel`                 | Full-cycle AI coding skill: plans, builds, tests, lints, fixes bugs, and writes production-grade docs.                                                   |
| Summarize                | `/summarize`                | Produces a structured execution summary of the current session — every action taken, issues found with their root causes, the solutions implemented...   |
| Teach                    | `/teach`                    | Teach the user a new skill or concept, within this workspace.                                                                                            |
| Technical Change Tracker | `/technical-change-tracker` | Track code changes with structured JSON records, state machine enforcement, and AI session handoff for bot continuity                                    |
| To Questionnaire         | `/to-questionnaire`         | Turn a decision you can't fully answer into a questionnaire for someone else to fill in.                                                                 |
| To Spec                  | `/to-spec`                  | Turn the current conversation into a spec and publish it to the project issue tracker: no interview, just synthesis of what you've already discussed.    |
| To Tickets               | `/to-tickets`               | Break a plan, spec, or the current conversation into a set of tracer-bullet tickets, each declaring its blocking edges, published to the configured...   |
| Triage                   | `/triage`                   | Move issues and external PRs through a state machine of triage roles, categorise, verify, grill if needed, and write agent-ready briefs.                 |
| Wait What                | `/wait-what`                | Stop. That last message did not land: re-pitch it.                                                                                                       |
| Wayfinder                | `/wayfinder`                | Plan a huge chunk of work (more than one agent session can hold) as a shared map of decision tickets on your issue tracker, and resolve them one at a... |
| Wizard                   | `/wizard`                   | Generate an interactive bash wizard that walks a human through steps only they can perform.                                                              |

### Standards & Code Quality

| Skill Name                    | Command                          | Description                                                                                                                                             |
| ----------------------------- | -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| API Endpoint Builder          | `/api-endpoint-builder`          | Builds production-ready REST API endpoints with validation, error handling, authentication, and documentation.                                          |
| BDD                           | `/bdd`                           | Executes development tasks using Behavior-Driven Development methodologies, establishing human-readable business specs (Gherkin syntax) prior to...     |
| Brooks Lint                   | `/brooks-lint`                   | AI code reviewer grounded in classic software engineering books for catching design smells, coupling issues, and architectural risks.                   |
| Bug Hunter                    | `/bug-hunter`                    | Systematically finds and fixes bugs using proven debugging techniques.                                                                                  |
| Clean                         | `/clean`                         | Scans the repository for code smells, dead code, formatting inconsistencies, and clutter across all user source files, outputting refactored and...     |
| Code Review                   | `/code-review`                   | Review the changes since a fixed point (commit, branch, tag, or merge-base) along two axes: Standards (does the code follow this repo's documented...   |
| Codebase Audit Pre Push       | `/codebase-audit-pre-push`       | Deep audit before GitHub push: removes junk files, dead code, security holes, and optimization issues.                                                  |
| Codebase Design               | `/codebase-design`               | Shared vocabulary for designing deep modules.                                                                                                           |
| DDD                           | `/ddd`                           | Enforces Domain-Driven Design principles across all implementation tasks, structuring code around Ubiquitous Language, Bounded Contexts, Aggregates...  |
| Diagnosing Bugs               | `/diagnosing-bugs`               | Diagnosis loop for hard bugs and performance regressions.                                                                                               |
| Domain Modeling               | `/domain-modeling`               | Build and sharpen a project's domain model.                                                                                                             |
| Full Output Enforcement       | `/full-output-enforcement`       | Overrides default LLM truncation behavior.                                                                                                              |
| Improve Codebase Architecture | `/improve-codebase-architecture` | Scan a codebase for deepening opportunities, present them as a visual HTML report, then grill through whichever one you pick.                           |
| Logic Lens                    | `/logic-lens`                    | AI-powered Claude Code skill that performs deep code review using formal logic and reasoning frameworks to detect bugs, anti-patterns, and security...  |
| Modularize                    | `/modularize`                    | Restructures monolithic files and tightly coupled functions into modular, decoupled components adhering to the Single Responsibility Principle (SRP).   |
| No Comment                    | `/no-comment`                    | No comments were writed while writing the code                                                                                                          |
| Optimalize                    | `/optimalize`                    | Analyzes the codebase for performance, memory, and structural optimizations.                                                                            |
| Performance Optimizer         | `/performance-optimizer`         | Identifies and fixes performance bottlenecks in code, databases, and APIs.                                                                              |
| S13n                          | `/s13n`                          | Standardizes a project by detecting where the same concern is solved in divergent ways across files, asking the user which variant is canonical when... |
| Setup TS Deep Modules         | `/setup-ts-deep-modules`         | Wire dependency-cruiser into a TypeScript repo so each package is a deep module, with implementation hidden in subfolders and reachable only through... |
| TDD                           | `/tdd`                           | Test-driven development.                                                                                                                                |
| Writing Guidelines            | `/writing-guidelines`            | Review docs/prose for Writing Guidelines compliance.                                                                                                    |

### Agent & Skill Authoring

| Skill Name             | Command                   | Description                                                                                                                                       |
| ---------------------- | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| ECL Harness Engineer   | `/ecl-harness-engineer`   | Create or audit ECL Agent Harness infrastructure: AGENTS.md, change tracking, repository guidance, lint checks, CI gates, and agent handoff docs. |
| Skill Check            | `/skill-check`            | Validate Claude Code skills against the agentskills specification.                                                                                |
| Workflow Skill Creator | `/workflow_skill_creator` | Distills a completed user workflow or interaction into a reusable agent skill.                                                                    |
| Writing For Agents     | `/writing-for-agents`     | Writing documents for agents.                                                                                                                     |

### Writing & Compression

| Skill Name            | Command                  | Description                                                                                                               |
| --------------------- | ------------------------ | ------------------------------------------------------------------------------------------------------------------------- |
| Antislop              | `/antislop`              | Anti Slop: Rules for AI Coding Agents.                                                                                    |
| Antislop Code         | `/antislop-code`         | Code comment hygiene for AI coding agents: remove generic AI-slop comments, keep the valuable ones, never touch the code. |
| Antislop Copywriting  | `/antislop-copywriting`  | Copy and text skill for antislop.                                                                                         |
| Antislop Human        | `/antislop-human`        | Human and accessibility skill for antislop.                                                                               |
| Antislop Layoutmobile | `/antislop-layoutmobile` | Mobile layout skill for antislop.                                                                                         |
| Antislop UI           | `/antislop-ui`           | UI and visual skill for antislop.                                                                                         |
| Cavecrew              | `/cavecrew`              | Decision guide for delegating to caveman-style subagents.                                                                 |
| Caveman               | `/caveman`               | Ultra-compressed communication mode.                                                                                      |
| Caveman Compress      | `/caveman-compress`      | Compress natural language memory files (CLAUDE.md, todos, preferences) into caveman format to save input tokens.          |
| Caveman Help          | `/caveman-help`          | Quick-reference card for all caveman modes, skills, and commands.                                                         |
| Caveman Review        | `/caveman-review`        | Ultra-compressed code review comments.                                                                                    |
| Caveman Stats         | `/caveman-stats`         | Show real token usage and estimated savings for the current session.                                                      |
| Unslop                | `/unslop`                | Cut AI tells from any writing.                                                                                            |
| Writing Beats         | `/writing-beats`         | Writing, exploit; assemble raw material into a journey of beats, grounding each term before a beat leans on it.           |
| Writing Fragments     | `/writing-fragments`     | Writing, explore: mine raw fragments, no structure yet.                                                                   |
| Writing Shape         | `/writing-shape`         | Writing, exploit: shape raw material into an article, paragraph by paragraph.                                             |

### Design & UI

| Skill Name                 | Command                       | Description                                                                                                                                           |
| -------------------------- | ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| 3D UI                      | `/3d-ui`                      | Web and App implementation guide for 3D UI.                                                                                                           |
| AI Native UI               | `/ai-native-ui`               | Web and App implementation guide for AI Native UI.                                                                                                    |
| Aurora UI                  | `/aurora-ui`                  | Web and App implementation guide for Aurora UI.                                                                                                       |
| Bento UI                   | `/bento-ui`                   | Web and App implementation guide for Bento UI.                                                                                                        |
| Brandkit                   | `/brandkit`                   | Premium brand-kit image generation skill for creating high-end brand-guidelines boards, logo systems, identity decks, and visual-world presentations. |
| Brutalism                  | `/brutalism`                  | Web and App implementation guide for Brutalism.                                                                                                       |
| Brutalist Typography       | `/brutalist-typography`       | Web and App implementation guide for Brutalist Typography.                                                                                            |
| Card Based Design          | `/card-based-design`          | Web and App implementation guide for Card-Based Design.                                                                                               |
| Claymorphism               | `/claymorphism`               | Web and App implementation guide for Claymorphism.                                                                                                    |
| Color Blocking             | `/color-blocking`             | Web and App implementation guide for Color Blocking.                                                                                                  |
| Command Center UI          | `/command-center-ui`          | Web and App implementation guide for Command Center UI.                                                                                               |
| Cyber Y2K                  | `/cyber-y2k`                  | Web and App implementation guide for Cyber Y2K.                                                                                                       |
| Cyberpunk UI               | `/cyberpunk-ui`               | Web and App implementation guide for Cyberpunk UI.                                                                                                    |
| Dark Mode                  | `/dark-mode`                  | Web and App implementation guide for Dark Mode Design.                                                                                                |
| Dashboard Design           | `/dashboard-design`           | Web and App implementation guide for Dashboard Design.                                                                                                |
| Data Dense Design          | `/data-dense-design`          | Web and App implementation guide for Data-Dense Design.                                                                                               |
| Design It                  | `/design-it`                  | Routes frontend design tasks to 48 specific UI styles.                                                                                                |
| Design Taste Frontend      | `/design-taste-frontend`      | Anti-slop frontend skill for landing pages, portfolios, and redesigns.                                                                                |
| Design Taste Frontend V1   | `/design-taste-frontend-v1`   | The original v1 taste-skill, preserved for projects depending on its exact behavior.                                                                  |
| Duotone Design             | `/duotone-design`             | Web and App implementation guide for Duotone Design.                                                                                                  |
| Editorial Design           | `/editorial-design`           | Web and App implementation guide for Editorial Design.                                                                                                |
| Emil Design Eng            | `/emil-design-eng`            | Use when designing or reviewing polished product UI with Emil Kowalski-inspired animation, interaction, and component craft guidance.                 |
| Flat Design                | `/flat-design`                | Web and App implementation guide for the Flat Design style.                                                                                           |
| Flat Design 2              | `/flat-design-2`              | Web and App implementation guide for Flat Design 2.0 (Semi-Flat).                                                                                     |
| Floating UI                | `/floating-ui`                | Web and App implementation guide for Floating UI.                                                                                                     |
| Frutiger Aero              | `/frutiger-aero`              | Web and App implementation guide for Frutiger Aero.                                                                                                   |
| Glassmorphism              | `/glassmorphism`              | Web and App implementation guide for Glassmorphism.                                                                                                   |
| GPT Taste                  | `/gpt-taste`                  | Elite UX/UI & Advanced GSAP Motion Engineer.                                                                                                          |
| Gradient Design            | `/gradient-design`            | Web and App implementation guide for Gradient Design.                                                                                                 |
| High Contrast              | `/high-contrast`              | Web and App implementation guide for High Contrast Design.                                                                                            |
| High End Visual Design     | `/high-end-visual-design`     | Teaches the AI to design like a high-end agency.                                                                                                      |
| Holographic UI             | `/holographic-ui`             | Web and App implementation guide for Holographic UI.                                                                                                  |
| Industrial Brutalist UI    | `/industrial-brutalist-ui`    | Raw mechanical interfaces fusing Swiss typographic print with military terminal aesthetics.                                                           |
| Isometric Design           | `/isometric-design`           | Web and App implementation guide for Isometric Design.                                                                                                |
| Layered Design             | `/layered-design`             | Web and App implementation guide for Layered Design.                                                                                                  |
| Material Design            | `/material-design`            | Web and App implementation guide for Material Design.                                                                                                 |
| Maximalism                 | `/maximalism`                 | Web and App implementation guide for Controlled Maximalism.                                                                                           |
| Minimalism                 | `/minimalism`                 | Web and App implementation guide for the Minimalism design style.                                                                                     |
| Minimalist UI              | `/minimalist-ui`              | Clean editorial-style interfaces.                                                                                                                     |
| Monochromatic UI           | `/monochromatic-ui`           | Web and App implementation guide for Monochromatic UI.                                                                                                |
| Neo Brutalism              | `/neo-brutalism`              | Web and App implementation guide for Neo-Brutalism.                                                                                                   |
| Neumorphism                | `/neumorphism`                | Web and App implementation guide for Neumorphism (Soft UI).                                                                                           |
| Premium 3D Website         | `/premium-3d-website`         | Guidelines for building premium 3D websites, focusing on custom WebGL shaders, post-processing, physics-based interactions, smooth animations...      |
| Redesign Existing Projects | `/redesign-existing-projects` | Upgrades existing websites and apps to premium quality.                                                                                               |
| Retro Design               | `/retro-design`               | Web and App implementation guide for Retro Design (60s-80s).                                                                                          |
| Retro Futurism             | `/retro-futurism`             | Web and App implementation guide for Retro Futurism.                                                                                                  |
| Sci Fi Interface           | `/sci-fi-interface`           | Web and App implementation guide for Sci-Fi Interface Design.                                                                                         |
| Skeuomorphism              | `/skeuomorphism`              | Web and App implementation guide for Skeuomorphism.                                                                                                   |
| Soft Pastel                | `/soft-pastel`                | Web and App implementation guide for Soft Pastel Design.                                                                                              |
| Spatial Computing UI       | `/spatial-computing-ui`       | Web and App implementation guide for Spatial Computing UI.                                                                                            |
| Spatial Design             | `/spatial-design`             | Web and App implementation guide for Spatial Design.                                                                                                  |
| Stitch Design Taste        | `/stitch-design-taste`        | Semantic Design System Skill for Google Stitch.                                                                                                       |
| Swiss Design               | `/swiss-design`               | Web and App implementation guide for Swiss Design (International Typographic Style).                                                                  |
| Synthwave                  | `/synthwave`                  | Web and App implementation guide for Synthwave.                                                                                                       |
| Tile Design                | `/tile-design`                | Web and App implementation guide for Tile Design.                                                                                                     |
| Typography First           | `/typography-first`           | Web and App implementation guide for Typography First Design.                                                                                         |
| Vaporwave                  | `/vaporwave`                  | Web and App implementation guide for Vaporwave.                                                                                                       |
| Vibrant Maximalism         | `/vibrant-maximalism`         | Web and App implementation guide for Vibrant Maximalism.                                                                                              |
| Widget Based Design        | `/widget-based-design`        | Web and App implementation guide for Widget-Based Design.                                                                                             |
| Y2K Design                 | `/y2k-design`                 | Web and App implementation guide for Y2K Design.                                                                                                      |

### Frontend & Frameworks

| Skill Name                        | Command                              | Description                                                                                                                                           |
| --------------------------------- | ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| Astro                             | `/astro`                             | Build content-focused websites with Astro — zero JS by default, islands architecture, multi-framework components, and Markdown/MDX support.           |
| Composition Patterns              | `/composition-patterns`              | ---                                                                                                                                                   |
| Frontend API Integration Patterns | `/frontend-api-integration-patterns` | Production-ready patterns for integrating frontend applications with backend APIs, including race condition handling, request cancellation, retry...  |
| Frontend Lighthouse               | `/frontend-lighthouse`               | Add a portable Lighthouse CI gate for production frontend builds with Core Web Vitals budgets, category floors, median runs, and CI artifacts.        |
| Fumadocs                          | `/fumadocs`                          | Instructions for AI coding agents, follow them in order.                                                                                              |
| Hono                              | `/hono`                              | Build ultra-fast web APIs and full-stack apps with Hono — runs on Cloudflare Workers, Deno, Bun, Node.js, and any WinterCG-compatible runtime.        |
| Image To Code                     | `/image-to-code`                     | Elite website image-to-code skill for Codex.                                                                                                          |
| Imagegen Frontend Mobile          | `/imagegen-frontend-mobile`          | Elite mobile app image-generation skill for creating premium, app-native screen concepts and flows.                                                   |
| Imagegen Frontend Web             | `/imagegen-frontend-web`             | Elite frontend image-direction skill for generating premium, conversion-aware website design references.                                              |
| Migrate To Shoehorn               | `/migrate-to-shoehorn`               | Migrate test files from `as` type assertions to @total-typescript/shoehorn.                                                                           |
| Python Pptx Generator             | `/python-pptx-generator`             | Generate complete Python scripts that build polished PowerPoint decks with python-pptx and real slide content.                                        |
| Rayden Code                       | `/rayden-code`                       | Generate React code with Rayden UI components using correct props, tokens, and premium layout patterns                                                |
| React Best Practices              | `/react-best-practices`              | React and Next.js performance optimization guidelines from Vercel Engineering.                                                                        |
| React Native Skills               | `/react-native-skills`               | ---                                                                                                                                                   |
| React View Transitions            | `/react-view-transitions`            | Guide for implementing smooth, native-feeling animations using React's View Transition API (`<ViewTransition>` component, `addTransitionType`, and... |
| Review Animations                 | `/review-animations`                 | Use when reviewing animation and motion code against a strict craft, performance, accessibility, and interaction-quality bar.                         |
| SvelteKit                         | `/sveltekit`                         | Build full-stack web applications with SvelteKit — file-based routing, SSR, SSG, API routes, and form actions in one framework.                       |
| Web Design Guidelines             | `/web-design-guidelines`             | Review UI code for Web Interface Guidelines compliance.                                                                                               |

### Scientific & Bioinformatics

| Skill Name                           | Command                                 | Description                                                                                                                                              |
| ------------------------------------ | --------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Alphafold Database Fetch And Analyze | `/alphafold_database_fetch_and_analyze` | Retrieve and analyze AlphaFold predicted structures for a protein.                                                                                       |
| Alphagenome Single Variant Analysis  | `/alphagenome_single_variant_analysis`  | Analyzes genetic variant effects on gene expression (RNA-seq), chromatin accessibility (DNASE), histone marks (ChIP), and transcription factors using... |
| Chembl Database                      | `/chembl_database`                      | Query the ChEMBL database for bioactive molecules, drug targets, bioactivity data, approved drugs, and chemical structures.                              |
| Clinical Trials Database             | `/clinical_trials_database`             | Query ClinicalTrials.gov via APIv2.                                                                                                                      |
| Clinvar Database                     | `/clinvar_database`                     | Use when needing clinical significance, pathogenicity classifications (e.g., Pathogenic, Benign, VUS), clinical evidence rationales, or finding "hard... |
| Dbsnp Database                       | `/dbsnp_database`                       | Use when you want to look up, map, and search for short genetic variants (SNPs, indels) in NCBI's dbSNP database.                                        |
| Embl Ebi Ols                         | `/embl_ebi_ols`                         | Query and search the EMBL-EBI Ontology Lookup Service (OLS) for biomedical ontology terms, definitions, and hierarchies across 250+ ontologies (e.g....  |
| Encode Ccres Database                | `/encode_ccres_database`                | Query the ENCODE Registry of cis-Regulatory Elements (cCREs) via the SCREEN GraphQL API, or make custom queries to the ENCODE Portal REST API for...     |
| Ensembl Database                     | `/ensembl_database`                     | Query the Ensembl database to resolve gene, transcript, and protein IDs, fetch genomic or protein sequences, retrieve gene structures (exons), and...    |
| Foldseek Structural Search           | `/foldseek_structural_search`           | Performs 3D structural searches of proteins against various databases (PDB, AlphaFold, CATH, MGnify, etc.) using the Foldseek API.                       |
| Gnomad Database                      | `/gnomad_database`                      | Query the Genome Aggregation Database (gnomAD).                                                                                                          |
| Gtex Database                        | `/gtex_database`                        | Use when you want to retrieve quantitative RNA expression data and variant eQTL information from the GTEx (Genotype-Tissue Expression) Project across... |
| Human Protein Atlas Database         | `/human_protein_atlas_database`         | Use when you want to retrieve semi-quantitative protein expression and spatial localisation data from the Human Protein Atlas (HPA).                     |
| Interpro Database                    | `/interpro_database`                    | Identify domains, families, and sites in proteins; find all proteins in a family or sharing a domain; explore species distribution for a domain...       |
| Jaspar Database                      | `/jaspar_database`                      | Query the JASPAR database for Transcription Factor (TF) binding profiles.                                                                                |
| Literature Search Arxiv              | `/literature_search_arxiv`              | Search for scientific papers, preprints, and publications on arXiv.                                                                                      |
| Literature Search Biorxiv            | `/literature_search_biorxiv`            | Browse, filter, and download life sciences, biology, and medical preprints from bioRxiv and medRxiv.                                                     |
| Literature Search Europepmc          | `/literature_search_europepmc`          | Search Europe PMC for scientific literature and download open-access full texts and PDFs.                                                                |
| Literature Search Openalex           | `/literature_search_openalex`           | Query the OpenAlex scholarly database for research papers, authors, institutions, topics, sources, publishers, funders, geo-locations, and keywords.     |
| Ncbi Sequence Fetch                  | `/ncbi_sequence_fetch`                  | Retrieve protein and nucleotide sequences from NCBI databases using E-utilities.                                                                         |
| Open Targets Database                | `/opentargets_database`                 | Query Open Targets Platform for target-disease associations, drug target discovery, tractability/safety data, genetics/omics evidence, known drugs...    |
| Openfda Database                     | `/openfda_database`                     | Query, search, and download data from the openFDA API for drugs, devices, foods, tobacco, cosmetics, animal and veterinary products, substances, and...  |
| Pdb Database                         | `/pdb_database`                         | Use when you want to search for or download experimentally-determined 3D structures for biomolecules (proteins, nucleic acids, bound ligands).           |
| Predicting the Past                  | `/predictingthepast`                    | Ancient text restoration, attribution, dating, contextualization, and embedding via Aeneas (Latin) / Ithaca (Ancient Greek).                             |
| Protein Sequence Msa                 | `/protein_sequence_msa`                 | Performs multiple sequence alignment of proteins with EBI Clustal Omega.                                                                                 |
| Protein Sequence Similarity Search   | `/protein_sequence_similarity_search`   | Searches for homologous protein sequences using MMseqs2 (fast, default) or BLAST (comprehensive, fallback).                                              |
| Pubchem Database                     | `/pubchem_database`                     | Query PubChem, search by name/CID/SMILES, retrieve properties, similarity/substructure searches, bioactivity, for cheminformatics.                       |
| Pubmed Database                      | `/pubmed_database`                      | Search PubMed for scientific literature, including published clinical trials.                                                                            |
| PyMOL                                | `/pymol`                                | Visualize, analyze, and render protein and molecular structures using PyMOL.                                                                             |
| Quickgo Database                     | `/quickgo_database`                     | Query the QuickGO and Evidence & Conclusion Ontology (ECO) REST API.                                                                                     |
| Reactome Database                    | `/reactome_database`                    | Query the Reactome database (Analysis and Content Services).                                                                                             |
| String Database                      | `/string_database`                      | Query the STRING database for protein-protein interactions (PPIs), functional enrichment, and homology.                                                  |
| Ucsc Conservation And Tfbs           | `/ucsc_conservation_and_tfbs`           | Fetch Evolutionary Conservation scores (phyloP, phastCons) and Transcription Factor Binding Sites (TFBS) from the UCSC Genome Browser.                   |
| Unibind Database                     | `/unibind_database`                     | Queries the UniBind database for experimentally validated transcription factor (TF) binding sites.                                                       |
| Uniprot Database                     | `/uniprot_database`                     | Access protein metadata, function, taxonomy, and sequences across UniProtKB, UniParc, and UniRef.                                                        |

### Tooling & Utilities

| Skill Name                  | Command                        | Description                                                                                                                              |
| --------------------------- | ------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Agenttrace Session Audit    | `/agenttrace-session-audit`    | Audit local AI coding-agent sessions with agenttrace for cost, tool failures, latency, anomalies, health, diffs, and CI gates.           |
| Android CLI                 | `/android-cli`                 | Provides instructions for installing and using the `android` CLI.                                                                        |
| AX Extract Workflow         | `/ax-extract-workflow`         | Reconstruct workflow behind a past coding-agent artifact using local ax sessions/commits/skills/tool traces.                             |
| Context7 MCP                | `/context7-mcp`                | This skill should be used when the user asks about libraries, frameworks, API references, or needs code examples.                        |
| Deploy To Vercel            | `/deploy-to-vercel`            | Deploy applications and websites to Vercel.                                                                                              |
| Global Chat Agent Discovery | `/global-chat-agent-discovery` | Discover and search 18K+ MCP servers and AI agents across 6+ registries using Global Chat's cross-protocol directory and MCP server.     |
| jq                          | `/jq`                          | Expert jq usage for JSON querying, filtering, transformation, and pipeline integration.                                                  |
| Ping                        | `/ping`                        | Health-checks the agent session and reports a "pong" with measured tool round-trip latency, host facts, and clock skew.                  |
| tmux                        | `/tmux`                        | Expert tmux session, window, and pane management for terminal multiplexing, persistent remote workflows, and shell scripting automation. |
| uv                          | `/uv`                          | Checks whether the uv Python package manager is installed and installs it if missing.                                                    |

## Repository Layout

```text
.
├── .github/workflows/
│   └── skill-scan.yml     # SkillSpector security gate
├── skills/
│   ├── i18n/
│   │   ├── SKILL.md
│   │   └── references/    # intl-language, intl-bidi, intl-pluralization, ...
│   ├── s13n/
│   │   ├── SKILL.md
│   │   └── references/    # std-js, std-php, std-python, std-structure, ...
│   └── ...                # one directory per skill
└── README.md
```

## License

See [LICENSE](LICENSE).
