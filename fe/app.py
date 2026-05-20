import dash
from dash import Input, Output, dcc, html
import dash_bootstrap_components as dbc

app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
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
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,900&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap" rel="stylesheet">
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


def _site_header():
    return html.Header(
        html.Div(
            [
                dcc.Link(
                    [
                        html.Span(className="trec-logo-mark",
                                  **{"aria-hidden": "true"}),
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
