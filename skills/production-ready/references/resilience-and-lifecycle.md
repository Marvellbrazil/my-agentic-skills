# Resilience & Process Lifecycle

In production (Kubernetes, AWS ECS, Fly.io, Cloud Run), processes are ephemeral. Deployments, auto-scaling, and spot instance terminations regularly send `SIGTERM` signals. A non-resilient process drops active user requests, corrupts database transactions, and leaves orphaned sockets.

---

## 1. Graceful Shutdown Protocol

When a process receives a termination signal (`SIGTERM` or `SIGINT`), it must perform an orderly shutdown sequence.

### The 5-Step Orderly Drain
1. **Trap the signal**: Catch `SIGTERM` and `SIGINT` once. Prevent multiple traps from clashing.
2. **Stop ingress traffic**: Close the HTTP server so no new connections are accepted. Return `Connection: close` on pending responses.
3. **Set a termination deadline**: Start a countdown (e.g. 15–30 seconds). If graceful teardown does not finish within the deadline, force-exit (`process.exit(1)`) to avoid hanging container kills.
4. **Drain in-flight operations**: Wait for currently executing HTTP requests, background tasks, or queue workers to finish.
5. **Close persistent resources**: Disconnect database connection pools, Redis clients, message bus connections, and flush telemetry/log buffers.
6. **Exit cleanly**: Terminate with code 0 (`process.exit(0)`).

### Node.js / Express Implementation
```typescript
import http from "node:http";
import process from "node:process";
import { db } from "./db";
import { logger } from "./logger";

export function setupGracefulShutdown(server: http.Server, timeoutMs = 15000) {
  let isShuttingDown = false;

  const shutdown = async (signal: string) => {
    if (isShuttingDown) return;
    isShuttingDown = true;
    logger.info({ signal }, "Shutdown signal received. Starting graceful drain...");

    // Force exit if drain exceeds timeout
    const forceExitTimer = setTimeout(() => {
      logger.error("Graceful shutdown timed out. Forcing process exit.");
      process.exit(1);
    }, timeoutMs);
    forceExitTimer.unref(); // Don't keep event loop alive just for timer

    // 1. Stop accepting new connections
    server.close(async (err) => {
      if (err) {
        logger.error({ err }, "Error while closing HTTP server");
        process.exit(1);
      }

      try {
        // 2. Close database connection pool
        logger.info("Closing database connections...");
        await db.$disconnect(); // or pool.end()

        logger.info("Graceful shutdown completed successfully.");
        clearTimeout(forceExitTimer);
        process.exit(0);
      } catch (error) {
        logger.error({ error }, "Error during cleanup phase");
        process.exit(1);
      }
    });
  };

  process.on("SIGTERM", () => shutdown("SIGTERM"));
  process.on("SIGINT", () => shutdown("SIGINT"));
}
```

---

## 2. Health & Readiness Probes

Orchestrators need distinct probes to differentiate between a booting container and a broken container.

| Probe | Path | Purpose | Behavior on Failure |
| --- | --- | --- | --- |
| **Liveness** | `/livez` or `/healthz` | Checks if process event loop is alive. | Container restarted immediately. |
| **Readiness** | `/readyz` | Checks if app can serve traffic (DB connected, cache warm). | Traffic shifted away; container NOT restarted. |

### Implementation Pattern
```typescript
import { Router } from "express";
import { db } from "./db";

export const healthRouter = Router();

// Liveness probe: shallow check (is process running?)
healthRouter.get("/livez", (_req, res) => {
  res.status(200).json({ status: "alive", uptime: process.uptime() });
});

// Readiness probe: deep check (are dependencies reachable?)
healthRouter.get("/readyz", async (_req, res) => {
  try {
    // Check DB ping with short timeout
    await db.$queryRaw`SELECT 1`;
    res.status(200).json({ status: "ready", db: "connected" });
  } catch (error) {
    res.status(503).json({
      status: "unavailable",
      db: "disconnected",
      message: "Database ping failed"
    });
  }
});
```

---

## 3. Unhandled Process Errors

Uncaught exceptions or unhandled promise rejections put application state in an undefined, corrupted state. The only safe behavior is to log the fatal error and restart.

```typescript
// Register top-level exception handlers
process.on("uncaughtException", (error) => {
  logger.fatal({ err: error }, "FATAL: Uncaught exception occurred. Exiting process.");
  // Exit immediately so supervisor/orchestrator can spawn a clean replica
  process.exit(1);
});

process.on("unhandledRejection", (reason, promise) => {
  logger.error({ reason, promise }, "Unhandled promise rejection detected.");
  process.exit(1);
});
```

---

## 4. Database Connection Pool Discipline

Never allow infinite connections. Connection pools must be strictly bounded to prevent exhausting database max connection limits.

### Configuration Guide
```typescript
// Example: pg Pool or Prisma connection limit
const poolConfig = {
  max: 20,                  // Max active connections per instance
  min: 2,                   // Keep small idle pool
  idleTimeoutMillis: 30000, // Close idle connections after 30s
  connectionTimeoutMillis: 5000, // Fail if cannot acquire connection in 5s
};
```
- **Formula for max pool size**:
  $$\text{Pool Size Per App} \le \frac{\text{DB Max Connections} - \text{Reserved (15)}}{\text{Number of App Replicas}}$$
