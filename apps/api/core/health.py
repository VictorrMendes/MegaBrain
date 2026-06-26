from fastapi import APIRouter

from kernel.runtime import runtime

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    report = await runtime.health_report()
    return report.to_dict()
