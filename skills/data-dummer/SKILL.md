---
name: data-dummer
description: Generates seed, fixture, and factory data that satisfies the project's real schema — reading the ORM or migrations first, respecting foreign keys and constraints, generating realistic locale-aware values, and producing a deterministic, re-runnable artifact. Use when the user types /data-dummer, asks for dummy data, seed data, test fixtures, fake records, or a database seeder. Asks for volume, locale, format, and realism before generating.
allowed-tools: Read Write Edit Glob Grep Bash
---

# Data Dummer

Generate dummy data that the project's **actual schema accepts**.

## Why This Is Not a One-Line Prompt

"Buatkan saya data dummy berbentuk seeder untuk project ini" produces a script that looks plausible and fails the moment it runs. The five things that make generated data actually usable, and that a plain prompt omits:

1. **Schema fidelity.** The columns, types, nullability, enums, and lengths come from the real schema — read, not invented. A generator that guesses column names produces a script that crashes on line 3.
2. **Referential integrity.** Foreign keys are satisfied, in dependency order, with parent rows created before children. This is the single most common reason a generated seeder fails.
3. **Determinism.** A fixed seed, so the same command produces the same data. Random seed data makes tests flaky and bug reports unreproducible.
4. **Idempotency.** Re-running the seeder does not duplicate or violate unique constraints.
5. **Locale realism.** Names, addresses, phone numbers, and currencies match the country the user asked for — not `John Doe` for every row.

A generator that gets these right is a tool. One that does not is a liability.

## The Contract

- **Read the schema before writing a line.** Never invent a column, table, enum value, or constraint.
- **Ask the four questions below before generating.** They change the artifact materially.
- **Produce something that runs.** Verify it, do not just emit it.
- **Deterministic by default.** Seeded randomness, and say what the seed is.

## Phase 1 — Read the Schema

Find the source of truth. Do not assume; locate it.

```bash
ls -a
find . -maxdepth 3 \
  \( -name 'schema.prisma' -o -name '*.sql' -o -path '*migrations*' \
     -o -name 'models.py' -o -name 'models.rb' -o -name '*.entity.ts' \
     -o -name 'schema.rb' -o -name '*.model.ts' \) \
  -not -path './node_modules/*' -not -path './.git/*' -not -path './vendor/*' 2>/dev/null | head -40
```

| Stack              | Source of truth                       | Also read                                         |
| ------------------ | ------------------------------------- | ------------------------------------------------- |
| Prisma             | `prisma/schema.prisma`                | `prisma/migrations/` for defaults and constraints |
| Drizzle            | `src/db/schema.ts`                    | migration folder                                  |
| TypeORM            | `*.entity.ts`                         | `ormconfig` / `data-source.ts`                    |
| Sequelize          | `models/*.js`                         | `migrations/`                                     |
| Knex               | `migrations/`                         | seed folder conventions                           |
| Laravel / Eloquent | `database/migrations/`, `app/Models/` | `database/factories/`, `database/seeders/`        |
| Django             | `*/models.py`, `*/migrations/`        | existing `fixtures/`                              |
| Rails              | `db/schema.rb`, `db/migrate/`         | `db/seeds.rb`, `spec/factories/`                  |
| SQLAlchemy         | `models.py`, Alembic `versions/`      | existing session setup                            |
| Raw SQL            | `.sql` DDL                            | —                                                 |
| MongoDB            | Mongoose schemas, or a validator      | —                                                 |

Extract and record, per table: column names, types, nullability, defaults, unique constraints, enums, length limits, and **foreign keys with their direction**.

```bash
grep -rn "ForeignKey\|references\|belongsTo\|hasMany\|@ManyToOne\|FOREIGN KEY" \
  --include='*.py' --include='*.ts' --include='*.rb' --include='*.php' --include='*.sql' \
  . 2>/dev/null | head -40
```

**Build the dependency graph before generating anything.** A table with an FK to another must be populated after it. Cycles (a `users.primary_org_id` and an `orgs.owner_id`) need a two-pass insert: create with nulls, then backfill.

## Phase 2 — Ask Before Generating

Ask these four in one round. Each changes the output materially.

**1. What form should the artifact take?**

| Form                     | Best for                                                | Produces                                                     |
| ------------------------ | ------------------------------------------------------- | ------------------------------------------------------------ |
| **Seeder script**        | Populating a dev or staging database                    | A runnable script (`db/seeds.rb`, `seeders/*.ts`, `seed.py`) |
| **SQL file**             | Environments with no application runtime, or for review | A `.sql` file with explicit `INSERT`s in FK order            |
| **JSON / YAML fixtures** | Test suites, snapshots, deterministic assertions        | Data files loaded by the test framework                      |
| **Factory / builder**    | Tests that need per-case variation                      | Parameterized factories (FactoryBot, factory_boy, Fishery)   |
| **Both**                 | Real projects — bulk data plus test factories           | A seeder for volume, factories for tests                     |

If the user says "seeder", confirm whether they also want factories. They usually do, and it costs nothing to generate both.

**2. How much data?**

Ask for a number per table, or a shape. Vague answers are fine — propose a default and let them adjust:

- **Smoke** (5-20 rows/table) — the app renders and the happy path works.
- **Realistic dev** (100-1,000 rows/table, long-tail distribution) — pagination, search, and sorting are exercised; charts have shape.
- **Load** (100k+ rows) — performance and index behavior. Generate with bulk insert, not an ORM loop.
- **Edge-heavy** (small count, adversarial) — empty strings, max-length values, unicode, nulls where allowed, boundary dates.

**3. Which country / locale?**

This is the question a plain prompt never asks, and it is why generic seed data looks fake.

| Locale  | Names                     | Address                     | Phone               | Currency (formatted by `Intl`) | Gotchas                                           |
| ------- | ------------------------- | --------------------------- | ------------------- | ------------------------------ | ------------------------------------------------- |
| `en_US` | Given + family            | Street, City, ST ZIP        | `(555) 123-4567`    | USD, `$1,234,567.89`           | 5-digit ZIP, state codes                          |
| `en_GB` | Given + family            | Street, Town, Postcode      | `07700 900123`      | GBP, `£1,234,567.89`           | Alphanumeric postcode                             |
| `id_ID` | Indonesian names          | Jalan, Kelurahan, Kecamatan | `+62 812-3456-7890` | IDR, `Rp 1.234.568`            | No family-name convention; many single-word names |
| `de_DE` | Given + family            | Straße, PLZ Ort             | `+49 30 1234567`    | EUR, `1.234.567,89 €`          | Decimal comma, `ß`                                |
| `ja_JP` | Family + given (reversed) | Prefecture, City, Chome     | `090-1234-5678`     | JPY, `￥1,234,568`             | **Zero decimal places**; name order reversed      |
| `ar_SA` | Arabic names              | District, Street            | `+966 5X XXX XXXX`  | SAR                            | RTL text; Hijri dates may be expected             |
| `pt_BR` | Given + family            | Rua, Bairro, CEP            | `+55 11 91234-5678` | BRL, `R$ 1.234.567,89`         | CPF format is 11 digits                           |
| Mixed   | Several locales           | —                           | —                   | —                              | Best for testing i18n; name the distribution      |

Ask for **one primary locale** plus optionally a mixed distribution. Mixed data is the strongest choice when the project is internationalized, because it surfaces formatting bugs.

**Two locale-ID formats, and mixing them is a common crash.** Faker providers take an **underscore** ID (`id_ID`, `ja_JP`) matching POSIX/ICU convention. `Intl` takes a **hyphen** BCP 47 tag (`id-ID`, `ja-JP`) and throws `RangeError: Incorrect locale information provided` on the underscore form. Convert between them when the same locale feeds both a faker provider and a formatter.

```js
// Faker wants id_ID; Intl wants id-ID. This throws:
new Intl.NumberFormat("id_ID"); // RangeError
new Intl.NumberFormat("id-ID").format(1234567.89); // "Rp 1.234.568"
```

Note that `id-ID` renders IDR as `Rp 1.234.568` with a space and no decimals — not `Rp1.234.567`. Never hand-write a currency format; format through the runtime so the output matches what the app actually shows.

**4. How realistic?**

- **Realistic** — plausible names, coherent addresses, correct currency, sensible dates. The default.
- **Synthetic-but-valid** — obviously fake (`Test User 001`) but schema-valid. Best when a human must never confuse it with real data.
- **Adversarial** — unicode, emoji, RTL text, max-length strings, nulls, boundary numbers. Best for finding bugs.

Also confirm, without asking if the answer is discoverable:

- **Deterministic?** Default yes. Pick a seed, state it, make it overridable.
- **Idempotent?** Default yes — truncate-then-insert, or upsert on a natural key.
- **Where does it run?** Local only, or staging too. **Never seed production.** If the user asks for production, refuse and explain.

## Phase 3 — Generate

### Determinism first

Fix the seed before generating anything. Every generator supports this; use it.

```ts
import { faker } from "@faker-js/faker";
faker.seed(42);
```

```python
from faker import Faker
fake = Faker("id_ID")
Faker.seed(42)
```

```ruby
Faker::Config.random = Random.new(42)
```

```php
$faker = Faker\Factory::create("id_ID");
$faker->seed(42);
```

State the seed in the output and make it overridable via an env var or CLI flag. A seeder whose output changes every run cannot be used to reproduce a bug report.

Three seeding nuances that cause flaky data if missed:

- **Python's `Faker.seed()` is class-level.** It seeds the shared RNG for every instance created afterwards. For per-instance control use `fake.seed_instance(42)`, which creates a dedicated RNG and leaves other instances alone.
- **PHP's `$faker->seed()` reseeds the global Mersenne Twister.** Calling it twice in one process resets the sequence; re-seed at the top of the seeder, not per row.
- **Ruby re-seeds by replacing the RNG object.** `Faker::Config.random = Random.new(42)` and setting it to `nil` restores entropy-based seeding.

### Mixed locales: generate one weighted instance, not N branches

When the user asks for a mixed distribution, do not branch per row. Every major faker supports a weighted multi-locale instance, which keeps the data coherent — a Japanese address is not paired with an Indonesian name.

```python
from collections import OrderedDict
from faker import Faker

Faker.seed(42)
fake = Faker(OrderedDict([("id_ID", 8), ("en_US", 1), ("ja_JP", 1)]))
fake.name()          # ~80% Indonesian
fake["ja_JP"].name() # force a specific locale
```

```ts
import { Faker, base, en, id_ID, ja_JP } from "@faker-js/faker";

// Build one instance per locale up front, with `base`/`en` as fallbacks
// so a missing provider entry does not throw at generation time.
const perLocale = {
  id_ID: new Faker({ locale: [id_ID, en, base] }),
  en_US: new Faker({ locale: [en, base] }),
  ja_JP: new Faker({ locale: [ja_JP, en, base] }),
};

const LOCALES = ["id_ID", "id_ID", "id_ID", "id_ID", "en_US", "ja_JP"];
const pick = new Faker({ locale: [en, base] });
pick.seed(42);

const rowFaker = perLocale[pick.helpers.arrayElement(LOCALES)];
rowFaker.person.fullName(); // generated entirely in that locale
```

Generate the whole row from one locale. A row with an Indonesian name and a US ZIP code is worse than a uniform dataset — it is data that cannot exist, and it will produce false confidence when it passes validation.

### Generate in dependency order

1. Topologically sort tables by FK dependency.
2. Generate parents first, collecting their generated IDs.
3. Reference real parent IDs in children — never a hardcoded `1` unless the parent with id 1 is guaranteed to exist.
4. Handle cycles with a two-pass insert.

```ts
const users = await db
  .insert(usersTable)
  .values(
    Array.from({ length: 50 }, () => ({
      email: faker.internet.email(),
      name: faker.person.fullName(),
    })),
  )
  .returning({ id: usersTable.id });

const orders = await db.insert(ordersTable).values(
  Array.from({ length: 200 }, () => ({
    userId: faker.helpers.arrayElement(users).id,
    total: faker.number.int({ min: 10_000, max: 5_000_000 }),
  })),
);
```

### Respect every constraint

- **Enums.** Read the allowed values from the schema. Never invent one.
- **Uniques.** Use a generator that cannot collide (`faker.internet.email()` can; append the index if needed).
- **Length limits.** `VARCHAR(50)` gets a value under 50 characters. Read the limit.
- **Nullability.** Only emit `null` where the column allows it — unless generating adversarial data.
- **Money.** Integer minor units if the schema stores cents; never a float. Match the schema's convention exactly.
- **Timestamps.** Distribute across a plausible range, not all at `now()`. Include some at boundaries — month ends, DST transitions, leap day — when generating adversarial data.
- **Soft deletes.** If the model uses them, seed a realistic proportion of deleted rows.

### Bulk insert for volume

An ORM loop inserting 100k rows one at a time takes hours. Use the bulk path: `createMany`, `bulk_create`, `insert_all`, `COPY`, or a multi-row `INSERT`.

## Phase 4 — Verify

**Run it.** A generated seeder that has never executed is a draft, not a deliverable.

```bash
# Adapt to the project's own command
npx prisma db seed
bun run seed
python manage.py loaddata fixtures/dev.json
php artisan db:seed
bundle exec rails db:seed
psql "$DATABASE_URL" -f seed.sql
```

Then confirm, with real queries:

- [ ] The script runs to completion against a clean database.
- [ ] Row counts match what was requested, per table.
- [ ] No FK violation, no unique violation, no NOT NULL violation.
- [ ] Re-running produces the same result and does not duplicate rows.
- [ ] A representative sample reads as realistic for the chosen locale — spot-check five rows by eye.
- [ ] The app renders the seeded data: list pages paginate, detail pages open, no empty-state-only screens.
- [ ] Nothing points at production. Print the resolved database target before inserting.

```bash
echo "Seeding target: $DATABASE_URL"
```

If the target is not local, stop and confirm with the user.

## Output

```markdown
## Schema Read

- Source: `prisma/schema.prisma` (14 models)
- Dependency order: User → Organization → Project → Task → Comment
- Cycles: none

## Preferences

- Form: seeder script + factories
- Volume: realistic dev — 200 users, 500 projects, 5,000 tasks
- Locale: `id_ID` primary, 20% mixed (`en_US`, `ja_JP`) for i18n coverage
- Realism: realistic
- Deterministic: seed 42, overridable via `SEED`
- Idempotent: yes — truncate then insert

## Files Created

| Path                      | Purpose                         |
| ------------------------- | ------------------------------- |
| `prisma/seed.ts`          | Main seeder, dependency-ordered |
| `tests/factories/user.ts` | Per-test factory                |

## Verification

| Check                 | Result                                    |
| --------------------- | ----------------------------------------- |
| Runs against clean DB | Pass                                      |
| Row counts            | 200 / 500 / 5,000 / 12,400 — as requested |
| Re-run idempotent     | Pass — counts unchanged                   |
| Constraint violations | 0                                         |
| App renders           | `/projects` paginates; detail pages open  |

## Notes

- `ja_JP` rows use JPY with zero decimal places, per the locale.
- Task `dueDate` values span 18 months, not clustered at `now()`.
```

## Common Mistakes

| Mistake                                                | Why It Breaks                                         | Correct Approach                                       |
| ------------------------------------------------------ | ----------------------------------------------------- | ------------------------------------------------------ |
| Inventing column names                                 | The script crashes on the first insert                | Read the schema; never guess                           |
| Inserting children before parents                      | FK violation                                          | Topologically sort; two-pass for cycles                |
| Hardcoding `userId: 1`                                 | Fails when the parent does not exist or is re-seeded  | Reference the generated parent IDs                     |
| Unseeded randomness                                    | Every run differs; bug reports are unreproducible     | Fix the seed; state it; make it overridable            |
| Non-idempotent seeder                                  | Re-running duplicates rows or violates uniques        | Truncate-then-insert, or upsert on a natural key       |
| One ORM call per row at volume                         | Takes hours for 100k rows                             | Bulk insert (`createMany`, `COPY`, multi-row `INSERT`) |
| All timestamps set to `now()`                          | Sorting, ageing, and "last week" views are untestable | Distribute across a plausible range                    |
| Float money                                            | Rounding errors the schema never intended             | Integer minor units, matching the schema               |
| `John Doe` for every locale                            | The data is useless for testing formatting            | Use the locale's faker provider                        |
| Ignoring enum values                                   | Invalid value rejected by the DB                      | Read the enum from the schema                          |
| VARCHAR overflow                                       | Insert truncates or errors                            | Read and respect the length                            |
| Emitting null into NOT NULL                            | Insert fails                                          | Check nullability first                                |
| Emitting null into a nullable column never in practice | Downstream code has no null branch and crashes        | Match the realistic distribution                       |
| Never running the seeder                               | Ships a broken script                                 | Execute it against a clean DB                          |
| Pointing at production                                 | Destroys real data                                    | Print and confirm the target; never seed prod          |
| Only a seeder, no factories                            | Tests still hand-build objects                        | Generate both when the project tests with factories    |
