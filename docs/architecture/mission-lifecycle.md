# Mission Lifecycle — Especificação

## 1. State Machine

```
                    ┌─────────┐
         intent     │ PENDING │
         received   └────┬────┘
                         │ planner assigned
                    ┌────▼────┐
                    │PLANNING │◄─── replan requested
                    └────┬────┘
                         │ plan generated
              ┌──────────▼──────────┐
              │   requires_approval?│
              └──────┬──────┬───────┘
                  no │      │ yes
                     │ ┌────▼──────────┐
                     │ │WAITING_APPROVAL│
                     │ └────┬──────────┘
                     │      │ approved
                ┌────▼──────▼────┐
                │     READY      │
                └────────┬───────┘
                         │ executor starts
                ┌────────▼───────┐
                │    RUNNING     │◄──────────┐
                └──┬──────┬──────┘           │
                   │      │ pause requested  │ resume
          done     │  ┌───▼────┐             │
                   │  │ PAUSED ├─────────────┘
                   │  └───┬────┘
                   │      │ step failed, retry < max
                   │  ┌───▼────────┐
                   │  │  RETRYING  │────────────► RUNNING
                   │  └───┬────────┘
                   │      │ retry > max
           ┌───────▼──┐ ┌─▼──────┐ ┌──────────┐
           │SUCCEEDED │ │ FAILED │ │CANCELLED │
           └──────────┘ └────────┘ └──────────┘
```

### Transições válidas

| De | Para | Gatilho |
|---|---|---|
| PENDING | PLANNING | planner atribuído |
| PLANNING | WAITING_APPROVAL | plano gerado + approval requerido |
| PLANNING | READY | plano gerado + sem approval |
| WAITING_APPROVAL | PLANNING | aprovação negada (replanejar) |
| WAITING_APPROVAL | READY | aprovação concedida |
| READY | RUNNING | executor inicia |
| RUNNING | PAUSED | pause solicitado pelo usuário |
| RUNNING | RETRYING | step falhou, retry disponível |
| RUNNING | SUCCEEDED | todos os steps concluídos |
| RUNNING | FAILED | step falhou, retry esgotado |
| RUNNING | CANCELLED | cancelamento solicitado |
| PAUSED | RUNNING | resume solicitado |
| PAUSED | CANCELLED | cancelamento solicitado |
| RETRYING | RUNNING | retry iniciado |
| RETRYING | FAILED | retry máximo atingido |
| PLANNING | FAILED | planner falhou |

---

## 2. Diagrama de Sequência — Fluxo Completo

```
User/Trigger   Kernel     Mission    PlanProvider   MissionEngine  Capability  Memory   Knowledge  Scheduler
     │            │           │            │               │            │          │          │          │
     │──intent───►│           │            │               │            │          │          │          │
     │            │──create──►│            │               │            │          │          │          │
     │            │           │──status:PLANNING           │            │          │          │          │
     │            │           │──select────►               │            │          │          │          │
     │            │           │            │──plan(intent)►│            │          │          │          │
     │            │           │            │  ◄──steps─────│            │          │          │          │
     │            │           │◄──plan─────│               │            │          │          │          │
     │            │           │──persist MissionSteps      │            │          │          │          │
     │            │           │                            │            │          │          │          │
     │            │  [requires_approval=true]              │            │          │          │          │
     │            │           │──status:WAITING_APPROVAL   │            │          │          │          │
     │◄──notify───│           │            │               │            │          │          │          │
     │──approve──►│           │            │               │            │          │          │          │
     │            │           │──status:READY              │            │          │          │          │
     │            │           │            │               │            │          │          │          │
     │            │           │──assign────────────────────►            │          │          │          │
     │            │           │──status:RUNNING            │            │          │          │          │
     │            │           │            │      ┌────────┘            │          │          │          │
     │            │           │            │      │ for each step:      │          │          │          │
     │            │           │            │      │──resolve capability─►          │          │          │
     │            │           │            │      │  ◄──tool────────────│          │          │          │
     │            │           │            │      │──execute(tool,args)─►          │          │          │
     │            │           │            │      │  ◄──result──────────│          │          │          │
     │            │           │            │      │──persist step.output│          │          │          │
     │            │           │            │      │──persist Artifact   │          │          │          │
     │            │           │            │      └────────┐            │          │          │          │
     │            │           │            │               │            │          │          │          │
     │            │           │──status:SUCCEEDED          │            │          │          │          │
     │            │           │──update knowledge──────────────────────────────────────────►  │          │
     │            │           │──update memory─────────────────────────────────────────────►  │          │
     │            │           │──emit: mission.completed   │            │          │          │          │
     │            │◄──event───│            │               │            │          │          │          │
     │            │──dispatch─────────────────────────────────────────────────────────────────────────►  │
     │◄──notify───│           │            │               │            │          │          │          │
```

---

## 3. Modelo de Dados

### Mission

```
missions
├── id                UUID PK
├── workspace_id      UUID FK→workspaces
├── intent            TEXT NOT NULL        — intenção em linguagem natural
├── status            mission_status       — enum (ver state machine)
├── planner           TEXT                 — qual PlanProvider foi usado
├── executor          TEXT                 — qual executor está rodando
├── trigger           mission_trigger      — manual | scheduled | event | rule
├── requires_approval BOOLEAN DEFAULT false
├── created_at        TIMESTAMPTZ
├── updated_at        TIMESTAMPTZ
└── completed_at      TIMESTAMPTZ
```

### MissionStep

```
mission_steps
├── id                UUID PK
├── mission_id        UUID FK→missions ON DELETE CASCADE
├── parent_step_id    UUID FK→mission_steps (para steps paralelos/aninhados)
├── order             INTEGER NOT NULL
├── type              step_type            — tool | workflow | agent | human
├── tool              TEXT                 — capability tool name
├── input             JSONB
├── output            JSONB
├── status            step_status          — pending | running | succeeded | failed | skipped
├── started_at        TIMESTAMPTZ
├── finished_at       TIMESTAMPTZ
└── retry_count       INTEGER DEFAULT 0
```

### MissionContext

```
mission_contexts
├── id                    UUID PK
├── mission_id            UUID FK→missions UNIQUE
├── conversation_id       UUID FK→conversations (nullable)
├── event_id              UUID                 — evento que disparou (nullable)
├── available_capabilities TEXT[] (ARRAY)
├── workspace_config      JSONB
└── metadata              JSONB
```

### MissionArtifact

```
mission_artifacts
├── id          UUID PK
├── mission_id  UUID FK→missions ON DELETE CASCADE
├── step_id     UUID FK→mission_steps (nullable)
├── type        TEXT        — report | file | image | summary | log | patch | commit
├── mime        TEXT
├── name        TEXT
├── uri         TEXT        — path local ou URL
├── metadata    JSONB
└── created_at  TIMESTAMPTZ
```

### MissionLog

```
mission_logs
├── id          UUID PK
├── mission_id  UUID FK→missions ON DELETE CASCADE
├── step_id     UUID FK→mission_steps (nullable)
├── level       TEXT        — info | warning | error
├── message     TEXT
├── metadata    JSONB
└── occurred_at TIMESTAMPTZ
```

---

## 4. Event Envelope

```python
@dataclass
class KhonshuEvent:
    id:             UUID
    type:           str          # "mission.created", "document.ingested", etc.
    version:        str          # "1.0" — para evolução do schema
    workspace_id:   UUID
    correlation_id: UUID         # mesmo para toda uma cadeia de eventos
    causation_id:   UUID | None  # evento pai imediato
    actor:          str          # "user" | "scheduler" | "agent" | "system"
    source:         str          # "chat" | "scheduler" | "inbox" | "mission"
    payload:        dict
    metadata:       dict
    priority:       int          # 0 (baixa) a 9 (crítica)
    occurred_at:    datetime
```

### Tipos de evento registrados

| type | source | descrição |
|---|---|---|
| `mission.created` | qualquer | missão criada |
| `mission.planning` | kernel | planejamento iniciado |
| `mission.ready` | kernel | plano aprovado, pronto para executar |
| `mission.running` | kernel | executor iniciou |
| `mission.step.started` | executor | step iniciou |
| `mission.step.completed` | executor | step concluiu |
| `mission.step.failed` | executor | step falhou |
| `mission.completed` | executor | missão concluída |
| `mission.failed` | executor | missão falhou |
| `document.ingested` | inbox | documento ingerido |
| `knowledge.updated` | knowledge | conhecimento atualizado |
| `memory.created` | memory | memória criada |
| `scheduler.fired` | scheduler | trigger temporal/evento/regra disparou |

---

## 5. PlanProvider Interface

```python
class PlanProvider(Protocol):
    async def create_execution_plan(self, mission: Mission) -> list[MissionStep]:
        ...

# Implementações:
# LLMPlannerProvider     — usa LLM para gerar passos
# WorkflowTemplateProvider — carrega template YAML/Pydantic
# ManualPlanProvider     — passos definidos pelo usuário
# ImportedPlanProvider   — importa plano de outra missão
```

---

## 6. Scheduler Trigger Types

```
TemporalTrigger   — cron expression, one-shot datetime
EventTrigger      — reage a um tipo de evento específico
RuleTrigger       — condições booleanas sobre estado do sistema
                   (ex: cpu > 90% AND last_analysis > 30min)
```

---

## 7. Capability Registry

```yaml
# Exemplo de capability descriptor
name: container_management
description: >
  Manage Docker containers: lifecycle, inspection, logs and metrics.
tools:
  - docker.start
  - docker.stop
  - docker.restart
  - docker.logs
  - docker.stats
  - docker.inspect
tags:
  - infrastructure
  - docker
  - observability
```

O Planner consulta o Registry por descrição semântica,
não por nome de ferramenta.
