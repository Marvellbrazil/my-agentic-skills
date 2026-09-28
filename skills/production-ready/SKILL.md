---
name: production-ready
description: Prepares, audits, and hardens projects for production deployment. Detects financial cost loopholes, unbounded queries, runaway API billing risks, missing timeouts, and uncapped loops. Generates dynamic, strictly validated environment variable configs (.env, .env.example), implements health probes, graceful shutdown protocols, error shielding, security headers, and rate limits. Use whenever the user asks to "make this production ready", "audit for production", "check deployment readiness", "prevent billing runaways", "setup environment variables", "prepare for release", or before shipping any code to cloud/staging/production.
allowed-tools: Bash Read Grep Glob Edit Write
---

# Production-Ready Setups Creator

Transform prototype and development-grade code into resilient, cost-controlled, and observable production-ready software.

Deploying unhardened software causes two major classes of failure:
1. **Financial and Resource Disasters**: Uncapped loops, unbounded database queries, missing network timeouts, and unprotected third-party API calls (e.g. OpenAI, Stripe) that trigger massive cloud bills, exhaust connection pools, or cause self-inflicted denial-of-service.
2. **Operational Fragility**: Hardcoded connection strings, missing environment validation, dropped in-flight requests during rolling deployments, unmasked stack traces leaking to users, and unstructured logs.

This skill audits a codebase across these failure modes, implements missing production safeguards, and generates verified configuration.

---

## The 5 Pillars of Production Readiness

| Pillar | Focus | Reference Module |
| --- | --- | --- |
| **1. Cost & Resource Guards** | Query limits, pagination, network timeouts, backoff, LLM/API spending caps | `references/cost-and-resource-guards.md` |
| **2. Dynamic Environment & Config** | Zero hardcoded values, startup schema validation, complete `.env.example` | `references/env-and-config.md` |
| **3. Resilience & Lifecycle** | Graceful shutdown (`SIGTERM`/`SIGINT`), health probes (`/livez`, `/readyz`) | `references/resilience-and-lifecycle.md` |
| **4. Security & Error Shielding** | Security headers, CORS restriction, rate limiting, generic 500 responses | `references/security-and-observability.md` |
| **5. Observability & Logging** | Structured JSON logging, request correlation IDs, PII redaction | `references/security-and-observability.md` |

---

## Workflow

### Step 1 — Project Discovery & Surface Analysis

Inspect the project to identify runtime, framework, database, external dependencies, and ingress entry points.

```bash
# Identify manifests, runtimes, and lockfiles
ls -la
cat package.json pyproject.toml go.mod Cargo.toml requirements.txt 2>/dev/null | head -50

# Scan existing environment setups
find . -maxdepth 2 -name ".env*" -not -path "./.git/*"

# Locate entry points and server definitions
grep -rnE "(listen\(|createServer|FastAPI\(|express\(|http\.ListenAndServe)" src/ app/ server/ 2>/dev/null | head -20
```

Record:
- Primary language, framework, and runtime version.
- Database clients / ORMs (Prisma, Drizzle, TypeORM, SQLAlchemy, pg, Mongoose).
- External paid APIs (OpenAI, Anthropic, Stripe, SendGrid, Twilio, AWS SDK).
- Process entry point file (`server.ts`, `main.py`, `app.js`).

---

### Step 2 — Audit for Financial Loopholes & Cost Hazards

Search the codebase for code patterns that risk runaway cloud or API spend:

```bash
# 1. Unbounded Database Queries (missing limit/take)
grep -rnE "(findMany|findAll|\.find\(|SELECT \*)" src/ app/ 2>/dev/null | grep -vE "(take:|limit:|LIMIT)" | head -30

# 2. Network calls without explicit timeouts
grep -rnE "fetch\(|axios\.(get|post)|requests\.(get|post)" src/ app/ 2>/dev/null | head -30

# 3. Uncapped concurrent paid API calls
grep -rnE "Promise\.all\(" src/ app/ 2>/dev/null | head -20

# 4. Unbounded loops or queue processing
grep -rnE "while\s*\(true\)|while\s*\(1\)" src/ app/ 2>/dev/null | head -20
```

Read `references/cost-and-resource-guards.md` for specific remediation patterns:
- Clamp all client-supplied pagination limits: `Math.min(limit, 100)`.
- Attach `AbortSignal.timeout(ms)` to every HTTP call.
- Wrap concurrent batches in concurrency limiters (e.g. `p-limit`).
- Add hard token ceilings (`max_tokens`) to LLM requests.

---

### Step 3 — Dynamic Environment Configuration & Schema Validation

Guarantee zero hardcoding. The project must be fully configurable across environments by altering environment variables alone.

1. **Audit for hardcoded values**:
   ```bash
   grep -rnE "(http://localhost|0\.0\.0\.0|postgres://|mongodb://|redis://)" src/ app/ 2>/dev/null | head -30
   grep -rnE "(sk-[a-zA-Z0-9]{20,}|bearer [a-zA-Z0-9_\-\.]{20,})" src/ app/ 2>/dev/null | head -20
   ```

2. **Implement Fail-Fast Startup Validation**:
   If the project lacks startup schema validation, implement an environment validator module (e.g. `src/config/env.ts` using Zod/Joi or `app/config.py` using Pydantic Settings).
   - Require all critical connection strings (`DATABASE_URL`, `SECRET_KEY`, `PORT`).
   - Coerce numeric and boolean strings to native primitives.
   - Halt execution (`process.exit(1)`) on boot if any required key is missing, listing every missing key.

3. **Generate or Sync `.env.example`**:
   - Inventory every environment variable referenced in the code.
   - Write `.env.example` with clear comments, type formats, and safe non-secret defaults.
   - Ensure `.env` is listed in `.gitignore`.

Read `references/env-and-config.md` for full implementation details.

---

### Step 4 — Implement Resilience & Lifecycle Controls

Ensure containers and instances can be stopped, restarted, and deployed without dropping user requests or corrupting transactions.

1. **Add Graceful Shutdown**:
   - Catch `SIGTERM` and `SIGINT`.
   - Close HTTP listener to stop new connections.
   - Set a 15–30s shutdown deadline.
   - Drain active requests and close database pools cleanly (`db.$disconnect()` or `pool.end()`).

2. **Add Liveness & Readiness Probes**:
   - `/livez` (or `/healthz`): Shallow check verifying the HTTP event loop is active (returns 200).
   - `/readyz`: Deep check verifying database and critical backing services respond (returns 200 or 503).

3. **Add Global Process Exception Traps**:
   - Catch `uncaughtException` and `unhandledRejection`.
   - Log the fatal diagnostic and exit cleanly with code 1 so the supervisor can spawn a fresh instance.

Read `references/resilience-and-lifecycle.md` for code templates.

---

### Step 5 — Security & Observability Hardening

1. **HTTP Security Headers & CORS**:
   - Add security headers (`helmet` in Node.js, security middleware in Python).
   - Restrict CORS origin to explicitly configured `CORS_ORIGIN` env vars. Never leave `*` with credentials in production.

2. **Ingress Payload & Rate Limiting**:
   - Restrict body-parser payloads (e.g. `express.json({ limit: '1mb' })`).
   - Apply rate limiting to public and authentication endpoints.

3. **Error Shielding**:
   - Replace raw error responses with sanitized envelopes.
   - Never send database errors, query strings, or stack traces to client HTTP responses.

4. **Structured JSON Logging**:
   - Replace ad-hoc `console.log` with structured JSON logger (e.g. Pino, Winston, Loguru).
   - Redact sensitive keys (`password`, `token`, `authorization`, `creditCard`).

Read `references/security-and-observability.md` for implementation patterns.

---

### Step 6 — Verification & Delivery Report

Verify all changes:
1. Verify the project builds: run build command.
2. Verify test suites pass: run test command.
3. Validate `.env.example` matches code references.

Deliver a structured **Production Readiness Report**:

```markdown
# Production Readiness Report — [Project Name]

## Summary
- **Status**: [Ready / Ready with Warnings / Action Required]
- **Runtime**: [e.g. Node 20 / TypeScript / Express]
- **Safeguards Applied**: [N] automated fixes implemented

## 1. Loophole & Financial Hazard Audit
- [x] Query limits: pagination clamped to max 100
- [x] Network timeouts: AbortSignal attached to all external fetch calls
- [x] Paid API limits: LLM generations constrained with max_tokens
- [x] Rate limiting: Ingress endpoints protected

## 2. Dynamic Environment & Configuration
- [x] Fail-fast startup validator implemented in `src/config/env.ts`
- [x] Zero hardcoded URLs/secrets remaining
- [x] `.env.example` synchronized with all required variables
- [x] `.env` confirmed in `.gitignore`

## 3. Resilience & Lifecycle
- [x] Graceful shutdown handling `SIGTERM`/`SIGINT` with 15s drain
- [x] `/livez` and `/readyz` health endpoints configured
- [x] Top-level process crash handlers installed

## 4. Security & Observability
- [x] Security headers & CORS lockdown configured
- [x] Client error shielding active (zero stack traces leaked)
- [x] Structured JSON logger with automatic PII redaction

## Next Steps for Operator
1. Copy `.env.example` to `.env` and fill production secrets in target environment.
2. Configure cloud orchestrator (Kubernetes / ECS / Cloud Run) to target `/livez` and `/readyz`.
```
