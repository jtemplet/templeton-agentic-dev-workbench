---
name: style-fizzy
description: Use when writing controllers, models, concerns, or POROs in the Fizzy codebase - enforces Fizzy's vanilla Rails house style and conventions
---

# Fizzy Coding Style

Fizzy's vanilla-Rails house style: thin controllers, rich domain models, no service layer. This skill adds the Fizzy-specific Rails deltas and worked examples on top of the universal style core injected each session. Follow these patterns when writing new code or modifying existing code in this codebase.

## When to Use / When NOT to Use

Use when:

- Writing or modifying controllers, models, concerns, or POROs in the Fizzy codebase.
- Deciding where logic belongs (controller vs model vs concern vs PORO) in Fizzy.
- Reviewing Fizzy code for adherence to the conventions below.

Do NOT use when:

- Working in a non-Fizzy Rails codebase: use `style-rails` instead.
- Writing non-Rails Ruby (plain gems, scripts, CLIs): the Fizzy Rails deltas do not apply.
- Editing generated scaffolding you have been told to leave as-is.

## Universal Core (injected)

The "TRUE code" posture and the 9 universal principles (wait for duplication, small single-purpose units, simple interfaces, inject dependencies, tell don't ask, compose over inherit, fail fast, read top-down, names that document) are injected separately every session from `hooks/style-core.md`. This skill does not restate them; it carries only the Fizzy-specific Rails mechanics that sit on top.

## Fizzy Principles

1. **Stay vanilla Rails.** Thin controllers, rich domain models. There is no service layer between controllers and models; business logic lives in models and concerns, not in a `services/` tier.

2. **Give models intention-revealing APIs.** Model methods express business intent that controllers call directly.

   ```ruby
   # Bad - controller assembles the mechanics
   def create
     @card.goldness ||= Goldness.create!(card: @card)
   end

   # Good - intention-revealing model API
   def create
     @card.gild
   end
   ```

3. **Favor simplicity over cleverness.** Clear, readable code beats clever abstractions. Reach for plain Rails before introducing indirection.

4. **Use concerns for composition.** Mix related behavior in via concerns; keep the primary model file focused.

   - Controller concerns: `app/controllers/concerns/` (e.g., `CardScoped`, `Authentication`).
   - Shared model concerns: `app/models/concerns/` (e.g., `Searchable`, `Eventable`).
   - Model-specific concerns: `app/models/model_name/` (e.g., `Card::Golden`, `Board::Publishable`).
   - Use `extend ActiveSupport::Concern`, an `included do` block for callbacks/associations/scopes, and a `class_methods` block for class-level extensions.

5. **Order controller elements predictably.** Class-level declarations (`include`, `before_action`, `layout`) first, then public action methods in RESTful order (index, show, new, create, edit, update, destroy), then `private`, then private helpers.

6. **Order model elements predictably.** Concerns (`include`), associations, attachments/rich text, callbacks, scopes, delegations, public methods, `private`, private methods.

7. **Design resource-oriented routes.** Model actions as CRUD on resources. When an action does not fit standard CRUD, introduce a new resource rather than a custom action.

   ```ruby
   # Bad - custom action
   resources :cards do
     post :close
   end

   # Good - new resource
   resources :cards do
     resource :closure
   end
   ```

8. **Call model methods directly from controllers.** Keep business logic in models; controllers orchestrate the response.

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

9. **Use `params.expect` for strong parameters.** Rails 8 `params.expect`, defined in the private section.

   ```ruby
   private
     def card_params
       params.expect(card: [ :title, :description, :created_at ])
     end
   ```

10. **Set up instance variables with `before_action`.** Define the setup methods in the private section.

    ```ruby
    before_action :set_board, only: %i[ create ]

    private
      def set_board
        @board = Current.user.boards.find params[:board_id]
      end
    ```

11. **Define queries as scopes; lean on association defaults.** Use lambda syntax for all scopes and chain them for complex queries. Use `default:` for automatic association assignment.

    ```ruby
    scope :latest, -> { order last_active_at: :desc, id: :desc }
    scope :closed, -> { joins(:closure) }
    scope :closed_by, ->(users) { closed.where(closures: { user_id: Array(users) }) }

    belongs_to :account, default: -> { board.account }
    belongs_to :creator, class_name: "User", default: -> { Current.user }
    ```

12. **Reach for a PORO (service object) only when justified, and keep it in `app/models`.** Justified cases: complex multi-step operations (e.g., `Signup`), form objects that validate but do not persist, coordinators orchestrating multiple models, parsing/transformation logic. They are domain objects, not a special "service layer", so they do not get a `services/` directory. Use `ActiveModel::Model` for form-like objects; use a private `initialize` with class-level factory methods when appropriate.

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

13. **Prefer expanded conditionals over guard clauses.** Show both branches.

    ```ruby
    # Bad - guard clause
    def todos_for_new_group
      ids = params.require(:todolist)[:todo_ids]
      return [] unless ids
      @bucket.recordings.todos.find(ids.split(","))
    end

    # Good - expanded conditional
    def todos_for_new_group
      if ids = params.require(:todolist)[:todo_ids]
        @bucket.recordings.todos.find(ids.split(","))
      else
        []
      end
    end
    ```

    Exception: use a guard clause when the return is at the very beginning of the method and the main body is non-trivial.

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

14. **Indent content under visibility modifiers; no newline directly under them.**

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

    For modules whose methods are all private, keep the modifier flush with a blank line:

    ```ruby
    module SomeModule
      private

      def some_private_method
        # ...
      end
    end
    ```

15. **Order methods by invocation flow (vertical order).** A method appears before the methods it calls, so the file reads top-down.

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

16. **Use a bang method only when a non-bang counterpart exists.** Do not append `!` merely to flag a destructive action.

    ```ruby
    # Good - has both versions
    def save / save!

    # Bad - no non-bang version exists
    def delete_everything!  # just name it delete_everything
    ```

17. **Define custom errors inline and rarely.** Prefer standard Ruby/Rails exceptions; when a custom error is warranted, define it inside the class that raises it.

    ```ruby
    class Webhook::Delivery
      class ResponseTooLarge < StandardError; end

      def perform_request
        # ...
        raise ResponseTooLarge if bytes_read > MAX_RESPONSE_SIZE
      end
    end
    ```

18. **Use `Current` for request-scoped values.** Common attributes: `Current.user`, `Current.account`, `Current.identity`.

## Anti-Patterns

- **Custom controller action instead of a resource.** Why it hurts: routes drift from CRUD, controllers grow ad-hoc verbs. Corrected: introduce a resource (`resource :closure`) rather than `post :close`.

- **Business logic in the controller instead of the model.** Why it hurts: logic becomes untestable in isolation and is not reusable; controllers stop being thin. Corrected: move it into an intention-revealing model method (`@card.gild`) and call it directly.

- **Guard clause where an expanded conditional reads better.** Why it hurts: a short method's early `return` hides the alternative branch and the method's shape. Corrected: use `if/else` for short methods; reserve guard clauses for early returns guarding a non-trivial body.

- **Gratuitous bang method.** Why it hurts: `!` signals "the dangerous variant of a safe method", so a lone `delete_everything!` lies about having a counterpart. Corrected: drop the `!` unless a non-bang version exists.

## Worked Examples

### Controller: thin, before_action setup, params.expect

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

The matching controller concern keeps scoped-resource setup out of the controller:

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

### Model: rich domain, ordered elements, intention-revealing methods

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

Behavior that deserves its own file lives in a model-specific concern:

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

Shared behavior lives in a concern under `app/models/concerns/`:

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

### Service object (PORO): justified, lives in app/models

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

## Apply Workflow

1. Decide where the logic belongs: model method (default for business logic), concern (shared or model-specific behavior), controller (orchestration only), or PORO (only if justified per principle 12).
2. If it is a new behavior on a resource, prefer adding/using a RESTful route and a thin controller action that calls a model method.
3. Place new concerns in the correct directory (`app/controllers/concerns/`, `app/models/concerns/`, or `app/models/model_name/`).
4. Order elements per the controller/model conventions; order methods by invocation flow.
5. Write intention-revealing model APIs; use `params.expect`, `before_action` setup, scopes, association defaults, and `Current` as the conventions dictate.
6. Prefer expanded conditionals; reserve guard clauses for the documented exception.
7. Apply visibility-modifier indentation; avoid gratuitous bang methods and custom errors.
8. Run the project linter and tests before finishing.

## Quality Checklist

- [ ] Controllers are thin and call model methods directly.
- [ ] Models contain business logic with intention-revealing methods.
- [ ] Concerns organize related behavior; controller/model element order is correct.
- [ ] Model-specific concerns are in `app/models/model_name/`; shared concerns in `app/models/concerns/` or `app/controllers/concerns/`.
- [ ] Service objects (POROs) live in `app/models/` and are only introduced when justified.
- [ ] Routes are resource-oriented; no custom actions where a resource fits.
- [ ] Strong params use `params.expect`; setup uses `before_action`.
- [ ] Scopes use lambda syntax; association defaults are used where appropriate.
- [ ] Expanded conditionals instead of guard clauses (unless guarding a non-trivial body at method start).
- [ ] Private methods are indented under `private`; methods ordered by invocation flow.
- [ ] No unnecessary bang methods or custom errors; `Current` used for request-scoped values.
