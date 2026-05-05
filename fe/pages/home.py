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
                            html.H1("TREC Data Portal",
                                    className="display-3 text-center"),
                            html.H2("Traversing European Coastlines",
                                    className="text-center"),
                            html.H4(
                                "An expedition to study coastal ecosystems "
                                "and their response to the environment, from "
                                "molecules to communities",
                                className="text-center"),
                        ]
                    ),
                    color="light",
                ),
                className="mt-4",
            )
        )
    ),
    style={
        'backgroundImage': f'url({BACKGROUND_URL})',
        'backgroundPosition': 'center',
        'backgroundRepeat': 'no-repeat',
        'backgroundSize': 'cover',
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
            ]), sm=6, md=4, className="mt-3"),
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
            ]), sm=6, md=4, className="mt-3"),
            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.H4("API Documentation", className="card-title"),
                    html.P("Access TREC data programmatically through our "
                           "REST API.",
                           className="card-text"),
                ]),
                dbc.CardFooter(dbc.Button(
                    "API Documentation", color="primary", href="/api")),
            ]), sm=6, md=4, className="mt-3"),
        ], className="mb-3 mt-4"),
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
            ]), sm=6, md=4),
            className="mb-4 justify-content-center",
        ),
    ]),
])
