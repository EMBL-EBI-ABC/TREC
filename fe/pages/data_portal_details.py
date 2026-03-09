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

BIA_API_URL = "https://www.ebi.ac.uk/biostudies/api/v1/files/S-BIAD2258"
PROXY_BASE = "http://localhost:8080/zarr-proxy"
VIEWER_BASE = "http://localhost:5173"


def build_zarr_proxy_url(file_entry: dict) -> str:
    """Construct the proxied Zarr URL for a BIA file entry."""
    location = file_entry["acquisition_location"]
    date = file_entry["acquisition_date"]
    name = file_entry["name"]
    tile = file_entry["tile"]
    folder = f"LSM900_{date}"
    ome_zarr = f"{name}_{tile}.ome.zarr"
    inner_zarr = f"{name}.zarr"
    return f"{PROXY_BASE}/{location}/{folder}/{ome_zarr}/{inner_zarr}"


def fetch_bia_images_for_sample(biosample_id: str) -> list:
    full_biosample_url = f"https://www.ebi.ac.uk/biosamples/samples/{biosample_id}"
    matches = []
    start = 0
    length = 100

    while True:
        try:
            resp = requests.get(
                BIA_API_URL,
                params={"start": start, "length": length},
                timeout=10
            )
            data = resp.json()
        except Exception:
            break

        entries = data.get("data", [])
        if not entries:
            break

        for entry in entries:
            if entry.get("BioSamples_ID") == full_biosample_url:
                if entry.get("type") == "file" and entry.get("name"):
                    matches.append(entry)

        if matches and not any(
            e.get("BioSamples_ID") == full_biosample_url for e in entries
        ):
            break

        start += length
        if start >= data.get("recordsTotal", 0):
            break

    return matches


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
            f"http://0.0.0.0:8080/data_portal/{sample_id}", timeout=10
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
        bia_files = fetch_bia_images_for_sample(biosample_id)
        if bia_files:
            displayed = bia_files[:5]

            tile_urls = {
                f"tile-{e['tile']}": build_zarr_proxy_url(e)
                for e in displayed
            }
            first_tab_id = f"tile-{displayed[0]['tile']}"
            first_viewer_url = f"{VIEWER_BASE}/?source={tile_urls[first_tab_id]}"

            tabs = [
                dbc.Tab(label=f"Tile {e['tile']}", tab_id=f"tile-{e['tile']}")
                for e in displayed
            ]

            children.append(html.H4("Microscopy Images", style={"marginTop": "20px"}))
            children.append(html.P(
                f"{len(bia_files)} tile(s) found in BioImage Archive (S-BIAD2258).",
                className="text-muted"
            ))
            children.append(dcc.Store(id="tile-url-store", data=tile_urls))
            children.append(
                dbc.Tabs(tabs, id="tile-tabs", active_tab=first_tab_id)
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

            if len(bia_files) > 5:
                children.append(html.P(
                    f"Showing 5 of {len(bia_files)} tiles.",
                    className="text-muted small"
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
    Input("tile-tabs", "active_tab"),
    State("tile-url-store", "data"),
    prevent_initial_call=True,
)
def switch_viewer_tab(active_tab, tile_urls):
    if not active_tab or not tile_urls:
        return html.Div("Select a tile to view.", className="text-muted")
    proxy_url = tile_urls.get(active_tab)
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