# UI Specification

Server-rendered pages built with Django Templates and Bootstrap 5.3. A design layer in `static/css/app.css` adds a brand identity, dark mode, charts and motion on top of Bootstrap. The layout is mobile-first and works from 360px wide upwards.

## 1. Design principles

1. **Status at a glance.** Every budget shows its state four ways: a badge with text and icon, a coloured bar or ring, the percentage, and the remaining amount. Colour is never the only signal.
2. **One primary action per screen.** "Add expense" is always one tap away: in the navbar on desktop, as a floating button on phones.
3. **Plain numbers.** Money is always shown as `₹1,234.50` (symbol configurable) in tabular figures, right aligned in tables.
4. **No dead ends.** Every list has an empty state that explains what to do next and links to it.
5. **Motion with a purpose.** Animations explain change (a bar filling to its value, a toast counting down). They never block input, and they switch off for users who ask for reduced motion.

## 2. Visual language

### Colour tokens

| Token | Light | Dark | Used for |
| --- | --- | --- | --- |
| Primary | `#6366f1` indigo | `#818cf8` | Links, active nav, primary buttons |
| Brand gradient | indigo `#6366f1` to violet `#8b5cf6` to pink `#ec4899` | same | Logo, primary buttons, current month bar |
| Hero gradient | `#4338ca` to `#6d28d9` to `#db2777` (slowly shifting) | same | Dashboard hero, auth panel |
| Normal | `#10b981` emerald | `#34d399` | Budget below 80% |
| Warning | `#f59e0b` amber | `#fbbf24` | Budget at 80% to 99.9% |
| Danger | `#ef4444` red | `#f87171` | Budget at 100% or more, destructive actions |
| No budget | `#64748b` slate | `#94a3b8` | Category without a budget this month |
| Surface | `#ffffff` on `#f4f6fb` | `#10182b` on `#0a0f1e` | Cards on page background |

- Text that sits on a light background uses the darker `*-text-emphasis` shade, which meets WCAG AA contrast. The bright base colours are only used for fills (bars, rings, icons).
- Each category gets a stable identity colour from a 10-colour palette (by id). It is used for its avatar, legend dot and donut segment, and is deliberately separate from the green / amber / red status colours.

### Typography and shape

- Font: Inter (variable, self-hosted), with `tabular-nums` for every amount.
- Headings: weight 800 with slight negative letter spacing. Eyebrow labels are uppercase, 0.75rem, letter-spaced.
- Radius: 0.75rem for controls, 1.1rem for cards, 1.6rem for the hero.
- Elevation: soft two-layer shadows; cards lift on hover.

### Themes

- Light and dark themes use Bootstrap 5.3 colour modes (`data-bs-theme`).
- The first visit follows the system preference. The sun/moon button switches theme and the choice is remembered in the browser.
- `theme.js` runs in `<head>`, so there is no flash of the wrong theme.

## 3. Motion

| Animation | Where | Details |
| --- | --- | --- |
| Fade-up entrance | Page headers, cards, table rows | 0.7s, staggered 80ms per item (35ms for rows) |
| Gradient drift | Dashboard hero, auth panel | 16s background-position loop |
| Floating blobs | Hero, auth panel, empty-state icons | Blurred shapes drifting 12px up and down |
| Bar fill | Progress bars, hero budget bar | Grows from 0 to its width in 1.1s |
| Ring and donut draw | Usage rings, spending donut | Stroke draws from 0; donut segments draw one after another |
| Trend bars | Six-month chart | Grow from the baseline, staggered; hover shows the amount |
| Count-up | Stat cards, donut total | Numbers count to their value in 1.2s (ease-out) |
| Danger cues | Danger badges, danger alert icons | Heartbeat icon and a soft pulse ring; shimmer across over-budget bars |
| Toasts | Flash messages | Slide in from the right with a countdown bar; auto-close after 6s (12s for warnings) |
| Micro-interactions | Buttons, icon buttons, logo, new-category card | Lift, rotate or gradient slide on hover; press feedback on click |

- All entrance animations are time-based CSS, so content always ends up visible even if JavaScript is disabled.
- `@media (prefers-reduced-motion: reduce)` cuts every animation and transition to near zero, and the count-up script is skipped.

## 4. Global layout

```text
+------------------------------------------------------------------------------+
| [logo] SpendWise    Dashboard  Expenses  Budgets  Categories   [+ Add] [sun] [user v] |  sticky glass navbar
+------------------------------------------------------------------------------+
|                                                              [toasts, top right]  |
|  page content (container-xl)                                                      |
|                                                                                   |
+------------------------------------------------------------------------------+
| footer                                                                        |
+------------------------------------------------------------------------------+
                                                                    [+] floating button (phones)
```

- Navbar collapses into a menu button below 992px. The active section is a highlighted pill with `aria-current="page"`.
- The user menu shows who is signed in and holds "Log out", a POST form with a CSRF token.
- Visitors who are not logged in see the brand, the theme toggle, "Log in" and "Get started".
- A "Skip to content" link is the first focusable element.

## 5. Pages

### 5.1 Log in, register and log-out confirmation

- Split card: on the left an animated gradient panel with the product pitch, three feature points and a floating mock budget card. On the right, the form.
- On phones only the form is shown.
- Floating-label inputs. Field errors appear under each field, and form-wide errors (such as a wrong password) appear in a red alert above the form.
- Opening `/accounts/logout/` directly shows "Log out of SpendWise?" with a POST button.

### 5.2 Dashboard `/dashboard/?month=YYYY-MM`

```text
+------------------------------------------------------------------------------+
| OCTOBER 2026 OVERVIEW                                    [<] October 2026 [>] |
| Good afternoon, demo                                          [+ Add expense] |
| You've used 71.3% of your October budget and 3 categories need attention.      |
| [=================71%=====          ]                     (gradient hero)     |
+------------------------------------------------------------------------------+
[x] Transport is over budget by ₹450.00 (115.0% used).                  [View]
[x] Entertainment has used its entire budget of ₹2,000.00.              [View]
[!] Food has used 86.2% of its budget, ₹1,100.00 left.                  [View]

[Spent this month] [Monthly budget] [Remaining budget (ring)] [Budget alerts]

+--------------------------------------------+ +-----------------------------+
| Category breakdown          [Manage budgets]| | Where your money went       |
| avatar | budget | spent | remaining | bar | | |     (donut with total)      |
| ... one row per category, status badge     | | legend: colour, %, amount   |
| Total row                                   | |                             |
+--------------------------------------------+ +-----------------------------+
+--------------------------------------------+ +-----------------------------+
| Last 6 months   (bars + dashed budget line) | | Recent expenses   [View all]|
+--------------------------------------------+ +-----------------------------+
```

- Alert banners list only Warning and Danger categories, worst first. Danger icons pulse.
- The Remaining card is coloured by the overall state and carries a usage ring.
- Rows without a budget show "Set budget", which opens the budget form with category and month filled in.
- The current month's trend bar uses the brand gradient; a month over its budget turns red.
- Empty states: no categories (with "Create your first category"), no spending (donut), no history (trend), no expenses (recent list).

### 5.3 Expenses

| Screen | URL | Content |
| --- | --- | --- |
| List | `/expenses/` | Header with "Total: ₹x" pill, filter card (month, category, notes search) that refreshes on change, table with category avatar, notes, category pill, relative date ("Today"), amount and icon actions. 20 per page |
| Create | `/expenses/create/` | Amount with ₹ prefix, date (today), category, notes. Submit returns to the dashboard with toasts |
| Edit | `/expenses/<id>/update/` | Same form, filled in. Submit returns to the list |
| Delete | `/expenses/<id>/delete/` | Confirmation card with a wobbling danger icon and the expense details |

If the user has no categories, the create page explains why and links to "Create a category" instead of showing an unusable form.

### 5.4 Categories

| Screen | URL | Content |
| --- | --- | --- |
| List | `/categories/` | Cards with colour accent, avatar, description, this month's progress and badge, expense and budget counts, edit/delete. A dashed "New category" card closes the grid |
| Detail | `/categories/<id>/` | Header card, this month's usage ring with budget / spent / remaining, budget history, latest 10 expenses, "Add expense" pre-selecting the category |
| Create / Edit | `/categories/create/`, `/categories/<id>/update/` | Name, description |
| Delete | `/categories/<id>/delete/` | Warns how many budgets go with it. If the category has expenses, a required "Move its expenses to" select is shown |

### 5.5 Budgets

| Screen | URL | Content |
| --- | --- | --- |
| List | `/budgets/?month=YYYY-MM` | Month navigation, "Start from last month" copy card (only when something new can be copied), summary strip with overall ring, one card per budget with a usage ring, spent / limit, remaining and badge, and a list of categories without a budget |
| Create / Edit | `/budgets/create/`, `/budgets/<id>/update/` | Category, month (`<input type="month">`), monthly limit with ₹ prefix |
| Delete | `/budgets/<id>/delete/` | Confirmation card; expenses are not affected |

### 5.6 Error pages

- 404 and 403: large gradient status code floating gently, a short explanation and "Back to the dashboard". A 404 is also what another user's record looks like.
- 403 (CSRF failure): explains that the form expired.
- 500: a standalone page with inline styles, so it renders even if the layout itself is broken.

## 6. Components

| Component | Implementation |
| --- | --- |
| Status badge | `{% alert_badge %}`: `badge rounded-pill bg-{state}-subtle text-{state}-emphasis border` + icon + label |
| Progress bar | Bootstrap `.progress` with gradient fill per state, width capped at 100%, percentage beside it |
| Usage ring | `{% progress_ring %}`: SVG circle, `pathLength=100`, capped at 100% while the label shows the real value |
| Spending donut | `{% spending_donut %}`: one SVG circle per category (dash array = share), small gaps, total in the centre, legend below |
| Trend chart | `{% trend_chart %}`: CSS grid of bars scaled to the highest month, dashed budget marker, hover tooltip, hidden list for screen readers |
| Stat card | Label, gradient icon bubble, count-up value, caption |
| Toast | Bootstrap toast with gradient icon, message, close button and countdown bar |
| Form field | Floating label, Bootstrap classes added by `BootstrapFormMixin`, error message with icon |
| Empty state | Floating icon tile, sentence and optional primary button |

## 7. Responsive behaviour

| Width | Behaviour |
| --- | --- |
| < 576px | Single column, hero stacks its controls, tables scroll inside their card, floating add button |
| 576px - 1199px | Two stat cards per row, charts stacked under the breakdown, navbar collapsed below 992px |
| >= 1200px | Four stat cards per row; breakdown and donut side by side, trend and recent expenses side by side |

## 8. Accessibility checklist

- Every input has a `<label>` (floating). Help text is linked with `aria-describedby`; invalid fields get `aria-invalid="true"`.
- One `h1` per page and `h2` for each section.
- Progress bars use `role="progressbar"` with `aria-valuenow`, `aria-valuemin` and `aria-valuemax`. Rings and charts use `role="img"` with a text alternative, and the trend chart also has a visually hidden list of values.
- Decorative icons are `aria-hidden="true"`; text always accompanies them.
- Toasts use `role="status"` (or `role="alert"` for warnings) inside an `aria-live` region and can be closed.
- Destructive actions always go through a confirmation page that uses POST.
- All motion is disabled under `prefers-reduced-motion: reduce`.
