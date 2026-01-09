---
name: rails-rspec-tester
description: Use when writing RSpec tests in Rails applications - enforces opinionated testing style with request specs, context-driven organization, and DRY principles
---

# RSpec Rails Tester

A specialized agent for writing RSpec tests in Rails applications following a specific, opinionated style.

## Core Testing Philosophy

- **Request specs over controller tests**: Always write request specs, never controller tests
- **Setup outside `it` blocks**: All data creation and scenario setup happens in `let`, `let!`, or `subject` blocks
- **Concise assertions**: The `it` block should only contain `subject` (if needed) and the expectation
- **Context-driven organization**: Use `context` blocks to describe scenarios, typically starting with "when..."
- **DRY principles**: Avoid repetition; extract common setup to shared contexts or higher-level `let` blocks
- **Smart factory usage**: Prefer `build` and `build_stubbed` over `create` when appropriate (when persistence isn't required)

## Test Structure Pattern

### Good Pattern

```ruby
context "when condition exists" do
  let!(:resource) { create(:resource, attribute: value) }
  let(:params) { { key: "value" } }

  subject { post resource_path, params: params }

  it "performs the expected action" do
    expect { subject }.to change(Model, :count).by(1)
  end

  it "has the correct attributes" do
    subject
    expect(Model.last).to have_attributes(key: "value")
  end
end
```

### Bad Pattern (Never Do This)

```ruby
it "does something" do
  resource = create(:resource)  # NO - create should be in let!
  post resource_path            # NO - request should be in subject
  expect(response).to be_successful
end
```

## Key Rules

1. **HTTP requests go in `subject` blocks**
   ```ruby
   subject { post invitations_path, params: { invitation: invitation_params } }
   ```

2. **Data setup uses `let` or `let!`**
   - Use `let!` when the record must exist before the action
   - Use `let` for lazy evaluation
   - Use `build`/`build_stubbed` when persistence isn't needed

3. **Context blocks describe scenarios**
   ```ruby
   context "when user is unauthorized" do
   context "when email is duplicate" do
   context "with invalid params" do
   ```

4. **`it` blocks are concise**
   ```ruby
   it "creates the record" do
     expect { subject }.to change(Model, :count).by(1)
   end

   it "returns success status" do
     subject
     expect(response).to have_http_status(:ok)
   end
   ```

5. **Call `subject` explicitly when needed**
   - Use `expect { subject }` for testing changes
   - Call `subject` before assertions that check the result state

## Common Scenarios

### Testing Record Creation

```ruby
context "with valid params" do
  let(:params) { { title: "Test", description: "Description" } }
  subject { post items_path, params: { item: params } }

  it "creates the item" do
    expect { subject }.to change(Item, :count).by(1)
  end

  it "has correct attributes" do
    subject
    expect(Item.last).to have_attributes(params)
  end

  it "returns created status" do
    subject
    expect(response).to have_http_status(:created)
  end
end
```

### Testing Authorization

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

### Testing Duplicate Prevention

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

### Testing Updates

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

## Factory Usage Guidelines

### Factory Methods

- **`create`**: When the record must be persisted (testing relationships, associations, queries)
- **`build`**: When you need an unsaved instance (testing validations, before callbacks)
- **`build_stubbed`**: When you need an instance that appears persisted but isn't (fast unit tests)

```ruby
# Use create when testing persistence or queries
let!(:user) { create(:user) }

# Use build when testing validations
let(:invalid_user) { build(:user, email: nil) }

# Use build_stubbed for unit tests that don't touch the database
let(:user) { build_stubbed(:user) }
```

### `let` vs `let!` Strategy

Choose between `let` and `let!` based on when the record needs to exist:

- **Use `let!` with `create`** when the record must exist before the action (testing queries, associations, authorization checks)
- **Use `let` with `create`** when the record is only needed in some examples (saves DB hits by lazy-loading)
- **Prefer `let` over `let!`** when possible for performance

```ruby
# Good - record must exist for the query to find it
let!(:existing_user) { create(:user, email: "test@example.com") }
subject { User.find_by(email: "test@example.com") }

# Good - lazy evaluation, only creates when needed
let(:admin) { create(:user, :admin) }

context "when user is admin" do
  before { sign_in(admin) }  # Only creates admin in this context
  # ...
end

# Bad - using let! when let would suffice
let!(:admin) { create(:user, :admin) }  # Created even if never used
```

## Working with Shared Examples

When using shared examples with `it_behaves_like`, ensure all variables referenced in `subject` or the shared example are defined at the `describe` level or higher, not within individual `context` blocks.

```ruby
# Good - variables defined at describe level
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

# Bad - invitation_params only available in one context
describe "POST /deals/:deal_id/invitations" do
  let(:deal) { create(:deal) }
  subject { post deal_invitations_path(deal), params: { invitation: invitation_params } }

  context "when user is authorized" do
    let(:invitation_params) { { email: "test@example.com" } }  # ❌ Not available to other contexts
    it_behaves_like "creates an invitation"
  end
end
```

**Key principle**: Variables used in `subject` must be accessible from all contexts that call `subject`. Define them at the appropriate scope level.

## Verifying Newly Created Records

When asserting on newly created records, query for the specific record by its unique attributes rather than relying on `Model.last`, which is unreliable when multiple records might exist in the table.

```ruby
# Good - find by unique attribute to verify the specific record
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
    expect(invitation).to have_attributes(
      name: "New User",
      status: "pending"
    )
  end
end

# Also good - verify presence first, then check attributes
it "creates invitation with correct attributes" do
  subject
  expect(Invitation.find_by(email: params[:email])).to be_present
  expect(Invitation.find_by(email: params[:email])).to have_attributes(name: "New User")
end

# Bad - Model.last is unreliable when multiple records exist
it "creates invitation with correct attributes" do
  subject
  expect(Invitation.last).to have_attributes(params)  # ❌ Which record is "last"?
end

# Bad - where().last is unnecessarily complex
it "creates the invitation" do
  subject
  new_invitation = Invitation.where(email: "new@example.com").last  # ❌ Just use find_by
  expect(new_invitation).to be_present
end
```

**Best practices**:
- **Always use `find_by` with a unique attribute** (email, reference ID, unique combination)
- **Never use `Model.last`** - you can't assume the table has only one record or that yours is last
- Use `be_present` to verify the record exists with the unique attribute
- Use `have_attributes` for additional attribute verification after finding the specific record
- Avoid `where().last` - `find_by` is clearer and more direct

## Context Naming Conventions

Use consistent, descriptive naming patterns for context blocks:

```ruby
# Use "when [condition/state]" for scenarios and states
context "when user is authenticated" do
context "when record already exists" do
context "when email is invalid" do
context "when deal is archived" do

# Use "with [parameters/data]" for parameter variations
context "with valid params" do
context "with invalid email" do
context "with missing required fields" do
context "with admin privileges" do

# Use specific domain terms for authorization contexts
context "authorization" do
  context "when accessing own organization's resource" do
  context "when accessing another organization's resource" do
  context "when user lacks required role" do
end

# Use "for [actor/role]" when testing role-based behavior
context "for admin users" do
context "for guest users" do
context "for organization owners" do
```

**Avoid vague names**: Instead of "when it works" use "when params are valid". Instead of "bad data" use "with missing email field".

## Testing Nested Resources

When testing nested resources (routes like `/deals/:deal_id/invitations`), ensure parent resources are properly set up:

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
      expect(Invitation.last.deal).to eq(deal)
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

**Key patterns**:
- Set up parent resources with `let!` at the describe level
- Use nested path helpers (`deal_invitations_path(deal)`)
- Test associations between child and parent
- Test authorization on parent resources

## Before You Write Tests

1. **Understand the feature**: What behavior are you testing?
2. **Identify contexts**: What scenarios/conditions need coverage?
3. **Plan the structure**: What setup is shared? What varies per context?
4. **Write request specs**: Never controller tests
5. **Keep it DRY**: Extract common setup; avoid repetition

## Red Flags to Avoid

- ❌ Creating records inside `it` blocks
- ❌ Making HTTP requests inside `it` blocks
- ❌ Long `it` blocks with multiple assertions on unrelated things
- ❌ Controller tests (use request specs instead)
- ❌ Repeating setup across multiple contexts
- ❌ Using `create` when `build` or `build_stubbed` would suffice

## When to Use This Skill

Use this skill when:
- Writing new RSpec tests for Rails applications
- Converting controller tests to request specs
- Refactoring existing tests to follow this style
- Reviewing test code for style compliance
- Need examples of proper test structure

The agent will analyze your code, understand the feature being tested, and generate well-structured, concise RSpec tests following these exact patterns.
