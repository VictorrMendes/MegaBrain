import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.database import AsyncSessionLocal
from kernel.events import event_bus
from models.workspace import Workspace
from engines.integration.engine import IntegrationManager
from sqlalchemy import select

from kernel.events.bus import EventBus
async def fake_publish(self, *args, **kwargs):
    pass
EventBus.publish_event = fake_publish
EventBus.publish_infra_event = fake_publish
EventBus.publish = fake_publish

async def main():
    try:
        async with AsyncSessionLocal() as session:
        # Find active workspace
        result = await session.execute(select(Workspace).where(Workspace.is_active == True))
        workspace = result.scalar_one_or_none()
        if not workspace:
            print("Nenhum workspace ativo encontrado.")
            return

        print(f"Encontrado workspace ativo: {workspace.name} ({workspace.id})")
        
        manager = IntegrationManager(lambda: AsyncSessionLocal())
        
        print("Conectando integração 'docker'...")
        try:
            integration = await manager.connect(
                workspace_id=workspace.id,
                slug="docker",
                config={"socket": "/var/run/docker.sock"},
                account_name_override="Servidor Local"
            )
            print(f"Sucesso! Integração ID: {integration.id}")
            
            print("Executando sync inicial...")
            await manager.sync(integration.id)
            print("Integração Docker habilitada e sincronizada com sucesso!")
        except Exception as e:
            print(f"Erro ao conectar integração: {e}")

if __name__ == "__main__":
    asyncio.run(main())
