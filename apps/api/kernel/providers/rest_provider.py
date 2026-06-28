import os
import httpx
from typing import Any
from kernel.logger import get_logger
from kernel.capabilities.models import CapabilityDefinition
from .execution_provider import ExecutionProvider

logger = get_logger(__name__)

class RestExecutionProvider(ExecutionProvider):
    """
    Executes a capability by calling an external REST API (like n8n, Make, etc).
    Expects N8N_API_URL and N8N_API_KEY for n8n specific logic (like workflow discovery).
    For a fully generic one, it would use Webhook URLs directly.
    Here we implement the n8n REST API execution as requested by the architecture.
    """
    
    def __init__(self):
        self.base_url = os.getenv("N8N_API_URL", "http://localhost:5678/api/v1")
        self.api_key = os.getenv("N8N_API_KEY", "")
        self.headers = {"X-N8N-API-KEY": self.api_key}
        self.workflow_cache: dict[str, str] = {} # tag -> workflow_id

    async def _resolve_workflow_id(self, tag: str) -> str | None:
        if tag in self.workflow_cache:
            return self.workflow_cache[tag]
            
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/workflows", headers=self.headers, params={"tags": tag})
                resp.raise_for_status()
                data = resp.json()
                if data and "data" in data and len(data["data"]) > 0:
                    workflow_id = data["data"][0]["id"]
                    self.workflow_cache[tag] = workflow_id
                    return workflow_id
        except Exception as e:
            logger.error("rest_provider.resolve_failed", tag=tag, error=str(e))
        return None

    async def execute(self, definition: CapabilityDefinition, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        logger.info("rest_provider.executing", capability=definition.capability)
        
        tag = definition.workflow_tag
        if not tag:
            raise ValueError(f"Capability {definition.capability} missing workflow_tag for REST provider.")
            
        workflow_id = await self._resolve_workflow_id(tag)
        if not workflow_id:
            raise ValueError(f"Could not resolve workflow_id for tag: {tag}")
            
        execution_id = context.get("execution_id", "unknown")
        
        try:
            async with httpx.AsyncClient(timeout=definition.timeout) as client:
                # Dispara a execução na API do n8n
                # O payload do webhook do n8n pode precisar de wrap no objeto correto.
                body = {"data": payload, "execution_id": execution_id}
                
                resp = await client.post(
                    f"{self.base_url}/workflows/{workflow_id}/execute", 
                    headers=self.headers, 
                    json=body
                )
                resp.raise_for_status()
                result = resp.json()
                
                return {
                    "status": "success",
                    "provider_execution_id": result.get("executionId"),
                    "details": "Execution triggered successfully."
                }
        except Exception as e:
            logger.error("rest_provider.execution_failed", error=str(e))
            return {"status": "failed", "error": str(e)}

rest_provider = RestExecutionProvider()
