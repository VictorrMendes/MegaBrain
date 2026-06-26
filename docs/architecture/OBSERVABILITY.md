# PAIOS — Observability Reference

**Version:** 1.0  
**Related:** `ARCHITECTURE.md §14`

---

## 0. Philosophy

PAIOS must be able to answer the following questions at any time:

- Is the system healthy?
- Which missions are running and how long have they been running?
- Which tools are slow or failing?
- Is the LLM responding within acceptable latency?
- Which capabilities are used most?
- How accurate is the knowledge and memory retrieval?
- Are there resource bottlenecks?

These questions must be answered without querying the application database. They must be answered from a time-series metrics store (InfluxDB) and visualised in Grafana.

---

## 1. Infrastructure

| Component | Role |
|---|---|
| InfluxDB 2.x | Time-series metrics storage |
| Grafana | Dashboard and alerting |
| structlog (existing) | Structured JSON logs |
| asyncpg / FastAPI middleware | Request and DB metrics |

All metrics use the same tag set for correlation:

```
workspace_id    — tenant isolation
component       — which engine/provider emitted this metric
environment     — development | production
```

---

## 2. Metric Catalog

### 2.1 Mission Engine

| Metric | Type | Description |
|---|---|---|
| `mission.duration_seconds` | Histogram | Total time from PENDING to terminal state |
| `mission.planning_latency_seconds` | Histogram | Time in PLANNING state |
| `mission.execution_latency_seconds` | Histogram | Time from RUNNING to terminal |
| `mission.step_duration_seconds` | Histogram | Duration per step (tag: `tool`) |
| `mission.step_retry_count` | Counter | Number of step retries (tag: `tool`) |
| `mission.created_total` | Counter | Missions created (tag: `trigger`) |
| `mission.completed_total` | Counter | Missions completed successfully |
| `mission.failed_total` | Counter | Missions failed (tag: `reason`) |
| `mission.cancelled_total` | Counter | Missions cancelled |
| `mission.active_count` | Gauge | Currently RUNNING + PAUSED missions |
| `mission.approval_wait_seconds` | Histogram | Time waiting for human approval |

### 2.2 Plan System

| Metric | Type | Description |
|---|---|---|
| `planner.latency_seconds` | Histogram | Time for PlanProvider to generate plan (tag: `provider`) |
| `planner.steps_generated` | Histogram | Number of steps in generated plan (tag: `provider`) |
| `planner.validation_failures_total` | Counter | Plans rejected by PlanValidator (tag: `reason`) |
| `workflow.executions_total` | Counter | Workflow template executions (tag: `workflow_name`) |
| `workflow.duration_seconds` | Histogram | Workflow execution time (tag: `workflow_name`) |

### 2.3 LLM Provider

| Metric | Type | Description |
|---|---|---|
| `llm.request_latency_seconds` | Histogram | Time from request to first token (tag: `model`, `operation`) |
| `llm.stream_duration_seconds` | Histogram | Full streaming duration |
| `llm.tokens_total` | Counter | Tokens consumed (tag: `model`, `direction`: input/output) |
| `llm.errors_total` | Counter | Provider errors (tag: `model`, `error_type`) |
| `llm.think_blocks_filtered_total` | Counter | `<think>` blocks stripped from responses |

### 2.4 Embedding Provider

| Metric | Type | Description |
|---|---|---|
| `embedding.latency_seconds` | Histogram | Per-call embedding time (tag: `model`) |
| `embedding.batch_size` | Histogram | Items per batch call |
| `embedding.cache_hit_rate` | Gauge | Cache hit ratio (if embedding cache is added) |
| `embedding.dimensions` | Gauge | Embedding vector size (sanity check) |

### 2.5 RAG Engine

| Metric | Type | Description |
|---|---|---|
| `rag.ingest_duration_seconds` | Histogram | Document ingestion time |
| `rag.chunks_created_total` | Counter | Chunks created per ingest |
| `rag.retrieve_latency_seconds` | Histogram | Retrieval query time |
| `rag.retrieve_results_count` | Histogram | Number of chunks returned per query |
| `rag.fallback_retrievals_total` | Counter | Times fallback retrieve_all_chunks was used |
| `rag.ingest_failures_total` | Counter | Failed ingestions (tag: `reason`) |

### 2.6 Memory Engine

| Metric | Type | Description |
|---|---|---|
| `memory.recall_latency_seconds` | Histogram | RRF recall query time |
| `memory.recall_results_count` | Histogram | Memories returned per recall |
| `memory.bm25_results_count` | Histogram | BM25 candidates before RRF |
| `memory.vector_results_count` | Histogram | Vector candidates before RRF |
| `memory.created_total` | Counter | Memories stored (tag: `type`, `source`) |
| `memory.superseded_total` | Counter | Memories updated via supersede |

### 2.7 Knowledge Engine

| Metric | Type | Description |
|---|---|---|
| `knowledge.facts_created_total` | Counter | Facts extracted and stored |
| `knowledge.observations_created_total` | Counter | Observations stored |
| `knowledge.entities_total` | Gauge | Total entities per workspace |
| `knowledge.confidence_score` | Histogram | Distribution of fact/observation confidence |
| `knowledge.expired_observations_total` | Counter | Observations that expired |
| `knowledge.update_latency_seconds` | Histogram | Time to update knowledge after a mission |

### 2.8 Capability Registry

| Metric | Type | Description |
|---|---|---|
| `capability.tool_calls_total` | Counter | Tool invocations (tag: `capability`, `tool`) |
| `capability.tool_errors_total` | Counter | Tool failures (tag: `capability`, `tool`, `error_type`) |
| `capability.tool_latency_seconds` | Histogram | Tool execution time (tag: `capability`, `tool`) |
| `capability.registered_total` | Gauge | Number of registered capabilities at startup |
| `capability.validation_failures_total` | Counter | PlanValidator failures (tag: `reason`) |

### 2.9 Scheduler

| Metric | Type | Description |
|---|---|---|
| `scheduler.fires_total` | Counter | Trigger activations (tag: `trigger_type`, `trigger_name`) |
| `scheduler.lag_seconds` | Histogram | Actual fire time vs scheduled time |
| `scheduler.missions_created_total` | Counter | Missions created by scheduler |
| `scheduler.rule_evaluations_total` | Counter | RuleTrigger condition evaluations per interval |

### 2.10 Event Bus

| Metric | Type | Description |
|---|---|---|
| `eventbus.events_published_total` | Counter | Events published (tag: `type`, `source`) |
| `eventbus.events_consumed_total` | Counter | Events processed by handlers (tag: `type`) |
| `eventbus.handler_latency_seconds` | Histogram | Handler execution time (tag: `handler`) |
| `eventbus.handler_errors_total` | Counter | Handler failures (tag: `handler`, `event_type`) |
| `eventbus.queue_depth` | Gauge | Pending events in channel (if measurable) |

### 2.11 API / HTTP

| Metric | Type | Description |
|---|---|---|
| `http.request_duration_seconds` | Histogram | Request latency (tag: `method`, `route`, `status`) |
| `http.requests_total` | Counter | Total requests (tag: `method`, `route`, `status`) |
| `http.sse_connections_active` | Gauge | Active SSE streaming connections |
| `http.sse_duration_seconds` | Histogram | SSE stream duration |

### 2.12 Database

| Metric | Type | Description |
|---|---|---|
| `db.query_latency_seconds` | Histogram | Query execution time (tag: `operation`) |
| `db.pool_connections_active` | Gauge | Active connections in pool |
| `db.pool_connections_idle` | Gauge | Idle connections in pool |
| `db.vector_search_latency_seconds` | Histogram | pgvector `<=>` query time |

### 2.13 Agent Workers

| Metric | Type | Description |
|---|---|---|
| `agent.executions_total` | Counter | Worker invocations (tag: `agent_name`) |
| `agent.latency_seconds` | Histogram | Processing time per invocation (tag: `agent_name`) |
| `agent.parse_failures_total` | Counter | JSON parse errors from LLM output (tag: `agent_name`) |
| `agent.memories_extracted_total` | Counter | Memories created by MemoryExtractor |

---

## 3. Alerting Rules

Priority alerts (must page on-call):

| Alert | Condition | Severity |
|---|---|---|
| LLM unavailable | `llm.errors_total` rate > 5/min for 3min | Critical |
| Mission backlog | `mission.active_count` > 20 for 10min | Warning |
| Embedding latency | p99 > 5s for 5min | Warning |
| DB pool exhausted | `db.pool_connections_idle` = 0 for 2min | Critical |
| Event handler errors | `eventbus.handler_errors_total` rate > 10/min | Warning |

---

## 4. Dashboard Layout (Grafana)

### Row 1: System Health
- LLM availability (last 24h uptime)
- Active missions (gauge)
- Event throughput (events/min)
- API error rate (%)

### Row 2: Mission Performance
- Mission duration histogram
- Planning latency by provider
- Step failure rate by tool
- Mission outcomes (succeeded/failed/cancelled pie)

### Row 3: LLM & Embeddings
- LLM request latency p50/p95/p99
- Token consumption over time
- Embedding latency
- Think-block filter rate

### Row 4: Knowledge & Memory
- Knowledge facts created/day
- Memory recall latency
- RRF component contribution (BM25 vs vector)
- Observation expiry rate

### Row 5: Infrastructure
- DB query latency
- Pool connections
- pgvector search latency
- Active SSE connections

---

## 5. Implementation Notes

PAIOS already has InfluxDB configured in `kernel/config/settings.py`:

```python
influxdb_url:    str = "http://localhost:8086"
influxdb_token:  str = ""
influxdb_org:    str = "vmserver"
influxdb_bucket: str = "khonshu"
```

The metrics emission layer should be implemented as a `MetricsProvider` (following the Provider Abstraction pattern) that wraps InfluxDB's line protocol. No engine should import InfluxDB directly.

```python
class MetricsProvider(Protocol):
    def counter(name: str, value: int, tags: dict) -> None: ...
    def histogram(name: str, value: float, tags: dict) -> None: ...
    def gauge(name: str, value: float, tags: dict) -> None: ...
```

This allows replacing InfluxDB with Prometheus, StatsD or any other backend without touching engine code.
