---
name: rails-conventions
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
6. **Vanilla Rails** - Thin controllers, rich domain models, no unnecessary service layers

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

### Controllers

#### Structure and Organization

**Order of elements:**

1. Class-level declarations (`include`, `before_action`, `layout`, etc.)
2. Public action methods (in RESTful order when possible: index, show, new, create, edit, update, destroy)
3. `private` keyword
4. Private helper methods

**Example:**

```ruby
class CardsController < ApplicationController
  include FilterScoped

  before_action :set_board, only: %i[ create ]
  before_action :set_card, only: %i[ show edit update destroy ]

  def index
    set_page_and_extract_portion_from @filter.cards
  end

  def create
    card = @board.cards.create! card_params.merge(creator: Current.user)
    redirect_to card_path(card)
  end

  private
    def set_card
      @card = Current.user.accessible_cards.find_by!(number: params[:id])
    end

    def card_params
      params.expect(card: [ :title, :description ])
    end
end
```

#### Controller Conventions

**Use concerns for shared behavior:**

- Concerns live in `app/controllers/concerns/`
- Use for setting up scoped resources (e.g., `CardScoped`, `BoardScoped`)
- Use for cross-cutting concerns (e.g., `Authentication`, `Authorization`)

**Many Small Controllers > Few Fat Controllers:**

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

**Resource-oriented design:**

- Model actions as CRUD operations on resources
- When an action doesn't fit standard CRUD, introduce a new resource rather than custom actions

  ```ruby
  # Bad
  resources :cards do
    post :close
  end

  # Good
  resources :cards do
    resource :closure
  end
  ```

**Call model methods directly:**

- Controllers should call model APIs, not extract logic
- Keep business logic in models, not controllers

  ```ruby
  # Good
  def create
    @card.gild
    respond_to do |format|
      format.turbo_stream { render_card_replacement }
      format.json { head :no_content }
    end
  end
  ```

**Parameter handling:**

- Use `params.expect` (Rails 8) for strong parameters
- Define param methods in private section

  ```ruby
  private
    def card_params
      params.expect(card: [ :title, :description, :created_at ])
    end
  ```

**Instance variable setup:**

- Use `before_action` callbacks for setting instance variables
- Define setup methods in private section

  ```ruby
  before_action :set_board, only: %i[ create ]

  private
    def set_board
      @board = Current.user.boards.find params[:board_id]
    end
  ```

### Models

#### Structure and Organization

**Order of elements:**

1. Concerns (via `include`)
2. Associations (`belongs_to`, `has_many`, etc.)
3. Attachments and rich text
4. Callbacks (`before_save`, `after_create`, etc.)
5. Scopes
6. Delegations
7. Public methods
8. `private` keyword
9. Private methods

**Example:**

```ruby
class Card < ApplicationRecord
  include Closeable, Golden, Taggable

  belongs_to :account
  belongs_to :board
  belongs_to :creator, class_name: "User", default: -> { Current.user }

  has_many :comments, dependent: :destroy
  has_one_attached :image, dependent: :purge_later
  has_rich_text :description

  before_create :assign_number
  after_save -> { board.touch }, if: :published?

  scope :latest, -> { order last_active_at: :desc, id: :desc }
  scope :golden, -> { joins(:goldness) }

  delegate :accessible_to?, to: :board

  def move_to(new_board)
    transaction do
      update!(board: new_board)
      events.update_all(board_id: new_board.id)
    end
  end

  private
    def assign_number
      self.number ||= account.increment!(:cards_count).cards_count
    end
end
```

#### Model Conventions

**Heavy use of concerns:**

- Shared concerns in `app/models/concerns/` (e.g., `Searchable`, `Eventable`)
- Model-specific concerns in `app/models/model_name/` (e.g., `Card::Golden`, `Board::Publishable`)
- Concerns encapsulate related behavior (associations, scopes, methods)

**Rich domain models:**

- Models contain business logic, not just data access
- Methods should be intention-revealing

  ```ruby
  # Good
  def gild
    create_goldness! unless golden?
  end

  def close(user: Current.user)
    unless closed?
      transaction do
        create_closure! user: user
        track_event :closed, creator: user
      end
    end
  end
  ```

**Scopes for queries:**

- Define common queries as scopes
- Chain scopes for complex queries
- Use lambda syntax for all scopes

  ```ruby
  scope :latest, -> { order last_active_at: :desc, id: :desc }
  scope :closed, -> { joins(:closure) }
  scope :closed_by, ->(users) { closed.where(closures: { user_id: Array(users) }) }
  ```

**Use defaults for associations:**

- Leverage `default:` option for automatic assignment

  ```ruby
  belongs_to :account, default: -> { board.account }
  belongs_to :creator, class_name: "User", default: -> { Current.user }
  ```

**Use ActiveRecord Fully:**

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

### Concerns

#### Controller Concerns

**Structure:**

```ruby
module CardScoped
  extend ActiveSupport::Concern

  included do
    before_action :set_card, :set_board
  end

  private
    def set_card
      @card = Current.user.accessible_cards.find_by!(number: params[:card_id])
    end

    def set_board
      @board = @card.board
    end
end
```

**Patterns:**

- Use `extend ActiveSupport::Concern`
- Use `included do` block for callbacks and helpers
- Methods are private unless explicitly needed as helpers
- Can define `class_methods` block for class-level extensions

**When to use:**

- Setting up scoped resources (e.g., `@card`, `@board`)
- Shared authentication/authorization logic
- Cross-cutting presentation concerns (e.g., `TurboFlash`)

#### Model Concerns

**Structure for shared concerns:**

```ruby
module Searchable
  extend ActiveSupport::Concern

  included do
    after_create_commit :create_in_search_index
    after_update_commit :update_in_search_index
  end

  def reindex
    update_in_search_index
  end

  private
    def update_in_search_index
      search_record_class.upsert!(search_record_attributes)
    end
end
```

**Structure for model-specific concerns:**

```ruby
module Card::Golden
  extend ActiveSupport::Concern

  included do
    has_one :goldness, dependent: :destroy
    scope :golden, -> { joins(:goldness) }
  end

  def golden?
    goldness.present?
  end

  def gild
    create_goldness! unless golden?
  end

  def ungild
    goldness&.destroy
  end
end
```

**When to use:**

- Encapsulate related associations, scopes, and methods
- Keep primary model file focused and readable
- Shared behavior across multiple models (in `app/models/concerns/`)
- Model-specific behavior that deserves its own file (in `app/models/model_name/`)

**Concern organization:**

- Model-specific concerns: `app/models/model_name/feature.rb` (e.g., `Card::Golden`)
- Shared concerns: `app/models/concerns/feature.rb` (e.g., `Searchable`)
- Each concern should have a clear, focused purpose

### Service Objects (POROs)

Keep models focused. Use concerns for shared behavior.

**When service objects ARE appropriate:**

- Complex multi-model transactions
- External API integrations with significant logic
- Business processes that don't map to a single model
- Form objects that need validation but aren't persisted
- Coordinating objects that orchestrate multiple models
- Parsing or transformation logic

**When to use models + concerns instead:**

- Single model operations (create, update, delete)
- Shared behavior across models
- Standard CRUD with callbacks

**Structure:**

```ruby
class Signup
  include ActiveModel::Model
  include ActiveModel::Attributes
  include ActiveModel::Validations

  attr_accessor :email_address, :full_name
  attr_reader :account, :user

  validates :email_address, format: { with: URI::MailTo::EMAIL_REGEXP }

  def create_identity
    @identity = Identity.find_or_create_by!(email_address: email_address)
    @identity.send_magic_link for: :sign_up
  end

  def complete
    if valid?
      create_account
      true
    else
      false
    end
  end

  private
    def create_account
      @account = Account.create_with_owner(
        account: { name: full_name },
        owner: { identity: identity }
      )
    end
end
```

**Location:**

- Place in `app/models/` directory (not a separate `services/` directory)
- They are domain objects, not a special "service layer"

**Patterns:**

- Use `ActiveModel::Model` for form-like objects
- Private `initialize` when using factory methods
- Class methods for factory patterns when appropriate

  ```ruby
  class Notifier
    class << self
      def for(source)
        # factory logic
      end
    end

    private
      def initialize(source)
        @source = source
      end
  end
  ```

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

### Method Ordering: Vertical Invocation Order

Order methods based on their call order to show flow:

```ruby
class SomeClass
  def some_method
    method_1
    method_2
  end

  private
    def method_1
      method_1_1
      method_1_2
    end

    def method_1_1
      # ...
    end

    def method_1_2
      # ...
    end

    def method_2
      # ...
    end
end
```

This combines with the step-down rule: public methods first, then private methods ordered by their invocation flow.

### Conditional Returns

**Prefer expanded conditionals over guard clauses:**

```ruby
# Good
def todos_for_new_group
  if ids = params.require(:todolist)[:todo_ids]
    @bucket.recordings.todos.find(ids.split(","))
  else
    []
  end
end

# Bad
def todos_for_new_group
  ids = params.require(:todolist)[:todo_ids]
  return [] unless ids
  @bucket.recordings.todos.find(ids.split(","))
end
```

**Exception:** Use guard clauses when:

- The return is at the very beginning of the method
- The main method body is non-trivial (several lines)

  ```ruby
  def after_recorded_as_commit(recording)
    return if recording.parent.was_created?

    if recording.was_created?
      broadcast_new_column(recording)
    else
      broadcast_column_change(recording)
    end
  end
  ```

### Visibility Modifiers

**No newline under visibility modifiers, indent content under them:**

```ruby
class SomeClass
  def public_method
    # ...
  end

  private
    def private_method_1
      # ...
    end

    def private_method_2
      # ...
    end
end
```

**For modules with only private methods:**

```ruby
module SomeModule
  private

  def some_private_method
    # ...
  end
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
- Form object with validation? Service object OK
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

## Other Conventions

**Bang methods:**

- Only use **!** when there's a non-bang counterpart
- Don't use **!** to merely flag "destructive" actions

  ```ruby
  # Good (has both versions)
  def save / save!

  # Bad (no non-bang version)
  def delete_everything!  # Just name it delete_everything
  ```

**Custom errors:**

- Rarely needed - prefer standard Ruby/Rails exceptions
- When needed, define inline in the class that uses them

  ```ruby
  class Webhook::Delivery
    class ResponseTooLarge < StandardError; end

    def perform_request
      # ...
      raise ResponseTooLarge if bytes_read > MAX_RESPONSE_SIZE
    end
  end
  ```

**Current context:**

- Use `Current` attributes for request-scoped values
- Common: `Current.user`, `Current.account`, `Current.identity`

## Golden Rule

When in doubt, do it the simplest Rails way possible. Add complexity only when you have proof you need it.

## Summary Checklist

When writing new code, verify:

- [ ] Controllers are thin, call model methods directly
- [ ] Models contain business logic with intention-revealing methods
- [ ] Concerns are used to organize related behavior
- [ ] Model-specific concerns go in `app/models/model_name/`
- [ ] Shared concerns go in `app/models/concerns/` or `app/controllers/concerns/`
- [ ] Service objects (POROs) are in `app/models/` only when appropriate
- [ ] Step-down rule: public methods first, then private methods
- [ ] Methods ordered by invocation flow within visibility sections
- [ ] Expanded conditionals instead of guard clauses (unless at method start)
- [ ] Private methods are indented under `private` keyword
- [ ] No unnecessary bang methods or custom errors
- [ ] Rails 8 defaults used (Solid Stack, Hotwire, etc.)

## Additional Reference

- Rails Doctrine: <https://rubyonrails.org/doctrine>
- Rails 8 Release Notes: <https://guides.rubyonrails.org/8_0_release_notes.html>
