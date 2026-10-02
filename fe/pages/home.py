import dash
import dash_bootstrap_components as dbc
import requests
from dash import html, dcc

from api_config import API_BASE_URL

dash.register_page(
    __name__,
    title="Home",
    path="/"
)


def _fetch_stats():
    try:
        return requests.get(f"{API_BASE_URL}/stats", timeout=5).json()
    except Exception:
        return {}


def _fmt(val):
    if val is None:
        return "—"
    try:
        return f"{int(val):,}"
    except (TypeError, ValueError):
        return "—"


def _hero():
    return html.Div(
        [
            html.Picture(
                [
                    html.Source(
                        srcSet="/assets/trec-hero-mobile.webp",
                        media="(max-width: 767px)",
                    ),
                    html.Source(
                        srcSet="/assets/trec-hero-2048.webp",
                        media="(min-width: 1600px)",
                    ),
                    html.Img(
                        src="/assets/trec-hero-1920.webp",
                        alt="",
                        width="1920",
                        height="640",
                        className="home-hero-image",
                    ),
                ],
                className="home-hero-picture",
            ),

            html.Div(
                [
                    html.H1(
                        "TREC Data Portal"
                    ),
                    html.H2(
                        "Transversing European Coastlines"
                    ),
                    html.P(
                        "Explore biodiversity and molecular adaptation across "
                        "European coastal ecosystems — from molecules to communities.",
                        className="lead",
                    ),
                    html.Div(
                        [
                            dcc.Link(
                                "Explore the data",
                                href="/data-portal",
                                className="btn trec-btn-primary",
                            ),
                            dcc.Link(
                                "About TREC",
                                href="/about",
                                className="btn trec-btn-secondary",
                            ),
                        ],
                        className="mt-4 d-flex flex-wrap gap-3",
                    ),
                ],
                className="home-hero-inner",
            ),
        ],
        className="home-hero",
    )


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


def _nav_card(icon, title, description, href):
    return dbc.Col(
        html.A(
            dbc.Card(
                dbc.CardBody(
                    [
                        html.I(className=f"bi {icon} ico d-block"),
                        html.H3(title, className="card-title"),
                        html.P(description, className="card-text text-muted"),
                    ],
                    className="p-4",
                ),
                className="home-navcard",
            ),
            href=href,
            className="text-decoration-none text-reset home-navcard-link",
        ),
        xs=12, sm=6, lg=3,
    )


def _nav_section():
    return html.Div(dbc.Container(
        [
            html.H2("Explore the portal", className="mb-4"),
            dbc.Row(
                [
                    _nav_card(
                        "bi-map",
                        "Sample Metadata",
                        "Explore TREC sampling stations on an interactive map; "
                        "search and filter samples by environment, organism, "
                        "and analysis type.",
                        "/data-portal",
                    ),
                    _nav_card(
                        "bi-grid-3x3",
                        "Data Availability",
                        "See which data types are available at each station — "
                        "metagenomics, metabolomics, imaging, and more.",
                        "/availability",
                    ),
                    _nav_card(
                        "bi-code-slash",
                        "API Documentation",
                        "Access TREC data programmatically through our REST API.",
                        "/api",
                    ),
                    _nav_card(
                        "bi-info-circle",
                        "About",
                        "Learn about the TREC expedition and its mission to "
                        "explore coastal ecosystems across Europe.",
                        "/about",
                    ),
                ],
                className="g-4",
            ),
        ],
        className="trec-page",
    ),
    className="home-nav-section"
    )


def _about_section():
    return dbc.Container(
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H2("A scientific voyage to address environmental challenges"),
                        html.P(
                            "With TREC, we embark on a journey through European "
                            "coastlines to explore biodiversity and molecular "
                            "adaptability of microbial communities as well as "
                            "key selected organisms. We fouc on coastal habitats "
                            "as they are the richest in species biodiversity and "
                            "they also often present the highest levels of pollution.",
                        ),
                        html.P(
                            "By combining the expertise and infrastructure of EMBL "
                            "and multiple European partners, TREC aims to initiate "
                            "a new era of coastal ecosystems exploration. The goal "
                            "is timely and ambitious - to observe, model, and "
                            "understand the effects of changing environments on "
                            "on organisms and communities, at the cellular and "
                            "molecular levels.",
                        ),
                        html.P(
                            [
                                "TREC is a flagship project of ",
                                html.A(
                                    html.Strong("Planetary Biology"),
                                    href="https://www.embl.org/about/info/planetary-biology/",
                                    className="home-planetary-link",
                                ),
                                ", one of the transversal themes launched by EMBL's programme \"",
                                html.A(
                                    "Molecules to Ecosystems",
                                    href="https://www.embl.org/about/programme/",
                                ),
                                "\" 2022–2026.",
                            ]
                        ),
                    ],
                    md=8,
                ),
                dbc.Col(
                    html.Img(
                        src=(
                            "https://www.embl.org/about/info/trec/"
                            "wp-content/uploads/2023/02/"
                            "20230126_TREC_Tag_RGB-s.jpg"
                        ),
                        className="img-fluid home-about-logo",
                        alt="TREC expedition logo",
                    ),
                    md=4,
                ),
            ],
            className="align-items-center",
        ),
        className="trec-page home-about-section",
    )


def layout():
    return html.Div([
        _hero(),
        _stats_section(),
        _nav_section(),
        _about_section(),
    ])
