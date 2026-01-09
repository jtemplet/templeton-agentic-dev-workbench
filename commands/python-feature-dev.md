---
description: Guided Python feature development with Sandi Metz principles
argument-hint: [feature-description]
---

<!--
Usage: /python-feature-dev [feature-description]
Example: /python-feature-dev "add user authentication system"

Invokes the python-feature-developer agent to guide feature implementation through:
1. Discovery - Ask clarifying questions about requirements
2. Implementation - Write code following Sandi Metz principles
3. Simplification - Refine code for clarity and maintainability
4. Linting - Apply ruff for PEP8/Google Python Style compliance
-->

Use the Task tool to launch the python-feature-developer agent with the following prompt:

"$ARGUMENTS"

If no arguments provided, ask the user to describe the feature they want to implement.
