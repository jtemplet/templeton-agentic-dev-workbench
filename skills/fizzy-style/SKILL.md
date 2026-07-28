---
name: fizzy-style
description: Use when writing controllers, models, or concerns in this codebase - enforces Fizzy's vanilla Rails style and conventions
---

# Fizzy Coding Style

This skill captures the Ruby on Rails coding conventions used in the Fizzy codebase. Follow these patterns when writing new code or modifying existing code.

## Core Philosophy

- **Vanilla Rails**: Thin controllers, rich domain models. No service layer between controllers and models.
- **Intention-revealing APIs**: Model methods should clearly express business intent (e.g., `@card.gild`, `@board.close`)
- **Simplicity over cleverness**: Clear, readable code is preferred over clever abstractions
- **Concerns for composition**: Use concerns to mix in related behavior, keep models focused

## Controllers

### Structure and Organization

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

### Controller Conventions

**Use concerns for shared behavior:**

- Concerns live in `app/controllers/concerns/`
- Use for setting up scoped resources (e.g., `CardScoped`, `BoardScoped`)
- Use for cross-cutting concerns (e.g., `Authentication`, `Authorization`)

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

## Models

### Structure and Organization

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

### Model Conventions

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

## Concerns

### Controller Concerns

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

### Model Concerns

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

## Service Objects (POROs)

**When to use:**

- Complex multi-step operations (e.g., `Signup` for account creation)
- Form objects that need validation but aren't persisted
- Coordinating objects that orchestrate multiple models
- Parsing or transformation logic

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

## Conditional Returns

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

## Visibility Modifiers

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

## Method Ordering

**Vertical invocation order:**
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

## Other Conventions

**Bang methods:**

- Only use `!` when there's a non-bang counterpart
- Don't use `!` to merely flag "destructive" actions

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

## Summary Checklist

When writing new code, verify:

- [ ] Controllers are thin, call model methods directly
- [ ] Models contain business logic with intention-revealing methods
- [ ] Concerns are used to organize related behavior
- [ ] Model-specific concerns go in `app/models/model_name/`
- [ ] Shared concerns go in `app/models/concerns/` or `app/controllers/concerns/`
- [ ] Service objects (POROs) are in `app/models/` if needed
- [ ] Expanded conditionals instead of guard clauses (unless at method start)
- [ ] Private methods are indented under `private` keyword
- [ ] Methods ordered by invocation flow
- [ ] No unnecessary bang methods or custom errors
