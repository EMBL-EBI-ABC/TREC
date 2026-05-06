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
