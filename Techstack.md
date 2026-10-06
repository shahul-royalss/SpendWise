# Tech Stack

The brief fixes the core stack (Django, SQLite, Django Templates with Bootstrap). Everything else was picked to keep the project easy to run, easy to review and safe by default.

## Overview

| Layer | Choice | Version | Why |
| --- | --- | --- | --- |
| Language | Python | 3.10+ (developed on 3.13) | Required by Django 5.2 |
| Web framework | Django | 5.2 LTS | Required by the brief. LTS release with security support until April 2028 |
| Database | SQLite | bundled with Python | Required by the brief. Zero setup, file based, fine for a single-user-per-account app |
| Templates | Django Templates | built in | Server-rendered pages, auto-escaping against XSS |
| UI framework | Bootstrap | 5.3.8 | Required by the brief. Vendored under `static/vendor/`, no CDN needed |
| Icons | Bootstrap Icons | 1.13.1 | Matches Bootstrap, vendored as a web font |
| Static files | WhiteNoise | 6.12 | Serves CSS, JS and fonts from Django itself, also with `DEBUG=False` |
| Configuration | python-dotenv | 1.2 | Reads a local `.env` file; real settings come from environment variables |
| Tests | Django test runner (`unittest`) | built in | No extra framework; uses `TestCase`, `SimpleTestCase` and the test client |
| Coverage | coverage.py | 7.16 | Branch coverage report, build fails below 90% |
| Lint / format | Ruff | 0.16 | One tool for flake8, isort, pyupgrade, bandit-style security rules and formatting |
| CI | GitHub Actions | n/a | Lint, Django checks, migration check and tests on Python 3.10 to 3.13 |
| App server (deploy) | Gunicorn | 23.0 | Production WSGI server used in the Docker image |
| Container | Docker | n/a | `python:3.13-slim`, runs as a non-root user, SQLite file on a volume |

## Why server-rendered Django instead of an API + SPA

- The brief asks for Django Templates and server-rendered views. The key endpoint, `POST /expenses/create/`, is defined as a classic form post that answers with a 302 or a 200.
- Fewer moving parts. There is no build step, no JavaScript framework and no token handling. Django's CSRF and session protection cover every form.

## Why vendored Bootstrap instead of a CDN

- The app looks the same with no internet access, for example on a judge's laptop or in a sandbox.
- The Content-Security-Policy can be `'self'` only. No third-party script origin is trusted.
- WhiteNoise serves the files with proper caching and compression headers.

## Project layout

```text
personal-expense-tracker/
|-- config/            settings, root URLs, WSGI/ASGI
|-- core/              shared pieces: Bootstrap form mixin, security headers middleware
|-- accounts/          registration, login, logout
|-- tracker/           the expense tracker domain
|   |-- models.py      Category, Budget, Expense + per-user querysets
|   |-- services.py    budget maths and alert rules (pure, unit tested)
|   |-- dates.py       month helpers
|   |-- money.py       decimal rounding and currency formatting
|   |-- forms.py       model forms scoped to the logged-in user
|   |-- fields.py      MonthField, CategoryChoiceField
|   |-- mixins.py      ownership, user-aware forms, month navigation
|   |-- views/         dashboard, expenses, categories, budgets
|   |-- templatetags/  currency filter, alert badge tag
|   |-- management/    seed_demo command
|   `-- tests/         unit and integration tests
|-- templates/         base layout, shared partials, error pages
`-- static/            app.css + vendored Bootstrap
```

## Architecture notes

- **Thin views, logic in services.** Views only handle HTTP. Calculations live in `tracker/services.py` as plain functions and dataclasses that are easy to unit test.
- **Ownership in one place.** `OwnedObjectMixin` filters every detail, update and delete view by `request.user`. Forms get the user and limit category choices to that user's categories. Custom querysets (`for_user`, `in_month`, `for_month`) keep the filtering readable.
- **Database as the last line of defence.** Check and unique constraints mean bad data is rejected even if it bypasses the forms (admin, shell, scripts).
- **Decimal everywhere.** Money is stored as `DECIMAL(12, 2)` and calculated with `decimal.Decimal`, so the threshold checks are exact.

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `DJANGO_DEBUG` | `False` | Debug mode, only for local development |
| `DJANGO_SECRET_KEY` | random per start | Signing key. Set it in production |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,[::1]` | Comma-separated host names |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | empty | Needed when served from another origin over HTTPS |
| `DJANGO_SECURE_HTTPS` | `False` | Turns on SSL redirect, secure cookies and HSTS |
| `DJANGO_TIME_ZONE` | `Asia/Kolkata` | Decides which month "today" belongs to |
| `SQLITE_PATH` | `db.sqlite3` in the project | Location of the database file |
| `CURRENCY_SYMBOL` | `₹` | Symbol used when formatting money |

## Dependency policy

- Runtime dependencies are pinned to exact versions in `requirements.txt`. There are only three: Django, WhiteNoise and python-dotenv.
- Dev tools are in `requirements-dev.txt`, and Gunicorn is in `requirements-prod.txt`.
- No dependency is needed for forms, auth, charts or the API. Django already covers them.
