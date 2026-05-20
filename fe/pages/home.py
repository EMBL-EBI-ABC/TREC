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
        html.Div(className="blob", **{"aria-hidden": "true"}),
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
                        html.H4(title, className="card-title"),
                        html.P(description, className="card-text text-muted"),
                    ],
                    className="p-4",
                ),
                className="home-navcard",
            ),
            href=href,
            className="text-decoration-none text-reset",
        ),
        xs=12, sm=6, lg=3,
    )


def _nav_section():
    return dbc.Container(
        [
            html.H2("Explore the portal", className="mb-4"),
            dbc.Row(
                [
                    _nav_card(
                        "bi-map",
                        "Data Portal",
                        "Explore TREC sampling stations on an interactive map; "
                        "search and filter samples by environment, organism, "
                        "and analysis type.",
                        "/data",
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
                className="g-4 mb-5",
            ),
        ],
        className="trec-page",
    )


def layout():
    return html.Div([
        _hero(),
        _stats_section(),
        _nav_section(),
    ])
