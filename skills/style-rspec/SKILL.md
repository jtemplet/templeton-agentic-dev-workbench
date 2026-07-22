---
name: style-rspec
description: Use when writing or reviewing RSpec tests in a Rails app - the RSpec/Rails delta on the style-testing core, covering request specs over controller specs, let/let!/subject mechanics, FactoryBot build vs create, and shared-example scoping
---

# Templeton RSpec Style

**This skill extends `style-testing`, the universal testing core. Load that first.** It owns the
principles (one behavior per case, hoisted declarative setup, deterministic identification and
clocks, scenario-named groups, what not to test). This file owns only the RSpec-on-Rails spelling
of those principles, plus the handful of Rails concerns that have no framework-free equivalent. If
a rule here would still read as correct advice with the RSpec nouns stripped out, it belongs in
`style-testing`, not here.

## When to Use / When NOT to Use

Use when:

- Writing or reviewing RSpec specs in a Rails application.
- Converting controller specs to request specs.

Do NOT use when:

- Testing non-Rails Ruby (a plain gem, a Sinatra service): request-spec conventions like
  `post resource_path` and `have_http_status` do not apply. Use `style-testing` alone.
- The project uses Minitest or `test/`-style integration tests. Use `style-testing` alone.

## How the core is spelled in RSpec

| `style-testing` principle | RSpec/Rails spelling |
|---|---|
| 1, test at the outermost fast seam | A **request spec**, never a controller spec. Controller specs skip routing, middleware, and real rendering, so they pass while the endpoint is broken. |
| 2, name the action once | Put the HTTP call in `subject`, then call `subject` or `expect { subject }`. |
| 3, declarative hoisted setup | All data setup in `let`/`let!`. Never `create` inside an `it` block. |
| 5, scenario groups | `context` blocks named `"when ..."`, `"with ..."`, `"for ..."`. |
| 6, lightest sufficient fixture | `build_stubbed` for pure unit work, `build` for validations, `create` only when persistence, queries, or associations matter. |
| 7, lazy unless ordering matters | Lazy `let` by default; `let!` only when the record must exist before the action runs. |
| 8, identify by unique key | `Model.find_by(unique_attr)`, never `Model.last` or `where(...).last`. |
| 9, shared setup visible to every case | Variables referenced by `subject` or `it_behaves_like` are defined at the `describe` level, not inside one `context`. |
| 10, prerequisites exist, real addressing | Nested-resource parents created with `let!` at the `describe` level, addressed via nested path helpers (`deal_invitations_path(deal)`), never a hand-built string. |
| 11, injected clock | `travel_to` / `freeze_time` from ActiveSupport::Testing::TimeHelpers. |

## RSpec-Only Concerns

These have no framework-free parent; they are genuinely Rails mechanics.

1. **`let!` forces evaluation; `let` is lazy and memoized per example.** This is the mechanism
   behind principle 7. `let!` is `let` plus an implicit `before`, so it runs even in examples that
   never reference it. That is why the default is `let`.

   ```ruby
   # GOOD - lazy, built only where referenced
   let(:admin) { create(:user, :admin) }

   # GOOD - eager, because the query under test must find it
   let!(:existing_user) { create(:user, email: "test@example.com") }
   subject { User.find_by(email: "test@example.com") }
   ```

2. **`expect { subject }` versus `subject`.** Use the block form when asserting on a *change*
   (`change(Item, :count).by(1)`), and the bare call when asserting on the resulting `response`.
   Calling `subject` twice in one example issues the request twice.

3. **FactoryBot's three build strategies are not interchangeable.** `build_stubbed` fakes an ID and
   never touches the database, `build` leaves an unsaved instance, `create` persists. Validation
   specs want `build`; anything asserting on a query wants `create`.

4. **`it_behaves_like` resolves variables at the point of *invocation*, not definition.** A shared
   example referencing `invitation_params` fails in any `context` that does not define it, which is
   why principle 9's "visible to every case" means the `describe` level here.

## Worked Example

```ruby
describe "POST /deals/:deal_id/invitations" do
  let!(:organization)     { create(:organization) }
  let!(:deal)             { create(:deal, organization: organization) }
  let(:invitation_params) { { email: "test@example.com", role: "viewer" } }

  subject { post deal_invitations_path(deal), params: { invitation: invitation_params } }

  context "with valid params" do
    it "creates the invitation" do
      expect { subject }.to change(Invitation, :count).by(1)
    end

    it "returns created status" do
      subject
      expect(response).to have_http_status(:created)
    end

    it "persists the submitted attributes" do
      subject
      expect(Invitation.find_by(email: "test@example.com")).to have_attributes(role: "viewer")
    end
  end

  context "when the email is already invited" do
    let!(:existing) { create(:invitation, deal: deal, email: "test@example.com") }

    it "does not create a duplicate" do
      expect { subject }.not_to change(Invitation, :count)
    end
  end
end
```

## Quality Checklist

Apply `style-testing`'s checklist first. Then, RSpec-specific:

- [ ] These are request specs, not controller specs.
- [ ] The HTTP call lives in `subject`; no request is issued inside an `it` block.
- [ ] No records are created inside `it` blocks; all setup is in `let`/`let!`.
- [ ] `build`/`build_stubbed` used wherever persistence is not required.
- [ ] `let!` used only where the record must exist before the action.
- [ ] Created records verified with `find_by(unique_attr)`, never `Model.last`.
- [ ] Variables used by `subject` or `it_behaves_like` are defined at the `describe` level.
- [ ] Nested-resource parents are created with `let!` and addressed via nested path helpers.
