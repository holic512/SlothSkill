---
name: plantuml-professional-diagrams
description: Author and render professional PlantUML diagrams for reports, architecture docs, technical specs, and Markdown workflows. Use this when Codex needs to choose an appropriate PlantUML diagram type, write high-quality sequence/component/activity/deployment diagrams, render `.puml` or Markdown `plantuml` blocks to SVG or PNG, or rewrite Markdown to reference rendered images.
---

# PlantUML Professional Diagrams

Own both diagram quality and rendering. Prefer diagrams that explain behavior, boundaries, and decisions with the fewest possible elements.

## Start Here

1. Read [references/diagram-rules.md](references/diagram-rules.md) before authoring.
2. If you need rendering commands, formats, or rewrite rules, read [references/rendering-workflow.md](references/rendering-workflow.md).
3. If you need a starting template, inspect [references/examples.md](references/examples.md) and copy from `assets/examples/`.

## Working Rules

- Choose the diagram family before writing PlantUML. Do not default to sequence diagrams when a component, deployment, or activity view would explain the system faster.
- Prefer SVG for web, Markdown, design review, zooming, and long-term editing.
- Use PNG when the destination tooling does not reliably display SVG, or when a raster image is explicitly requested.
- Keep labels short and domain-specific. Replace vague labels such as `Service A`, `Module B`, or `Process`.
- Model only the interactions or structures the reader needs. Omit incidental calls, getters, logging chatter, and framework noise.
- Use restrained styling. Prefer the CSS-style `style` block or `!theme` for modern diagrams. Keep `skinparam` as a compatibility fallback, not the primary styling approach.
- Validate syntax before claiming a diagram is finished.

## Diagram Selection

Use these defaults:

- Use a sequence diagram for message order, retries, callbacks, orchestration, and cross-service call flow.
- Use an activity diagram for branching business logic, approval flow, compensation flow, or stateful processing steps.
- Use a component diagram for service boundaries, interfaces, ownership, and integration surfaces.
- Use a deployment diagram for runtime topology, nodes, environments, gateways, and network boundaries.
- Use a class diagram only when data model or API structure is the real point of the document.

When unclear, draft the simplest candidate and check whether the reader's main question is about order, logic, structure, or topology.

## Authoring Standard

Build diagrams with this quality bar:

- Add a title when the scenario is specific and the deliverable benefits from it.
- Keep participant and node names stable across related diagrams.
- Use `alt`, `opt`, `loop`, `par`, `group`, and notes only when they reflect real behavior.
- Split overloaded diagrams into two smaller diagrams when the narrative has more than one main story.
- Avoid decorative colors. If the user wants a polished default, use a built-in theme or a restrained style block.
- Prefer explicit actor or boundary names such as `Client App`, `API Gateway`, `Order Service`, `Payment Worker`, `PostgreSQL`.

## Rendering Workflow

For Markdown files with fenced `plantuml` blocks:

1. Run [scripts/render_plantuml.py](scripts/render_plantuml.py) with the Markdown file, output directory, and bundled JAR.
2. Prefer `--formats svg,png` when the final destination is unknown.
3. If the deliverable needs image links instead of code blocks, run [scripts/rewrite_markdown_with_images.py](scripts/rewrite_markdown_with_images.py) with the JSON mapping from the render step.

For standalone `.puml` files:

1. Render directly with `scripts/render_plantuml.py`.
2. Keep the `.puml` source next to the deliverable whenever future edits are likely.

Default outputs:

- `images/plantuml-001-<slug>.svg`
- `images/plantuml-001-<slug>.png`
- `render-map.json`

## Python Scripts

Keep the Python scripts. They are justified because they provide deterministic block extraction, output naming, mapping JSON, and Markdown rewrite behavior that would otherwise be reimplemented ad hoc in many tasks.

Do not remove them unless the surrounding workflow no longer needs Markdown block extraction or post-processing.

## Failure Handling

- Stop immediately if `java` is unavailable.
- Stop immediately if Graphviz `dot` is unavailable.
- Stop immediately if the bundled PlantUML JAR is missing.
- If rendering fails, return the exact PlantUML or Graphviz error.
- If SVG renders but the consumer cannot display it, rerender PNG instead of rewriting the diagram.
- If the diagram is technically valid but visually overloaded, revise the source rather than compensating with more styling.

## Coordination

When another skill produces report Markdown:

- keep or insert valid `plantuml` blocks in the source Markdown
- render the blocks with this skill
- rewrite Markdown only when the final artifact should reference images rather than source blocks

This skill should not rewrite report prose unless the change is required to keep captions or diagram placement coherent.
