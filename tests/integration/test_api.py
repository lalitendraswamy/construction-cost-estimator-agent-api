"""HTTP contract tests: real FastAPI app + real graph, fake LLM and in-memory repos."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from estimator_agent.main import create_app
from tests.fakes import ScriptedChatModel, fake_container_factory, make_context, settings_for_tests

pytestmark = pytest.mark.integration
ADMIN = {"X-Admin-Key": "test-admin-key"}


@pytest.fixture
def model() -> ScriptedChatModel:
    return ScriptedChatModel()


@pytest.fixture
def client(model: ScriptedChatModel) -> Iterator[TestClient]:
    settings = settings_for_tests()
    app = create_app(
        settings, container_factory=fake_container_factory(make_context(model, settings))
    )
    with TestClient(app) as c:
        yield c


def test_health(client: TestClient) -> None:
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").status_code == 200
    assert "x-request-id" in client.get("/health/live").headers


def test_chat_json_mode_returns_interrupt(client: TestClient, model: ScriptedChatModel) -> None:
    model.structured_outputs = {
        "LanguageGuess": [{"language": "en", "confident": True}],
        "RouteDecision": [{"intent": "estimate", "reason": "t"}],
        "SpecExtraction": [{"project_type": "new_house"}],
    }
    r = client.post(
        "/api/v1/chat?stream=false",
        json={"thread_id": "api-thread-1", "message": "I want to build a house"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["event"] == "interrupt"
    assert body["data"]["type"] == "ask_user"

    state = client.get("/api/v1/threads/api-thread-1").json()
    assert state["pending"]["type"] == "ask_user"


def test_chat_sse_stream(client: TestClient, model: ScriptedChatModel) -> None:
    model.structured_outputs = {"RouteDecision": [{"intent": "chit_chat", "reason": "t"}]}
    model.responses = ["Namaste! I can estimate your construction cost."]
    with client.stream(
        "POST", "/api/v1/chat", json={"thread_id": "api-thread-2", "message": "hi"}
    ) as r:
        text = "".join(r.iter_text())
    assert "event: progress" in text
    assert "event: token" in text
    assert "event: final" in text


def test_resume_without_pending_interrupt_is_409(client: TestClient) -> None:
    r = client.post("/api/v1/chat/resume", json={"thread_id": "nothing-here", "value": "yes"})
    assert r.status_code == 409
    assert r.headers["content-type"].startswith("application/problem+json")


def test_admin_requires_key(client: TestClient) -> None:
    assert client.get("/api/v1/admin/pending").status_code == 401
    assert client.get("/api/v1/admin/pending", headers=ADMIN).json() == []


def test_admin_rate_card_validation(client: TestClient) -> None:
    bad = {
        "city": "vizag",
        "tier": "basic",
        "base_rate_per_sqft": 2000,
        "band_min_per_sqft": 1500,
        "band_max_per_sqft": 2500,
        "shares": {"labour": 0.5},
    }  # shares don't sum to 1
    assert client.put("/api/v1/admin/rates", json=bad, headers=ADMIN).status_code == 422
