---
name: templeton-swift-style
description: Writes and reviews Swift/iOS in the house style (protocol-oriented, value-type-first, TRUE code). Use when writing or reviewing Swift code.
---

# Templeton Swift Style

Writes and reviews Swift/iOS code in the house style: protocol-oriented, value-type-first, and TRUE (Transparent, Reasonable, Usable, Exemplary). This skill carries only the Swift-specific deltas layered on top of the universal style core; it does not restate the universal principles.

## When to Use / When NOT to Use

Use when:

- Writing new Swift types, view models, or SwiftUI views in the house style.
- Reviewing Swift/iOS code for design quality (protocol orientation, value semantics, error handling, concurrency).
- Refactoring Swift toward value types, composition, and explicit errors.

Do NOT use when:

- The code is not Swift (use the matching language style skill instead).
- Reviewing generated or vendored Swift (e.g. `*.generated.swift`, protobuf output, third-party `Pods/`).
- Hacking in a throwaway playground or one-off script where production design rigor is overhead.

## Universal Core (injected)

The universal "TRUE code" definition and the 9 language-agnostic principles (wait for duplication, small single-purpose units, simple interfaces, dependency injection, tell-don't-ask, compose over inherit, fail fast, step-down reading order, self-documenting names) are injected separately from `hooks/style-core.md` and apply here unchanged. This skill does not repeat them; the sections below add only what is specific to Swift.

## Swift Principles

1. **Default to value types; reach for a class only with a reason.** Use `struct`/`enum` unless you need reference semantics: shared mutable state, object identity, `class`-only framework requirements (`NSObject`, `ObservableObject`), or deinit lifecycle.

   ```swift
   // BAD
   class User {
       var name: String
       var email: String
       init(name: String, email: String) { self.name = name; self.email = email }
   }
   ```

   Why: `User` has no identity, no shared mutation, and no deinit needs. A class adds reference semantics, aliasing bugs, and avoidable retain-cycle risk.

   ```swift
   // GOOD
   struct User {
       let name: String
       let email: String
   }
   ```

2. **Make protocols the primary abstraction, not class inheritance.** Model capabilities as protocols and compose conformances; do not build base classes to share behavior.

   ```swift
   // BAD
   class BaseRepository { func save() { /* shared persistence */ } }
   class UserRepository: BaseRepository { /* + user logic */ }
   ```

   Why: A base class hard-couples subclasses to shared internals and forces a single hierarchy. Tests cannot substitute behavior cleanly.

   ```swift
   // GOOD
   protocol Repository { func save() throws }
   struct UserRepository: Repository {
       let store: PersistenceStore   // injected
       func save() throws { try store.persist() }
   }
   ```

3. **Avoid the Bool trap.** Never expose two or more boolean parameters; model intent with an `enum`, a typed options `struct`, or `OptionSet`.

   ```swift
   // BAD
   func loadUsers(animated: Bool, includeArchived: Bool, forceRefresh: Bool) { }
   loadUsers(animated: true, includeArchived: false, forceRefresh: true) // what is true?
   ```

   Why: Boolean call sites are unreadable and trivially transposed, and each new flag doubles the combinations.

   ```swift
   // GOOD
   struct LoadOptions: OptionSet {
       let rawValue: Int
       static let animated      = LoadOptions(rawValue: 1 << 0)
       static let includeArchived = LoadOptions(rawValue: 1 << 1)
       static let forceRefresh  = LoadOptions(rawValue: 1 << 2)
   }
   func loadUsers(_ options: LoadOptions) { }
   loadUsers([.animated, .forceRefresh])
   ```

4. **Make errors explicit; never silently nil.** Prefer `throws` (or `Result`) with typed error cases over `try?` that collapses every failure into `nil`.

   ```swift
   // BAD
   func fetchUser(_ id: String) -> User? {
       try? decoder.decode(User.self, from: data)
   }
   ```

   Why: The caller cannot tell "not found" from "decode failed" from "offline." Failures vanish.

   ```swift
   // GOOD
   enum UserFetchError: Error { case notFound, decoding(Error) }

   func fetchUser(_ id: String) async throws -> User {
       let (data, response) = try await session.data(from: url(for: id))
       guard (response as? HTTPURLResponse)?.statusCode == 200 else {
           throw UserFetchError.notFound
       }
       do { return try decoder.decode(User.self, from: data) }
       catch { throw UserFetchError.decoding(error) }
   }
   ```

5. **Use async/await and structured concurrency; manage captures deliberately.** Prefer `async`/`await` over completion handlers, isolate UI state with `@MainActor`, and write an explicit capture list with a one-line reason whenever you capture `self`.

   ```swift
   // BAD
   func refresh() {
       service.load { result in
           self.items = result   // strong capture; leaks if service retains the closure
       }
   }
   ```

   Why: An undocumented strong `self` capture in a retained closure creates a retain cycle and hides the threading contract.

   ```swift
   // GOOD
   @MainActor
   func refresh() async throws {
       let result = try await service.load()
       self.items = result   // structured await; no escaping closure, no cycle
   }
   // When a closure must escape, justify the capture:
   // [weak self] in  // view may be deallocated before the callback fires
   ```

6. **Keep SwiftUI views thin; push logic into view models.** Views render state and forward intent. Put business logic and mutable state in an `ObservableObject` view model with `@Published` properties, and extract subviews before a `body` grows unreadable.

   ```swift
   // BAD
   struct OrderView: View {
       @State private var items: [Item] = []
       var body: some View {
           VStack {
               // 120 lines: networking, total math, formatting, and layout inline
           }
       }
   }
   ```

   Why: Business logic embedded in `body` is untestable, re-runs on every render, and bloats the view past readability.

   ```swift
   // GOOD
   @MainActor
   final class OrderViewModel: ObservableObject {
       @Published private(set) var rows: [OrderRow] = []
       func load() async { /* fetch + map to rows */ }
   }

   struct OrderView: View {
       @StateObject var model: OrderViewModel
       var body: some View {
           List(model.rows) { OrderRowView(row: $0) }
               .task { await model.load() }
       }
   }
   ```

7. **Use extensions to organize by responsibility, never to hide size.** Split conformances and cohesive helpers into extensions for readability, but moving 200 lines into an extension does not reduce the type's responsibilities.

   ```swift
   // BAD
   extension OrderProcessor {
       // 200 lines of unrelated networking, pricing, and formatting
       // hidden in an extension so the main type "looks small"
   }
   ```

   Why: An extension changes file layout, not coupling. A type doing five jobs across five extensions is still a type doing five jobs.

   ```swift
   // GOOD
   extension OrderProcessor: Equatable { /* just the conformance */ }
   extension OrderProcessor {
       // cohesive pricing helpers, all one abstraction level
   }
   // Genuinely separate responsibilities become their own injected types.
   ```

## Anti-Patterns

Each smell below shows bad, why it hurts, and the correction.

- **Class where a struct fits.** Bad: a `class` model with stored `let`s and no identity. Why: needless reference semantics and aliasing/retain-cycle risk. Fix: make it a `struct` (see Principle 1).
- **Deep inheritance.** Bad: `class C: B`, `class B: A` sharing behavior through three levels. Why: fragile base class, single rigid hierarchy, hard to test. Fix: model capabilities as protocols and compose (Principle 2).
- **Bool-param trap.** Bad: `configure(animated: true, secure: false)`. Why: unreadable call sites and combinatorial explosion. Fix: an `enum`, options `struct`, or `OptionSet` (Principle 3).
- **Silent `try?`.** Bad: `let user = try? decode(...)` discarding the error. Why: every distinct failure becomes an indistinguishable `nil`. Fix: `throws` with typed error cases (Principle 4).
- **Singletons / global mutable state.** Bad: `NetworkManager.shared` referenced directly inside a type. Why: hidden dependency, unmockable, cross-test contamination. Fix: inject the dependency through `init` behind a protocol.
- **Fat SwiftUI view.** Bad: networking, computation, and formatting inline in `body`. Why: untestable, re-runs every render, unreadable. Fix: move logic to an `ObservableObject` view model and extract subviews (Principle 6).

## Worked Examples

### Value type: class to struct (full before/after)

Before:

```swift
class User {
    var name: String
    var email: String

    init(name: String, email: String) {
        self.name = name
        self.email = email
    }
}
```

After:

```swift
struct User {
    let name: String
    let email: String
}
```

Why: `User` is immutable, has no identity, and shares no state. A `struct` gives value semantics, thread-safety, and free `Equatable`/`Hashable` synthesis, and removes reference-cycle risk.

### Tell, don't ask: stop reaching through objects

Before:

```swift
// UserViewController.swift
if viewModel.user.account.subscription.isActive {
    processPayment(viewModel.user.account.subscription.amount)
}
```

After:

```swift
if viewModel.hasActiveSubscription {
    viewModel.processSubscriptionPayment()
}
```

Why: The chain couples the controller to the internal shape of `User`, `Account`, and `Subscription`; any of those changing breaks the controller. Moving the behavior onto the view model leaves the controller sending one message.

### Step-down rule: one abstraction level per method

Before:

```swift
class OrderProcessor {
    func process(order: Order) -> OrderResult {
        guard !order.items.isEmpty else { return OrderResult.empty() }

        // sudden drop to networking details
        let url = URL(string: "https://api.example.com/orders")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let data = try? JSONEncoder().encode(order)
        let (response, _) = try? URLSession.shared.data(for: request)

        let total = calculateTotal(order)          // back to mid level
        let signature = order.description.sha256()  // low level again
    }
}
```

After:

```swift
class OrderProcessor {
    private let api: OrderAPI
    private let calculator: PricingCalculator

    // High level: business narrative only
    func process(order: Order) async throws -> OrderResult {
        guard !orderIsEmpty(order) else { return OrderResult.empty() }

        let total = calculateTotal(order)
        let signature = signOrder(order)
        return try await saveAndReturn(order, total: total, signature: signature)
    }

    // Mid level: orchestration
    private func orderIsEmpty(_ order: Order) -> Bool { order.items.isEmpty }
    private func calculateTotal(_ order: Order) -> Decimal { calculator.compute(order) }
    private func signOrder(_ order: Order) -> String { createSignature(order.description) }
    private func saveAndReturn(_ order: Order, total: Decimal, signature: String) async throws -> OrderResult {
        try await api.save(order, total: total, signature: signature)
    }

    // Low level: implementation detail
    private func createSignature(_ data: String) -> String { data.sha256() }
}
```

Why: The reader skims `process` for intent, then descends only as needed. Networking and encoding move behind injected `OrderAPI`/`PricingCalculator`, and silent `try?` is replaced by propagated `throws`.

### Error handling: explicit failures over silent nil

Before:

```swift
func fetchUser(_ id: String) -> User? {
    let result = try? decoder.decode(User.self, from: data)
    return result
}
```

After:

```swift
enum UserFetchError: Error {
    case networkError(URLError)
    case decodingError(DecodingError)
    case userNotFound
}

func fetchUser(_ id: String) async throws -> User {
    let (data, response) = try await URLSession.shared.data(from: url)
    guard (response as? HTTPURLResponse)?.statusCode == 200 else {
        throw UserFetchError.userNotFound
    }
    do {
        return try decoder.decode(User.self, from: data)
    } catch let error as DecodingError {
        throw UserFetchError.decodingError(error)
    }
}
```

Why: Typed cases let callers distinguish "not found" from "bad payload" and respond appropriately instead of guessing from a bare `nil`.

### Principles at a glance (quick reference)

| Delta | Goal | Common mistake |
|-------|------|----------------|
| Value types first | Predictability, thread-safety | Reaching for `class` by default |
| Protocol orientation | Composition without hierarchy | Sharing behavior via base classes |
| No Bool trap | Readable, future-proof call sites | Multiple boolean parameters |
| Explicit errors | Distinguishable, handleable failures | `try?` collapsing errors to `nil` |
| Structured concurrency | Safe threading, no leaks | Undocumented strong `self` captures |
| Thin SwiftUI views | Testable, cheap renders | Business logic inside `body` |

## Review / Apply Workflow

When writing Swift:

1. Choose value vs reference type deliberately; default to `struct`/`enum`.
2. Express abstractions as protocols and inject collaborators through `init`.
3. Keep call sites readable: no Bool trap, interfaces within the universal param budget.
4. Make failure modes explicit with `throws`/typed errors; never swallow with `try?`.
5. Use `async`/`await` with `@MainActor` for UI state; justify every capture list.
6. Keep views thin; extract logic into view models and subviews.

When reviewing Swift:

1. Read changed files top to bottom for intent before judging details.
2. Confirm correctness first: if tests pass and behavior is right, cap severity at MEDIUM (verification-first).
3. Flag the Swift smells in the Anti-Patterns list, each with file:line.
4. For every flag, give bad -> why -> corrected with the matching principle named.
5. Separate must-fix design defects from optional polish; do not gold-plate.

## Quality Checklist

- [ ] Types default to `struct`/`enum`; each `class` has a stated reference-semantics reason.
- [ ] Abstractions are protocols; collaborators are injected, no direct singletons/global state.
- [ ] No method exposes two or more boolean parameters.
- [ ] Errors are explicit (`throws`/typed/`Result`); no silent `try?` discarding failures.
- [ ] Concurrency is structured; UI mutation is `@MainActor`; every capture list is justified.
- [ ] SwiftUI views are thin; business logic lives in view models; large bodies are decomposed.
- [ ] Extensions organize by responsibility and do not mask oversized types.
- [ ] Each method reads at one abstraction level (step-down rule holds).
