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
        <link rel="stylesheet" href="https://assets.emblstatic.net/vf/v2.5.30/css/styles.css">
        {%css%}
    </head>
    <body>
        <header id="masthead-black-bar"
            class="clearfix masthead-black-bar ebi-header-footer vf-content vf-u-fullbleed">
        <div>
            <nav id="search-bar" class="search-bar global-masthead-interactive-banner">
                <div class="row padding-bottom-medium">
                    <div class="columns padding-top-medium">
                        <button class="close-button" aria-label="Close search" type="button">
                            <span aria-hidden="true">x</span>
                        </button>
                    </div>
                </div>
                <div class="row">
                    <form id="global-search" name="global-search"
                          action="https://www.ebi.ac.uk/ebisearch/search.ebi"
                          method="GET">
                        <div class="input-group">
                            <label class="vf-form__label vf-u-sr-only"
                                   for="global-searchbox">Search all of EMBL-EBI</label>
                            <input type="text" name="query" id="global-searchbox"
                                   class="input-group-field"
                                   placeholder="Search all of EMBL-EBI">
                            <div class="input-group-button">
                                <input type="submit" name="submit" value="Search" class="button">
                                <input type="hidden" name="db" value="allebi">
                                <input type="hidden" name="requestFrom" value="ebi_index">
                            </div>
                        </div>
                    </form>
                </div>
            </nav>
        </div>
        <div>
            <nav class="row" aria-label="EMBL-EBI global navigation">
                <ul id="global-nav" class="menu global-nav text-right"
                    data-vf-google-analytics-region="Black bar">
                    <li class="float-right show-for-medium embl-ebi">
                        <a class="float-right custom-ebi-logo-bg custom-ebi-logo-bg-transparent-text"
                           href="https://www.ebi.ac.uk/">EMBL-EBI</a>
                    </li>
                    <li class="float-right search">
                        <a href="#" class="inline-block collpased float-left search-toggle"
                           aria-label="Open EMBL-EBI search">
                            <span class="show-for-small-only">Search</span>
                        </a>
                    </li>
                    <li class="what about"><a href="https://www.ebi.ac.uk/about">About us</a></li>
                    <li class="what training"><a href="https://www.ebi.ac.uk/training">Training</a></li>
                    <li class="what research"><a href="https://www.ebi.ac.uk/research">Research</a></li>
                    <li class="what services"><a href="https://www.ebi.ac.uk/services">Services</a></li>
                    <li class="where ebi"><a href="https://www.ebi.ac.uk/">EMBL-EBI home</a></li>
                </ul>
            </nav>
        </div>
    </header>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
            <script src="https://assets.emblstatic.net/vf/v2.5.30/scripts/scripts.js"></script>
        </footer>
    </body>
</html>"""


def _site_header():
    return html.Header(
        dbc.Container(
            [
                dcc.Link(
                    "TREC Data Portal",
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
                "trec-header-container d-flex align-items-center "
                "justify-content-between h-100"
            ),
        ),
        className="trec-header",
        style={"width": "100%"},
    )


def _site_footer():
    footer_columns = [
        (
            "Services",
            "https://www.ebi.ac.uk/services",
            [
                ("Data resources and tools", "https://www.ebi.ac.uk/services/data-resources-and-tools"),
                ("Data submission", "https://www.ebi.ac.uk/submission"),
                ("Support and feedback", "https://www.ebi.ac.uk/support"),
                ("Licensing", "https://www.ebi.ac.uk/licencing"),
                ("Long-term data preservation", "https://www.ebi.ac.uk/long-term-data-preservation"),
            ],
        ),
        (
            "Research",
            "https://www.ebi.ac.uk/research",
            [
                ("Publications", "https://www.ebi.ac.uk/research/publications"),
                ("Research groups", "https://www.ebi.ac.uk/research/groups"),
                ("Postdocs", "https://www.ebi.ac.uk/research/postdocs"),
                ("PhDs", "https://www.ebi.ac.uk/research/eipp"),
            ],
        ),
        (
            "Training",
            "https://www.ebi.ac.uk/training",
            [
                ("Live training", "https://www.ebi.ac.uk/training/live-events"),
                ("On-demand training", "https://www.ebi.ac.uk/training/on-demand"),
                ("Support for trainers", "https://www.ebi.ac.uk/training/trainer-support"),
                ("Contact organisers", "https://www.ebi.ac.uk/training/contact-us"),
            ],
        ),
        (
            "Industry",
            "https://www.ebi.ac.uk/industry",
            [
                ("Members Area", "https://www.ebi.ac.uk/industry/private/members-area/"),
                ("Contact Industry team", "https://www.ebi.ac.uk/industry/contact-us"),
            ],
        ),
        (
            "About",
            "https://www.ebi.ac.uk/about",
            [
                ("FAQ", "https://www.ebi.ac.uk/about/faq"),
                ("Contact us", "https://www.ebi.ac.uk/about/contact"),
                ("Events", "https://www.ebi.ac.uk/about/events"),
                ("Jobs", "https://www.ebi.ac.uk/about/jobs"),
                ("News", "https://www.ebi.ac.uk/about/news"),
                ("People and groups", "https://www.ebi.ac.uk/about/people"),
                ("Intranet for staff", "https://intranet.ebi.ac.uk"),
            ],
        ),
    ]

    return html.Footer(
        html.Div(
            [
                html.P(
                    html.A(
                        "EMBL-EBI is the home for big data in biology.",
                        href="https://www.ebi.ac.uk/about/our-impact",
                        className="vf-footer__link",
                    ),
                    className="vf-footer__notice",
                ),
                html.P(
                    "We help scientists exploit complex information "
                    "to make discoveries that benefit humankind.",
                    className="vf-footer__notice",
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.H4(
                                    html.A(
                                        heading,
                                        href=heading_url,
                                        className="vf-heading__link",
                                    ),
                                    className="vf-links__heading",
                                ),
                                html.Ul(
                                    [
                                        html.Li(
                                            html.A(
                                                label,
                                                href=href,
                                                className="vf-list__link",
                                            ),
                                            className="vf-list__item",
                                        )
                                        for label, href in links
                                    ],
                                    className="vf-links__list vf-list",
                                ),
                            ],
                            className="vf-links",
                        )
                        for heading, heading_url, links in footer_columns
                    ],
                    className="vf-footer__links-group vf-grid",
                ),
                html.P(
                    [
                        html.Span(
                            "EMBL-EBI, Wellcome Genome Campus, "
                            "Hinxton, Cambridgeshire, CB10 1SD, UK.",
                            className="vf-footer__legal-text",
                        ),
                        html.Span(
                            html.A(
                                "Tel: +44 (0)1223 49 44 44",
                                href="tel:00441223494444",
                                className="vf-footer__link",
                            ),
                            className="vf-footer__legal-text",
                        ),
                        html.Span(
                            html.A(
                                "Full contact details",
                                href="https://www.ebi.ac.uk/about/contact",
                                className="vf-footer__link",
                            ),
                            className="vf-footer__legal-text",
                        ),
                    ],
                    className="vf-footer__legal",
                ),
                html.P(
                    [
                        html.Span(
                            "Copyright © EMBL 2026",
                            className="vf-footer__legal-text",
                        ),
                        html.Span(
                            [
                                "EMBL-EBI is part of the ",
                                html.A(
                                    "European Molecular Biology Laboratory",
                                    href="https://www.embl.org",
                                    className="vf-footer__link",
                                ),
                            ],
                            className="vf-footer__legal-text",
                        ),
                        html.Span(
                            html.A(
                                "Terms of use",
                                href="https://www.ebi.ac.uk/about/terms-of-use",
                                className="vf-footer__link",
                            ),
                            className="vf-footer__legal-text",
                        ),
                    ],
                    className="vf-footer__legal",
                ),
            ],
            className="vf-footer__inner",
        ),
        className="vf-footer",
        **{"data-vf-google-analytics-region": "ebi-footer"},
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
