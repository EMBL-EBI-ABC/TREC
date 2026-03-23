import dash
import dash_bootstrap_components as dbc
from dash import html, callback, Output, Input
import requests

dash.register_page(
    __name__,
    title="Home",
    path="/"
)

BACKGROUND_URL = (
    "https://www.embl.org/about/info/trec/wp-content/uploads/2022/02/TREC-web-banner.jpg")

banner = html.Div(
    dbc.Container(
        dbc.Row(
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.H1("TREC Data Portal", className="display-3",
                                    style={"textAlign": "center"}),
                            html.H2("Traversing European Coastlines",
                                    style={"textAlign": "center"}),
                            html.H4("An expedition to study coastal ecosystems and "
                                    "their response to the environment, from molecules "
                                    "to communities", style={"textAlign": "center"}),
                        ]
                    ),
                    color="light",
                ),
                style={"marginTop": "2em"},
            )
        )
    ),
    style={
        'backgroundImage': f'url({BACKGROUND_URL})',
        'backgroundPosition': 'center',
        'backgroundRepeat': 'no-repeat',
        'background-size': 'cover',
        'height': '20em',
    }
)


def stat_card(title, value_id):
    return dbc.Card(
        dbc.CardBody([
            html.H6(title, className="text-muted", style={"textAlign": "center"}),
            html.H2(dbc.Spinner(html.Span(id=value_id)), style={"textAlign": "center"}),
        ]),
        style={"marginBottom": "1em"}
    )


def data_portal_card():
    return dbc.Card(
        [
            dbc.CardBody([
                html.H4("Data", className="card-title"),
                html.P("Browse and filter all TREC samples by organism, protocol, location and more.",
                       className="card-text"),
            ]),
            dbc.CardFooter(dbc.Button("Data", color="primary", href="/data"), className="text-center"),
        ], className="h-100"
    )


def api_card():
    return dbc.Card(
        [
            dbc.CardBody([
                html.H4("API Documentation", className="card-title"),
                html.P("Programmatic access to TREC data via a REST API.",
                       className="card-text"),
            ]),
            dbc.CardFooter(dbc.Button("API Documentation", color="primary", href="/api"), className="text-center"),
        ], className="h-100"
    )


def about_card():
    return dbc.Card(
        [
            dbc.CardBody([
                html.H4("About", className="card-title"),
                html.P("Learn about the TREC expedition and its scientific goals.",
                       className="card-text"),
            ]),
            dbc.CardFooter(dbc.Button("About", color="primary", href="/about"), className="text-center"),
        ], className="h-100"
    )


def sampling_map_card():
    return dbc.Card(
        [
            dbc.CardBody([
                html.H4("Sampling Map", className="card-title"),
                html.P("Explore sampling locations along European coastlines.",
                       className="card-text"),
            ]),
            dbc.CardFooter(dbc.Button("Sampling Map", color="primary", href="/sampling-map"), className="text-center"),
        ], className="h-100"
    )

def expedition_timeline_card():
    return dbc.Card(
        [
            dbc.CardBody([
                html.H4("Expedition Timeline", className="card-title"),
                html.P("Watch the TREC expedition unfold along European coastlines month by month.",
                       className="card-text"),
            ]),
            dbc.CardFooter(dbc.Button("Expedition Timeline", color="primary",
                                      href="/expedition-timeline"), className="text-center"),
        ], className="h-100"
    )

layout = html.Div(
    [
        banner,
        dbc.Container(
            [
                # Stats row
                dbc.Row(
                    [
                        dbc.Col(stat_card("Total Samples", "stat-total"), md=3),
                        dbc.Col(stat_card("Countries Visited", "stat-countries"), md=3),
                        dbc.Col(stat_card("Protocols Used", "stat-protocols"), md=3),
                        dbc.Col(stat_card("Collection Years", "stat-years"), md=3),
                    ],
                    style={"marginTop": "2em"}
                ),
                # Cards row
                dbc.Row(
                    [
                        dbc.Col(data_portal_card(), md=4),
                        dbc.Col(sampling_map_card(), md=4),
                        dbc.Col(expedition_timeline_card(), md=4),
                        dbc.Col(api_card(), md=4),
                    ],
                    className="g-3",
                    style={"marginBottom": "1em", "marginTop": "1em"},
                ),
                dbc.Row(
                    dbc.Col(about_card(), md=4),
                    style={"marginBottom": "2em"},
                )
            ]
        )
    ]
)


@callback(
    Output("stat-total", "children"),
    Output("stat-countries", "children"),
    Output("stat-protocols", "children"),
    Output("stat-years", "children"),
    Input("stat-total", "id"),  # fires once on page load
)
def load_stats(_):
    try:
        response = requests.get(
            "http://localhost:8080/data_portal",
            params={"size": 1}
        ).json()

        total = f"{response['total']:,}"

        countries = len(response["aggregations"]["location"]["buckets"])

        protocols = len(response["aggregations"]["protocol"]["buckets"])

        years = sorted([
            b["key"] for b in response["aggregations"]["collection_year"]["buckets"]
        ])
        year_range = f"{years[0]} – {years[-1]}" if len(years) > 1 else years[0]

        return total, countries, protocols, year_range

    except Exception:
        return "—", "—", "—", "—"