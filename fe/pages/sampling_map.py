import dash
import os
from dash import dcc, callback, Output, Input, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd

dash.register_page(
    __name__,
    path_template="/sampling-map",
    title="Sampling Map",
)

DATA = pd.read_parquet(os.path.abspath("./") + "/pages" + "/sampling_map.parquet")


def layout(**kwargs):
    return dbc.Container([
        dbc.Row(
            dbc.Col(dbc.Spinner(dcc.Graph(id="sampling-map")), md=12, id="col-map")),
        dbc.Row(
            dbc.Col(dash_table.DataTable(
                id="datatable-paging",
                columns=[
                    {"name": "BioSample ID", "id": "links", "presentation": "markdown"},
                    {"name": "Organism", "id": "organism"},
                    {"name": "Depth", "id": "depth"},
                    {"name": "Altitude", "id": "altitude"},
                    {"name": "Geographic Location", "id": "location"}
                ],
                style_cell={"textAlign": "center"},
                css=[dict(selector="p", rule="margin: 0; text-align: center"),
                     dict(selector="a", rule="text-decoration: none")],
                page_current=0,
                page_size=10,
                page_action="custom",
                style_table={'overflowX': 'scroll'}
            ), md=12, id="col-table")
        )
    ])


@callback(
    Output("sampling-map", "figure"),
    Input("sampling-map", "figure"),
)
def build_map(sampling_map):
    map_fig = px.scatter_map(DATA, lat="lat", lon="lon", zoom=3, hover_name="id",
                             height=800)
    return map_fig


@callback(
    Output("datatable-paging", "data"),
    Output("datatable-paging", "page_count"),
    Input("sampling-map", "selectedData"),
    Input("sampling-map", "clickData"),
    Input('datatable-paging', "page_current"),
    Input('datatable-paging', "page_size")
)
def build_table(selected_data, click_data, page_current, page_size):
    if selected_data is None and click_data is None:
        return DATA.iloc[
               page_current * page_size:(page_current + 1) * page_size
               ].to_dict("records"), len(DATA.index) // page_size + 1
    else:
        selected_samples = []
        if selected_data is not None:
            selected_samples.extend(
                [item["hovertext"] for item in selected_data["points"]])
        if click_data is not None:
            selected_samples.extend(
                [item["hovertext"] for item in click_data["points"]])
        page_current = 0
        filtered_df = DATA[DATA["id"].isin(selected_samples)]
        return filtered_df.iloc[
               page_current * page_size:(page_current + 1) * page_size
               ].to_dict("records"), len(filtered_df.index) // page_size + 1
