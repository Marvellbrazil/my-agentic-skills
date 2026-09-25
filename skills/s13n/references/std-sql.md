# SQL and Database Standards

The database is the one layer every service in a system shares, so a divergent convention here is a correctness and availability risk rather than a style disagreement. An implicit cast that silently disables an index, a `NOT IN` against a nullable column that returns zero rows, a `timestamp without time zone` that drifts an hour twice a year, or a migration that takes an `ACCESS EXCLUSIVE` lock on a hot table at peak traffic all pass review and pass tests, then fail in production. This module covers schema naming and data types, migrations, query construction, indexing, and transaction discipline for the relational engines a typical repository targets.

## Contents

- [When This Applies](#when-this-applies)
- [Schema, Naming, and Data Types](#schema-naming-and-data-types)
  - [Identifiers, keywords, and case](#identifiers-keywords-and-case)
  - [Data types](#data-types)
  - [Column ordering, defaults, and soft deletes](#column-ordering-defaults-and-soft-deletes)
- [Migrations and Schema Change](#migrations-and-schema-change)
- [Query Construction and NULL Semantics](#query-construction-and-null-semantics)
  - [Parameterization](#parameterization)
  - [Explicit joins, qualification, and column lists](#explicit-joins-qualification-and-column-lists)
  - [NULL and three-valued logic](#null-and-three-valued-logic)
- [Indexing, Plans, and Query Performance](#indexing-plans-and-query-performance)
  - [Pagination](#pagination)
  - [N+1 queries](#n1-queries)
  - [Read the plan before optimizing](#read-the-plan-before-optimizing)
- [Transactions, Concurrency, and Access Patterns](#transactions-concurrency-and-access-patterns)
- [Common Mistakes](#common-mistakes)
- [Checklist](#checklist)
- [References](#references)

## When This Applies

- The repository contains `.sql` files, `migrations/`, `alembic/`, `db/migrate/`, `db/migration/`, `schema.prisma`, or a schema definition embedded in a manifest.
- Two tables disagree on naming shape: `users` beside `UserProfile`, `user_id` beside `userId`, `created_at` beside `createdAt`.
- Constraints or indexes have engine-generated names (`users_pkey` beside `SYS_C0012345`, `DF__Orders__total__1A14E395`) or none at all, so `DROP CONSTRAINT` scripts cannot be written.
- Schema change happens outside the migration directory: a `CREATE INDEX` in a runbook, an ad-hoc `ALTER TABLE` in a console session, a hand-edited `schema.rb`.
- Query strings are assembled with `+`, `.format()`, f-strings, template literals, or `.replace()` before execution.
- The ORM layer issues a query per row of a loop, or a request's query count grows linearly with the result size.
- A table is read with `LIMIT 20 OFFSET 100000`, or a list endpoint has no keyset path.
- Money, timestamps, or identifiers were stored in a type chosen by default rather than by decision (`float`, `timestamp without time zone`, `varchar(36)`).
- Deletion is implemented with a `deleted_at` or `is_deleted` column and no stated rule for how queries, uniqueness, or retention handle it.
- Sibling modules govern the surrounding tree: [std-structure.md](std-structure.md) for where migrations and fixtures live, [std-yaml-json.md](std-yaml-json.md) for the YAML/JSON documents some engines store, and the language module ([std-python.md](std-python.md), [std-php.md](std-php.md), [std-js.md](std-js.md), [std-go.md](std-go.md)) for the call site that builds the query.

## Schema, Naming, and Data Types

### Identifiers, keywords, and case

Unquoted identifiers are folded by the engine, and the direction differs per engine. PostgreSQL folds to lowercase, Oracle to uppercase, and MySQL/SQLite preserve the case as written. Quoting an identifier in PostgreSQL makes it case-sensitive forever, which is why `"Users"` and `users` become two different relations. MySQL adds a second trap: table-name case sensitivity depends on the filesystem unless `lower_case_table_names` is set, so a schema that works on Windows can fail on Linux.

| Rule                   | Detail                                                                                                                                               |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| Table and column names | `snake_case`, never quoted, never mixed case                                                                                                         |
| Identifier limit       | PostgreSQL 63 bytes, MySQL 64, SQL Server 128, Oracle 128 (30 before 12.2); over-length PostgreSQL identifiers are truncated silently                |
| Keyword case           | Uppercase keywords, lowercase identifiers — one convention for the repo, enforced by the formatter                                                   |
| Table number           | Pick singular or plural and hold it: Django defaults to `<app>_<model>` singular, Rails/ActiveRecord pluralizes, most hand-written schemas pluralize |
| Primary key            | `id`, or `<table>_id` if the repo uses prefixed keys; never both in one schema                                                                       |
| Foreign key            | `<referenced_table_singular>_id` — `orders.customer_id` referencing `customers.id`                                                                   |
| Index                  | `idx_<table>_<columns>`, unique `uq_<table>_<columns>`                                                                                               |
| Constraint             | `fk_<child>_<parent>`, `ck_<table>_<rule>`, `pk_<table>`, `uq_<table>_<columns>`                                                                     |
| Migration              | Tool-dictated: `V1__create_orders.sql` (Flyway), `20240115120000_create_orders.rb` (Rails), `0001_initial.py` (Django)                               |

Auto-generated names are a defect worth fixing explicitly. PostgreSQL derives `<table>_pkey`, `<table>_<column>_key`, `<table>_<column>_fkey`, `<table>_<column>_check`, `<table>_<column>_excl`, and `<table>_<column>_idx`; the `_fkey` name uses only the _first_ column of a composite key, so two foreign keys starting with the same column collide. SQL Server generates constraint names from a hash that differs per database, so a `DROP CONSTRAINT` script written against one environment fails on another. Oracle names unnamed constraints `SYS_Cnnnnnnn`. Name every constraint in the migration.

Reserved words need quoting, and the reserved set differs per engine, so a name that is safe in PostgreSQL may not be in MySQL. The recurring offenders are `order`, `user`, `group`, `table`, `limit`, `offset`, `default`, `comment`, `key`, `schema`, `desc`, `left`, `right`, `case`, `when`, `end`, `interval`, `range`, `rows`, `window`, `filter`, `start`, and `read`/`write` (reserved in MySQL). Prefer a non-reserved synonym (`accounts` instead of `user`, `sort_order` instead of `order`) over quoting: a quoted name is a permanent tax on every query and every ORM mapping.

### Data types

| Concern         | Use                                                                                                            | Never                                                 | Why                                                                                                                 |
| --------------- | -------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| Money           | `numeric(19,4)` or integer minor units (`bigint` cents)                                                        | `float`, `double`, `real`, `money`                    | Binary floating point cannot represent `0.10`; SQL Server's `money` is a non-standard fixed-4-decimal type          |
| Instant in time | `timestamptz` (PostgreSQL), `TIMESTAMP` with UTC convention (MySQL), `datetime2` + `GETUTCDATE()` (SQL Server) | `timestamp`/`timestamp without time zone` for events  | Zone-less columns silently mean "whatever the server's zone was"                                                    |
| Local date      | `date`                                                                                                         | `varchar`                                             | Range queries and arithmetic need a real date type                                                                  |
| Identifier      | `bigint` identity, or `uuid` for externally visible/distributed keys                                           | `varchar(36)` UUIDs, `int` for new high-volume tables | `int4` exhausts at 2.1 billion; `uuid` is 16 bytes and validates input                                              |
| Short text      | `text` / `varchar` without an arbitrary cap                                                                    | `char(n)`                                             | PostgreSQL has no performance difference between `text` and `varchar(n)`, but `char(n)` blank-pads and mis-compares |
| Structured data | `jsonb` (PostgreSQL)                                                                                           | `json` when the column is queried                     | `jsonb` is binary, deduplicates keys, and supports GIN indexing                                                     |
| Boolean         | `boolean`                                                                                                      | `varchar` flags                                       | MySQL's `BOOLEAN` is `TINYINT(1)`; treat it as an integer in the schema, not a string                               |

Three type decisions deserve their own note.

**Timestamps.** PostgreSQL's `timestamptz` stores an absolute instant in UTC and renders it in the session's `TimeZone`; `timestamp` stores a wall-clock reading with no zone. MySQL's `TIMESTAMP` converts between the session zone and UTC and is bounded to `1970-01-01 00:00:01` through `2038-01-19 03:14:07` UTC, while `DATETIME` performs no conversion and spans 1000–9999. SQLite has no date type at all: store ISO-8601 `TEXT` (lexicographic ordering matches chronological ordering), Unix epoch `INTEGER`, or Julian-day `REAL`, and hold one choice per column.

**UUIDs versus bigint.** Random UUIDv4 values scatter inserts across the B-tree, causing page splits and cache misses; time-ordered UUIDv7 (RFC 9562) restores locality. PostgreSQL has `gen_random_uuid()` in core and `uuid` is a first-class 16-byte type; MySQL 8 stores `BINARY(16)` and `UUID_TO_BIN(uuid, 1)` swaps the time fields for index locality; SQL Server has `uniqueidentifier` with `NEWSEQUENTIALID()` for the sequential variant. Generate v7 in the application or with an extension such as `pg_uuidv7`; use `bigint` identity (`GENERATED ALWAYS AS IDENTITY`, not `serial`) when keys never leave the database.

**Enums.** A PostgreSQL native enum is compact but adding a value is DDL, and reordering or removing one requires rebuilding the type and every dependent column. A `text` column with a `CHECK` constraint or a lookup table is portable and changeable with a normal migration. Pick one and use it everywhere; a schema with a native enum, a check constraint, and a lookup table for the same concept has three truths.

### Column ordering, defaults, and soft deletes

Adding a nullable column, or a `NOT NULL` column with a default, is metadata-only in PostgreSQL 11+ and does not rewrite the table; _reordering_ columns does rewrite it, so column order is a one-way decision that should not be churned. MySQL 8.0.12+ can add a column with `ALGORITHM=INSTANT`, but only when the column is appended last, so `ALTER TABLE ... ADD COLUMN` in the middle of a table is a rebuild.

Defaults carry semantics that are easy to get wrong. In PostgreSQL `now()` and `CURRENT_TIMESTAMP` are the _transaction_ start time, identical for every row of a long transaction; `clock_timestamp()` is the wall clock, and `statement_timestamp()` is the statement start. Audit columns want the transaction timestamp; a monotonic event log wants `clock_timestamp()`. In MySQL, `CURRENT_TIMESTAMP` on a `DATETIME`/`TIMESTAMP` is the statement's start time, and `ON UPDATE CURRENT_TIMESTAMP` gives a maintained `updated_at` for free. Sequences and identity columns produce gaps on rollback and on cached blocks; gaps are normal, not a bug to "fix".

Soft deletes cost more than a boolean. A `deleted_at timestamptz NULL` convention requires every read path to filter, breaks every unique constraint (a deleted user still occupies its email), degrades index selectivity as the deleted set grows, and defeats foreign-key integrity because the row still exists. The partial-index fix in PostgreSQL and SQLite is a scoped unique index:

```sql
CREATE UNIQUE INDEX uq_users_email_active
    ON users (email)
    WHERE deleted_at IS NULL;
```

MySQL has no partial indexes; emulate with a stored generated column that nulls out when deleted:

```sql
ALTER TABLE users
  ADD COLUMN email_active VARCHAR(255)
    GENERATED ALWAYS AS (IF(deleted_at IS NULL, email, NULL)) STORED,
  ADD UNIQUE KEY uq_users_email_active (email_active);
```

State the retention rule alongside the convention: what purges soft-deleted rows, and after how long. A soft-delete column with no purge job is an unbounded table.

## Migrations and Schema Change

Migrations are the only path to a schema change. A `CREATE INDEX` typed into a console, a `psql -c "ALTER TABLE ..."` in a deploy script, or a hand-edited `schema.rb` breaks the guarantee that the migration directory describes the database, and the divergence is discovered at the worst possible moment. Commit a migration for every change and make the tooling the sole writer.

| Tool           | Naming                                             | Notes                                                             |
| -------------- | -------------------------------------------------- | ----------------------------------------------------------------- |
| Flyway         | `V1__create_orders.sql`, repeatable `R__views.sql` | Validates checksums of applied migrations                         |
| Alembic        | `alembic revision --autogenerate -m "add status"`  | Autogenerate compares models; review the output, it is a draft    |
| Django         | `0001_initial.py` from `makemigrations`            | `RunPython` needs `migrations.RunPython.noop` as the reverse      |
| Rails          | `20240115120000_create_orders.rb`                  | `db/schema.rb` is derived, never edited                           |
| golang-migrate | `000001_init.up.sql` / `000001_init.down.sql`      | A failed run leaves a `dirty` flag to clear manually              |
| Prisma         | `migrations/<timestamp>_<name>/migration.sql`      | `migrate dev` writes; `migrate deploy` only applies, never resets |

Rules that hold across all of them:

- **Forward-only.** Do not ship a `down` that destroys data in production; roll forward with a new migration. A column rename is not a rename: it is add-new, dual-write, backfill, switch reads, stop writing the old column, drop it later.
- **Never edit an applied migration.** Checksum validation will fail, and environments that already ran it will silently diverge from environments that did not. Fix forward.
- **Migrations must not import application models.** A model that later loses a field breaks a two-year-old migration. Use raw DDL or a frozen table definition.
- **One logical change per migration**, so a partial failure has one cause and the reviewer can reason about one lock.
- **Expand/contract for every destructive change.** Add nullable column → backfill in bounded batches → add the constraint → deploy code that reads it → drop the old column in a later migration, after no deployed revision references it.
- **Know what locks the DDL takes.** PostgreSQL `ALTER TABLE` takes `ACCESS EXCLUSIVE`, which blocks reads as well as writes; set `SET lock_timeout = '3s'` at the top of the migration so it fails fast instead of queueing behind a long query and blocking everything behind it. `CREATE INDEX CONCURRENTLY` avoids the write lock but cannot run inside a transaction block, so it needs its own migration with transactional DDL disabled.
- **Add foreign keys and checks without a long validation scan.** PostgreSQL supports `ADD CONSTRAINT ... NOT VALID` followed by a separate `VALIDATE CONSTRAINT`, and `ADD CONSTRAINT ... UNIQUE USING INDEX` on an index built concurrently.
- **Prefer `CREATE INDEX CONCURRENTLY` for large tables**, and know that the rest of the engines differ: MySQL 8 supports many `ALTER TABLE` operations online via `ALGORITHM=INPLACE, LOCK=NONE`, but a column type change is a copy; SQL Server has online index rebuilds as an Enterprise feature. For MySQL tables too large for an in-place change, `gh-ost` or `pt-online-schema-change` is the escape hatch.
- **Transactional DDL is not universal.** PostgreSQL and SQL Server roll back DDL with the transaction; MySQL and Oracle auto-commit each DDL statement, so a half-applied MySQL migration is a real state you must be able to repair. Do not assume a failed migration is a no-op.
- **Seed data is not fixture data.** Seeds are the reference rows every environment needs (currencies, roles, country codes) and must be idempotent — `INSERT ... ON CONFLICT DO NOTHING` (PostgreSQL/SQLite), `INSERT ... ON DUPLICATE KEY UPDATE` (MySQL), `MERGE` (SQL Server/Oracle). Fixtures are test-scoped and must not be importable by production code. Keep seeds out of the migration checksum path where the tool allows it, and never let a seed overwrite operator-edited rows.

## Query Construction and NULL Semantics

### Parameterization

Values are never concatenated into SQL text. This is not only an injection defense: a literal value produces a different statement text on every call, which defeats plan caching on SQL Server, prevents statement-cache reuse, and makes `pg_stat_statements` group nothing. Bind values and let the driver send query and parameters separately.

```python
cur.execute(
    "SELECT id, email FROM users WHERE email = %s AND status = %s",
    (email, status),
)
rows = cur.fetchall()
```

```javascript
const { rows } = await pool.query(
  "SELECT id, email FROM users WHERE email = $1 AND status = $2",
  [email, status],
);
```

```php
$pdo = new PDO($dsn, $user, $pass, [PDO::ATTR_EMULATE_PREPARES => false]);
$stmt = $pdo->prepare('SELECT id, email FROM users WHERE email = :email AND status = :status');
$stmt->execute(['email' => $email, 'status' => $status]);
```

```go
row := db.QueryRowContext(ctx,
    `SELECT id, email FROM users WHERE email = $1 AND status = $2`, email, status)
```

```java
try (PreparedStatement ps = conn.prepareStatement(
        "SELECT id, email FROM users WHERE email = ? AND status = ?")) {
    ps.setString(1, email);
    ps.setString(2, status);
    try (ResultSet rs = ps.executeQuery()) {
        while (rs.next()) {
            long id = rs.getLong("id");
        }
    }
}
```

`PDO::ATTR_EMULATE_PREPARES` defaults to true for PDO_MYSQL, which makes the driver interpolate client-side rather than using server-side binding; turn it off so the guarantee is the server's. For a variable-length `IN` list, build a placeholder sequence and pass the values as parameters (`WHERE id = ANY($1::uuid[])` in PostgreSQL, `WHERE id IN (?, ?, ?)` elsewhere) — never interpolate the list contents. Parameters can never stand in for identifiers: `ORDER BY $1` does not sort by the column named by the parameter, it sorts by a constant. Route table and column selection through an allowlist map in application code.

### Explicit joins, qualification, and column lists

Write explicit `JOIN ... ON` syntax. A comma join with a forgotten predicate is not a syntax error — it is a cartesian product that succeeds and returns garbage, and it is the single most common way a "correct" query destroys a database. `USING (col)` is a valid shorthand when the joined columns share a name and removes the duplicate column from the output. In MySQL, comma joins have lower precedence than `JOIN`, so `FROM a, b JOIN c ON b.x = c.x` binds `b JOIN c` first, which is rarely what the author meant.

Qualify every column with its table alias in any statement with more than one relation, and alias tables when the name is longer than the alias saves. Unqualified `id` in a three-table join silently resolves to whichever relation the planner picks, and adding a column to one of the tables can change that resolution without changing the query. The `WHERE` clause is also where a `LEFT JOIN` is destroyed: `LEFT JOIN payments p ON p.order_id = o.id WHERE p.status = 'paid'` filters out the null-extended rows and behaves exactly like an inner join; the predicate belongs in the `ON` clause.

`SELECT *` is banned in application code. It transfers columns the caller does not use, prevents index-only scans, breaks positional result handling (`row[3]`) when a column is added, and — paired with `INSERT INTO t VALUES (...)` without a column list — breaks on any column reorder. Enumerate the columns in both directions.

### NULL and three-valued logic

`NULL` means "unknown", and any comparison with it evaluates to `unknown`, which is filtered like false. `col = NULL` is never true, `col <> NULL` is never true, and `NULL = NULL` is unknown. Only `IS NULL` / `IS NOT NULL` and `IS DISTINCT FROM` / `IS NOT DISTINCT FROM` answer the question. The consequences are specific:

- **`NOT IN` with a NULL in the list returns zero rows.** `x NOT IN (1, NULL)` expands to `NOT (x = 1 OR x = NULL)`; for any `x <> 1` the inner expression is unknown, and `NOT unknown` is unknown. Use `NOT EXISTS`, or filter `WHERE col IS NOT NULL` in the subquery.
- **`EXISTS` short-circuits and is NULL-safe** where `IN` is not, which makes `NOT EXISTS` the default anti-join.
- **Aggregates ignore NULLs.** `COUNT(*)` counts rows; `COUNT(col)` counts non-null values. `AVG(col)` divides by the count of non-null values, so a NULL that means "zero" skews the average upward. `SUM` over zero rows returns NULL, not 0 — wrap it: `COALESCE(SUM(amount), 0)`.
- **`GROUP BY` and `DISTINCT` treat all NULLs as equal**, which is the one place SQL does not follow three-valued logic. `ORDER BY` placement is engine-dependent: PostgreSQL sorts NULLs last for `ASC`, MySQL and SQL Server sort them first, Oracle sorts them last. Write `NULLS FIRST`/`NULLS LAST` explicitly when the order matters.
- **Unique constraints permit multiple NULLs.** PostgreSQL 15+ adds `UNIQUE NULLS NOT DISTINCT` when you want the opposite.
- **Empty string is not NULL** in PostgreSQL, MySQL, and SQL Server, but Oracle treats `''` as NULL, so a not-null check that passes on one engine fails on another.

Implicit conversion is the other silent correctness hazard. Comparing a `varchar` column to an integer parameter, or an `nvarchar` column to a `varchar` parameter in SQL Server, makes the engine convert the _column_ rather than the parameter, and a converted column cannot use its index — the plan degrades to a scan with no error and no warning. Collation adds a further divergence: MySQL's `utf8mb4_0900_ai_ci` and SQL Server's default `SQL_Latin1_General_CP1_CI_AS` are case-insensitive, so `WHERE email = 'Alice@Example.com'` matches `alice@example.com` on those engines and does not on PostgreSQL. Check the collation before relying on either behavior, and normalize case in the application when the identifier is a login.

Arithmetic has its own engine divergences: integer division truncates everywhere (`1/2` is `0`), division by zero raises an error in PostgreSQL and SQL Server but returns NULL in MySQL unless strict mode intervenes, and string concatenation differs — `||` in PostgreSQL, SQLite, and Oracle; `CONCAT()` in MySQL (returns NULL if any argument is NULL); `+` in SQL Server, where `CONCAT()` since 2012 treats NULL as an empty string.

## Indexing, Plans, and Query Performance

Indexes are the difference between a millisecond and a minute, and every index is a write tax: each `INSERT`, `UPDATE`, and `DELETE` must maintain all of them. An unused index is pure cost.

- **Index every foreign key on the referencing side.** MySQL creates an index for a foreign key automatically; PostgreSQL and SQL Server do not, so a parent delete or key update scans the child table. Index the referencing column in the same migration that creates the constraint.
- **Composite index column order follows the query.** Equality predicates first, then the range or sort column; the leftmost-prefix rule means an index on `(a, b)` serves `a` and `(a, b)` but not `b`. A separate index on `b` is not a substitute.
- **Index frequent predicates, not every column.** An index on a low-cardinality boolean is nearly useless; a partial index on the selective slice is not: `CREATE INDEX ON orders (created_at) WHERE status = 'pending'` (PostgreSQL, SQLite, and SQL Server's filtered indexes). MySQL has no partial index — use a generated column or a composite index led by the discriminating column.
- **Expression and functional indexes** serve queries that apply a function to the column: `CREATE INDEX ON users (lower(email))` (PostgreSQL, Oracle, SQL Server via a computed column); MySQL 8.0.13+ supports functional key parts as `((lower(email)))`.
- **Covering indexes** avoid the heap fetch: PostgreSQL 11+ `INCLUDE (col)`, MySQL and SQL Server by appending the columns to the key. An index-only scan is only available when every referenced column is in the index and the visibility map is current (PostgreSQL).
- **A changed indexed column prevents HOT updates** in PostgreSQL: the update cannot stay on the same page, so it writes a new heap tuple and updates every index. Marking a frequently-updated column as indexed is a write-amplification decision, not a free one.
- **Indexes bloat.** A long-running transaction or a replication slot holds back the `xmin` horizon, `VACUUM` cannot reclaim dead tuples, and index size grows without bound. Watch `pg_stat_activity` for `state = 'idle in transaction'` and use `REINDEX CONCURRENTLY` (PostgreSQL 12+) to rebuild without a write lock.
- **Find unused indexes before adding more.** `pg_stat_user_indexes.idx_scan`, MySQL's `sys.schema_unused_indexes`, SQL Server's `sys.dm_db_index_usage_stats`. Drop what nothing reads.

### Pagination

`LIMIT n OFFSET m` makes the engine produce and discard `m` rows, so page 5000 costs 5000 times page 1. Keyset (cursor) pagination seeks directly into the index:

```sql
SELECT id, created_at, total
FROM orders
WHERE (created_at, id) < (:last_created_at, :last_id)
ORDER BY created_at DESC, id DESC
LIMIT 20;
```

The row-value comparison is supported by PostgreSQL, MySQL 8, and SQLite; SQL Server does not support row constructors in comparisons and needs the expanded form:

```sql
WHERE created_at < @last_created_at
   OR (created_at = @last_created_at AND id < @last_id)
```

The tiebreaker column is mandatory — without a unique column in the ordering, rows with equal sort keys are skipped or repeated across pages. Keyset pagination requires a stable `ORDER BY` backed by a matching index, gives up random page access (there is no "jump to page 400"), and is the only pagination that stays flat as the table grows.

### N+1 queries

An N+1 is a loop that issues one query per row. It is invisible in development with ten rows and fatal with ten thousand. Every ORM has an eager-loading mechanism; use it rather than querying inside the loop.

| Stack         | Eager load                                                                          | Guard                                           |
| ------------- | ----------------------------------------------------------------------------------- | ----------------------------------------------- |
| Django        | `select_related()` for FK/O2O, `prefetch_related()` for many-to-many and reverse FK | `nplusone`, `django-debug-toolbar` query counts |
| SQLAlchemy    | `selectinload()`, `joinedload()`                                                    | `lazy="raise"` on the relationship              |
| Rails         | `includes()`, `eager_load()`, `preload()`                                           | `strict_loading`, the `bullet` gem              |
| Laravel       | `with()`                                                                            | `Model::preventLazyLoading()`                   |
| JPA/Hibernate | `JOIN FETCH`, `@EntityGraph`                                                        | `hibernate.default_batch_fetch_size`            |
| Prisma        | `include`                                                                           | Log query counts per request in tests           |

Eager-loading collections through joins in the same statement multiplies rows (two collections produce a cartesian product), which is why SQLAlchemy's `selectinload` and Hibernate's batch fetching issue a bounded number of extra queries instead of one joined query. Prefer that shape for collections and a join for to-one relations.

### Read the plan before optimizing

Do not add an index because a query "feels slow". Get the plan, and read the estimated row counts against the actual ones — a large divergence means stale statistics, and stale statistics are the most common cause of a bad plan. PostgreSQL: `EXPLAIN (ANALYZE, BUFFERS)`, with `ANALYZE <table>` to refresh statistics; wrap an `EXPLAIN ANALYZE` of a write statement in `BEGIN; ... ROLLBACK;` so it is not committed. MySQL: `EXPLAIN` and `EXPLAIN ANALYZE` (8.0.18+). SQL Server: the actual execution plan, plus `SET STATISTICS IO ON`. SQLite: `EXPLAIN QUERY PLAN`. Use `SET enable_seqscan = off` in PostgreSQL only as a diagnostic to confirm what the planner would do with an index. Find the worst offenders in aggregate with `pg_stat_statements` (PostgreSQL, requires `shared_preload_libraries`) or `performance_schema.events_statements_summary_by_digest` (MySQL).

## Transactions, Concurrency, and Access Patterns

A transaction is a scope, and the scope should be as small as correctness allows. Holding one open across an HTTP call, a queue publish, or a file upload converts a database problem into a lock convoy. In PostgreSQL a long transaction also pins the `xmin` horizon and blocks vacuum from reclaiming dead tuples, so an idle-in-transaction session is a storage-growth incident.

| Engine       | Default isolation | Notes                                                                                                                                       |
| ------------ | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| PostgreSQL   | `READ COMMITTED`  | Each statement takes a fresh snapshot; `REPEATABLE READ` is snapshot isolation; `SERIALIZABLE` uses SSI and can abort with SQLSTATE `40001` |
| MySQL/InnoDB | `REPEATABLE READ` | Consistent reads use a snapshot; `FOR UPDATE` reads the latest committed row and takes next-key locks                                       |
| SQL Server   | `READ COMMITTED`  | Locking by default; snapshot behavior only when `READ_COMMITTED_SNAPSHOT` is enabled                                                        |
| Oracle       | `READ COMMITTED`  | Statement-level read consistency                                                                                                            |

Set the timeouts, because the defaults are effectively infinite: PostgreSQL `statement_timeout`, `lock_timeout`, and `idle_in_transaction_session_timeout` all default to `0` (disabled); MySQL `innodb_lock_wait_timeout` defaults to 50 seconds; SQL Server's `LOCK_TIMEOUT` defaults to `-1`. Set them per role or per connection, not per query.

Deadlocks and serialization failures are expected outcomes, not bugs: acquire locks in a consistent order across every code path that touches the same rows, and retry the whole transaction on PostgreSQL SQLSTATE `40001` (serialization failure) or `40P01` (deadlock detected), and on MySQL error `1213` (deadlock) or `1205` (lock wait timeout). The retried unit must be idempotent, which means the retry wraps the transaction boundary, not a single statement.

For a queue or job table, do not implement `SELECT` then `UPDATE`: two workers will claim the same row. Use a single locking read with `SKIP LOCKED`, supported by PostgreSQL 9.5+ and MySQL 8.0:

```sql
SELECT id, payload
FROM jobs
WHERE status = 'queued'
ORDER BY created_at
FOR UPDATE SKIP LOCKED
LIMIT 1;
```

Where the work is not a row, PostgreSQL advisory locks (`pg_advisory_xact_lock`) provide a named mutex that releases with the transaction. Both mechanisms are session-level state, which matters for the next point.

Connection poolers change what SQL you can write. PgBouncer in `transaction` pooling mode hands a server connection to a different client between transactions, so session-scoped features — `SET`, `LISTEN`/`NOTIFY`, temporary tables, advisory locks held for the session, and named prepared statements on older PgBouncer versions — behave unexpectedly. Configure the driver accordingly (for example `statement_cache_size=0` with asyncpg) or use session pooling for those workloads. Size the pool against the engine's real limit: PostgreSQL's `max_connections` is one process per connection, and oversubscribing it causes context-switch thrash rather than more throughput.

Normalization is the default; denormalization is a decision with an owner. Keep a table in third normal form until a measured read path requires otherwise, then denormalize deliberately and state the invariant plus the mechanism that repairs it — a trigger, a materialized view refreshed on a schedule (`REFRESH MATERIALIZED VIEW CONCURRENTLY` in PostgreSQL, which requires a unique index), or an application job with a reconciliation query. A denormalized column with no repair path is a permanently stale column, and a second source of truth is exactly the divergence this standardization pass exists to remove.

## Common Mistakes

| Mistake                                                                | Why It Breaks                                                                                     | Correct Approach                                                           |
| ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| `WHERE col = NULL` or `col <> NULL`                                    | Evaluates to `unknown`; returns zero rows and no error                                            | `col IS NULL` / `col IS NOT NULL`, or `IS DISTINCT FROM`                   |
| `WHERE id NOT IN (SELECT user_id FROM bans)`                           | A single NULL in `bans.user_id` makes the whole predicate unknown, so no rows match               | `NOT EXISTS (SELECT 1 FROM bans b WHERE b.user_id = u.id)`                 |
| Comma join with a forgotten predicate                                  | Runs as a cartesian product and returns plausible-looking wrong data                              | Explicit `JOIN ... ON`, and qualify every column                           |
| Predicate on a `LEFT JOIN`ed table in `WHERE`                          | Silently converts the outer join to an inner join and drops the null-extended rows                | Move the predicate into the `ON` clause                                    |
| `SELECT *` in a hot path                                               | Transfers unused columns, blocks index-only scans, breaks positional reads when a column is added | Enumerate the columns; add an `INCLUDE` index if a covering scan is needed |
| `LIMIT 20 OFFSET 100000`                                               | The engine materializes and discards 100000 rows on every page request                            | Keyset pagination on an indexed `(sort_key, unique_key)` pair              |
| Money stored as `float`/`double`                                       | Binary floating point cannot represent decimal fractions; totals drift and reconciliation fails   | `numeric(19,4)` or integer minor units                                     |
| Events stored as `timestamp without time zone`                         | The instant is ambiguous and shifts with the server's zone and daylight saving                    | `timestamptz` / UTC-conventioned `TIMESTAMP` / `datetime2` in UTC          |
| Foreign key column with no index (PostgreSQL, SQL Server)              | Parent deletes and key updates scan the child table                                               | Create the index in the same migration as the constraint                   |
| Comparing a `varchar` column to an integer, or `nvarchar` to `varchar` | The engine converts the column, not the parameter, so the index is unusable                       | Match parameter types to column types exactly                              |
| Case-insensitive collation used for a login identifier                 | `Alice@Example.com` and `alice@example.com` authenticate as the same account                      | Normalize case in the application; index the normalized form               |
| Query built by string concatenation                                    | SQL injection, plus a new statement text per call that defeats plan caching                       | Bound parameters in every driver; allowlist identifiers                    |
| Soft delete with no purge job and no scoped unique index               | Table and indexes grow without bound; a deleted row still holds its unique key                    | Partial unique index on the active rows plus a documented retention job    |
| Constraint left with an auto-generated name                            | `DROP CONSTRAINT` scripts differ per environment; SQL Server's names are per-database hashes      | Name every constraint in the migration                                     |
| Long transaction open across an external call                          | Locks held, vacuum blocked, bloat accumulates, other writers time out                             | Bound the transaction to the database work; move I/O outside it            |
| Query per row in a loop                                                | Query count grows with result size; latency is dominated by round trips                           | Eager-load with the ORM's mechanism; assert the query count in tests       |

## Checklist

1. Inventory every table and column name for case and shape; confirm one convention (`snake_case`, one table-number choice) with no quoted mixed-case identifiers.
2. Verify every constraint and index has an explicit name following the repo's prefix scheme, and that no schema relies on an engine-generated name.
3. Check each foreign key column has an index on the referencing side, and that the constraint's `ON DELETE` behavior is deliberate.
4. Audit money columns: no `float`/`double`/`real`, and a single representation (integer minor units or `numeric`) across the whole schema.
5. Audit timestamp columns: instants are zone-aware or UTC-conventioned, and no column mixes the two conventions.
6. Audit identifier columns: `bigint` identity or a proper UUID type, never `varchar(36)` or an exhausted `int` range.
7. Grep the application for query construction by concatenation, f-string, template literal, or `.format()` and replace every hit with bound parameters.
8. Grep for `SELECT *` and for `INSERT INTO ... VALUES` without a column list in application code; enumerate the columns.
9. Find every `= NULL`, `<> NULL`, and `NOT IN (subquery)` and rewrite them to `IS NULL` and `NOT EXISTS`.
10. Find every `LEFT JOIN` whose joined table is filtered in `WHERE`, and move those predicates into the `ON` clause.
11. Find every `LIMIT ... OFFSET` on a large or growing table and convert it to keyset pagination with a unique tiebreaker and a supporting index.
12. Grep for lazy relationship access inside loops and add the ORM's eager-loading call; add a test assertion on queries per request.
13. Confirm every schema change exists as a committed migration, that no migration has been edited after being applied, and that no console or runbook DDL remains.
14. Review each pending migration for lock level, `lock_timeout`, `CONCURRENTLY` on large-table index creation, and a batched backfill rather than one unbounded `UPDATE`.
15. Confirm destructive changes follow expand/contract and that no deployed code revision references a column being dropped.
16. Confirm soft-delete columns have a scoped unique index for active rows and a documented retention job.
17. Read `EXPLAIN` for the slowest statements, compare estimated against actual rows, refresh statistics, and verify each new index is actually chosen (`idx_scan` moves).
18. Check transaction boundaries: no external calls inside a transaction, timeouts set at the role or connection level, and retry logic on `40001`/`40P01`/`1213`/`1205`.
19. Verify seed data is idempotent, deterministic, and separate from test fixtures.
20. Write the resulting rules into the repository documentation ([std-docs.md](std-docs.md)) so the next agent resolves the same questions from the repo instead of asking.

## References

- [PostgreSQL: Lexical Structure — Identifiers and Key Words](https://www.postgresql.org/docs/current/sql-syntax-lexical.html) — case folding, quoting, the 63-byte identifier limit
- [PostgreSQL: Appendix C. SQL Key Words](https://www.postgresql.org/docs/current/sql-keywords-appendix.html) — reserved versus non-reserved per SQL standard and per engine
- [PostgreSQL: Constraints](https://www.postgresql.org/docs/current/ddl-constraints.html) — default `_pkey`/`_key`/`_fkey`/`_check`/`_excl` naming, `NOT VALID`, `NULLS NOT DISTINCT`, deferrable constraints
- [PostgreSQL: CREATE INDEX](https://www.postgresql.org/docs/current/sql-createindex.html) — `CONCURRENTLY`, `INCLUDE`, partial `WHERE`, expression indexes, `REINDEX CONCURRENTLY`
- [PostgreSQL: Indexes](https://www.postgresql.org/docs/current/indexes.html) — index types, partial and covering indexes, the cost of maintaining indexes on write
- [PostgreSQL: Comparison Functions and Operators](https://www.postgresql.org/docs/current/functions-comparison.html) — `IS DISTINCT FROM`, `IS NULL` semantics
- [PostgreSQL: Data Types](https://www.postgresql.org/docs/current/datatype.html) — `numeric`, `timestamptz`, `uuid`, and why `text`/`varchar` perform identically
- [PostgreSQL: Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html) — the anomalies each level permits and the `40001` serialization failure
- [PostgreSQL: Explicit Locking](https://www.postgresql.org/docs/current/explicit-locking.html) — row lock modes, `SKIP LOCKED`, advisory locks, deadlock avoidance
- [PostgreSQL: Using EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html) — reading estimated versus actual rows, `ANALYZE` and `BUFFERS`
- [PostgreSQL: Routine Vacuuming](https://www.postgresql.org/docs/current/routine-vacuuming.html) — the `xmin` horizon, autovacuum thresholds, and bloat
- [PostgreSQL Wiki: Transactional DDL in PostgreSQL](https://wiki.postgresql.org/wiki/Transactional_DDL_in_PostgreSQL:_A_Competitive_Analysis) — which engines roll DDL back and which auto-commit
- [MySQL: Keywords and Reserved Words](https://dev.mysql.com/doc/refman/8.4/en/keywords.html) — the per-engine reserved set that differs from PostgreSQL's
- [MySQL: Optimization and Indexes](https://dev.mysql.com/doc/refman/8.4/en/optimization-indexes.html) and [EXPLAIN Output](https://dev.mysql.com/doc/refman/8.4/en/explain.html) — `EXPLAIN ANALYZE` since 8.0.18, functional key parts, index merge
- [MySQL: InnoDB Locking and Transaction Model](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking-transaction-model.html) — next-key locks, REPEATABLE READ behavior, deadlock errors `1213` and `1205`
- [MySQL: Online DDL Operations](https://dev.mysql.com/doc/refman/8.4/en/innodb-online-ddl-operations.html) — which `ALTER TABLE` operations are `ALGORITHM=INPLACE` versus a table copy
- [MySQL: Date and Time Types](https://dev.mysql.com/doc/refman/8.4/en/datetime.html) — `TIMESTAMP` UTC conversion and the 2038 bound versus `DATETIME`
- [MySQL: Character Sets and Collations](https://dev.mysql.com/doc/refman/8.4/en/charset.html) — case sensitivity and trailing-space padding (`_ci`, `_bin`, PAD SPACE versus NO PAD)
- [SQL Server: Data Type Conversion](https://learn.microsoft.com/en-us/sql/t-sql/data-types/data-type-conversion-database-engine) — implicit conversion and the data-type-precedence rule that disables index seeks
- [SQL Server: Transaction Locking and Row Versioning Guide](https://learn.microsoft.com/en-us/sql/relational-databases/sql-server-transaction-locking-and-row-versioning-guide) — `READ_COMMITTED_SNAPSHOT`, isolation levels, and blocking
- [SQL Server: Create Filtered Indexes](https://learn.microsoft.com/en-us/sql/relational-databases/indexes/create-filtered-indexes) — the partial-index equivalent
- [SQLite: Datatypes In SQLite](https://www.sqlite.org/datatype3.html) — type affinity, and why `NUMERIC` will happily convert a money value to `REAL`
- [SQLite: Partial Indexes](https://www.sqlite.org/partialindex.html) and [The SQLite Query Optimizer Overview](https://www.sqlite.org/optoverview.html) — partial and expression indexes, and how the planner picks them
- [Oracle: Database Object Names and Qualifiers](https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/Database-Object-Names-and-Qualifiers.html) — the 128-byte identifier limit and case folding
- [Use The Index, Luke: No Offset](https://use-the-index-luke.com/no-offset) — why `OFFSET` degrades and how keyset pagination replaces it
- [RFC 9562: Universally Unique IDentifiers](https://www.rfc-editor.org/rfc/rfc9562.html) — UUIDv7 and the time-ordered layout that preserves index locality
- [OWASP: SQL Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html) — parameterized queries and the identifier allowlist
- [SQLFluff Rules Reference](https://docs.sqlfluff.com/en/stable/reference/rules.html) — `capitalisation.keywords`, `references.qualification`, and the layout rules that enforce this module's conventions
- [Flyway: Migrations](https://documentation.red-gate.com/flyway/flyway-concepts/migrations) — versioned versus repeatable naming and checksum validation
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html), [Django Migrations](https://docs.djangoproject.com/en/stable/topics/migrations/), [Rails Active Record Migrations](https://guides.rubyonrails.org/active_record_migrations.html), [Prisma Migrate](https://www.prisma.io/docs/orm/prisma-migrate), [golang-migrate](https://github.com/golang-migrate/migrate) — migration file naming and forward/backward semantics per tool
- [SQLAlchemy: Relationship Loading Techniques](https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html) and [Laravel: Preventing Lazy Loading](https://laravel.com/docs/eloquent-relationships#preventing-lazy-loading) — the eager-loading APIs and their guard rails
- [PgBouncer Features](https://www.pgbouncer.org/features.html) — what transaction pooling mode breaks, and why session-scoped state is unsafe behind it
- [gh-ost](https://github.com/github/gh-ost) and [pt-online-schema-change](https://docs.percona.com/percona-toolkit/pt-online-schema-change.html) — online schema change for MySQL tables too large for in-place DDL
