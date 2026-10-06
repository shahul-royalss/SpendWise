# PRD: Personal Expense Tracker with Budget Alerts

| Item | Detail |
| --- | --- |
| Product name | SpendWise |
| Event | SVCET Hackathon, powered by LearnSquare (6 October 2026) |
| Stack | Django, SQLite, Django Templates + Bootstrap |
| Related docs | [Techstack.md](Techstack.md), [UIspec.md](UIspec.md), [Tasks.md](Tasks.md) |

## 1. Problem

Most people only find out they overspent when the month is over and the bank statement arrives. By then nothing can be done about it. A statement lists transactions, but it doesn't compare them with what the person planned to spend.

## 2. Goal

Give every user a private place to:

1. log expenses as they happen,
2. group them into their own categories,
3. set a monthly limit for each category, and
4. see at any moment how much of each limit is used, with an early warning at 80% and a clear danger signal at 100%.

## 3. Target users

- Students and young professionals who want a simple monthly spending plan.
- Each account is private. Nobody can see or change another user's data.

## 4. Scope

### In scope (v1)

- Account registration, login and logout.
- Category management (create, list, view, edit, delete).
- Monthly budgets per category (set, update, delete, copy from the previous month).
- Expense logging with amount, date, category and optional notes, plus edit, delete and filtering.
- Dashboard with monthly totals, remaining budget per category, a category breakdown and alert badges.
- Demo data command so reviewers can see every alert state quickly.

### Out of scope (later)

- Income tracking and savings goals
- Multiple currencies
- Recurring expenses
- Receipt uploads
- CSV import and export
- Email or push notifications
- Shared or family budgets

## 5. Data model

| Entity | Fields | Rules |
| --- | --- | --- |
| User | Django's built-in `auth.User` | Owns every other record |
| Category | `user`, `name`, `description` | Name required, at most 50 characters, unique per user (case-insensitive) |
| Budget | `user`, `category`, `monthly_limit` (decimal), `month_year` | `monthly_limit` > 0; `month_year` stored as the first day of the month; one budget per category per month |
| Expense | `user`, `category`, `amount` (decimal), `date` (date), `notes` (optional text) | `amount` > 0 with at most 2 decimal places; notes at most 500 characters |

Every model also has `created_at` and `updated_at`. Money uses `DecimalField(max_digits=12, decimal_places=2)`, never floats.

## 6. Functional requirements

### FR-1 Authentication

- FR-1.1 A visitor can register with a username and password; email is optional. Django's password validators apply.
- FR-1.2 A registered user can log in and log out. Logout uses POST so a third-party page cannot log the user out with a link. Opening `/accounts/logout/` directly shows a confirmation page.
- FR-1.3 Any unauthenticated request to the dashboard, expense, budget or category pages redirects to `/accounts/login/?next=...`.
- FR-1.4 A logged-in user who opens the login or register page is sent to the dashboard.

### FR-2 Category management

- FR-2.1 A user can create, list, view, edit and delete their own categories.
- FR-2.2 Category names must be unique per user, ignoring case. Two different users may both have "Food".
- FR-2.3 Deleting a category that still has expenses is never silent:
  - with no expenses, the category is deleted and its budgets go with it;
  - with expenses, the user must pick another of their categories to move the expenses to. The move and the delete run in one transaction;
  - the database also protects the link (`on_delete=PROTECT`), so an expense can never lose its category.

### FR-3 Budget management

- FR-3.1 A user can set a monthly limit for any of their categories for any month.
- FR-3.2 There is only one budget per category per month. A second one is rejected with a clear message pointing to the existing budget.
- FR-3.3 A user can update or delete a budget.
- FR-3.4 A user can copy last month's budgets into the current month for categories that do not have one yet.

### FR-4 Expense logging

- FR-4.1 `POST /expenses/create/` accepts form data `amount`, `date`, `category`, `notes`.
  - On success it returns **HTTP 302** to the dashboard.
  - On invalid input it returns **HTTP 200** and shows the form with errors.
- FR-4.2 `category` may be the category id (what the HTML form sends) or the category name, case-insensitive. The spec example `category=Food` works. Only the user's own categories are accepted.
- FR-4.3 Zero, negative or non-numeric amounts are rejected, and so are amounts with more than 2 decimal places.
- FR-4.4 After saving, the user sees a confirmation. If the expense pushes its category to 80% or 100% of the month's budget, a warning or danger message is shown as well.
- FR-4.5 A user can list (newest first, 20 per page), filter (month, category, text in notes), edit and delete their expenses.

### FR-5 Dashboard and calculations

For the selected month (default: the current month, changeable with `?month=YYYY-MM`):

- FR-5.1 Total spent in the month, across all categories.
- FR-5.2 Total budget, which is the sum of the month's category limits.
- FR-5.3 Remaining budget overall, which is the total budget minus the amount spent in budgeted categories. Spending in categories without a budget is shown separately as "unbudgeted".
- FR-5.4 A breakdown row per category: limit, spent, remaining (negative when over), percentage used, share of total spending, progress bar and status badge.
- FR-5.5 The five most recent expenses of the month.
- FR-5.6 Links to the previous and next month.
- FR-5.7 A donut chart of the month's spending by category, and a six-month trend of spending against the total budget.

### FR-6 Visual budget alerts

| Spent as % of limit | State | Badge | Colour |
| --- | --- | --- | --- |
| No budget set | No budget | grey | `secondary` |
| below 80% | Normal | green | `success` |
| 80% up to (but not including) 100% | Warning | amber | `warning` |
| 100% or more | Danger | red | `danger` |

- Thresholds are compared with exact decimal arithmetic, so exactly 80.00 of 100.00 is Warning and 79.99 is Normal.
- Percentages are displayed rounded **down** to one decimal, so 79.99% shows as 79.9% and the label never claims a threshold that wasn't reached.
- Categories in Warning or Danger also get an alert banner at the top of the dashboard, worst first.

## 7. Business rules

1. A month always means the calendar month of the user's local date (time zone from settings, default `Asia/Kolkata`).
2. Spent for a category in a month = the sum of that user's expenses in that category dated from the 1st of the month up to, but not including, the 1st of the next month.
3. Remaining = monthly limit - spent. A negative value means the category is over budget.
4. Usage % = spent / monthly limit x 100.
5. Every query is filtered by the logged-in user. Another user's record behaves exactly like a record that does not exist (HTTP 404).

## 8. Non-functional requirements

| Area | Requirement |
| --- | --- |
| Security | CSRF on every form, POST for every state change, ownership enforced in querysets and forms, no secrets in the repo, Content-Security-Policy, clickjacking protection, Django password hashing and validators, HTTPS settings switch on with one variable |
| Data integrity | Database check constraints for positive amounts and limits, unique constraints for category names and budgets, `PROTECT` on expense categories, decimal money |
| Performance | Dashboard summary uses a fixed number of queries (2) whatever the number of categories; expense list is paginated; index on `(user, date)` |
| Accessibility | Semantic headings, labels on every input, `aria` attributes on progress bars and charts, colour never the only signal (badges have text and icons), skip link, every animation off under `prefers-reduced-motion` |
| Portability | Runs with `pip install` + `migrate` + `runserver`, no extra services; Bootstrap is vendored so the UI works offline |
| Quality | Ruff lint and format, automated tests with coverage, CI on every push |

## 9. Edge cases

| Case | Expected behaviour |
| --- | --- |
| User B opens user A's expense, budget or category URL | 404; nothing is changed |
| User B posts user A's category id when creating an expense | 200 with "Select a valid choice" error |
| Amount `0`, `-5`, `abc` or `1.234` | 200 with a field error; nothing saved |
| Duplicate category name, e.g. "food" when "Food" exists | 200 with a field error |
| Second budget for the same category and month | 200 with a form error |
| Delete a category that has expenses | Blocked until the user chooses where to move them |
| `?month=` missing, malformed or out of range | Falls back to the current month |
| User with no categories | Dashboard and forms show an empty state with a link to create one |
| Spending exactly at 80% / 100% | Warning / Danger |

## 10. Acceptance checklist

| Requirement from the brief | Where it is implemented | Covered by tests |
| --- | --- | --- |
| Register, login, logout | `accounts/` | `accounts/tests.py` |
| Login required for dashboard, expenses, budgets | `LoginRequiredMixin` on every tracker view | `tracker/tests/test_views_access.py` |
| Category CRUD isolated per user | `tracker/views/categories.py` | `test_views_categories.py`, `test_views_access.py` |
| Monthly budgets per category | `tracker/views/budgets.py`, `BudgetForm` | `test_views_budgets.py`, `test_forms.py` |
| `POST /expenses/create/`: 302 on success, 200 on errors | `ExpenseCreateView` | `test_views_expenses.py` |
| Negative and zero amounts rejected | `ExpenseForm.clean_amount` + DB check constraint | `test_forms.py`, `test_models.py`, `test_views_expenses.py` |
| Dashboard totals, remaining per category, breakdown | `tracker/services.py`, `dashboard.html` | `test_budget_calculations.py`, `test_views_dashboard.py` |
| Normal < 80% <= Warning < 100% <= Danger | `get_alert_level` | `test_alert_thresholds.py` |
| Safe category deletion | `CategoryDeleteView`, `PROTECT` | `test_views_categories.py`, `test_models.py` |
| SQLite | `config/settings.py` | n/a |

## 11. Success metrics

- Every item in section 10 passes in CI.
- A new user can register, add a category, set a budget and log an expense in under a minute.
- The dashboard loads with two summary queries, however many categories exist.
