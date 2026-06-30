---
name: style-rails
description: Use when generating Rails code, evaluating gems, or making Rails architectural decisions - enforces the Rails 8 Way (convention over configuration, Solid Stack over external dependencies, Hotwire)
---

# Rails Conventions

Enforce "The Rails 8 Way": convention over configuration, integrated systems, and Rails-native solutions over external frameworks. This skill carries only the Rails-8-specific deltas on top of the injected universal style core: trust Rails defaults and add complexity only when you have proof you need it.

## When to Use / When NOT to Use

Use when:

- Generating or refactoring Rails code
- Evaluating whether to add a gem or framework
- Making architectural decisions
- Choosing between Rails-native vs third-party solutions

Do NOT use when:

- Non-Rails Ruby projects
- Rails 7 or earlier (some features are Rails 8-specific)
- Projects explicitly using alternative patterns (Trailblazer, Hanami)

## Universal Core (injected)

The universal style core ("TRUE code" plus the 9 universal principles, including the step-down rule and the posture of correctness > speed, simplicity > cleverness, explicit > magic, start simple) is injected separately each session from `hooks/style-core.md`. Do not restate it here. This skill references it where Rails layers specific mechanics on top, e.g. the Rails method-ordering rules build on the core's step-down principle.

## Rails Principles

Numbered, imperative. Each is paired with a concrete BAD -> GOOD.

### 1. Trust Rails defaults (convention over configuration)

Use Rails naming conventions, the full integrated stack (ActiveRecord, not a separate ORM), and expressive vanilla Rails. Embrace progress over stability (Hotwire, not jQuery). Default answer to "should I add this?" is no: prefer the Rails-native path.

```ruby
# Bad: manual joins, hand-rolled query plumbing
User.connection.execute("SELECT * FROM posts WHERE user_id = #{id}")

# Good: associations and ActiveRecord
class User < ApplicationRecord
  has_many :posts
end
current_user.posts
```

### 2. Use the Solid Stack, not external dependencies

Rails 8 ships integrated replacements for the usual external services. Reach for these before adding Sidekiq, Redis, or React.

- Solid Queue (background jobs, not Sidekiq)
- Solid Cache (caching, not Redis)
- Solid Cable (WebSockets, not Redis)
- Authentication generator (not Devise for new apps)
- Propshaft (assets)
- Hotwire: Turbo + Stimulus (not React)

```ruby
# Bad
gem "sidekiq"
gem "redis"

# Good: nothing to add, use the built-ins
class ReportJob < ApplicationJob   # Solid Queue
  queue_as :default
end
```

### 3. Keep controllers thin; call model methods directly

Controllers call model APIs and orchestrate the response. Business logic lives in models, not controllers.

```ruby
# Bad: logic in the controller
def create
  @card = @board.cards.new(card_params)
  @card.goldness = Goldness.new unless @card.goldness
  @card.save!
  # ...
end

# Good: controller calls an intention-revealing model method
def create
  @card.gild
  respond_to do |format|
    format.turbo_stream { render_card_replacement }
    format.json { head :no_content }
  end
end
```

Element order in a controller: (1) class-level declarations (`include`, `before_action`, `layout`), (2) public action methods in RESTful order (index, show, new, create, edit, update, destroy), (3) `private` keyword, (4) private helpers.

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

### 4. Prefer many small RESTful controllers over fat ones

Create RESTful controllers prolifically. Each action gets focused context. When a filter or state appears, give it its own controller instead of branching.

```ruby
# Bad: one controller branching on a filter param
class MessagesController < ApplicationController
  def index
    case params[:filter]
    when 'drafts' then @messages = current_user.messages.drafts
    when 'trash' then @messages = current_user.messages.trashed
    else @messages = current_user.messages.inbox
    end
  end
end

# Good: one focused controller per state
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

### 5. Use resource-oriented routing; introduce a resource, not a custom action

When an action does not fit standard CRUD, introduce a new resource rather than bolting a custom action onto an existing controller.

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

### 6. Build rich domain models with intention-revealing methods

Models hold business logic, not just data access. Methods read like domain verbs.

```ruby
# Bad: caller assembles the steps
card.create_goldness! unless card.goldness.present?

# Good: model exposes intent
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

Element order in a model: (1) concerns via `include`, (2) associations, (3) attachments and rich text, (4) callbacks, (5) scopes, (6) delegations, (7) public methods, (8) `private` keyword, (9) private methods.

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

### 7. Use concerns heavily to organize related behavior

Shared concerns live in `app/models/concerns/` or `app/controllers/concerns/`; model-specific concerns live in `app/models/model_name/`. Use `extend ActiveSupport::Concern`, an `included do` block for callbacks/helpers, and keep methods private unless explicitly needed as helpers. A `class_methods` block adds class-level extensions.

```ruby
# Bad: scoping logic copy-pasted into every controller
class CardsController < ApplicationController
  before_action do
    @card = Current.user.accessible_cards.find_by!(number: params[:card_id])
    @board = @card.board
  end
end

# Good: shared controller concern
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

Shared model concern (in `app/models/concerns/`):

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

Model-specific concern (in `app/models/card/`), encapsulating its own associations, scopes, and methods:

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

### 8. Express queries as scopes

Define common queries as lambda scopes and chain them for complex queries.

```ruby
# Bad: inline conditions scattered across callers
Card.where(published: true).where("created_at > ?", 1.week.ago)

# Good: named, chainable scopes
scope :latest,    -> { order last_active_at: :desc, id: :desc }
scope :closed,    -> { joins(:closure) }
scope :closed_by, ->(users) { closed.where(closures: { user_id: Array(users) }) }
```

Validations stay in the model too:

```ruby
class User < ApplicationRecord
  validates :email, presence: true, uniqueness: true
  validates :age, numericality: { greater_than_or_equal_to: 18 }
end
```

### 9. Use `params.expect` for strong parameters

Use the Rails 8 `params.expect` API and define param methods in the private section.

```ruby
# Bad: legacy require/permit
def card_params
  params.require(:card).permit(:title, :description, :created_at)
end

# Good: Rails 8 expect
private
  def card_params
    params.expect(card: [ :title, :description, :created_at ])
  end
```

Use `before_action` callbacks for instance-variable setup, with setup methods private:

```ruby
before_action :set_board, only: %i[ create ]

private
  def set_board
    @board = Current.user.boards.find params[:board_id]
  end
```

Also lean on association `default:` for automatic assignment:

```ruby
belongs_to :account, default: -> { board.account }
belongs_to :creator, class_name: "User", default: -> { Current.user }
```

### 10. Add service objects (POROs) only when justified, in app/models

Keep models focused and use concerns for shared behavior. Reach for a PORO only for: complex multi-model transactions, external API integrations with significant logic, business processes that map to no single model, form objects that validate but do not persist, coordinating objects orchestrating multiple models, or parsing/transformation logic. For single-model CRUD and shared behavior, use model methods and concerns instead. Place POROs in `app/models/` (not a separate `services/` directory); they are domain objects, not a "service layer."

```ruby
# Bad: a service for plain CRUD
class CreateUserService
  def call(attrs) = User.create!(attrs)
end

# Good: a PORO for a genuine multi-step process
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

Use a private `initialize` with class-method factories when appropriate:

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

### 11. Order methods public-then-private, by vertical invocation flow

This builds on the universal step-down principle (see the injected core). Rails-specific mechanics: public methods first, then `private`, then private helpers ordered by the order they are called. No newline under a visibility modifier; indent the methods beneath it.

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

For modules with only private methods, the modifier sits flush:

```ruby
module SomeModule
  private

  def some_private_method
    # ...
  end
end
```

### 12. Prefer expanded conditionals over guard clauses

Default to expanded `if/else` rather than early-return guards.

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

Exception: use a guard clause when the return is at the very start of the method and the main body is non-trivial.

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

### 13. Use bang methods, custom errors, and Current sparingly

- Bang methods: only use `!` when a non-bang counterpart exists; do not use `!` merely to flag "destructive."
- Custom errors: rarely needed; prefer standard Ruby/Rails exceptions, and when needed define them inline in the class that uses them.
- Request-scoped state: use `Current` attributes (`Current.user`, `Current.account`, `Current.identity`).

```ruby
# Bad: bang with no non-bang counterpart
def delete_everything!   # just name it delete_everything
end

# Good: save / save! pair, custom error defined inline
class Webhook::Delivery
  class ResponseTooLarge < StandardError; end

  def perform_request
    # ...
    raise ResponseTooLarge if bytes_read > MAX_RESPONSE_SIZE
  end
end
```

## Anti-Patterns

Each is bad -> why -> corrected.

- **Repository Pattern.** Bad: `UserRepository#find(id)` wrapping `User.find(id)`. Why: it adds a redundant layer over ActiveRecord, which is already the repository. Corrected: call `User.find(id)` (and scopes/associations) directly.
- **Excessive Service Objects.** Bad: `CreateUserService`, `UpdateUserService`, `DeleteUserService` for standard CRUD. Why: it scatters trivial logic into ceremony objects that duplicate ActiveRecord. Corrected: use ActiveRecord methods and callbacks; reserve POROs for genuinely complex processes (see principle 10).
- **God Objects.** Bad: a `UserManager` holding every user-related method. Why: it concentrates unrelated responsibilities and resists testing. Corrected: spread responsibilities across models, controllers, mailers, and concerns.
- **Fighting REST.** Bad: custom `register`, `login`, `forgot_password` actions on one controller. Why: it overloads a single controller and breaks resource semantics. Corrected: create separate RESTful controllers (`RegistrationsController`, `SessionsController`, `PasswordResetsController`).
- **Over-Engineering.** Bad: microservices, Redis clusters, message queues, or GraphQL added prematurely. Why: it pays for scale and flexibility you cannot prove you need. Corrected: start simple with the integrated Rails stack; scale when you have proof.

### Quick Decision Trees

Should I create a service object?

- Single model operation? Use model + callbacks.
- Multiple models in a transaction? Service object OK.
- External API integration? Service object OK.
- Form object with validation? Service object OK.
- Otherwise? Use model methods or a concern.

Should I create a new controller?

- One of the 7 REST actions? Add to the existing controller.
- State/filter of a resource (drafts, archived)? Create a nested controller.
- Operating on a relationship (like, bookmark)? Create a singular resource controller.
- Otherwise? Rethink, you might be fighting REST.

## Worked Examples

### Step-down: ArticlePublisher (before / after)

The public interface reads as a narrative; details follow below. (This applies the injected core's step-down principle with Rails visibility mechanics.)

Good, reads top-to-bottom:

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

Read `publish` first and you understand what happens; the steps follow in call order.

Bad, forces the reader to jump around:

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

The reader must jump to the bottom to find the public API, then back up for details. Chaos.

### Controller + model structure (the Rails Way assembled)

The thin controller (principle 3) and the rich model (principle 6) work together: the controller calls `@card.gild`, all the behavior lives in the `Card::Golden` concern (principle 7), and routing introduces a `resource :closure` rather than a custom action (principle 5). See the `CardsController`, `Card`, and `Card::Golden` listings above for the full assembled shape.

## Apply Workflow

When writing or refactoring Rails code, work the steps in order:

1. **Identify the resource.** Frame the change as CRUD on a resource. If it does not fit, introduce a new resource or a nested/singular-resource controller (principle 5) rather than a custom action.
2. **Run the "Should I add this gem?" framework.**
   - Does Rails 8 provide this? Use the Rails version.
   - Does Rails have a conventional way? Use the convention.
   - Will this simplify or complicate? Choose simplicity.
   - Default: NO, use the Rails-native solution. Exception: only when Rails genuinely lacks the functionality.
3. **Run the "Should I create a service object / new controller?" decision trees** (see Anti-Patterns above). Default to model methods, concerns, and many small RESTful controllers.
4. **Place behavior correctly.** Logic in rich models; shared behavior in concerns (`app/models/concerns/`, `app/controllers/concerns/`); model-specific concerns in `app/models/model_name/`; justified POROs in `app/models/`.
5. **Order the file.** Apply the element orders (controller, model) and the public-then-private, invocation-order method layout (principle 11).
6. **Use Rails 8 plumbing.** `params.expect`, `before_action` setup, Solid Stack, Hotwire, `Current` for request state.
7. **Apply the Golden Rule.** When in doubt, do it the simplest Rails way possible. Add complexity only when you have proof you need it.

### Solid Stack quick reference

Solid Queue (background jobs):

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

Solid Cache:

```ruby
Rails.cache.fetch(["product", id, "stats"], expires_in: 1.hour) do
  expensive_calculation
end
```

Authentication generator:

```bash
bin/rails generate authentication
```

Creates User model, Session model, SessionsController, password reset, and email confirmation.

## Quality Checklist

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
- [ ] Private methods are indented under the `private` keyword
- [ ] `params.expect` used for strong parameters
- [ ] No unnecessary bang methods or custom errors
- [ ] Rails 8 defaults used (Solid Stack, Hotwire, etc.)

## Additional Reference

- Rails Doctrine: <https://rubyonrails.org/doctrine>
- Rails 8 Release Notes: <https://guides.rubyonrails.org/8_0_release_notes.html>
