---
name: agentic-clean-code
description: >
  Principles for writing clean, elegant, and maintainable agentic code, drawing from
  Uncle Bob's Clean Code and Sandi Metz's POODR, transposed into the agentic programming
  context. Use this skill whenever you are designing or implementing multi-agent systems,
  tool definitions, orchestration logic, prompt architecture, agent loops, or any code
  where an LLM drives execution. Trigger this skill when the user asks about agentic code
  quality, agent design, clean agent architecture, or how to structure tools and prompts
  well. Also trigger when reviewing or refactoring existing agentic code for clarity.
---

# Agentic Clean Code

Principles for writing clean, elegant agentic systems. Draws from Robert C. Martin
(Clean Code, SOLID) and Sandi Metz (POODR) — transposed into the agentic context
where the "function caller" is an LLM and the "runtime" is a conversation loop.

---

## The Core Tension in Agentic Code

Traditional clean code assumes a deterministic caller. Agentic code does not. The LLM
chooses which tools to call, in what order, with what arguments. This changes everything:

- **Ambiguous APIs get misused** more than in human-authored code
- **Side effects are catastrophic** when an agent misreads context
- **Long context is the enemy** of precise reasoning
- **Naming is even more critical** — the model reads it, not just the programmer
The principles below address these realities directly.

---

## I. Tool Design Principles

### 1. One Tool, One Job (Uncle Bob: SRP → Agentic SRP)

A tool should do exactly one thing and do it completely. If you find yourself naming a
tool `search_and_summarize` or `fetch_and_store`, split it.

**Bad:**

```python
def research_and_draft(topic: str) -> str:
    """Search the web, summarize findings, and write a draft."""
    ...
```

**Good:**

```python
def search_web(query: str) -> list[SearchResult]: ...
def summarize_results(results: list[SearchResult]) -> str: ...
def draft_section(summary: str, tone: str) -> str: ...
```

The agent orchestrates composition. The tools stay pure.

### 2. Tell, Don't Ask (Sandi Metz → Agentic)

Tools should execute decisions, not return data for the agent to decide upon — unless
decision-making is explicitly the agent's role. Tools that return raw data and require
the agent to reason about next steps create long reasoning chains and accumulate errors.

**Bad:**

```python
def get_file_status(path: str) -> dict:
    """Returns metadata so the caller can decide what to do."""
```

**Good:**

```python
def ensure_file_exists(path: str) -> None:
    """Creates the file if it doesn't exist. Idempotent."""
```

### 3. Explicit Contracts (Uncle Bob: Clean Boundaries)

Every tool's input and output must be unambiguous. Use typed schemas. Never accept
`**kwargs` or return raw dicts without a schema. The model infers behavior from the
contract — a loose contract produces loose behavior.

```python
# Bad: Vague contract
def process(data: dict) -> dict: ...

# Good: Explicit contract
class EmailDraft(BaseModel):
    recipient: str
    subject: str
    body: str
    cc: list[str] = []

def draft_email(context: MeetingContext) -> EmailDraft: ...
```

### 4. No Surprise Side Effects (Uncle Bob: Side Effect-Free Functions)

If a tool writes to disk, sends a network request, or mutates state — say so explicitly
in the name and docstring. Never bury side effects in tools named like queries.

```python
# Bad: Looks like a read, acts like a write
def get_or_create_record(id: str) -> Record: ...

# Good: Side effect is in the name
def create_record_if_missing(id: str) -> Record: ...
```

### 5. Idempotency by Default

Agentic tools get called multiple times — retries, replanning, parallel branches. Design
tools to be safe to call more than once. If idempotency isn't possible, make it obvious.

---

## II. Prompt Architecture Principles

### 6. Small Prompts (Sandi Metz: Small Methods)

A system prompt longer than ~200 words is a code smell. If your system prompt is doing
multiple jobs — persona definition, tool instructions, formatting rules, behavioral
constraints — extract and separate them. Long prompts diffuse model attention and are
hard to test.

**Decompose by concern:**

- Identity prompt: Who is this agent?
- Capability prompt: What tools does it have?
- Constraint prompt: What should it never do?
- Format prompt: How should it respond?
Each concern can be composed, versioned, and tested independently.

### 7. No Implicit State in Prompts (Uncle Bob: Don't Hide Information)

Prompts that rely on implicit context accumulated elsewhere create hidden dependencies.
State that matters should be passed explicitly in the message — not assumed from earlier
turns or injected silently.

```python
# Bad: Assumes agent "remembers" the user's name from turn 1
system = "You are a helpful assistant."

# Good: Explicit context injection
system = f"You are helping {user.name}. Their current task is: {task.description}."
```

### 8. Prompt Parameters Are Function Arguments (Sandi Metz: Argument Objects)

If your prompt takes more than 3 injected variables, introduce a context object. Don't
build prompts via string concatenation — treat them like function signatures.

```python
# Bad
prompt = f"User: {name}. Tone: {tone}. Format: {fmt}. Length: {length}. Task: {task}."

# Good
@dataclass
class PromptContext:
    user: User
    task: Task
    preferences: ResponsePreferences

def build_prompt(ctx: PromptContext) -> str: ...
```

---

## III. Orchestration Principles

### 9. Separate Orchestration from Execution (Uncle Bob: Separate Concerns)

Orchestrators decide *what* to do and in what order. Executors (tools/agents) do the
work. Never mix them. An orchestrator that also does work is impossible to reason about.

```text
Orchestrator: "Given the plan, which step is next? Call the right tool."
Tool:         "Given these inputs, produce this output."
```

If an agent is making decisions AND calling tools in the same loop iteration, ask whether
those concerns can be split across a planning step and an execution step.

### 10. Minimize the Agent's Footprint (Sandi Metz: Dependency Inversion → Agentic)

Agents should depend on abstractions (tool interfaces), not concrete implementations.
An agent that knows too much about the system it's operating in is brittle. Give it only
the tools it needs. Unused tools in a tool list pollute the decision space.

```python
# Bad: Give the agent everything
tools = [search, read_file, write_file, send_email, create_calendar_event, ...]

# Good: Scope tools to the task
tools = [search, read_file]  # Research agent gets read-only tools
```

### 11. Make Agent Boundaries Explicit (Uncle Bob: Clean Architecture Layers)

Each agent in a multi-agent system should have a clearly defined input contract, output
contract, and failure behavior. Inter-agent communication via unstructured natural
language strings is the agentic equivalent of global mutable state.

```python
# Bad: Loose handoff
result = await subagent.run("Do the research thing")

# Good: Typed handoff
request = ResearchRequest(topic=topic, depth="shallow", format="bullet_points")
result: ResearchReport = await research_agent.run(request)
```

### 12. Fail Loudly and Early (Uncle Bob: Error Handling)

Agents that swallow errors and continue create compounding failures that are nearly
impossible to debug. Every tool should raise or return a structured error on failure.
Every orchestrator should have an explicit error policy — not a silent fallback.

```python
class ToolError(Exception):
    tool_name: str
    reason: str
    recoverable: bool

# Orchestrator handles explicitly:
try:
    result = tool.call(args)
except ToolError as e:
    if e.recoverable:
        return await replanner.replan(e)
    raise AgentFailure(f"{e.tool_name} failed unrecoverably: {e.reason}")
```

---

## IV. Naming Principles

### 13. Name for the Model, Not Just the Human (Uncle Bob: Meaningful Names → Amplified)

In agentic code, tool names and docstrings are parsed by the model at runtime. They are
functional specification, not just documentation. Names must be:

- **Unambiguous** — `get_user` vs `get_user_by_email` vs `get_user_by_id`
- **Action-oriented** — start with a verb: `search_`, `create_`, `delete_`, `check_`
- **Scoped** — `calendar_create_event`, not `create_event` (namespace collisions confuse models)

### 14. Docstrings Are Contracts (Sandi Metz: Messages Are Interface)

The docstring is the agent's only API documentation. Write it like a contract:

```python
def send_email(draft: EmailDraft) -> SendResult:
    """
    Sends an email using the authenticated SMTP connection.

    Does NOT save a copy to Sent unless save_to_sent=True.
    Raises ToolError if recipient address is invalid.
    Raises ToolError if SMTP auth has expired.
    """
```

Never write "Sends an email." That's a category, not a contract.

---

## V. Testability Principles

### 15. Every Tool Must Be Testable in Isolation (Uncle Bob: Testable Design)

If you can't write a unit test for a tool without spinning up an agent loop, the tool is
doing too much. Tools should be pure functions of their inputs wherever possible, with
I/O side effects injected as dependencies.

### 16. Test Agent Behavior at the Step Level (Sandi Metz: Test Messages, Not Methods)

Don't test the full agent end-to-end for every case. Test the *decisions* the agent
makes at each step given specific context. Mock the tool layer. Assert on which tool
was called with what arguments — not just the final output.

---

## VI. The Metz Rules — Agentic Edition

Sandi Metz's famous 4 rules for OOP classes, adapted:

| Original | Agentic Equivalent |
|---|---|
| Classes ≤ 100 lines | Tool implementations ≤ 50 lines |
| Methods ≤ 5 lines | Tool logic ≤ 20 lines (or extract helpers) |
| ≤ 4 method parameters | ≤ 3 tool parameters (use typed objects for more) |
| Controllers instantiate one object | Orchestrators call one tool per reasoning step |

The last rule is the most important: if your orchestrator is calling multiple tools in a
single LLM turn without reasoning in between, that's a workflow pretending to be an agent.

---

## VII. Smell Checklist

Before shipping agentic code, check for these smells:

- [ ] Tools with "and" in the name → split them
- [ ] System prompts over 300 words → decompose by concern
- [ ] Tools that return raw dicts → add typed schemas
- [ ] Agent loops with no error policy → add explicit failure handling
- [ ] Prompt variables injected via string concat → use context objects
- [ ] Tool lists with >8 tools → scope to the task
- [ ] Tools that assume previous tool output without it being passed explicitly → hidden state
- [ ] Docstrings that describe the tool category, not the contract → rewrite

---

## Further Reading

- *Clean Code* — Robert C. Martin (Ch. 2: Names, Ch. 3: Functions, Ch. 7: Error Handling)
- *Practical Object-Oriented Design* — Sandi Metz (Ch. 4: Flexible Interfaces, Ch. 9: Costs)
- Simon Willison's `llm` CLI codebase — exemplary tool composability
- Anthropic's [tool use best practices](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)
