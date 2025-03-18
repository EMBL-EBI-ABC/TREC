import requests
import dash
import plotly.express as px
import pandas as pd
import dash_bootstrap_components as dbc
from dash import callback, html, Output, Input, dcc
from .data_portal import return_sample_id_button

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
                    style={"marginTop": "15px", "marginBottom": "15px"},
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
        html.H3(response["biosampleId"], className="card-title", id="header"),
        html.Hr()
    ]
    desc_list = html.Div(
        [
            html.H4("Metadata"),
            html.P(f"Organism: {response['organism']}"),
            html.P(["BioSample ID: ",
                    html.A(response["biosampleId"], style={"textDecoration": "none"},
                           href=f"https://www.ebi.ac.uk/biosamples/samples/"
                                f"{response['biosampleId']}")]),
            html.P(f"Depth: {response['depth']}"),
            html.P(f"Altitude: {response['altitude']}"),
            html.P(f"Collection Date: {response['collection_date']}"),
            html.P(f"Geographic Location (county and/or sea): {response['location']}"),
            *[html.P(f"{field['name']}: {field['value']}") for field in
              response["customFields"]]
        ]
    )
    children.append(desc_list)
    if "lat" in response and "lon" in response:
        df = pd.DataFrame([{"lat": response["lat"], "lon": response["lon"]}])
        fig = px.scatter_map(df, lat="lat", lon="lon", zoom=11)
        children.append(html.H4("Sampling Map"))
        children.append(dcc.Graph(figure=fig))
    if "relationships" in response and len(response["relationships"]) > 0:
        children.append(html.H4("Relationships"))
        table_header = [
            html.Thead(html.Tr([html.Th(value, className="text-center") for value in
                                ["Source", "Type", "Target"]]))]
        table_body = [
            html.Tbody(
                [html.Tr(
                    [html.Td(return_sample_id_button(row["source"]),
                             className="text-center"),
                     html.Td(row["type"], className="text-center"),
                     html.Td(return_sample_id_button(row["target"]),
                             className="text-center")])
                    for
                    row in response["relationships"]])
        ]
        table = dbc.Table(table_header + table_body, striped=True, bordered=True,
                          hover=True, responsive=True)
        children.append(table)
    return children
