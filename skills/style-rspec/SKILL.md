---
name: style-rspec
description: Use when writing or reviewing RSpec tests in Rails apps - enforces request specs, let/let!/subject setup, context-driven organization, and DRY conventions
---

# Templeton RSpec Style

An opinionated RSpec-on-Rails testing style: request specs over controller tests, all setup in `let`/`let!`/`subject`, concise `it` blocks, and context-driven organization. This skill is RSpec/Rails specifics; the universal style core applies loosely on top.

## When to Use / When NOT to Use

Use when:

- Writing new RSpec tests for Rails applications.
- Converting controller tests to request specs.
- Refactoring existing tests to follow this style.
- Reviewing test code for style compliance.
- You need concrete examples of proper request-spec structure.

Do NOT use when:

- Testing non-Rails Ruby (e.g. a plain gem, a Sinatra service): request-spec conventions like `post resource_path` and `have_http_status` do not apply; lean on the universal core only.
- The project uses a different test framework (Minitest, `test/`-style integration tests): these are RSpec-specific deltas.
- You are told not to touch a legacy controller-spec-only suite: do not rewrite specs into request specs against instruction; honor the existing pattern.
- Setup truly cannot be hoisted (e.g. randomized per-example fixtures where lazy `let` would change behavior): prefer correctness over the rule.

## Universal Core (injected)

The "TRUE code" posture and nine universal principles are injected separately each session from `hooks/style-core.md`. Do not restate them. In testing terms they show up as: DRY setup is "wait for duplication before abstracting" (extract to shared `let`/contexts once repetition is real), and concise `it` blocks are "small single-purpose units." Everything below is the RSpec/Rails delta.

## RSpec Principles

1. **Write request specs, never controller tests.** Exercise the real HTTP stack so routing, middleware, and rendering are covered.

   ```ruby
   # BAD - controller spec
   describe ResourcesController, type: :controller do
     it "creates" do
       post :create, params: { resource: { title: "X" } }
       expect(response).to be_successful
     end
   end

   # GOOD - request spec
   describe "POST /resources" do
     subject { post resources_path, params: { resource: { title: "X" } } }

     it "returns success" do
       subject
       expect(response).to be_successful
     end
   end
   ```

2. **Put the HTTP request in `subject`.** The action under test belongs in one place, named `subject`, not inline in every `it`.

   ```ruby
   # BAD - request inline in the example
   it "creates" do
     post invitations_path, params: { invitation: invitation_params }
     expect(response).to be_successful
   end

   # GOOD - request lives in subject
   subject { post invitations_path, params: { invitation: invitation_params } }
   ```

3. **Do all data setup in `let`/`let!`, never create records inside `it`.** Scenario state is declarative setup, not procedural example code.

   ```ruby
   # BAD - record created inside the example
   it "does something" do
     resource = create(:resource)
     post resource_path
     expect(response).to be_successful
   end

   # GOOD - setup hoisted to let!
   let!(:resource) { create(:resource) }
   subject { post resource_path }

   it "does something" do
     subject
     expect(response).to be_successful
   end
   ```

4. **Keep `it` blocks concise: `subject` plus one expectation cluster.** Split unrelated assertions into separate examples.

   ```ruby
   # BAD - one example asserts many unrelated things
   it "works" do
     expect { subject }.to change(Item, :count).by(1)
     expect(response).to have_http_status(:created)
     expect(Item.find_by(title: "Test").description).to eq("Description")
   end

   # GOOD - one cluster per example
   it "creates the item" do
     expect { subject }.to change(Item, :count).by(1)
   end

   it "returns created status" do
     subject
     expect(response).to have_http_status(:created)
   end
   ```

5. **Organize by `context`, named "when.../with.../for...".** Each context describes one scenario; avoid vague names.

   ```ruby
   # BAD - vague context names
   context "it works" do
   context "bad data" do

   # GOOD - precise, pattern-named contexts
   context "when user is unauthorized" do
   context "with missing email field" do
   context "for admin users" do
   ```

6. **Prefer `build`/`build_stubbed` over `create` when persistence is not needed.** Hit the database only when the test actually depends on it.

   ```ruby
   # BAD - persists when only validation is exercised
   let(:invalid_user) { create(:user, email: nil) }

   # GOOD - unsaved instance for validation, stub for fast unit tests
   let(:invalid_user) { build(:user, email: nil) }
   let(:user) { build_stubbed(:user) }
   # use create only when persistence/queries/associations matter
   let!(:user) { create(:user) }
   ```

7. **Prefer lazy `let` over eager `let!`; reserve `let!` for records that must exist before the action.** Lazy evaluation saves DB hits in examples that never touch the record.

   ```ruby
   # BAD - created even in examples that never use it
   let!(:admin) { create(:user, :admin) }

   # GOOD - lazy; created only where referenced
   let(:admin) { create(:user, :admin) }

   # GOOD - eager, because the query must find it
   let!(:existing_user) { create(:user, email: "test@example.com") }
   subject { User.find_by(email: "test@example.com") }
   ```

8. **Verify created records with `find_by(unique_attr)`, never `Model.last` or `where(...).last`.** You cannot assume your record is the only one or the last one in the table.

   ```ruby
   # BAD - which record is "last"?
   it "creates the invitation" do
     subject
     expect(Invitation.last).to have_attributes(params)
   end

   # BAD - where().last is needlessly indirect
   it "creates the invitation" do
     subject
     new_invitation = Invitation.where(email: "new@example.com").last
     expect(new_invitation).to be_present
   end

   # GOOD - find the specific record by a unique attribute
   it "creates the invitation" do
     subject
     expect(Invitation.find_by(email: "new@example.com")).to be_present
   end
   ```

9. **Define shared-example variables at the `describe` level.** Any variable referenced by `subject` or an `it_behaves_like` must be visible to every context that invokes it.

   ```ruby
   # BAD - invitation_params only exists in one context
   describe "POST /deals/:deal_id/invitations" do
     let(:deal) { create(:deal) }
     subject { post deal_invitations_path(deal), params: { invitation: invitation_params } }

     context "when user is authorized" do
       let(:invitation_params) { { email: "test@example.com" } }
       it_behaves_like "creates an invitation"
     end
   end

   # GOOD - shared vars hoisted to describe level
   describe "POST /deals/:deal_id/invitations" do
     let(:deal) { create(:deal) }
     let(:invitation_params) { { email: "test@example.com", role: "viewer" } }
     subject { post deal_invitations_path(deal), params: { invitation: invitation_params } }

     context "when user is authorized" do
       it_behaves_like "creates an invitation"
     end

     context "when email is taken" do
       let!(:existing) { create(:invitation, email: "test@example.com") }
       it_behaves_like "rejects duplicate invitation"
     end
   end
   ```

10. **Set up nested-resource parents with `let!` at the describe level and use nested path helpers.** The parent must exist before the child action, and the route must be addressed through its helper.

    ```ruby
    # BAD - parent not persisted; flat path helper for a nested route
    describe "POST /deals/:deal_id/invitations" do
      let(:deal) { build(:deal) }
      subject { post invitations_path, params: { invitation: invitation_params } }
    end

    # GOOD - parents created with let!, nested path helper
    describe "POST /deals/:deal_id/invitations" do
      let!(:organization) { create(:organization) }
      let!(:deal) { create(:deal, organization: organization) }
      let(:invitation_params) { { email: "test@example.com", role: "viewer" } }
      subject { post deal_invitations_path(deal), params: { invitation: invitation_params } }
    end
    ```

## Anti-Patterns

- **Creating records inside `it` blocks.**
  - Why: setup state is implicit and re-runs per example; it hides scenario differences and bloats examples.
  - Fix: move creation into `let`/`let!`.

  ```ruby
  # BAD
  it "does something" do
    resource = create(:resource)
    expect(resource).to be_valid
  end

  # GOOD
  let(:resource) { build(:resource) }
  it "is valid" do
    expect(resource).to be_valid
  end
  ```

- **Making HTTP requests inside `it` blocks.**
  - Why: the action under test should be one named thing (`subject`), not repeated inline across examples.
  - Fix: hoist the request into `subject`, then call `subject` or `expect { subject }`.

  ```ruby
  # BAD
  it "creates" do
    post items_path, params: { item: params }
    expect(response).to have_http_status(:created)
  end

  # GOOD
  subject { post items_path, params: { item: params } }
  it "returns created" do
    subject
    expect(response).to have_http_status(:created)
  end
  ```

- **Long `it` blocks asserting many unrelated things.**
  - Why: a failure no longer tells you what broke, and the example name cannot describe one behavior.
  - Fix: one expectation cluster per example.

  ```ruby
  # BAD
  it "works" do
    expect { subject }.to change(Item, :count).by(1)
    expect(response).to have_http_status(:created)
  end

  # GOOD
  it "creates the item" do
    expect { subject }.to change(Item, :count).by(1)
  end
  it "returns created status" do
    subject
    expect(response).to have_http_status(:created)
  end
  ```

- **Controller tests instead of request specs.**
  - Why: controller specs skip routing, middleware, and real rendering, so they pass while the endpoint is broken.
  - Fix: rewrite as a request spec hitting the route via its path helper.

  ```ruby
  # BAD
  post :create, params: { resource: { title: "X" } }

  # GOOD
  post resources_path, params: { resource: { title: "X" } }
  ```

- **Repeating setup across multiple contexts.**
  - Why: drift between near-identical contexts produces false confidence and noisy diffs.
  - Fix: hoist shared `let`/`subject` to the enclosing `describe`; extract repeated behavior into shared examples (once duplication is real).

- **Using `create` when `build`/`build_stubbed` would suffice.**
  - Why: needless DB writes slow the suite and obscure what the test actually depends on.
  - Fix: `build` for validations, `build_stubbed` for pure unit tests, `create` only when persistence/queries/associations matter.

- **Asserting on `Model.last` (or `where(...).last`) for created records.**
  - Why: "last" is undefined when other rows exist or ordering changes, so the assertion checks the wrong record.
  - Fix: `Model.find_by(unique_attr)`.

  ```ruby
  # BAD
  expect(Invitation.last).to have_attributes(params)

  # GOOD
  expect(Invitation.find_by(email: params[:email])).to have_attributes(name: "New User")
  ```

## Worked Examples

### Record creation

```ruby
context "with valid params" do
  let(:params) { { title: "Test", description: "Description" } }
  subject { post items_path, params: { item: params } }

  it "creates the item" do
    expect { subject }.to change(Item, :count).by(1)
  end

  it "has correct attributes" do
    subject
    expect(Item.find_by(title: "Test")).to have_attributes(params)
  end

  it "returns created status" do
    subject
    expect(response).to have_http_status(:created)
  end
end
```

### Authorization

```ruby
context "when accessing another organization's resource" do
  let!(:other_org) { create(:organization) }
  let!(:other_resource) { create(:resource, organization: other_org) }

  subject { get resource_path(other_resource) }

  it "returns not found" do
    subject
    expect(response).to have_http_status(:not_found)
  end
end
```

### Duplicate prevention

```ruby
context "when email already exists" do
  let!(:existing_record) { create(:invitation, email: "test@example.com") }
  let(:params) { { email: "test@example.com" } }

  subject { post invitations_path, params: { invitation: params } }

  it "does not create a duplicate" do
    expect { subject }.not_to change(Invitation, :count)
  end

  it "returns unprocessable entity" do
    subject
    expect(response).to have_http_status(:unprocessable_entity)
  end
end
```

### Updates

```ruby
context "updating attributes" do
  let!(:resource) { create(:resource, title: "Old Title") }
  let(:new_params) { { title: "New Title" } }

  subject { patch resource_path(resource), params: { resource: new_params } }

  it "updates the title" do
    expect { subject }.to change { resource.reload.title }.from("Old Title").to("New Title")
  end

  it "returns success" do
    subject
    expect(response).to have_http_status(:ok)
  end
end
```

### Verifying with `find_by` instead of `Model.last`

```ruby
# Verify presence first, then check attributes on the specific record
context "with valid params" do
  let(:params) { { email: "new@example.com", name: "New User" } }
  subject { post invitations_path, params: { invitation: params } }

  it "creates the invitation" do
    subject
    expect(Invitation.find_by(email: "new@example.com")).to be_present
  end

  it "creates invitation with correct attributes" do
    subject
    invitation = Invitation.find_by(email: "new@example.com")
    expect(invitation).to have_attributes(name: "New User", status: "pending")
  end
end
```

### Nested resources

```ruby
describe "POST /deals/:deal_id/invitations" do
  # Parent resource setup
  let!(:organization) { create(:organization) }
  let!(:deal) { create(:deal, organization: organization) }

  # Nested resource params
  let(:invitation_params) { { email: "test@example.com", role: "viewer" } }

  # Subject uses nested path helper
  subject { post deal_invitations_path(deal), params: { invitation: invitation_params } }

  context "with valid params" do
    it "creates invitation associated with deal" do
      expect { subject }.to change(deal.invitations, :count).by(1)
    end

    it "has correct deal association" do
      subject
      expect(deal.invitations.find_by(email: "test@example.com").deal).to eq(deal)
    end
  end

  context "authorization" do
    context "when accessing another organization's deal" do
      let!(:other_deal) { create(:deal, organization: create(:organization)) }
      subject { post deal_invitations_path(other_deal), params: { invitation: invitation_params } }

      it "returns not found" do
        subject
        expect(response).to have_http_status(:not_found)
      end
    end
  end
end
```

### Shared examples with hoisted variables

```ruby
describe "POST /deals/:deal_id/invitations" do
  let(:deal) { create(:deal) }
  let(:invitation_params) { { email: "test@example.com", role: "viewer" } }

  subject { post deal_invitations_path(deal), params: { invitation: invitation_params } }

  context "when user is authorized" do
    it_behaves_like "creates an invitation"
  end

  context "when email is taken" do
    let!(:existing) { create(:invitation, email: "test@example.com") }
    it_behaves_like "rejects duplicate invitation"
  end
end
```

## Apply Workflow

1. **Understand the feature.** What behavior is under test, and which endpoint exercises it?
2. **Identify contexts.** Enumerate the scenarios/conditions that need coverage (valid, invalid, unauthorized, duplicate, ...).
3. **Plan the structure.** Decide what setup is shared (hoist to `describe`) versus what varies per context. Set up nested-resource parents with `let!`.
4. **Write request specs.** Put the HTTP call in `subject`; never write controller tests.
5. **Fill in setup with `let`/`let!`.** Prefer lazy `let`; use `let!` only when the record must exist first. Prefer `build`/`build_stubbed` over `create` when persistence is not needed.
6. **Write concise examples.** One expectation cluster per `it`; call `subject` or `expect { subject }`. Verify created records with `find_by(unique_attr)`.
7. **Keep it DRY.** Once duplication is real, extract shared `let`/contexts or shared examples (variables defined at `describe` level).

## Quality Checklist

- [ ] These are request specs, not controller tests.
- [ ] No records are created inside `it` blocks (all in `let`/`let!`).
- [ ] No HTTP requests inside `it` blocks (the action lives in `subject`).
- [ ] Each `it` asserts one expectation cluster, not many unrelated things.
- [ ] Contexts are named "when.../with.../for..." and describe one scenario each.
- [ ] `build`/`build_stubbed` used wherever persistence is not required; `create` reserved for persistence/queries/associations.
- [ ] Lazy `let` preferred; `let!` only where the record must exist before the action.
- [ ] Created records verified with `find_by(unique_attr)`, never `Model.last` or `where(...).last`.
- [ ] Shared-example and `subject` variables are defined at the `describe` level.
- [ ] Nested-resource parents set up with `let!` and addressed via nested path helpers.
- [ ] Shared setup is hoisted; no needless repetition across contexts.
