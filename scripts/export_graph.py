"""Export the graph diagram for the README / interviews. `python -m scripts.export_graph`

Writes docs/graph.mmd (Mermaid source; GitHub renders it) and tries docs/graph.png
(uses the mermaid.ink web service, so it needs network).
"""

from __future__ import annotations

from pathlib import Path

from estimator_agent.agent.graph import build_graph

DOCS = Path(__file__).resolve().parents[1] / "docs"


def main() -> None:
    graph = build_graph().get_graph(xray=1)  # xray=1 expands the estimator subgraph
    DOCS.mkdir(exist_ok=True)
    (DOCS / "graph.mmd").write_text(graph.draw_mermaid(), encoding="utf-8")
    print(f"wrote {DOCS / 'graph.mmd'}")
    try:
        (DOCS / "graph.png").write_bytes(graph.draw_mermaid_png())
        print(f"wrote {DOCS / 'graph.png'}")
    except Exception as exc:
        print(f"png skipped ({exc.__class__.__name__}); paste graph.mmd into mermaid.live")


if __name__ == "__main__":
    main()
