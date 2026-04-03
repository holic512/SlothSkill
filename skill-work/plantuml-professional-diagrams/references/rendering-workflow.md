# Rendering Workflow

Use this reference when you need exact commands, output choices, or failure diagnosis.

## Environment Checks

Confirm all three prerequisites before rendering:

- `java -version`
- `dot -V`
- bundled JAR exists at the skill root

## Output Strategy

Choose output format based on destination:

- `svg`: default for Markdown, websites, architecture docs, and design review
- `png`: fallback for DOCX pipelines, tools with poor SVG support, or explicit raster output
- `svg,png`: safest default when the final destination is not yet fixed

## Render Markdown Blocks

```bash
python3 scripts/render_plantuml.py report.source.md images \
  --jar plantuml-1.2026.2.jar \
  --formats svg,png \
  --json-out render-map.json
```

## Render A Standalone `.puml`

```bash
python3 scripts/render_plantuml.py assets/examples/sequence-service-retry.puml images \
  --jar plantuml-1.2026.2.jar \
  --formats svg
```

## Rewrite Markdown

```bash
python3 scripts/rewrite_markdown_with_images.py \
  report.source.md \
  render-map.json \
  report.md
```

The rewrite step uses the preferred format recorded in the JSON mapping. When both SVG and PNG exist, it prefers SVG unless told otherwise during rendering.

## Professional Defaults

Prefer these rendering choices:

- render SVG first
- disable metadata for generated images
- keep filenames deterministic and readable
- keep a JSON mapping whenever Markdown blocks are involved

## Practical Notes From PlantUML

- Modern PlantUML styling should favor `style` or `!theme`; `skinparam` remains a compatibility tool.
- PlantUML supports direct SVG output from the CLI and SVG is the best default for scalable documents.
- PlantUML CLI supports syntax checking, output directories, explicit formats, metadata disabling, and Graphviz path selection. Those should be surfaced through helper scripts instead of requiring ad hoc shell commands each time.

## Failure Diagnosis

If rendering fails:

- syntax error: inspect the specific block or `.puml` source first
- missing output file: inspect the PlantUML stderr/stdout captured by the script
- Graphviz issues: confirm `dot` is on PATH or pass the detected path through the helper script
- visual clutter: reduce participants, notes, and message count before changing colors
