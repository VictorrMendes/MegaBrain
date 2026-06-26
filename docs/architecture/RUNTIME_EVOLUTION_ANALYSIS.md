# PAIOS — Análise Arquitetural de Evolução do Runtime
**Fase 0–3 do Protocolo Obrigatório de Revisão Arquitetural**  
**Data:** 2026-06-26  
**Escopo:** 12 áreas de evolução propostas pelo Arquiteto Principal

---

## Nota Prévia

Este documento é obrigatoriamente produzido **antes de qualquer linha de código**.  
As Fases 0–3 devem ser concluídas e revisadas antes de iniciar a Fase 4 (Implementação).

---

## Fase 0 — Entendimento do Problema

Perguntas obrigatórias respondidas para cada item proposto.

---

### Item 1 — KhonshuRuntime

**Q1. Qual problema real resolve?**  
O boot do sistema está espalhado entre `main.py` (lifespan FastAPI) e `core/dependencies.py` (singletons lazy). Se adicionarmos uma segunda interface (CLI, Telegram Bot, Worker assíncrono), não existe um ponto único de inicialização para reutilizar. Todo boot logic teria que ser duplicado.

**Q2. Já é resolvido por algum componente existente?**  
Parcialmente. `core/dependencies.py` gerencia singletons. `main.py` gerencia a sequência de boot via `@asynccontextmanager lifespan`. Mas esses dois não compõem um Runtime — são código FastAPI específico.

**Q3. Pertence ao domínio do PAIOS ou é conveniência de implementação?**  
Pertence ao **Kernel** do PAIOS. Um Sistema Operacional Cognitivo precisa de um Kernel explícito. O Runtime não é uma conveniência — é a afirmação arquitetural de que o domínio existe independente da interface web.

**Q4. Cria novo conceito ou estende existente?**  
Novo conceito, mas substitui código existente. `KhonshuRuntime` não se sobrepõe a nada — ele consolida o que hoje está dividido em dois arquivos sem identidade formal.

**Q5. Justificativa para o novo conceito:**  
A arquitetura declara "o Kernel é o centro" mas nenhuma classe se chama Kernel. O `main.py` deveria ser um adapter FastAPI que instancia `KhonshuRuntime`, não a sede do boot logic.

---

### Item 2 — Dependency Graph / Eliminar acoplamento entre engines

**Q1. Qual problema real resolve?**  
`SchedulerEngine.__init__` recebe `mission_engine: object`. `InboxEngine.__init__` recebe `mission_engine: object` e `knowledge_engine: object`. A tipagem `object` é um sinal de que há um acoplamento indesejado que foi resolvido com gambiarras de tipo, não com design.

**Q2. Já é resolvido?**  
Não. O tipo `object` é um workaround que esconde o problema.

**Q3. Domínio ou infraestrutura?**  
Problema de design arquitetural. Impacta o domínio porque cria dependências que dificultam a evolução independente dos engines.

**Q4. Novo conceito ou extensão?**  
Extensão. O Event Bus já existe. A solução é usar o que já existe: engines comunicam via eventos, não via chamadas diretas.

**Q5. Por que não pode ser representado pelo atual?**  
Pode — e deve. O InboxEngine não deve chamar `mission_engine.create()` diretamente. Deve publicar um evento `inbox.item_routed_as_task`. O MissionEngine deve subscribir e criar a missão. Isso elimina o acoplamento sem introduzir novos conceitos.

---

### Item 3 — ExecutionContext

**Q1. Qual problema real resolve?**  
Quando um Executor rodar steps de uma missão, cada step precisa de: variáveis de steps anteriores, artifacts gerados, configurações do workspace, permissões, referências a engines. Sem um objeto de contexto, o Executor seria um god object que importa todos os engines.

**Q2. Já é resolvido?**  
Parcialmente. `MissionContext` no banco de dados guarda a configuração inicial da missão. Mas `MissionContext` é um modelo de persistência — não é um objeto de runtime. Durante execução, o contexto cresce (outputs de steps anteriores alimentam inputs dos próximos).

**Q3. Domínio ou infraestrutura?**  
Domínio. ExecutionContext é um Value Object do DDD — representa o estado completo de uma execução em andamento.

**Q4. Novo conceito ou extensão?**  
Novo conceito distinto de `MissionContext`. O `MissionContext` (DB) é o ponto de partida; o `ExecutionContext` (runtime) é o estado vivo durante execução.

**Q5. Justificativa:**  
Sem ExecutionContext, steps não podem receber outputs de steps anteriores. Workflows como `{{ steps[0].output.text }}` ficam impossíveis. O contexto de execução não pode ser substituído pelo contexto de banco de dados.

---

### Item 4 — MissionArtifact (pipeline)

**Q1. Qual problema real resolve?**  
`MissionArtifact` existe como modelo de banco. Nenhum componente cria artifacts durante execução. Um mission step que gera um relatório em PDF não tem mecanismo para persistir esse PDF e vinculá-lo à missão.

**Q2. Já é resolvido?**  
O modelo está criado (migration 006). O pipeline de criação não existe.

**Q3. Domínio ou infraestrutura?**  
Domínio. Artifacts são a saída tangível de missões. Sem eles, o sistema não tem "memória de o que fez".

**Q4. Novo conceito?**  
Não — o conceito já existe. Precisa de implementação no Executor.

**Conclusão:** Não é um item independente. Faz parte do Executor (Item 8). Quando o Executor existir, artifacts são gerados naturalmente.

---

### Item 5 — Transaction Policies

**Q1. Qual problema real resolve?**  
Hoje não há definição de o que fazer quando um step falha. Retry? Abortar a missão? Tentar uma ação compensatória? Ignorar e continuar? Sem política, o Executor teria que tomar decisões arbitrárias.

**Q2. Já é resolvido?**  
`retry_count` existe em `MissionStep` mas não há política — apenas um contador. O `_MAX_RETRIES = 3` em `MissionEngine` é hardcoded, não configurável por step.

**Q3. Domínio ou infraestrutura?**  
Domínio. A política de falha é parte da semântica de um step de missão.

**Q4. Novo conceito ou extensão?**  
Extensão. Adicionar `failure_policy: FailurePolicy` como enum em `MissionStep`. Sem nova tabela ou classe.

---

### Item 6 — Evolução do Capability Registry

**Q1. Qual problema real resolve?**  
O Planner escolhe tools sem saber o custo, risco ou latência estimada. Isso leva a planos que selecionam ferramentas destrutivas quando ferramentas mais seguras resolveriam o mesmo problema.

**Q2. Já é resolvido?**  
Não. `Capability` tem `permissions` e `required_context` mas não tem `risk_level`, `estimated_latency_ms`, `side_effects` ou `estimated_cost`.

**Q3. Domínio ou infraestrutura?**  
Domínio. Os metadados de uma capability são parte da sua identidade semântica.

**Q4. Novo conceito?**  
Extensão do dataclass `Capability` existente.

---

### Item 7 — PolicyEngine

**Q1. Qual problema real resolve?**  
`PermissionEngine` responde: "este workspace tem autorização para usar X?". `PolicyEngine` responde: "o PAIOS deve executar X neste momento, independente de permissões?". São perguntas diferentes. Um workspace pode ter permissão para deletar arquivos, mas a política global pode exigir confirmação humana antes de qualquer deleção.

**Q2. Já é resolvido?**  
Não. `PermissionEngine` existe mas resolve uma questão diferente.

**Q3. Domínio ou infraestrutura?**  
Domínio. Regras de comportamento seguro são parte da identidade do PAIOS como sistema.

**Q4. Novo conceito?**  
Sim, e justificado. `PolicyEngine` ≠ `PermissionEngine`. O primeiro é system-wide e baseado em regras declarativas. O segundo é per-workspace e baseado em autorização.

---

### Item 8 — Executor

**Q1. Qual problema real resolve?**  
**O Executor não existe.** `MissionEngine` cria missões e gera planos mas nada executa os steps. PAIOS planeja mas nunca age. É o gap mais crítico da arquitetura atual.

**Q2. Já é resolvido?**  
Não. É o componente mais importante que está faltando.

**Q3. Domínio ou infraestrutura?**  
Domínio crítico. O Executor é o que transforma PAIOS de um planejador em um agente.

**Q4. Novo conceito?**  
Sim. O Executor não é uma extensão de nenhum componente existente — é o runtime de execução de steps.

---

### Item 9 — Observabilidade

**Q1. Qual problema real resolve?**  
`OBSERVABILITY.md` documenta métricas que deveriam existir, mas nenhuma é coletada. Operação em produção é cega.

**Q2. Já é resolvido?**  
Parcialmente. Structlog produz logs. Mas logs ≠ métricas.

**Q3. Domínio ou infraestrutura?**  
Infraestrutura de suporte. Não altera o domínio.

**Q4. Abordagem:**  
Estender o sistema de logging existente para emitir métricas via `MetricsProvider` Protocol (já definido em ADR-003 mas não implementado).

---

### Item 10 — Scheduler com prioridades

**Q1. Qual problema real resolve?**  
Quando múltiplos triggers disparam simultaneamente, não há critério de ordenação. Um trigger "critical" pode esperar enquanto um trigger "background" ocupa recursos.

**Q2. Já é resolvido?**  
Não. Todos os triggers têm a mesma prioridade implícita.

**Q3. Domínio ou infraestrutura?**  
Domínio. Prioridade de trigger é parte da definição do trigger.

**Q4. Novo conceito?**  
Extensão. Adicionar `priority: TriggerPriority` enum em `SchedulerTrigger`.

---

### Item 11 — LLMProvider com perfis de capacidade

**Q1. Qual problema real resolve?**  
Todas as chamadas ao LLM usam o mesmo modelo, independente da tarefa. Planejamento de missão complexa compete com classificação de inbox simples. Modelos maiores são usados para tarefas que modelos menores resolvem.

**Q2. Já é resolvido?**  
Não. `OllamaProvider` usa um modelo configurado globalmente.

**Q3. Domínio ou infraestrutura?**  
Provider (infraestrutura). O domínio solicita uma capacidade cognitiva; o provider decide qual modelo usar.

**Q4. Novo conceito?**  
Extensão do `LLMProvider` Protocol. Adicionar `generate_for_task(task_type, ...)`.

---

## Fase 1 — Análise Crítica da Arquitetura Atual

### 1.1 Inventário de Gargalos

| # | Problema | Categoria | Impacto | Urgência | Esforço |
|---|---|---|---|---|---|
| P1 | **Executor não existe** — steps nunca são executados | Domínio crítico | Crítico | Alta | Alto |
| P2 | **ExecutionContext não existe** — sem estado de runtime | Domínio crítico | Crítico | Alta | Médio |
| P3 | **Acoplamento direto entre engines** — `object` typing | Acoplamento | Alto | Média | Médio |
| P4 | **Boot espalhado** — sem KhonshuRuntime formal | Manutenibilidade | Alto | Baixa | Alto |
| P5 | **Sem Transaction Policies** — comportamento de falha undefined | Resiliência | Alto | Alta | Baixo |
| P6 | **Sem PolicyEngine** — execução sem regras de segurança | Segurança | Alto | Média | Médio |
| P7 | **MissionArtifact sem pipeline** — artefatos nunca criados | Domínio | Alto | Média | Médio |
| P8 | **Capability metadata incompleto** — Planner cego a risco/custo | Qualidade | Médio | Baixa | Baixo |
| P9 | **LLM modelo fixo** — não há routing por tarefa | Desempenho | Médio | Baixa | Baixo |
| P10 | **Scheduler sem prioridades** — triggers competem sem critério | Resiliência | Médio | Baixa | Baixo |
| P11 | **Sem métricas** — operação em produção é cega | Observabilidade | Médio | Baixa | Alto |
| P12 | **eval() inseguro em RuleTrigger** | Segurança | Alto | Alta | Baixo |

### 1.2 Análise de Acoplamento

**Acoplamentos atuais entre engines:**

```
InboxEngine ──calls──► KnowledgeEngine.store_fact()
InboxEngine ──calls──► MissionEngine.create()
SchedulerEngine ──calls──► MissionEngine.create()
MissionEngine ──imports──► capability_registry (global singleton)
MissionEngine ──imports──► event_bus (global singleton)
```

Os dois primeiros são acoplamentos que violam a regra de engines não conhecerem umas às outras.  
Os dois últimos são acoplamentos com o Kernel (Capability Registry, EventBus) — **esses são aceitáveis** porque o Kernel é exatamente quem deve ser referenciado.

**Acoplamentos aceitáveis (Kernel):**
- `MissionEngine` → `capability_registry` ✅
- `MissionEngine` → `event_bus` ✅
- `SchedulerEngine` → `event_bus` ✅

**Acoplamentos problemáticos (Engine → Engine):**
- `InboxEngine` → `KnowledgeEngine` ❌ — resolve com evento
- `InboxEngine` → `MissionEngine` ❌ — resolve com evento
- `SchedulerEngine` → `MissionEngine` ❌ — resolve com evento

### 1.3 Análise de Segurança

**P12 — eval() em RuleTrigger:**
```python
result = eval(trigger.rule_expression, {"__builtins__": {}}, {})
```
`{"__builtins__": {}}` não é suficiente para sandbox seguro em Python. Existe RCE via `().__class__.__mro__[1].__subclasses__()`. Este é um risco de segurança real e urgente.

Solução correta: usar `asteval` (biblioteca) ou parser de expressões próprio com whitelist de operações (comparações, operadores booleanos, literais numéricos, acesso a atributos pré-aprovados).

### 1.4 Análise de Concorrência

O `SchedulerEngine.tick()` é chamado a cada 60s em background. Se múltiplos triggers disparam ao mesmo tempo, são processados sequencialmente no mesmo loop. Para um single-developer com poucos triggers, isso é aceitável agora. Para escala, precisaria de uma fila de trabalho.

**Conclusão:** Não é um problema urgente dado o escopo do projeto. Documentar como limitação conhecida.

---

## Fase 2 — Avaliação de Cada Problema

### P1 + P2 — Executor + ExecutionContext (análise conjunta)

**Por que é um problema:**  
PAIOS é um Sistema Operacional Cognitivo que precisa **executar missões**. O sistema atual cria planos perfeitos que nunca saem do papel. Sem Executor, todo o resto (KnowledgeEngine, MemoryEngine, SchedulerEngine) existe para suportar algo que não funciona.

**Consequências futuras:**  
Sem Executor, o Knowledge Engine nunca recebe atualizações de resultados de missão. Artifacts nunca são gerados. O sistema de memória não aprende com o que fez. O loop cognitivo (agir → aprender → lembrar → agir melhor) é impossível.

**Alternativas:**

_Alternativa A: Execute dentro do MissionEngine_  
Adicionar método `execute(mission_id)` ao `MissionEngine`.
- Prós: Menos arquivos. O lifecycle da missão fica em um lugar.
- Contras: MissionEngine já é complexo. Adicionar execução de tools tornaria a classe responsável por lifecycle, planejamento E execução — violação de SRP.

_Alternativa B: StepExecutor separado, orquestrado pelo MissionEngine_  
`MissionEngine.execute()` delega para `StepExecutor.run(step, context)`.
- Prós: SRP respeitado. StepExecutor pode ser testado independentemente. Pode ser substituído.
- Contras: Mais uma classe. Um arquivo a mais.

**Decisão: Alternativa B.**  
`StepExecutor` é um componente do domínio de execução, não da lifecycle de missão. O MissionEngine mantém controle do estado (state machine), o StepExecutor executa a mecânica de cada step. Eles têm responsabilidades distintas.

**ExecutionContext design:**
```python
@dataclass
class ExecutionContext:
    mission_id: UUID
    workspace_id: UUID
    execution_plan_id: UUID
    variables: dict[str, Any]         # outputs de steps anteriores
    artifacts: list[ArtifactRef]      # refs para artifacts criados
    permissions: set[str]             # permissões do workspace
    workspace_config: dict            # config do workspace
    metadata: dict                    # metadata da mission
    logger: BoundLogger               # logger contextualizado
```

O `ExecutionContext` é criado pelo `MissionEngine` antes de iniciar a execução e passado ao `StepExecutor`. Não acessa o banco diretamente — recebe todos os dados necessários na construção.

---

### P3 — Acoplamento direto Engine → Engine

**Por que é um problema:**  
`InboxEngine` conhece a interface interna de `MissionEngine` e `KnowledgeEngine`. Se uma dessas interfaces mudar, o `InboxEngine` quebra. O acoplamento é bidirecional em tempo de runtime (um engine holding a reference to another).

**Consequências futuras:**  
Adicionar um novo tipo de routing no InboxEngine (ex: "route to KnowledgeEngine Observation, not Fact") exige mudança no InboxEngine. Adicionar um novo engine que também deve reagir a inbox events exige mudança no InboxEngine. O InboxEngine vira um hub de acoplamento.

**Alternativas:**

_Alternativa A: Protocol types para cada engine_  
```python
class MissionCreatable(Protocol):
    async def create(workspace_id, intent, ...) -> Mission: ...

class InboxEngine:
    def __init__(self, mission_engine: MissionCreatable): ...
```
- Prós: Type safety. Contrato explícito.
- Contras: Ainda é acoplamento direto — apenas tipado melhor.

_Alternativa B: InboxEngine comunica via eventos_  
```python
# InboxEngine publica:
event_bus.publish_event(KhonshuEvent(type="inbox.routed_as_task", ...))
event_bus.publish_event(KhonshuEvent(type="inbox.routed_as_knowledge", ...))

# MissionEngine subscribe:
event_bus.subscribe_event("inbox.routed_as_task", self._on_inbox_task)

# KnowledgeEngine subscribe:
event_bus.subscribe_event("inbox.routed_as_knowledge", self._on_inbox_knowledge)
```
- Prós: Zero coupling. Qualquer engine pode reagir a eventos do inbox sem o InboxEngine saber. Clean Architecture perfeita.
- Contras: Mais difícil de debugar. Não há garantia de que o handler executou. Requer eventos síncronos ou um padrão de request/reply.

**Decisão: Alternativa B no médio prazo, Alternativa A como passo transitório imediato.**

Razão: Refatorar InboxEngine e SchedulerEngine para comunicação event-driven é a decisão correta, mas requer que os novos eventos (`inbox.routed_as_task`, `inbox.routed_as_knowledge`) sejam definidos e que MissionEngine e KnowledgeEngine subscrevam a eles. Isso é válido mas tem risco de regressão se feito sem testes.

**Passo imediato:** Definir `MissionEngineProtocol` e `KnowledgeEngineProtocol` em `kernel/protocols/` para eliminar o `object` typing. Isso não resolve o acoplamento mas o torna explícito e verificável.

**Passo seguinte (Phase 2):** Migrar para comunicação event-driven, eliminando os Protocols.

---

### P5 — Sem Transaction Policies

**Por que é um problema:**  
Um step de missão pode falhar por: timeout do LLM, serviço externo indisponível, dado inválido, permissão negada em runtime, erro de rede. Cada caso tem tratamento diferente. Um erro de rede merece retry. Uma permissão negada não deve ser retentada. Uma ação compensatória pode ser necessária quando um step anterior já teve efeito.

**Alternativas:**

_Alternativa A: Política hardcoded no Executor_  
Retry 3x para todos os erros. Falha depois.
- Prós: Simples.
- Contras: Retenta operações que não devem ser retentadas. Não permite compensação.

_Alternativa B: `failure_policy` em `MissionStep`_  
```python
class FailurePolicy(StrEnum):
    retry      = "retry"       # tenta novamente (até max_retries)
    abort      = "abort"       # cancela a missão imediatamente
    skip       = "skip"        # marca o step como skipped, continua
    compensate = "compensate"  # executa compensation_tool se definido
    ignore     = "ignore"      # registra o erro, continua
```
- Prós: Por-step configurável. O Planner declara a política no momento do planejamento.
- Contras: Adiciona campo na migration + lógica no Executor.

**Decisão: Alternativa B.** Custo baixo (um campo enum + lógica simples no Executor). Valor alto (comportamento correto em falha). Adicionar como parte da migration que cria o Executor.

---

### P6 — Sem PolicyEngine

**Por que é um problema:**  
Sem regras de segurança globais, qualquer missão aprovada pode executar qualquer tool que o workspace tenha permissão. Um workspace com permissão `infrastructure.docker.write` poderia executar `docker.rm -f postgres` se o Planner gerasse tal step. A permissão autoriza, mas a política deve proibir deleção destrutiva sem confirmação.

**Alternativas:**

_Alternativa A: Regras hardcoded no Executor_  
Checklist de strings proibidas no Executor.
- Prós: Simples.
- Contras: Difícil de manter. Não é configurável por workspace. Viola separação de responsabilidades.

_Alternativa B: PolicyEngine com regras declarativas_  
```python
class PolicyRule:
    name: str
    description: str
    tools_affected: list[str]     # ou ["*"] para todas
    condition: str                # expressão avaliada
    action: PolicyAction          # require_confirmation | deny | log | allow
    severity: PolicySeverity

class PolicyEngine:
    def check(tool_name, step_input, context) -> PolicyDecision: ...
```
Regras default configuradas em YAML/código. Por workspace overridable.
- Prós: Declarativo. Auditável. Extensível.
- Contras: Mais um componente.

_Alternativa C: Embutir policies como metadados de Capability_  
Adicionar `requires_confirmation_for: list[str]` na Capability.
- Prós: Mantém conhecimento de segurança junto com a capability.
- Contras: Mistura a definição de capability com políticas de execução. Viola SRP.

**Decisão: Alternativa B, implementação mínima.**  
PolicyEngine com um conjunto pequeno de regras default. Simples de adicionar regras. Não é um framework completo — é uma checagem linear de regras antes de cada step. A versão inicial tem apenas `require_confirmation` e `deny`.

---

### P4 — Boot espalhado (KhonshuRuntime)

**Por que é um problema:**  
Hoje, remover FastAPI do projeto tornaria o PAIOS não inicializável. O domínio depende da interface. Isso viola a Hexagonal Architecture: interfaces devem adaptar o domínio, não contê-lo.

**Alternativas:**

_Alternativa A: KhonshuRuntime como classe completa_  
Objeto que encapsula todo o boot: providers, plugins, engines, event bus, scheduler.
- Prós: `main.py` vira apenas: `runtime = KhonshuRuntime(); runtime.start(); app = create_fastapi_app(runtime)`.
- Contras: Alto esforço. Pode quebrar o que funciona.

_Alternativa B: Refatorar `core/dependencies.py` minimamente_  
Renomear o módulo, adicionar uma função `boot()` e `shutdown()` que main.py chama.
- Prós: Mudança incremental. Menor risco.
- Contras: Não resolve o problema fundamental de design.

_Alternativa C: Manter como está — aceitar FastAPI como entry point único por ora_  
Para um projeto de single-developer sem necessidade imediata de múltiplas interfaces, o custo do refactoring agora pode não se pagar.
- Prós: Zero risco de regressão. Foca esforço no que faz o sistema funcionar (Executor).
- Contras: Dívida arquitetural que crescerá.

**Decisão: Alternativa A, mas adiada para Phase 2.**  
O KhonshuRuntime é arquiteturalmente correto mas não é o que impede o sistema de funcionar. O Executor é. Prioridade: Executor primeiro, Runtime segundo. Quando o Runtime for implementado, será uma classe thin que delega para o que já existe.

---

### P12 — eval() inseguro em RuleTrigger

**Por que é um problema:**  
Python `eval()` com `{"__builtins__": {}}` não é sandbox seguro. O seguinte é possível:
```python
().__class__.__mro__[1].__subclasses__()[X]()
```
Isso permite acesso a subclasses de `object` em tempo de execução.

**Urgência: Alta.** Mesmo sem intenção maliciosa, um usuário pode escrever uma expressão que causa efeitos colaterais inesperados.

**Alternativas:**

_Alternativa A: Usar `asteval` (biblioteca Python)_  
```python
from asteval import Interpreter
aeval = Interpreter()
result = aeval(expression)
```
- Prós: Seguro. Suporta operações matemáticas e booleanas. Fácil.
- Contras: Dependência adicional.

_Alternativa B: Parser próprio com AST whitelist_  
Percorrer a AST do Python e rejeitar nós não permitidos (apenas `Compare`, `BoolOp`, `Num`, `Name` conhecidos).
- Prós: Zero dependência extra.
- Contras: Implementação manual de parser. Propenso a erros.

**Decisão: Alternativa A.** `asteval` é uma biblioteca madura, pequena e focada exatamente neste caso. O custo de uma dependência é menor que o risco de um parser caseiro inseguro.

---

### P8/P9/P10 — Capability metadata, LLM profiles, Scheduler priorities

Esses três são extensões de baixo risco e baixo esforço a componentes existentes. Não requerem novos componentes. A análise é direta:

- **Capability metadata:** Adicionar campos ao dataclass `Capability`. `estimated_latency_ms: int`, `risk_level: RiskLevel`, `side_effects: list[str]`, `estimated_cost_units: float`. O `to_planner_descriptor()` os inclui.

- **LLM profiles:** Adicionar `task_type: LLMTaskType` ao método `generate()` do Protocol. `OllamaProvider` usa o tipo para selecionar o modelo: `reasoning → qwen3:8b`, `classification → qwen2.5:3b`, `embedding → nomic-embed-text`.

- **Scheduler priorities:** Adicionar `priority: TriggerPriority` enum ao modelo `SchedulerTrigger`. O `tick()` ordena triggers por prioridade antes de processar.

---

## Fase 3 — Validação de Princípios

Antes de cada componente proposto:

### KhonshuRuntime
- Necessário criar novo módulo? Sim — consolida código existente, não adiciona complexidade.
- Existente pode ser estendido? `core/dependencies.py` pode virar o Runtime com mudança mínima.
- Reduz ou aumenta complexidade? Reduz — elimina código espalhado em dois arquivos.
- Válido em 5 anos? Sim — qualquer SO cognitivo precisa de um Kernel explícito.
- Domínio independente da infraestrutura? Sim — FastAPI vira um adapter do Runtime.

### ExecutionContext
- Necessário? Sim — sem ele, o Executor seria um god object.
- Existente pode ser estendido? `MissionContext` (DB) é diferente. Não pode ser reutilizado.
- Reduz complexidade? Sim — centraliza estado de execução em vez de passá-lo por parâmetros.
- Válido em 5 anos? Sim — o padrão de Command/Context é fundamental em DDD.

### StepExecutor
- Necessário? Sim — é a peça mais crítica que está faltando.
- Existente pode ser estendido? `MissionEngine` poderia absorver, mas violaria SRP.
- Reduz complexidade? Sim — separa lifecycle management de execution mechanics.

### PolicyEngine
- Necessário? Sim — PermissionEngine e PolicyEngine têm semânticas diferentes.
- Existente pode ser estendido? PermissionEngine não é extensível para o caso de uso.
- Reduz complexidade? Não — adiciona componente. Mas o problema que resolve é real.
- Alternativa mais simples? Embutir regras como metadados de Capability (Alternativa C acima), mas isso viola SRP.

**Decisão final:** PolicyEngine como um componente thin que avalia uma lista de regras declarativas. Não é um motor de regras completo.

### Transaction Policies
- Necessário? Sim — o Executor precisa saber o que fazer em falha.
- Existente pode ser estendido? `MissionStep` recebe um campo novo. Zero componentes novos.
- Reduz complexidade? Sim — elimina lógica hardcoded de retry.

---

## Síntese: Problemas Reais vs. Gold Plating

Depois da análise Fase 0–3, classifiquei os 12 itens propostos:

### Devem ser implementados (problema real, justificado):

| Item | O que implementar | Prioridade |
|---|---|---|
| Executor | `StepExecutor` + `ExecutionContext` | **Crítica** |
| Transaction Policies | Campo `failure_policy` em `MissionStep` | **Alta** |
| Segurança: eval() | Substituir por `asteval` | **Alta** |
| Engine decoupling | Protocol types agora; eventos no futuro | **Média** |
| PolicyEngine | Componente thin com regras declarativas | **Média** |
| KhonshuRuntime | Refatorar `core/dependencies.py` | **Média** |
| LLM profiles | Estender Protocol + OllamaProvider | **Baixa** |
| Capability metadata | Estender dataclass Capability | **Baixa** |
| Scheduler priorities | Campo no modelo + ordenação no tick() | **Baixa** |

### Não implementar agora (custo > benefício ou prematuro):

| Item | Razão |
|---|---|
| Dashboard interno completo | Requer frontend próprio. Grafana + logs atendem agora. |
| Observabilidade full (MetricsProvider) | Alta complexidade. Logs estruturados são suficientes inicialmente. |
| Comunicação event-driven entre engines | Correto no longo prazo, alto risco agora sem testes. Fazer depois do Executor. |

---

## Roadmap de Implementação Proposto

### Phase 1 — Core Execution (o sistema passa a funcionar)
1. `alembic/versions/012_step_failure_policy.py` — adiciona `failure_policy` em `mission_steps`
2. `engines/execution/context.py` — `ExecutionContext` dataclass
3. `engines/execution/executor.py` — `StepExecutor`
4. `engines/mission/engine.py` — adicionar `execute()` que usa `StepExecutor`
5. Corrigir `eval()` inseguro no SchedulerEngine (substituir por `asteval`)

### Phase 2 — Runtime e Segurança
6. `kernel/policies/engine.py` — `PolicyEngine` com regras default
7. `kernel/runtime.py` — `KhonshuRuntime` refatorando `core/dependencies.py`
8. `main.py` — usar `KhonshuRuntime` como entry point

### Phase 3 — Qualidade de Inteligência
9. Estender `LLMProvider` Protocol com `task_type`
10. Estender `Capability` dataclass com risk/cost/latency
11. Estender `SchedulerTrigger` com `priority`
12. ADR-007: StepExecutor + ExecutionContext + Transaction Policies

### Phase 4 — Decoupling (evento-driven entre engines)
13. Definir novos `DomainEventType`: `inbox.routed_as_task`, `inbox.routed_as_knowledge`
14. Refatorar `InboxEngine` para publicar eventos (remover dependências diretas)
15. Refatorar `SchedulerEngine` para publicar eventos (remover dependência de MissionEngine)
16. ADR-008: Engine Communication Pattern

---

## Checklist Final (Fase 3 — antes de implementar)

- [x] Domínio continua independente da infraestrutura?
- [x] Nenhuma engine conhecerá implementações concretas?
- [x] Não foram criadas abstrações desnecessárias?
- [x] Não há duplicação de responsabilidades?
- [x] Segue Clean Architecture (dependências apontam para o domínio)?
- [x] Segue Hexagonal Architecture (adapters ao redor do domínio)?
- [x] Cada decisão tem justificativa técnica, não preferência?
- [x] Solução é compreensível por outro desenvolvedor?
- [x] A arquitetura ficará mais simples após as alterações?
- [x] As decisões continuarão válidas em 5 anos?

**Status: Análise concluída. Pronto para Fase 4 (Implementação).**
