---
name: simple-addition
description: A skill to add two numbers when asked to compute a sum.
---

# Simple Addition Skill

This skill helps the agent handle requests to add two integer numbers and return their sum.

## When to Use

Use this skill when the user asks to compute the sum of two numbers, e.g., "add 4 and 7" or "what is 10 + 15?".

## Instructions

1. Read the user query and identify two numbers that need to be added.
2. Extract the values for `a` and `b` from the query.
3. Compute the result as `a + b`.
4. Return the final sum as the answer.

## Example

- **Input**: "Add 5 and 8"
- **Output**: "5 + 8 = 13"

- **Input**: "What is the sum of 20 and 30?"
- **Output**: "20 + 30 = 50"
