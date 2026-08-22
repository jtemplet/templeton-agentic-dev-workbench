# CONTEXT.md Format

The glossary format used by the `domain-modeling` skill.

## Structure

```md
# {Context Name}

{One or two sentences on what this context is and why it exists.}

## Language

**Order**:
A customer's request for goods, priced and accepted but not yet fulfilled.
_Avoid_: Purchase, transaction

**Invoice**:
A request for payment sent to a customer after delivery.
_Avoid_: Bill, payment request

**Customer**:
A person or organization that places orders.
_Avoid_: Client, buyer, account
```

## Rules

- **Be opinionated.** When several words exist for one concept, pick the best one and list the rest
  under `_Avoid_`. A glossary that permits every synonym has settled nothing.
- **Keep definitions tight.** One or two sentences. Define what the thing IS, not what it does.
- **Only terms specific to this project's context.** General programming concepts (timeouts, error
  types, utility patterns) do not belong, even when the project uses them constantly. Before adding
  a term, ask whether it is unique to this context or general to programming. Only the first
  belongs.
- **Group terms under subheadings** when natural clusters emerge. A flat list is fine when every
  term belongs to one cohesive area.

## Single-context and multi-context repositories

**Single context (most repositories):** one `CONTEXT.md` at the repository root.

**Several contexts:** a `CONTEXT-MAP.md` at the root lists the contexts, where they live, and how
they relate:

```md
# Context Map

## Contexts

- [Ordering](./src/ordering/CONTEXT.md): receives and tracks customer orders
- [Billing](./src/billing/CONTEXT.md): generates invoices and processes payments
- [Fulfillment](./src/fulfillment/CONTEXT.md): manages warehouse picking and shipping

## Relationships

- **Ordering to Fulfillment**: Ordering emits `OrderPlaced` events; Fulfillment consumes them to
  start picking
- **Fulfillment to Billing**: Fulfillment emits `ShipmentDispatched` events; Billing consumes them
  to generate an invoice
- **Ordering and Billing**: shared types for `CustomerId` and `Money`
```

Infer which structure applies:

- If `CONTEXT-MAP.md` exists, read it to find the contexts.
- If only a root `CONTEXT.md` exists, the repository has a single context.
- If neither exists, create a root `CONTEXT.md` lazily, when the first term is resolved.

When several contexts exist, infer which one the current topic belongs to. Ask when it is unclear.
