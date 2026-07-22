---
name: review-rails
description: Use when reviewing Rails 8 code before merge or PR - systematic review process covering security (XSS, SQL injection, authorization), Rails/Hotwire conventions, performance, and DRY with verify-before-flag discipline and priority-ranked findings
---

# Rails Code Review Technique

Systematic process for reviewing Ruby on Rails 8 code, prioritizing issues by impact (Critical to Low) and providing actionable fixes. Core principles: verify before flagging (if tests pass, verify claims before marking as issues); security first (actual vulnerabilities over theoretical concerns); pragmatic over pure (working non-standard code beats non-working standard code); context matters (understand Rails 8 patterns and modern conventions).

## When to Use / When NOT to Use

Use this skill when:

- Reviewing code before merging to main branch
- Creating or reviewing pull requests
- Performing pre-deployment code audits
- Reviewing changes that touch views, controllers, or models
- Investigating security vulnerabilities
- Optimizing Rails application performance

Don't use this for:

- Initial exploratory coding (too early)
- Non-Rails Ruby code
- Infrastructure/deployment configs (use other skills)
- Simple typo fixes or documentation updates

## Universal Core (injected)

The universal style core ("TRUE code" plus the 9 principles and the correctness-over-speed posture) is injected separately each session from `hooks/style-core.md`; apply it, do not restate it here. For Rails 8 *writing* conventions (the Rails Way, Solid Stack, Hotwire idioms), defer to the companion `style-rails` skill. For test style defer to `style-testing`, which owns the framework-independent principles, and additionally to `style-rspec` when the project's suite is RSpec. This skill owns the review *process*: security-first scanning, verify-before-flag discipline, and prioritized findings.

## Review Principles

Scan changes by category in priority order so critical issues surface first. Use this table as the at-a-glance map; the per-category checklists below expand each row.

| Category | Focus Areas | Priority | Red Flags |
|----------|-------------|----------|-----------|
| Security | XSS, unsafe rendering, SQL injection, mass assignment | Critical | `html_safe`, `raw`, direct SQL, `params` in queries |
| Rails Conventions | Rails 8 Way, Solid Stack, Hotwire patterns | High | Custom JavaScript when Hotwire works, ignoring conventions |
| Performance | N+1 queries, caching, unnecessary Turbo | High | Missing `includes`, no caching, Turbo frame without need |
| DRY | Duplicate code, repeated patterns, extraction opportunities | Medium | Copy-pasted blocks, repeated partials, duplicate helpers |
| CSS/Styling | Tailwind v4, redundant classes, unused utilities | Low | Inline styles, conflicting classes, non-Tailwind CSS |
| Browser Compat | CSS properties, vendor prefixes | Low | Modern-only features, missing fallbacks |

### Security (CRITICAL priority)

Check for:

- XSS vulnerabilities in HAML/ERB rendering
- Unsafe string interpolation or `html_safe` usage
- `raw()` method calls without sanitization
- Direct SQL queries vulnerable to injection
- Mass assignment issues in controllers
- Unvalidated user input rendering
- Missing CSRF protection on forms
- Missing authorization checks in public controllers

Common vulnerabilities:

```ruby
# BAD: XSS vulnerability
= raw(@user.bio)

# GOOD: Sanitized output
= sanitize(@user.bio, tags: %w[p br strong em])

# BAD: SQL injection
User.where("email = '#{params[:email]}'")

# GOOD: Parameterized query
User.where(email: params[:email])

# BAD: Missing authorization in public controller
class Public::DocumentsController < Public::BaseController
  def update
    document.update(params)  # No authorize check!
  end
end

# GOOD: Explicit authorization
class Public::DocumentsController < Public::BaseController
  def update
    authorize [:public, document], :update?
    document.update(params)
  end
end
```

### Rails Conventions & Best Practices (HIGH priority)

Check for:

- Following "The Rails 8 Way" patterns
- Using Solid Stack over external dependencies
- Proper Hotwire/Turbo usage (not custom JavaScript)
- Controllers returning proper responses
- Using native Rails methods instead of custom solutions
- Proper use of Rails helpers and concerns
- RESTful routing and controller actions
- Following ActiveRecord conventions

Rails 8 modern patterns (do not flag these as issues):

```ruby
# CORRECT: Rails 8 implicit Turbo Stream responses
def update
  @document.update(params)
  # Rails 8 + Turbo automatically handles response
  # No need for explicit respond_to or head :ok
end

# CORRECT: Modern where.missing syntax (Rails 7+)
scope :unassigned, -> { where.missing(:assignment) }

# CORRECT: broadcast_refresh_to for simple updates
broadcast_refresh_to(@deal)  # Intentional full page morph

# CORRECT: Concerns can be in app/models/model_name/
# File: app/models/document/fulfillable.rb
class Document
  module Fulfillable
    extend ActiveSupport::Concern
  end
end
```

Anti-patterns to flag:

```ruby
# BAD: Custom JavaScript when Hotwire works
<%= link_to "Delete", user_path(@user),
    data: { confirm: "Are you sure?", method: :delete } %>
<script>/* custom delete handler */</script>

# GOOD: Turbo handles this
<%= link_to "Delete", user_path(@user),
    data: { turbo_method: :delete, turbo_confirm: "Are you sure?" } %>

# BAD: Controller explicitly expects template but doesn't handle response
def create
  respond_to do |format|
    format.turbo_stream  # Expects template but no error handling
    # What if template doesn't exist?
  end
end

# GOOD: Explicit rendering or proper response
def create
  respond_to do |format|
    format.turbo_stream { render turbo_stream: turbo_stream.append(...) }
  end
rescue => e
  head :unprocessable_entity
end
```

### Performance & Optimization (HIGH priority)

Check for:

- N+1 query problems (missing `includes`, `preload`, `eager_load`)
- Opportunities for caching or memoization
- Unnecessary database queries in loops
- Missing database indexes for frequent queries
- Inefficient ActiveRecord queries
- Turbo Frames/Streams used when a simple redirect works
- Large payload responses

Performance issues:

```ruby
# BAD: N+1 query
@users.each do |user|
  user.posts.count  # Separate query for each user
end

# GOOD: Eager load
@users.includes(:posts).each do |user|
  user.posts.count  # Uses preloaded data
end

# BAD: Unnecessary complexity
respond_to do |format|
  format.turbo_stream  # For simple redirect
end

# GOOD: Simple redirect
redirect_to users_path, notice: "Created successfully"
```

### Code Duplication (MEDIUM priority)

Check for:

- Repeated code blocks (extract to partials)
- Repeated styling patterns (create shared component classes)
- Duplicate logic (move to helpers, concerns, or decorators)
- Similar views (use shared partials with locals)
- Repeated queries (extract to scopes or query objects)

DRY opportunities:

```haml
-# BAD: Repeated partial code
- @users.each do |user|
  .card.p-4.border.rounded
    .font-bold= user.name
    .text-gray-600= user.email

-# GOOD: Extract to partial
- @users.each do |user|
  = render 'user_card', user: user

-# _user_card.html.haml
.card.p-4.border.rounded
  .font-bold= user.name
  .text-gray-600= user.email
```

### CSS & Styling (LOW priority)

Check for:

- Using Tailwind v4 syntax only
- No custom CSS (utility-first approach)
- Redundant or conflicting Tailwind classes
- Unused Tailwind utilities that can be removed
- Inline styles (should use Tailwind)
- Proper responsive breakpoints
- Consistent spacing and sizing patterns

Styling issues:

```haml
-# BAD: Conflicting classes
.flex.block.p-4.p-6

-# GOOD: Consistent classes
.flex.p-6

-# BAD: Inline styles
%div{ style: "margin-top: 20px;" }

-# GOOD: Tailwind utilities
.mt-5

-# MINOR: Important flag (use sparingly)
.drop-zone[data-drop-target] {
  @apply bg-accent-purple/10! px-1 rounded-xl;
}

-# BETTER: Increase specificity
.drop-zone[data-drop-target] {
  @apply bg-accent-purple/10 px-1 rounded-xl;
}
```

### Bugs & Logic Issues (ALL priorities)

Check for:

- Logic errors or incorrect conditional logic
- Missing nil/null checks
- Missing error handling for external calls
- Race conditions in concurrent operations
- Incorrect data type handling
- Off-by-one errors in loops/ranges
- Missing edge case handling
- Methods that should return booleans but raise exceptions

Common issues:

```ruby
# BAD: Using bang method without error handling
def assign(document, requirement)
  document.update!(assignment: requirement)
  # Controller can't check success/failure
end

# GOOD: Return boolean for controller to check
def assign(document, requirement)
  document.update(assignment: requirement)
rescue ActiveRecord::RecordInvalid
  false
end

# Or provide both versions
def assign!(document, requirement)
  document.update!(assignment: requirement)
end

def assign(document, requirement)
  assign!(document, requirement)
  true
rescue ActiveRecord::RecordInvalid
  false
end
```

Specifically exclude (not a concern per project requirements):

- Accessibility issues
- ARIA attributes

### Browser Compatibility (LOW priority)

Check for:

- CSS properties requiring vendor prefixes
- JavaScript features needing polyfills
- Browser-specific CSS quirks
- Features not supported in target browsers

### Rails 8 Awareness: patterns you should NOT flag

These modern patterns are correct. Do not raise them as issues.

1. Implicit Turbo Stream responses

   ```ruby
   # This works in Rails 8 - no explicit response needed
   def update
     @resource.update(params)
   end
   ```

2. `where.missing` syntax (Rails 7+)

   ```ruby
   # Modern, readable, preferred
   scope :unassigned, -> { where.missing(:assignment) }
   ```

3. Concerns in model subdirectories

   ```ruby
   # Valid pattern: app/models/document/fulfillable.rb
   class Document
     module Fulfillable
       extend ActiveSupport::Concern
     end
   end
   ```

4. `broadcast_refresh_to` for simple updates

   ```ruby
   # Valid for public views - intentional full page morph
   broadcast_refresh_to(@deal)
   ```

5. Solid Stack components

   - Solid Queue (background jobs)
   - Solid Cache (caching)
   - Solid Cable (WebSockets)

## Anti-Patterns

The highest-signal Rails review smells, each as bad code, why it matters, then the corrected form.

XSS via `raw`:

```ruby
# BAD: renders unsanitized user content
= raw(@user.bio)
```

Why: `raw` (and `html_safe`) bypass Rails auto-escaping, so a crafted bio injects executable script into the page.

```ruby
# GOOD: allowlist the tags you intend to permit
= sanitize(@user.bio, tags: %w[p br strong em])
```

SQL injection via interpolation:

```ruby
# BAD: user input concatenated into raw SQL
User.where("email = '#{params[:email]}'")
```

Why: an attacker controls the SQL string and can read or destroy data.

```ruby
# GOOD: parameterized query lets ActiveRecord escape the value
User.where(email: params[:email])
```

Missing authorization in a public controller:

```ruby
# BAD: scoping is not authorization
def update
  document.update(params)
end
```

Why: public controllers are reachable without authentication; scoping alone does not prove the caller may mutate the record.

```ruby
# GOOD: explicit authorization, explicit failure
def update
  authorize [:public, document], :update?
  document.update(params)
rescue Pundit::NotAuthorizedError
  head :forbidden
end
```

N+1 query:

```ruby
# BAD: one query per user
@users.each { |user| user.posts.count }
```

Why: query count grows linearly with rows, degrading list views under load.

```ruby
# GOOD: eager-load the association once
@users.includes(:posts).each { |user| user.posts.count }
```

Custom JavaScript where Hotwire already works:

```ruby
# BAD: hand-rolled delete handler
<%= link_to "Delete", user_path(@user), data: { confirm: "Sure?", method: :delete } %>
<script>/* custom delete handler */</script>
```

Why: reinvents behavior Turbo provides, adding maintenance burden and drift from convention.

```ruby
# GOOD: let Turbo drive the request and confirmation
<%= link_to "Delete", user_path(@user), data: { turbo_method: :delete, turbo_confirm: "Sure?" } %>
```

Bang method without error handling:

```ruby
# BAD: raises into the caller, which cannot branch on success
def assign(document, requirement)
  document.update!(assignment: requirement)
end
```

Why: the controller has no clean way to detect failure and render the right response.

```ruby
# GOOD: return a boolean the caller can check
def assign(document, requirement)
  document.update(assignment: requirement)
rescue ActiveRecord::RecordInvalid
  false
end
```

## Worked Examples

A complete before/after using the per-issue format.

````markdown
### 🔴 Issue #1: Missing Authorization in Public Controller

**Category:** Security
**Priority:** CRITICAL
**Location:** `app/controllers/public/deals/documents/requirements_controller.rb:10-17`

**Problem:**

Controller actions have no explicit authorization checks beyond scoping.

```ruby
def update
  document = @deal.documents.find(params[:document_id])
  requirement = @deal.requirements.find(params[:deal_requirement_id])
  document.fulfill(requirement)
end
```

**Why It Matters:**

Public controllers are accessible without authentication. Even with signed RSVP tokens, you must explicitly verify that the token grants document manipulation permissions. An attacker could potentially manipulate documents if they obtain an RSVP signed ID.

**Fix:**

```ruby
def update
  document = @deal.documents.find(params[:document_id])
  requirement = @deal.requirements.find(params[:deal_requirement_id])

  # Add explicit authorization check
  authorize [:public, document], :update?

  document.fulfill(requirement)
  head :ok
rescue Pundit::NotAuthorizedError
  head :forbidden
end
```

**Verification:**

```bash
bundle exec rspec spec/requests/public/deals/documents/requirements_spec.rb
# Add test case for unauthorized access attempt
```
````

## Review Workflow

### Step 0: Pre-Review Validation (CRITICAL)

Before reviewing, verify the baseline.

```bash
# 1. Check if tests pass
bundle exec rspec
# If tests are passing, be skeptical of claims that code is "broken"

# 2. Get explicit commit range (required)
BASE_SHA=$(git rev-parse origin/main)  # or specific commit
HEAD_SHA=$(git rev-parse HEAD)
echo "Reviewing: $BASE_SHA..$HEAD_SHA"

# 3. Get the actual diff
git diff $BASE_SHA..$HEAD_SHA > /tmp/review-diff.txt

# 4. Check Rails version
grep "rails " Gemfile.lock | head -1
# Important: Rails 8 has different conventions than Rails 7
```

Pre-review checklist:

- [ ] Tests are passing (if not, that's your first issue)
- [ ] You have explicit BASE and HEAD commit SHAs
- [ ] You've reviewed the actual diff, not speculated about code
- [ ] You know the Rails version (8.x, 7.x, etc.)

### Step 1: Get the Diff with Context

```bash
# Get diff between commits with file context
git diff --stat $BASE_SHA..$HEAD_SHA

# Review only the changes
git diff $BASE_SHA..$HEAD_SHA

# IMPORTANT: Only review code that changed in this range
# Don't flag issues in code that wasn't touched
```

### Step 2: Category Scan (Priority Order)

Review changes in this exact order to catch critical issues first: Security (Critical), then Rails Conventions (High), then Performance (High), then Code Duplication (Medium), then CSS & Styling (Low), with Bugs/Logic and Browser Compatibility scanned throughout. The per-category checklists and code blocks are in [Review Principles](#review-principles).

### Step 3: Verification Before Flagging

Before marking something as an issue, verify your claim.

```bash
# If you think code is broken:
# 1. Check if tests pass
bundle exec rspec spec/path/to/relevant_spec.rb

# 2. Check Rails behavior (don't assume)
bundle exec rails runner "puts Document.new.respond_to?(:fulfill)"

# 3. Check actual behavior vs expected
# If tests pass and code works, it's NOT broken
# Even if it's non-standard

# 4. Check Rails version features
# Rails 8: where.missing, implicit turbo responses
# Rails 7: Turbo 8 features
# Don't flag modern features as issues
```

Examples of what NOT to flag:

```ruby
# DON'T FLAG: This works in Rails 8
def update
  @document.update(params)
  # No explicit render/response needed with Turbo
end

# DON'T FLAG: This is valid Rails pattern
class Document
  module Fulfillable  # Nested module in model file
    extend ActiveSupport::Concern
  end
end

# DON'T FLAG: This is modern Rails 7+ syntax
scope :unassigned, -> { where.missing(:deal_requirement_document) }

# DON'T FLAG: Broadcaster using refresh (intentional)
broadcast_refresh_to(@deal)  # Full page morph is valid pattern
```

### Step 4: Document Findings

Document each verified finding using the per-issue format, then assemble the summary report. Both templates are in [Output Format](#output-format).

## Output Format

Output MUST be in proper Markdown. For each issue found, use this exact per-issue format.

````markdown
### 🔴 Issue #X: [Short Title]

**Category:** [Security/Rails Conventions/Performance/etc.]
**Priority:** [CRITICAL/HIGH/MEDIUM/LOW]
**Location:** `file/path.rb:123-145`

**Problem:**

[Describe the specific issue with code example]

```ruby
# Current code showing the problem
def problematic_method
  # ...
end
```

**Why It Matters:**

[Explain the actual impact - security risk, performance issue, maintenance burden]

**Fix:**

```ruby
# Corrected code
def fixed_method
  # ...
end
```

**Verification:**

```bash
# Steps to verify the fix works
bundle exec rspec spec/path/spec.rb
# Expected: all tests pass
```
````

Then assemble the full summary report (also Markdown).

````markdown
# Rails Code Review Report

**Branch:** `feature-branch-name`
**Base:** `main`
**Commits:** `abc123..def456`
**Review Date:** YYYY-MM-DD

## Executive Summary

[1-2 sentence overview of changes and assessment]

**Overall Assessment:** [APPROVED / CONDITIONAL APPROVAL / BLOCK MERGE]

## Issues Found

[List all issues in priority order using the per-issue format above]

## Summary Table

| Priority | Category | Count | Issues |
|----------|----------|-------|--------|
| 🔴 CRITICAL | Security | X | [Brief list] |
| 🟡 HIGH | Rails Conventions | X | [Brief list] |
| 🟠 MEDIUM | Code Quality | X | [Brief list] |
| 🟢 LOW | CSS/Styling | X | [Brief list] |
| **TOTAL** | | **X** | |

## Positive Findings ✅

1. [What was done well]
2. [Good patterns observed]
3. [Thorough testing]

## Critical Actions Required

1. [Must fix before merge]
2. [Must fix before merge]

## Recommendations

### Immediate (Must Fix)

- [Required fixes]

### Short Term (Should Fix)

- [Recommended fixes]

### Long Term (Nice to Have)

- [Optional improvements]

## Overall Merge Recommendation

[APPROVED / CONDITIONAL APPROVAL / BLOCK MERGE] with reasoning.

## Verification Checklist

```bash
# Commands to verify fixes
bundle exec rspec
bundle exec rubocop
bundle exec brakeman
```
````

## Severity Scale

Use these strict definitions for priority levels.

### CRITICAL

- Security vulnerabilities: actual exploitable XSS, SQL injection, missing authorization
- Data loss risks: code that could delete or corrupt production data
- Broken functionality: code that causes 500 errors or breaks core features in production
- Examples: missing authorization, SQL injection, unhandled exceptions in critical paths

### HIGH

- Architecture problems: significant deviations from the Rails Way that cause maintenance burden
- Missing error handling: no rescue blocks for external calls that could fail
- Performance blockers: N+1 queries in main list views, missing critical indexes
- Missing features from requirements: functionality explicitly requested but not implemented
- Examples: N+1 queries, missing error handling, incorrect use of Rails patterns

### MEDIUM

- Non-standard patterns that work: code that functions but doesn't follow conventions
- Code duplication: repeated patterns that should be extracted
- Missing test coverage: core logic without tests
- Performance optimizations: opportunities for caching or query improvements
- Examples: duplicate code, could use scopes, missing tests for edge cases

### LOW

- Code style issues: formatting, naming conventions
- Optimization opportunities: minor performance tweaks
- CSS improvements: redundant classes, `!important` flags
- Unexplained *why*: a non-obvious decision, tradeoff, or workaround left with no comment (the absence of a comment is only a defect when the reasoning genuinely can't be recovered from the code; do not flag missing comments on self-explanatory code)
- Examples: CSS important flags, inline styles, could extract constant

If tests pass and the code works, the maximum severity is MEDIUM (a non-standard pattern), not HIGH or CRITICAL.

## Quality Checklist

Before finishing the review, verify:

- [ ] Reviewed the diff only (not code that wasn't touched), with full context rather than line-by-line
- [ ] Verified every claim against actual Rails behavior and passing tests before flagging
- [ ] Scanned security first, then conventions/performance/DRY/style in that order
- [ ] Did not flag modern Rails 8 patterns (`where.missing`, implicit Turbo responses, nested model concerns, `broadcast_refresh_to`, Solid Stack)
- [ ] Applied the severity scale, including the "if tests pass, max MEDIUM" rule, with priorities never mixed within one finding
- [ ] Output in proper Markdown (per-issue format plus summary report), not plain text
- [ ] Every finding is specific, explains WHY it matters, and ships an actionable fix with verification steps
