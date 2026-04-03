---
name: plantuml-professional-diagrams
description: Create professional PlantUML diagrams and render them into images for reports or technical documents. Use this when a report needs sequence diagrams, call-flow diagrams, interaction diagrams, or Markdown plantuml blocks must be converted into rendered images and Markdown image references.
metadata:
  short-description: Author and render professional PlantUML diagrams
---

# PlantUML Professional Diagrams

Use this skill when the deliverable requires a professional PlantUML diagram, especially sequence diagrams and related interaction diagrams. This skill owns both diagram quality and image rendering.

## Scope

Use this skill for:

- sequence diagrams
- call-flow diagrams
- interaction-focused activity diagrams
- PlantUML rendering from Markdown `plantuml` blocks
- replacing Markdown `plantuml` blocks with image references

Do not use this skill for DOCX export or general report writing.

## Inputs And Outputs

Accepted inputs:

- Markdown files containing `plantuml` blocks
- a diagram specification derived from report content
- a request to produce professional UML images for a report

Outputs:

- rendered PNG files
- optional mapping JSON describing the rendered blocks
- Markdown with image references instead of `plantuml` blocks when requested

## Diagram Authoring Rules

Before writing PlantUML, read [references/diagram-rules.md](references/diagram-rules.md).

Default expectations:

- prefer sequence diagrams when the reader needs message order, service interaction, or call flow
- use clear participant names
- keep message direction and activation bars accurate
- group alternate or conditional flows clearly
- add short notes only when they materially improve clarity
- keep the style clean, professional, and readable

Use a monochrome or restrained style unless the user requests otherwise.

## Rendering Workflow

1. Confirm that `java` is available.
2. Confirm that Graphviz `dot` is available.
3. Confirm that the bundled PlantUML JAR exists.
4. Render each Markdown `plantuml` block with [scripts/render_plantuml.py](scripts/render_plantuml.py).
5. If the user needs final Markdown with images, replace the blocks with [scripts/rewrite_markdown_with_images.py](scripts/rewrite_markdown_with_images.py).

Default image names:

- `images/plantuml-001.png`
- `images/plantuml-002.png`

## Failure Rules

- If `java` is missing, stop and tell the user to install Java.
- If Graphviz `dot` is missing, stop and tell the user to install Graphviz.
- If the PlantUML JAR is missing, stop and report the missing asset.
- If any diagram fails to render, stop and return the exact rendering error.

## Coordination With Other Skills

When `experiment-report-md` produces `report.source.md` and the report needs professional interaction diagrams:

- keep or insert valid `plantuml` blocks in the source Markdown
- run the rendering pipeline from this skill
- write image references back into the final Markdown when requested

This skill should not rewrite report prose unless the change is required to keep captions or diagram placement coherent.
