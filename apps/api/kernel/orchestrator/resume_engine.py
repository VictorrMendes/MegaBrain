from typing import Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json

from models.execution import Interaction, InteractionType, Execution, ExecutionStep, StepStatus, ExecutionStatus
from kernel.logger import get_logger
from kernel.orchestrator.parameter_resolver import parameter_resolver
from kernel.execution.execution_runtime import execution_runtime

logger = get_logger(__name__)

class ResumeEngine:
    """
    Responsible for intercepting incoming messages and matching them
    against suspended Interactions (WAITING_INPUT).
    If matched, it injects the answer into the payload and resumes execution.
    """
    
    def __init__(self, session_factory):
        self._sessions = session_factory

    async def try_resume(
        self, 
        message: str, 
        workspace_id: str, 
        conversation_id: Optional[str] = None,
        interaction_token: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Attempts to match the message to a suspended Interaction.
        Returns (True, response_message) if resumed, (False, None) if no interaction was found.
        """
        if not self._sessions:
            return False, None

        async with self._sessions() as session:
            # 1. Matching Logic
            interaction = await self._find_interaction(session, workspace_id, conversation_id, interaction_token)
            
            if not interaction:
                return False, None
                
            logger.info("resume_engine.interaction_matched", interaction_id=str(interaction.id))
            
            # 2. Inject Answer
            # For Sprint 4, we simply take the raw message and attempt to put it into the payload.
            # In a more advanced implementation (Phase 21), we might use a small LLM call to extract
            # the specific parameter value from the natural language response.
            # For now, we inject the raw message into all missing parameters (as a string).
            
            step = await session.get(ExecutionStep, interaction.step_id)
            if not step:
                logger.error("resume_engine.step_not_found", step_id=str(interaction.step_id))
                return False, None
                
            payload = step.payload or {}
            
            # Simple Injection (assuming the user answered the missing parameters)
            # This is a naive approach. Ideally, we would map the user's string to the JSON schema.
            # But the ParameterResolver will catch it if it's still invalid.
            missing_params = interaction.missing_parameters or []
            for param in missing_params:
                param_name = param.get("name")
                if param_name:
                    # In a real scenario, use LLM to extract the value from 'message' based on 'param.type'
                    # For now, we just inject the raw text if it's a string, or attempt to parse it.
                    payload[param_name] = message 
                    
            step.payload = payload
            
            # 3. Parameter Resolver re-check
            still_missing = parameter_resolver.resolve(step.capability, step.payload)
            
            if still_missing:
                # Still missing, update the interaction
                interaction.missing_parameters = [p.to_dict() for p in still_missing]
                interaction.retry_count += 1
                await session.commit()
                # We would need to generate a new question here ideally, but for now we return False
                # to let the system know it didn't fully resolve. Or we return True and ask again.
                # Let's return True, and say we are still missing it.
                return True, "I still need more information."
            
            # 4. Resolved! Continue Runtime
            interaction.status = "COMPLETED"
            step.status = StepStatus.READY.value # Or RUNNING
            
            # We must persist this before running
            await session.commit()
            
            # Resume the step
            logger.info("resume_engine.resuming_step", step_id=str(step.id))
            await execution_runtime.execute_node(step, workspace_id)
            
            # After execution, the orchestrator usually builds the response.
            # Since we bypassed the orchestrator loop, we return a simple success.
            # In Sprint 5, the Orchestrator will handle the response aggregation.
            return True, "Resumed execution successfully."

    async def _find_interaction(
        self, 
        session: AsyncSession, 
        workspace_id: str, 
        conversation_id: Optional[str],
        interaction_token: Optional[str]
    ) -> Optional[Interaction]:
        
        # Priority 1: interaction_token
        if interaction_token:
            stmt = select(Interaction).where(
                Interaction.interaction_token == UUID(interaction_token),
                Interaction.status == "PENDING"
            )
            result = await session.execute(stmt)
            interaction = result.scalar_one_or_none()
            if interaction:
                return interaction

        # Priority 2: conversation_id (most recent)
        if conversation_id:
            stmt = select(Interaction).where(
                Interaction.conversation_id == UUID(conversation_id),
                Interaction.status == "PENDING"
            ).order_by(Interaction.asked_at.desc()).limit(1)
            result = await session.execute(stmt)
            interaction = result.scalar_one_or_none()
            if interaction:
                return interaction
                
        # Priority 3: workspace_id (most recent)
        stmt = select(Interaction).where(
            Interaction.workspace_id == UUID(workspace_id),
            Interaction.status == "PENDING"
        ).order_by(Interaction.asked_at.desc()).limit(1)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
