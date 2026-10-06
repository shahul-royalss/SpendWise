# SpendWise: Personal Expense Tracker with Budget Alerts

[![CI](https://github.com/shahul-royalss/personal-expense-tracker/actions/workflows/ci.yml/badge.svg)](https://github.com/shahul-royalss/personal-expense-tracker/actions/workflows/ci.yml)

SpendWise is a Django web app for logging daily expenses, grouping them into your own categories and setting a monthly budget for each category. It keeps a running total and warns you **at 80%** of a budget and again **at 100%**, so you find out about overspending while there is still time to react.

Built for the SVCET Hackathon (powered by LearnSquare) with **Django 5.2, SQLite and Django Templates + Bootstrap 5.3**.

## Features

- **Accounts**: register, log in and log out. Logging out happens on POST; opening `/accounts/logout/` directly shows a confirmation page. Every page except login and register requires an account.
- **Categories**: create, view, edit and delete your own categories. Names are unique per user, ignoring case.
- **Monthly budgets**: one limit per category per month, with create, edit and delete. Last month's budgets can be copied with one click.
- **Expenses**: log amount, date, category and optional notes. `POST /expenses/create/` returns 302 on success and 200 with errors, as the brief specifies. The list supports filters, totals and pagination.
- **Dashboard**:
  - total spent this month
  - total budget
  - remaining budget, with a usage ring
  - a category breakdown table with progress bars and status badges
  - a "where your money went" donut chart
  - a six-month spending trend with budget markers
  - alert banners and recent expenses
  - previous / next month navigation
- **Budget alerts**: badges for Normal (< 80%), Warning (>= 80%) and Danger (>= 100%), plus a toast notification the moment an expense crosses a threshold.
- **Safe deletes**: a category that still has expenses can't be deleted until you choose where to move them. The database also protects the link with `on_delete=PROTECT`.
- **Strict data isolation**: every query is filtered by the logged-in user. Other users' records return 404.
- **Demo data**: `python manage.py seed_demo` creates an account with six months of history that shows every alert state.

### Interface

The UI is Bootstrap 5.3 with a custom design layer (`static/css/app.css`). Nothing is loaded from a CDN, so it looks the same offline.

- **Theme**: light and dark themes, following the system setting, plus a toggle that is remembered per browser.
- **Look**: a "ledger" palette:
  - warm paper backgrounds and ink text
  - a deep pine brand colour with one lime accent
  - muted green / ochre / brick for budget states
  - IBM Plex Sans, self-hosted
  - flat surfaces with hairline borders, no gradients or glass effects
- **Charts**: drawn in SVG and CSS, with no chart library. They include usage rings, a spending donut and the trend bars.
- **Motion** (short and quiet):
  - sections fade in
  - bars and rings fill to their value
  - totals count up
  - toasts slide in with a countdown bar
- **Reduced motion**: every animation turns off when the system asks for it (`prefers-reduced-motion`).
- **Mobile**: card layouts, a collapsing menu and a floating "add expense" button.
- **Forms**: floating labels with inline validation messages.

## Quick start

Requires Python 3.10 or newer.

```bash
git clone https://github.com/shahul-royalss/personal-expense-tracker.git
cd personal-expense-tracker

python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open http://127.0.0.1:8000/, register an account and start adding categories.

Optional:

```bash
# Sample account with categories, budgets and expenses (prints the password)
python manage.py seed_demo

# Admin access
python manage.py createsuperuser
```

No configuration is needed to run locally. To change settings, copy `.env.example` to `.env` and edit it (see [Configuration](#configuration)).

## Running the tests

```bash
pip install -r requirements-dev.txt

python manage.py test                              # 200+ tests
coverage run manage.py test && coverage report     # coverage (fails under 90%)
ruff check . && ruff format --check .              # lint and formatting
```

| Test module | What it proves |
| --- | --- |
| `tracker/tests/test_alert_thresholds.py` | Threshold alert logic: 79.99% Normal, exactly 80% Warning, exactly 100% Danger, uneven limits, rounding |
| `tracker/tests/test_budget_calculations.py` | Budget calculations: month boundaries, remaining, overspend, totals, unbudgeted spending, six-month trend, query counts, copying budgets |
| `tracker/tests/test_models.py` | Database constraints: positive amounts, unique names and budgets, `PROTECT`, month normalisation |
| `tracker/tests/test_forms.py` | Validation: negative/zero/malformed amounts, category by name or id, duplicates, other users' categories |
| `tracker/tests/test_views_*.py` | End-to-end requests for every page, including the exact spec example for `POST /expenses/create/` |
| `tracker/tests/test_views_access.py` | Login required everywhere; another user's objects give 404 for GET and POST |
| `tracker/tests/test_money_and_tags.py` | Money formatting, badges, usage rings, donut and trend chart maths |
| `accounts/tests.py` | Register, login (safe `next` only), logout only on POST |
| `core/tests.py` | Security headers, Bootstrap form styling, locally served assets |

CI runs the same checks on Python 3.10 to 3.13 for every push ([workflow](.github/workflows/ci.yml)).

## How it works

### Budget alerts

| Spent as % of the month's limit | State | Badge |
| --- | --- | --- |
| No budget set | No budget | grey |
| below 80% | Normal | green |
| 80% up to (but not including) 100% | Warning | amber |
| 100% or more | Danger | red |

The rule lives in one function, `tracker.services.get_alert_level`. It uses `Decimal` arithmetic, so exactly 80.00 of 100.00 is a Warning and 79.99 is still Normal. Displayed percentages are rounded **down** (79.99% shows as 79.9%), so the label never claims a threshold that wasn't reached.

### Calculations

For a user and a month (`?month=YYYY-MM`, default: this month):

- **Spent** per category is the sum of that user's expenses dated from the 1st of the month up to, but not including, the 1st of the next month.
- **Remaining** per category = monthly limit - spent. It is negative when over budget.
- **Total spent** covers all categories. **Total budget** is the sum of the month's limits.
- **Remaining budget** (overall) = total budget - spending in budgeted categories. Spending in categories without a budget is shown separately, so the totals always add up.

`get_monthly_summary()` builds the whole dashboard with **two queries**, however many categories there are. A test checks this.

### Deleting a category

- No expenses: the category and its budgets are deleted.
- Has expenses: the confirmation page asks which of your other categories should receive them. The move and the delete run in one transaction. Without a choice, nothing is deleted.
- `Expense.category` uses `on_delete=PROTECT`, so the database refuses to orphan expenses even if some code path bypassed the view.

### Data isolation

- `OwnedObjectMixin` filters every detail, update and delete view by `request.user`. Another user's id is a 404, so it doesn't even reveal that the record exists.
- Forms receive the user and only offer that user's categories. The owner is always set from the session, never from submitted data.
- Model `clean()` methods double-check that an expense's or budget's category belongs to the same user.

## API / routes

All pages are server-rendered. Forms are protected by Django's CSRF middleware.

### `POST /expenses/create/`

| Field | Required | Rules |
| --- | --- | --- |
| `amount` | yes | decimal > 0, at most 2 decimal places and 12 digits |
| `date` | yes | `YYYY-MM-DD` |
| `category` | yes | id **or** name (case-insensitive) of one of your categories, e.g. `Food` |
| `notes` | no | up to 500 characters |

```http
POST /expenses/create/
Content-Type: application/x-www-form-urlencoded

amount=45.50&date=2023-10-15&category=Food&notes=Lunch+with+client
```

| Outcome | Response |
| --- | --- |
| Valid | `302 Found`, `Location: /dashboard/`, plus a confirmation toast (and a budget warning if a threshold was crossed) |
| Invalid (e.g. `amount=-5`, `amount=0`, unknown category) | `200 OK`, the form is shown again with field errors |
| Not logged in | `302 Found` to `/accounts/login/?next=/expenses/create/` |

### All routes

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | Redirects to the dashboard |
| GET | `/healthz/` | Health check, no login needed |
| GET | `/dashboard/?month=YYYY-MM` | Monthly summary, breakdown, charts and alerts |
| GET | `/expenses/?month=&category=&q=&page=` | Expense list with filters |
| GET, POST | `/expenses/create/` | Log an expense |
| GET, POST | `/expenses/<id>/update/` | Edit an expense |
| GET, POST | `/expenses/<id>/delete/` | Confirm and delete an expense |
| GET | `/categories/` | Category list |
| GET, POST | `/categories/create/` | New category |
| GET | `/categories/<id>/` | Category detail: this month's status, budget history, latest expenses |
| GET, POST | `/categories/<id>/update/` | Edit a category |
| GET, POST | `/categories/<id>/delete/` | Delete, moving expenses if needed |
| GET | `/budgets/?month=YYYY-MM` | Budgets for a month |
| GET, POST | `/budgets/create/?month=&category=` | Set a budget (optionally prefilled) |
| GET, POST | `/budgets/<id>/update/` | Change a budget |
| GET, POST | `/budgets/<id>/delete/` | Delete a budget |
| POST | `/budgets/copy/` | Copy last month's budgets into `month` |
| GET, POST | `/accounts/register/` | Create an account (logs you in) |
| GET, POST | `/accounts/login/` | Log in |
| GET, POST | `/accounts/logout/` | POST logs out; GET only shows a confirmation page |
| | `/admin/` | Django admin |

## Project structure

```text
config/        settings (env based), root URLs, WSGI/ASGI
core/          shared: Bootstrap form mixin, security headers middleware
accounts/      registration, login, logout + templates and tests
tracker/
  models.py      Category, Budget, Expense, per-user querysets, constraints
  services.py    budget maths and alert rules (no HTTP, easy to test)
  dates.py       month helpers        money.py   decimal rounding, currency format
  forms.py       user-scoped forms    fields.py  MonthField, CategoryChoiceField
  mixins.py      ownership, user-aware forms, month navigation
  views/         dashboard, expenses, categories, budgets
  templatetags/  |currency, badges, usage rings, donut and trend charts
  management/    seed_demo command
  templates/     tracker pages and partials
  tests/         unit + integration tests
templates/     base layout, navbar, toasts, form partials, 403/404/500 pages
static/
  css/app.css    design system: theme tokens, dark mode, components, motion
  js/theme.js    applies the saved light/dark theme before the first paint
  js/app.js      count-up numbers, theme toggle, toasts, auto-submitting filters
  vendor/        Bootstrap 5.3.8, Bootstrap Icons 1.13.1, IBM Plex Sans (OFL)
```

More detail: [PRD.md](PRD.md) (requirements and acceptance checklist), [Techstack.md](Techstack.md) (choices and architecture), [UIspec.md](UIspec.md) (screens and components), [Tasks.md](Tasks.md) (build plan).

## Configuration

Settings come from environment variables. A `.env` file in the project root is loaded automatically if present.

| Variable | Default | Purpose |
| --- | --- | --- |
| `DJANGO_DEBUG` | `False` | Debug mode, for local development only |
| `DJANGO_SECRET_KEY` | random at each start | **Set this in production** |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,[::1]` | Comma-separated host names |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | empty | e.g. `https://spendwise.example.com` |
| `DJANGO_SECURE_HTTPS` | `False` | `True` behind HTTPS: SSL redirect, secure cookies, HSTS |
| `DJANGO_TIME_ZONE` | `Asia/Kolkata` | Decides which month "today" falls in |
| `SQLITE_PATH` | `./db.sqlite3` | Database file location |
| `DJANGO_STATIC_ROOT` | empty | Only needed for `collectstatic` |
| `CURRENCY_SYMBOL` | `₹` | Symbol used when formatting money |
| `DJANGO_MIGRATE_ON_START` | `False` | Run migrations when the app boots (serverless hosts with an empty `/tmp`) |
| `DEMO_USERNAME`, `DEMO_PASSWORD` | empty | With `DJANGO_MIGRATE_ON_START`, create this demo account on boot |

## Security

- No secrets in the repository. The secret key comes from the environment, and `.env` is git-ignored.
- `DEBUG` is off by default. `DJANGO_SECURE_HTTPS=True` enables SSL redirect, secure cookies and HSTS.
- CSRF protection on every form. State changes (including logout) only happen on POST.
- JavaScript is optional enhancement only, loaded from our own origin (no inline scripts). The only thing stored in the browser is the light/dark preference.
- Ownership is enforced in querysets, forms and model validation. Other users' records return 404.
- Input validation in forms plus database check and unique constraints.
- Django's password hashing and all four password validators. Login only follows same-site `next` URLs.
- Response headers:
  - `Content-Security-Policy`: only same-origin scripts, styles and fonts; Bootstrap is served locally
  - `Permissions-Policy`
  - `X-Frame-Options: DENY`
  - `nosniff`
  - `Referrer-Policy`
  - `Cross-Origin-Opener-Policy`
- The ORM is used for every query (no raw SQL). Templates auto-escape all user content.

## Deployment

`GET /healthz/` returns `{"status": "ok"}` once the database answers, for uptime checks.

### Vercel

The repository deploys to Vercel as-is (Vercel's zero-config Django support):

- `manage.py` and `WSGI_APPLICATION` are detected automatically. Static files are collected at build time and served from Vercel's CDN.
- `vercel.json` pins the function to the Mumbai region (`bom1`) and keeps tests out of the bundle.
- A Vercel function can only write to `/tmp`, so set `SQLITE_PATH=/tmp/spendwise.sqlite3` and `DJANGO_MIGRATE_ON_START=True`. The schema is then created when an instance starts. With `DEMO_USERNAME` / `DEMO_PASSWORD` set, a demo account with sample data is created as well.
- Also set `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS=.vercel.app` and `DJANGO_SECURE_HTTPS=True`.

Data on Vercel is temporary: it resets whenever Vercel starts a fresh instance. That suits a live demo. For data that has to persist, use the Docker image below with a volume.

### Docker

A production image runs Gunicorn behind a non-root user, with the SQLite file on a volume:

```bash
docker build -t spendwise .
docker run -p 8000:8000 \
  -e DJANGO_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(50))')" \
  -v spendwise-data:/app/data \
  spendwise
```

On a host with HTTPS also set `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` and `DJANGO_SECURE_HTTPS=True`. Static files are served by WhiteNoise, so no separate web server is required.
