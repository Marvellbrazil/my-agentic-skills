# Environment & Configuration Discipline

Production-ready systems treat configuration as a first-class contract. Code and configuration must remain strictly decoupled according to 12-Factor principles. Switching between local, staging, and production must never require changing a single line of code—only editing environment variables.

---

## 1. The Startup Validation Contract (Fail-Fast)

Never let an application boot with missing or malformed configuration only to crash hours later when a specific code path attempts to read an undefined variable.

### The Standard
- **Validate at the entry point**: Execute configuration validation before connecting to databases, initializing web servers, or mounting routes.
- **Fail immediately and loudly**: If any required variable is missing or invalid, print the exact list of offending keys and exit with `process.exit(1)` or equivalent.
- **Type coerce**: Convert string variables (`"3000"`, `"true"`, `"50"`) to typed primitives (`number`, `boolean`) during validation so the rest of the application uses strongly-typed values.

### TypeScript / Node.js Implementation (Zod)
```typescript
// src/config/env.ts
import { z } from "zod";

const envSchema = z.object({
  NODE_ENV: z.enum(["development", "test", "production"]).default("development"),
  PORT: z.coerce.number().int().min(1000).max(65535).default(3000),
  DATABASE_URL: z.string().url("DATABASE_URL must be a valid connection URL"),
  REDIS_URL: z.string().url().optional(),
  API_KEY_SECRET: z.string().min(32, "API_KEY_SECRET must be at least 32 characters"),
  CORS_ORIGIN: z.string().default("*"),
  LOG_LEVEL: z.enum(["trace", "debug", "info", "warn", "error"]).default("info"),
  MAX_UPLOAD_MB: z.coerce.number().int().positive().default(10),
});

export type Env = z.infer<typeof envSchema>;

function validateEnv(): Env {
  const parsed = envSchema.safeParse(process.env);
  if (!parsed.success) {
    console.error("❌ CRITICAL: Invalid environment configuration:");
    for (const issue of parsed.error.issues) {
      console.error(`   - ${issue.path.join(".")}: ${issue.message}`);
    }
    process.exit(1);
  }
  return parsed.data;
}

export const env = validateEnv();
```

### Python Implementation (Pydantic Settings)
```python
# app/config.py
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, PostgresDsn, Field
from typing import Optional

class Settings(BaseSettings):
    ENVIRONMENT: str = Field(default="development", pattern="^(development|staging|production)$")
    PORT: int = Field(default=8000, ge=1024, le=65535)
    DATABASE_URL: PostgresDsn
    SECRET_KEY: str = Field(min_length=32)
    CORS_ORIGIN: str = "*"
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True

try:
    settings = Settings()
except Exception as e:
    import sys
    print(f"CRITICAL: Failed to validate environment variables: {e}", file=sys.stderr)
    sys.exit(1)
```

---

## 2. Zero Hardcoding Rule

Never embed:
1. **Ports or Hosts**: `http://localhost:3000` or `0.0.0.0:8080`.
2. **Secrets, Keys, or Tokens**: API tokens, JWT secrets, encryption keys, webhook secrets.
3. **Database or Cache URIs**: `postgres://postgres:password@localhost:5432/mydb`.
4. **Third-party Endpoints**: Stripe webhook secrets, AWS S3 bucket names, mail server domains.

### Verification Checklist
- Run ripgrep to ensure no hardcoded URLs or credentials exist in `src/`:
  ```bash
  rg -i "(api[_-]?key|secret|password|bearer|authorization)\s*[:=]\s*['\"][a-zA-Z0-9_\-]{8,}['\"]" src/
  ```

---

## 3. The `.env.example` Specification

Every repository must maintain an exhaustive, accurate, and up-to-date `.env.example`.

### Rules
- **Every variable present**: If a variable is read in the code or schema, it must be listed in `.env.example`.
- **Zero real credentials**: Placeholders must clearly indicate expected structure (`pk_live_...`, `postgres://user:password@localhost:5432/dbname`) without real credentials.
- **Annotated**: Each variable should specify its purpose, required vs optional, and defaults.

### Template Standard
```bash
# ==============================================================================
# Application Configuration
# ==============================================================================
# Environment mode: development | test | production
NODE_ENV=development
PORT=3000

# ==============================================================================
# Database & Cache
# ==============================================================================
# PostgreSQL connection string
DATABASE_URL=postgres://user:password@localhost:5432/devdb
# Optional Redis connection string for caching & queues
REDIS_URL=redis://localhost:6379

# ==============================================================================
# Security & Authentication
# ==============================================================================
# Minimum 32-character secret for JWT signing or sessions
API_KEY_SECRET=replace_with_min_32_char_cryptographically_secure_random_string
# Allowed CORS origins (comma-separated or single domain)
CORS_ORIGIN=http://localhost:3000

# ==============================================================================
# Third-Party Integrations
# ==============================================================================
# External provider API key
EXTERNAL_SERVICE_API_KEY=your_key_here
```

---

## 4. Secret Masking & Logging Hygiene

- **Never log raw environment**: Avoid `console.log(process.env)` or dumping request headers in logs.
- **Redact secrets in error output**: Sanitize connection URLs so passwords do not leak in stack traces (`postgres://user:****@db.host.com:5432/db`).
- **Ignore `.env` from git**: Ensure `.env`, `.env.local`, `.env.*.local` are present in `.gitignore`.
