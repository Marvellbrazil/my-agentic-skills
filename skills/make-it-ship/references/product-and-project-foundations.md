# Product and project foundations

Source group 5. Covers project discipline, development hygiene, and planning foundations. Distinguish genuine production requirements (such as secret handling and environment separation) from personal workflow preferences (such as using specific AI assistants or plugin configurations). Use [SKILL.md](../SKILL.md) for reporting status and source mapping.

| ID | Source item | Applicability, interpretation and evidence to seek |
| ----- | --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| PF-01 | Create a PRD in Claude | Advisory workflow practice. Verify that product requirements, core scope, and target outcomes are documented in the repository or project wiki. Using Claude specifically is optional; any clear requirements source satisfies the product need. |
| PF-02 | Define value, pain, ICP | Product foundation. Inspect documentation or landing copy for clear target persona (ICP), user problem statement, and primary value proposition. Verify that the product solves an identifiable problem for an intended audience. |
| PF-03 | Export PRD to markdown | Documentation hygiene. Check whether project specifications, architecture notes, or roadmap documents are stored in accessible markdown or text files within the codebase for team and agent continuity. |
| PF-04 | Load PRD into Claude Code | Advisory workflow tooling. Check whether agent instructions or project context files link to relevant specifications. Optional; do not fail an audit if alternative AI tooling or manual engineering workflows are used. |
| PF-05 | Write your Claude.md | Project instruction hygiene. Check whether repository guidelines (such as `CLAUDE.md`, `AGENTS.md`, or `CONTRIBUTING.md`) exist to define coding conventions, test commands, and architectural guardrails for human and agent contributors. |
| PF-06 | Install Claude Code plugins | Advisory tooling. Verify relevant developer tooling and linters are configured for the team. Specific Claude Code plugins are optional and dependent on contributor workflows. |
| PF-07 | Connect GitHub | Version control and collaboration. Verify remote git repository connection, branch protection rules, and CI/CD workflow status. Alternative hosting platforms (GitLab, Bitbucket, self-hosted forge) equally satisfy this requirement. |
| PF-08 | Adda .gitignore | Repository hygiene (original typo: Adda). Inspect `.gitignore` to ensure `.env*` secrets, build artifacts, temporary caches, dependency folders (`node_modules/`, `vendor/`, `venv/`), and OS files are excluded from tracking. |
| PF-09 | Generate a brand doc | Design and identity consistency. Check whether brand assets, typography tokens, color palette, and tone-of-voice guidelines are documented for cohesive customer experience. Advisory for early prototypes. |
| PF-10 | Lock in your tech stack | Architecture stability. Inspect dependency manifests and lockfiles (`package-lock.json`, `bun.lock`, `composer.lock`, `Cargo.lock`, `poetry.lock`) to verify dependencies are pinned, coherent, and free from conflicting framework versions. |
| PF-11 | Set up a design system | UI consistency. Inspect design tokens, reusable UI component library, and stylesheet structure. Ensure consistent spacing, typography, and interactive components across the application. Related: DC-07, DC-13. |
| PF-12 | Break PRD into tasks | Execution planning. Check for structured issue backlog, roadmap milestones, or task tracking files (e.g. `TODOLIST.md`, GitHub Issues, Linear board) that organize implementation into verifiable units. |
| PF-13 | Set up database and aut | Core infrastructure (original typo: aut). Inspect database connection configuration, migrations, and authentication mechanism. Verify both data storage and user identity handling are functional and tested. Related: SB-04, SB-06, SB-10. |
| PF-14 | Move keys to env vars | Configuration security. Verify that all third-party API credentials, database passwords, and runtime secrets are loaded from environment variables rather than hardcoded in source code. Related: SB-01, AH-06, AH-12. |
| PF-15 | Split staging from prod | Environment isolation. Inspect deployment pipelines and configuration to verify separate staging and production environments exist with isolated databases, API keys, storage buckets, and domain routing. |
| PF-16 | Add a README | Onboarding and operational documentation. Check that `README.md` clearly explains project purpose, local development setup, environment variables, test execution, and deployment procedures. |
| PF-17 | Plan your folder structure | Architectural modularity. Inspect codebase organization for clear separation of concerns (e.g., domain logic, data access, UI components, API routes) and avoidance of monolithic or disorganized directories. |
| PF-18 | Add error tracking | Operational observability. Verify production error monitoring and crash reporting (e.g., Sentry, Bugsnag, Datadog, CloudWatch) are configured with PII redaction and release tracking. |
| PF-19 | Define what you won't build | Scope control. Check product documentation for explicit out-of-scope boundaries to prevent pre-launch feature creep and ensure a focused minimum viable release. |
| PF-20 | Commit small and often | Git discipline. Review recent git commit history for atomic, well-described commits focusing on single concerns. Discourage massive unstructured commits containing unrelated changes. |

## Supporting guidance

- Distinguish process advice from blocking production gates: missing staging infrastructure (PF-15) is a high-risk operational gap for financial/critical systems, whereas lacking a specific Claude Code plugin (PF-06) is an advisory workflow suggestion.
- For open-source or public projects, ensure `.gitignore` (PF-08) and `README.md` (PF-16) are comprehensive before public release.
