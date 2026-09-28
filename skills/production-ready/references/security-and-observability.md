# Security & Observability

In production environments, security vulnerabilities lead to data breaches, while poor observability causes prolonged outages with unidentifiable root causes.

---

## 1. Security Headers & CORS Lockdown

Every web application must set modern security headers and lock down Cross-Origin Resource Sharing (CORS).

### HTTP Security Headers
Never return raw HTTP responses without defense-in-depth headers.
- **Node.js**: Use `helmet()` middleware.
- **Python (FastAPI / Django)**: Use security middleware or proxy configuration (Nginx / Cloudflare).

Essential headers:
- `Strict-Transport-Security`: Enforce HTTPS for a minimum of 1 year (`max-age=31536000; includeSubDomains`).
- `X-Content-Type-Options: nosniff`: Prevent MIME-sniffing exploits.
- `X-Frame-Options: DENY` or `SAMEORIGIN`: Mitigate clickjacking attacks.
- `Content-Security-Policy (CSP)`: Restrict unauthorized script execution and asset injection.

### CORS Hardening
```typescript
import cors from "cors";

// BAD: Insecure wildcard in production with credentials
// app.use(cors({ origin: "*", credentials: true }));

// GOOD: Strictly validated origins from environment
const allowedOrigins = (process.env.CORS_ORIGIN || "")
  .split(",")
  .map(o => o.trim())
  .filter(Boolean);

app.use(cors({
  origin: (origin, callback) => {
    // Allow non-browser requests (curl, server-to-server) or matched origins
    if (!origin || allowedOrigins.includes(origin)) {
      callback(null, true);
    } else {
      callback(new Error(`Origin ${origin} not allowed by CORS policy`));
    }
  },
  credentials: true,
  methods: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
  allowedHeaders: ["Content-Type", "Authorization", "X-Request-Id"],
}));
```

---

## 2. Error Shielding (Never Leak Stack Traces)

Returning stack traces or database errors to client applications reveals database engines, table names, file paths, and dependency versions to attackers.

### The Rule
- **Client sees**: Opaque, generic status and error code (`{ "error": "InternalServerError", "message": "An unexpected error occurred", "requestId": "req-123" }`).
- **Server logs**: Full stack trace, contextual parameters, user ID, request ID.

### Express Global Error Boundary Example
```typescript
import { ErrorRequestHandler } from "express";
import { logger } from "./logger";

export const errorHandler: ErrorRequestHandler = (err, req, res, _next) => {
  const isProduction = process.env.NODE_ENV === "production";
  const requestId = req.headers["x-request-id"] as string || "unknown";

  // Always log full error details internally
  logger.error({
    err,
    requestId,
    method: req.method,
    url: req.originalUrl,
  }, "Request failed with unhandled error");

  const statusCode = err.status || err.statusCode || 500;

  res.status(statusCode).json({
    success: false,
    error: {
      code: err.code || "INTERNAL_SERVER_ERROR",
      message: isProduction && statusCode === 500
        ? "An internal server error occurred"
        : err.message,
      requestId,
      ...(isProduction ? {} : { stack: err.stack }),
    },
  });
};
```

---

## 3. Structured JSON Logging & PII Redaction

Plain-text `console.log("user logged in: " + user)` is unparseable at scale in Datadog, Grafana Loki, or CloudWatch, and risks leaking sensitive PII.

### Production Rules
- **JSON Output**: Every log entry must be structured JSON with `level`, `time`, `msg`, `requestId`, and structured metadata.
- **Log Levels**: Use appropriate levels (`debug`, `info`, `warn`, `error`, `fatal`). Never log `debug` or `trace` in production by default.
- **Automatic Redaction**: Redact passwords, credit card numbers, authorization headers, and session tokens.

### Pino Implementation with Redaction
```typescript
import pino from "pino";

export const logger = pino({
  level: process.env.LOG_LEVEL || "info",
  redact: {
    paths: [
      "req.headers.authorization",
      "req.headers.cookie",
      "password",
      "*.password",
      "token",
      "*.token",
      "creditCard",
      "apiKey",
      "secret",
    ],
    censor: "[REDACTED]",
  },
  formatters: {
    level: (label) => ({ level: label }),
  },
  timestamp: pino.stdTimeFunctions.isoTime,
});
```

---

## 4. Docker & Container Production Hardening

Running containers as `root` or shipping source files in production images increases attack surfaces.

### Best Practices
1. **Multi-Stage Builds**: Build in stage 1; copy only compiled assets and production dependencies into a lightweight scratch/distroless/alpine image.
2. **Run as Non-Root**:
   ```dockerfile
   # Ensure dedicated non-root user
   USER node
   ```
3. **Prevent Secret Leaks in Layers**: Never pass secrets as `ARG` or `ENV` in `Dockerfile`. Use secret mounts at runtime.
4. **Enforce `.dockerignore`**: Exclude `.env*`, `.git`, `tests`, `coverage`, `*.md`.
