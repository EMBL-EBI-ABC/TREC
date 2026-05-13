import dash
from dash import Input, Output, dcc, html
import dash_bootstrap_components as dbc

app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.MINTY,
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css",
    ],
    use_pages=True,
    suppress_callback_exceptions=True,
)

NAV_ITEMS = [
    ("Data Portal", "/data"),
    ("Availability", "/availability"),
    ("API", "/api"),
    ("About", "/about"),
]

app.index_string = """<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            .trec-header {
                height: 60px; background: #fafaf8;
                border-bottom: 1px solid #e9e9e9;
                box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            }
            @media (min-width: 768px) {
                .trec-header { height: 70px; }
            }
            .trec-logo {
                display: inline-flex; align-items: center;
                color: #1d3a2e; font-weight: 700; font-size: 1.4rem;
                letter-spacing: .1em; text-decoration: none;
                padding: .25rem .5rem; border-radius: 4px;
                transition: background-color .15s, color .15s;
            }
            .trec-logo:hover, .trec-logo:focus {
                color: #122620;
                background-color: rgba(29, 94, 74, 0.06);
                text-decoration: none;
            }
            .trec-logo-droplet {
                color: #1d5e4a; font-size: 1.2rem;
                margin-right: .4rem;
            }
            .trec-nav-link {
                color: #555; font-weight: 400; font-size: .85rem;
                text-decoration: none;
                transition: color .15s, background-color .15s,
                            border-color .15s;
                white-space: nowrap;
                padding: .25rem .5rem;
                border-bottom: 2px solid transparent;
                border-radius: 4px;
            }
            .trec-nav-link:hover, .trec-nav-link:focus {
                color: #1d3a2e; text-decoration: none;
                background-color: rgba(29, 94, 74, 0.06);
            }
            .trec-nav-link--active {
                color: #1d5e4a; font-weight: 600;
                border-bottom-color: #1d5e4a;
            }
            .trec-nav { gap: .65rem; }
            .trec-chip {
                background-color: transparent;
                color: #1d5e4a;
                border: 1px solid #1d5e4a;
                transition: background-color .15s, color .15s;
            }
            .trec-chip:hover, .trec-chip:focus {
                background-color: rgba(29, 94, 74, 0.08);
                color: #1d5e4a;
                border-color: #1d5e4a;
            }
            .trec-chip.active,
            .btn-check:checked + .trec-chip {
                background-color: #1d5e4a;
                color: #fff;
                border-color: #1d5e4a;
            }
            /* Predictive-search dropdown */
            .trec-predictive-search .Select-control {
                border: 1px solid #1d5e4a;
                border-radius: .375rem;
                box-shadow: none;
                min-height: 38px;
            }
            .trec-predictive-search .Select-control:hover {
                border-color: #14463a;
            }
            .trec-predictive-search.is-focused:not(.is-open)
                > .Select-control {
                border-color: #1d5e4a;
                box-shadow: 0 0 0 .15rem rgba(29, 94, 74, 0.2);
            }
            .trec-predictive-search .Select-placeholder {
                color: #6c757d;
                font-size: .9rem;
            }
            .trec-predictive-search .Select-menu-outer {
                border: 1px solid #d6e3df;
                box-shadow: 0 6px 14px rgba(0,0,0,0.08);
                border-radius: .375rem;
                margin-top: 2px;
                z-index: 1050;
            }
            .trec-predictive-search .Select-option.is-focused {
                background-color: rgba(29, 94, 74, 0.08);
            }
            .trec-predictive-search .Select-option.is-selected {
                background-color: rgba(29, 94, 74, 0.16);
                color: #1d3a2e;
            }
            .trec-suggest-option {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: .75rem;
                width: 100%;
            }
            .trec-suggest-name {
                color: #1d3a2e;
                font-size: .9rem;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }
            .trec-suggest-meta {
                color: #6c757d;
                font-size: .75rem;
                font-variant: small-caps;
                letter-spacing: .03em;
                white-space: nowrap;
                flex-shrink: 0;
            }
            @media (min-width: 480px) {
                .trec-nav-link { font-size: .9rem; }
                .trec-nav { gap: 1rem; }
            }
            @media (min-width: 768px) {
                .trec-nav { gap: 1.5rem; }
            }
            .trec-footer {
                background: #fafaf8;
                border-top: 1px solid #e9e9e9;
                padding: 1.25rem 1.5rem;
                color: #6c757d; font-size: .85rem;
                margin-top: 2rem;
            }
            .trec-footer-row {
                display: flex; flex-direction: column;
                align-items: center; gap: .5rem;
                text-align: center;
            }
            @media (min-width: 768px) {
                .trec-footer-row {
                    flex-direction: row;
                    justify-content: space-between;
                    text-align: left;
                }
            }
            .trec-footer-brand {
                color: #1d3a2e; font-weight: 600;
                font-size: .9rem; letter-spacing: .08em;
            }
            .trec-footer-link {
                color: #6c757d; text-decoration: none;
            }
            .trec-footer-link:hover, .trec-footer-link:focus {
                color: #1d3a2e; text-decoration: underline;
            }
            /* ===== Tables: shared badge primitives ===== */
            .trec-badge {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: .3rem;
                padding: .15rem .5rem;
                border-radius: 999px;
                font-size: .75rem;
                font-weight: 600;
                line-height: 1.4;
                white-space: nowrap;
            }
            .trec-badge-available {
                background-color: rgba(29, 94, 74, 0.10);
                color: #1d5e4a;
                border: 1px solid rgba(29, 94, 74, 0.20);
            }
            .trec-badge-available .trec-badge-glyph {
                font-weight: 700;
                line-height: 1;
            }
            .trec-badge-count {
                background-color: rgba(29, 94, 74, 0.06);
                color: #1d3a2e;
                border: 1px solid rgba(29, 94, 74, 0.16);
                min-width: 1.75rem;
            }
            .trec-muted-dash {
                color: #6c757d;
                font-weight: 500;
            }
            /* ===== Tables: shared polish for HTML tables (dbc.Table).
                  The samples DataTable mirrors these values inline via
                  style_header / style_cell on the component itself
                  (DataTable has its own DOM and can't consume this
                  class). Apply this class to dbc.Table components to
                  match the samples-table visual rhythm. ===== */
            .trec-table {
                margin-bottom: 0;
                font-size: 13px;
            }
            .trec-table thead th {
                font-weight: 600;
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 0.04em;
                color: #1d3a2e;
                background-color: rgba(29, 94, 74, 0.06);
                border-bottom: 1px solid #d6e3df;
                border-top: none;
                padding: 10px 14px 10px 18px;
                vertical-align: middle;
            }
            .trec-table tbody td {
                padding: 10px 14px;
                border-top: none;
                border-bottom: 1px solid #eef2f0;
                vertical-align: middle;
                font-size: 13px;
            }
            .trec-table.table-striped > tbody
                > tr:nth-of-type(odd) > * {
                background-color: rgba(29, 94, 74, 0.025);
                --bs-table-bg-type: rgba(29, 94, 74, 0.025);
                color: inherit;
            }
            .trec-table.table-hover > tbody > tr:hover > * {
                background-color: rgba(29, 94, 74, 0.08) !important;
                --bs-table-hover-bg: rgba(29, 94, 74, 0.08);
                color: inherit;
            }
            .trec-table tbody td a {
                text-decoration: none;
                color: #1d5e4a;
                border-bottom: 1px solid transparent;
                transition: color .15s, border-color .15s;
            }
            .trec-table tbody td a:hover {
                color: #14463a;
                border-bottom-color: #1d5e4a;
            }
            /* Sort indicators for dbc.Table headers — visually
               mirrors Dash DataTable's bundled fa-sort icons used on
               the samples table. Bootstrap Icons (loaded site-wide)
               doesn't have a single combined sort glyph, so we stack
               bi-caret-up-fill + bi-caret-down-fill and toggle the
               active caret based on sort direction. */
            .trec-table thead th.trec-sortable {
                cursor: pointer;
                user-select: none;
            }
            .trec-table .trec-sort-trigger {
                display: inline-flex;
                align-items: center;
                gap: .55rem;
                vertical-align: middle;
            }
            .trec-table .trec-sort-arrow {
                display: inline-flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                color: #1d5e4a;
                font-weight: normal;
                text-transform: none;
                letter-spacing: 0;
                line-height: 1;
            }
            .trec-table .trec-sort-caret {
                font-size: 9px;
                line-height: 0.85;
                display: block;
                opacity: 0.35;
                transition: opacity .15s, color .15s;
            }
            .trec-table thead th.trec-sortable:hover
                .trec-sort-caret {
                opacity: 0.65;
            }
            .trec-table .trec-sort-caret.active {
                opacity: 1;
                color: #14463a;
            }
            /* Samples table (Dash DataTable) sort indicator.
               DataTable bundles a Font Awesome fa-sort SVG (both
               triangles in one glyph) which renders too tightly
               stacked. Hide the SVG and synthesize the same
               two-Bootstrap-Icon stack the dbc.Table version above
               uses — shared font-size + line-height keeps the gap
               pixel-identical across both tables. Active-direction
               highlight uses :has() against FA's data-icon. */
            .dash-header .column-header--sort {
                display: inline-flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                color: #1d5e4a;
                line-height: 1;
                margin-right: .55rem;
                margin-left: 0;
                vertical-align: middle;
                cursor: pointer;
                transition: color .15s;
            }
            .dash-header .column-header--sort svg {
                display: none;
            }
            .dash-header .column-header--sort::before,
            .dash-header .column-header--sort::after {
                font-family: "bootstrap-icons";
                font-style: normal;
                font-weight: normal;
                font-size: 9px;
                line-height: 0.85;
                display: block;
                opacity: 0.35;
                transition: opacity .15s, color .15s;
            }
            .dash-header .column-header--sort::before {
                content: "\\F235";
            }
            .dash-header .column-header--sort::after {
                content: "\\F229";
            }
            .dash-header:hover .column-header--sort::before,
            .dash-header:hover .column-header--sort::after {
                opacity: 0.65;
            }
            .dash-header .column-header--sort:has(
                svg[data-icon="sort-up"])::before,
            .dash-header .column-header--sort:has(
                svg[data-icon="sort-down"])::after {
                opacity: 1;
                color: #14463a;
            }
            /* Non-sortable badge columns on the samples table: hide
               the sort indicator and swallow clicks on the header so
               there's no "No samples found" round-trip when the user
               clicks the column title. */
            .dash-header[data-dash-column="has_images"]
                .column-header--sort,
            .dash-header[data-dash-column="has_ena"]
                .column-header--sort {
                display: none;
            }
            .dash-header[data-dash-column="has_images"],
            .dash-header[data-dash-column="has_ena"] {
                cursor: default;
            }
            .dash-header[data-dash-column="has_images"]
                .column-header-name,
            .dash-header[data-dash-column="has_ena"]
                .column-header-name {
                pointer-events: none;
            }
        </style>
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


def _site_header():
    return html.Header(
        html.Div(
            [
                dcc.Link(
                    [
                        html.I(className="bi bi-house-fill trec-logo-droplet"),
                        html.Span("TREC"),
                    ],
                    href="/",
                    className="trec-logo",
                ),
                html.Nav(
                    [
                        dcc.Link(
                            label,
                            href=href,
                            id={"role": "trec-nav", "href": href},
                            className="trec-nav-link",
                        )
                        for label, href in NAV_ITEMS
                    ],
                    className="trec-nav d-flex align-items-center",
                ),
            ],
            className=(
                "d-flex align-items-center justify-content-between "
                "h-100 px-3 px-md-4"
            ),
        ),
        className="trec-header",
        style={"width": "100%"},
    )


def _site_footer():
    return html.Footer(
        html.Div(
            [
                html.Span("TREC", className="trec-footer-brand"),
                html.Span(
                    [
                        "Traversing European Coastlines · ",
                        html.A(
                            "An EMBL initiative",
                            href="https://www.embl.org/about/info/trec/",
                            target="_blank",
                            rel="noopener noreferrer",
                            className="trec-footer-link",
                        ),
                    ],
                ),
                html.Span("© 2026 EMBL"),
            ],
            className="trec-footer-row",
        ),
        className="trec-footer",
    )


app.layout = html.Div(
    [
        dcc.Location(id="trec-nav-url", refresh=False),
        _site_header(),
        html.Div(dash.page_container, style={"flex": "1 0 auto"}),
        _site_footer(),
    ],
    style={
        "minHeight": "100vh",
        "display": "flex",
        "flexDirection": "column",
    },
)
server = app.server


@app.callback(
    [Output({"role": "trec-nav", "href": href}, "className")
     for _, href in NAV_ITEMS],
    Input("trec-nav-url", "pathname"),
)
def _highlight_active_nav(pathname):
    pathname = pathname or "/"
    classes = []
    for _, href in NAV_ITEMS:
        is_active = pathname == href or pathname.startswith(href + "/")
        classes.append(
            "trec-nav-link trec-nav-link--active" if is_active
            else "trec-nav-link"
        )
    return classes


if __name__ == "__main__":
    app.run_server(debug=True)
