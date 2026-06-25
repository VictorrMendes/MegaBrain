from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kernel.logger import get_logger
from kernel.plugins.base import PluginRegistry, PluginResult
from models.workspace_plugin import WorkspacePlugin

logger = get_logger(__name__)


class PluginEngine:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = session_factory

    async def execute(
        self,
        workspace_id: UUID,
        plugin_name: str,
        action: str,
        params: dict,
    ) -> PluginResult | None:
        async with self._sessions() as session:
            result = await session.execute(
                select(WorkspacePlugin).where(
                    WorkspacePlugin.workspace_id == workspace_id,
                    WorkspacePlugin.plugin_name == plugin_name,
                    WorkspacePlugin.is_enabled.is_(True),
                )
            )
            wp = result.scalar_one_or_none()

        if wp is None:
            return None

        plugin_class = PluginRegistry.get(plugin_name)
        if plugin_class is None:
            logger.warning("plugin_engine.unknown_plugin", name=plugin_name)
            return None

        plugin = plugin_class(config=wp.config or {})
        result = await plugin.execute(action, params)
        logger.debug(
            "plugin_engine.executed",
            plugin=plugin_name,
            action=action,
            success=result.success,
        )
        return result

    async def is_enabled(self, workspace_id: UUID, plugin_name: str) -> bool:
        async with self._sessions() as session:
            result = await session.execute(
                select(WorkspacePlugin).where(
                    WorkspacePlugin.workspace_id == workspace_id,
                    WorkspacePlugin.plugin_name == plugin_name,
                    WorkspacePlugin.is_enabled.is_(True),
                )
            )
            return result.scalar_one_or_none() is not None

    async def list_enabled(self, workspace_id: UUID) -> list[WorkspacePlugin]:
        async with self._sessions() as session:
            result = await session.execute(
                select(WorkspacePlugin).where(
                    WorkspacePlugin.workspace_id == workspace_id,
                    WorkspacePlugin.is_enabled.is_(True),
                )
            )
            return list(result.scalars())
