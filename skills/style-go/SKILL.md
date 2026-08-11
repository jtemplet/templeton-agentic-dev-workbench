---
name: style-go
description: Writes and reviews Go in the house style - Go-specific deltas on top of the injected universal TRUE-code core, emphasizing accept interfaces and return structs, wrapped errors over sentinels, zero-value-useful types, table-driven tests, and a package API that reads from its doc comment
---

# Templeton Go Style

This skill writes and reviews Go in the house style. It carries only the Go-specific deltas on top of the universal TRUE-code core injected into every session; it does not restate that core. Use it whenever Go style decisions are in play.

Go already answers questions other languages leave open. `gofmt` settles formatting, so no rule here concerns layout. The standard library establishes idiom, so "what would `io` or `net/http` do" outranks any preference below.

## When to Use / When NOT to Use

Use this skill when:

- Writing new Go packages, types, or functions that should match the house style.
- Reviewing Go for structure, error handling, interfaces, concurrency, and tests.
- Refactoring or simplifying existing Go and you need the Go-specific deltas.

Do NOT use this skill when:

- The file is not Go (use `style-python`, `style-frontend`, `style-swift`, or the Rails skills).
- Formatting is the question. Run `gofmt`; it is not a matter of opinion.
- You only need the universal principles; those are injected and apply on their own.

## Universal Core (injected)

The universal TRUE-code principles (Transparent, Reasonable, Usable, Exemplary) are injected via `hooks/style-core.md` and are assumed here; this skill does not repeat them. They are: wait for duplication before abstracting; small single-purpose units; simple interfaces (<=4 params, typed param objects); inject dependencies on interfaces; tell-don't-ask; compose over inherit; fail fast with explicit errors; read top-down (step-down rule); let names document. Default posture: correctness > speed, simplicity > cleverness, explicit > magic, start simple.

Two universal rules land differently in Go, and the Go reading wins:

- **"Compose over inherit"** is not a choice here. Go has embedding and interface satisfaction, no inheritance. The delta is about *when to define an interface at all*; see principle 1.
- **"Simple interfaces (<=4 params)"** competes with Go's preference for explicit arguments over option structs. Under five parameters, pass them; see principle 6.

## Go Principles

These are the Go-specific deltas. Each pairs the rule with a concrete BAD -> why -> GOOD fix.

1. **Accept interfaces, return structs.** Define an interface at the *consumer*, naming what it needs, not at the producer describing what it has. One-method interfaces are the norm; a wide interface is a smell.

   ```go
   // BAD: the producer exports an interface mirroring its own type
   type Storer interface {
       Save(context.Context, Record) error
       Load(context.Context, string) (Record, error)
       Delete(context.Context, string) error
       List(context.Context) ([]Record, error)
   }

   func NewStore() Storer { return &fileStore{} }

   // why: every consumer takes all four methods to use one, the interface
   // duplicates the struct, and NewStore hides the concrete type its caller
   // may legitimately need.

   // GOOD: return the struct; each consumer declares the narrow interface it uses
   func NewStore() *FileStore { return &FileStore{} }

   // in the package that only reads:
   type recordLoader interface {
       Load(context.Context, string) (Record, error)
   }

   func Render(ctx context.Context, l recordLoader, id string) (string, error) { ... }
   ```

2. **Wrap errors with context; reach for a sentinel or type only when a caller must branch.** `fmt.Errorf("verb noun: %w", err)` is the default. The message names the operation that failed, lowercase, no trailing punctuation, and never repeats the word "error".

   ```go
   // BAD: context lost, or a sentinel nobody compares against
   if err != nil {
       return err
   }
   var ErrFailed = errors.New("failed")   // no caller ever tests for it

   // why: the caller gets "no such file or directory" with no idea which file
   // or which step, and an unused sentinel is API surface with no purpose.

   // GOOD: wrap with the operation and the subject
   raw, err := os.ReadFile(path)
   if err != nil {
       return fmt.Errorf("read %s: %w", path, err)
   }
   ```

   Define `ErrNotFound` and friends only when a caller genuinely does `errors.Is`. Use a custom error type when the caller needs a *field* from the failure, and pair it with `errors.As`.

3. **Make the zero value useful.** A struct usable as `var b Buffer` beats one requiring a constructor. Add a `New` only when construction must validate, must acquire something, or must set a non-zero default.

   ```go
   // BAD: a constructor whose only job is to fill in what the zero value implies
   func NewCounter() *Counter { return &Counter{counts: map[string]int{}} }

   // why: forces a constructor call, and `var c Counter` panics on first write,
   // which is a trap the type could simply not have.

   // GOOD: lazily initialize, so the zero value works
   func (c *Counter) Add(key string) {
       if c.counts == nil {
           c.counts = map[string]int{}
       }
       c.counts[key]++
   }
   ```

4. **`context.Context` is the first parameter of anything that blocks, and it is never stored in a struct.** Pass it down; do not stash it. Never pass `nil`; use `context.TODO()` while a call chain is still being wired.

   ```go
   // BAD: context as a field
   type Client struct { ctx context.Context; hc *http.Client }

   // why: the context's lifetime now belongs to the client rather than to the
   // call, so cancellation and deadlines apply to the wrong scope.

   // GOOD: context per call
   func (c *Client) Fetch(ctx context.Context, url string) (*Response, error) { ... }
   ```

5. **The goroutine's owner decides when it stops, and every one has a defined exit.** Never start a goroutine without knowing what closes it. Prefer a channel closed by the sender and a `context` for cancellation over a shared flag with a mutex.

   ```go
   // BAD: fire and forget
   go process(items)

   // why: nothing waits for it, nothing cancels it, a panic inside kills the
   // process, and the function returns before the work is observable.

   // GOOD: bounded lifetime the caller controls
   g, ctx := errgroup.WithContext(ctx)
   for _, item := range items {
       g.Go(func() error { return process(ctx, item) })
   }
   if err := g.Wait(); err != nil { ... }
   ```

   Guard shared state with a mutex held for the shortest possible span, and prefer passing values on a channel to sharing memory at all.

6. **Pass arguments; introduce an options struct only past four, or when most are optional.** Go prefers explicit call sites. When a struct is warranted, use a plain `Options` struct with meaningful zero values before reaching for functional options.

   ```go
   // BAD: functional options for a two-field constructor
   NewServer(WithPort(8080), WithTimeout(5*time.Second))

   // why: three exported symbols and a variadic signature to express what two
   // parameters already say.

   // GOOD
   NewServer(8080, 5*time.Second)
   // and past four, or when callers set two of nine:
   NewServer(ServerOptions{Port: 8080, Timeout: 5 * time.Second})
   ```

7. **Name for the call site, and let the package carry half the meaning.** `chunk.New` not `chunk.NewChunk`; `http.Get` not `http.HTTPGet`. Short receiver and local names (`c`, `f`, `buf`) are correct in Go, where the universal "length matches scope" rule points the same way. Getters drop the `Get` prefix.

   ```go
   // BAD
   package config
   func GetConfigValue(cfg *Config) string { ... }

   // why: reads as config.GetConfigValue, stuttering the package name twice.

   // GOOD
   package config
   func (c *Config) Value() string { ... }   // config.Value()
   ```

8. **Every exported identifier has a doc comment that starts with its own name and is a complete sentence.** This is not decoration: it is what `go doc` renders, so it is the package's API documentation. It states what the function does, what it returns on failure, and any constraint a caller cannot see from the signature.

   ```go
   // BAD
   // gets the value
   func ConfigValue(path, key, defaultValue string) string { ... }

   // GOOD
   // ConfigValue reads key from the named config file. Returns defaultValue if
   // the file is missing or the key is absent. The file is parsed line by line,
   // never sourced, so command substitutions in values are inert.
   func ConfigValue(path, key, defaultValue string) string { ... }
   ```

   This is the one place Go asks for more comment than the injected core's "comment only the why". The core still governs comments *inside* function bodies.

9. **`defer` the cleanup on the line after you acquire the thing.** Acquisition and release stay adjacent, so no later `return` can skip it.

   ```go
   // BAD: close at the end of a function with three returns
   f, err := os.Open(path)
   if err != nil { return err }
   // ... 30 lines, two early returns ...
   f.Close()

   // GOOD
   f, err := os.Open(path)
   if err != nil {
       return err
   }
   defer f.Close()
   ```

   When the close error matters (a file you wrote to), assign it to a named return in a deferred closure rather than dropping it.

10. **Return early and keep the happy path at the leftmost indentation.** Handle each error as it appears; never build an `else` around the success case. This is the step-down rule from the core, and Go's error returns make it mechanical.

    ```go
    // BAD
    if err == nil {
        if v, ok := m[k]; ok {
            return process(v)
        } else {
            return "", errMissing
        }
    } else {
        return "", err
    }

    // GOOD
    if err != nil {
        return "", err
    }
    v, ok := m[k]
    if !ok {
        return "", errMissing
    }
    return process(v)
    ```

11. **Use the standard library, and treat a new dependency as a decision to justify.** Go's standard library covers HTTP, JSON, templating, testing, and structured logging (`log/slog`). Reach outside it for something genuinely hard, not for convenience. A single-purpose helper is usually twenty lines you own instead of a module you track.

## Tests

Test *style* lives in `style-testing`, which is language-agnostic and applies here in full. Load it alongside this skill for any `*_test.go` file. Only the Go spellings belong below.

- **Table-driven by default.** A `[]struct` of named cases with `t.Run(c.name, ...)` per case, so a failure names itself.
- **Standard library only.** `testing` plus `if got != want { t.Errorf(...) }`. Reach for a comparison helper (`cmp.Diff`) on deep structures; do not import an assertion DSL.
- **`t.Helper()`** in any helper that calls `t.Fatal` or `t.Error`, so the failure points at the caller's line.
- **`t.Cleanup`** over a trailing teardown, and `t.TempDir` over a hand-rolled temp directory.
- **`t.Parallel()`** when a test is genuinely independent, and never when it shares mutable state.
- **Error assertions use `errors.Is`/`errors.As`**, never a string comparison of `err.Error()`.
- **`_test` package suffix** (`package foo_test`) when you want to test only the exported API, which is the better default for a package's contract.

```go
func TestParseLine(t *testing.T) {
    cases := []struct {
        name    string
        input   string
        want    Token
        wantErr error
    }{
        {name: "done with id", input: "DONE abc", want: TokenDone},
        {name: "empty input", input: "", wantErr: ErrEmpty},
    }
    for _, c := range cases {
        t.Run(c.name, func(t *testing.T) {
            got, err := ParseLine(c.input)
            if !errors.Is(err, c.wantErr) {
                t.Fatalf("err = %v, want %v", err, c.wantErr)
            }
            if got != c.want {
                t.Errorf("got %v, want %v", got, c.want)
            }
        })
    }
}
```

## Tooling

Prefer the command the project declares (a `Makefile` target, a `Taskfile`, or what its `AGENTS.md` names) over the generic form. Run them in this order; each catches what the previous cannot.

| Step | Command | What it settles |
|---|---|---|
| Format | `gofmt -l -w .` (or `goimports -w .`) | Layout and import grouping. Not negotiable. |
| Vet | `go vet ./...` | Suspicious constructs the compiler accepts: bad printf verbs, unused results, lost struct tags. |
| Static analysis | `staticcheck ./...` | Dead code, inefficiencies, misused stdlib. Pin the version so local and CI agree. |
| Test | `go test ./...`, then `go test -race ./...` | Behavior, then data races. A concurrency change without `-race` is unverified. |

`golangci-lint run` is a reasonable substitute for vet plus staticcheck when the project already configures it. Do not introduce it where a `Makefile` already pins the individual tools.

## Review Checklist

Work through these when reviewing Go:

- [ ] Interfaces are declared where they are consumed, and are narrow (one or two methods).
- [ ] Constructors return concrete types, not interfaces.
- [ ] Every error is either wrapped with the failing operation or deliberately handled; none is dropped with `_`.
- [ ] Sentinels and error types exist only where a caller branches on them.
- [ ] The zero value is either useful or the type documents why it needs a constructor.
- [ ] `context.Context` is the first parameter of every blocking call, and no struct stores one.
- [ ] Every goroutine has a defined exit, and shared state is guarded.
- [ ] Exported identifiers have doc comments beginning with their own name.
- [ ] Cleanup is deferred adjacent to acquisition.
- [ ] The happy path is leftmost; no `else` wraps the success case.
- [ ] Tests are table-driven, use the standard library, and compare errors with `errors.Is`.
- [ ] `gofmt`, `go vet`, and `staticcheck` are clean, and `go test -race` passes.

## Anti-Patterns

| Anti-pattern | Why it hurts | Instead |
|---|---|---|
| `interface{}` / `any` in a signature | Moves a compile-time error to runtime | A concrete type, or a type parameter |
| Naked `return` in a function with named results | The reader cannot see what is returned | Return the values explicitly |
| `panic` on an expected failure | Kills the process for something a caller could handle | Return an error |
| Ignoring an error with `_` | Silences the one signal that something broke | Handle it, or comment why it cannot fail |
| A `utils` or `common` package | Names a location, not a responsibility; grows without bound | Name the package for what it does |
| Getter/setter pairs on every field | Ceremony Go does not ask for | Export the field, or add behavior instead of accessors |
| `time.Sleep` to coordinate goroutines | Flaky by construction | Channels, `sync.WaitGroup`, or `errgroup` |
| A mutex guarding a whole struct for one field | Serializes unrelated work | Guard the narrowest span, or pass values on a channel |
