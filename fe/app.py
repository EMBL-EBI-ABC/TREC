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
                height: 60px; background: #fff;
                border-bottom: 1px solid #e9e9e9;
                box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            }
            @media (min-width: 768px) {
                .trec-header { height: 70px; }
            }
            .trec-logo {
                color: #1d3a2e; font-weight: 700; font-size: 1.4rem;
                letter-spacing: .1em; text-decoration: none;
                transition: opacity .15s;
            }
            .trec-logo:hover, .trec-logo:focus {
                color: #1d3a2e; opacity: .75; text-decoration: none;
            }
            .trec-logo-accent {
                color: #1d5e4a; margin-left: .35em;
                font-size: 1.6rem; line-height: 1;
                vertical-align: -.05em;
            }
            .trec-nav-link {
                color: #555; font-weight: 400; font-size: .85rem;
                text-decoration: none; transition: color .15s;
                white-space: nowrap; padding: .25rem 0;
            }
            .trec-nav-link:hover, .trec-nav-link:focus {
                color: #1d3a2e; text-decoration: none;
            }
            .trec-nav-link--active {
                color: #1d5e4a; font-weight: 600;
                border-bottom: 2px solid #1d5e4a;
            }
            .trec-nav { gap: .65rem; }
            @media (min-width: 480px) {
                .trec-nav-link { font-size: .9rem; }
                .trec-nav { gap: 1rem; }
            }
            @media (min-width: 768px) {
                .trec-nav { gap: 1.5rem; }
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
                        html.Span("TREC"),
                        html.Span("•", className="trec-logo-accent"),
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


app.layout = html.Div([
    dcc.Location(id="trec-nav-url", refresh=False),
    _site_header(),
    dash.page_container,
])
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
