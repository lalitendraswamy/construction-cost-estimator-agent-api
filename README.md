# Construction Estimator Agent API

Multi-agent construction cost estimator for **Sadhguru Associates** (Visakhapatnam), built with
**LangGraph + LangChain + FastAPI + MongoDB**. It interviews a visitor in English, Telugu or Hindi,
prices a line-item estimate with deterministic tools, answers approval/material questions with RAG,
and hands the lead to the owner with human-in-the-loop confirmation.

> Learning path: **[LEARNING.md](LEARNING.md)** · Design: **[docs/architecture.md](docs/architecture.md)** · Deploy: **[docs/deployment.md](docs/deployment.md)** (Render + Atlas)

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
make install                                           # pip install -e ".[dev]" + pre-commit
cp .env.example .env                                   # add GOOGLE_API_KEY + MONGODB_URI (Atlas)

make indexes seed ingest                               # one-time: indexes, placeholder rates, knowledge base
make check-db                                          # should print "verdict   : READY"
make dev                                               # http://localhost:8000/docs
```

**One database for everything:** local development and the Render deployment share the same
MongoDB Atlas database (`MONGODB_DB=estimator`). Use recognisable thread IDs locally
(e.g. `dev-…`) so test conversations are easy to spot.

Try it:

```bash
curl -s -X POST "localhost:8000/api/v1/chat?stream=false" -H "content-type: application/json" \
  -d '{"thread_id":"demo-thread-1","message":"Naku illu kattali, entha avutundi?"}'
# -> {"event":"interrupt","data":{"type":"ask_user","question":"...","language":"te"}}

curl -N -X POST localhost:8000/api/v1/chat -H "content-type: application/json" \
  -d '{"thread_id":"demo-thread-1","message":"Madhurawada, 200 sq yards"}'      # SSE stream
```

## Commands

| Command | What it does |
|---|---|
| `make test` | unit + integration tests (scripted LLM, no network, ~1 s) |
| `make lint` / `make format` / `make typecheck` | ruff, ruff format, mypy --strict |
| `make graph` | export the LangGraph diagram to `docs/graph.mmd` |
| `make evals` | LangSmith routing eval (real keys, real tokens) |
| `make check-db` | show which MongoDB is configured and whether it is set up |
| `make up` / `make down` | run the API in the production Docker image (against Atlas) |

## API (`/api/v1`)

| Method | Path | Purpose |
|---|---|---|
| POST | `/chat` | `{thread_id, message, input_mode, language?}` → SSE: `progress`, `token`, `interrupt`, `final` (`?stream=false` for JSON) |
| POST | `/chat/resume` | `{thread_id, value}` → answer a pending `interrupt()` explicitly |
| GET | `/threads/{id}` | checkpointed state: spec, estimate, variants, lead, pending interrupt |
| POST | `/voice/transcribe` | 501 in v1 (browser STT); seam for an Indic STT API |
| GET | `/admin/pending` | estimates waiting for owner approval (`X-Admin-Key`) |
| POST | `/admin/approve/{id}` | `{action: approve\|edit, total_inr?}` → resumes the graph |
| GET/PUT | `/admin/rates` | read / upsert rate cards (validated) |
| GET | `/health/live`, `/health/ready` | liveness / readiness (Mongo ping) |

## Project layout

```
src/estimator_agent/
├── main.py                  FastAPI app factory + lifespan
├── core/                    config (pydantic-settings), logging (structlog), errors, LLM registry, security
├── domain/                  pure Pydantic models: ProjectSpec, Estimate, Lead, RateCard, RouteDecision
├── services/                deterministic business logic: units, quantities, pricing, fees, formatting
├── db/                      AsyncMongoClient, indexes, repository protocols + Mongo implementations
├── rag/                     ingest (loaders/splitters) + Atlas Vector Search store/retriever
├── agent/
│   ├── graph.py             parent StateGraph (supervisor + 4 agents + 2 interrupts)
│   ├── state.py             EstimatorState + reducers
│   ├── context.py           runtime context (DI for nodes)
│   ├── routing.py           pure conditional-edge functions
│   ├── runner.py            HTTP <-> graph protocol (resume, streaming, approvals)
│   ├── checkpointer.py      InMemorySaver / MongoDBSaver with allow-listed serializer
│   ├── nodes/               input, supervisor, intake(+ask_user), knowledge, contact, owner_approval, responder
│   ├── subgraphs/estimator/ compiled subgraph: quantities → rates → price → validate(↺) → explain
│   ├── tools/               the 11 PRD tools (typed schemas, HITL confirmations)
│   └── prompts/             one ChatPromptTemplate module per agent
├── api/                     container (composition root), deps, middleware, rate limit, v1 routers
├── schemas/                 API DTOs
└── observability/           LangSmith run config + token usage callback
tests/  unit/ · integration/ (PRD §6 walkthrough runs end-to-end) · evals/ (LangSmith) · fakes.py
scripts/ create_indexes · seed_rates · ingest_kb · export_graph
data/   seed/rate_cards.json (placeholder) · knowledge_base/*.md (placeholder)
```

## Status

All P0 + P1 features are scaffolded and covered by tests with a scripted LLM. **Rates, approval fees
and knowledge-base text are placeholders** (`source: "placeholder"`, which shows a "sample rates" banner)
until Ravikumar supplies real values. Stretch items (F10 `Send` fan-out, PDF, time travel) are
listed as exercises in [LEARNING.md](LEARNING.md#stretch-exercises-p2).
