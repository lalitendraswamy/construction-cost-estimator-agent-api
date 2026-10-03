# What to learn from this scaffold

This repo is a working skeleton, not a finished product. Every PRD concept has a real home in
the code, and the full PRD §6 conversation already runs in a test (`tests/integration/test_conversation_flow.py`)
with a scripted LLM. Your job: **understand each piece, then replace the placeholders and do the exercises.**

How to study each item: open the file → find the concept → run the named test → do the exercise →
answer the interview question out loud. Order follows the PRD build phases.

---

## Phase 0 — Enterprise Python foundations (half a day)

You can't defend an "enterprise" project in an interview if you can't explain its skeleton.

| Learn | Where | What to notice |
|---|---|---|
| `pyproject.toml` (PEP 621), src layout, extras | `pyproject.toml` | `[dev]` optional extra for tooling; ruff + mypy strict + pytest config in one file |
| 12-factor config | `core/config.py` | `pydantic-settings` reads `.env`; `SecretStr`; why `export_provider_env` exists (SDKs read `os.environ`, not your Settings) |
| Structured logging | `core/logging.py`, `api/middleware.py` | `structlog` contextvars: one `request_id` appears on every log line of a request |
| App factory + lifespan | `main.py` | `create_app(settings, container_factory)`: no globals, so tests build their own app |
| Composition root / DI | `api/container.py`, `api/deps.py` | everything long-lived is built **once**; endpoints declare needs with `Annotated[..., Depends()]` |
| Ports & adapters | `db/repositories/protocols.py` vs `mongo.py` vs `tests/fakes.py` | nodes depend on `Protocol`s; Mongo and in-memory are interchangeable |
| Async MongoDB | `db/mongo.py` | PyMongo's native `AsyncMongoClient` (Motor is deprecated) |
| Errors as problem+json | `core/exceptions.py` | domain errors → RFC 9457 responses; one place, not try/except everywhere |
| Pure-ASGI middleware | `api/middleware.py` | why not `BaseHTTPMiddleware` (it buffers / breaks streaming + contextvars) |

**Exercise:** add a `REQUEST_TIMEOUT_SECONDS` setting and enforce it in the middleware.
**Interview Q:** "How would you swap MongoDB for Postgres?" → new repository classes + container; nothing in `agent/` changes.

---

## Phase 1 — LangChain core

| Concept | Where | Notes |
|---|---|---|
| `init_chat_model` + model swap | `core/llm.py` | `"google_genai:gemini-3.5-flash-lite"` for routing, `"google_genai:gemini-3.8-flash"` for explanation. Swapping Gemini models is a `.env` change |
| Model tiers as a cost decision | `ModelRegistry.chat("small" \| "strong")` | nodes ask for a *tier*, never a vendor class |
| `ChatPromptTemplate` + `MessagesPlaceholder` | `agent/prompts/*.py` | `{language_name}` templating = PRD F3 |
| LCEL `prompt \| model \| parser` | `nodes/responder.py`, `subgraphs/estimator/nodes.py::explain_node` | `StrOutputParser` also strips thinking blocks from reasoning models |
| Structured output | `core/llm.py::structured`, `RouteDecision`, `SpecExtraction` | **Why `method="json_schema"`:** Gemini enforces the schema server-side, so a malformed route or spec is impossible; more reliable than parsing tool calls |
| Tools with typed schemas | `agent/tools/*.py` | `@tool(args_schema=PydanticModel)`; factories (closures) inject repos without globals |
| `response_format="content_and_artifact"` | `tools/knowledge.py` | model sees text; code gets the source list on `ToolMessage.artifact` for citations |
| Document loaders, splitters, embeddings, vector store | `rag/ingest.py`, `rag/vectorstore.py` | Markdown header splitter → size splitter; `source_doc` metadata for citations |
| Retriever as a tool | `tools/knowledge.py` | RAG inside a ReAct agent instead of a fixed chain: the agent decides *when* to search |
| Callbacks | `observability/tracing.py`, `agent/runner.py::_stream` | `UsageMetadataCallbackHandler` totals tokens per model per turn (cost per estimate) |
| LangSmith tracing | `.env` `LANGSMITH_*` + `turn_config()` | run name, tags, `thread_id` metadata → searchable traces |

**Exercises**
1. Run `make ingest` (Gemini embeddings, free), then switch the retriever to `search_type="mmr"` and compare answers.
2. Add a `language` pre-filter to the retriever (the vector index already declares it as a filter field).
3. Write `test_explain_drops_numbers` that scripts the strong model to return a digit and asserts `summary is None`.

---

## Phase 2 — LangGraph core (the most important phase)

| Concept | Where | Must be able to explain |
|---|---|---|
| `StateGraph` + typed state | `agent/state.py`, `agent/graph.py` | each key is a *channel* |
| Reducers | `state.py` | `add_messages` (append/update by id), `operator.add` (`variants`), **custom `merge_spec`** (patch only the fields set → what-if F8) |
| Nodes, normal edges | `graph.py` | `START → input → supervisor` |
| Conditional edges | `routing.py` | pure functions → unit-tested in `tests/unit/test_state_and_routing.py` |
| `Command(goto=…, update=…)` routing | `nodes/intake.py` | the node decides and writes state in one return; `Command[Literal[...]]` annotation draws the edges |
| Cycles | `ask_user → intake`, `validate → fetch_rates` | loops are just edges back; guard them (retry once) |
| Runtime context vs state | `agent/context.py`, `Runtime[AgentContext]` in every node | context = dependencies (not checkpointed), state = data (checkpointed) |
| Checkpointer + `thread_id` | `agent/checkpointer.py`, `observability/tracing.py::turn_config` | memory per conversation; survives across HTTP requests; `InMemorySaver` dev → `MongoDBSaver` prod |
| Serializer allow-list | `checkpointer.py::build_serializer`, `domain/__init__.py::CHECKPOINT_TYPES` | a tampered checkpoint DB can't make you import arbitrary classes |
| `interrupt()` + `Command(resume=…)` | `nodes/intake.py::ask_user_node`, `agent/runner.py` | the graph **pauses**, the HTTP request ends, the next request resumes it |
| **Node re-execution on resume** | `ask_user_node`, `await_approval_node`, `tools/contact.py` | on resume the node runs *from the top*. Keep LLM calls and side effects **out** of interrupting nodes. This is the #1 interview trap |
| Supervisor multi-agent | `nodes/supervisor.py` + `routing.py` | LLM classifies, code routes (ADR 0001) |
| Graph visualisation | `make graph` | `get_graph(xray=1).draw_mermaid()` expands subgraphs |

**Run:** `pytest tests/integration/test_conversation_flow.py::test_prd_walkthrough_turns_1_to_5 -v`, then
put a breakpoint in `ask_user_node` and watch it run twice: once to pause, once to resume.

**Exercises**
1. Move the question-generation LLM call *into* `ask_user_node` and write a test that counts LLM calls. See the double billing. Revert.
2. U5 mid-interview: if the user answers an Intake question with a question ("what is VUDA?"), route `ask_user` → `supervisor` instead of `intake`. Hint: classify the resume value, return `Command(goto=...)`.
3. Switch `.env` to `CHECKPOINTER=mongodb`, restart the API mid-interview, and resume the thread.

**Interview Qs:** What happens to state when two nodes write the same key in one step? (reducer, or
`InvalidUpdateError`). Why is `missing_fields` computed and not trusted from the LLM?

---

## Phase 3 — Estimator subgraph + RAG

| Concept | Where | Notes |
|---|---|---|
| Compiled subgraph as a node | `subgraphs/estimator/graph.py` | own `StateGraph`, compiled, `add_node("estimator", subgraph)` |
| `input_schema` / `output_schema` | `subgraphs/estimator/state.py` | private keys stay private; **without `output_schema`, `variants` would be duplicated** by the parent's `operator.add` (read the docstring) |
| Checkpointer inheritance | subgraph `compile()` has no checkpointer | it inherits the parent's |
| `RetryPolicy` | `fetch_rates` node | `retry_on=is_transient`: retry DB blips, never business errors |
| Validate-and-retry loop | `validate_node`, `route_after_validate` | bad rate card → retry with the default city → else flag; tested in `test_validator_retries_with_default_city_rates` |
| Custom stream events | `agent/streaming.py::emit_progress` | `get_stream_writer()` → `stream_mode="custom"` → "Calculating rates…" in the UI |
| Prebuilt ReAct agent | `nodes/knowledge.py` | `create_agent(model, tools, system_prompt)`, the v1 successor of `create_react_agent` |
| Deterministic tools | `tools/estimation.py`, `services/pricing.py` | PRD formula `A×R + F + C + k×subtotal`, ±8% range (ADR 0002) |

**Exercises**
1. Replace the placeholder coefficients in `services/quantities.py` and `data/seed/rate_cards.json` with Ravikumar's numbers, then update the expected totals in the tests.
2. Move the approval-fee schedule from code into Mongo (new repository + admin endpoint).

---

## Phase 4 — Contact + owner approval (human-in-the-loop, twice)

| Concept | Where | Notes |
|---|---|---|
| HITL inside a tool | `tools/contact.py::require_confirmation` | `interrupt()` *inside* a tool inside a `create_agent` subgraph; nested interrupts surface to the parent |
| Validate before the interrupt | `book_meeting`, `notify_owner` | phone normalisation happens first, then confirm, then the side effect |
| Approval gate | `nodes/owner_approval.py` | split into `request_approval` (side effects, runs once) and `await_approval` (only `interrupt()`) |
| Idempotency | `ApprovalRepository.upsert_pending` returns `created` | notify the owner only on first creation |
| Admin resume | `api/v1/admin.py` → `runner.resume_owner_approval` | `Command(resume={"action": "edit", "total_inr": ...})` from a *different* user |
| Don't leak unapproved numbers | `runner.py::_public_interrupt` | the user sees "under review", never the estimate |

**Run:** `test_estimate_over_one_crore_waits_for_owner` and `test_contact_tool_waits_for_confirmation`.

**Exercise:** add `action: "reject"` with a reason that the Responder explains politely.

---

## Phase 5 — Streaming, API, voice

| Concept | Where | Notes |
|---|---|---|
| Multi-mode streaming | `runner.py::_stream` | `stream_mode=["updates","messages","custom"]`, `subgraphs=True` → `(namespace, mode, chunk)` |
| Token streaming from one node only | filter `meta["langgraph_node"] == "responder"` | internal LLM calls (router, extractor) are never shown |
| SSE | `api/v1/chat.py` | `sse-starlette`; event types `progress/token/interrupt/final/error`; `?stream=false` for curl |
| Resume protocol | `runner.py::stream_message` | the client just keeps POSTing `/chat`; the server decides run vs resume |
| I/O-agnostic graph | `tools/language.py` | voice is an adapter (`input_mode`), the graph doesn't change |
| Rate limiting | `api/rate_limit.py` | per-IP via slowapi; needs Redis storage once you run more than one replica |

**Exercise:** build the Next.js widget: `fetch` + `ReadableStream` SSE parser, render `progress` as a
status line, `interrupt.type=confirm_action` as Yes/No buttons that POST `/chat/resume`.

---

## Phase 6 — Testing and evaluation (what makes it "enterprise")

| Concept | Where |
|---|---|
| Scripted fake LLM (supports structured output and tool calls) | `tests/fakes.py::ScriptedChatModel` |
| Testing the *compiled* graph, not mocks of it | `tests/integration/test_conversation_flow.py` |
| HTTP contract tests with an injected container | `tests/integration/test_api.py` |
| LangSmith dataset + evaluator | `tests/evals/run_evals.py` (`make evals`) |

**Exercise:** grow `tests/evals/dataset.jsonl` to the PRD's 15 multi-turn conversations and add
evaluators for "estimate only after spec complete" and "reply language == state.language".

---

## Stretch exercises (P2)

1. **`Send` fan-out (F10):** a `compare_tiers` node returning `[Send("price_tier", {...tier}) for tier in QualityTier]`; results fan in through the `variants` reducer (`operator.add` is already there for this).
2. **Time travel:** `graph.aget_state_history(config)` → "go back to the previous estimate" via `update_state` on an older checkpoint.
3. **PDF quote:** render `Estimate` with WeasyPrint/ReportLab in a new endpoint.
4. **Real auth:** replace `X-Admin-Key` with OAuth/JWT; add per-user rate limits.
5. **Durability modes:** compare `durability="sync"|"async"|"exit"` on `astream` and measure latency.

## Gotchas this scaffold already handles (know *why*)

* Gemini 2.5 is closed to new projects → defaults are Gemini 3.x (`gemini-3.5-flash-lite`, `gemini-3.8-flash`, `gemini-embedding-2`).
* Gemini 3 is tuned for its default temperature → we no longer force `temperature=0`; determinism comes from structured output.
* `with_structured_output(method="json_schema")` → schema enforced server-side by Gemini.
* Free tier = low requests-per-minute; one chat turn makes 3–5 LLM calls → `LLM_MAX_RETRIES=3` backs off on 429.
* Nodes that `interrupt()` re-run on resume → side effects live in separate nodes or after the interrupt.
* Subgraph `output_schema` prevents reducer double-counting.
* Romanised Telugu ("naku illu kattali") isn't detectable by script → LLM fallback; "G+1, standard" keeps the previous language.
* Telugu vowel signs aren't `\w` in Python regex → `is_affirmative` splits on whitespace.
* Windows has no tz database → IST as a fixed offset, no `tzdata` dependency.
* `/health/ready` ping is bounded at 2 s so probes fail fast.

## Interview talking points you can now back with a file + test

| Claim | File | Proof |
|---|---|---|
| Supervisor multi-agent graph, typed state, reducers, subgraph | `agent/graph.py`, `agent/state.py` | `make graph`, walkthrough test |
| Two kinds of `interrupt()` + checkpointer across HTTP requests | `nodes/intake.py`, `nodes/owner_approval.py` | approval test |
| LLM kept out of arithmetic | `services/pricing.py`, ADR 0002 | `test_price_estimate_formula` |
| RAG as a retriever tool in a ReAct agent on Atlas Vector Search | `tools/knowledge.py`, `rag/` | `test_knowledge_question_cites_source` |
| Language and modality live in state | `nodes/input.py`, `nodes/responder.py` | Telugu disclaimer assertion |
| Traced and evaluated in LangSmith | `observability/`, `tests/evals/` | `make evals` |
