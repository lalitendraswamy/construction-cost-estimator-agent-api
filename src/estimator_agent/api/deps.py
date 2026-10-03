"""FastAPI dependencies. Endpoints ask for what they need; the container provides it."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from estimator_agent.agent.runner import ChatRunner
from estimator_agent.api.container import Container
from estimator_agent.core.security import verify_admin_key
from estimator_agent.db.repositories import ApprovalRepository, RateRepository


def get_container(request: Request) -> Container:
    return request.app.state.container  # type: ignore[no-any-return]


ContainerDep = Annotated[Container, Depends(get_container)]


async def require_admin(
    container: ContainerDep, x_admin_key: Annotated[str | None, Header()] = None
) -> None:
    expected = container.settings.admin_api_key.get_secret_value()
    if not verify_admin_key(x_admin_key, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin key")


def get_runner(container: ContainerDep) -> ChatRunner:
    return container.runner


def get_rates(container: ContainerDep) -> RateRepository:
    return container.context.rates


def get_approvals(container: ContainerDep) -> ApprovalRepository:
    return container.context.approvals


RunnerDep = Annotated[ChatRunner, Depends(get_runner)]
RatesDep = Annotated[RateRepository, Depends(get_rates)]
ApprovalsDep = Annotated[ApprovalRepository, Depends(get_approvals)]
