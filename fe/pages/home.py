import dash
import dash_bootstrap_components as dbc
from dash import html

dash.register_page(
    __name__,
    title="Home",
    path="/"
)

BACKGROUND_URL = (
    "https://www.embl.org/about/info/trec/wp-content/uploads/2022/02/"
    "TREC-web-banner.jpg")

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
                            html.H4(
                                "An expedition to study coastal ecosystems "
                                "and their response to the environment, from "
                                "molecules to communities",
                                style={"textAlign": "center"}),
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

layout = html.Div([
    banner,
    dbc.Container([
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.H4("Data Portal", className="card-title"),
                    html.P("Explore TREC sampling stations on an interactive "
                           "map, search and filter samples by environment, "
                           "organism, and analysis type.",
                           className="card-text"),
                ]),
                dbc.CardFooter(dbc.Button(
                    "Explore Data", color="primary", href="/data")),
            ]), md=4, style={"marginTop": "1em"}),
            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.H4("Data Availability", className="card-title"),
                    html.P("See which data types are available at each "
                           "station — metagenomics, metabolomics, imaging, "
                           "and more.",
                           className="card-text"),
                ]),
                dbc.CardFooter(dbc.Button(
                    "View Availability", color="primary",
                    href="/availability")),
            ]), md=4, style={"marginTop": "1em"}),
            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.H4("API Documentation", className="card-title"),
                    html.P("Access TREC data programmatically through our "
                           "REST API.",
                           className="card-text"),
                ]),
                dbc.CardFooter(dbc.Button(
                    "API Documentation", color="primary", href="/api")),
            ]), md=4, style={"marginTop": "1em"}),
        ], style={"marginBottom": "1em", "marginTop": "2em"}),
        dbc.Row(
            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.H4("About", className="card-title"),
                    html.P("Learn about the TREC expedition and its mission "
                           "to explore coastal ecosystems across Europe.",
                           className="card-text"),
                ]),
                dbc.CardFooter(dbc.Button(
                    "About", color="primary", href="/about")),
            ]), md=4),
            style={"marginBottom": "2em"},
        ),
    ]),
])
