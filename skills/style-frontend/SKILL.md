---
name: style-frontend
description: Writes and reviews JavaScript/TypeScript, React, and Vue in the house style - TRUE components, frontend-specific deltas (small presentational components, logic in hooks/composables, typed props, no class components) layered on the injected universal style core.
---

# Frontend Style (JS/TS, React, Vue)

Write and review JavaScript/TypeScript, React, and Vue code in the house style. This skill carries only the frontend-specific deltas (component sizing, props, hooks/composables, state, TypeScript) on top of the universal TRUE-code core that is injected separately. Apply both together.

## When to Use / When NOT to Use

Use when:

- Writing or reviewing React (function components, hooks) or Vue 3 (Composition API, composables) code.
- Authoring or reviewing TypeScript/JavaScript modules that back a UI (state, props, view logic).
- Refactoring a component that mixes presentation with business logic, has too many props, or drills props through layers.

Do NOT use when:

- The code is backend-only (Node service logic, API handlers, DB access with no UI concern); use the matching backend style skill instead.
- The change touches non-JS/TS files (config, CSS-only tweaks, Markdown, infra).
- The change is a trivial markup or copy tweak with no structural impact.

## Universal Core (injected)

The universal TRUE-code principles (Transparent, Reasonable, Usable, Exemplary) and the 9 language-agnostic rules (wait for duplication, small single-purpose units, simple interfaces, dependency injection, tell-don't-ask, compose over inherit, fail fast, step-down reading order, names do the documenting) are injected via `hooks/style-core.md` and assumed here. This skill does not repeat them; it only adds the frontend deltas below.

## Frontend Principles

1. Keep components small and presentational (~100-150 lines including template/JSX). If you cannot name what a component does in one phrase, split it.

   ```tsx
   // BAD: one component fetches, transforms, and renders (200+ lines)
   function UserDashboard({ userId }) {
     const [data, setData] = useState(null)
     useEffect(() => { fetch(`/api/users/${userId}`).then(/* 30 lines */) }, [userId])
     return <div>{/* deeply nested inline JSX with calculations */}</div>
   }
   // why: reader cannot see structure; fetch + transform + render are tangled.
   // GOOD: composition only; details live in hooks/children
   function UserDashboard({ userId }) {
     const { data, loading } = useUserData(userId)
     if (loading) return <LoadingSpinner />
     return <><UserHeader name={data.name} /><OrderList orders={data.orders} /></>
   }
   ```

2. Cap props at 4-5; group related props into a typed object; never use behavioral boolean flags. Split into separate components or use composition/slots instead.

   ```tsx
   // BAD: behavioral flags create combinatorial complexity
   <DataTable data={users} sortable filterable paginated striped showFooter />
   // why: 6+ flags multiply states; testing and reasoning explode.
   // GOOD: distinct components, or composition for the complex case
   <SortableTable data={users} onSort={handleSort} />
   <Table data={users}><TableBody striped /><Pagination pageSize={20} /></Table>
   ```

3. Extract business logic into custom hooks (React) or composables (Vue); keep the component presentational.

   ```tsx
   // BAD: API + routing logic inside the component
   const submit = async () => {
     const res = await fetch('/api/orders', { method: 'POST', body: JSON.stringify(order) })
     router.push(`/orders/${(await res.json()).id}`)
   }
   // why: cannot test the flow without mounting; mixes UI, network, navigation.
   // GOOD: logic in a hook, component just wires it
   const { submitOrder, isSubmitting } = useOrderSubmission()
   const handleSubmit = () => submitOrder({ customerId, items })
   ```

4. Never write class components for new code; share logic through hooks/composables, not base classes.

   ```tsx
   // BAD: class component with lifecycle methods for new code
   class Profile extends React.Component {
     componentDidMount() { this.load() }
     render() { return <div>{this.state.name}</div> }
   }
   // why: lifecycle methods scatter logic; no easy logic reuse; off-pattern.
   // GOOD: function component + hook
   function Profile({ id }) {
     const { name } = useProfile(id)
     return <div>{name}</div>
   }
   ```

5. Inject services and clients; do not instantiate them inside components. React: Context, props, or hooks. Vue: provide/inject, props, or composables.

   ```tsx
   // BAD: component constructs its own client (untestable, coupled)
   function Orders() { const api = new OrderApiClient(BASE_URL); /* ... */ }
   // why: cannot swap or mock the client; hidden dependency on global config.
   // GOOD: receive the dependency
   function Orders() { const { createOrder } = useOrderApi() /* injected via context */ }
   ```

6. Start with local state; lift only when shared; reach for a global store (Pinia/Zustand/Redux) only for shared app state, server-cache, or cross-cutting concerns (auth, theme).

   ```tsx
   // BAD: modal open/close pushed into a global Redux slice
   dispatch(openInviteModal())
   // why: UI-only state in global store adds boilerplate and coupling.
   // GOOD: local state, lifted only if a sibling needs it
   const [isOpen, setIsOpen] = useState(false)
   ```

7. Use TypeScript everywhere; avoid `any` (use `unknown` and narrow); model state with discriminated unions.

   ```tsx
   // BAD: any erases all safety
   function render(data: any) { return <p>{data.titel}</p> } // typo survives
   // why: any disables checking; typos and shape errors ship.
   // GOOD: unknown + narrowing, or a discriminated union for state
   type State = { status: 'loading' } | { status: 'error'; error: Error } | { status: 'ok'; data: User }
   ```

8. Handle errors at boundaries (React Error Boundaries, Vue `errorCaptured`); do not swallow them silently or use try/catch for control flow.

   ```tsx
   // BAD: error swallowed, user sees nothing, dev sees nothing
   try { await save() } catch { /* ignore */ }
   // why: failures vanish; debugging and recovery become impossible.
   // GOOD: surface and let a boundary catch what is unexpected
   try { await save() } catch (e) { setError(e instanceof Error ? e : new Error('Save failed')) }
   ```

9. Remove `console.log` before commit; never log secrets or PII. Use a real logger for production diagnostics.

   ```javascript
   // BAD: debug log left in, leaks user data
   console.log(userData)
   // why: clutters output, can expose tokens/PII in production consoles.
   // GOOD: structured logger, no sensitive fields
   logger.info('User data loaded', { userId: user.id })
   ```

## Anti-Patterns

- Logic-in-component: business/network logic lives in the component. Why: untestable, couples UI to side effects. Fix: extract to a hook/composable; component stays presentational.
- Props explosion: a component takes 8-12 props, several behavioral booleans. Why: combinatorial states, hard to test. Fix: split into focused components or compose via slots/children.
- Prop drilling: a value is threaded through 3+ intermediate components that do not use it. Why: brittle, noisy, refactor-hostile. Fix: Context/provide-inject for cross-cutting values, or composition so the consumer renders where the data lives.
- Premature "flexible" mega-component: one component built to handle every future case via flags/slots. Why: violates wait-for-duplication; rigid and complex before any real need. Fix: build the concrete case; extract only on the third repetition.
- Class components for new code: lifecycle-method classes instead of function components. Why: scatters logic, no clean reuse, off the modern path. Fix: function component plus hooks/composables.
- `any` everywhere: types defaulted to `any` to silence the compiler. Why: erases type safety; typos and shape drift ship. Fix: `unknown` with narrowing, precise interfaces, discriminated unions.

## Worked Examples

Separation of concerns: move logic out of the component into a composable.

```vue
<!-- BEFORE: OrderForm.vue - API, totals, and routing all in the component -->
<script setup>
const submitOrder = async () => {
  try {
    const response = await fetch('/api/orders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        items: items.value,
        total: items.value.reduce((sum, item) => sum + item.price, 0),
        customerId: customerId.value
      })
    })
    if (!response.ok) throw new Error('Failed')
    const order = await response.json()
    router.push(`/orders/${order.id}`)
  } catch (error) {
    errorMessage.value = 'Something went wrong'
  }
}
</script>
```

```vue
<!-- AFTER: logic in a composable, component handles presentation only -->
<script setup>
// composables/useOrderSubmission.js
export function useOrderSubmission() {
  const { createOrder } = useOrderApi()
  const router = useRouter()
  const submitOrder = async (orderData) => {
    const order = await createOrder(orderData)
    router.push(`/orders/${order.id}`)
    return order
  }
  return { submitOrder }
}

// OrderForm.vue
const props = defineProps({
  items: { type: Array, required: true },
  customerId: { type: String, required: true }
})
const { submitOrder } = useOrderSubmission()
const handleSubmit = async () => {
  try {
    await submitOrder({ items: props.items, customerId: props.customerId })
  } catch (error) {
    errorMessage.value = 'Something went wrong'
  }
}
</script>
```

Why: the component is tightly coupled to the API, totals math, and routing, so the business flow cannot be tested without mounting it and it violates single responsibility. After extraction the composable owns the flow (testable in isolation), the component owns presentation and user interaction, and dependencies are injected via `useOrderApi`. The result reads top-down and is reusable wherever order submission is needed.

A clean React target component, for reference, shows the same separation with typed props and an injected hook:

```tsx
interface OrderFormProps {
  customerId: string
  onSuccess?: (orderId: string) => void
}

export function OrderForm({ customerId, onSuccess }: OrderFormProps) {
  const { submitOrder, isSubmitting, error } = useOrderSubmission()
  const [items, setItems] = useState<OrderItem[]>([])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    const orderId = await submitOrder({ customerId, items })
    onSuccess?.(orderId)
  }

  return (
    <form onSubmit={handleSubmit}>
      <OrderItemList items={items} onChange={setItems} />
      {error && <ErrorMessage error={error} />}
      <SubmitButton loading={isSubmitting} />
    </form>
  )
}
```

## Review / Apply Workflow

When writing frontend code:

1. Start with the concrete case and local state; do not pre-build flexibility.
2. Type props and state up front; group related props into a typed object.
3. As soon as business or network logic appears, extract it into a hook/composable so the component stays presentational.
4. Inject services via Context/hooks (React) or provide-inject/composables (Vue).
5. Keep the file readable top-down: structure first, then state, derived values, effects, handlers, helpers (extract helpers if more than 2-3).
6. Remove debug logging before commit.

When reviewing frontend code:

1. Scan for logic-in-component and prop-explosion first; these are the highest-value fixes.
2. Flag premature abstractions (single-use hooks/components built "for flexibility").
3. Trace props for drilling; suggest Context/composition where a value passes through unused.
4. Check TypeScript usage: no `any`, discriminated unions for state, precise prop types.
5. Verify errors are handled at a boundary, not swallowed.
6. Report each finding as bad -> why it matters -> corrected version, with `file:line` references.

## Quality Checklist

- [ ] Components are small (~100-150 lines) and presentational; logic lives in hooks/composables.
- [ ] No component exceeds 4-5 props; related props are grouped into typed objects; no behavioral boolean flags.
- [ ] No class components in new code; reuse is via hooks/composables.
- [ ] Services and clients are injected, not instantiated inside components.
- [ ] State is local by default; global store used only for shared/app/server-cache/cross-cutting state.
- [ ] TypeScript is used throughout; no `any`; state uses discriminated unions where appropriate.
- [ ] Errors are handled at boundaries and never silently swallowed.
- [ ] No leftover `console.log`; no secrets or PII in logs.
- [ ] File reads top-down from structure to details; no prop drilling.
