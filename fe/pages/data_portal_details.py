import requests
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

BIONGFF_VIEWER_URL = "https://biongff.github.io/biongff-viewer/"


def layout(sample_id=None, **kwargs):
    return dbc.Container(
        dbc.Spinner(html.Div(id="detail-content", key=sample_id)),
        className="mt-3",
    )


def make_breadcrumb(sample, station_name, parent_id):
    """Build breadcrumb: Station > Source Sample > This Sample."""
    items = []
    if station_name:
        items.append(html.Li(
            html.A(f"📍 {station_name}", href="/data",
                   className="text-decoration-none"),
            className="breadcrumb-item"))
    if parent_id:
        items.append(html.Li(
            html.A(parent_id, href=f"/data-portal/{parent_id}",
                   className="text-decoration-none"),
            className="breadcrumb-item"))
    items.append(html.Li(
        sample["biosampleId"], className="breadcrumb-item active"))
    return html.Nav(html.Ol(items, className="breadcrumb"))


def make_metadata_table(label, rows):
    """Build a labeled metadata table."""
    return html.Div([
        html.Small(label, className="text-muted d-block mb-2 fw-bold"),
        dbc.Table([
            html.Tbody([
                html.Tr([
                    html.Td(k, className="text-muted",
                            style={"width": "160px", "fontSize": "13px"}),
                    html.Td(v, style={"fontSize": "13px"}),
                ])
                for k, v in rows if v
            ])
        ], borderless=True, size="sm"),
    ], className="mb-3")


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
    Input("detail-content", "key"),
)
def build_detail_page(sample_id):
    if not sample_id:
        return html.P("No sample ID provided", className="text-danger")

    try:
        resp = requests.get(
            f"{API_BASE_URL}/data_portal/{sample_id}").json()
    except Exception as e:
        return html.P(f"Error: {e}", className="text-danger")

    if not resp.get("results"):
        return html.P("Sample not found", className="text-danger")

    sample = resp["results"][0]
    cf = sample.get("customFields") or []

    parent_id = sample.get("parent_sample_id")
    station_name = sample.get("station_name")
    is_source = sample.get("is_source_sample", False)

    # --- Breadcrumb ---
    breadcrumb = make_breadcrumb(sample, station_name, parent_id)

    # --- Sample identity ---
    badges = []
    if sample.get("analysis_type"):
        badges.append(dbc.Badge(sample["analysis_type"], color="success",
                                className="me-1"))
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
    derived_section = html.Div()
    derived_ids = sample.get("derived_sample_ids") or []
    if is_source and derived_ids:
        derived_rows = []
        for did in derived_ids:
            try:
                d_resp = requests.get(
                    f"{API_BASE_URL}/data_portal/{did}").json()
                if d_resp.get("results"):
                    d = d_resp["results"][0]
                    derived_rows.append(html.Tr([
                        html.Td(html.A(
                            did, href=f"/data-portal/{did}",
                            className="text-decoration-none text-success",
                        ), style={"fontSize": "13px"}),
                        html.Td(d.get("analysis_type") or "",
                                style={"fontSize": "13px"}),
                        html.Td(d.get("organism") or "",
                                style={"fontSize": "13px"}),
                    ]))
            except Exception:
                derived_rows.append(html.Tr([
                    html.Td(html.A(
                        did, href=f"/data-portal/{did}",
                        className="text-decoration-none text-success",
                    ), style={"fontSize": "13px"}),
                    html.Td(""), html.Td(""),
                ]))

        if derived_rows:
            derived_section = html.Div([
                html.Small("DERIVED SAMPLES",
                           className="text-muted d-block mb-2 fw-bold"),
                dbc.Table([
                    html.Thead(html.Tr([
                        html.Th("BioSample ID", style={"fontSize": "13px"}),
                        html.Th("Analysis Type", style={"fontSize": "13px"}),
                        html.Th("Organism", style={"fontSize": "13px"}),
                    ])),
                    html.Tbody(derived_rows),
                ], striped=True, hover=True, bordered=True, size="sm"),
            ], className="mb-3")

    # --- Source sample link (for derived samples) ---
    source_link = html.Div()
    if parent_id and not is_source:
        source_link = html.Div([
            html.Small("SOURCE SAMPLE",
                       className="text-muted d-block mb-2 fw-bold"),
            html.A(parent_id, href=f"/data-portal/{parent_id}",
                   className="text-decoration-none text-success"),
        ], className="mb-3")

    # --- Left column ---
    left_col = dbc.Col([identity, env_table, collection_table,
                        derived_section, source_link], md=7)

    # --- Right column: map + linked data ---

    # Mini map
    map_section = html.Div()
    if sample.get("lat") and sample.get("lon"):
        df = pd.DataFrame([{"lat": sample["lat"], "lon": sample["lon"]}])
        fig = px.scatter_map(df, lat="lat", lon="lon", zoom=9)
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=180)
        map_section = dcc.Graph(figure=fig, config={"scrollZoom": False},
                                style={"marginBottom": "16px"})

    # Linked data cards
    linked_cards = []

    # BioSamples link
    linked_cards.append(dbc.Card(dbc.CardBody(dbc.Row([
        dbc.Col([
            html.Div("BioSamples", className="fw-bold small"),
            html.Small("Original record at EBI", className="text-muted"),
        ]),
        dbc.Col(
            dbc.Button("View →", color="success", size="sm",
                       href=f"https://www.ebi.ac.uk/biosamples/samples/"
                            f"{sample['biosampleId']}",
                       external_link=True, target="_blank"),
            width="auto", className="d-flex align-items-center",
        ),
    ])), className="mb-2"))

    # BioImage Archive
    if sample.get("has_images") == "Yes" and sample.get("image_zarr_url"):
        viewer_url = (f"{BIONGFF_VIEWER_URL}?source="
                      f"{sample['image_zarr_url']}")
        linked_cards.append(dbc.Card(dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Div("🖼️ BioImage Archive", className="fw-bold small"),
                    html.Small("Microscopy images available",
                               className="text-muted"),
                ]),
                dbc.Col(
                    dbc.Button("Open viewer →", color="success", size="sm",
                               href=viewer_url, external_link=True,
                               target="_blank"),
                    width="auto", className="d-flex align-items-center",
                ),
            ]),
            html.Iframe(
                src=viewer_url,
                style={"width": "100%", "height": "160px", "border": "none",
                       "borderRadius": "4px", "marginTop": "10px",
                       "background": "#1a1a2e"},
            ),
        ]), className="mb-2", style={"background": "#fffdf0"}))
    elif sample.get("has_images") == "Yes":
        linked_cards.append(dbc.Card(dbc.CardBody(dbc.Row([
            dbc.Col([
                html.Div("🖼️ BioImage Archive", className="fw-bold small"),
                html.Small("Images available", className="text-muted"),
            ]),
        ])), className="mb-2"))

    # ENA
    ena_accession = sample.get("ena_accession")
    if sample.get("has_ena_data") and ena_accession:
        linked_cards.append(dbc.Card(dbc.CardBody(dbc.Row([
            dbc.Col([
                html.Div("ENA", className="fw-bold small"),
                html.Small("Sequence data", className="text-muted"),
            ]),
            dbc.Col(
                dbc.Button("View →", color="success", size="sm",
                           href=f"https://www.ebi.ac.uk/ena/browser/view/"
                                f"{ena_accession}",
                           external_link=True, target="_blank"),
                width="auto", className="d-flex align-items-center",
            ),
        ])), className="mb-2"))
    else:
        linked_cards.append(dbc.Card(dbc.CardBody(dbc.Row([
            dbc.Col([
                html.Div("ENA", className="fw-bold small"),
                html.Small("Sequence data (coming soon)",
                           className="text-muted"),
            ]),
            dbc.Col(
                dbc.Badge("Pending", color="secondary"),
                width="auto", className="d-flex align-items-center",
            ),
        ])), className="mb-2"))

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
            html.Div("Quality Control", className="fw-bold small mb-1"),
            *qc_content,
        ]), className="mb-2"))

    right_col = dbc.Col([
        html.Div([
            html.Small("LINKED DATA",
                       className="text-muted d-block mb-2 fw-bold"),
            map_section,
            *linked_cards,
        ]),
    ], md=5)

    return html.Div([breadcrumb, dbc.Row([left_col, right_col])])
