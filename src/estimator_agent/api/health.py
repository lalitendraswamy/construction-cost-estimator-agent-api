"""Liveness (process is up) vs readiness (dependencies reachable): k8s / Render probes."""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from estimator_agent.api.deps import ContainerDep

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready(container: ContainerDep, response: Response) -> dict[str, str]:
    if await container.ready_check():
        return {"status": "ok"}
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "degraded", "mongodb": "unreachable"}
