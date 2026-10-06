# UI Specification

Server-rendered pages built with Django Templates and Bootstrap 5.3. The layout is mobile-first and works from 360px wide upwards.

## 1. Design principles

1. **Status at a glance.** Every budget shows its state three ways: a coloured badge with text, a coloured progress bar and the percentage. Colour is never the only signal.
2. **One primary action per screen.** "Add expense" is always one click away in the navbar.
3. **Plain numbers.** Money is always shown as `₹1,234.50` (symbol configurable), right aligned in tables.
4. **No dead ends.** Empty states explain what to do next and link to it.

## 2. Visual language

| Token | Bootstrap class | Used for |
| --- | --- | --- |
| Primary | `primary` (blue) | Navbar, main buttons, links |
| Normal | `success` (green) | Budget below 80% |
| Warning | `warning` (amber) | Budget at 80% to 99.9% |
| Danger | `danger` (red) | Budget at 100% or more, delete buttons |
| No budget | `secondary` (grey) | Category without a budget this month |

- Font: Bootstrap's system font stack.
- Cards: `card` + `shadow-sm` on a light grey page (`bg-body-tertiary`).
- Icons: Bootstrap Icons. `check-circle-fill` for Normal, `exclamation-triangle-fill` for Warning, `x-octagon-fill` for Danger, `dash-circle` for No budget.

## 3. Global layout

```text
+----------------------------------------------------------------+
| SpendWise  Dashboard  Expenses  Budgets  Categories  [+ Add expense] [user v] |
+----------------------------------------------------------------+
| flash messages (dismissible alerts)                            |
|                                                                |
| page content (container, max 1320px)                           |
|                                                                |
+----------------------------------------------------------------+
| footer                                                         |
+----------------------------------------------------------------+
```

- Navbar collapses into a hamburger below 992px. The active section is highlighted and has `aria-current="page"`.
- The user menu holds "Log out", a POST form with a CSRF token.
- Visitors who are not logged in only see the brand and Log in / Register.
- A "Skip to content" link is the first focusable element.

## 4. Pages

### 4.1 Login `/accounts/login/` and Register `/accounts/register/`

- Centred card, max 420px wide.
- Login: username, password, submit. "No account? Register" link.
- Register: username, email (optional), password, password confirmation, with password rules listed under the field. "Already registered? Log in" link.
- Errors appear under each field (`is-invalid` + `invalid-feedback`). Form-wide errors such as a wrong password appear in a red alert above the form.

### 4.2 Dashboard `/dashboard/?month=YYYY-MM`

```text
Dashboard                                  [<]  October 2026  [>]  [This month]
Spending overview for October 2026

[!] Transport is over budget by ₹450.00 (115.0% used)               (danger)
[!] Food has used 86.2% of its budget, ₹1,100.00 left                (warning)

+-------------+ +-------------+ +-------------+ +-------------+
| Spent       | | Budget      | | Remaining   | | Alerts      |
| ₹16,500.00  | | ₹22,000.00  | | ₹6,300.00   | | 2 over      |
| 15 expenses | | 5 budgets   | | 71.3% used  | | 1 near limit|
+-------------+ +-------------+ +-------------+ +-------------+

Category breakdown                                  [Manage budgets]
| Category | Budget | Spent | Remaining | Usage (bar + %) | Status |
| ...rows sorted by name...                                        |
| Total    | ...    | ...   | ...       |                 |        |

Recent expenses (5)                                  [View all]
```

- Alert banners (`alert-warning` / `alert-danger`) list only categories in Warning or Danger, worst first.
- The Remaining card is coloured by the overall state of all budgets.
- Rows without a budget show "Set budget". The link opens the budget form with the category and month already filled in.
- Progress bars are capped at 100% width. The real percentage is shown as text next to the bar.
- Empty state (no categories): "Create your first category" button.

### 4.3 Expenses

| Screen | URL | Content |
| --- | --- | --- |
| List | `/expenses/` | Filter bar (month, category, search in notes), total of the filtered rows, table (date, category, notes, amount, actions), pagination with 20 per page |
| Create | `/expenses/create/` | Amount, date (defaults to today), category select, notes. Submit returns to the dashboard |
| Edit | `/expenses/<id>/update/` | Same form, filled in. Submit returns to the list |
| Delete | `/expenses/<id>/delete/` | Confirmation card showing the expense, plus Delete (red) and Cancel |

- If the user has no categories, the create page shows an info alert with a link to create one instead of an unusable form.
- After saving, a green confirmation appears. A warning or danger alert is added when the category crosses 80% or 100%.

### 4.4 Categories

| Screen | URL | Content |
| --- | --- | --- |
| List | `/categories/` | Cards or table: name, description, number of expenses and budgets, actions |
| Detail | `/categories/<id>/` | This month's status (budget, spent, remaining, bar, badge), budget history, latest 10 expenses, "Add expense" pre-selecting this category |
| Create / Edit | `/categories/create/`, `/categories/<id>/update/` | Name, description |
| Delete | `/categories/<id>/delete/` | Warns how many budgets will be removed. If the category has expenses, a required "Move its expenses to" select is shown |

### 4.5 Budgets

| Screen | URL | Content |
| --- | --- | --- |
| List | `/budgets/?month=YYYY-MM` | Month navigation, table of budgets (category, limit, spent, remaining, bar, badge, actions), "Categories without a budget" list with "Set budget" buttons, "Copy last month's budgets" button when there is something to copy |
| Create / Edit | `/budgets/create/`, `/budgets/<id>/update/` | Category select, month (`<input type="month">`), monthly limit |
| Delete | `/budgets/<id>/delete/` | Confirmation card |

### 4.6 Error pages

- 404: "Page not found" with a link back to the dashboard. This is also what another user's record looks like.
- 403 (CSRF failure): explains that the form expired and asks the user to reload.
- 500: a standalone page with no template inheritance, so it renders even if the layout is broken.

## 5. Components

| Component | Markup | Notes |
| --- | --- | --- |
| Status badge | `span.badge.rounded-pill.text-bg-{state}` + icon + label | Rendered by the `{% alert_badge %}` tag |
| Progress bar | `div.progress[role=progressbar][aria-valuenow]` > `div.progress-bar.bg-{state}` | Width capped at 100 |
| Summary card | `card` with label, big number and small caption | 4 per row on desktop, 2 on tablet, 1 on phone |
| Month navigation | button group: previous, month name, next, "This month" | Keeps `?month=` in the URL so it can be bookmarked |
| Form field | label, input with Bootstrap class, help text, errors | Classes are added by `BootstrapFormMixin`, never written in templates |
| Flash message | dismissible `alert` | Django `error` maps to Bootstrap `danger` |
| Pagination | `pagination` with Previous / Page x of y / Next | Keeps the active filters through `{% querystring %}` |
| Empty state | centred icon, sentence and primary button | Used on every list |

## 6. Responsive behaviour

| Width | Behaviour |
| --- | --- |
| < 576px | Summary cards stacked, tables scroll horizontally inside `.table-responsive`, filter fields stacked |
| 576px - 991px | Two summary cards per row, navbar collapsed |
| >= 992px | Four summary cards per row, full navbar |

## 7. Accessibility checklist

- Every input has a `<label>`. Help text is linked with `aria-describedby`, and invalid fields get `aria-invalid="true"`.
- Headings follow order: one `h1` per page, `h2` for each section.
- Progress bars have `role="progressbar"`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax` and an `aria-label`.
- Icons are decorative (`aria-hidden="true"`) because text always follows them.
- Text and badge colours use Bootstrap 5.3's contrast-checked `text-bg-*` helpers.
- Destructive actions always go through a confirmation page that uses POST.
