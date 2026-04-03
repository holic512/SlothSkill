# Inspection Checklist

Use this checklist before writing the report. The goal is to keep topic-driven material separate from implementation evidence.

## Topic Sources

Look for the experiment title, course context, and project objective in:

- the user request
- the repository directory name
- assignment files or requirement documents
- README files
- existing report titles or older prompt titles

If the title is incomplete, normalize it conservatively. Do not invent domain details that are not supported.

## Repository Evidence

Inspect:

- repository structure and module boundaries
- language and framework indicators
- build files, dependency manifests, startup scripts, and config files
- entrypoints, controllers, services, utilities, schedulers, and data access layers
- SQL files, ORM models, migrations, or schema definitions
- screenshots, UI assets, and named pages when available
- tests, logs, assertions, and validation artifacts

## Evidence Priority

Topic-driven sections:

- background
- significance
- objectives
- user needs
- experiment purpose
- requirements analysis

Code-driven sections:

- architecture
- module design
- data design
- implementation
- runtime flow
- testing and issue analysis

## Avoidable Mistakes

- do not turn a template example into a project fact
- do not treat a filename guess as confirmed responsibility
- do not claim a database schema that is not present
- do not present framework defaults as project-specific functionality
- do not use code structure alone as the entire requirements section

## Missing Evidence Policy

If evidence is incomplete:

- keep requirements discussion at the task and scenario level
- keep design discussion at the supported abstraction level
- use screenshot placeholders when needed
- write a testing plan instead of fake execution results
