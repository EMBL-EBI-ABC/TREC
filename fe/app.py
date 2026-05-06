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
                height: 70px; background-color: #1d5e4a;
                border-bottom: 1px solid rgba(0,0,0,0.1);
            }
            .trec-logo {
                color: #fff; font-weight: 700; font-size: 1.5rem;
                letter-spacing: .15em; text-decoration: none;
                transition: opacity .15s;
            }
            .trec-logo:hover, .trec-logo:focus {
                color: #fff; opacity: .8; text-decoration: none;
            }
            .trec-nav-link {
                color: #fff; opacity: .85; text-decoration: none;
                font-size: .85rem; transition: opacity .15s;
                white-space: nowrap;
            }
            .trec-nav-link:hover, .trec-nav-link:focus {
                color: #fff; opacity: 1; text-decoration: underline;
                text-underline-offset: .25em;
            }
            .trec-nav-link--active {
                opacity: 1; font-weight: 600;
                text-decoration: underline; text-underline-offset: .3em;
                text-decoration-thickness: 2px;
            }
            .trec-nav { gap: .65rem; }
            @media (min-width: 480px) {
                .trec-nav-link { font-size: .95rem; }
                .trec-nav { gap: 1rem; }
            }
            @media (min-width: 768px) {
                .trec-header { height: 90px; }
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
                dcc.Link("TREC", href="/", className="trec-logo"),
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
