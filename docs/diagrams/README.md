# Architecture Diagrams

## Files

| Diagram | Shows |
|---|---|
| `current-architecture.excalidraw` | The full query + ingestion path as implemented today |
| `rag-query-flow.excalidraw` | Step-by-step `POST /query` request lifecycle, including the evidence-sufficiency branch |
| `ingestion-flow.excalidraw` | Step-by-step `ingest_file()` lifecycle, including all guardrail checks |
| `roadmap.excalidraw` | v0.1 (current) vs. v0.2–v0.7 (future, not implemented) |
| `observability-baseline.excalidraw` | Current structured-logging baseline vs. a future OpenTelemetry platform |

## Conventions

- **Solid, colored boxes** = implemented in this codebase today, verifiable by reading the module
  named on the box.
- **Dashed, grey boxes** = future/roadmap only. If it's dashed, it does not exist in the code —
  drawing it any other way would misrepresent the project's actual state.
- Each diagram ends with a caption answering "what does this diagram prove?" — a diagram that
  can't answer that question for itself isn't earning its place in the docs.

## Source vs. rendered

`.excalidraw` files are the source of truth (hand-authored JSON scene files, editable in
Excalidraw / the VS Code Excalidraw extension). `.svg` renders are generated from them — **not
included in this change**, because no automated Excalidraw-to-SVG export path is available in the
sandboxed environment this change was produced in (checked: no Excalidraw CLI, no headless
renderer, no `inkscape`/`rsvg-convert`). Also **not independently visually verified** — the JSON
was validated for schema/syntax correctness (round-tripped through a JSON parser) but not
confirmed to render correctly by actually opening it in Excalidraw.

**To produce the `.svg` files** (manual, one-time per diagram, needed before docs links below will
resolve to an image instead of just the source):

1. Open the `.excalidraw` file in VS Code (with the Excalidraw extension) or at excalidraw.com.
2. Confirm it renders as expected — if any element looks wrong, this is the point to fix it; it
   was authored by hand and not visually verified before commit.
3. File → Export → SVG (or the extension's export button) → save as the matching `.svg` filename
   in this directory.

## Diagram drift control

These diagrams describe the codebase **as of this change**. If retrieval, ingestion, or the
observability approach changes materially, update the relevant `.excalidraw` source (and
re-export the `.svg`) in the same change that alters the code — a diagram that silently goes stale
is worse than no diagram, because it actively misinforms.
