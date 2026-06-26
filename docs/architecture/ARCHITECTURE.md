# PAIOS — Architecture Reference

**Status:** Living Document  
**Version:** 2.0  
**Last updated:** 2026-06-25

---

## 0. Philosophy

> **PAIOS is a Cognitive Operating System. The LLM is a replaceable component.**

This is the most important sentence in this document. Every architectural decision flows from it.

PAIOS is not a chatbot. It is not an agent framework. It is not a RAG pipeline.

It is an operating system that:

- **Acts** — creates and executes missions without waiting for user input
- **Learns** — builds knowledge and memory over time from all interactions
- **Reacts** — responds to events, rules and schedules, not only to messages
- **Observes** — monitors its own components and the environment
- **Coordinates** — routes events between components through a typed contract

The chat interface is one input channel, equivalent in importance to the scheduler, the inbox and the event bus. None of them is the center of the system. The **Kernel** is the center.

---

## 1. Layer Model

```
┌─────────────────────────────────────────────────────────────────┐
│  INTERFACES                                                       │
│  Chat · CLI · Telegram · Dashboard · API · Webhook               │
├─────────────────────────────────────────────────────────────────┤
│  DOMAIN ENGINES                                                   │
│  MissionEngine · KnowledgeEngine · MemoryEngine                  │
│  PromptEngine · RAGEngine · PluginEngine · ObsidianEngine        │
├─────────────────────────────────────────────────────────────────┤
│  COORDINATION                                                     │
│  Kernel Runtime · EventBus · CapabilityRegistry · Scheduler      │
├─────────────────────────────────────────────────────────────────┤
│  PLAN SYSTEM                                                      │
│  PlanProvider · PlanValidator · WorkflowEngine                   │
├─────────────────────────────────────────────────────────────────┤
│  PROVIDERS (Abstraction Layer)                                    │
│  LLMProvider · EmbeddingProvider · StorageProvider               │
│  EventBusProvider · NotificationProvider · SearchProvider        │
│  PlannerProvider                                                  │
├─────────────────────────────────────────────────────────────────┤
│  INFRASTRUCTURE                                                   │
│  PostgreSQL + pgvector · Ollama · Redis · Docker                  │
└─────────────────────────────────────────────────────────────────┘
```

**Rule:** each layer may only depend on the layer directly below it.  
An engine must never import from an interface. A provider must never import from an engine.  
The Kernel coordinates; it does not implement domain logic.

---

## 2. Component Map

```
apps/api/
│
├── kernel/                 COORDINATION LAYER
│   ├── config/             — Settings via env vars (pydantic-settings)
│   ├── logger/             — Structured JSON logging (structlog)
│   ├── events/             — EventBus + KhonshuEvent envelope
│   ├── capabilities/       — CapabilityRegistry (semantic)
│   ├── permissions/        — Permission engine per workspace
│   ├── plugins/            — 6 built-in plugins (ntfy, weather, search, HA, Notion, GCal)
│   ├── providers/          — OllamaProvider (LLM + embeddings)
│   └── agents/             — Background workers (memory, task, summarizer)
│
├── engines/                DOMAIN LAYER
│   ├── memory/             — MemoryEngine (RRF recall, remember, supersede)
│   ├── mission/            — MissionEngine (state machine, lifecycle)
│   ├── plan/               — PlanProvider interface + LLM + Workflow implementations
│   ├── prompt/             — PromptEngine (dynamic system prompt)
│   ├── rag/                — RAGEngine (ingest, retrieve, fallback)
│   ├── plugin/             — PluginEngine (enable/disable per workspace)
│   └── obsidian/           — ObsidianEngine (vault sync, graph, RAG ingest)
│
├── models/                 PERSISTENCE
│   ├── workspace.py
│   ├── memory.py
│   ├── conversation.py
│   ├── document.py
│   ├── mission.py          — Mission, ExecutionPlan*, MissionStep, Context, Artifact, Log
│   ├── obsidian.py
│   └── workspace_plugin.py
│
├── routers/                INTERFACE LAYER (HTTP)
│   ├── workspaces.py
│   ├── conversations.py    — chat + SSE streaming
│   ├── documents.py
│   ├── memories.py
│   ├── missions.py         — full lifecycle endpoints
│   ├── obsidian.py
│   └── plugins.py
│
└── schemas/                REQUEST / RESPONSE (Pydantic)

apps/web/                   FRONTEND (Next.js 15)
├── src/app/api/[...path]/  — SSE-safe proxy (pipes upstream.body directly)
├── src/app/chat/           — chat interface
├── src/app/graph/          — Obsidian knowledge graph
└── src/components/

scripts/
└── sync_obsidian.py        — incremental Obsidian vault sync

docs/architecture/
├── ARCHITECTURE.md         — this document
├── mission-lifecycle.md    — state machine + sequence + data model
├── OBSERVABILITY.md        — metrics catalog
└── adr/                    — Architecture Decision Records
```

*`ExecutionPlan` is documented as a separate entity in ADR-001 and mission-lifecycle.md. Current code uses `mission_steps` directly linked to `missions`; `ExecutionPlan` is the next evolution step for replanning support.*

---

## 3. Provider Abstraction Layer

No layer above Providers may import a concrete implementation.  
All engines and the Kernel depend exclusively on interfaces.

This guarantees that replacing Ollama with another LLM, PostgreSQL with another store, or Redis with another message broker requires zero changes in domain logic.

### 3.1 Defined Providers

#### LLMProvider
```python
class LLMProvider(Protocol):
    async def generate(prompt: str, system: str | None) -> GenerateResult: ...
    async def stream(prompt: str, system: str | None) -> AsyncIterator[str]: ...
    async def chat(messages: list[ChatMessage]) -> GenerateResult: ...
    async def chat_stream(messages: list[ChatMessage]) -> AsyncIterator[str]: ...
```
Current implementation: `OllamaProvider` (Ollama REST API).  
Could be replaced by: Anthropic, OpenAI, local llama.cpp, vLLM.

#### EmbeddingProvider
```python
class EmbeddingProvider(Protocol):
    async def embed(text: str) -> EmbedResult: ...
    async def embed_batch(texts: list[str]) -> list[EmbedResult]: ...
```
Current implementation: `OllamaProvider` with `nomic-embed-text`.  
Could be replaced by: sentence-transformers, OpenAI embeddings, Cohere.

#### EventBusProvider
```python
class EventBusProvider(Protocol):
    async def publish(event: KhonshuEvent) -> None: ...
    async def subscribe(event_type: str, handler: TypedEventHandler) -> None: ...
    async def connect() -> None: ...
    async def disconnect() -> None: ...
```
Current implementation: PostgreSQL LISTEN/NOTIFY (asyncpg).  
Could be replaced by: Redis Streams, RabbitMQ, Kafka.  
See ADR-002 for the typed event contract that insulates this replacement.

#### StorageProvider
```python
class StorageProvider(Protocol):
    async def store(key: str, data: bytes, metadata: dict) -> str: ...
    async def retrieve(uri: str) -> bytes: ...
    async def delete(uri: str) -> None: ...
```
Used by: MissionArtifacts, Knowledge Engine, Inbox (future).  
Current implementation: local filesystem.

#### NotificationProvider
```python
class NotificationProvider(Protocol):
    async def notify(title: str, body: str, priority: int) -> None: ...
```
Current implementation: ntfy plugin.  
Could be replaced by: Telegram bot, email, Slack.

#### SearchProvider
```python
class SearchProvider(Protocol):
    async def search(query: str, limit: int) -> list[SearchResult]: ...
```
Current implementation: DuckDuckGo plugin.

#### PlannerProvider
```python
class PlannerProvider(Protocol):
    name: str
    async def create_execution_plan(mission: Mission) -> ExecutionPlan: ...
```
Implementations: `LLMPlanProvider`, `WorkflowPlanProvider`, `ManualPlanProvider`.  
See Section 6 and ADR-001.

---

## 4. Event System

### 4.1 Domain Events vs Infrastructure Events

This is one of the most important structural boundaries in PAIOS. Conflating the two creates coupling between business logic and infrastructure — a violation of the dependency rule that makes the system brittle over time.

**Domain Events** represent something meaningful that happened in the business domain. They are immutable facts. Other domain components may react to them. They are always named in past tense.

```
MissionCreated       — a mission was created
MissionCompleted     — a mission finished successfully
KnowledgeUpdated     — knowledge graph changed
MemoryCreated        — a memory was stored
DocumentIngested     — a document entered the system
TaskCompleted        — a task agent completed work
WorkspaceCreated     — a new workspace was provisioned
SchedulerFired       — a scheduler trigger activated
```

**Infrastructure Events** represent technical state changes within the system's own components. Domain engines must never subscribe to infrastructure events. Infrastructure monitors subscribe to them for observability.

```
PluginLoaded         — a plugin was registered at startup
LLMAvailable         — Ollama became reachable
DatabaseConnected    — pool established
EventBusConnected    — pub/sub channel ready
ContainerStarted     — a Docker container started (from Docker plugin)
HTTPRequestReceived  — an API request arrived
EmbeddingCacheHit    — embedding was served from cache
```

**Why the separation matters:**  
If the Mission Engine subscribes to `ContainerStarted` to trigger health checks, it now depends on Docker's infrastructure. When Docker is replaced, the Mission Engine needs to change. The rule is: domain components publish and subscribe only to domain events. Infrastructure events are consumed by monitoring and infrastructure components exclusively.

See ADR-002 for the full rationale.

### 4.2 Event Envelope

Every event in PAIOS — domain or infrastructure — uses the same envelope:

```python
@dataclass
class KhonshuEvent:
    id:             UUID       # unique event identifier
    type:           str        # "mission.created", "knowledge.updated", ...
    version:        str        # schema version, e.g. "1.0"
    workspace_id:   UUID       # tenant isolation
    correlation_id: UUID       # shared across an entire causal chain
    causation_id:   UUID|None  # the direct parent event
    actor:          str        # who triggered: "user"|"scheduler"|"agent"|"system"
    source:         str        # which component: "chat"|"scheduler"|"mission"|"inbox"
    payload:        dict       # event-specific data
    metadata:       dict       # cross-cutting: trace_id, session_id, etc.
    priority:       int        # 0 (low) to 9 (critical)
    occurred_at:    datetime   # wall-clock UTC time of the original fact
```

**`correlation_id`** — The same UUID is shared by every event in a single causal chain. Example: a user sends a message → `correlation_id=X` flows through `MessageReceived`, `MissionCreated`, `MissionCompleted`, `MemoryCreated`, `NotificationSent`. With one query you reconstruct the full trace of a user action.

**`causation_id`** — Points to the `id` of the direct parent event. While `correlation_id` lets you find all events in a chain, `causation_id` lets you reconstruct the directed graph of causation. Useful for debugging: "this notification was caused by this step failure, which was caused by this mission."

**`version`** — Events evolve. A consumer reading version `1.0` of `mission.created` must not break when version `1.1` adds a new field. Producers increment minor versions for additive changes, major for breaking changes. Consumers should be tolerant of unknown fields.

### 4.3 Registered Domain Event Types

| Type | Published by | Description |
|---|---|---|
| `mission.created` | MissionEngine | Mission record created |
| `mission.planning` | MissionEngine | Planning started |
| `mission.ready` | MissionEngine | Plan approved, ready to run |
| `mission.running` | MissionEngine | Execution started |
| `mission.step.started` | MissionEngine | A step began |
| `mission.step.completed` | MissionEngine | A step succeeded |
| `mission.step.failed` | MissionEngine | A step failed |
| `mission.completed` | MissionEngine | All steps succeeded |
| `mission.failed` | MissionEngine | Mission failed unrecoverably |
| `mission.cancelled` | MissionEngine | Mission cancelled by request |
| `document.ingested` | RAGEngine / Inbox | Document processed and embedded |
| `knowledge.updated` | KnowledgeEngine | Entity, fact or relation changed |
| `memory.created` | MemoryEngine | A memory was persisted |
| `scheduler.fired` | Scheduler | A trigger activated |
| `workspace.created` | WorkspaceRouter | New workspace provisioned |

---

## 5. Capability Registry

The CapabilityRegistry is the single source of truth about what PAIOS can do.  
Plugins do not expose methods. They expose **capabilities** — semantic descriptions of what they can accomplish.

This distinction matters for the Planner: it must ask "who can manage containers?" not "does `docker.restart()` exist?". The former survives plugin refactoring; the latter breaks on every rename.

### 5.1 Capability Schema

```yaml
name: container_management

description: >
  Manage Docker containers: start, stop, restart, inspect containers,
  stream logs, read real-time CPU/memory metrics, and execute commands
  inside running containers.

plugin: docker

permissions:
  - infrastructure.docker.read
  - infrastructure.docker.write

required_context:
  - docker_socket_path     # or DOCKER_HOST env var

tools:
  - name: docker.start
    description: Start a stopped container by name or ID
    parameters:
      container: string

  - name: docker.stop
    description: Stop a running container gracefully
    parameters:
      container: string
      timeout:   integer (default 10)

  - name: docker.logs
    description: Stream the last N lines of container logs
    parameters:
      container: string
      lines:     integer (default 100)
      since:     string (duration, e.g. "1h")

  - name: docker.stats
    description: Get CPU, memory and network metrics for a container
    parameters:
      container: string

  - name: docker.exec
    description: Execute a command inside a running container
    parameters:
      container: string
      command:   string

events_consumed:
  - scheduler.fired       # e.g. for scheduled health checks

events_produced:
  - infrastructure.container.started
  - infrastructure.container.stopped
  - infrastructure.container.unhealthy

dependencies:
  - docker daemon reachable at docker_socket_path

tags:
  - infrastructure
  - docker
  - observability
```

### 5.2 Why This Structure

`permissions` — allows the PlanValidator to refuse execution if the current workspace does not hold the required permissions before a single line of tool code runs.

`required_context` — makes missing prerequisites detectable at plan validation time, not at runtime.

`events_consumed / events_produced` — documents the reactive contract. The Scheduler can fire events that Docker consumes. Other capabilities can react to events Docker produces.

`dependencies` — enables health-checking: the Kernel can verify all capability dependencies are satisfied before accepting a mission that uses them.

See ADR-004 for the full rationale for semantic capabilities over method catalogs.

---

## 6. Mission System

The Mission System is the heart of PAIOS. It is what separates a cognitive OS from a chatbot.

### 6.1 Separation: Mission / ExecutionPlan / MissionStep

Three distinct entities with distinct responsibilities:

```
Intent (natural language)
    │
    ▼
Mission          ← persistent objective; survives replanning
    │
    ▼
PlanProvider     ← selects strategy
    │
    ▼
ExecutionPlan    ← a specific strategy; may be superseded
    │
    ▼
PlanValidator    ← verifies permissions, capabilities, parameters
    │
    ▼
MissionStep[]    ← executable actions; audit trail
    │
    ▼
Executor         ← runs tools via CapabilityRegistry
```

**Mission** represents the objective. It exists from creation to completion or cancellation. It does not change when the plan changes. It carries the `intent`, `status`, `trigger` and workspace ownership.

**ExecutionPlan** represents a specific strategy for the mission. A mission may have multiple plans over its lifetime — the first attempt fails, the mission is replanned with a different PlanProvider, a new ExecutionPlan is created while the old one is marked `superseded`. This is the entity that receives human approval. See ADR-001 for the full rationale.

**MissionStep** represents a single executable action within a plan. It belongs to an `ExecutionPlan`, not directly to a Mission. It is the unit of: retry logic, parallelism, dependency tracking, auditing, metrics collection. Steps are never deleted, only marked `skipped` or `failed`.

### 6.2 Data Model

```
missions
├── id                UUID PK
├── workspace_id      UUID FK→workspaces CASCADE
├── intent            TEXT NOT NULL
├── status            mission_status enum
├── trigger           mission_trigger enum  (manual|scheduled|event|rule)
├── requires_approval BOOLEAN DEFAULT false
├── created_at        TIMESTAMPTZ
├── updated_at        TIMESTAMPTZ
└── completed_at      TIMESTAMPTZ

execution_plans                         ← separate entity (planned evolution)
├── id                UUID PK
├── mission_id        UUID FK→missions CASCADE
├── version           INTEGER NOT NULL    ← plan A=1, after replan B=2
├── provider          TEXT                ← which PlanProvider generated this
├── status            plan_status enum    (draft|validated|approved|executing|superseded|failed)
├── created_at        TIMESTAMPTZ
└── metadata          JSONB               ← planner config, token count, etc.

mission_steps
├── id                UUID PK
├── mission_id        UUID FK→missions    (denormalized for query convenience)
├── execution_plan_id UUID FK→execution_plans CASCADE
├── parent_step_id    UUID FK→mission_steps SET NULL  (parallel/nested steps)
├── order             INTEGER NOT NULL
├── type              step_type enum      (tool|workflow|agent|human)
├── tool              TEXT                (capability tool name)
├── input             JSONB
├── output            JSONB
├── status            step_status enum    (pending|running|succeeded|failed|skipped)
├── started_at        TIMESTAMPTZ
├── finished_at       TIMESTAMPTZ
└── retry_count       INTEGER DEFAULT 0

mission_contexts
├── id                    UUID PK
├── mission_id            UUID FK→missions UNIQUE
├── conversation_id       UUID FK→conversations SET NULL
├── event_id              UUID (the triggering event id, nullable)
├── available_capabilities TEXT[]
├── workspace_config      JSONB
└── metadata              JSONB

mission_artifacts
├── id          UUID PK
├── mission_id  UUID FK→missions CASCADE
├── step_id     UUID FK→mission_steps SET NULL
├── type        TEXT       (report|file|image|summary|log|patch|commit)
├── mime        TEXT
├── name        TEXT
├── uri         TEXT
├── metadata    JSONB
└── created_at  TIMESTAMPTZ

mission_logs
├── id          UUID PK
├── mission_id  UUID FK→missions CASCADE
├── step_id     UUID FK→mission_steps SET NULL
├── level       TEXT       (info|warning|error)
├── message     TEXT
├── metadata    JSONB
└── occurred_at TIMESTAMPTZ
```

### 6.3 Advantages of This Separation

**Auditability** — every step, with its input, output, timing and status, is individually queryable. "Which tool failed most this week?" is a simple SQL count.

**Replay** — a failed step can be retried independently. A failed plan can be discarded; the mission continues with a new plan.

**Replanification** — the Mission survives when its plan fails. `mission.status = PLANNING` is re-entered; a new `ExecutionPlan` is created; old steps remain as historical record.

**Parallel execution** — `parent_step_id` enables steps to declare dependencies. Steps with no dependency on each other can run concurrently inside the same plan.

**Human approval** — approval is granted to an `ExecutionPlan`, not to the Mission. A human can compare plan v1 vs plan v2 and approve the better one.

**Metrics** — step-level timestamps (`started_at`, `finished_at`) give exact execution duration per tool, per plan, per mission, per workspace.

---

## 7. Mission State Machine

See `mission-lifecycle.md` for the complete state diagram and all valid transitions.

Summary of states:

| State | Meaning |
|---|---|
| `PENDING` | Created, waiting for planner assignment |
| `PLANNING` | PlanProvider is generating an ExecutionPlan |
| `WAITING_APPROVAL` | Plan generated, waiting for human approval |
| `READY` | Plan approved (or no approval required), ready to execute |
| `RUNNING` | Executor is running steps |
| `PAUSED` | Execution suspended by user request |
| `RETRYING` | A step failed and is being retried |
| `SUCCEEDED` | All steps completed successfully |
| `FAILED` | Irrecoverable failure — mission is terminal |
| `CANCELLED` | Cancelled by user or system |

**Rule:** status changes are always performed through `MissionEngine.transition()`, never by direct field assignment. All transitions are validated against the transition table before execution. Invalid transitions raise `InvalidTransitionError`.

---

## 8. Plan System

### 8.1 PlanProvider Interface

```python
class PlanProvider(Protocol):
    name: str
    async def create_execution_plan(mission: Mission) -> ExecutionPlan: ...
```

The provider receives the full `Mission` (including its `MissionContext`, which contains `available_capabilities`) and returns an `ExecutionPlan` with its `MissionStep[]`. The provider does **not** persist anything — that is exclusively the MissionEngine's responsibility.

**Registered providers:**

| Name | Strategy |
|---|---|
| `llm` | Calls LLM with capabilities context, parses structured JSON plan |
| `workflow` | Loads a `WorkflowTemplate` from `WorkflowRegistry` |
| `manual` | Steps provided explicitly by the caller |
| `imported` | Copies steps from another mission |

### 8.2 PlanValidator

The validator sits between the PlanProvider and the Executor. It receives an `ExecutionPlan` and returns either a validated plan or a list of validation errors. Execution cannot proceed with a failed validation.

```
PlanProvider
    │
    ▼
ExecutionPlan (draft)
    │
    ▼
PlanValidator
    ├── permission_check()    — workspace holds required permissions?
    ├── capability_check()    — all tools exist in CapabilityRegistry?
    ├── parameter_check()     — all step inputs match tool parameter schemas?
    └── dependency_check()    — required_context keys available?
    │
    ▼
ExecutionPlan (validated) → Executor
or
ValidationError[] → back to PLANNING
```

See ADR-006 for the rationale for this step.

### 8.3 Workflow Engine

The Workflow Engine is a declarative pipeline system. It has no intelligence. It executes a fixed sequence of steps defined in a template.

**Who decides to run a Workflow:**
- The `LLMPlanProvider` (Planner recognizes the intent matches a workflow)
- The Scheduler (a TemporalTrigger references a workflow by name)
- A human (via the REST API, specifying `provider: workflow`)

**What a Workflow is not:**
- It is not a Planner. It cannot reason about intent.
- It is not a Mission. It has no goal of its own.
- It is not dynamic. Once defined, it executes the same steps every time.

A Workflow is stored as a `WorkflowTemplate`, validated into a typed model at registration time, and converted to `MissionStep[]` at plan creation time. The runtime never handles raw YAML.

```yaml
# Workflow definition (human-authored, stored/loaded at startup)
name: document_ingestion
description: Process an incoming document through OCR, chunking and embedding
steps:
  - tool: ocr.extract
    input: { file: "{{ context.file_uri }}" }
  - tool: rag.chunk
    input: { text: "{{ steps[0].output.text }}" }
  - tool: rag.embed
    input: { chunks: "{{ steps[1].output.chunks }}" }
  - tool: knowledge.store
    input: { embeddings: "{{ steps[2].output }}", source: "{{ context.file_uri }}" }
```

Template variables (`{{ }}`) are resolved at step execution time, not at plan creation time, allowing outputs of prior steps to flow as inputs to subsequent steps.

---

## 9. Scheduler

The Scheduler makes PAIOS proactive. It creates Missions without user interaction.

Three trigger types with distinct semantics:

### TemporalTrigger
Fires at a specific time or on a cron schedule.

```python
TemporalTrigger(
    name="morning_briefing",
    schedule="0 8 * * *",          # every day at 08:00
    mission_intent="Generate the daily briefing",
    workflow="morning_briefing",
)
```

### EventTrigger
Fires when a specific domain event is published on the EventBus.

```python
EventTrigger(
    name="on_document_ingested",
    event_type="document.ingested",
    mission_intent="Summarize the ingested document and update knowledge",
)
```

### RuleTrigger
Fires when a boolean condition over system state becomes true. This is a rule engine, not a simple threshold.

```python
RuleTrigger(
    name="high_cpu_analysis",
    rule="metrics.cpu_avg_5m > 90 AND last_mission('server_analysis') > 30m",
    mission_intent="Analyze server performance and report findings",
)
```

All three triggers produce the same output: a `Mission.create()` call with `trigger=SCHEDULED|EVENT|RULE`, allowing the rest of the system to treat all missions uniformly.

---

## 10. Knowledge Engine

The Knowledge Engine elevates document chunks into structured, queryable knowledge. It is distinct from the RAG Engine.

**RAG Engine** answers the question: "which chunks of text are semantically similar to this query?"

**Knowledge Engine** answers the question: "what does the system *know* about this entity?"

### 10.1 Data Model

```
Entity
├── id, name, type, workspace_id
├── embedding (for semantic search over entities)
└── created_at, updated_at

Relation
├── id, source_entity_id, target_entity_id
├── predicate (e.g. "uses", "owns", "works_at")
└── metadata, confidence, created_at

Fact
├── id, entity_id
├── subject, predicate, object    (RDF-style triple)
├── source                        (document_id or conversation_id)
├── confidence                    FLOAT (0.0–1.0)
├── workspace_id
└── created_at, updated_at

Observation
├── id, entity_id
├── description                   (natural language)
├── source
├── confidence                    FLOAT (0.0–1.0, typically lower than Facts)
├── expires_at                    TIMESTAMPTZ (can expire)
├── workspace_id
└── created_at
```

### 10.2 Fact vs Observation

**Fact** is a discrete, verifiable statement with a clear source.

> Subject: Victor · Predicate: uses · Object: Ubuntu  
> Source: document `setup-guide.md`, line 12  
> Confidence: 0.97

Facts are extracted from documents, conversations and explicit user statements. They do not expire unless explicitly superseded.

**Observation** is a pattern inferred from multiple signals. It has no single source, lower confidence, and may become stale.

> "Victor costuma programar entre 22h e 02h"  
> Derived from: 47 conversation timestamps  
> Confidence: 0.71  
> Expires: 30 days (refreshed if pattern continues)

Observations are generated by agents (Summarizer, MemoryExtractor) running in the background. They enrich responses with inferred knowledge that no single document contains.

See ADR-005 for the full rationale.

---

## 11. Memory Engine

The Memory Engine stores what PAIOS remembers about the user and context.

### 11.1 Memory Types

| Type | Description | Example |
|---|---|---|
| `semantic` | User preferences and patterns | "Prefers concise answers without examples" |
| `episodic` | Specific past events | "Deployed the API on 2026-06-20" |
| `long` | Long-term facts extracted from conversations | "Victor uses qwen3:8b as LLM" |

### 11.2 Recall Strategy: RRF

Recall uses **Reciprocal Rank Fusion** combining:
- BM25 full-text search (Portuguese tokenization via `tsvector`)
- Vector cosine similarity (pgvector `<=>`)

Score formula: `1/(60 + rank_bm25) + 1/(60 + rank_vec)`

This hybrid approach outperforms either method alone, particularly for queries that are semantically similar but lexically distant (vector wins), or queries with specific proper nouns (BM25 wins).

### 11.3 Memory Schema (current + planned evolution)

```
memories (current)
├── id, workspace_id, type, content, embedding
├── metadata_ (JSONB)
├── superseded_by (UUID, self-referential)
└── created_at, fts (tsvector)

memories (planned evolution — ADR in progress)
├── (all above)
├── confidence    FLOAT DEFAULT 1.0
├── importance    FLOAT DEFAULT 0.5
├── source        TEXT   (conversation|manual|agent|imported|api)
├── expires_at    TIMESTAMPTZ
└── version       INTEGER
```

`superseded_by` (already implemented) creates an immutable audit chain: updating a memory creates a new record and marks the old one with a pointer to the new one. No memory is ever deleted.

---

## 12. Prompt Engine

The Prompt Engine assembles the system prompt dynamically before each LLM call. It is deliberately dumb: it retrieves context from other engines and assembles it. It does not contain intelligence.

### 12.1 Assembly Order

```
[Base system prompt — identity, architecture, behavior rules]
         +
[## Preferências do usuário — top semantic memories]
         +
[## Contexto relevante — RRF-recalled long memories]
         +
[## Documentos disponíveis — filenames of ready documents]
         +
[## Documentos relevantes — RAG chunks for this query]
              ↑ fallback to retrieve_all_chunks() if semantic returns empty
```

### 12.2 Design Rule

The Prompt Engine must never contain business logic. If the prompt needs to know about missions, it must call MissionEngine. If it needs to know about knowledge, it calls KnowledgeEngine. The prompt is a view over the current system state, assembled at request time.

---

## 13. Interfaces

All interfaces — chat, CLI, API, Telegram, dashboard — are consumers of the same Kernel.  
None of them is the "main" interface. The Kernel does not know they exist.

```
Interface A (Chat)     →  Kernel.create_mission(intent)
Interface B (Telegram) →  Kernel.create_mission(intent)
Interface C (CLI)      →  Kernel.create_mission(intent)
Scheduler              →  Kernel.create_mission(intent)
EventTrigger           →  Kernel.create_mission(intent)
```

Adding a new interface requires implementing one function: call `create_mission()` or read the appropriate engine. It does not require changes to any engine, model or provider.

---

## 14. Pending Evolutions

The following are architecturally defined but not yet implemented in code:

| Item | Priority | ADR |
|---|---|---|
| `ExecutionPlan` as separate DB entity | High | ADR-001 |
| `PlanValidator` | High | ADR-006 |
| Knowledge Engine (Entity/Relation/Fact/Observation) | High | ADR-005 |
| Capability Registry full schema (permissions, events, context) | High | ADR-004 |
| Domain/Infrastructure event channel separation | High | ADR-002 |
| Scheduler (TemporalTrigger + EventTrigger + RuleTrigger) | High | — |
| Memory evolution (confidence, importance, source, expires_at) | Medium | — |
| Cognitive Inbox (universal intake pipeline) | Medium | — |
| StorageProvider abstraction | Medium | ADR-003 |
| Workflow template variables (`{{ }}` resolution) | Medium | — |
| Observability integration (InfluxDB + Grafana) | Medium | OBSERVABILITY.md |

---

## References

- `docs/architecture/mission-lifecycle.md` — state machine + sequence diagram
- `docs/architecture/OBSERVABILITY.md` — metrics catalog
- `docs/architecture/adr/ADR-001.md` — Mission / ExecutionPlan / MissionStep separation
- `docs/architecture/adr/ADR-002.md` — Domain events vs infrastructure events
- `docs/architecture/adr/ADR-003.md` — Provider abstraction layer (Protocols)
- `docs/architecture/adr/ADR-004.md` — Capability Registry: semantic capabilities over method catalogs
- `docs/architecture/adr/ADR-005.md` — Knowledge Engine: Observations as distinct from Facts
- `docs/architecture/adr/ADR-006.md` — PlanValidator between Planner and Executor
