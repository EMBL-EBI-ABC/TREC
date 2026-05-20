import dash
import dash_bootstrap_components as dbc
from dash import html

dash.register_page(
    __name__,
    title="API",
)


def iframe_layout():
    return html.Iframe(
        src="https://trec-be-868757013548.europe-west2.run.app/redoc",
        title="TREC API Documentation",
        style={
            "display": "block",
            "height": "calc(100vh - 220px)",
            "width": "100%",
            "border": "none",
            "overflow": "auto",
        }
    )


layout = dbc.Container(
    [
        html.Div(
            [
                html.H2("API"),
                html.P("Programmatic access to TREC data via our REST API.",
                       className="text-muted mb-3"),
            ],
            className="trec-page pb-0",
        ),
        iframe_layout(),
    ],
    fluid=True,
)
