from typing import List, Dict, Any
from kernel.logger import get_logger
from kernel.providers.base import LLMProvider, ChatMessage
from kernel.orchestrator.parameter_resolver import MissingParameter

logger = get_logger(__name__)

class ClarificationEngine:
    """
    Formulates a natural language question to ask the user for missing parameters.
    Highly optimized to reduce token usage and prevent hallucination by only passing
    the exact context needed (no full WorldState or Execution Graph).
    """
    
    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider

    async def generate_question(
        self, 
        capability_name: str, 
        capability_description: str, 
        missing_parameters: List[MissingParameter]
    ) -> str:
        """
        Takes a capability and missing parameters and returns a natural language question.
        """
        logger.info("clarification_engine.generating_question", capability=capability_name)
        
        system_prompt = (
            "You are an internal system component responsible for asking the user for missing information.\n"
            "You will be given the description of an action the user wants to perform, and a list of missing parameters.\n"
            "Your ONLY job is to formulate a single, direct, and natural question asking the user for this missing information.\n"
            "Do NOT explain what you are doing. Do NOT add pleasantries. Do NOT hallucinate defaults.\n"
            "You MUST ALWAYS formulate the question in Brazilian Portuguese.\n"
            "Respond ONLY with the question in Portuguese."
        )
        
        missing_details = "\n".join([
            f"- Parameter: {p.name}\n  Description: {p.description}\n  Type: {p.type}" 
            for p in missing_parameters
        ])
        
        user_message = (
            f"Action: {capability_name}\n"
            f"Action Description: {capability_description}\n\n"
            f"Missing Information:\n{missing_details}"
        )
        
        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_message),
        ]
        
        try:
            result = await self.llm.chat(messages)
            question = result.content.strip()
            logger.debug("clarification_engine.question_generated", question=question)
            return question
        except Exception as exc:
            logger.error("clarification_engine.error", error=str(exc))
            # Fallback question if LLM fails
            params = ", ".join([p.name for p in missing_parameters])
            return f"I need more information to proceed with {capability_name}. Please provide: {params}."

# This should ideally be instantiated dynamically with the LLMProvider from the Orchestrator.
