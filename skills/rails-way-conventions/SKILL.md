---
name: rails-way-conventions
description: Use when generating Rails code, evaluating gems, or making Rails architectural decisions - enforces Rails 8 Way philosophy (convention over configuration, Solid Stack over external dependencies, Hotwire)
---

# Rails Conventions

## Overview

Enforce "The Rails 8 Way": convention over configuration, integrated systems, and Rails-native solutions over external frameworks.

Core principle: Trust Rails defaults. Add complexity only when you have proof you need it.

## When to Use

- Generating or refactoring Rails code
- Evaluating whether to add a gem or framework
- Making architectural decisions
- Choosing between Rails-native vs third-party solutions

## When NOT to Use

- Non-Rails Ruby projects
- Rails 7 or earlier (some features are Rails 8-specific)
- Projects explicitly using alternative patterns (Trailblazer, Hanami)

## Core Philosophy (Rails Doctrine)

1. **Convention Over Configuration** - Use Rails defaults and naming conventions
2. **Omakase** - Trust framework choices (Solid Stack, not Redis)
3. **Integrated Systems** - Use full Rails stack together (ActiveRecord, not separate ORM)
4. **Programmer Happiness** - Expressive, readable code
5. **Progress Over Stability** - Embrace modern patterns (Hotwire, not jQuery)

## Quick Decision Framework

**Should I add [GEM]?**

1. Does Rails 8 provide this? Use Rails version
2. Does Rails have a conventional way? Use conventions
3. Will this simplify or complicate? Choose simplicity

**Default: NO, use Rails-native solution**

Exception: Only when Rails genuinely doesn't provide the functionality

## Rails 8 Defaults

**Use these (Rails 8 built-in):**
- Solid Queue (background jobs, not Sidekiq)
- Solid Cache (caching, not Redis)
- Solid Cable (WebSockets, not Redis)
- Authentication generator (not Devise for new apps)
- Propshaft (assets)
- Hotwire (Turbo + Stimulus, not React)

## Code Organization Patterns

### Step-Down Rule: Read Top-to-Bottom

Classes and methods must follow the step-down rule—code reads like a narrative from highest-level public interface down to implementation details. Public methods first, private methods below. High-level abstractions before low-level details.

**Why:** Developers read code top-down. Force them to jump around and they lose context.

**Pattern:**
```ruby
class ArticlePublisher
  def publish(article)
    validate_article(article)
    send_notifications(article)
    update_article_state(article)
    record_event(article)
  end

  private

  def validate_article(article)
    raise InvalidArticle unless article.valid?
  end

  def send_notifications(article)
    NotificationService.publish_article(article)
  end

  def update_article_state(article)
    article.update(published_at: Time.current, status: :published)
  end

  def record_event(article)
    PublishEvent.create(article: article, user: article.author)
  end
end
```

Read the `publish` method first—you understand what happens. Details follow below.

**Anti-pattern:**
```ruby
class ArticlePublisher
  private

  def update_article_state(article)
    article.update(published_at: Time.current, status: :published)
  end

  def record_event(article)
    PublishEvent.create(article: article, user: article.author)
  end

  def validate_article(article)
    raise InvalidArticle unless article.valid?
  end

  public

  def publish(article)
    validate_article(article)
    send_notifications(article)
    update_article_state(article)
    record_event(article)
  end

  def send_notifications(article)
    NotificationService.publish_article(article)
  end
end
```

Reader must jump to bottom to find the public API, then jump back up for details. Chaos.

### Many Small Controllers > Few Fat Controllers

Create RESTful controllers prolifically. Each action gets focused context.

**Anti-pattern:**
```ruby
class MessagesController < ApplicationController
  def index
    case params[:filter]
    when 'drafts' then @messages = current_user.messages.drafts
    when 'trash' then @messages = current_user.messages.trashed
    else @messages = current_user.messages.inbox
    end
  end
end
```

**Rails Way:**
```ruby
class MessagesController < ApplicationController
  def index
    @messages = current_user.messages.inbox
  end
end

class Messages::DraftsController < ApplicationController
  def index
    @messages = current_user.messages.drafts
  end
end

class Messages::TrashesController < ApplicationController
  def index
    @messages = current_user.messages.trashed
  end
end
```

### Use Models + Concerns, Not Service Objects (Usually)

Keep models focused. Use concerns for shared behavior.

**When service objects ARE appropriate:**
- Complex multi-model transactions
- External API integrations with significant logic
- Business processes that don't map to a single model

**When to use models + concerns instead:**
- Single model operations (create, update, delete)
- Shared behavior across models
- Standard CRUD with callbacks

### Use ActiveRecord Fully

```ruby
# Scopes for query reuse
class Article < ApplicationRecord
  scope :published, -> { where(published: true) }
  scope :recent, -> { where("created_at > ?", 1.week.ago) }
  scope :by_author, ->(author) { where(author: author) }
end

# Associations, not manual joins
class User < ApplicationRecord
  has_many :posts
end
current_user.posts  # Clear, simple

# Validations in models
class User < ApplicationRecord
  validates :email, presence: true, uniqueness: true
  validates :age, numericality: { greater_than_or_equal_to: 18 }
end
```

## Common Anti-Patterns to Avoid

**Repository Pattern:**
Don't create UserRepository to wrap User.find(id). Use ActiveRecord directly.

**Excessive Service Objects:**
Don't create CreateUserService, UpdateUserService, DeleteUserService for standard CRUD. Use ActiveRecord methods and callbacks.

**God Objects:**
Don't create UserManager with all user-related methods. Spread responsibilities across models, controllers, mailers.

**Fighting REST:**
Don't add custom actions like register, login, forgot_password to one controller. Create separate RESTful controllers: RegistrationsController, SessionsController, PasswordResetsController.

**Over-Engineering:**
Don't add microservices, Redis clusters, message queues, or GraphQL prematurely. Start simple, scale when you have proof you need it.

## Quick Decision Trees

**Should I create a service object?**
- Single model operation? Use model + callbacks
- Multiple models in transaction? Service object OK
- External API integration? Service object OK
- Otherwise? Use model methods or concern

**Should I create a new controller?**
- One of 7 REST actions? Add to existing controller
- State/filter of resource (drafts, archived)? Create nested controller
- Operating on relationship (like, bookmark)? Create singular resource controller
- Otherwise? Rethink, might be fighting REST

## Solid Stack Quick Reference

**Solid Queue (Background Jobs):**
```ruby
class ReportJob < ApplicationJob
  queue_as :default
  def perform(user_id)
    user = User.find(user_id)
    ReportMailer.send_report(user, generate_report(user)).deliver_now
  end
end

ReportJob.perform_later(current_user.id)
```

**Solid Cache:**
```ruby
Rails.cache.fetch(["product", id, "stats"], expires_in: 1.hour) do
  expensive_calculation
end
```

**Authentication Generator:**
```bash
bin/rails generate authentication
```

Creates User model, Session model, SessionsController, password reset, and email confirmation.

## Golden Rule

When in doubt, do it the simplest Rails way possible. Add complexity only when you have proof you need it.

## Additional Reference

- Rails Doctrine: https://rubyonrails.org/doctrine
- Rails 8 Release Notes: https://guides.rubyonrails.org/8_0_release_notes.html
