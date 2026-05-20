# TREC Frontend Redesign ("Coastal Editorial") Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dramatically improve the visual quality of the TREC Dash frontend ("Coastal Editorial" direction) without changing any functionality.

**Architecture:** Replace the `dbc.themes.MINTY` theme with the neutral `dbc.themes.BOOTSTRAP` base, then layer a custom CSS design system (tokens → base → chrome → components → pages) loaded automatically from `fe/assets/`. The large inline `<style>` block in `app.py` is migrated into organized `assets/*.css` files. All component IDs, callbacks, routes, and data flow are preserved — changes are limited to CSS, markup classes, and cosmetic component props.

**Tech Stack:** Python, Dash, dash-bootstrap-components, Plotly (Scattermap), CSS custom properties, Google Fonts (Fraunces, Inter, IBM Plex Mono).

---

## Working context (read before starting)

- **Branch:** work on `feature/fe-redesign-coastal-editorial` (already created). Do NOT use a separate git worktree — the local Dash dev server hot-reloads *this* checkout, and we rely on that for visual verification.
- **Servers (must be running during execution):**
  - Backend on `:8000` — from `be/`: `.venv/bin/uvicorn main:app --reload --port 8000`
  - Frontend on `:8050` — from `fe/`: `.venv/bin/python app.py` (Dash debug, hot-reloads on file save)
  - The frontend reads `API_BASE_URL=http://localhost:8000` from the root `.env`.
- **Visual reference (source of truth for the look):** the approved mockup at `.design/directions.html` — **Direction A** section. Serve it with `python3 -m http.server 8077` from `.design/` and open `http://localhost:8077/directions.html`.
- **Verification tooling:** Playwright MCP browser. Standard verification loop for every UI task:
  1. Save file(s) → Dash hot-reloads.
  2. `browser_navigate` to the page, wait ~2s for callbacks/map.
  3. `browser_take_screenshot` (full page) and visually compare against the reference + the task's expected outcome.
  4. Check `browser_console_messages` shows **no Dash callback errors** (warnings about deprecated props are acceptable).
  5. `curl -s -o /dev/null -w "%{http_code}" http://localhost:8050/<path>` returns `200`.
- **Hard rule:** never rename or remove a component `id`, never change a callback's `Input`/`Output`/`State` set, never change route paths. Cosmetic component props (`color`, `className`, `size`, marker colors, basemap style) may change.

### Dash assets loading (important)
Dash auto-loads every `assets/*.css` file **alphabetically**, after `external_stylesheets`. Numeric filename prefixes (`00-`, `10-`, …) therefore control cascade order. Files load after the Bootstrap base, so our overrides win.

### Target `fe/assets/` layout after this plan
- `00-tokens.css` — CSS variables (color, type, spacing, radius, shadow).
- `10-base.css` — element resets, body background, typography defaults, links.
- `20-chrome.css` — header, nav, footer.
- `30-components.css` — buttons, chips, badges, cards, tables, pagination, dropdown, sort carets (refined migration of the current inline rules).
- `40-pages.css` — home hero/stats, data-portal layout, availability, details, about.
- `favicon.ico` — unchanged.
- `stat_cards.css` — **deleted** in Task 6 (its rules fold into `40-pages.css`).

---

## Task 1: Capture baseline + migrate inline CSS to assets (no visual change)

Goal: get the giant inline `<style>` out of `app.py` and into `assets/` **with zero visual change**, so later tasks edit real stylesheets. This is a pure refactor.

**Files:**
- Create: `fe/assets/30-components.css`
- Modify: `fe/app.py` (remove the inline `<style>…</style>` block from `app.index_string`, lines 29-372)

- [ ] **Step 1: Capture baseline screenshots**

With both servers running, screenshot the current state for later comparison:
- `browser_navigate` → `http://localhost:8050/` → `browser_take_screenshot` full page → `.design/baseline-home.png`
- Repeat for `/data` (wait 3s for map), `/availability`, `/about`, `/api`.

- [ ] **Step 2: Move the inline CSS verbatim into `fe/assets/30-components.css`**

Copy the **exact** CSS rules currently between `<style>` and `</style>` in `app.py` (the block spanning lines ~30-371, starting `.trec-header {` and ending with the `.dash-header[data-dash-column="has_ena"] .column-header-name { pointer-events: none; }` rule) into a new file `fe/assets/30-components.css`. Do not edit any rule — copy as-is. (Note: the `content: "\\F235"` escapes in the Python string become single-backslash `content: "\F235"` in the CSS file.)

- [ ] **Step 3: Remove the inline `<style>` block from `app.py`**

In `fe/app.py`, edit `app.index_string` so the `<head>` no longer contains the `<style>…</style>` block. The head becomes:

```python
app.index_string = """<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>"""
```

- [ ] **Step 4: Verify pixel-identical**

Reload `/`, `/data`, `/availability`. Screenshot each and compare to the Step 1 baselines — they must look identical (CSS just moved files). Confirm `200` on each and no new console errors.

- [ ] **Step 5: Commit**

```bash
git add fe/assets/30-components.css fe/app.py
git commit -m "Refactor: move inline CSS from app.py into assets/30-components.css

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Design tokens, fonts, and theme base

Goal: introduce the color/type/spacing token system, load the fonts, swap the theme base, and set global typography + canvas background.

**Files:**
- Create: `fe/assets/00-tokens.css`
- Create: `fe/assets/10-base.css`
- Modify: `fe/app.py` (theme in `external_stylesheets`; add font `<link>` tags to `index_string` head)

- [ ] **Step 1: Create `fe/assets/00-tokens.css`**

```css
:root {
  /* Brand */
  --trec-green: #0E4D3C;
  --trec-green-deep: #15614b;
  --trec-green-dark: #0a3a2d;
  --trec-coral: #D9714E;
  --trec-coral-dark: #c15c3b;

  /* Neutrals */
  --trec-canvas: #F7F4EC;     /* page background (sand/cream) */
  --trec-paper: #FFFFFF;      /* cards / surfaces */
  --trec-paper-2: #FBF9F3;    /* sunken surfaces (sidebars, table head) */
  --trec-ink: #1A2420;        /* primary text */
  --trec-muted: #6f7a72;      /* secondary text */
  --trec-faint: #8a7f6c;      /* labels on cream */
  --trec-border: #e6e0d3;     /* hairline on cream */
  --trec-border-2: #f1ece1;   /* row dividers */

  /* Semantic */
  --surface: var(--trec-paper);
  --border: var(--trec-border);
  --link: var(--trec-green);
  --accent: var(--trec-coral);

  /* Type */
  --font-display: "Fraunces", Georgia, serif;
  --font-sans: "Inter", system-ui, -apple-system, sans-serif;
  --font-mono: "IBM Plex Mono", ui-monospace, monospace;

  /* Spacing (8px scale) */
  --sp-1: 4px;  --sp-2: 8px;  --sp-3: 12px; --sp-4: 16px;
  --sp-5: 24px; --sp-6: 32px; --sp-7: 48px; --sp-8: 64px;

  /* Radius */
  --r-sm: 8px;  --r-md: 14px; --r-pill: 999px;

  /* Shadow */
  --shadow-1: 0 6px 18px rgba(20,40,32,.06);
  --shadow-2: 0 18px 40px rgba(20,40,32,.10);
}
```

- [ ] **Step 2: Create `fe/assets/10-base.css`**

```css
body {
  background: var(--trec-canvas);
  color: var(--trec-ink);
  font-family: var(--font-sans);
  -webkit-font-smoothing: antialiased;
}

h1, h2, h3, h4, h5 { font-family: var(--font-display); color: var(--trec-ink); }
h1 { font-weight: 600; letter-spacing: -0.01em; }
h2, h3 { font-weight: 600; }

a { color: var(--link); }
a:hover { color: var(--trec-green-dark); }

/* Numeric/scientific emphasis */
.trec-num { font-family: var(--font-mono); font-feature-settings: "tnum" 1; }

/* Standard page wrapper used by content pages */
.trec-page { padding: var(--sp-6) 0 var(--sp-7); }

:focus-visible {
  outline: 2px solid var(--trec-coral);
  outline-offset: 2px;
}
```

- [ ] **Step 3: Swap theme + load fonts in `app.py`**

In `fe/app.py`, change the theme from MINTY to the neutral Bootstrap base, keeping the Bootstrap Icons stylesheet:

```python
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css",
    ],
    use_pages=True,
    suppress_callback_exceptions=True,
)
```

Then add the Google Fonts links to the `<head>` of `app.index_string` (immediately after `{%favicon%}`):

```html
        {%favicon%}
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,900&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap" rel="stylesheet">
        {%css%}
```

- [ ] **Step 4: Verify**

Reload `/`. Expected: page background turns warm cream, body text is Inter, any heading is Fraunces serif. Components may look unstyled/plain in spots (we restyle them next) but nothing should be broken. Confirm `200` and no console errors. Screenshot `/` → `.design/after-task2-home.png`.

- [ ] **Step 5: Commit**

```bash
git add fe/assets/00-tokens.css fe/assets/10-base.css fe/app.py
git commit -m "Add design tokens, web fonts, and neutral theme base

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Global chrome (header, nav, footer)

Goal: restyle the site header (wordmark + nav with coral active underline) and footer to the new tokens.

**Files:**
- Create: `fe/assets/20-chrome.css`
- Modify: `fe/app.py` — `_site_header()` (lines ~385-417) and the existing `.trec-header`/`.trec-nav*`/`.trec-footer*` rules currently in `30-components.css` (move/override them here)

- [ ] **Step 1: Create `fe/assets/20-chrome.css`**

```css
/* ===== Header ===== */
.trec-header {
  height: 64px;
  background: var(--trec-canvas);
  border-bottom: 1px solid var(--trec-border);
  box-shadow: none;
}
@media (min-width: 768px) { .trec-header { height: 72px; } }

.trec-logo {
  display: inline-flex; align-items: center; gap: .55rem;
  font-family: var(--font-display);
  color: var(--trec-green); font-weight: 900; font-size: 1.5rem;
  letter-spacing: .04em; text-decoration: none;
  padding: .25rem .4rem; border-radius: var(--r-sm);
}
.trec-logo:hover { color: var(--trec-green-dark); background: transparent; }
.trec-logo-mark {
  width: 22px; height: 22px;
  background: var(--trec-green);
  border-radius: 50% 50% 50% 0;
  transform: rotate(-45deg);
  display: inline-block;
}

.trec-nav { gap: 1.25rem; }
.trec-nav-link {
  color: var(--trec-muted); font-weight: 500; font-size: .9rem;
  text-decoration: none; white-space: nowrap;
  padding: .35rem .2rem; border-bottom: 2px solid transparent;
  transition: color .15s, border-color .15s;
}
.trec-nav-link:hover { color: var(--trec-green); }
.trec-nav-link--active {
  color: var(--trec-green); font-weight: 600;
  border-bottom-color: var(--trec-coral);
}

/* ===== Footer ===== */
.trec-footer {
  background: var(--trec-canvas);
  border-top: 1px solid var(--trec-border);
  padding: 1.5rem; color: var(--trec-muted); font-size: .85rem;
  margin-top: var(--sp-7);
}
.trec-footer-row {
  display: flex; flex-direction: column; align-items: center;
  gap: .5rem; text-align: center;
}
@media (min-width: 768px) {
  .trec-footer-row { flex-direction: row; justify-content: space-between; text-align: left; }
}
.trec-footer-brand {
  font-family: var(--font-display);
  color: var(--trec-green); font-weight: 700; letter-spacing: .04em;
}
.trec-footer-link { color: var(--trec-muted); text-decoration: none; }
.trec-footer-link:hover { color: var(--trec-green); text-decoration: underline; }
```

- [ ] **Step 2: Remove the now-duplicated chrome rules from `30-components.css`**

Delete from `fe/assets/30-components.css` the rule blocks for `.trec-header`, `.trec-logo`, `.trec-logo-droplet`, `.trec-nav-link`, `.trec-nav-link--active`, `.trec-nav`, `.trec-footer`, `.trec-footer-row`, `.trec-footer-brand`, `.trec-footer-link` (they are superseded by `20-chrome.css`). Leave all other rules (chips, predictive search, badges, tables, sort carets) intact.

- [ ] **Step 3: Update the logo markup in `app.py`**

In `_site_header()` replace the droplet `<I>` icon with the CSS wordmark mark. Change:

```python
                dcc.Link(
                    [
                        html.I(className="bi bi-house-fill trec-logo-droplet"),
                        html.Span("TREC"),
                    ],
                    href="/",
                    className="trec-logo",
                ),
```

to:

```python
                dcc.Link(
                    [
                        html.Span(className="trec-logo-mark"),
                        html.Span("TREC"),
                    ],
                    href="/",
                    className="trec-logo",
                ),
```

- [ ] **Step 4: Verify**

Reload `/about` (simple page, good for chrome). Expected: cream header, droplet-style green mark + "TREC" wordmark in Fraunces, nav links muted with green hover; the active page shows a coral underline. Footer matches. Navigate between pages to confirm the active underline tracks the route (the `_highlight_active_nav` callback is unchanged). `200`, no console errors. Screenshot → `.design/after-task3-chrome.png`.

- [ ] **Step 5: Commit**

```bash
git add fe/assets/20-chrome.css fe/assets/30-components.css fe/app.py
git commit -m "Restyle global header, nav, and footer (Coastal Editorial chrome)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Shared components (buttons, chips, badges, cards, tables, pagination, dropdown)

Goal: refine the reusable component layer in `30-components.css` to the new tokens and **fix the clashing coral-pink Bootstrap pagination**. Availability is the best verification page (table + pagination + badges).

**Files:**
- Modify: `fe/assets/30-components.css`

- [ ] **Step 1: Update the badge primitives in `30-components.css`**

Replace the existing `.trec-badge*` / `.trec-muted-dash` rule blocks with token-based versions:

```css
.trec-badge {
  display: inline-flex; align-items: center; justify-content: center;
  gap: .3rem; padding: .15rem .5rem; border-radius: var(--r-pill);
  font-size: .75rem; font-weight: 600; line-height: 1.4; white-space: nowrap;
}
.trec-badge-available {
  background: rgba(14,77,60,.10); color: var(--trec-green);
  border: 1px solid rgba(14,77,60,.20);
}
.trec-badge-available .trec-badge-glyph { font-weight: 700; line-height: 1; }
.trec-badge-count {
  background: rgba(14,77,60,.06); color: var(--trec-green);
  border: 1px solid rgba(14,77,60,.16); min-width: 1.75rem;
}
.trec-muted-dash { color: var(--trec-muted); font-weight: 500; }
```

- [ ] **Step 2: Update the table styling in `30-components.css`**

Replace the `.trec-table*` thead/tbody color rules so they use tokens and the green palette (keep the structural padding/border layout). Specifically set:

```css
.trec-table { margin-bottom: 0; font-size: 13px; }
.trec-table thead th {
  font-weight: 600; font-size: 12px; text-transform: uppercase;
  letter-spacing: .04em; color: var(--trec-green);
  background: var(--trec-paper-2);
  border-bottom: 1px solid var(--trec-border);
  border-top: none; padding: 10px 14px 10px 18px; vertical-align: middle;
}
.trec-table tbody td {
  padding: 10px 14px; border-top: none;
  border-bottom: 1px solid var(--trec-border-2);
  vertical-align: middle; font-size: 13px;
}
.trec-table.table-striped > tbody > tr:nth-of-type(odd) > * {
  background: rgba(14,77,60,.025); --bs-table-bg-type: rgba(14,77,60,.025); color: inherit;
}
.trec-table.table-hover > tbody > tr:hover > * {
  background: rgba(14,77,60,.06) !important; --bs-table-hover-bg: rgba(14,77,60,.06); color: inherit;
}
.trec-table tbody td a { text-decoration: none; color: var(--trec-green); border-bottom: 1px solid transparent; }
.trec-table tbody td a:hover { color: var(--trec-green-dark); border-bottom-color: var(--trec-coral); }
/* numeric cells */
.trec-table td.trec-num, .trec-table .trec-num { font-family: var(--font-mono); }
```

Also update the sort-caret color rules: change every `color: #1d5e4a;` to `color: var(--trec-green);` and every `color: #14463a;` (active) to `color: var(--trec-coral);` within the `.trec-table .trec-sort-*` and `.dash-header .column-header--sort` blocks. Leave the `\F235`/`\F229` glyph content and the `has_ena` hide rules unchanged.

- [ ] **Step 3: Update the predictive-search dropdown rules**

In the `.trec-predictive-search*` blocks, replace the hardcoded greens (`#1d5e4a`, `#14463a`, `rgba(29,94,74,…)`) with `var(--trec-green)`, `var(--trec-green-dark)`, and `rgba(14,77,60,…)` equivalents respectively. Keep structure/sizes.

- [ ] **Step 4: Add buttons, chips, pagination component rules**

Append to `30-components.css`:

```css
/* ===== Buttons ===== */
.btn.trec-btn-primary {
  background: var(--trec-coral); border-color: var(--trec-coral);
  color: #fff; font-weight: 600; border-radius: var(--r-sm); padding: .6rem 1.4rem;
}
.btn.trec-btn-primary:hover { background: var(--trec-coral-dark); border-color: var(--trec-coral-dark); color:#fff; }
.btn.trec-btn-ghost {
  background: transparent; border: 1px solid rgba(247,244,236,.5);
  color: var(--trec-canvas); font-weight: 600; border-radius: var(--r-sm); padding: .6rem 1.4rem;
}
.btn.trec-btn-ghost:hover { background: rgba(247,244,236,.12); color: var(--trec-canvas); }

/* ===== Chips (refine the existing .trec-chip) ===== */
.trec-chip {
  background: transparent; color: var(--trec-green);
  border: 1px solid var(--trec-green); border-radius: var(--r-pill);
}
.trec-chip:hover, .trec-chip:focus { background: rgba(14,77,60,.08); color: var(--trec-green); border-color: var(--trec-green); }
.trec-chip.active, .btn-check:checked + .trec-chip {
  background: var(--trec-green); color: #fff; border-color: var(--trec-green);
}

/* ===== Cards ===== */
.trec-card {
  background: var(--trec-paper); border: 1px solid var(--trec-border);
  border-radius: var(--r-md); box-shadow: var(--shadow-1);
}

/* ===== Pagination (fix clashing Bootstrap pink active) ===== */
.pagination { --bs-pagination-color: var(--trec-green); --bs-pagination-hover-color: var(--trec-green-dark);
  --bs-pagination-focus-color: var(--trec-green-dark);
  --bs-pagination-active-bg: var(--trec-green); --bs-pagination-active-border-color: var(--trec-green);
  --bs-pagination-hover-bg: rgba(14,77,60,.08); --bs-pagination-border-color: var(--trec-border);
}
```

(Note: the existing `.trec-chip` block from the old inline CSS may already be in the file — replace it with the version above rather than duplicating.)

- [ ] **Step 5: Verify**

Reload `/availability`. Expected: table headers green-on-cream, rows with subtle striping/hover, ✓ badges in green, pagination active page is **brand green (not pink)**. Search box and sort carets in green. `200`, no console errors. Screenshot → `.design/after-task4-availability.png`.

- [ ] **Step 6: Commit**

```bash
git add fe/assets/30-components.css
git commit -m "Restyle shared components; fix clashing pagination color

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Home page (editorial hero, stat strip, nav cards)

Goal: rebuild the home hero to the editorial treatment (drop the EMBL photo for a green gradient), present all 6 stats in a dark-green strip with mono numerals, and restyle the nav cards.

**Files:**
- Modify: `fe/pages/home.py` (`_hero` lines ~34-76, `_stat_card`/`_stats_section` lines ~79-148, `_nav_card`/`_nav_section` lines ~151-212)
- Create: home rules inside `fe/assets/40-pages.css`

- [ ] **Step 1: Create `fe/assets/40-pages.css` with the home section**

```css
/* ===== Home hero ===== */
.home-hero {
  position: relative; overflow: hidden;
  background: radial-gradient(120% 140% at 80% -20%, var(--trec-green-deep) 0%, var(--trec-green) 55%, var(--trec-green-dark) 100%);
  color: var(--trec-canvas);
  padding: var(--sp-8) var(--sp-5);
}
.home-hero .eyebrow {
  font-size: .75rem; letter-spacing: .28em; text-transform: uppercase;
  color: #9fd3c0; margin-bottom: var(--sp-4);
}
.home-hero h1 { color: var(--trec-canvas); font-size: clamp(2.2rem, 5vw, 3.4rem); line-height: 1.04; max-width: 18ch; margin-bottom: var(--sp-4); }
.home-hero p.lead { color: #cfe3da; max-width: 46ch; font-size: 1.05rem; }
.home-hero .blob {
  position: absolute; right: -60px; bottom: -120px; width: 360px; height: 360px;
  border-radius: 50% 50% 50% 0; background: rgba(217,113,78,.18); transform: rotate(-30deg);
}
.home-hero-inner { position: relative; z-index: 1; }

/* ===== Home stat strip ===== */
.home-stats { background: var(--trec-green-dark); }
.home-stat { padding: var(--sp-5); border-right: 1px solid rgba(255,255,255,.08); }
.home-stat:last-child { border-right: none; }
.home-stat .n { font-family: var(--font-mono); font-size: 1.9rem; font-weight: 600; color: #fff; line-height: 1; }
.home-stat .l { font-size: .72rem; letter-spacing: .12em; text-transform: uppercase; color: #9fd3c0; margin-top: var(--sp-2); }

/* ===== Home nav cards ===== */
.home-navcard {
  background: var(--trec-paper); border: 1px solid var(--trec-border);
  border-radius: var(--r-md); box-shadow: var(--shadow-1); height: 100%;
  transition: transform .15s, box-shadow .15s;
}
.home-navcard:hover { transform: translateY(-3px); box-shadow: var(--shadow-2); }
.home-navcard .ico { color: var(--trec-coral); font-size: 1.6rem; margin-bottom: var(--sp-3); }
.home-navcard h4 { font-size: 1.15rem; margin-bottom: var(--sp-2); }
```

- [ ] **Step 2: Rewrite `_hero()` in `home.py`**

Replace the entire `_hero()` function body (and the `BACKGROUND_URL` constant is no longer needed — delete it) with:

```python
def _hero():
    return html.Div(
        html.Div(
            [
                html.Div("Traversing European Coastlines", className="eyebrow"),
                html.H1("The molecular pulse of Europe's coastlines."),
                html.P(
                    "Explore biodiversity and molecular adaptation across "
                    "European coastal ecosystems — from molecules to whole "
                    "communities.",
                    className="lead",
                ),
                html.Div(
                    [
                        dcc.Link("Explore the data →", href="/data",
                                 className="btn trec-btn-primary me-2"),
                        dcc.Link("About TREC", href="/about",
                                 className="btn trec-btn-ghost"),
                    ],
                    className="mt-4",
                ),
            ],
            className="home-hero-inner",
        ),
        className="home-hero",
    )
```

Add `dcc` to the existing dash import in `home.py` if not present: `from dash import html, dcc`.

- [ ] **Step 3: Rewrite `_stats_section()` and `_stat_card()` in `home.py`**

Replace both with a single dark strip showing all 6 stats:

```python
def _stats_section():
    stats_data = _fetch_stats()
    items = [
        ("Stations", stats_data.get("total_stations")),
        ("Countries", stats_data.get("total_countries")),
        ("Source Samples", stats_data.get("total_source_samples")),
        ("Total Samples", stats_data.get("total_samples")),
        ("With Imaging", stats_data.get("total_with_images")),
        ("With ENA Data", stats_data.get("total_with_ena")),
    ]
    return html.Div(
        dbc.Row(
            [
                dbc.Col(
                    html.Div(
                        [
                            html.Div(_fmt(val), className="n"),
                            html.Div(label, className="l"),
                        ],
                        className="home-stat",
                    ),
                    xs=6, md=4, lg=2,
                )
                for label, val in items
            ],
            className="g-0",
        ),
        className="home-stats",
    )
```

(Delete the now-unused `_stat_card` function and its `icon` parameters. `_fmt` and `_fetch_stats` are unchanged.)

- [ ] **Step 4: Restyle `_nav_card()` in `home.py`**

Replace the card `className` values to use the new class. Change the `dbc.Card(...)` so it uses `className="home-navcard"` (drop `shadow-sm h-100 border-0`), the icon `html.I` keeps its `bi {icon}` but className becomes `f"bi {icon} ico d-block"` (drop `text-success fs-1`), and wrap content in `dbc.CardBody(..., className="p-4")`. Keep the `href`, `title`, `description`, and grid `xs/sm/lg` exactly as-is. Also wrap the nav section heading: in `_nav_section` precede the row with `html.H2("Explore the portal", className="mb-4")` inside the container, and give the container `className="trec-page"`.

- [ ] **Step 5: Verify**

Reload `/`. Expected: green gradient hero with Fraunces headline + coral "Explore the data" button + ghost "About TREC" button; a dark-green 6-up stat strip with mono numerals (97, 24, 67,809, 82,260, 351, 0); four editorial nav cards with coral icons that lift on hover. No EMBL photo. `200`, no console errors. Screenshot → `.design/after-task5-home.png` and compare with mock A.

- [ ] **Step 6: Commit**

```bash
git add fe/pages/home.py fe/assets/40-pages.css
git commit -m "Redesign home page: editorial hero, stat strip, nav cards

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Data Portal (filters, map, table, stats banner, pagination)

Goal: restyle the core tool. Layout and every callback stay; we change classes/props and the map's basemap + marker palette. This is the largest task — verify carefully.

**Files:**
- Modify: `fe/pages/data_portal.py` (filters sidebar ~44-112; stats banner callback `load_stats` ~197-229; map figure `load_map_and_filters` ~447-572; station summary card in `initialize_from_url` ~644-661)
- Modify: `fe/assets/40-pages.css` (append data-portal rules)
- Delete: `fe/assets/stat_cards.css`

- [ ] **Step 1: Append data-portal rules to `40-pages.css`**

```css
/* ===== Data portal stat banner ===== */
.stat-card { background: var(--trec-paper); border: 1px solid var(--trec-border) !important; border-radius: var(--r-md); box-shadow: var(--shadow-1); }
.stat-card .stat-icon { color: var(--trec-coral); margin-bottom: .25rem; line-height: 1; }
.stat-card .stat-number { font-family: var(--font-mono); font-size: 1.8rem; font-weight: 600; line-height: 1.1; }
.stat-card .stat-label { margin-top: .125rem; letter-spacing: .03em; }

/* ===== Filters sidebar ===== */
.portal-sidebar { background: var(--trec-paper-2); border: 1px solid var(--trec-border); border-radius: var(--r-md); padding: var(--sp-5); }
.portal-sidebar h6 { font-family: var(--font-display); }
.portal-sidebar .form-label, .portal-sidebar label.fw-bold {
  font-size: .72rem !important; letter-spacing: .12em; text-transform: uppercase;
  color: var(--trec-faint); font-weight: 600;
}
.portal-sidebar .form-check-label { text-transform: none; letter-spacing: 0; color: var(--trec-ink); font-weight: 400; font-size: .85rem; }
.portal-sidebar .form-check-input:checked { background-color: var(--trec-green); border-color: var(--trec-green); }

/* ===== Station summary panel ===== */
.station-panel-card { background: var(--trec-paper); border: 1px solid var(--trec-border); border-left: 4px solid var(--trec-coral); border-radius: var(--r-md); }
.station-panel-card .count { font-family: var(--font-mono); color: var(--trec-green); font-weight: 600; }
```

- [ ] **Step 2: Restyle the filters sidebar wrapper + chip-ify short lists in `data_portal.py`**

In `make_filters_sidebar()` change the outer return `className="p-3 border-end h-100"` to `className="portal-sidebar"`. Leave all child component IDs/options untouched.

Then convert the two **short** checklists to chip toggles using the exact pattern the existing `colour-by` `RadioItems` already uses (lines ~141-155), which is proven to work in this codebase. For `env-type-filter` and `analysis-type-filter`, change their `dbc.Checklist(id=..., className="small mb-3")` to:

```python
        dbc.Checklist(
            id="env-type-filter",
            inline=True,
            input_class_name="btn-check",
            label_class_name="btn btn-sm trec-chip mb-1 me-1",
            label_checked_class_name="active",
            class_name="mb-3",
        ),
```

and the analogous change for `analysis-type-filter` (same props, its own `id`). Keep the long lists (`organism-filter`, `country-filter`, `protocol-filter`) as checklists with their scroll-box `style`, and leave `source-filter` (RadioItems) and `linked-data-filter` as-is. Do NOT change any `id`, and do NOT set `options`/`value` here — those stay populated by their callbacks. (The widen of the sidebar column happens in Step 6.)

- [ ] **Step 3: Restyle the stats banner cards in `load_stats`**

In the `load_stats` callback, change each `dbc.Card` `className` from
`"stat-card shadow-sm h-100 border-0 border-start border-3 border-success"`
to `"stat-card h-100"`, and change the icon `className` from
`f"bi {icon} text-success fs-5 d-block stat-icon"` to
`f"bi {icon} fs-5 d-block stat-icon"`. Keep the IDs, the `stats` list, and grid `xs=6, md=3`.

- [ ] **Step 4: Recolor the map + switch basemap in `load_map_and_filters`**

In `load_map_and_filters`, update the palette constants and selected-marker so they match the brand:

- Change default station color `"#2c7a5c"` → `"#0E4D3C"` everywhere it appears (the `get_colour` `colour_by == "none"` return and the `LABELS["none"]` key).
- Replace the `COLOUR_MAPS` and the `has_images`/`unknown`/`no-match` colors with a coordinated set:

```python
    COLOUR_MAPS = {
        "environment_type": {"marine": "#2f7fa6", "soil": "#c08a3e",
                              "aerosol": "#7a6f9b"},
        "analysis_type": {"Metagenomics": "#0E4D3C", "Metabolomics": "#D9714E",
                          "Imaging": "#c08a3e", "Ions": "#3a8f7d"},
    }
    LABELS = {
        "none": {"#0E4D3C": "Stations", "#cfc6b4": "No matching samples"},
        "has_images": {"#D9714E": "Has images", "#9aa89f": "No images",
                       "#cfc6b4": "No matching samples"},
        "environment_type": {"#2f7fa6": "Marine", "#c08a3e": "Soil",
                             "#7a6f9b": "Aerosol", "#9aa89f": "Unknown",
                             "#cfc6b4": "No matching samples"},
        "analysis_type": {"#0E4D3C": "Metagenomics", "#D9714E": "Metabolomics",
                          "#c08a3e": "Imaging", "#3a8f7d": "Ions",
                          "#9aa89f": "Unknown", "#cfc6b4": "No matching samples"},
    }
```

- In `get_colour`, update the "no matching" return `"#cccccc"` → `"#cfc6b4"`, the `has_images` returns `"#f39c12"`/`"#95a5a6"` → `"#D9714E"`/`"#9aa89f"`, and the fallback `"#95a5a6"` → `"#9aa89f"`.
- For the selected-station highlight trace, change `marker=dict(size=22, color="#FFD700", opacity=1.0)` to `marker=dict(size=24, color="#0E4D3C", opacity=1.0)` (a larger deep-green dot; the trace `name="Selected"` stays). Do not add a `marker.line`/border — Scattermap markers don't reliably render outlines.
- In `fig.update_layout`, change `map=dict(style="open-street-map", …)` to `map=dict(style="carto-positron", center=dict(lat=43, lon=10), zoom=3.5)`.

- [ ] **Step 5: Restyle the station summary card in `initialize_from_url` and `show_station_panel`**

The station summary `dbc.Card` currently uses `className="mt-3 mb-2 bg-success bg-opacity-10"`. Change to `className="station-panel-card mt-3 mb-2 p-1"`. Change the inner count spans' `className="fw-bold text-success"` → `className="count"`, and the analysis-type `dbc.Badge(t, color="success", …)` → `dbc.Badge(t, className="trec-badge trec-badge-available me-1")`. Apply the same edits anywhere this summary card is constructed (search the file for `bg-success bg-opacity-10`). Keep all data values and IDs.

- [ ] **Step 6: Widen the filters column**

In the `layout`, change the filters `dbc.Col(make_filters_sidebar(), xs=12, md=2, className="pe-0")` to `xs=12, md=3, className="pe-3"` and the content column `dbc.Col([...], xs=12, md=10)` to `xs=12, md=9`. Wrap the whole `layout = dbc.Container([...])` content top padding by adding `className="trec-page"` to that `dbc.Container`.

- [ ] **Step 7: Delete the superseded `stat_cards.css`**

```bash
git rm fe/assets/stat_cards.css
```

(Its rules now live in `40-pages.css` from Step 1.)

- [ ] **Step 8: Verify (thorough)**

Reload `/data`. Then exercise behavior:
- Stat banner: 4 cards, coral icons, mono numerals.
- Filters sidebar: cream panel, uppercase labels, chips/checks in green; wider column.
- Map: clean light Carto basemap, **green** station dots (not the old teal), legend colors coordinated when switching "Color by" to Environment/Analysis/Has images.
- Click a station marker → summary card appears with coral left-border + mono counts + green analysis badges; samples table loads below; pagination active page is green.
- Apply a filter (e.g. an Environment chip) → non-matching stations grey out (`#cfc6b4`); table/filter options update.
Confirm `browser_console_messages` has **no callback errors** and `/data` returns `200`. Screenshot → `.design/after-task6-dataportal.png` and a second screenshot with a station selected.

- [ ] **Step 9: Commit**

```bash
git add fe/pages/data_portal.py fe/assets/40-pages.css
git commit -m "Redesign data portal: filters, map palette/basemap, table, banner

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Availability page polish

Goal: the table/pagination/badges already inherit the shared component styles (Task 4). Add page-level framing (title, search field, page padding) and confirm no clashes.

**Files:**
- Modify: `fe/pages/availability.py` (page heading/intro and the table container className)
- Modify: `fe/assets/40-pages.css` (append availability rules if needed)

- [ ] **Step 1: Apply page wrapper + heading treatment**

In `availability.py`, find the outermost layout container and add `className="trec-page"` to it. Ensure the page title uses an `html.H2`/`H3` (Fraunces will apply automatically) and the intro line uses `className="text-muted"`. Ensure the data table component has the `trec-table` class in its `className` (add it if missing) so it picks up the shared table styling. Do not change column definitions, the search `id`, sort state, or pagination `id`.

- [ ] **Step 2: Verify**

Reload `/availability`. Expected: Fraunces title, cream page, green table headers, ✓/— badges in brand tokens, green pagination. `200`, no console errors. Screenshot → `.design/after-task7-availability.png`.

- [ ] **Step 3: Commit**

```bash
git add fe/pages/availability.py fe/assets/40-pages.css
git commit -m "Polish availability page framing

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Sample details page

Goal: restyle the detail cards, headings, and image-viewer frame to tokens. No change to data fetching or the hardcoded remote URLs.

**Files:**
- Modify: `fe/pages/data_portal_details.py` (the `detail-content` rendering callback — cards, headings, badges)
- Modify: `fe/assets/40-pages.css` (append details rules if needed)

- [ ] **Step 1: Restyle detail rendering**

In the callback that builds `detail-content`, change any `dbc.Card` to include `className="trec-card"` (add to existing classes), convert `color="success"` badges to `className="trec-badge trec-badge-available"`, and ensure section headings are `html.H4`/`H5` (Fraunces). Frame the image/zarr viewer area with a `trec-card` wrapper and a small uppercase label using the sidebar label style. Keep `sample-id-store`, `build_zarr_proxy_url`, all URLs, and the data flow unchanged.

- [ ] **Step 2: Verify**

Navigate to a sample detail page. Easiest path: open `/data`, click a station, then click a sample link in the table (it routes to `/data-portal/<sample_id>`). Alternatively navigate directly to a known ID, e.g. `http://localhost:8050/data-portal/SAMEA118102762`. Expected: cards use the cream/paper card style, headings in Fraunces, badges in brand tokens. `200`, no console errors. Screenshot → `.design/after-task8-details.png`.

- [ ] **Step 3: Commit**

```bash
git add fe/pages/data_portal_details.py fe/assets/40-pages.css
git commit -m "Restyle sample details page

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: About + API pages

Goal: editorial treatment for About; clean frame for the API ReDoc iframe.

**Files:**
- Modify: `fe/pages/about.py`
- Modify: `fe/pages/api.py`
- Modify: `fe/assets/40-pages.css` (append about rules if needed)

- [ ] **Step 1: Editorialize About**

In `about.py`, add `className="trec-page"` to the outer `dbc.Container`, change the leading `html.H3` to `html.H1` (Fraunces display), give the body paragraphs `className="lead text-muted"` on the first paragraph for rhythm, and keep the two-column `dbc.Row` (md=8 / md=4) and the EMBL image/link exactly as-is.

- [ ] **Step 2: Frame the API page**

In `api.py`, add a page header above the iframe: wrap the existing `dbc.Container` content so it shows an `html.H2("API")` + a one-line `html.P("Programmatic access to TREC data via our REST API.", className="text-muted")` inside a `trec-page` wrapper, then the existing `iframe_layout()` below (keep the iframe `src` and styles). The iframe height can be reduced from `100vh` to `calc(100vh - 220px)` so the page header is visible. Do not change the iframe `src`.

- [ ] **Step 3: Verify**

Reload `/about` and `/api`. Expected: About has a Fraunces H1, readable lead paragraph, image intact; API shows a titled header above the framed ReDoc docs. `200`, no console errors. Screenshots → `.design/after-task9-about.png`, `.design/after-task9-api.png`.

- [ ] **Step 4: Commit**

```bash
git add fe/pages/about.py fe/pages/api.py fe/assets/40-pages.css
git commit -m "Editorialize about page and frame the API page

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: Cross-cutting pass (responsive, contrast, cleanup)

Goal: final QA across all pages at desktop and mobile widths, accessibility checks, and scratch-file cleanup.

**Files:**
- Modify: any `fe/assets/*.css` for fixes found
- Modify: `.gitignore` (ignore scratch artifacts)

- [ ] **Step 1: Mobile sweep**

`browser_resize` to 390×844. Navigate `/`, `/data`, `/availability`, `/about`, `/api`. Confirm: hero text wraps cleanly, stat strip reflows (6→2/3 per row), the data-portal filters collapse toggle (`filters-toggle`, `filters-collapse`) still works on mobile, tables scroll/stack acceptably, nothing overflows horizontally. Screenshot each → `.design/mobile-*.png`. Fix any overflow in CSS (prefer `40-pages.css`).

- [ ] **Step 2: Contrast + focus check**

Verify (visually and/or with the browser devtools accessibility panel) that: hero text on green ≥ AA, coral buttons text ≥ AA, muted greys on cream ≥ AA for body text. Tab through the data-portal controls and confirm the coral `:focus-visible` outline shows. Adjust token values only if a check fails.

- [ ] **Step 3: Desktop final sweep**

`browser_resize` to 1440×900. Navigate all six routes once more; confirm no console callback errors anywhere and each returns `200`. Capture a final `.design/final-*.png` set.

- [ ] **Step 4: Ignore scratch artifacts**

Append to `.gitignore`:

```
# Local design/QA scratch
.design/
.playwright-mcp/
/home.png
/dataportal.png
/availability.png
```

- [ ] **Step 5: Commit**

```bash
git add .gitignore fe/assets/
git commit -m "Cross-cutting redesign QA: responsive, contrast, focus, cleanup

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Final verification checklist (run after Task 10)

- [ ] All six routes (`/`, `/data`, `/availability`, `/data-portal/<id>`, `/about`, `/api`) return `200` and render with no console callback errors.
- [ ] Data portal: map markers/legend, station click → summary + table, filtering, search dropdown, and pagination all work and are restyled.
- [ ] No color clashes remain (map palette and pagination match brand).
- [ ] `app.py` has no inline `<style>` block; all styling lives in `fe/assets/*.css`.
- [ ] Fonts (Fraunces/Inter/IBM Plex Mono) load and apply.
- [ ] Desktop and mobile both look intentional; focus states visible; AA contrast holds.
- [ ] `fe/assets/stat_cards.css` removed; new `00/10/20/30/40` files present.
