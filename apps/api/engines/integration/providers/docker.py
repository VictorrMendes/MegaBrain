"""Docker integration provider.

Connects to the Docker Engine API via Unix socket or TCP.
No third-party SDK required — uses httpx directly.

Default config: {"socket": "/var/run/docker.sock"}
Alternative:    {"host": "http://docker:2375"}
"""
from __future__ import annotations

from datetime import datetime

import httpx

from engines.integration.base import (
    ConnectResult,
    IntegrationProvider,
    IntegrationRegistry,
    SyncResult,
)
from models.integration import (
    AccountStatus,
    ConnectedAccount,
    IntegrationCategory,
    IntegrationHealth,
    SyncMode,
)

_DEFAULT_SOCKET = "/var/run/docker.sock"
_TIMEOUT = 10.0


def _make_client(config: dict) -> httpx.AsyncClient:
    host = config.get("host")
    if host:
        return httpx.AsyncClient(base_url=host, timeout=_TIMEOUT)
    socket = config.get("socket", _DEFAULT_SOCKET)
    return httpx.AsyncClient(
        transport=httpx.AsyncHTTPTransport(uds=socket),
        base_url="http://docker",
        timeout=_TIMEOUT,
    )


@IntegrationRegistry.register
class DockerProvider(IntegrationProvider):
    slug = "docker"
    name = "Docker"
    description = "Monitora containers, logs e saúde da infra local"
    category = IntegrationCategory.infrastructure
    icon = "🐳"
    sync_strategy = SyncMode.scheduled
    capabilities = [
        "docker.list_containers",
        "docker.start_container",
        "docker.stop_container",
        "docker.restart_container",
        "docker.get_logs",
    ]
    supported_events = [
        "docker.container.started",
        "docker.container.stopped",
        "docker.container.failed",
    ]

    async def connect(self, config: dict) -> ConnectResult:
        try:
            async with _make_client(config) as client:
                resp = await client.get("/version")
                resp.raise_for_status()
                data = resp.json()
            return ConnectResult(
                account_name="Docker Engine",
                config={
                    "version": data.get("Version", "unknown"),
                    "api_version": data.get("ApiVersion", "unknown"),
                    "os": data.get("Os", "unknown"),
                    "arch": data.get("Arch", "unknown"),
                    **config,
                },
            )
        except Exception as exc:
            return ConnectResult(
                account_name="Docker Engine",
                error=str(exc),
            )

    async def sync(
        self,
        account: ConnectedAccount | None,
        since: datetime | None = None,
    ) -> SyncResult:
        config = account.config if account else {}
        try:
            async with _make_client(config) as client:
                resp = await client.get(
                    "/containers/json", params={"all": "true"}
                )
                resp.raise_for_status()
                containers = resp.json()
        except Exception as exc:
            return SyncResult(
                error_message=f"Docker API error: {exc}",
                life_context_lines=["Docker: ⚠️ sem conexão com o daemon"],
            )

        running = [
            c for c in containers if c.get("State") == "running"
        ]
        stopped = [
            c for c in containers
            if c.get("State") in ("exited", "dead", "created")
        ]
        unhealthy = [
            c for c in containers
            if c.get("Status", "").startswith("unhealthy")
        ]

        lines: list[str] = []
        total = len(containers)
        n_run = len(running)
        if total == 0:
            lines.append("Docker: nenhum container encontrado")
        else:
            lines.append(f"Docker: {n_run}/{total} containers rodando")
        if unhealthy:
            names = ", ".join(
                c.get("Names", ["?"])[0].lstrip("/")
                for c in unhealthy[:3]
            )
            lines.append(f"Docker: ⚠️ containers unhealthy: {names}")
        if stopped:
            names = ", ".join(
                c.get("Names", ["?"])[0].lstrip("/")
                for c in stopped[:3]
            )
            lines.append(f"Docker: containers parados: {names}")

        return SyncResult(
            items_synced=total,
            life_context_lines=lines,
            metadata={
                "containers": [
                    {
                        "id": c["Id"][:12],
                        "name": c.get("Names", ["?"])[0].lstrip("/"),
                        "image": c.get("Image", "?"),
                        "state": c.get("State", "?"),
                        "status": c.get("Status", "?"),
                    }
                    for c in containers
                ]
            },
        )

    async def health(
        self, account: ConnectedAccount | None
    ) -> IntegrationHealth:
        config = account.config if account else {}
        try:
            async with _make_client(config) as client:
                resp = await client.get("/ping")
                if resp.status_code == 200:
                    return IntegrationHealth.healthy
                return IntegrationHealth.degraded
        except Exception:
            return IntegrationHealth.unhealthy

    async def execute(
        self,
        capability: str,
        params: dict,
        account: ConnectedAccount | None,
    ) -> dict:
        config = account.config if account else {}
        container_id = params.get("container_id", "")

        action_map = {
            "docker.start_container":   ("post", f"/containers/{container_id}/start"),
            "docker.stop_container":    ("post", f"/containers/{container_id}/stop"),
            "docker.restart_container": ("post", f"/containers/{container_id}/restart"),
        }

        if capability == "docker.list_containers":
            async with _make_client(config) as client:
                resp = await client.get(
                    "/containers/json", params={"all": "true"}
                )
                resp.raise_for_status()
                return {"containers": resp.json()}

        if capability == "docker.get_logs":
            tail = params.get("tail", 50)
            async with _make_client(config) as client:
                resp = await client.get(
                    f"/containers/{container_id}/logs",
                    params={"stdout": "true", "stderr": "true",
                            "tail": str(tail)},
                )
                resp.raise_for_status()
                return {"logs": resp.text}

        if capability in action_map:
            method, path = action_map[capability]
            async with _make_client(config) as client:
                resp = getattr(client, method)(path)
                (await resp).raise_for_status()
                return {"ok": True, "container_id": container_id}

        raise NotImplementedError(f"Unknown capability: {capability}")
