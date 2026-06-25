from abc import ABC, abstractmethod

from kernel.logger import get_logger

logger = get_logger(__name__)


class AgentWorker(ABC):
    name: str

    @abstractmethod
    async def handle(self, payload: dict) -> None: ...

    async def __call__(self, payload: dict) -> None:
        try:
            await self.handle(payload)
        except Exception as e:
            logger.error("agent.error", agent=self.name, error=str(e))
