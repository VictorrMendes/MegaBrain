import asyncio
from kernel.orchestrator.decision import DecisionEngine
from kernel.providers.base import LLMProvider, ChatMessage, ExecutionProfile

class DummyLLM(LLMProvider):
    async def chat(self, messages, profile=None):
        print("Prompt sent to LLM:")
        for m in messages:
            print(f"[{m.role.upper()}]: {m.content}\n")
        return type("Obj", (), {"content": '{"target_capability": "calendar.list_events", "target_provider": "google", "capability_params": {"time_min": "amanhã", "time_max": "depois de amanhã"}}'})()

async def test():
    engine = DecisionEngine(DummyLLM())
    decision = await engine.decide("Quais reuniões eu tenho amanhã?")
    print("Decisão extraída:")
    print(decision)

asyncio.run(test())
