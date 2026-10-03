"""LangSmith evaluation: route accuracy + reply-language match (PRD §11 success metrics).

Needs real keys (GOOGLE_API_KEY, LANGSMITH_API_KEY). Uses free-tier quota.
    python -m tests.evals.run_evals

TODO(learn): grow to the PRD's 15 *multi-turn* conversations, add evaluators for
"estimate only after spec complete" and "cost/sqft inside tier band".
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langsmith import Client, evaluate

from estimator_agent.agent.prompts.supervisor import SUPERVISOR_PROMPT
from estimator_agent.core.config import export_provider_env, get_settings
from estimator_agent.core.llm import LangChainModelRegistry, structured
from estimator_agent.domain import RouteDecision

DATASET = "estimator-routing-v1"
ROWS = [
    json.loads(line)
    for line in (Path(__file__).parent / "dataset.jsonl").read_text("utf-8").splitlines()
]


def ensure_dataset(client: Client) -> None:
    if client.has_dataset(dataset_name=DATASET):
        return
    ds = client.create_dataset(DATASET, description="Supervisor routing, labelled intents")
    client.create_examples(
        dataset_id=ds.id,
        inputs=[{"message": r["message"]} for r in ROWS],
        outputs=[
            {"intent": r["expected_intent"], "language": r["expected_language"]} for r in ROWS
        ],
    )


def main() -> None:
    settings = get_settings()
    export_provider_env(settings)
    model = LangChainModelRegistry(settings).chat("small")
    router = SUPERVISOR_PROMPT | structured(model, RouteDecision)

    def target(inputs: dict[str, Any]) -> dict[str, Any]:
        from langchain_core.messages import HumanMessage

        decision = router.invoke(
            {
                "messages": [HumanMessage(inputs["message"])],
                "last_agent": "none",
                "has_estimate": False,
                "spec": "{}",
            }
        )
        return {"intent": decision.intent.value}

    def route_accuracy(outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> bool:
        return bool(outputs["intent"] == reference_outputs["intent"])

    client = Client()
    ensure_dataset(client)
    evaluate(target, data=DATASET, evaluators=[route_accuracy], experiment_prefix="supervisor")


if __name__ == "__main__":
    main()
