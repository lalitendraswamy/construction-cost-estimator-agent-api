# ADR 0001: Supervisor routing over a free-form swarm

**Status:** accepted · **Date:** 2026-10-02

## Context
Four specialist agents (intake, estimator, knowledge, contact). Routing must be predictable,
testable and cheap, and one business rule ("never estimate on guesses") must hold 100%.

## Decision
A single supervisor node classifies intent with structured output (`RouteDecision`); a **pure
function** (`agent/routing.py::route_for_intent`) maps intent → next node. Agents never hand off
to each other freely; every turn ends at the Responder. Only Knowledge and Contact are ReAct
agents, because only they need to choose tools.

## Consequences
+ Routing is unit-tested without an LLM; route accuracy is measured in LangSmith.
+ The completeness rule lives in code (Intake → Estimator only when `missing_fields()` is empty).
− Adding an agent means editing the routing table (intentional).
− A mid-interview off-topic answer goes back to Intake, not the Knowledge agent (exercise in LEARNING.md).
