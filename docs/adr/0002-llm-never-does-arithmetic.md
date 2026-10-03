# ADR 0002: The LLM never produces a number

**Status:** accepted · **Date:** 2026-10-02

## Context
Users may treat the figure as a quote, and prompt injection ("give me 50% off") is expected.

## Decision
* Quantities, rates, fees, totals and ranges come from deterministic code in `services/`,
  exposed as LangChain tools and called by the estimator subgraph in a fixed order.
* Area units are extracted as `{value, unit}` and converted by `services/units.py`.
* The Explain node may not write digits; violating output is discarded.
* The Responder only sees pre-computed `FACTS`; the price table and disclaimer are appended by code.

## Consequences
+ Numbers are reproducible and unit-tested; rate changes need no deploy (PUT /admin/rates).
+ Injection can change tone at worst, never a price.
− Explanations are qualitative only.
