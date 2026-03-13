import requests
import dash
import plotly.express as px
import pandas as pd
import dash_bootstrap_components as dbc
from dash import callback, html, Output, Input, dcc, State
from .data_portal import return_sample_id_button

dash.register_page(
    __name__,
    path_template="/data-portal/<sample_id>",
    title="Sample Details"
)

PROXY_BASE = "https://trec-be-test-868757013548.europe-west2.run.app/zarr-proxy"
VIEWER_BASE = "https://biongff-viewer-868757013548.europe-west2.run.app"



def build_zarr_proxy_url(file_entry: dict) -> str:
    location = file_entry["acquisition_location"]
    date = file_entry["acquisition_date"]
    name = file_entry["name"]
    tile = file_entry["tile"]
    folder = f"LSM900_{date}"
    ome_zarr = f"{name}_{tile}.ome.zarr"
    inner_zarr = f"{name}.zarr"
    url = f"{PROXY_BASE}/{location}/{folder}/{ome_zarr}/{inner_zarr}"
    print(f"Generated URL: {url}")  # add this
    return url



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
    try:
        api_response = requests.get(
            f"https://trec-be-test-868757013548.europe-west2.run.app/data_portal/{sample_id}", timeout=10
        ).json()
        results = api_response.get("results", [])
        if not results:
            return [html.P(f"No data found for sample ID: {sample_id}", className="text-muted")]
        response = results[0]
    except Exception as e:
        return [html.P(f"Error loading sample data: {str(e)}", className="text-danger")]

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
                    for row in response["relationships"]])
        ]
        table = dbc.Table(table_header + table_body, striped=True, bordered=True,
                          hover=True, responsive=True)
        children.append(table)

    # --- microscopy images section ---
    biosample_id = response.get("biosampleId")
    if biosample_id:
        bia_files = response.get("images") or []
        if bia_files:
            displayed = bia_files

            tile_urls = {
                f"tile-{e['tile']}": build_zarr_proxy_url(e)
                for e in displayed
            }
            first_tile_id = f"tile-{displayed[0]['tile']}"
            first_viewer_url = f"{VIEWER_BASE}/?source={tile_urls[first_tile_id]}"

            children.append(html.H4("Microscopy Images", style={"marginTop": "20px"}))
            children.append(html.P(
                f"{len(bia_files)} tile(s) found in BioImage Archive (S-BIAD2258).",
                className="text-muted"
            ))
            children.append(dcc.Store(id="tile-url-store", data=tile_urls))
            children.append(
                dcc.Dropdown(
                    id="tile-tabs",
                    options=[
                        {"label": f"Tile {e['tile']}", "value": f"tile-{e['tile']}"}
                        for e in displayed
                    ],
                    value=first_tile_id,
                    clearable=False,
                    style={"marginBottom": "10px"}
                )
            )
            children.append(html.Div(
                html.Iframe(
                    src=first_viewer_url,
                    style={
                        "width": "100%",
                        "height": "600px",
                        "border": "none",
                        "borderRadius": "4px",
                    }
                ),
                id="viewer-container"
            ))
        else:
            children.append(html.Div(
                "No microscopy images found for this sample in BioImage Archive.",
                className="text-muted",
                style={"marginTop": "20px"}
            ))

    return children


@callback(
    Output("viewer-container", "children"),
    Input("tile-tabs", "value"),
    State("tile-url-store", "data"),
    prevent_initial_call=True,
)
def switch_viewer_tile(selected_tile, tile_urls):
    if not selected_tile or not tile_urls:
        return html.Div("Select a tile to view.", className="text-muted")
    proxy_url = tile_urls.get(selected_tile)
    if not proxy_url:
        return html.Div("Image not available.", className="text-muted")
    viewer_url = f"{VIEWER_BASE}/?source={proxy_url}"
    return html.Iframe(
        src=viewer_url,
        style={
            "width": "100%",
            "height": "600px",
            "border": "none",
            "borderRadius": "4px",
        }
    )