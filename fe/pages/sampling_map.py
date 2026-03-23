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



def altitude_to_range(alt_str):
    try:
        value = float(str(alt_str).replace("m", "").strip())
        if value < 0:
            return "Below 0 m"
        elif value <= 10:
            return "0-10 m"
        elif value <= 20:
            return "11-20 m"
        elif value <= 30:
            return "21-30 m"
        else:
            return "Above 30 m"
    except (ValueError, AttributeError):
        return "Not provided"

@callback(
    Output("sampling-map", "figure"),
    Input("sampling-map", "figure"),
)

def build_map(sampling_map):
    DATA["Altitude Range"] = DATA["altitude"].apply(altitude_to_range)
    map_fig = px.scatter_map(DATA, lat="lat", lon="lon", zoom=3, hover_name="id",
                             color="Altitude Range",
                             hover_data=["altitude"],
                             height=800,
                             category_orders={"Altitude Range": [
                                 "Below 0 m", "0-10 m", "11-20 m", "21-30 m", "Above 30 m", "Not provided"
                             ]})
    map_fig.update_layout(legend_title_text="<b>Altitude Range</b>")

    return map_fig


@callback(
    Output("datatable-paging", "data"),
    Output("datatable-paging", "page_count"),
    Output("datatable-paging", "page_current"),
    Input("sampling-map", "selectedData"),
    Input("sampling-map", "clickData"),
    Input('datatable-paging', "page_current"),
    Input('datatable-paging', "page_size")
)
def build_table(selected_data, click_data, page_current, page_size):
    if selected_data is None and click_data is None:
        return DATA.iloc[
               page_current * page_size:(page_current + 1) * page_size
               ].to_dict("records"), len(DATA.index) // page_size + 1, page_current
    else:
        selected_samples = []
        if selected_data is not None:
            selected_samples.extend(
                [item["hovertext"] for item in selected_data["points"]])
        if click_data is not None:
            selected_samples.extend(
                [item["hovertext"] for item in click_data["points"]])
        filtered_df = DATA[DATA["id"].isin(selected_samples)]
        return filtered_df.iloc[
               page_current * page_size:(page_current + 1) * page_size
               ].to_dict("records"), len(filtered_df.index) // page_size + 1, 0
