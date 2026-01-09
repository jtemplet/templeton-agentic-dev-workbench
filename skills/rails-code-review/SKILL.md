---
name: rails-code-review
description: Use when reviewing Rails 8 code before merge or PR - systematic technique covering security vulnerabilities (XSS, SQL injection), Rails conventions, Hotwire/Turbo patterns, performance optimization, and DRY principles with priority-based issue categorization
---

# Rails Code Review Technique

## Overview

Systematic framework for reviewing Ruby on Rails 8 code focusing on security, conventions, performance, and maintainability. Prioritizes issues by impact (Critical → High → Medium → Low) and provides actionable fixes.

**Core principles:**
1. **Verify before flagging** - If tests pass, verify claims before marking as issues
2. **Security first** - Actual vulnerabilities over theoretical concerns
3. **Pragmatic over pure** - Working non-standard code > Non-working standard code
4. **Context matters** - Understand Rails 8 patterns and modern conventions

## When to Use

**Use this skill when:**
- Reviewing code before merging to main branch
- Creating or reviewing pull requests
- Performing pre-deployment code audits
- Reviewing changes that touch views, controllers, or models
- Investigating security vulnerabilities
- Optimizing Rails application performance

**Don't use this for:**
- Initial exploratory coding (too early)
- Non-Rails Ruby code
- Infrastructure/deployment configs (use other skills)
- Simple typo fixes or documentation updates

## Quick Reference

| Category | Focus Areas | Priority | Red Flags |
|----------|-------------|----------|-----------|
| **Security** | XSS, unsafe rendering, SQL injection, mass assignment | Critical | `html_safe`, `raw`, direct SQL, `params` in queries |
| **Rails Conventions** | Rails 8 Way, Solid Stack, Hotwire patterns | High | Custom JavaScript when Hotwire works, ignoring conventions |
| **Performance** | N+1 queries, caching, unnecessary Turbo | High | Missing `includes`, no caching, Turbo frame without need |
| **DRY** | Duplicate code, repeated patterns, extraction opportunities | Medium | Copy-pasted blocks, repeated partials, duplicate helpers |
| **CSS/Styling** | Tailwind v4, redundant classes, unused utilities | Low | Inline styles, conflicting classes, non-Tailwind CSS |
| **Browser Compat** | CSS properties, vendor prefixes | Low | Modern-only features, missing fallbacks |

## Implementation

### Step 0: Pre-Review Validation (CRITICAL)

**Before reviewing, verify the baseline:**

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

**Pre-review checklist:**
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

Review changes in this exact order to catch critical issues first:

#### A. Security (CRITICAL PRIORITY)

**Check for:**
- [ ] XSS vulnerabilities in HAML/ERB rendering
- [ ] Unsafe string interpolation or `html_safe` usage
- [ ] `raw()` method calls without sanitization
- [ ] Direct SQL queries vulnerable to injection
- [ ] Mass assignment issues in controllers
- [ ] Unvalidated user input rendering
- [ ] Missing CSRF protection on forms
- [ ] Missing authorization checks in public controllers

**Common vulnerabilities:**
```ruby
# ❌ BAD: XSS vulnerability
= raw(@user.bio)

# ✅ GOOD: Sanitized output
= sanitize(@user.bio, tags: %w[p br strong em])

# ❌ BAD: SQL injection
User.where("email = '#{params[:email]}'")

# ✅ GOOD: Parameterized query
User.where(email: params[:email])

# ❌ BAD: Missing authorization in public controller
class Public::DocumentsController < Public::BaseController
  def update
    document.update(params)  # No authorize check!
  end
end

# ✅ GOOD: Explicit authorization
class Public::DocumentsController < Public::BaseController
  def update
    authorize [:public, document], :update?
    document.update(params)
  end
end
```

#### B. Rails Conventions & Best Practices (HIGH PRIORITY)

**Check for:**
- [ ] Following "The Rails 8 Way" patterns
- [ ] Using Solid Stack over external dependencies
- [ ] Proper Hotwire/Turbo usage (not custom JavaScript)
- [ ] Controllers returning proper responses
- [ ] Using native Rails methods instead of custom solutions
- [ ] Proper use of Rails helpers and concerns
- [ ] RESTful routing and controller actions
- [ ] Following ActiveRecord conventions

**Rails 8 Modern Patterns (Don't flag these as issues):**
```ruby
# ✅ CORRECT: Rails 8 implicit Turbo Stream responses
def update
  @document.update(params)
  # Rails 8 + Turbo automatically handles response
  # No need for explicit respond_to or head :ok
end

# ✅ CORRECT: Modern where.missing syntax (Rails 7+)
scope :unassigned, -> { where.missing(:assignment) }

# ✅ CORRECT: broadcast_refresh_to for simple updates
broadcast_refresh_to(@deal)  # Intentional full page morph

# ✅ CORRECT: Concerns can be in app/models/model_name/
# File: app/models/document/fulfillable.rb
class Document
  module Fulfillable
    extend ActiveSupport::Concern
  end
end
```

**Anti-patterns to flag:**
```ruby
# ❌ BAD: Custom JavaScript when Hotwire works
<%= link_to "Delete", user_path(@user),
    data: { confirm: "Are you sure?", method: :delete } %>
<script>/* custom delete handler */</script>

# ✅ GOOD: Turbo handles this
<%= link_to "Delete", user_path(@user),
    data: { turbo_method: :delete, turbo_confirm: "Are you sure?" } %>

# ❌ BAD: Controller explicitly expects template but doesn't handle response
def create
  respond_to do |format|
    format.turbo_stream  # Expects template but no error handling
    # What if template doesn't exist?
  end
end

# ✅ GOOD: Explicit rendering or proper response
def create
  respond_to do |format|
    format.turbo_stream { render turbo_stream: turbo_stream.append(...) }
  end
rescue => e
  head :unprocessable_entity
end
```

#### C. Performance & Optimization (HIGH PRIORITY)

**Check for:**
- [ ] N+1 query problems (missing `includes`, `preload`, `eager_load`)
- [ ] Opportunities for caching or memoization
- [ ] Unnecessary database queries in loops
- [ ] Missing database indexes for frequent queries
- [ ] Inefficient ActiveRecord queries
- [ ] Turbo Frames/Streams used when simple redirect works
- [ ] Large payload responses

**Performance issues:**
```ruby
# ❌ BAD: N+1 query
@users.each do |user|
  user.posts.count  # Separate query for each user
end

# ✅ GOOD: Eager load
@users.includes(:posts).each do |user|
  user.posts.count  # Uses preloaded data
end

# ❌ BAD: Unnecessary complexity
respond_to do |format|
  format.turbo_stream  # For simple redirect
end

# ✅ GOOD: Simple redirect
redirect_to users_path, notice: "Created successfully"
```

#### D. Code Duplication (MEDIUM PRIORITY)

**Check for:**
- [ ] Repeated code blocks → extract to partials
- [ ] Repeated styling patterns → create shared component classes
- [ ] Duplicate logic → move to helpers, concerns, or decorators
- [ ] Similar views → use shared partials with locals
- [ ] Repeated queries → extract to scopes or query objects

**DRY opportunities:**
```haml
-# ❌ BAD: Repeated partial code
- @users.each do |user|
  .card.p-4.border.rounded
    .font-bold= user.name
    .text-gray-600= user.email

-# ✅ GOOD: Extract to partial
- @users.each do |user|
  = render 'user_card', user: user

-# _user_card.html.haml
.card.p-4.border.rounded
  .font-bold= user.name
  .text-gray-600= user.email
```

#### E. CSS & Styling (LOW PRIORITY)

**Check for:**
- [ ] Using Tailwind v4 syntax only
- [ ] No custom CSS (utility-first approach)
- [ ] Redundant or conflicting Tailwind classes
- [ ] Unused Tailwind utilities that can be removed
- [ ] Inline styles (should use Tailwind)
- [ ] Proper responsive breakpoints
- [ ] Consistent spacing and sizing patterns

**Styling issues:**
```haml
-# ❌ BAD: Conflicting classes
.flex.block.p-4.p-6

-# ✅ GOOD: Consistent classes
.flex.p-6

-# ❌ BAD: Inline styles
%div{ style: "margin-top: 20px;" }

-# ✅ GOOD: Tailwind utilities
.mt-5

-# ⚠️ MINOR: Important flag (use sparingly)
.drop-zone[data-drop-target] {
  @apply bg-accent-purple/10! px-1 rounded-xl;
}

-# ✅ BETTER: Increase specificity
.drop-zone[data-drop-target] {
  @apply bg-accent-purple/10 px-1 rounded-xl;
}
```

#### F. Bugs & Logic Issues (ALL PRIORITIES)

**Check for:**
- [ ] Logic errors or incorrect conditional logic
- [ ] Missing nil/null checks
- [ ] Missing error handling for external calls
- [ ] Race conditions in concurrent operations
- [ ] Incorrect data type handling
- [ ] Off-by-one errors in loops/ranges
- [ ] Missing edge case handling
- [ ] Methods that should return booleans but raise exceptions

**Common issues:**
```ruby
# ❌ BAD: Using bang method without error handling
def assign(document, requirement)
  document.update!(assignment: requirement)
  # Controller can't check success/failure
end

# ✅ GOOD: Return boolean for controller to check
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

**Note:** Specifically exclude:
- Accessibility issues (not a concern per project requirements)
- ARIA attributes (not a concern per project requirements)

#### G. Browser Compatibility (LOW PRIORITY)

**Check for:**
- [ ] CSS properties requiring vendor prefixes
- [ ] JavaScript features needing polyfills
- [ ] Browser-specific CSS quirks
- [ ] Features not supported in target browsers

### Step 3: Verification Before Flagging

**CRITICAL: Before marking something as an issue, verify your claim:**

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

**Examples of what NOT to flag:**

```ruby
# ✅ DON'T FLAG: This works in Rails 8
def update
  @document.update(params)
  # No explicit render/response needed with Turbo
end

# ✅ DON'T FLAG: This is valid Rails pattern
class Document
  module Fulfillable  # Nested module in model file
    extend ActiveSupport::Concern
  end
end

# ✅ DON'T FLAG: This is modern Rails 7+ syntax
scope :unassigned, -> { where.missing(:deal_requirement_document) }

# ✅ DON'FLAG: Broadcaster using refresh (intentional)
broadcast_refresh_to(@deal)  # Full page morph is valid pattern
```

### Step 4: Issue Documentation

**CRITICAL: Output MUST be in proper Markdown format**

For each issue found, provide in this exact format:

```markdown
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
```

**Complete example:**

```markdown
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
```

### Step 5: Summary Report

**Output format (must be Markdown):**

```markdown
# Rails Code Review Report

**Branch:** `feature-branch-name`
**Base:** `main`
**Commits:** `abc123..def456`
**Review Date:** YYYY-MM-DD

## Executive Summary

[1-2 sentence overview of changes and assessment]

**Overall Assessment:** [APPROVED / CONDITIONAL APPROVAL / BLOCK MERGE]

## Issues Found

[List all issues in priority order using the format from Step 4]

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
```

---

## Severity Guidelines

**Use these strict definitions for priority levels:**

### CRITICAL
- **Security vulnerabilities:** Actual exploitable XSS, SQL injection, missing authorization
- **Data loss risks:** Code that could delete or corrupt production data
- **Broken functionality:** Code that causes 500 errors or breaks core features in production
- **Examples:** Missing authorization, SQL injection, unhandled exceptions in critical paths

### HIGH
- **Architecture problems:** Significant deviations from Rails Way that cause maintenance burden
- **Missing error handling:** No rescue blocks for external calls that could fail
- **Performance blockers:** N+1 queries in main list views, missing critical indexes
- **Missing features from requirements:** Functionality explicitly requested but not implemented
- **Examples:** N+1 queries, missing error handling, incorrect use of Rails patterns

### MEDIUM
- **Non-standard patterns that work:** Code that functions but doesn't follow conventions
- **Code duplication:** Repeated patterns that should be extracted
- **Missing test coverage:** Core logic without tests
- **Performance optimizations:** Opportunities for caching or query improvements
- **Examples:** Duplicate code, could use scopes, missing tests for edge cases

### LOW
- **Code style issues:** Formatting, naming conventions
- **Optimization opportunities:** Minor performance tweaks
- **CSS improvements:** Redundant classes, `!important` flags
- **Documentation gaps:** Missing comments on complex logic
- **Examples:** CSS important flags, inline styles, could extract constant

**Critical Rule:** If tests pass and code works, maximum priority is MEDIUM (non-standard pattern), not CRITICAL or HIGH.

---

## Common Mistakes to Avoid

**When reviewing:**
- ❌ Reviewing line-by-line without understanding context
- ❌ Flagging non-standard patterns as CRITICAL when they work
- ❌ Not verifying claims against actual Rails behavior
- ❌ Assuming code is broken without checking tests
- ❌ Focusing on style issues before security/logic
- ❌ Not checking for N+1 queries in list views
- ❌ Ignoring Rails 8 modern patterns (where.missing, implicit responses)
- ❌ Accepting "it works" without checking security

**When providing feedback:**
- ❌ Vague criticism: "This could be better"
- ❌ Missing code examples in fixes
- ❌ Not explaining WHY something is an issue
- ❌ Mixing multiple priorities (critical + style) without distinction
- ❌ Not providing verification steps
- ❌ Outputting plain text instead of proper Markdown
- ❌ Flagging modern Rails patterns as issues

**When determining severity:**
- ❌ Marking everything as CRITICAL
- ❌ Calling working non-standard code "broken"
- ❌ High priority for style issues
- ❌ Critical for theoretical concerns without actual risk

---

## Rails 8 Awareness

**Modern patterns you should NOT flag as issues:**

1. **Implicit Turbo Stream Responses**
   ```ruby
   # This works in Rails 8 - no explicit response needed
   def update
     @resource.update(params)
   end
   ```

2. **where.missing Syntax** (Rails 7+)
   ```ruby
   # Modern, readable, preferred
   scope :unassigned, -> { where.missing(:assignment) }
   ```

3. **Concerns in Model Subdirectories**
   ```ruby
   # Valid pattern: app/models/document/fulfillable.rb
   class Document
     module Fulfillable
       extend ActiveSupport::Concern
     end
   end
   ```

4. **broadcast_refresh_to for Simple Updates**
   ```ruby
   # Valid for public views - intentional full page morph
   broadcast_refresh_to(@deal)
   ```

5. **Solid Stack Components**
   - Solid Queue (background jobs)
   - Solid Cache (caching)
   - Solid Cable (WebSockets)

---

## Integration

**Use with slash commands:**
```bash
/rails-code-review  # Triggers this skill automatically
```

**Use with requesting-code-review:**
After running automated code review, use this skill as a second pass for
Rails-specific patterns and conventions that generic reviewers might miss.

**Workflow:**
1. Get explicit commit range: `BASE_SHA..HEAD_SHA`
2. Run pre-validation: tests pass? Rails version?
3. Review diff only (not entire codebase)
4. Verify claims before flagging
5. Output proper Markdown
6. Provide actionable fixes

## Summary

**Review order:** Validate → Security → Conventions → Performance → DRY → Style

**For each issue:** Category + Priority + Location + Problem + Why + Fix + Verify

**Output:** Prioritized list, **formatted in proper Markdown**, with actionable fixes and verification steps.

**Golden Rule:** Verify before you flag. If tests pass, it's probably not broken.
