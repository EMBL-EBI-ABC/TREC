import requests
import dash
from dash import callback, html, Output, Input
import dash_bootstrap_components as dbc

dash.register_page(
    __name__,
    path_template="/data-portal/<sample_id>"
)


def layout(sample_id=None, **kwargs):
    return dbc.Container(
        [
            dbc.Row(
                dbc.Col(
                    dbc.Spinner(
                        dbc.Card(dbc.CardBody(id="card", key=sample_id))
                    ),
                    md={"width": 10, "offset": 1},
                    style={"marginTop": "15px"}
                )
            )
        ]
    )


@callback(
    Output("card", "children"),
    Input("card", "key"),
)
def build_data_portal_details_page(sample_id):
    response = requests.get(
        f"https://trec-be-868757013548.europe-west2.run.app/data_portal/{sample_id}"
    ).json()
    response = response["results"][0]
    children = [
        html.H3(response["biosampleId"], className="card-title", id="header")]
    return children