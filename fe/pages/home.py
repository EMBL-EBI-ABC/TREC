import dash
import dash_bootstrap_components as dbc
import requests
from dash import html

from api_config import API_BASE_URL

dash.register_page(
    __name__,
    title="Home",
    path="/"
)

BACKGROUND_URL = (
    "https://www.embl.org/about/info/trec/wp-content/uploads/2022/02/"
    "TREC-web-banner.jpg")

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
    card = dbc.Card(
        dbc.CardBody(
            [
                html.H1(
                    "TREC Data Portal",
                    className="display-4 fw-bold mb-2",
                    style={"color": "#1d3a2e"},
                ),
                html.P(
                    "Traversing European Coastlines",
                    className="lead mb-2",
                ),
                html.P(
                    "Exploring coastal ecosystem biodiversity from "
                    "molecules to communities.",
                    className="text-muted mb-0 small",
                ),
            ],
            className="p-4 p-md-5 text-center",
        ),
        className="shadow rounded border-0",
        style={"backgroundColor": "rgba(255,255,255,0.95)"},
    )
    return html.Div(
        dbc.Container(
            dbc.Row(
                dbc.Col(card, xs=12, md=8, lg=6),
                className="justify-content-center w-100 g-0",
            ),
        ),
        style={
            "backgroundImage": f"url({BACKGROUND_URL})",
            "backgroundPosition": "center",
            "backgroundRepeat": "no-repeat",
            "backgroundSize": "cover",
            "height": "min(18em, 35vh)",
            "width": "100%",
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "center",
        },
    )


def _stat_card(label, value, icon):
    return dbc.Col(
        dbc.Card(
            dbc.CardBody(
                [
                    html.I(
                        className=(
                            f"bi {icon} text-success fs-4 d-block mb-1"
                        ),
                    ),
                    html.Div(
                        _fmt(value),
                        className="lh-1 mb-1",
                        style={
                            "fontSize": "1.75rem",
                            "fontWeight": 700,
                            "whiteSpace": "nowrap",
                        },
                    ),
                    html.Div(
                        label,
                        className=(
                            "text-uppercase text-muted small fw-semibold"
                        ),
                        style={"whiteSpace": "nowrap"},
                    ),
                ],
                className="py-2 px-3",
            ),
            className=(
                "shadow-sm border-0 border-start border-3 border-success"
            ),
            style={"height": "110px"},
        ),
        xs=6, md=4, lg=2,
    )


def _stats_section():
    stats_data = _fetch_stats()
    items = [
        ("Stations", stats_data.get("total_stations"), "bi-geo-alt-fill"),
        ("Countries", stats_data.get("total_countries"),
         "bi-globe-europe-africa"),
        ("Source Samples", stats_data.get("total_source_samples"),
         "bi-droplet-fill"),
        ("Total Samples", stats_data.get("total_samples"),
         "bi-collection-fill"),
        ("With Imaging", stats_data.get("total_with_images"),
         "bi-camera-fill"),
        ("With ENA Data", stats_data.get("total_with_ena"), "bi-dna"),
    ]
    return dbc.Container(
        [
            html.Div(
                [
                    html.H3(
                        "The scale of the TREC dataset",
                        className="text-center fw-bold mb-2",
                    ),
                ],
                className="mt-4",
            ),
            dbc.Row(
                [_stat_card(label, val, icon)
                 for label, val, icon in items],
                className="g-3 mb-4",
            ),
        ],
    )


def _nav_card(icon, title, description, href):
    return dbc.Col(
        html.A(
            dbc.Card(
                dbc.CardBody(
                    [
                        html.I(
                            className=(
                                f"bi {icon} text-success fs-1 d-block mb-3"
                            ),
                        ),
                        html.H4(title, className="card-title"),
                        html.P(description, className="card-text text-muted"),
                    ],
                    className="p-4",
                ),
                className="shadow-sm h-100 border-0",
                style={"cursor": "pointer"},
            ),
            href=href,
            className="text-decoration-none text-reset",
        ),
        xs=12, sm=6, lg=3,
    )


def _nav_section():
    return dbc.Container(
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
    )


def layout():
    return html.Div([
        _hero(),
        _stats_section(),
        _nav_section(),
    ])
