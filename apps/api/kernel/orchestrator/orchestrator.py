"""CognitiveOrchestrator — the executive brain of Khonshu.

Coordinates the full cognitive pipeline for every user request:
  1. Build base context          (ContextBuilder)
  2. Decide routing              (DecisionEngine)
  3. Optional: web search        (SearchEngine)
  4. Optional: create mission    (MissionEngine)
  5. Generate response           (LLMProvider)
  6. Learn from the exchange     (LearningEngine)

No engine knows about the orchestrator. The orchestrator knows all
engines. Dependency direction is strictly one-way: router → orchestrator
→ engines.
"""
from __future__ import annotations

import contextlib
from collections.abc import Awaitable, Callable
from uuid import UUID

from kernel.logger import get_logger
from kernel.providers.base import ChatMessage, LLMProvider

from .decision import DecisionEngine
from .learning import LearningEngine
from .models import (
    ConversationResult,
    LearningAction,
    LearningActionType,
    LearningDecision,
    OrchestratorRequest,
    OrchestratorResponse,
    RiskLevel,
    TraceNode,
)
from .trace import ReasoningTrace

logger = get_logger("khonshu.orchestrator")


class CognitiveOrchestrator:
    """Coordinates all cognitive engines for a single user request.

    All constructor parameters except the first four are optional so
    the orchestrator degrades gracefully when an engine is unavailable.
    """

    def __init__(
        self,
        context_builder,
        decision_engine: DecisionEngine,
        learning_engine: LearningEngine,
        llm_provider: LLMProvider,
        memory_engine=None,
        knowledge_engine=None,
        search_engine=None,
        mission_engine=None,
        metrics=None,
    ) -> None:
        self._context = context_builder
        self._decision = decision_engine
        self._learning = learning_engine
        self._llm = llm_provider
        self._memory = memory_engine
        self._knowledge = knowledge_engine
        self._search = search_engine
        self._mission = mission_engine
        self._metrics = metrics

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    async def execute(
        self,
        request: OrchestratorRequest,
        on_step: Callable[["TraceNode"], Awaitable[None]] | None = None,
    ) -> OrchestratorResponse:
        """Run the full cognitive pipeline and return a rich response.

        on_step, if provided, is called after each pipeline step
        completes (or is skipped/failed). Use this for streaming UIs.
        """
        workspace_id = UUID(request.workspace_id)
        trace = ReasoningTrace()

        # ── 1. Build base context ────────────────────────────────────────
        ctx = await self._build_context(request, workspace_id, trace)
        if on_step:
            await on_step(trace.nodes[-1])

        # ── 2. Decide routing ────────────────────────────────────────────
        decision = await self._decide(request, trace)
        if on_step:
            await on_step(trace.nodes[-1])

        # ── 3. Optional: web search ──────────────────────────────────────
        search_context, internet_sources = await self._maybe_search(
            request, workspace_id, decision, trace
        )
        if on_step:
            await on_step(trace.nodes[-1])

        # ── 4. Optional: create mission ──────────────────────────────────
        missions_created = await self._maybe_create_mission(
            request, workspace_id, decision, trace
        )
        if on_step:
            await on_step(trace.nodes[-1])

        # ── 5. Generate response ─────────────────────────────────────────
        response_text = await self._generate(
            request, ctx, search_context, trace
        )
        if on_step:
            await on_step(trace.nodes[-1])

        # ── 6. Learn ─────────────────────────────────────────────────────
        learning_actions = await self._maybe_learn(
            request,
            decision,
            response_text,
            ctx,
            missions_created,
            workspace_id,
            trace,
        )
        if on_step:
            await on_step(trace.nodes[-1])

        return OrchestratorResponse(
            response=response_text,
            decision=decision,
            trace=trace.nodes,
            confidence=decision.confidence,
            risk=decision.risk_level,
            sources=[],
            capabilities_used=[],
            missions_created=missions_created,
            learning_actions=learning_actions,
            thinking_steps=trace.thinking_steps(),
            memory_used=ctx.memory_count,
            knowledge_used=ctx.knowledge_count,
            internet_sources=internet_sources,
            integrations_used=[],
            planner_used=decision.need_planner,
            mission_created=bool(missions_created),
            estimated_cost=decision.estimated_cost,
            estimated_time=decision.estimated_latency,
            approval_required=decision.need_confirmation,
        )

    # ------------------------------------------------------------------ #
    # Pipeline steps                                                       #
    # ------------------------------------------------------------------ #

    async def _build_context(self, request, workspace_id, trace):
        node = trace.begin("build_context", "ContextBuilder")
        _metrics_ctx = (
            self._metrics.time_context_build()
            if self._metrics else contextlib.nullcontext()
        )
        with _metrics_ctx:
            ctx = await self._context.build(
                workspace_id=workspace_id,
                user_message=request.message,
            )
        trace.complete(
            node,
            f"{ctx.memory_count} mem, "
            f"{ctx.knowledge_count} facts, "
            f"{ctx.chunk_count} chunks",
        )
        if self._metrics:
            self._metrics.record_memory_hit(ctx.memory_count)
            self._metrics.record_knowledge_hit(ctx.knowledge_count)
        return ctx

    async def _decide(self, request, trace):
        node = trace.begin("decide", "DecisionEngine")
        _metrics_ctx = (
            self._metrics.time_planning()
            if self._metrics else contextlib.nullcontext()
        )
        with _metrics_ctx:
            decision = await self._decision.decide(request.message)
        label = decision.reason or f"risk={decision.risk_level.value}"
        trace.complete(node, label)
        return decision

    async def _maybe_search(self, request, workspace_id, decision, trace):
        if not decision.need_search or self._search is None:
            reason = (
                "not needed"
                if not decision.need_search
                else "engine unavailable"
            )
            trace.skip("search", "SearchEngine", reason)
            return "", 0

        node = trace.begin("search", "SearchEngine")
        try:
            result = await self._search.search(
                request.message, workspace_id
            )
            summary = result.get("summary", "")
            count = result.get("count", 0)
            trace.complete(node, f"{count} results")
            if self._metrics:
                self._metrics.record_web_search()
            return summary, count
        except Exception as exc:
            trace.fail(node, str(exc))
            logger.warning("orchestrator.search_failed", error=str(exc))
            return "", 0

    async def _maybe_create_mission(
        self, request, workspace_id, decision, trace
    ):
        if not decision.need_mission or self._mission is None:
            reason = (
                "not needed"
                if not decision.need_mission
                else "engine unavailable"
            )
            trace.skip("create_mission", "MissionEngine", reason)
            return []

        node = trace.begin("create_mission", "MissionEngine")
        try:
            from models.mission import MissionTrigger
            requires_approval = (
                decision.need_confirmation
                or decision.risk_level != RiskLevel.low
            )
            conv_id = (
                UUID(request.conversation_id)
                if request.conversation_id else None
            )
            mission = await self._mission.create(
                workspace_id=workspace_id,
                intent=request.message,
                trigger=MissionTrigger.MANUAL,
                requires_approval=requires_approval,
                conversation_id=conv_id,
            )
            mission_ids = [str(mission.id)]
            trace.complete(node, f"mission {str(mission.id)[:8]}…")
            if self._metrics:
                self._metrics.record_auto_mission()
            return mission_ids
        except Exception as exc:
            trace.fail(node, str(exc))
            logger.warning(
                "orchestrator.mission_create_failed", error=str(exc)
            )
            return []

    async def _generate(self, request, ctx, search_context, trace):
        node = trace.begin("generate", "LLMProvider")
        enriched_prompt = ctx.system_prompt
        if search_context:
            enriched_prompt += (
                f"\n\n## Resultados de Pesquisa Web\n{search_context}"
            )
        try:
            result = await self._llm.chat(
                messages=[
                    ChatMessage(
                        role="system", content=enriched_prompt
                    ),
                    ChatMessage(
                        role="user", content=request.message
                    ),
                ],
            )
            response_text = result.content
            trace.complete(node, f"{len(response_text)} chars")
            return response_text
        except Exception as exc:
            trace.fail(node, str(exc))
            raise

    async def _maybe_learn(
        self,
        request,
        decision,
        response_text,
        ctx,
        missions_created,
        workspace_id,
        trace,
    ):
        if not decision.need_learning:
            trace.skip("learn", "LearningEngine", "not needed")
            return []

        node = trace.begin("learn", "LearningEngine")
        try:
            conv_result = ConversationResult(
                request=request,
                decision=decision,
                response=response_text,
                memories_retrieved=ctx.memory_count,
                knowledge_count=ctx.knowledge_count,
                missions_created=missions_created,
            )
            ld = await self._learning.decide(conv_result)
            applied: list[LearningAction] = []
            if ld.should_learn and ld.actions:
                applied = await self._apply_learning(ld, workspace_id)
            trace.complete(
                node,
                f"{len(applied)} applied — {ld.reason}",
            )
            return applied
        except Exception as exc:
            trace.fail(node, str(exc))
            logger.warning("orchestrator.learning_failed", error=str(exc))
            return []

    # ------------------------------------------------------------------ #
    # Learning application                                                 #
    # ------------------------------------------------------------------ #

    async def _apply_learning(
        self,
        ld: LearningDecision,
        workspace_id: UUID,
    ) -> list[LearningAction]:
        applied: list[LearningAction] = []
        for action in ld.actions:
            if action.type == LearningActionType.ignore:
                continue
            try:
                await self._persist_action(action, workspace_id)
                applied.append(action)
            except Exception as exc:
                logger.warning(
                    "orchestrator.learning_persist_failed",
                    type=action.type.value,
                    error=str(exc),
                )
        return applied

    async def _persist_action(
        self, action: LearningAction, workspace_id: UUID
    ) -> None:
        from models.memory import MemoryType

        t = action.type

        if t == LearningActionType.update_preference and self._memory:
            await self._memory.remember(
                workspace_id=workspace_id,
                content=action.content,
                type=MemoryType.semantic,
                confidence=action.confidence,
                importance=0.9,
                source="orchestrator",
            )

        elif t == LearningActionType.record_pattern and self._memory:
            await self._memory.remember(
                workspace_id=workspace_id,
                content=action.content,
                type=MemoryType.semantic,
                confidence=action.confidence,
                importance=0.7,
                source="orchestrator",
            )

        elif t == LearningActionType.create_memory and self._memory:
            await self._memory.remember(
                workspace_id=workspace_id,
                content=action.content,
                type=MemoryType.episodic,
                confidence=action.confidence,
                importance=0.6,
                source="orchestrator",
            )

        elif t == LearningActionType.create_fact and self._knowledge:
            await self._knowledge.store_fact(
                workspace_id=workspace_id,
                statement=action.content,
                source_type="orchestrator_learning",
                confidence=action.confidence,
            )

        elif (
            t == LearningActionType.create_observation
            and self._knowledge
        ):
            await self._knowledge.store_observation(
                workspace_id=workspace_id,
                statement=action.content,
                derived_from="orchestrator_learning",
                confidence=action.confidence,
                expires_in_days=7,
            )
