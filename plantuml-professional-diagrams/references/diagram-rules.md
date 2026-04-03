# Diagram Rules

Use these rules when authoring or reviewing PlantUML diagrams for reports.

## When To Prefer A Sequence Diagram

Choose a sequence diagram when the reader needs to understand:

- the order of calls between modules
- request and response flow
- synchronous or asynchronous coordination
- validation, persistence, and output steps across components

Do not force a sequence diagram when a static structure diagram would be clearer.

## Quality Rules

- keep participant names stable and specific
- do not overload the diagram with low-value method calls
- use activation bars for active processing periods
- use `alt`, `opt`, `loop`, and `group` only when they match real behavior
- keep messages directional and concise
- place notes sparingly
- ensure the title matches the actual scenario

## Styling Rules

Default PlantUML prelude:

```plantuml
@startuml
skinparam monochrome true
skinparam shadowing false
skinparam sequenceMessageAlign center
skinparam responseMessageBelowArrow true
```

Use additional skinparams only when they improve readability.

## Markdown Integration

- keep figure captions near the rendered image location
- use relative `images/...` paths in Markdown
- preserve image order across the report
