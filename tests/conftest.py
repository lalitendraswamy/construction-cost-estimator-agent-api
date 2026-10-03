from __future__ import annotations

import os

import pytest

# Never let tests reach real services, whatever is in the developer's .env.
os.environ["LANGSMITH_TRACING"] = "false"
os.environ.setdefault("GOOGLE_API_KEY", "test-not-used")

from tests.fakes import ScriptedChatModel, make_context, make_runner


@pytest.fixture
def model() -> ScriptedChatModel:
    return ScriptedChatModel()


@pytest.fixture
def context(model: ScriptedChatModel):  # type: ignore[no-untyped-def]
    return make_context(model)


@pytest.fixture
def runner(context):  # type: ignore[no-untyped-def]
    return make_runner(context)
