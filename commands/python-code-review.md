---
description: Perform comprehensive Python code review following PEP 8 and Google Python Style Guide standards
---

You are acting as a Python code review expert. Follow the python-code-review skill workflow:

**Required workflow:**

1. Load the python-code-review skill using the Skill tool
2. Get the git diff between current branch and main (or read specified files if provided)
3. Execute systematic review following the skill's priority order:
   - Security (CRITICAL) - SQL injection, hardcoded secrets, unsafe functions
   - Code Quality & Best Practices (HIGH) - Exception handling, resource management, function defaults
   - Type Hints (HIGH) - Modern syntax, proper annotations
   - Style & Formatting (MEDIUM) - PEP 8 compliance, line length, indentation, whitespace
   - Imports (MEDIUM) - Order, style, format
   - Naming Conventions (MEDIUM) - Consistency with PEP 8 standards
   - Documentation (MEDIUM) - Docstrings, comments, Google style
   - Performance (MEDIUM) - String concatenation, generators, comprehensions
   - Maintainability (LOW) - Function length, main guard

4. Document every issue using the skill's output format:
   - Category (Style/Documentation/Quality/Security/Performance/Maintainability)
   - Severity (Critical/High/Medium/Low)
   - Lines (specific line numbers)
   - PEP 8/Google Reference (if applicable)
   - Description with current code
   - Recommended fix with corrected code
   - Rationale (why this matters)

5. Provide summary with:
   - Overall Assessment (Excellent/Good/Fair/Needs Improvement)
   - PEP 8 Compliance level (High/Medium/Low)
   - Google Style Compliance level (High/Medium/Low)
   - Key Strengths (2-4 well-implemented aspects)
   - Critical Issues (if any)
   - Positive Highlights
   - Priority-ordered recommendations

**Key Review Principles:**

- Consistency within project > rigid adherence to rules
- Wait for third occurrence before flagging duplication (Sandi Metz principle)
- Be constructive and provide actionable recommendations
- Focus on changes being made (not rewriting entire codebase)
- Prioritize: Critical (security/bugs) > High (readability) > Medium (style) > Low (nitpicks)

**Output must follow the exact format specified in the python-code-review skill.**
