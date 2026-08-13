import requests
from urllib.parse import quote
import dash
import plotly.express as px
import pandas as pd
import dash_bootstrap_components as dbc
from dash import callback, html, Output, Input, dcc
from api_config import API_BASE_URL

dash.register_page(
    __name__,
    path_template="/data-portal/<sample_id>",
    title="Sample Details",
)

# from dotenv import load_dotenv
import os
# load_dotenv()
# API_BASE_URL = "http://0.0.0.0:8080"


VIEWER_BASE = ("https://livingobjects.ebi.ac.uk/bioimaging-01-pub/"
               "bia-zarr-test/vizarr/index.html")
BIA_IMAGE_PAGE = "https://beta.bioimagearchive.org/bioimage-archive/image"

def layout(sample_id=None, **kwargs):
    return dbc.Container([
        dcc.Store(id="sample-id-store", data=sample_id),
        dbc.Spinner(html.Div(id="detail-content")),
    ], className="mt-3")


def make_breadcrumb(sample, station_name, parent_id):
    """Build breadcrumb: Station > Source Sample > This Sample."""
    items = []
    if station_name:
        items.append(html.Li(
            html.A([html.I(className="bi bi-geo-alt-fill me-1",
                           style={"color": "#D9714E"}),
                    station_name],
                   href="/data-portal",
                   className="text-decoration-none"),
            className="breadcrumb-item"))
    if parent_id:
        items.append(html.Li(
            html.A(parent_id, href=f"/data-portal/{parent_id}",
                   className="text-decoration-none"),
            className="breadcrumb-item"))
    items.append(html.Li(
        sample["biosampleId"], className="breadcrumb-item active",
        **{"aria-current": "page"}))
    return html.Nav(html.Ol(items, className="breadcrumb"),
                    **{"aria-label": "Sample navigation"})


def make_metadata_table(label, rows):
    """Build a labeled metadata table inside a card."""
    return html.Div([
        html.H6(label, className="text-muted mb-2"),
        dbc.Table([
            html.Tbody([
                html.Tr([
                    html.Td(k, className="text-muted small",
                            style={"width": "160px"}),
                    html.Td(v, className="small"),
                ])
                for k, v in rows if v
            ])
        ], borderless=True, size="sm", className="mb-0",
            style={"--bs-table-bg": "transparent"}),
    ], className="trec-card p-3 mb-3")


def get_field(custom_fields, name):
    """Extract a value from customFields by name."""
    if not custom_fields:
        return None
    for f in custom_fields:
        if f.get("name", "").lower() == name.lower():
            val = f.get("value", "").strip()
            if val and val.lower() not in ("not provided", "not applicable"):
                return val
    return None


@callback(
    Output("detail-content", "children"),
    Input("sample-id-store", "data"),
)
def build_detail_page(sample_id):
    if not sample_id:
        return dbc.Alert("No sample ID provided", color="danger")

    try:
        resp = requests.get(
            f"{API_BASE_URL}/data_portal/{sample_id}").json()
    except Exception as e:
        return dbc.Alert(f"Error: {e}", color="danger")

    if not resp.get("results"):
        return dbc.Alert("Sample not found", color="danger")

    sample = resp["results"][0]
    cf = sample.get("customFields") or []

    parent_id = sample.get("parent_sample_id")
    station_name = sample.get("station_name")
    is_source = sample.get("is_source_sample", False)
    # Don't treat self-referencing parent as a real parent
    if parent_id == sample.get("biosampleId"):
        parent_id = None
        is_source = True

    # --- Breadcrumb ---
    breadcrumb = make_breadcrumb(sample, station_name, parent_id)

    # --- Sample identity ---
    badges = []
    if sample.get("analysis_type"):
        badges.append(html.Span(sample["analysis_type"],
                                className="trec-badge trec-badge-available me-1"))
    protocol = get_field(cf, "protocol label")
    if protocol:
        badges.append(dbc.Badge(f"{protocol} protocol", color="info",
                                className="me-1"))
    if is_source:
        badges.append(dbc.Badge("Source sample", color="secondary",
                                className="me-1"))

    identity = html.Div([
        html.H4(sample["biosampleId"], className="mb-1"),
        html.Div(badges, className="mb-2"),
        html.Small([
            "Derived from ",
            html.A(parent_id, href=f"/data-portal/{parent_id}",
                   className="text-decoration-none text-success"),
        ], className="text-muted") if parent_id else None,
    ], className="mb-3")

    # --- Environmental context ---
    biome = sample.get("biome") or get_field(cf,
                                              "broad-scale environmental "
                                              "context")
    local_env = sample.get("local_environment") or get_field(
        cf, "local environmental context")
    medium = sample.get("environmental_medium") or get_field(
        cf, "environmental medium")
    size_lower = sample.get("size_fraction_lower")
    size_upper = sample.get("size_fraction_upper")
    size_str = None
    if size_lower is not None and size_upper is not None:
        size_str = f"{size_lower}–{size_upper} µm"
    elif size_lower is not None:
        size_str = f"≥{size_lower} µm"

    env_table = make_metadata_table("ENVIRONMENTAL CONTEXT", [
        ("Organism", sample.get("organism")),
        ("Biome", biome),
        ("Local environment", local_env),
        ("Medium", medium),
        ("Environment type", sample.get("environment_type")),
        ("Size fraction", size_str),
    ])

    # --- Collection details ---
    date_str = sample.get("collection_date")
    if date_str:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            date_str = dt.strftime("%d %B %Y, %H:%M UTC")
        except (ValueError, AttributeError):
            pass

    collection_table = make_metadata_table("COLLECTION", [
        ("Date", date_str),
        ("Location", f"{sample.get('lat', '')}°N, {sample.get('lon', '')}°E"
         if sample.get("lat") else None),
        ("Depth", sample.get("depth")),
        ("Altitude", sample.get("altitude")),
        ("Collection device", sample.get("collection_device")
         or get_field(cf, "collection device")),
        ("Platform", sample.get("sampling_platform")
         or get_field(cf, "sampling platform")),
    ])

    # --- Derived samples table (for source samples) ---
    # Query for samples that have this sample as their parent
    derived_section = html.Div()
    if is_source:
        try:
            d_resp = requests.get(f"{API_BASE_URL}/data_portal", params={
                "parent_sample_id": sample["biosampleId"],
                "size": 50,
            }).json()
            derived_results = d_resp.get("results", [])
            # Filter out self-references
            derived_results = [d for d in derived_results
                               if d.get("biosampleId") != sample["biosampleId"]]
        except Exception:
            derived_results = []

        if derived_results:
            derived_rows = [
                html.Tr([
                    html.Td(html.A(
                        d["biosampleId"],
                        href=f"/data-portal/{d['biosampleId']}",
                        className="text-decoration-none text-success",
                    ), className="small"),
                    html.Td(d.get("analysis_type") or "", className="small"),
                    html.Td(d.get("organism") or "", className="small"),
                ])
                for d in derived_results
            ]
            derived_section = html.Div([
                html.H5(f"Derived Samples ({len(derived_results)})",
                        className="fs-6 fw-semibold text-muted mb-2"),
                dbc.Table([
                    html.Thead(html.Tr([
                        html.Th("BioSample ID", className="small"),
                        html.Th("Analysis Type", className="small"),
                        html.Th("Organism", className="small"),
                    ])),
                    html.Tbody(derived_rows),
                ], striped=True, hover=True, bordered=True, size="sm",
                    className="mb-0"),
            ], className="trec-card p-3 mb-3")

    # --- Left column ---
    left_col = dbc.Col([identity, env_table, collection_table,
                        derived_section], md=7)

    # --- Right column: map + linked data ---

    # Mini map
    map_section = html.Div()
    if sample.get("lat") and sample.get("lon"):
        df = pd.DataFrame([{"lat": sample["lat"], "lon": sample["lon"]}])
        fig = px.scatter_map(df, lat="lat", lon="lon", zoom=9)
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=180)
        map_section = dcc.Graph(figure=fig, config={"scrollZoom": False},
                                className="mb-3")

    # Linked data cards
    linked_cards = []

    # BioSamples link
    linked_cards.append(dbc.Card(dbc.CardBody(dbc.Row([
        dbc.Col([
            html.H5("BioSamples", className="mb-0 fs-6"),
            html.Small("Original record at EBI", className="text-muted"),
        ]),
        dbc.Col(
            dbc.Button("View →", color="success", size="sm",
                       href=f"https://www.ebi.ac.uk/biosamples/samples/"
                            f"{sample['biosampleId']}",
                       external_link=True, target="_blank"),
            width="auto", className="d-flex align-items-center",
        ),
    ])), className="trec-card mb-2"))

    # BioImage Archive
    first_image = None
    if sample.get("images"):
        tiles = sorted(sample["images"], key=lambda x: int(x.get("tile") or 0))
        first_image = next((t for t in tiles if t.get("ome_zarr_uri")), None)

    if sample.get("has_images") == "Yes" and first_image:
        viewer_url = f"{VIEWER_BASE}?source={quote(first_image['ome_zarr_uri'], safe=':/')}"
        bia_page = (f"{BIA_IMAGE_PAGE}/{first_image['uuid']}"
                    if first_image.get("uuid") else None)
        viewer_buttons = [
            dbc.Button("Open viewer →", color="success", size="sm",
                       href=viewer_url, external_link=True, target="_blank"),
        ]
        if bia_page:
            viewer_buttons.append(
                dbc.Button("View on BioImage Archive →", color="link", size="sm",
                           href=bia_page, external_link=True, target="_blank",
                           className="ms-1"))
        linked_cards.append(dbc.Card(dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.H5("BioImage Archive", className="mb-0 fs-6"),
                    html.Small(f"{len(sample['images'])} microscopy image(s) available",
                               className="text-muted"),
                ]),
                dbc.Col(
                    viewer_buttons,
                    width="auto", className="d-flex align-items-center",
                ),
            ]),
            html.Div(
                [
                    html.Div("Imaging", className="text-uppercase small fw-bold text-muted mb-2"),
                    html.Iframe(
                        src=viewer_url,
                        title="Sample imaging viewer",
                        className="mt-2",
                        style={"width": "100%", "height": "250px", "border": "none",
                               "borderRadius": "4px", "background": "#1a1a2e"},
                    ),
                ],
                className="trec-card p-3 mb-3 mt-2",
            ),
        ]), className="trec-card mb-2"))
    elif sample.get("has_images") == "Yes":
        linked_cards.append(dbc.Card(dbc.CardBody(dbc.Row([
            dbc.Col([
                html.H5("BioImage Archive", className="mb-0 fs-6"),
                html.Small("Images available", className="text-muted"),
            ]),
        ])), className="trec-card mb-2"))

    # ENA
    ena_accession = sample.get("ena_accession")
    if sample.get("has_ena_data") and ena_accession:
        linked_cards.append(dbc.Card(dbc.CardBody(dbc.Row([
            dbc.Col([
                html.H5("ENA", className="mb-0 fs-6"),
                html.Small("Sequence data", className="text-muted"),
            ]),
            dbc.Col(
                dbc.Button("View →", color="success", size="sm",
                           href=f"https://www.ebi.ac.uk/ena/browser/view/"
                                f"{ena_accession}",
                           external_link=True, target="_blank"),
                width="auto", className="d-flex align-items-center",
            ),
        ])), className="trec-card mb-2"))
    else:
        linked_cards.append(dbc.Card(dbc.CardBody(dbc.Row([
            dbc.Col([
                html.H5("ENA", className="mb-0 fs-6"),
                html.Small("Sequence data (coming soon)",
                           className="text-muted"),
            ]),
            dbc.Col(
                html.Span("Pending", className="trec-badge trec-badge-count"),
                width="auto", className="d-flex align-items-center",
            ),
        ])), className="trec-card mb-2"))

    # QC control relationship
    control_id = sample.get("control_sample_id")
    controlled_ids = sample.get("controlled_sample_ids") or []
    if control_id or controlled_ids:
        qc_content = []
        if control_id:
            qc_content.append(html.Div([
                html.Small("Control: ", className="text-muted"),
                html.A(control_id, href=f"/data-portal/{control_id}",
                       className="text-decoration-none text-success small"),
            ]))
        if controlled_ids:
            qc_content.append(html.Div([
                html.Small("Is control of: ", className="text-muted"),
                *[html.A(cid, href=f"/data-portal/{cid}",
                         className="text-decoration-none text-success "
                                   "small me-1")
                  for cid in controlled_ids],
            ]))
        linked_cards.append(dbc.Card(dbc.CardBody([
            html.H5("Quality Control", className="mb-1 fs-6"),
            *qc_content,
        ]), className="trec-card mb-2"))

    right_col = dbc.Col([
        html.Div([
            html.H5("Linked Data", className="text-muted mb-2 fs-6"),
            map_section,
            *linked_cards,
        ]),
    ], md=5)

    return html.Div([breadcrumb, dbc.Row([left_col, right_col])])
