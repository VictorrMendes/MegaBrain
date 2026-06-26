# Documento de Trabalho — PAIOS / Khonshu Backend
**Data:** 2026-06-25  
**Escopo:** Resumo completo de tudo que foi arquitetado e implementado nesta sessão de desenvolvimento.

---

## 1. Visão Geral: o que é o Khonshu

**Khonshu é o backend do PAIOS — Personal AI Operating System.**

A premissa central: PAIOS não é um chatbot, não é um agente e não é um pipeline de RAG. É um **Sistema Operacional Cognitivo**. O LLM é um componente substituível, não o núcleo do sistema. O núcleo é o **Kernel**.

O PAIOS:
- **Age** — cria e executa missões sem esperar input do usuário
- **Aprende** — constrói conhecimento e memória ao longo do tempo
- **Reage** — responde a eventos, regras e agendamentos, não apenas a mensagens
- **Observa** — monitora seus próprios componentes e o ambiente
- **Coordena** — roteia eventos entre componentes via contrato tipado

O chat é uma das interfaces de entrada, equivalente em importância ao Scheduler, ao Inbox e ao Event Bus. Nenhum deles é o centro do sistema.

---

## 2. Estado do Projeto Antes desta Sessão

O projeto já tinha implementado (Sprints 1–7):

| Sprint | O que tinha |
|---|---|
| 1 | Schema inicial: workspaces, memories, embeddings (pgvector), OllamaProvider |
| 2 | Conversations: histórico de mensagens, streaming SSE |
| 3 | Documents: ingestão, RAGEngine (chunking + embeddings) |
| 4 | Chat Interface: Next.js 15, streaming, gerenciamento de workspace/conversa |
| 5 | RAGEngine completo + correções de deploy |
| 6 | Agents de background (MemoryExtractor, Summarizer, TaskExtractor) + Plugins (ntfy, weather, search, HA, Notion, GCal) |
| 7 | ObsidianEngine: sync de vault, grafo de conhecimento, RAG de notas |

**O que não existia ainda:** Sistema de Missões estruturado, Knowledge Engine separado do RAG, Scheduler, Memory com qualidade (confidence/importance), Cognitive Inbox.

---

## 3. Arquitetura de Camadas (definida e documentada)

```
┌─────────────────────────────────────────────────────────────┐
│  INTERFACES                                                   │
│  Chat · CLI · Telegram · Dashboard · API · Webhook           │
├─────────────────────────────────────────────────────────────┤
│  DOMAIN ENGINES                                               │
│  MissionEngine · KnowledgeEngine · MemoryEngine              │
│  PromptEngine · RAGEngine · PluginEngine · ObsidianEngine    │
│  SchedulerEngine · InboxEngine                               │
├─────────────────────────────────────────────────────────────┤
│  COORDINATION                                                 │
│  Kernel Runtime · EventBus · CapabilityRegistry · Scheduler  │
├─────────────────────────────────────────────────────────────┤
│  PLAN SYSTEM                                                  │
│  PlanProvider · PlanValidator · WorkflowEngine               │
├─────────────────────────────────────────────────────────────┤
│  PROVIDERS (Abstraction Layer — Python Protocols)            │
│  LLMProvider · EmbeddingProvider · StorageProvider           │
│  EventBusProvider · NotificationProvider · SearchProvider    │
│  PlannerProvider · MetricsProvider                           │
├─────────────────────────────────────────────────────────────┤
│  INFRAESTRUTURA                                               │
│  PostgreSQL + pgvector · Ollama · Redis · Docker             │
└─────────────────────────────────────────────────────────────┘
```

**Regra de dependência:** cada camada só depende da camada diretamente abaixo. Um engine nunca importa de uma interface. Um provider nunca importa de um engine.

---

## 4. Architecture Decision Records (ADRs)

Foram escritos e aprovados 6 ADRs nesta sessão. Cada um documenta o problema, as alternativas consideradas, a decisão e as consequências.

### ADR-001 — Mission, ExecutionPlan e MissionStep como entidades separadas

**Problema:** A implementação original ligava `MissionStep` diretamente à `Mission`. Ao replanificar, os steps tinham que ser deletados — perdendo o histórico do plano anterior. Aprovação humana não tinha um objeto ao qual se ligar. Nenhum versionamento de plano.

**Decisão:** Três entidades distintas:
- **Mission** — o objetivo. Persiste desde a criação até a conclusão ou cancelamento. Não muda quando o plano muda.
- **ExecutionPlan** — uma estratégia específica. Pode ser `superseded` quando replanejar. É ela que recebe a aprovação humana. Tem `version`, `provider`, `status`, `validation_errors`.
- **MissionStep** — ação executável individual. Pertence ao `ExecutionPlan`, não à `Mission`. É a unidade de retry, paralelismo, auditoria e métricas.

**Impacto no código:** migration 007, modelo `ExecutionPlan` em `models/mission.py`, `MissionEngine.plan()` reformulado.

---

### ADR-002 — Eventos de Domínio separados de Eventos de Infraestrutura

**Problema:** O registro `EventType` misturava `mission.created` com `plugin.loaded`. Se o MissionEngine subscribe a `container.started` (Docker), ele fica acoplado ao Docker. Trocar Docker por Podman exige mudar o MissionEngine.

**Decisão:** Dois canais físicos no PostgreSQL LISTEN/NOTIFY:
- `khonshu.events` — eventos de domínio. Fatos sobre o negócio. Passado perfeito. Significativos para um stakeholder não-técnico.
- `khonshu.infra` — eventos de infraestrutura. Mudanças de estado técnico. Para monitoramento.

Domain engines só podem subscribir ao canal de domínio. Infra events são consumidos exclusivamente por monitoring.

**Impacto no código:** `kernel/events/schema.py` → `DomainEventType` e `InfraEventType`. `kernel/events/bus.py` → `subscribe_event()`, `subscribe_infra()`, `publish_event()`, `publish_infra_event()`, `_dispatch_infra()`.

---

### ADR-003 — Camada de Abstração de Providers (Python Protocols)

**Problema:** Engines importavam `OllamaProvider` diretamente. Trocar o LLM exigiria mudar todos os engines. Sem testabilidade real.

**Decisão:** Todos os providers são definidos como `Protocol` em `kernel/providers/base.py`. Concrete implementations são conectadas somente em `core/dependencies.py`. Nenhum engine importa uma classe concreta de provider.

**Providers definidos:**
- `LLMProvider` — generate, stream, chat, chat_stream
- `EmbeddingProvider` — embed, embed_batch
- `EventBusProvider` — publish_event, subscribe_event, connect, disconnect
- `StorageProvider` — store, retrieve, delete (não implementado ainda)
- `NotificationProvider` — notify
- `SearchProvider` — search
- `PlannerProvider` — create_execution_plan
- `MetricsProvider` — counter, histogram, gauge (não implementado ainda)

---

### ADR-004 — Capability Registry: Capacidades Semânticas sobre Catálogo de Métodos

**Problema:** Um registry de assinaturas de métodos (`docker.restart(container: str)`) é frágil: renomear o método quebra todos os planos que referenciavam o nome antigo. O LLM Planner não consegue raciocinar sobre "quem pode gerenciar containers?" a partir de uma lista de 50 assinaturas.

**Decisão:** Capabilities são descritores semânticos. Tools são detalhes de implementação.

- **Planner** raciocina sobre capabilities (por descrição, tags, eventos).
- **Plan steps** referenciam tools (por nome).
- **Executor** resolve tools via `capability_registry.get_tool(tool_name)`.
- **PlanValidator** verifica existência das tools e permissões do workspace.

**Schema de Capability:**
```
name, description, plugin, permissions[], required_context[],
tools[], events_consumed[], events_produced[], dependencies[], tags[]
```

**Impacto no código:** `kernel/capabilities/registry.py` — `Capability` dataclass expandido com todos os campos acima.

---

### ADR-005 — Knowledge Engine: Observações como entidade distinta de Fatos

**Problema:** O Knowledge Engine original usava uma única entidade `Fact` para todo o conhecimento. Mas existem dois tipos fundamentalmente diferentes de claims de conhecimento:

1. **Verificado:** "O PostgreSQL roda na porta 5432" — tem fonte primária, alta confiança, não expira.
2. **Inferido:** "O usuário prefere resumos de manhã" — derivado de padrões, confiança variável, pode ficar obsoleto.

Tratar ambos como `Fact` colapsa a distinção e gera falsa precisão.

**Decisão:** Duas entidades distintas:

**Fact:**
- Statement verificado com fonte primária explícita
- `source_type` ("conversation" | "document" | "user_explicit")
- `source_id` (FK para a fonte)
- `confidence` ≈ 1.0 (alta)
- Não expira (apenas superseded)
- `superseded_by_id` — imutabilidade via cadeia

**Observation:**
- Padrão inferido de múltiplos sinais, sem fonte única
- `derived_from` ("conversation_pattern" | "mission_statistics" | "rule_engine")
- `derivation_agent` — qual engine produziu
- `confidence` 0.0–1.0 (variável, tipicamente menor)
- `expires_at` opcional
- `reinforcement_count` — aumentado quando o padrão se confirma novamente
- `expired` — flag setado pelo decay job

**Fórmula de decaimento de confiança:**
```
nova_confiança = confiança * 0.5 ^ (dias_sem_reforço / 30)
```
Quando `confidence < 0.15`, a observação é marcada como `expired = True`.

**No Prompt Engine:**
```
## Fatos conhecidos (verificados)
- Servidor: Samsung NP550XCJ, 16GB RAM

## Observações (padrões inferidos)
- [70% confiança] Usuário prefere resumos pela manhã
```
Observações abaixo de 0.4 de confiança são excluídas do prompt.

---

### ADR-006 — PlanValidator: Camada de Validação entre Planner e Executor

**Problema:** Na implementação Phase 2A, steps gerados pelo LLM iam diretamente ao Executor. Se o LLM alucinasse um nome de tool, o erro era descoberto na execução — depois de steps com efeitos colaterais já terem rodado. Aprovação humana era solicitada em planos potencialmente inválidos.

**Decisão:** `PlanValidator` dedicado, chamado pelo `MissionEngine` após qualquer `PlanProvider` retornar um plano e antes de qualquer transição para `WAITING_APPROVAL` ou `READY`.

**Regras de validação:**

| Regra | Código | Fatal? |
|---|---|---|
| Tool não existe no registry | `tool_not_found` | Sim |
| Workspace não tem permissão necessária | `permission_denied` | Sim |
| Parâmetro required faltando | `missing_required_parameter` | Sim |
| `required_context` indisponível | `missing_context` | Sim |
| Plano sem steps | `empty_plan` | Sim |
| Plano muito longo (warning) | `plan_too_long` | Não |

Se inválido: `ExecutionPlan.status = "failed"`, `validation_errors` armazenado como JSONB, evento `mission.plan_validation_failed` publicado, missão vai para `FAILED`.

---

## 5. Sistema de Missões — Implementação Completa

### 5.1 State Machine

```
PENDING → PLANNING → WAITING_APPROVAL → READY → RUNNING → SUCCEEDED
                                      ↘ READY ↗             ↓ FAILED
                        ← replan ←                          ↓ CANCELLED
                                                   ↔ PAUSED
                                                   → RETRYING
```

Todas as transições passam por `MissionEngine.transition()`. Transições inválidas lançam `InvalidTransitionError`.

### 5.2 Models implementados (`models/mission.py`)

```python
# Enums
MissionStatus    — pending, planning, waiting_approval, ready, running,
                   paused, retrying, succeeded, failed, cancelled
MissionTrigger   — manual, scheduled, event, rule
StepType         — tool, workflow, agent, human
StepStatus       — pending, running, succeeded, failed, skipped
ExecutionPlanStatus — draft, validated, approved, running, completed,
                      failed, superseded

# Models
Mission          — id, workspace_id, intent, status, trigger,
                   requires_approval, created_at, updated_at, completed_at

ExecutionPlan    — id, mission_id, version, planner, status,
                   validation_errors (JSONB), approved_at, approved_by

MissionStep      — id, mission_id (denorm), execution_plan_id, parent_step_id,
                   order, type, tool, input, output, status,
                   started_at, finished_at, retry_count

MissionContext   — id, mission_id, conversation_id, event_id,
                   available_capabilities, workspace_config (JSONB), metadata_

MissionArtifact  — id, mission_id, step_id, type, mime, name, uri, metadata_

MissionLog       — id, mission_id, step_id, level, message, metadata_
```

### 5.3 Migration 006 + 007

- **006** — tabelas base: missions, mission_steps, mission_contexts, mission_artifacts, mission_logs. Todos os enums.
- **007** — tabela `execution_plans`. Adiciona `execution_plan_id` em `mission_steps`. Backfill: cria um `ExecutionPlan` por mission existente. Adiciona FK constraint depois do backfill.

### 5.4 MissionEngine

Métodos implementados:
- `create()` — cria Mission + MissionContext + publica `mission.created`
- `plan()` — cria `ExecutionPlan` (draft), chama PlanProvider, chama PlanValidator, transita para VALIDATED ou FAILED
- `approve()` / `reject()` — aprovação humana do ExecutionPlan
- `start()` — transita para RUNNING
- `fail()` / `cancel()` / `pause()` / `resume()`
- `update_step()` — atualiza status/output de um step
- `get()` / `list_missions()`
- `transition()` — valida e executa transições de estado

### 5.5 Plan System

**PlanProvider (interface):**
```python
class PlanProvider(Protocol):
    name: str
    async def create_execution_plan(mission: Mission) -> list[MissionStep]: ...
```

**Implementações:**
- `LLMPlanProvider` — chama Ollama com contexto de capabilities, parseia JSON com steps
- `WorkflowPlanProvider` — carrega WorkflowTemplate do registro, converte para steps com resolução de `{{ }}` variables

**WorkflowTemplate com resolução de variáveis:**
```yaml
steps:
  - tool: rag.chunk
    input: { file: "{{ workspace_config.vault_path }}" }
  - tool: knowledge.store
    input: { source: "{{ metadata_.source }}" }
```
Variáveis são resolvidas em tempo de execução usando `workspace_config + metadata_` da Mission.

**PlanValidator (`engines/plan/validator.py`):**
```python
@dataclass
class ValidationError:
    code: str
    message: str
    step_index: int | None
    detail: dict

@dataclass
class ValidationResult:
    valid: bool
    errors: list[ValidationError]
    warnings: list[ValidationError]

class PlanValidator:
    def validate(
        self, steps, mission, registry,
        workspace_permissions=None,
        available_context_keys=None,
    ) -> ValidationResult: ...
```

---

## 6. Event System — Implementação Completa

### 6.1 Event Envelope (`kernel/events/schema.py`)

```python
@dataclass
class KhonshuEvent:
    id:             UUID
    type:           str        # "mission.created", "knowledge.updated", ...
    version:        str        # "1.0"
    workspace_id:   UUID
    correlation_id: UUID       # compartilhado por toda a cadeia causal
    causation_id:   UUID|None  # evento pai direto
    actor:          str        # "user"|"scheduler"|"agent"|"system"
    source:         str        # "chat"|"scheduler"|"mission"|"inbox"
    payload:        dict
    metadata:       dict
    priority:       int        # 0 (baixo) a 9 (crítico)
    occurred_at:    datetime
```

### 6.2 DomainEventType (eventos implementados)

```python
class DomainEventType:
    MISSION_CREATED               = "mission.created"
    MISSION_PLANNING              = "mission.planning"
    MISSION_PLAN_VALIDATION_FAILED = "mission.plan_validation_failed"
    MISSION_READY                 = "mission.ready"
    MISSION_RUNNING               = "mission.running"
    MISSION_STEP_STARTED          = "mission.step.started"
    MISSION_STEP_COMPLETED        = "mission.step.completed"
    MISSION_STEP_FAILED           = "mission.step.failed"
    MISSION_COMPLETED             = "mission.completed"
    MISSION_FAILED                = "mission.failed"
    MISSION_CANCELLED             = "mission.cancelled"
    DOCUMENT_INGESTED             = "document.ingested"
    KNOWLEDGE_UPDATED             = "knowledge.updated"
    MEMORY_CREATED                = "memory.created"
    SCHEDULER_FIRED               = "scheduler.fired"
    WORKSPACE_CREATED             = "workspace.created"

EventType = DomainEventType  # alias de retrocompatibilidade
```

### 6.3 InfraEventType (canal separado)

```python
class InfraEventType:
    PLUGIN_LOADED          = "plugin.loaded"
    LLM_AVAILABLE          = "llm.available"
    DATABASE_CONNECTED     = "database.connected"
    EVENT_BUS_CONNECTED    = "eventbus.connected"
    CONTAINER_STARTED      = "infrastructure.container.started"
    HTTP_REQUEST_RECEIVED  = "http.request.received"
    EMBEDDING_CACHE_HIT    = "embedding.cache.hit"
```

### 6.4 EventBus (`kernel/events/bus.py`)

```python
# Canais
_EVENTS_CHANNEL = "khonshu.events"   # domínio
_INFRA_CHANNEL  = "khonshu.infra"    # infraestrutura

# Métodos de domínio (existentes)
subscribe_event(event_type, handler)
publish_event(event)

# Métodos de infra (novos)
subscribe_infra(event_type, handler)
publish_infra_event(event)
_dispatch_infra(conn, pid, channel, payload_str)

# Wildcard para EventTriggers do Scheduler
# _dispatch_typed agora despacha para handlers de tipo exato E para "*":
for handler in (
    self._typed_handlers.get(event.type, [])
    + self._typed_handlers.get("*", [])
):
    asyncio.create_task(self._safe_typed_call(handler, event))
```

O suporte a `"*"` foi necessário porque o `SchedulerEngine` precisa receber todos os eventos de domínio para verificar `EventTrigger`s.

---

## 7. Capability Registry — Implementação Completa

`kernel/capabilities/registry.py`:

```python
@dataclass
class CapabilityTool:
    name: str
    description: str
    fn: Callable
    parameters: dict

@dataclass
class Capability:
    name: str
    description: str
    plugin: str
    tags: list[str]
    tools: dict[str, CapabilityTool]
    permissions: list[str]          # novo
    required_context: list[str]     # novo
    dependencies: list[str]         # novo
    events_consumed: list[str]      # novo
    events_produced: list[str]      # novo

class CapabilityRegistry:
    register(capability)
    get(name) -> Capability
    get_tool(tool_name) -> CapabilityTool | None   # para o Executor
    list_capabilities() -> list[Capability]
    to_planner_context() -> str   # para o LLM Planner
```

---

## 8. Knowledge Engine — Implementação Completa

### 8.1 Modelos (`models/knowledge.py`)

```python
class EntityType(StrEnum):
    person, service, device, concept, place, organization, document, other

class Entity(Base):          # knowledge_entities
    id, workspace_id, name, type, aliases (JSONB), embedding (Vector)

class Relation(Base):        # knowledge_relations
    id, workspace_id, source_entity_id, relation, target_entity_id,
    confidence, source_type, metadata_

class Fact(Base):             # knowledge_facts
    id, workspace_id, entity_id, statement, source_type, source_id,
    confidence, superseded_by_id, created_at

class Observation(Base):      # knowledge_observations
    id, workspace_id, entity_id, statement,
    derived_from, derivation_agent, sample_size,
    confidence, reinforcement_count, last_reinforced_at,
    expires_at, expired, created_at
```

### 8.2 Migration 008

- 4 tabelas: `knowledge_entities`, `knowledge_relations`, `knowledge_facts`, `knowledge_observations`
- Índices FTS em português: `ix_knowledge_entities_name_fts`, `ix_knowledge_facts_statement_fts`

### 8.3 KnowledgeEngine (`engines/knowledge/engine.py`)

```python
class KnowledgeEngine:
    # Entities
    get_or_create_entity(workspace_id, name, entity_type, aliases)
    list_entities(workspace_id, entity_type, limit)

    # Relations
    add_relation(workspace_id, source_entity_id, relation, target_entity_id)

    # Facts
    store_fact(workspace_id, statement, source_type, source_id, entity_id, confidence)
    list_facts(workspace_id, entity_id, include_superseded, limit)

    # Observations
    store_observation(workspace_id, statement, derived_from, derivation_agent,
                      entity_id, confidence, sample_size, expires_in_days)
    reinforce_observation(observation_id, confidence_delta, new_sample_size)
    list_observations(workspace_id, entity_id, min_confidence, include_expired, limit)

    # Decay job — chamado periodicamente pelo Scheduler
    run_decay(workspace_id) -> int   # retorna count de observations expiradas

    # Para o PromptEngine
    build_prompt_context(workspace_id, min_observation_confidence) -> str
```

---

## 9. Scheduler — Implementação Completa

### 9.1 Modelo (`models/scheduler.py`)

```python
class TriggerType(StrEnum):   temporal, event, rule
class TriggerStatus(StrEnum): active, paused, disabled

class SchedulerTrigger(Base):   # scheduler_triggers
    id, workspace_id, name, description
    type: TriggerType
    status: TriggerStatus

    # Temporal
    cron_expression: str | None
    timezone: str

    # Event
    event_type: str | None
    event_filter: dict | None  # JSONB — filtra por workspace_id e campos do payload

    # Rule
    rule_expression: str | None
    poll_interval_seconds: int

    # Missão gerada
    mission_intent_template: str   # suporta {{ }} para variáveis
    mission_context: dict | None   # JSONB — contexto passado para a Mission
    requires_approval: bool

    # Metadados
    last_fired_at, next_fire_at, fire_count, created_at, updated_at
```

### 9.2 Migration 009

- Enums `trigger_type`, `trigger_status`
- Tabela `scheduler_triggers`
- Índices: workspace_id, type, status, next_fire_at, event_type

### 9.3 SchedulerEngine (`engines/scheduler/engine.py`)

```python
class SchedulerEngine:
    def __init__(self, session_factory, mission_engine):
        event_bus.subscribe_event("*", self._on_domain_event)

    async def tick(self) -> None:
        # chamado a cada 60s pelo lifespan loop
        # dispara TemporalTriggers com next_fire_at <= now
        # dispara RuleTriggers (avalia rule_expression)

    async def _on_domain_event(self, event: KhonshuEvent) -> None:
        # match de EventTriggers por event.type + workspace_id + event_filter

    async def _fire(self, trigger, event_context=None) -> None:
        # renderiza template {{ }} com event_context
        # publica SCHEDULER_FIRED
        # chama mission_engine.create(...)
        # atualiza last_fired_at, fire_count, next_fire_at

    async def _evaluate_rule(self, trigger) -> bool:
        # eval() restrito + check de poll_interval

    # CRUD de triggers
    create_trigger, list_triggers, get_trigger,
    pause_trigger, resume_trigger, delete_trigger
```

**Três tipos de trigger:**

| Tipo | Semântica | Exemplo |
|---|---|---|
| `TemporalTrigger` | Cron expression | `"0 8 * * *"` — todo dia às 8h |
| `EventTrigger` | Reage a evento de domínio | `"document.ingested"` → summarize |
| `RuleTrigger` | Condição booleana avaliada periodicamente | `cpu_avg_5m > 90` |

### 9.4 Lifespan Loop (main.py)

```python
async def _scheduler_tick_loop() -> None:
    while True:
        await scheduler.tick()
        await asyncio.sleep(60)

tick_task = asyncio.create_task(_scheduler_tick_loop())
# on shutdown: tick_task.cancel()
```

---

## 10. Memory Engine — Evolução (Phase 2C)

### 10.1 Novos campos (`models/memory.py`)

```python
class Memory(Base):
    # campos anteriores ...
    confidence: float    # server_default="1.0"
    importance: float    # server_default="0.5"
    source: str | None   # "conversation"|"mission"|"user_explicit"|"agent"
    source_id: UUID | None  # auto-referência (FK com use_alter=True)
    expires_at: datetime | None
```

### 10.2 Migration 010

- ADD COLUMN: confidence, importance, source, source_id, expires_at
- FK com `use_alter=True` (evita deadlock na auto-referência)
- Índices: `ix_memories_workspace_id`, `ix_memories_expires_at`

### 10.3 Recall com RRF + importance boost

```sql
WITH bm25 AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY ts_rank(fts, q) DESC) AS rank
    FROM memories WHERE ...AND fts @@ q
),
vec AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY embedding <=> :vector) AS rank
    FROM memories WHERE ...
),
rrf AS (
    SELECT COALESCE(b.id, v.id) AS id,
           COALESCE(1.0 / (60 + b.rank), 0) + COALESCE(1.0 / (60 + v.rank), 0)
           AS rrf_score
    FROM bm25 b FULL OUTER JOIN vec v ON b.id = v.id
)
SELECT m.id FROM rrf
JOIN memories m ON m.id = rrf.id
-- Memórias expiradas excluídas
WHERE (m.expires_at IS NULL OR m.expires_at > now())
-- Boost de importância
ORDER BY rrf.rrf_score * (0.5 + 0.5 * m.importance) DESC
```

**Fórmula:** `score_final = rrf_score × (0.5 + 0.5 × importance)`

Memórias expiradas são excluídas do recall. Memórias de alta importância (próximas de 1.0) têm score até 2× maior que memórias de baixa importância.

---

## 11. Cognitive Inbox — Implementação Completa

### 11.1 O que é

O Cognitive Inbox é o **pipeline universal de entrada** do PAIOS. Qualquer conteúdo externo — mensagem de texto, arquivo, URL, email, nota, evento — entra aqui primeiro. O `InboxEngine` decide para onde vai:

```
InboxItem (pending)
    │
    ▼
InboxEngine._classify() — chama LLM com prompt de roteamento
    │
    ├── route = "knowledge" → KnowledgeEngine.store_fact()
    ├── route = "task"      → MissionEngine.create()
    ├── route = "both"      → ambos os acima
    └── route = "dismiss"   → marca como dismissed
```

### 11.2 Modelo (`models/inbox.py`)

```python
class InboxItemType(StrEnum):   text, file, url, email, note, event
class InboxItemStatus(StrEnum): pending, processing, routed_knowledge,
                                 routed_task, routed_both, dismissed

class InboxItem(Base):   # inbox_items
    id, workspace_id
    type: InboxItemType
    status: InboxItemStatus
    raw_content: str
    title: str | None
    source: str           # "api"|"email"|"telegram"|"obsidian"|"webhook"
    metadata_: dict       # JSONB
    mission_id: UUID | None   # FK → missions (SET NULL)
    knowledge_extracted: bool
    routing_notes: str | None
    created_at, processed_at
```

### 11.3 Migration 011

- Enums `inbox_item_type`, `inbox_item_status`
- Tabela `inbox_items`
- FKs para `workspaces` (CASCADE) e `missions` (SET NULL)
- Índices: workspace_id, status, type, created_at

### 11.4 Prompt de roteamento

```
Você é o roteador do Cognitive Inbox do PAIOS.
...
Responda SOMENTE com JSON válido:
{
  "route": "knowledge|task|both|dismiss",
  "title": "...",
  "reasoning": "...",
  "mission_intent": "...",  // se task ou both
  "key_facts": ["..."]      // se knowledge ou both
}
```

### 11.5 InboxEngine (`engines/inbox/engine.py`)

```python
class InboxEngine:
    submit(workspace_id, raw_content, item_type, title, source,
           metadata, process_now) -> InboxItem

    process(item_id) -> InboxItem   # classifica + roteia via LLM

    list_items(workspace_id, status, item_type, limit, offset)
    get_item(item_id)
    dismiss(item_id)
```

### 11.6 Router (`routers/inbox.py`)

5 endpoints sob `/workspaces/{workspace_id}/inbox`:

| Método | Path | Ação |
|---|---|---|
| POST | `` | Submit novo item |
| GET | `` | Lista itens (filtro por status/type) |
| GET | `/{item_id}` | Get item |
| POST | `/{item_id}/process` | Processa item manualmente |
| POST | `/{item_id}/dismiss` | Descarta item |

---

## 12. Correções e Bugfixes Técnicos

### 12.1 EventBus wildcard `"*"` não despachava

**Problema:** `SchedulerEngine` registrava handler com `"*"` mas `_dispatch_typed` só buscava handlers por tipo exato. EventTriggers nunca disparavam.

**Fix:** Concatenar handlers do tipo exato com handlers de `"*"`:
```python
for handler in (
    self._typed_handlers.get(event.type, [])
    + self._typed_handlers.get("*", [])
):
    asyncio.create_task(self._safe_typed_call(handler, event))
```

### 12.2 Bug `DomainDomainEventType` ao usar replace_all

**Problema:** Replace_all de `"EventType."` → `"DomainEventType."` em arquivos que já tinham `"DomainEventType."` gerou `"DomainDomainEventType."`.

**Fix:** Segundo replace_all para corrigir `"DomainDomainEventType."` → `"DomainEventType."`.

### 12.3 Import local dentro de método (ruff I001)

**Problema:** `from sqlalchemy import func, select as sa_select` dentro do método `plan()`.

**Fix:** Mover `func` para o import de nível superior, substituir `sa_select` pelo `select` já importado no topo.

### 12.4 Line too long E501 em `models/memory.py`

**Problema:** FK de `source_id` em uma linha só ultrapassava 80 chars.

**Fix:** Quebrar `ForeignKey(...)` em múltiplas linhas com `use_alter=True` e `name=`.

### 12.5 Ruff auto-fixes aplicados

- UP042: `str, enum.Enum` → `StrEnum`
- UP017: `datetime.timezone.utc` → `datetime.UTC`
- UP007: `Optional[X]` → `X | None`
- UP035: `from typing import ...` → `from collections.abc import ...`
- I001: ordenação de imports em todos os arquivos novos

---

## 13. Stack de Dados — Todas as Migrations

| Migration | Tabelas criadas |
|---|---|
| 001 | workspaces, memories (+ pgvector) |
| 002 | conversations, messages |
| 003 | documents, document_chunks |
| 004 | workspace_plugins |
| 005 | obsidian_notes, obsidian_links |
| 006 | missions, mission_steps, mission_contexts, mission_artifacts, mission_logs |
| 007 | execution_plans + execution_plan_id em mission_steps |
| 008 | knowledge_entities, knowledge_relations, knowledge_facts, knowledge_observations |
| 009 | scheduler_triggers |
| 010 | confidence, importance, source, source_id, expires_at em memories |
| 011 | inbox_items |

---

## 14. Routers HTTP — Endpoints disponíveis

| Prefixo | Router | Operações |
|---|---|---|
| `/workspaces` | workspaces.py | CRUD workspaces |
| `/workspaces/{id}/conversations` | conversations.py | CRUD + chat SSE |
| `/workspaces/{id}/documents` | documents.py | ingestão + RAG |
| `/workspaces/{id}/memories` | memories.py | remember, recall, list |
| `/workspaces/{id}/missions` | missions.py | lifecycle completo |
| `/workspaces/{id}/triggers` | scheduler.py | CRUD triggers + pause/resume |
| `/workspaces/{id}/inbox` | inbox.py | submit, list, get, process, dismiss |
| `/workspaces/{id}/obsidian` | obsidian.py | sync, search, graph |
| `/plugins` | plugins.py | enable/disable por workspace |

---

## 15. O que ainda não foi implementado

| Item | Prioridade | Referência |
|---|---|---|
| `StorageProvider` concreto | Média | ADR-003 |
| `MetricsProvider` / InfluxDB | Média | OBSERVABILITY.md |
| Decay job do Knowledge Engine (via Scheduler) | Média | ADR-005 |
| Executor de steps (rodar tools) | Alta | mission-lifecycle.md |
| Endpoints GET para Knowledge Engine | Baixa | — |
| Trocar modelo Ollama: `qwen2.5:3b` | Alta | correção thinking mode |
| Testar sync do Obsidian com vault real | Média | — |
| `engines/plan/__init__.py` exportar PlanValidator | Baixa | — |

---

## 16. Arquivos criados/modificados nesta sessão

### Documentação
- `docs/architecture/ARCHITECTURE.md` — documento principal (v2.0, completo)
- `docs/architecture/mission-lifecycle.md` — state machine + sequence diagram
- `docs/architecture/OBSERVABILITY.md` — catálogo de métricas
- `docs/architecture/adr/ADR-001.md` — Mission/ExecutionPlan/MissionStep
- `docs/architecture/adr/ADR-002.md` — Domain vs Infrastructure events
- `docs/architecture/adr/ADR-003.md` — Provider Abstraction Layer
- `docs/architecture/adr/ADR-004.md` — Capability Registry semântico
- `docs/architecture/adr/ADR-005.md` — Fact vs Observation
- `docs/architecture/adr/ADR-006.md` — PlanValidator

### Models
- `models/mission.py` — ExecutionPlan, ExecutionPlanStatus, campos evolution
- `models/knowledge.py` — Entity, Relation, Fact, Observation (novo)
- `models/scheduler.py` — SchedulerTrigger, TriggerType, TriggerStatus (novo)
- `models/memory.py` — confidence, importance, source, source_id, expires_at
- `models/inbox.py` — InboxItem, InboxItemType, InboxItemStatus (novo)

### Migrations
- `alembic/versions/007_execution_plans.py` — novo
- `alembic/versions/008_knowledge.py` — novo
- `alembic/versions/009_scheduler.py` — novo
- `alembic/versions/010_memory_evolution.py` — novo
- `alembic/versions/011_inbox.py` — novo

### Engines
- `engines/mission/engine.py` — PlanValidator integrado, ExecutionPlan, eventos tipados
- `engines/plan/validator.py` — PlanValidator (novo)
- `engines/plan/workflow.py` — resolução de variáveis `{{ }}` (novo)
- `engines/knowledge/engine.py` — KnowledgeEngine completo (novo)
- `engines/scheduler/engine.py` — SchedulerEngine completo (novo)
- `engines/memory/engine.py` — RRF + importance boost + expiry
- `engines/inbox/engine.py` — InboxEngine com roteamento LLM (novo)

### Kernel
- `kernel/events/schema.py` — DomainEventType, InfraEventType, EventType alias
- `kernel/events/bus.py` — canais separados, wildcard dispatch, infra channel
- `kernel/capabilities/registry.py` — Capability com permissions, context, events

### Routers e Schemas
- `routers/scheduler.py` — 6 endpoints (novo)
- `routers/inbox.py` — 5 endpoints (novo)
- `schemas/scheduler.py` — CreateTriggerRequest, TriggerResponse (novo)
- `schemas/inbox.py` — SubmitInboxRequest, InboxItemResponse, ProcessResultResponse (novo)

### Core
- `core/dependencies.py` — get_knowledge_engine, get_scheduler_engine, get_inbox_engine
- `main.py` — scheduler tick loop, inbox init, registro de routers
