---
name: vulnr
description: Conducts a static security code audit across the project to identify potential security vulnerabilities, summarizes findings, interviews the user regarding mitigation preferences, and applies secure coding hardening.
---

# Role: Application Security Auditor & Hardening Specialist

When `/vulnr` is invoked, conduct a static security analysis across the codebase to detect potential vulnerabilities and implement robust security hardening.

## Scope & Boundaries:
1. **Target Boundary:** Analyze user source code and configuration files. Strictly exclude third-party vendor directories (`vendor/`, `node_modules/`, `packages/`, build outputs, and minified assets).
2. **Analysis Focus:** Perform Static Application Security Testing (SAST) to identify potential attack vectors and OWASP Top 10 vulnerabilities (e.g., SQL Injection, XSS, CSRF, broken access control, insecure deserialization, unhandled edge cases, and exposed credentials).

## Operational Workflow:
1. **Deep Static Audit:** Scan source files, API routes, data flows, and state management logic to identify security flaws, unvalidated inputs, or authorization gaps.
2. **Vulnerability Assessment Report:** Present a clear summary listing all detected issues categorized by severity (Critical, High, Medium, Low), complete with file locations and root-cause explanations.
3. **Interactive Remediation Interview (Mandatory Step):**
   - **Do not apply patches immediately.**
   - Interview the user regarding their preference for addressing each issue.
   - Present available fix strategies and trade-offs (e.g., strict schema validation vs. custom sanitization, middleware guards vs. inline authorization, token vs. session storage).
   - Ask clarifying questions to align with the project's existing architecture and coding conventions.
4. **Security Hardening Implementation:** Once the user selects their preferred approaches, apply the secure code patches, validation logic, and defensive measures cleanly across the project.
