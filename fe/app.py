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
    ("Data Portal", "/data-portal"),
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
        <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap" rel="stylesheet">
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
                    "TREC",
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
    footer_columns = [
        (
            "Services",
            [
                ("Data resources and tools", "https://www.ebi.ac.uk/services/data-resources-and-tools/"),
                ("Data submission", "https://www.ebi.ac.uk/submission"),
                ("Support and feedback", "https://www.ebi.ac.uk/about/contact/support/"),
                ("Licensing", "https://www.ebi.ac.uk/licencing/"),
                ("Long-term data preservation", "https://www.ebi.ac.uk/long-term-data-preservation/"),
            ],
        ),
        (
            "Research",
            [
                ("Publications", "https://www.ebi.ac.uk/research/publications/"),
                ("Research groups", "https://www.ebi.ac.uk/research/groups/"),
                ("Postdocs and PhDs", "https://www.ebi.ac.uk/research/postdocs/"),
            ],
        ),
        (
            "Training",
            [
                ("Live training", "https://www.ebi.ac.uk/training/live-events"),
                ("On-demand training", "https://www.ebi.ac.uk/training/on-demand"),
                ("Support for trainers", "https://www.ebi.ac.uk/training/trainer-support"),
                ("Contact organisers", "https://www.ebi.ac.uk/about/contact/support/training"),
            ],
        ),
        (
            "Industry",
            [
                ("Members Area", None),
                ("Contact Industry team", "https://www.ebi.ac.uk/industry/"),
            ],
        ),
        (
            "About",
            [
                ("FAQ", "https://www.ebi.ac.uk/about/faq/"),
                ("Contact us", "https://www.ebi.ac.uk/about/contact/"),
                ("Events", "https://www.ebi.ac.uk/about/events/"),
                ("Jobs", "https://www.ebi.ac.uk/careers/"),
                ("News", "https://www.ebi.ac.uk/about/news/"),
                ("People and groups", "https://www.ebi.ac.uk/people/"),
                ("Intranet for staff", "https://intranet.ebi.ac.uk/"),
            ],
        ),
    ]

    return html.Footer(
        html.Div(
            [
                html.Div(
                    [
                        html.P(
                            "EMBL-EBI is the home for big data in biology.",
                            className="trec-footer-intro",
                        ),
                        html.P(
                            "We help scientists exploit complex information "
                            "to make discoveries that benefit humankind.",
                            className="trec-footer-intro",
                        ),
                    ],
                    className="trec-footer-intro-block",
                ),

                html.Div(
                    [
                        html.Div(
                            [
                                html.H2(
                                    heading,
                                    className="trec-footer-heading",
                                ),
                                html.Ul(
                                    [
                                        html.Li(
                                            html.A(
                                                label,
                                                href=href,
                                                className="trec-footer-link",
                                            )
                                            if href
                                            else html.Span(
                                                label,
                                                className="trec-footer-placeholder",
                                            )
                                        )
                                        for label, href in links
                                    ],
                                    className="trec-footer-list",
                                ),
                            ],
                            className="trec-footer-column",
                        )
                        for heading, links in footer_columns
                    ],
                    className="trec-footer-grid",
                ),

                html.Div(className="trec-footer-divider"),

                html.Div(
                    [
                        html.Span(
                            "EMBL-EBI, Wellcome Genome Campus, "
                            "Hinxton, Cambridgeshire, CB10 1SD, UK."
                        ),
                        html.Span("Tel: +44 (0)1223 49 44 44"),
                        html.Span("Full contact details"),
                    ],
                    className="trec-footer-contact",
                ),

                html.Div(
                    [
                        html.Span("Copyright © EMBL 2026"),
                        html.Span(
                            "EMBL-EBI is part of the European Molecular "
                            "Biology Laboratory"
                        ),
                        html.Span("Terms of use"),
                    ],
                    className="trec-footer-legal",
                ),
            ],
            className="trec-footer-inner",
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


@server.route("/data")
def _redirect_legacy_data():
    """Permanent redirect from the old list path to /data-portal,
    preserving any query string (e.g. ?station=...)."""
    from flask import redirect, request
    qs = request.query_string.decode()
    target = "/data-portal" + (f"?{qs}" if qs else "")
    return redirect(target, code=301)


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
