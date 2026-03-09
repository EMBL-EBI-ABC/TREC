import requests
import dash
import plotly.express as px
import pandas as pd
import dash_bootstrap_components as dbc
from dash import callback, html, Output, Input, dcc
from .data_portal import return_sample_id_button

dash.register_page(
    __name__,
    path_template="/data-portal/<sample_id>",
    title="Sample Details"
)

BIA_API_URL = "https://www.ebi.ac.uk/biostudies/api/v1/files/S-BIAD2258"
S3_BASE = "https://s3.embl.de/live-confocal-trec-super-plankton"
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

    # --- microscopy images section ---
    biosample_id = response.get("biosampleId")
    if biosample_id:
        bia_files = fetch_bia_images_for_sample(biosample_id)
        if bia_files:
            children.append(html.H4("Microscopy Images", style={"marginTop": "20px"}))
            children.append(html.P(
                f"{len(bia_files)} tile(s) found in BioImage Archive (S-BIAD2258).",
                className="text-muted"
            ))

            # tab per tile (cap at 5 to avoid overwhelming the page)
            displayed = bia_files[:5]
            tabs = []
            for entry in displayed:
                tile = entry.get("tile", "?")
                proxy_url = build_zarr_proxy_url(entry)
                viewer_url = f"{VIEWER_BASE}/?source={proxy_url}"
                tab = dbc.Tab(
                    html.Iframe(
                        src=viewer_url,
                        style={
                            "width": "100%",
                            "height": "600px",
                            "border": "none",
                            "borderRadius": "4px",
                        }
                    ),
                    label=f"Tile {tile}",
                    tab_id=f"tile-{tile}",
                )
                tabs.append(tab)

            children.append(
                dbc.Tabs(tabs, active_tab=f"tile-{displayed[0].get('tile', '0')}")
            )

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