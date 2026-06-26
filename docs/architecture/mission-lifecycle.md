# Mission Lifecycle — Specification

**Version:** 2.0  
**Related:** `ARCHITECTURE.md §6`, `adr/ADR-001.md`

---

## 1. Entity Separation

A Mission, an ExecutionPlan and its Steps are three distinct entities.

```
Intent (natural language string)
    │
    ▼
Mission              id, workspace_id, intent, status, trigger
    │                Persistent objective. Survives replanning.
    │
    ▼
PlanProvider         Selects planning strategy (LLM, Workflow, Manual)
    │
    ▼
ExecutionPlan        id, mission_id, version, provider, status
    │                A specific strategy. May be superseded.
    │
    ▼
PlanValidator        Checks permissions, capabilities, parameters
    │
    ▼
MissionStep[]        id, execution_plan_id, order, tool, input, output, status
                     Executable actions. Unit of audit, retry, and metrics.
    │
    ▼
Executor             Resolves tools via CapabilityRegistry and runs them
```

**Rule:** A Mission is never modified when it is replanned. Only a new ExecutionPlan is created and the old one is marked `superseded`. The Mission's status transitions back to `PLANNING`.

---

## 2. State Machine

```
                    ┌───────────┐
         intent     │  PENDING  │
         received   └─────┬─────┘
                          │ planner assigned
                    ┌─────▼─────┐
                    │  PLANNING  │ ◄── replan requested (new ExecutionPlan)
                    └─────┬─────┘
                          │ ExecutionPlan generated + validated
               ┌──────────▼──────────┐
               │   requires_approval? │
               └──────┬──────┬───────┘
                   no │      │ yes
                      │ ┌────▼────────────┐
                      │ │ WAITING_APPROVAL │
                      │ └────┬─────┬──────┘
                      │      │     │ rejected → replan
                      │      │ approved
                 ┌────▼──────▼────┐
                 │     READY      │
                 └────────┬───────┘
                          │ executor starts
                 ┌────────▼───────┐
       ┌────────►│    RUNNING     │◄──────────┐
       │         └──┬──────┬──────┘           │
       │            │      │ pause requested  │ resume
       │   done     │  ┌───▼────┐             │
       │            │  │ PAUSED ├─────────────┘
       │            │  └───┬────┘
       │            │      │ step failed, retry < max_retries
       │            │  ┌───▼────────┐
       └────────────┼──┤  RETRYING  │
                    │  └───┬────────┘
                    │      │ retry > max_retries → FAILED
           ┌────────▼──┐ ┌─▼──────┐ ┌──────────┐
           │ SUCCEEDED │ │ FAILED │ │CANCELLED │
           └───────────┘ └────────┘ └──────────┘
```

### 2.1 Valid Transitions

| From | To | Trigger | Actor |
|---|---|---|---|
| PENDING | PLANNING | Planner assigned | system |
| PENDING | CANCELLED | Cancellation requested | user / system |
| PLANNING | WAITING_APPROVAL | Plan generated, approval required | system |
| PLANNING | READY | Plan generated, no approval required | system |
| PLANNING | FAILED | PlanProvider raised unrecoverable error | system |
| WAITING_APPROVAL | PLANNING | Plan rejected — create new ExecutionPlan | user |
| WAITING_APPROVAL | READY | Plan approved | user |
| WAITING_APPROVAL | CANCELLED | Cancellation requested | user |
| READY | RUNNING | Executor starts | system |
| READY | CANCELLED | Cancellation requested | user |
| RUNNING | PAUSED | Pause requested | user |
| RUNNING | RETRYING | Step failed, retries available | system |
| RUNNING | SUCCEEDED | All steps completed | system |
| RUNNING | FAILED | Step failed, retries exhausted | system |
| RUNNING | CANCELLED | Cancellation requested | user / system |
| PAUSED | RUNNING | Resume requested | user |
| PAUSED | CANCELLED | Cancellation requested | user |
| RETRYING | RUNNING | Retry attempt starts | system |
| RETRYING | FAILED | Max retries reached | system |

**All other transitions are invalid and raise `InvalidTransitionError`.**  
Status is never set by direct field assignment — always through `MissionEngine.transition()`.

---

## 3. Step State Machine

```
PENDING → RUNNING → SUCCEEDED
                 → FAILED → (mission: RETRYING or FAILED)
         SKIPPED  (dependency not met or plan skipped this step)
```

---

## 4. Full Sequence Diagram

```
User/Trigger  Kernel    Mission  PlanProvider  PlanValidator  Executor  Capability  Memory  Knowledge
     │           │          │         │               │           │          │          │         │
     │──intent──►│          │         │               │           │          │          │         │
     │           │──create─►│         │               │           │          │          │         │
     │           │          │──PENDING►               │           │          │          │         │
     │           │          │         │               │           │          │          │         │
     │           │          │──assign PlanProvider    │           │          │          │         │
     │           │          │──PLANNING               │           │          │          │         │
     │           │          │──plan(mission)──────────►           │          │          │         │
     │           │          │          ◄──ExecutionPlan           │          │          │         │
     │           │          │──validate(plan)─────────────────────►          │          │         │
     │           │          │          ◄──ValidationResult────────│          │          │         │
     │           │          │                                      │          │          │         │
     │           │   [requires_approval=true]                      │          │          │         │
     │           │          │──WAITING_APPROVAL                    │          │          │         │
     │◄─notify───│          │                                      │          │          │         │
     │──approve─►│          │                                      │          │          │         │
     │           │          │──READY                               │          │          │         │
     │           │          │                                      │          │          │         │
     │           │          │──RUNNING                             │          │          │         │
     │           │          │──assign Executor────────────────────►           │          │         │
     │           │          │         │               │ for each step:        │          │         │
     │           │          │         │               │──resolve tool─────────►          │         │
     │           │          │         │               │  ◄──CapabilityTool────│          │         │
     │           │          │         │               │──step.status=RUNNING  │          │         │
     │           │          │         │               │──tool.fn(input)───────►          │         │
     │           │          │         │               │  ◄──result────────────│          │         │
     │           │          │         │               │──step.output=result   │          │         │
     │           │          │         │               │──step.status=SUCCEEDED│          │         │
     │           │          │         │               │──persist Artifact     │          │         │
     │           │          │         │               │                       │          │         │
     │           │          │──SUCCEEDED               │                      │          │         │
     │           │          │──update knowledge──────────────────────────────────────────────────►  │
     │           │          │──update memory─────────────────────────────────────────────►         │
     │           │          │──emit: mission.completed  │                     │          │         │
     │           │◄─event───│                           │                     │          │         │
     │◄─notify───│          │                           │                     │          │         │
```

---

## 5. Data Model

### missions
```
id                UUID PK
workspace_id      UUID FK→workspaces CASCADE
intent            TEXT NOT NULL
status            mission_status ENUM
trigger           mission_trigger ENUM    (manual|scheduled|event|rule)
requires_approval BOOLEAN DEFAULT false
created_at        TIMESTAMPTZ
updated_at        TIMESTAMPTZ
completed_at      TIMESTAMPTZ
```

### execution_plans *(planned — not yet in migration 006)*
```
id          UUID PK
mission_id  UUID FK→missions CASCADE
version     INTEGER NOT NULL          ← 1 = first plan, 2 = after replan
provider    TEXT                      ← "llm" | "workflow" | "manual"
status      plan_status ENUM          (draft|validated|approved|executing|superseded|failed)
created_at  TIMESTAMPTZ
metadata    JSONB                     ← token count, planner config, etc.
```

### mission_steps
```
id                UUID PK
mission_id        UUID FK→missions     (denormalized for queries)
execution_plan_id UUID FK→execution_plans CASCADE  ← owned by the plan
parent_step_id    UUID FK→mission_steps SET NULL   (parallel/nested)
order             INTEGER NOT NULL
type              step_type ENUM       (tool|workflow|agent|human)
tool              TEXT                 (capability tool name)
input             JSONB
output            JSONB
status            step_status ENUM     (pending|running|succeeded|failed|skipped)
started_at        TIMESTAMPTZ
finished_at       TIMESTAMPTZ
retry_count       INTEGER DEFAULT 0
```

### mission_contexts
```
id                    UUID PK
mission_id            UUID FK→missions UNIQUE
conversation_id       UUID FK→conversations SET NULL
event_id              UUID (triggering event id, nullable)
available_capabilities TEXT[]
workspace_config      JSONB
metadata              JSONB
```

### mission_artifacts
```
id          UUID PK
mission_id  UUID FK→missions CASCADE
step_id     UUID FK→mission_steps SET NULL
type        TEXT    (report|file|image|summary|log|patch|commit)
mime        TEXT
name        TEXT
uri         TEXT
metadata    JSONB
created_at  TIMESTAMPTZ
```

### mission_logs
```
id          UUID PK
mission_id  UUID FK→missions CASCADE
step_id     UUID FK→mission_steps SET NULL
level       TEXT    (info|warning|error)
message     TEXT
metadata    JSONB
occurred_at TIMESTAMPTZ
```

---

## 6. Event Timeline (Mission Domain Events)

```
mission.created
    └── mission.planning
            └── mission.ready (or mission.failed if planning fails)
                    └── mission.running
                            ├── mission.step.started
                            │       └── mission.step.completed
                            │       or  mission.step.failed
                            │               └── (retry) mission.step.started
                            │               or  mission.failed
                            └── mission.completed
                            or  mission.cancelled
```

All events in a single mission share the same `correlation_id`.  
Each event's `causation_id` points to the `id` of its direct parent event.
