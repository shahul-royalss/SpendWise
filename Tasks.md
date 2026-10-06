# Tasks

Build plan for the hackathon day. Items are checked off as they land on `main`.

## 1. Setup

- [x] Django 5.2 project (`config`) with `core`, `accounts` and `tracker` apps
- [x] Settings from environment variables, `.env.example`, secure defaults
- [x] Vendor Bootstrap 5.3.8 and Bootstrap Icons, serve with WhiteNoise
- [x] Ruff, coverage and pinned requirements

## 2. Data layer

- [x] `Category`, `Budget` and `Expense` models with timestamps
- [x] Check constraints (amount > 0, limit > 0) and unique constraints (category name per user, one budget per category per month)
- [x] `PROTECT` on `Expense.category`, `CASCADE` on budgets
- [x] Per-user querysets: `for_user`, `in_month`, `for_month`, `total`
- [x] Initial migration

## 3. Authentication

- [x] Register (auto login), login, logout with POST
- [x] Redirect logged-in users away from login and register
- [x] `LOGIN_URL` so protected pages redirect to login

## 4. Categories

- [x] List, detail, create, update and delete views
- [x] Case-insensitive unique names per user
- [x] Safe delete: move expenses to another category or block

## 5. Budgets

- [x] Month field (`YYYY-MM`) stored as the first day of the month
- [x] List for a month with spent, remaining and status
- [x] Create, update and delete, with duplicates rejected
- [x] Copy last month's budgets

## 6. Expenses

- [x] `POST /expenses/create/`: 302 to the dashboard on success, 200 with errors
- [x] Category accepted as id or name, limited to the user's own categories
- [x] Reject zero, negative and badly formatted amounts
- [x] List with filters, total and pagination; update; delete
- [x] Flash a warning or danger message when an expense crosses a threshold

## 7. Dashboard and alerts

- [x] `services.py`: `get_alert_level`, `usage_percentage`, monthly summary, category spending
- [x] Summary cards, alert banners, category breakdown with progress bars and badges
- [x] Month navigation with `?month=`
- [x] Recent expenses

## 8. Quality and security

- [x] Unit tests: alert thresholds, budget calculations, dates, money formatting
- [x] Model, form and view tests, including per-user isolation for every URL
- [x] Content-Security-Policy and Permissions-Policy headers
- [x] Ruff clean, coverage of 90% or more (currently 99%)

## 9. Delivery

- [x] `seed_demo` management command
- [x] README with setup, tests, architecture and API behaviour
- [x] GitHub Actions CI on Python 3.10 to 3.13
- [x] Dockerfile
- [x] Push to the public GitHub repository

## Ideas for later

- [ ] Charts for month-over-month spending
- [ ] CSV export of expenses
- [ ] Recurring expenses (rent, subscriptions)
- [ ] Email reminder when a budget reaches 80%
