# Rails 8 Way - Quick Reference

## Common Patterns

### Authentication (Rails 8 Built-in)

```ruby
# Generate
bin/rails generate authentication

# Controller
class SessionsController < ApplicationController
  def create
    if user = User.authenticate_by(email: params[:email], password: params[:password])
      start_new_session_for(user)
      redirect_to root_path
    else
      render :new, status: :unprocessable_entity
    end
  end
end

# Model
class User < ApplicationRecord
  has_secure_password
  has_many :sessions, dependent: :destroy
  
  normalizes :email_address, with: ->(e) { e.strip.downcase }
  generates_token_for :password_reset, expires_in: 15.minutes
end
```

### Background Jobs (Solid Queue)

```ruby
# Job
class ReportJob < ApplicationJob
  queue_as :default
  
  def perform(user_id)
    user = User.find(user_id)
    ReportMailer.send_report(user, generate_report(user)).deliver_now
  end
end

# Enqueue
ReportJob.perform_later(current_user.id)
```

### Caching (Solid Cache)

```ruby
# Fragment caching in views
<% cache @product do %>
  <%= render @product %>
<% end %>

# Low-level caching
Rails.cache.fetch(["product", product.id, "stats"], expires_in: 1.hour) do
  expensive_calculation
end
```

### Real-time (Solid Cable + Turbo)

```ruby
# Model
class Comment < ApplicationRecord
  belongs_to :post
  after_create_commit -> { broadcast_append_to post, :comments }
end

# View
<%= turbo_stream_from @post, :comments %>
<div id="comments">
  <%= render @post.comments %>
</div>
```

### Hotwire Patterns

```erb
<!-- Turbo Frame (lazy load) -->
<%= turbo_frame_tag "comments", src: post_comments_path(@post), loading: :lazy %>

<!-- Turbo Stream (live updates) -->
<%= turbo_stream_from @post %>

<!-- Stimulus Controller -->
<div data-controller="dropdown">
  <button data-action="click->dropdown#toggle">Menu</button>
  <div data-dropdown-target="menu" class="hidden">...</div>
</div>
```

### RESTful Controllers (Many Small Ones)

```ruby
# Instead of one fat controller with filters
class Messages::DraftsController < ApplicationController
  def index
    @messages = current_user.messages.drafts
  end
end

class Messages::StarredController < ApplicationController
  def index
    @messages = current_user.messages.starred
  end
end
```

### Models with Concerns

```ruby
# app/models/concerns/trackable.rb
module Trackable
  extend ActiveSupport::Concern
  
  included do
    after_create :track_creation
  end
  
  private
  def track_creation
    Analytics.track("#{self.class.name} Created", id: id)
  end
end

# app/models/user.rb
class User < ApplicationRecord
  include Trackable
end
```

### Scopes for Queries

```ruby
class Post < ApplicationRecord
  scope :published, -> { where(published: true) }
  scope :recent, -> { order(created_at: :desc).limit(10) }
  scope :by_author, ->(author) { where(author: author) }
end

# Chainable
Post.published.recent.by_author("DHH")
```

## Command Snippets

```bash
# New Rails 8 app
rails new myapp --database=postgresql

# Generate authentication
bin/rails generate authentication

# Generate model with associations
rails g model Post title:string body:text user:references published:boolean

# Generate namespaced controller
rails g controller messages/drafts index

# Run background jobs
bin/jobs

# Database operations
rails db:create db:migrate db:seed

# Console
rails console

# Tests
rails test
rails test:system
```

## Configuration Snippets

```ruby
# config/environments/production.rb
config.active_job.queue_adapter = :solid_queue
config.cache_store = :solid_cache_store
config.action_cable.adapter = :solid_cable

# config/routes.rb
resources :posts do
  resources :comments, only: [:create]
  
  namespace :posts do
    resource :publication, only: [:create, :destroy]
  end
end
```
