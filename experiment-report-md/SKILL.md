---
name: experiment-report-md
description: Generate English Markdown experiment reports from the current codebase by analyzing repository evidence, inferring the coursework topic, and writing only experiment-style report content. Use this for Java or Python lab reports, coursework experiment reports, or project experiment reports that should stop at report.source.md and call plantuml-professional-diagrams when professional sequence or interaction diagrams are needed.
metadata:
  short-description: Generate experiment report Markdown from code evidence
---

# Experiment Report Markdown

Use this skill when the user wants an experiment-style report derived from the current repository. This skill produces the report draft in Markdown only. It does not export DOCX and it does not render diagrams into images.

## Scope

Use this skill for:

- Java experiment reports
- Python experiment reports
- coursework or lab reports backed by an implementation repository
- project experiment reports where the report must be grounded in code and repo evidence

Do not use this skill for:

- database design reports as a standalone deliverable
- Linux operations reports
- project management reports
- generic report orchestration across unrelated report types
- DOCX export

## Output Contract

- Primary artifact: `docx/<report-name>/report.source.md`
- Language: English
- The Markdown may contain `plantuml` blocks when a diagram is necessary
- If a professional sequence diagram, call-flow diagram, or similar interaction diagram is needed, use `plantuml-professional-diagrams` after drafting the Markdown

## Workflow

### 1. Build the report intent

Extract or infer:

- report topic
- report name
- experiment type
- minimum word count if the user gave one

When the topic is not explicit, infer it from:

- the user request
- the current directory name
- README files
- assignment files or requirement documents
- existing report titles or prompt titles

### 2. Inspect the repository

Read [references/inspection-checklist.md](references/inspection-checklist.md) before scanning the project.

Separate evidence into two buckets:

- topic-driven material: background, objectives, user needs, experiment purpose
- code-driven material: architecture, modules, data design, implementation details, testing evidence

Do not let the requirements section collapse into a code walkthrough.

### 3. Choose an experiment template

Use only experiment templates:

- [references/templates/java_experiment.md](references/templates/java_experiment.md)
- [references/templates/python_experiment.md](references/templates/python_experiment.md)
- [references/templates/generic_experiment.md](references/templates/generic_experiment.md)

Pick the most specific template supported by repository evidence. Fall back to the generic experiment template when language or structure is mixed.

### 4. Write `report.source.md`

Read [references/output-rules.md](references/output-rules.md) before drafting.

Requirements:

- write natural English with no AI/meta phrasing
- keep heading depth aligned with chapter depth
- use topic-driven sections for background and requirements
- use code-driven sections for design, implementation, and testing
- keep unsupported claims out of the report
- if screenshots do not exist, use explicit placeholder captions instead of inventing evidence

### 5. Hand off diagrams when needed

If the report needs a professional sequence diagram, call-flow diagram, activity-style interaction diagram, or other PlantUML deliverable:

- leave a valid `plantuml` block in `report.source.md`, or
- prepare a diagram specification from the discovered module interactions
- then use `plantuml-professional-diagrams`

That companion skill owns diagram authoring standards, image rendering, and Markdown image replacement.

## Writing Rules

- Never mention that the report was generated from a prompt
- Never write sentences such as "according to the code analysis" or similar meta narration
- Never present guessed behavior as confirmed implementation
- If testing evidence is missing, write a test design or validation plan instead of fake results

## References

- Inspection and evidence gathering: [references/inspection-checklist.md](references/inspection-checklist.md)
- Output and structure rules: [references/output-rules.md](references/output-rules.md)
- Experiment templates: [references/templates/](references/templates)
