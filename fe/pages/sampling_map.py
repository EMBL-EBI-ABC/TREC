import dash
import requests
from dash import dcc, callback, Output, Input, html
from itertools import chain
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd

dash.register_page(
    __name__,
    path_template="/sampling-map"
)


def layout(**kwargs):
    return dbc.Container([
        dbc.Row(
            dbc.Col(dbc.Spinner(dcc.Graph(id="sampling-map")), md=12, id="col-map")),
    ])


@callback(
    Output("sampling-map", "figure"),
    Input("sampling-map", "figure"),
)
def build_map(sampling_map):
    generators = []
    response = requests.get(
        "https://trec-be-868757013548.europe-west2.run.app/data_portal_analytics"
    ).json()
    while response["total"] > 0:
        generators.append(({"lon": item["lon"], "lat": item["lat"],
                            "id": item["biosampleId"], "organism": item["organism"],
                            "depth": item["depth"], "altitude": item["altitude"],
                            "location": item["location"]} for item in
                           response["results"] if "lon" in item and "lat" in item))
        response = requests.get(
            "https://trec-be-868757013548.europe-west2.run.app/data_portal_analytics",
            params={"search_after": response["search_after"]}).json()
    data = chain(*generators)
    df = pd.DataFrame(data)
    map_fig = px.scatter_map(df, lat="lat", lon="lon", zoom=3, hover_name="id",
                             height=800)
    map_fig.update_traces(cluster=dict(enabled=True))
    return map_fig