# `<tool_name>`

Use this template for a newly registered MCP tool. Replace all placeholders and
keep the headings unchanged so `scripts/validate_tool_specs.py` can validate it.

## Purpose

State what the tool does, when to call it, and when another tool is a better fit.

## Interface

| Parameter | Type | Required | Default | Definition |
| --- | --- | --- | --- | --- |
| `<parameter>` | `<type>` | Yes or No | `<value>` | `<constraint and meaning>` |

## Preconditions

State required dataset/category/image state, authorization, and validation rules.

## Behavior and invariants

State observable state changes, ordering, atomicity, geometry, or immutability
rules. Link to the shared contract instead of copying universal rules.

## Output

Describe the success envelope, its `data` shape, and any extra MCP content.

## Business errors

List stable error codes relevant to callers and the condition for each.

## Example

```json
{ "example": "request" }
```

## Acceptance criteria

List caller-observable success and failure conditions that tests must protect.
