# Sales AI 2.0

## Overview

Sales AI 2.0 is an independent reconstruction of an AI-powered e-commerce sales
assistant. It currently includes the Phase 1 foundation and the Phase 2 PostgreSQL product
catalog: typed product specifications, promotion validity, safe repository filters,
repeatable fictional seed data, Alembic migrations, and isolated tests. Phase 3 adds
multilingual intent understanding with deterministic routing between two GPT-OSS models.

## Architecture

- **FastAPI** provides the HTTP boundary and dependency-injection framework.
- **LangGraph** will orchestrate validated query plans in Phase 4; no graph exists yet.
- **Groq API** serves independently configured GPT-OSS 20B and 120B clients on demand.
- **SQLAlchemy 2.x** provides synchronous persistence and request-scoped sessions.
- **PostgreSQL 17** runs locally in Docker and holds transactional product data.
- **RAG** will provide grounded retrieval in a future phase; no ingestion or vector search
  is implemented yet.

## Technology stack

Python 3.12, FastAPI, Pydantic Settings, SQLAlchemy 2.x, Psycopg 3, Alembic,
PostgreSQL 17, Docker Compose, LangGraph, LangChain Core, LangChain Groq, Pytest, and Ruff.

## Installation

From Linux or WSL:

```bash
cd sales-ai-v2
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

## Configuration

Copy the documented template, then replace its development password:

```bash
cp .env.example .env
```

`POSTGRES_PASSWORD` is required. `GROQ_API_KEY` may remain empty for unit tests. The `.env`
file is ignored by Git; never commit it. Configuration is validated at startup and secret
fields use Pydantic's `SecretStr` representation.

For live intent parsing, set the following without committing the key:

```env
GROQ_API_KEY=your_key
GROQ_MODEL_FAST=openai/gpt-oss-20b
GROQ_MODEL_POWERFUL=openai/gpt-oss-120b
GROQ_TIMEOUT_SECONDS=30
GROQ_MAX_RETRIES=2
GROQ_REASONING_EFFORT_FAST=low
GROQ_REASONING_EFFORT_POWERFUL=medium
GROQ_ALLOW_POWERFUL_FALLBACK=true
INTENT_API_ENABLED=true
```

Clients are created lazily on the first intent request. Importing or starting the FastAPI
application does not call Groq. Set `INTENT_API_ENABLED=false` when the endpoint should not
be exposed; production exposure also requires authentication and rate limiting in a future
phase.

## Database

Start and inspect PostgreSQL:

```bash
docker compose up -d
docker compose ps
docker compose logs db
```

Connect from the host (the command prompts for the password from `.env`):

```bash
psql -h 127.0.0.1 -p 55432 -U sales_ai -d sales_ai -W
```

Stop services without deleting persistent data:

```bash
docker compose down
```

Apply and inspect migrations:

```bash
alembic upgrade head
alembic current
alembic check
```

The Phase 2 revision is `20261030_01` (`create_product_catalog_tables`). Downgrades and
`docker compose down -v` are destructive and are never run automatically.

## Product catalog

The catalog uses three tables:

- `products` stores nullable price and availability values without inventing defaults.
- `product_specs` stores unique per-product numeric or textual technical attributes.
- `promotions` stores product/category targets and inclusive date boundaries.

`ProductRepository` supports category, brand, precise price, explicit stock, and multiple
numeric specification filters. `PromotionRepository` returns an offer as current only when
both date boundaries are known and include the injected current date. Repository methods
use SQLAlchemy expressions and injected synchronous sessions; no raw user input is
interpolated into SQL.

Load the fictional development catalog safely:

```bash
python -m app.db.seed
```

The command is idempotent, updates only records already marked as test data, refuses a
stable-name collision with non-test data, and never truncates tables. Seeded products and
offers are fictional development fixtures, not verified Géant inventory.

Run the repository demonstration after migrating and seeding:

```bash
python examples/catalog_demo.py
```

## Phase 3 intent architecture

The NLU flow has four boundaries:

1. `ModelRouter` selects a model using deterministic message features; it makes no LLM call.
2. `LLMService` invokes exactly one selected Groq client with strict JSON Schema output.
3. `QueryPlan` performs Pydantic structural validation on the untrusted response.
4. `QueryValidator` enforces budgets, categories, currencies, references, clarification
   consistency, message limits, and prompt-override rejection.

GPT-OSS 20B is the default for greetings, basic classification, straightforward product
filters, language detection, and explicit product references. GPT-OSS 120B is selected for
multiple intentions, preference trade-offs, highly colloquial Darija, ambiguous comparison
references, complex mixed-language messages, or three or more explicit constraints. A 20B
parse may escalate once after invalid structured output or a clearly inadequate plan. There
is no automatic fallback for authentication failures, and rate-limit/timeout retries remain
bounded in one layer.

Supported language labels are English (`en`), French (`fr`), Modern Standard Arabic (`ar`),
Algerian Darija in Arabic or Latin script (`dz`), mixed language (`mixed`), and `unknown`.
Price normalization recognizes DZD/DA/dinar forms. Colloquial money is normalized only when
the expression and scale are sufficiently clear; otherwise the plan requests clarification.

`QueryPlan` contains the original message, intent, language, category, brand, Decimal price
bounds, currency, explicit stock requirement, numeric specification constraints, product
references, and clarification fields. Every property is required by the model-facing schema;
unknown scalar values are `null` and missing collections are empty arrays. A valid JSON shape
is not considered trustworthy until business validation also succeeds.

Examples:

```text
Find a laptop under 100000 DZD with 16GB RAM.
Je veux un PC portable avec 16 Go de RAM à moins de 100000 DA.
نحتاج حاسوب محمول أقل من 100 ألف دينار.
3tini pc portable b moins de 100000 da.
Compare TEST-LAPTOP-01 and TEST-LAPTOP-02.
وريني les promotions تاع TV.
```

The parser never executes model-generated SQL, performs a product search, invents catalog
facts, or sends a customer message as a system instruction. Provider timeouts, rate limits,
authentication failures, unavailable services, and invalid structured responses have
separate sanitized API errors; credentials and reasoning traces are not logged.

Business-validation failures carry a stable error code, rejected field path, safe reason,
and safe expected-value description. They also preserve model, latency, and token metadata
for callers that need diagnostics. Set `INTENT_VALIDATION_DEBUG=true` only during local
development to emit these sanitized fields; raw customer messages and rejected values are
not logged. Non-recoverable errors such as negative prices do not trigger a larger-model
call.

## Running the API

With `.env` configured:

```bash
uvicorn app.main:app --reload
```

OpenAPI documentation is available at `http://127.0.0.1:8000/docs`.

## API endpoints

- `GET /health` checks the API without requiring PostgreSQL.
- `GET /health/db` runs `SELECT 1`; it returns HTTP 503 without sensitive details when the
  database is unavailable.
- `POST /api/intent/parse` validates a multilingual message and returns its query plan,
  selected model, latency, and token metadata. It does not access the product repository.

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/intent/parse \
  -H 'Content-Type: application/json' \
  -d '{"message":"I need a laptop under 100000 DZD with 16GB RAM"}'
```

## Testing

Unit tests need no Docker, database, internet connection, or Groq key:

```bash
pytest -q
ruff check .
```

PostgreSQL integration tests require an explicitly configured, disposable database whose
name ends with `_test`; the normal `sales_ai` database is rejected:

```bash
export TEST_DATABASE_URL='postgresql+psycopg://USER:PASSWORD@127.0.0.1:55432/sales_ai_test'
pytest -m integration -v
```

Integration tests create and remove only their own catalog tables in that dedicated test
database. They do not create, drop, or reset the development database.

The optional real-Groq test is disabled unless both the flag and key are present:

```bash
RUN_GROQ_INTEGRATION=1 pytest -m groq_integration -v
```

A future live smoke test can use the separately guarded two-request harness. It permits one
request per model, disables retries and escalation, counts at the provider-runnable boundary,
and records validation diagnostics even when the provider response fails business rules:

```bash
CONFIRM_GROQ_SMOKE=YES python scripts/quota_safe_groq_smoke.py --execute
```

Do not run this command as part of unit tests or routine development.

The manually labeled evaluation corpus contains 44 English, French, Arabic, Darija, mixed,
and ambiguity cases. Compare both models on exactly the same cases only when live evaluation
cost is explicitly authorized:

```bash
RUN_GROQ_EVALUATION=1 python -m app.evaluation.intent_eval --model compare
```

The runner reports intent, slot, price, and clarification accuracy, invalid-output rate,
escalation frequency, mean latency, and token usage. No benchmark result is committed or
claimed without executing the live evaluation.

## Project structure

```text
app/api/           HTTP routing modules
app/core/          validated settings and JSON logging
app/db/            SQLAlchemy engine, models, sessions, and repeatable seed data
app/agents/        future LangGraph orchestration
app/tools/         future agent-callable tools
app/services/      intent parser, routing, validation, and Groq client boundary
app/repositories/  product and promotion persistence adapters
app/schemas/       typed catalog filters and read contracts
app/rag/           future retrieval infrastructure
alembic/           database migration environment
data/              local development assets and labeled intent evaluation cases
tests/             isolated unit tests
```

## Planned features and roadmap

- **Phase 1 — Project foundation:** implemented and verified.
- **Phase 2 — Database models, repositories, promotions, seed data, and migrations:**
  implemented.
- **Phase 3 — Dual GPT-OSS multilingual intent understanding:** implemented.
- Later phases: LangGraph orchestration, controlled product tools, RAG, and conversations.

Phase 4 will consume only validated `QueryPlan` objects as LangGraph state, route them to
controlled repository-backed tools, and preserve model metadata for observability. No
LangGraph execution graph, RAG pipeline, authentication, frontend, or CI/CD workflow is
included in Phase 3.
