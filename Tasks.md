# Tasks

Build plan for the hackathon day. Items are checked off as they land on `main`.

## 1. Setup

- [ ] Django 5.2 project (`config`) with `core`, `accounts` and `tracker` apps
- [ ] Settings from environment variables, `.env.example`, secure defaults
- [ ] Vendor Bootstrap 5.3.8 and Bootstrap Icons, serve with WhiteNoise
- [ ] Ruff, coverage and pinned requirements

## 2. Data layer

- [ ] `Category`, `Budget` and `Expense` models with timestamps
- [ ] Check constraints (amount > 0, limit > 0) and unique constraints (category name per user, one budget per category per month)
- [ ] `PROTECT` on `Expense.category`, `CASCADE` on budgets
- [ ] Per-user querysets: `for_user`, `in_month`, `for_month`, `total`
- [ ] Initial migration

## 3. Authentication

- [ ] Register (auto login), login, logout with POST
- [ ] Redirect logged-in users away from login and register
- [ ] `LOGIN_URL` so protected pages redirect to login

## 4. Categories

- [ ] List, detail, create, update and delete views
- [ ] Case-insensitive unique names per user
- [ ] Safe delete: move expenses to another category or block

## 5. Budgets

- [ ] Month field (`YYYY-MM`) stored as the first day of the month
- [ ] List for a month with spent, remaining and status
- [ ] Create, update and delete, with duplicates rejected
- [ ] Copy last month's budgets

## 6. Expenses

- [ ] `POST /expenses/create/`: 302 to the dashboard on success, 200 with errors
- [ ] Category accepted as id or name, limited to the user's own categories
- [ ] Reject zero, negative and badly formatted amounts
- [ ] List with filters, total and pagination; update; delete
- [ ] Flash a warning or danger message when an expense crosses a threshold

## 7. Dashboard and alerts

- [ ] `services.py`: `get_alert_level`, `usage_percentage`, monthly summary, category spending
- [ ] Summary cards, alert banners, category breakdown with progress bars and badges
- [ ] Month navigation with `?month=`
- [ ] Recent expenses

## 8. Quality and security

- [ ] Unit tests: alert thresholds, budget calculations, dates, money formatting
- [ ] Model, form and view tests, including per-user isolation for every URL
- [ ] Content-Security-Policy and Permissions-Policy headers
- [ ] Ruff clean, coverage of 90% or more

## 9. Delivery

- [ ] `seed_demo` management command
- [ ] README with setup, tests, architecture and API behaviour
- [ ] GitHub Actions CI
- [ ] Dockerfile
- [ ] Push to GitHub and submit the link
