# Cost & Resource Guards

Production systems fail financially before they fail technically. A single missing rate limit, uncapped loop, or unbounded database query can deplete API budgets, exhaust cloud instances, or trigger devastating cloud billing spikes overnight.

## 1. Third-Party API & LLM Cost Runaways

External paid APIs (OpenAI, Anthropic, Stripe, Twilio, AWS) charge per token, per call, or per byte. Unprotected calls represent direct financial liabilities.

### Hazards
- **Infinite/Runaway Loops**: Unbounded `while` loops polling or re-querying paid APIs without max iteration guards.
- **Uncapped Concurrency**: `Promise.all(items.map(...))` on unbounded arrays firing thousands of paid requests simultaneously, causing 429 rate limits, socket exhaustion, and massive billing.
- **Cache Absence on Expensive Operations**: Repeating identical LLM prompts, embeddings, or geocoding lookups without a caching layer (Redis, in-memory LRU, or database cache).
- **Missing Token/Spend Budgets**: Allowing user prompts or agent execution loops without hard token limits (`max_tokens`) or user-level rate/credit caps.

### Production Rules
```typescript
// BAD: Unbounded concurrent paid API calls
await Promise.all(records.map(r => openai.embeddings.create({ input: r.text, model: "text-embedding-3-small" })));

// GOOD: Batched with chunking, concurrency limit, and error boundary
import pLimit from "p-limit";
const limit = pLimit(5); // max 5 concurrent requests
const results = await Promise.all(
  records.map(r => limit(() => cachedEmbeddingLookup(r.text)))
);
```
- **Always enforce `max_tokens` / `max_completion_tokens`** on LLM generations.
- **Enforce per-user / per-tenant rate limits and usage quotas** before reaching third-party API gateways.
- **Set hard spending caps and alerts** in cloud/provider dashboards.

---

## 2. Database Query Boundaries & Pagination

Unbounded database queries are the primary cause of sudden database CPU saturation, connection starvation, and Out-Of-Memory (OOM) process crashes.

### Hazards
- **Missing `LIMIT` Clauses**: Executing `SELECT * FROM table` or ORM queries (`find()`, `findMany()`) without a hard cap. As tables grow, payloads balloon from kilobytes to hundreds of megabytes.
- **Deep Offset Pagination**: `OFFSET 500000` scans and discards half a million rows on every page, destroying database IOPS.
- **Unindexed Filtering**: Queries filtering on non-indexed columns causing full table scans under production traffic.
- **N+1 Query Cascades**: ORM relations fetched in loops instead of batch-joins or eager-loading.

### Production Rules
- **Hard Max Limit Enforced in Code**: Never let clients request `?limit=100000`. Enforce a clamp: `const limit = Math.min(parseInt(req.query.limit || "20", 10), 100);`.
- **Keyset / Cursor Pagination**: For large datasets, use cursor-based pagination (`WHERE id > :cursor ORDER BY id ASC LIMIT :limit`) rather than offset.
- **Select Projection**: Explicitly select required columns (`SELECT id, name, status`) instead of raw wildcards (`SELECT *`).

---

## 3. Timeouts on All Network Boundaries

A network call without an explicit timeout is an infinite liability. Upstream hangs will freeze application threads, exhaust connection pools, and trigger cascading failure across the architecture.

### Hazards
- Default Node.js `fetch` has **no timeout**. A hung remote server will hold open the socket indefinitely.
- Default Python `requests.get(url)` has **no timeout**.
- Default Go `http.Client{}` has **no timeout**.
- Database connection pools without connection / statement timeouts.

### Production Rules
| Platform | Default Hazard | Production Requirement |
| --- | --- | --- |
| Node.js `fetch` | No timeout (hangs forever) | `AbortSignal.timeout(5000)` or `new AbortController()` |
| Axios | `timeout: 0` (unlimited) | Configure global `timeout: 10000` (10 seconds) |
| Python `requests` | None (hangs indefinitely) | Always pass `timeout=(3.05, 10)` (connect, read) |
| Go `http.Client` | 0 (unlimited) | `Timeout: 10 * time.Second` |
| PostgreSQL / Prisma | Default unlimited | `statement_timeout = 5000`, `connection_timeout = 3000` |

```typescript
// Node fetch with robust timeout
const response = await fetch("https://api.external.com/v1/resource", {
  signal: AbortSignal.timeout(8000), // 8s timeout
  headers: { "Accept": "application/json" },
});
```

---

## 4. Retries, Backoff, and Circuit Breakers

Blind retries turn a minor transient glitch into an unrecoverable thundering herd (self-inflicted DDoS).

### Hazards
- Retrying HTTP 4xx client errors (400, 401, 403, 404, 422). These are semantic failures; retrying them simply burns CPU and bandwidth.
- Immediate retry loops without delay.
- Synchronized retries without jitter causing traffic spikes at constant intervals (e.g. exactly every 1000ms).

### Production Rules
1. **Retry Only Idempotent & Transient Errors**: HTTP 408, 429, 500, 502, 503, 504 and network drops (`ECONNRESET`, `ETIMEDOUT`). Never retry 400, 401, 403, 404, 422.
2. **Exponential Backoff with Full Jitter**:
   $$\text{sleep} = \text{random}(0, \min(M, B \times 2^{\text{attempt}}))$$
3. **Cap Maximum Attempts**: 3 attempts maximum. Never retry indefinitely.
4. **Circuit Breakers**: Trip open when error rate exceeds threshold (e.g., 50% over 20 calls), fast-failing subsequent requests for 30s to allow upstream recovery.

---

## 5. Ingress Payload & Rate Protection

Every endpoint exposed to the internet must protect its resources from abuse and denial-of-service.

### Hazards
- **Missing Payload Size Limit**: Allowing arbitrary JSON bodies (`app.use(express.json())` without `limit: '1mb'`). Attackers can send a 100MB string to crash JSON parser or exhaust RAM.
- **Missing Rate Limiting**: Open login, registration, password reset, or compute endpoints vulnerable to brute force and scraping.
- **Unbounded File Uploads**: Upload endpoints lacking file size checks, MIME type verification, and disk space guards.

### Production Rules
```typescript
// Express example
import rateLimit from "express-rate-limit";

// Strict JSON parser limit
app.use(express.json({ limit: "1mb" }));
app.use(express.urlencoded({ extended: true, limit: "1mb" }));

// Global rate limiting
app.use(rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 300, // 300 requests per IP per window
  standardHeaders: true,
  legacyHeaders: false,
}));

// Sensitive endpoint rate limiting (e.g. auth / paid operations)
export const sensitiveEndpointLimiter = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: 10, // 10 requests per minute
  message: { error: "Too many requests. Please slow down." },
});
```
