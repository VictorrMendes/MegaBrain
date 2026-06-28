"""CognitiveOrchestrator — the executive brain of Khonshu.

ADR-011: Tool-First Architecture.

Pipeline:
  1. Build base context  (ContextBuilder — memory, knowledge, RAG)
  2. Route intent        (IntentRouter — deterministic keyword analysis)
  3. Decide routing      (DecisionEngine LLM — merges IntentRouter flags)
  4. Execute caps        (CapabilityExecutor — search, integrations, missions)
  5. Generate response   (LLMProvider — only interprets Kernel outputs)
  6. Validate response   (CapabilityValidator — reject hallucinated limits)
  7. Learn               (LearningEngine)

The LLM never calls tools directly. It receives data produced by the Kernel
and synthesizes a response. The Kernel is the source of truth.
"""
from __future__ import annotations

import contextlib
import re
from collections.abc import Awaitable, Callable
from uuid import UUID

from kernel.logger import get_logger
from kernel.providers.base import ChatMessage, LLMProvider

from .capability_executor import CapabilityExecutor, CapabilityResult
from .decision import DecisionEngine
from .intent_router import IntentFlags, IntentRouter
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

TokenCallback = Callable[[str], Awaitable[None]]

logger = get_logger("khonshu.orchestrator")

# Phrases the LLM must never emit when the capability is active
_INVALID_SEARCH_PHRASES = [
    r"não tenho acesso à internet",
    r"nao tenho acesso a internet",
    r"não possuo acesso à internet",
    r"sem acesso à internet",
    r"não consigo acessar a internet",
    r"não tenho capacidade de buscar",
    r"não posso pesquisar",
]
_INVALID_DOCKER_PHRASES = [
    r"não consigo acessar containers",
    r"não tenho acesso ao docker",
    r"não posso monitorar containers",
]
_INVALID_CALENDAR_PHRASES = [
    r"não tenho (?:acesso (?:à|a)|integração de) (?:minha )?agenda",
    r"não consigo acessar (?:o )?calendário",
    r"não possuo calendário",
    r"sem acesso (?:ao )?calendário",
    r"não tenho integração de calendário",
]
_INVALID_WEATHER_PHRASES = [
    r"não consigo verificar (?:o )?clima",
    r"não tenho (?:acesso|dados) (?:a(?:o)?|sobre) (?:o )?clima",
    r"não possuo dados (?:de|do|sobre) clima",
    r"sem (?:acesso a(?:o)?|dados de) (?:o )?clima",
]
# Always invalid — regardless of which tool ran
_INVALID_GENERAL_PHRASES = [
    r"sou apenas (?:um )?(?:modelo|assistente|chatbot|ia) de linguagem",
    r"sou apenas um sistema local",
    r"não possuo (?:essa |esta )?capacidade",
    r"sou incapaz de",
    r"não tenho (?:essa |esta )?capacidade",
]


class CognitiveOrchestrator:
    """Coordinates all cognitive engines for a single user request."""

    def __init__(
        self,
        context_builder,
        decision_engine: DecisionEngine,
        learning_engine: LearningEngine,
        llm_provider: LLMProvider,
        capability_executor: CapabilityExecutor | None = None,
        memory_engine=None,
        knowledge_engine=None,
        metrics=None,
        session_factory=None,
    ) -> None:
        self._context = context_builder
        self._decision = decision_engine
        self._learning = learning_engine
        self._llm = llm_provider
        self._executor = capability_executor or CapabilityExecutor()
        self._memory = memory_engine
        self._knowledge = knowledge_engine
        self._metrics = metrics
        self._sessions = session_factory
        self._intent_router = IntentRouter()

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    async def execute(
        self,
        request: OrchestratorRequest,
        on_step: Callable[[TraceNode], Awaitable[None]] | None = None,
        on_token: TokenCallback | None = None,
    ) -> OrchestratorResponse:
        workspace_id = UUID(request.workspace_id)
        trace = ReasoningTrace()

        # ── 1. Build base context ────────────────────────────────────────
        ctx = await self._build_context(request, workspace_id, trace)
        if on_step:
            await on_step(trace.nodes[-1])

        # ── 2. Route intent (deterministic) ─────────────────────────────
        intent = self._route_intent(request.message, trace)
        if on_step:
            await on_step(trace.nodes[-1])

        # ── 3. Decide routing (LLM, merged with intent flags) ────────────
        decision = await self._decide(request, intent, trace)
        if on_step:
            await on_step(trace.nodes[-1])

        # ── 4. Execute capabilities ──────────────────────────────────────
        conv_id = (
            UUID(request.conversation_id)
            if request.conversation_id else None
        )
        requires_approval = (
            decision.need_confirmation
            or decision.risk_level != RiskLevel.low
        )
        cap_result = await self._executor.execute(
            message=request.message,
            workspace_id=workspace_id,
            decision=decision,
            intent=intent,
            trace=trace,
            requires_approval=requires_approval,
            conversation_id=conv_id,
        )
        if on_step:
            await on_step(trace.nodes[-1])

        # ── 5. Generate response ─────────────────────────────────────────
        response_text = await self._generate(
            request, ctx, cap_result, trace, on_token
        )
        if on_step:
            await on_step(trace.nodes[-1])

        # ── 6. Validate response ─────────────────────────────────────────
        response_text = await self._validate_response(
            response_text, cap_result, intent, trace
        )

        # ── 7. Learn ─────────────────────────────────────────────────────
        learning_actions = await self._maybe_learn(
            request, decision, response_text, ctx,
            cap_result.missions_created, workspace_id, trace,
        )
        if on_step:
            await on_step(trace.nodes[-1])

        orch_response = OrchestratorResponse(
            response=response_text,
            decision=decision,
            trace=trace.nodes,
            confidence=decision.confidence,
            risk=decision.risk_level,
            sources=[],
            capabilities_used=cap_result.capabilities_used,
            missions_created=cap_result.missions_created,
            learning_actions=learning_actions,
            thinking_steps=trace.thinking_steps(),
            memory_used=ctx.memory_count,
            knowledge_used=ctx.knowledge_count,
            internet_sources=cap_result.internet_sources,
            integrations_used=[],
            planner_used=decision.need_planner,
            mission_created=bool(cap_result.missions_created),
            estimated_cost=decision.estimated_cost,
            estimated_time=decision.estimated_latency,
            approval_required=decision.need_confirmation,
        )

        await self._persist_conversation(request, response_text)
        return orch_response

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

    def _route_intent(
        self, message: str, trace: ReasoningTrace
    ) -> IntentFlags:
        node = trace.begin("intent_route", "IntentRouter")
        intent = self._intent_router.analyze(message)
        trace.complete(node, intent.summary() or "none")
        return intent

    async def _decide(self, request, intent: IntentFlags, trace):
        node = trace.begin("decide", "DecisionEngine")
        _metrics_ctx = (
            self._metrics.time_planning()
            if self._metrics else contextlib.nullcontext()
        )
        with _metrics_ctx:
            decision = await self._decision.decide(request.message)

        # Merge: IntentRouter flags take priority (OR semantics)
        if intent.need_search:
            decision.need_search = True
        if intent.need_integrations:
            decision.need_integrations = True
        if intent.need_mission:
            decision.need_mission = True
            decision.need_planner = True
        if intent.need_memory:
            decision.need_memory = True

        label = decision.reason or f"risk={decision.risk_level.value}"
        if intent.detected:
            label = f"intent=[{intent.summary()}] {label}"
        trace.complete(node, label)
        return decision

    async def _generate(
        self,
        request,
        ctx,
        cap_result: CapabilityResult,
        trace,
        on_token: TokenCallback | None = None,
    ):
        node = trace.begin("generate", "LLMProvider")

        prompt_parts = [ctx.system_prompt]
        prompt_parts.extend(cap_result.to_prompt_sections())
        enriched_prompt = "\n\n".join(prompt_parts)

        messages = [
            ChatMessage(role="system", content=enriched_prompt),
            ChatMessage(role="user", content=request.message),
        ]
        try:
            if on_token is not None:
                chunks: list[str] = []
                async for chunk in self._llm.chat_stream(messages):
                    chunks.append(chunk)
                    await on_token(chunk)
                response_text = "".join(chunks)
            else:
                result = await self._llm.chat(messages)
                response_text = result.content

            trace.complete(node, f"{len(response_text)} chars")
            return response_text
        except Exception as exc:
            trace.fail(node, str(exc))
            raise

    async def _validate_response(
        self,
        response: str,
        cap_result: CapabilityResult,
        intent: IntentFlags,
        trace: ReasoningTrace,
    ) -> str:
        """Reject responses that falsely claim capability limitations.

        Checks: search denial when search ran, docker denial when docker
        data was provided, calendar/weather denials, and always-invalid
        general defensive phrases when any tool output exists.
        """
        invalid = False
        violated_cap = "unknown"

        # Search: invalid if internet WAS accessible (real results or no_results)
        search_accessible = (
            bool(cap_result.search_summary and cap_result.search_count > 0)
            or cap_result.search_error_type == "no_results"
        )
        if search_accessible:
            for pattern in _INVALID_SEARCH_PHRASES:
                if re.search(pattern, response, re.IGNORECASE):
                    invalid = True
                    violated_cap = "search"
                    break

        if (cap_result.docker_summary or (cap_result.generic_summary and "docker" in cap_result.generic_summary.lower())) and not invalid:
            for pattern in _INVALID_DOCKER_PHRASES:
                if re.search(pattern, response, re.IGNORECASE):
                    invalid = True
                    violated_cap = "docker"
                    break

        if (cap_result.calendar_summary or (cap_result.generic_summary and "calendar" in cap_result.generic_summary.lower())) and not invalid:
            for pattern in _INVALID_CALENDAR_PHRASES:
                if re.search(pattern, response, re.IGNORECASE):
                    invalid = True
                    violated_cap = "calendar"
                    break

        if (cap_result.weather_summary or (cap_result.generic_summary and "weather" in cap_result.generic_summary.lower())) and not invalid:
            for pattern in _INVALID_WEATHER_PHRASES:
                if re.search(pattern, response, re.IGNORECASE):
                    invalid = True
                    violated_cap = "weather"
                    break

        if cap_result.has_tool_output() and not invalid:
            for pattern in _INVALID_GENERAL_PHRASES:
                if re.search(pattern, response, re.IGNORECASE):
                    invalid = True
                    violated_cap = "general"
                    break

        if invalid:
            node = trace.begin("validate", "CapabilityValidator")
            _msg = f"denied {violated_cap} capability — corrected"
            trace.fail(node, _msg)
            logger.warning(
                "orchestrator.invalid_response_corrected",
                violated_cap=violated_cap,
            )
            sections = cap_result.to_prompt_sections()
            if sections:
                return (
                    "**[Resposta corrigida pelo Kernel]**\n\n"
                    + "\n\n".join(sections)
                )

        return response

    async def _persist_conversation(
        self, request: OrchestratorRequest, response_text: str
    ) -> None:
        if self._sessions is None or not request.conversation_id:
            return
        try:
            from models.conversation import (  # noqa: F401
                Conversation,
                Message,
                MessageRole,
            )

            conv_id = UUID(request.conversation_id)
            async with self._sessions() as session:
                conv = await session.get(Conversation, conv_id)
                if conv is None:
                    return
                session.add(Message(
                    conversation_id=conv_id,
                    role=MessageRole.user,
                    content=request.message,
                ))
                session.add(Message(
                    conversation_id=conv_id,
                    role=MessageRole.assistant,
                    content=response_text,
                ))
                await session.commit()
        except Exception as exc:
            logger.warning(
                "orchestrator.persist_failed", error=str(exc)
            )

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
