from dataclasses import dataclass, field
from enum import Enum


class Permission(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"
    ADMIN = "admin"


@dataclass
class PermissionContext:
    user_id: str
    workspace_id: str
    permissions: list[Permission] = field(default_factory=list)


class PermissionEngine:
    def check(self, ctx: PermissionContext, required: Permission) -> bool:
        if Permission.ADMIN in ctx.permissions:
            return True
        return required in ctx.permissions

    def require(self, ctx: PermissionContext, required: Permission) -> None:
        if not self.check(ctx, required):
            raise PermissionError(
                f"User '{ctx.user_id}' lacks permission '{required}' "
                f"in workspace '{ctx.workspace_id}'"
            )


permission_engine = PermissionEngine()
