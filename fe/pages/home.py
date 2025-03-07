import dash
import dash_bootstrap_components as dbc
from dash import html, dcc
import plotly.express as px
import pandas as pd

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
                style={"marginTop": "15px"},
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


def data_portal_card():
    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.H4("Data Portal",
                            className="card-title"),
                    html.P("This is some card text",
                           className="card-text"),
                ]
            ),
            dbc.CardFooter(dbc.Button(
                "Data Portal",
                color="primary",
                href="#")),
        ]
    )


def api_card():
    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.H4("API Documentation",
                            className="card-title"),
                    html.P("This is some card text",
                           className="card-text"),
                ]
            ),
            dbc.CardFooter(dbc.Button(
                "API Documentation",
                color="primary",
                href="#")),
        ]
    )


def about_card():
    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.H4("About",
                            className="card-title"),
                    html.P("This is some card text",
                           className="card-text"),
                ]
            ),
            dbc.CardFooter(dbc.Button(
                "About",
                color="primary",
                href="#")),
        ]
    )


layout = html.Div(
    [
        banner,
        dbc.Container(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            data_portal_card(),
                            md=4,
                            style={"marginTop": "2em"}
                        ),
                        dbc.Col(
                            api_card(),
                            md=4,
                            style={"marginTop": "2em"}
                        ),
                        dbc.Col(
                            about_card(),
                            md=4,
                            style={"marginTop": "2em"},
                        ),
                    ],
                    style={"marginBottom": "2em"},
                )
            ]
        )
    ]
)
