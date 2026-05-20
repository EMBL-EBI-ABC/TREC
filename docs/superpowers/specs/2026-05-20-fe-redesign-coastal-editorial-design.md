# TREC Data Portal — Frontend Redesign ("Coastal Editorial")

**Date:** 2026-05-20
**Status:** Approved design, pending implementation plan
**Scope:** `fe/` (Dash frontend). Presentation-only — no backend or behavior changes.

## Goal

Dramatically raise the visual quality and professionalism of the TREC Data
Portal frontend while preserving 100% of existing functionality. The portal
serves a broad scientific audience (researchers plus funders, partners,
students, press), so it must read as both an impressive public face and a
capable data tool, as one cohesive product.

The chosen visual direction is **"Coastal Editorial"**: warm and credible —
serif display headings on a sand/cream canvas, deep EMBL green, a clay-coral
accent, and monospace numerals on data surfaces. EMBL-aligned but elevated.

## Constraints & Principles

- **No functionality changes.** Every page keeps its current component IDs,
  callbacks, data flow, URLs, and behavior. Changes are limited to markup
  classes, CSS, and cosmetic component props (colors, variants, sizes).
- **Stay in Dash.** Keep `dash` + `dash-bootstrap-components`. We replace the
  `dbc.themes.MINTY` theme with the neutral `dbc.themes.BOOTSTRAP` base so all
  `dbc` grid/components keep working, then layer a custom design system on top.
- **CSS lives in `fe/assets/`.** Dash auto-loads `assets/*.css`. The large
  inline `<style>` block currently in `app.py` migrates into organized
  stylesheet files. No JS build step, no new tooling.
- **Accessibility:** WCAG-AA contrast for all text/background and the
  green/coral combinations; visible focus states; preserve existing
  `visually-hidden` labels and ARIA affordances.
- **Responsive:** preserve current responsive breakpoints/behavior.

## Design System (foundation)

Delivered as CSS custom properties defined once, consumed everywhere.

### Color tokens
- `--trec-green: #0E4D3C` (primary)
- `--trec-green-dark: #0a3a2d`
- `--trec-green-deep: #15614b` (gradient highlight)
- `--trec-canvas: #F7F4EC` (sand/cream page background)
- `--trec-paper: #FFFFFF` (cards/surfaces)
- `--trec-ink: #1A2420` (primary text)
- `--trec-coral: #D9714E` (accent / primary action / active indicators)
- Muted sage greys for secondary text, borders, and disabled/empty states
  (e.g. `--trec-muted`, `--trec-border`).
- Semantic aliases: `--surface`, `--border`, `--link`, `--accent`.

### Typography
- **Fraunces** (serif) — hero, page titles, section headings.
- **Inter** (sans) — UI, body, labels, nav.
- **IBM Plex Mono** — large stat numerals and numeric table cells / sample IDs
  only. Reinforces "scientific instrument" precision without shifting the
  editorial direction.
- Fonts loaded via Google Fonts (`<link>` in the Dash index template or
  `external_stylesheets`).

### Spacing / radius / shadow
- 8px-based spacing scale.
- Radii: 8px (controls/badges), 14px (cards/panels).
- Two soft elevation levels (subtle card shadow, stronger panel shadow).

### File organization (`fe/assets/`)
Proposed split (final names decided in the plan):
- `00-tokens.css` — variables (color, type, spacing, radius, shadow).
- `10-base.css` — element resets, typography defaults, links.
- `20-chrome.css` — header, nav, footer.
- `30-components.css` — buttons, chips, badges, cards, tables, pagination,
  dropdowns (the current `trec-*` rules, refined).
- `40-pages.css` — page-specific (home hero, portal layout, availability).

## Global Chrome

- **Header:** cream bar; refined wordmark = a small droplet/wave mark +
  "TREC"; nav links in Inter with a coral underline on the active route
  (refine the existing active-nav callback styling — callback logic unchanged).
- **Footer:** keep existing content and links; restyle to match tokens.

## Page Designs

### Home (`pages/home.py`)
- Editorial hero: deep-green gradient band, uppercase eyebrow ("Traversing
  European Coastlines"), large Fraunces headline, supporting sentence, two
  buttons — coral primary "Explore the data" → `/data`, ghost secondary
  "About TREC" → `/about`.
- The current full-bleed EMBL banner photo is demoted to an optional subtle
  background texture (or dropped) in favor of the gradient treatment.
- **Stat strip:** dark-green band, mono numerals, served by the existing
  `_fetch_stats()` data (Stations, Countries, Source Samples, Total Samples,
  With Imaging, With ENA Data).
- Existing nav cards restyled as clean editorial cards.

### Data Portal (`pages/data_portal.py`) — core tool
Keep the exact layout (filters | search + map + table) and every callback.
- **Filters sidebar:** widen slightly; group under small uppercase section
  labels; render short option lists (environment, analysis type, sample type,
  linked data) as editorial **chip / pill toggles**; keep scroll-boxed
  checklists for long lists (organism, country, protocol). Options data and
  callback wiring unchanged.
- **Map:** switch Plotly basemap from `open-street-map` to a cleaner muted
  basemap (`carto-positron`). Recolor markers to a harmonious brand palette
  (default station = coral) and remap the existing "color by" modes
  (environment_type, analysis_type, has_images) to a coordinated set that no
  longer clashes with the brand green. Selected-station highlight changes from
  gold (`#FFD700`) to a deep-green ring. `colour-by` options and callback
  behavior preserved.
- **Stats banner / station panel / sample table:** apply the new table system
  (`trec-table` refined), mono numerals for counts and sample IDs,
  coral/green badges for availability glyphs.
- **Pagination:** fix the clashing default Bootstrap coral-pink active button
  to brand green/coral.

### Availability (`pages/availability.py`)
- Apply the shared table system; fix the pink active-page pagination button;
  refine the ✓ / — availability cell badges to brand tokens.

### Sample Details (`pages/data_portal_details.py`)
- Restyle cards, headings, and the image-viewer framing to tokens.
- Out of scope: the hardcoded remote URLs (`BIONGFF_VIEWER_URL`, `S3_BASE`,
  `PROXY_BASE`) — left as-is.

### About (`pages/about.py`)
- Editorial two-column layout with Fraunces headings; keep copy and the EMBL
  link/image.

### API (`pages/api.py`)
- Keep the ReDoc iframe; restyle only the surrounding page frame.

## Cross-cutting

- Consistent visible focus states across interactive elements.
- WCAG-AA contrast verified on green/coral text combinations.
- Remove color-system clashes (map palette vs. brand; pagination).
- Migrate the inline `<style>` in `app.py` into `assets/`.

## Out of Scope

- Any backend (`be/`) change.
- Any change to data shape, filtering logic, callbacks, routing, or component
  IDs.
- The hardcoded remote URLs in the sample-details page.
- New build tooling / JS framework.

## Success Criteria

- All current pages render and behave identically (every callback works; map
  selection, filtering, search, pagination, station detail all functional).
- Visual quality is markedly improved and cohesive across all six pages,
  matching the approved "Coastal Editorial" direction.
- No remaining color clashes (map markers, pagination) with the brand palette.
- Inline styles removed from `app.py`; styling lives in organized `assets/`
  CSS.
- Responsive behavior and accessibility (contrast, focus, labels) preserved or
  improved.

## Verification Approach

Run the FE locally against the BE on `:8000` and visually verify each page
(home, data portal incl. station selection + filtering + pagination,
availability, sample details, about, API) at desktop and mobile widths, using
browser screenshots for before/after comparison.
