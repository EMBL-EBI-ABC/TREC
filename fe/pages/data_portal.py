import dash
import requests
import dash_bootstrap_components as dbc
from dash import callback, Output, Input, State, html, dcc
from api_config import API_BASE_URL

dash.register_page(
    __name__,
    path="/data",
    title="Data Portal",
)


def make_stats_banner():
    """Global stats banner — populated by callback on page load."""
    return html.Div(
        dbc.Row(
            id="stats-banner-row",
            className="g-0 justify-content-center",
            style={"padding": "12px 24px"},
        ),
        style={
            "background": "linear-gradient(135deg, #2c7a5c, #3da87a)",
            "color": "white",
        },
    )


def make_filters_sidebar():
    """Always-visible filters sidebar on the left."""
    return html.Div([
        html.H6("Filters", className="fw-bold mb-3"),

        html.Label("Environment", className="fw-bold small"),
        dbc.Checklist(id="env-type-filter", className="small mb-3"),

        html.Label("Organism", className="fw-bold small"),
        dbc.Checklist(
            id="organism-filter", className="small mb-3",
            style={"maxHeight": "12em", "overflowY": "auto"}),

        html.Label("Analysis Type", className="fw-bold small"),
        dbc.Checklist(id="analysis-type-filter", className="small mb-3"),

        html.Label("Country", className="fw-bold small"),
        dbc.Checklist(
            id="country-filter", className="small mb-3",
            style={"maxHeight": "12em", "overflowY": "auto"}),

        html.Label("Linked Data", className="fw-bold small"),
        dbc.Checklist(
            id="linked-data-filter",
            options=[
                {"label": "Has images", "value": "images"},
                {"label": "Has sequences", "value": "ena"},
            ],
            className="small mb-3",
        ),

        html.Label("Sample Type", className="fw-bold small"),
        dbc.RadioItems(
            id="source-filter",
            options=[
                {"label": "All", "value": "all"},
                {"label": "Source only", "value": "source"},
            ],
            value="all",
            className="small",
        ),
    ], style={"padding": "15px", "borderRight": "1px solid #e0e0e0",
              "height": "100%"})


layout = dbc.Container([
    # Stats banner
    make_stats_banner(),
    # Main layout: filters sidebar | map + station content
    dbc.Row([
        # Left: filters sidebar
        dbc.Col(
            make_filters_sidebar(),
            md=2,
            style={"paddingRight": "0"},
        ),
        # Right: search + map + station detail
        dbc.Col([
            # Search bar
            dbc.Input(
                id="search-input",
                placeholder="Search samples, organisms, locations...",
                type="text", debounce=True,
                className="mb-2 mt-2",
            ),
            # Map
            dbc.Spinner(
                dcc.Graph(id="station-map", style={"height": "450px"}),
            ),
            # Station detail below map
            html.Div(id="station-panel"),
        ], md=10),
    ], className="mt-2"),
])


# --- Callbacks ---

@callback(
    Output("stats-banner-row", "children"),
    Input("search-input", "id"),  # Trigger on page load
)
def load_stats(_):
    """Fetch global stats and render banner."""
    try:
        resp = requests.get(f"{API_BASE_URL}/stats").json()
    except Exception:
        return []
    stats = [
        ("Stations", resp.get("total_stations", 0)),
        ("Countries", resp.get("total_countries", 0)),
        ("Source Samples", f"~{resp.get('total_source_samples', 0):,}"),
        ("Total Samples", f"~{resp.get('total_samples', 0):,}"),
    ]
    return [
        dbc.Col(
            html.Div([
                html.Div(str(val), style={"fontSize": "28px",
                                          "fontWeight": "bold"}),
                html.Div(label, style={"fontSize": "12px", "opacity": "0.85"}),
            ], className="text-center"),
            width="auto",
            className="px-4",
        )
        for label, val in stats
    ]


@callback(
    Output("station-map", "figure"),
    Output("env-type-filter", "options"),
    Output("organism-filter", "options"),
    Output("analysis-type-filter", "options"),
    Output("country-filter", "options"),
    Input("search-input", "id"),  # Trigger on page load
)
def load_map_and_filters(_):
    """Fetch stations and build map + filter options."""
    import plotly.graph_objects as go

    try:
        stations_resp = requests.get(f"{API_BASE_URL}/stations").json()
    except Exception:
        stations_resp = {"stations": []}
    stations = stations_resp.get("stations", [])

    # Build map
    lats = [s["lat"] for s in stations]
    lons = [s["lon"] for s in stations]
    names = [s["station_name"] for s in stations]
    hover_texts = [
        f"{s['station_name']}<br>"
        f"{s['sample_count']} samples, {s['source_sample_count']} source<br>"
        f"Types: {', '.join(s['analysis_types'][:3])}"
        for s in stations
    ]
    sizes = [max(8, min(20, s["sample_count"] // 10)) for s in stations]

    fig = go.Figure(go.Scattermap(
        lat=lats, lon=lons,
        mode="markers",
        marker=dict(size=sizes, color="#2c7a5c", opacity=0.8),
        text=names,
        hovertext=hover_texts,
        hoverinfo="text",
        customdata=names,
    ))
    fig.update_layout(
        map=dict(style="open-street-map",
                 center=dict(lat=43, lon=10), zoom=3.5),
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
    )

    # Build filter options from aggregations
    try:
        agg_resp = requests.get(f"{API_BASE_URL}/data_portal",
                                params={"size": 0}).json()
        aggs = agg_resp.get("aggregations", {})
    except Exception:
        aggs = {}

    def make_options(agg_key):
        if agg_key in aggs:
            return [
                {"label": f"{b['key']} ({b['doc_count']})",
                 "value": b["key"]}
                for b in aggs[agg_key].get("buckets", [])
            ]
        return []

    return (
        fig,
        make_options("environment_type"),
        make_options("organism"),
        make_options("analysis_type"),
        make_options("country"),
    )


@callback(
    Output("station-panel", "children"),
    Input("station-map", "clickData"),
    prevent_initial_call=True,
)
def show_station_panel(click_data):
    """When a station marker is clicked, show summary + samples table."""
    if not click_data or "points" not in click_data:
        return None

    station_name = click_data["points"][0].get("customdata")
    if not station_name:
        station_name = click_data["points"][0].get("text", "")
    if not station_name:
        return html.P("Could not identify station",
                       className="text-muted text-center mt-3")

    try:
        detail = requests.get(
            f"{API_BASE_URL}/stations/{station_name}").json()
    except Exception as e:
        return html.P(f"Error loading station: {e}",
                       className="text-danger text-center mt-3")

    # --- Summary row ---
    summary = dbc.Card(
        dbc.CardBody(
            dbc.Row([
                dbc.Col([
                    html.H5(f"📍 {detail['station_name']}", className="mb-0"),
                    html.Small(
                        f"{detail['lat']:.4f}°N, {detail['lon']:.4f}°E"
                        + (f" · {detail['country']}"
                           if detail.get("country") else ""),
                        className="text-muted",
                    ),
                ], md=4),
                dbc.Col([
                    html.Span(str(detail["source_sample_count"]),
                              className="fw-bold text-success fs-5"),
                    html.Small(" source", className="text-muted"),
                    html.Span(" / ", className="text-muted mx-1"),
                    html.Span(str(detail["sample_count"]),
                              className="fw-bold text-success fs-5"),
                    html.Small(" total samples", className="text-muted"),
                ], md=3, className="d-flex align-items-center"),
                dbc.Col([
                    html.Div([
                        dbc.Badge(t, color="success", className="me-1 mb-1")
                        for t in detail.get("analysis_types", [])
                    ]),
                ], md=3),
                dbc.Col([
                    html.Small("ORGANISMS", className="text-muted d-block"),
                    html.Small(
                        ", ".join(detail.get("organism_counts", {}).keys()),
                        style={"fontSize": "11px"},
                    ),
                ], md=2),
            ], className="align-items-center"),
        ),
        className="mt-3 mb-2",
        style={"background": "#f0f7f4"},
    )

    # --- Samples table ---
    # Collect all samples: source + their derived
    rows = []
    for src in detail.get("source_samples", []):
        rows.append({
            "biosampleId": src["biosampleId"],
            "type": "Source",
            "organism": src.get("organism") or "",
            "device": src.get("collection_device") or "",
            "depth": src.get("depth") or "",
        })
        for d in src.get("derived_samples", []):
            rows.append({
                "biosampleId": d["biosampleId"],
                "type": d.get("analysis_type") or "Derived",
                "organism": "",
                "device": "",
                "depth": "",
            })

    if rows:
        table_header = html.Thead(html.Tr([
            html.Th("BioSample ID"),
            html.Th("Type"),
            html.Th("Organism"),
            html.Th("Collection Device"),
            html.Th("Depth"),
        ]))
        table_body = html.Tbody([
            html.Tr([
                html.Td(html.A(
                    r["biosampleId"],
                    href=f"/data-portal/{r['biosampleId']}",
                    className="text-decoration-none text-success",
                )),
                html.Td(dbc.Badge(r["type"],
                                  color="secondary" if r["type"] == "Source"
                                  else "info",
                                  style={"fontSize": "11px"})),
                html.Td(r["organism"], className="small"),
                html.Td(r["device"], className="small"),
                html.Td(r["depth"], className="small"),
            ])
            for r in rows
        ])
        table = dbc.Table(
            [table_header, table_body],
            striped=True, hover=True, bordered=True, responsive=True,
            size="sm",
        )
    else:
        table = html.P("No samples found at this station",
                        className="text-muted")

    return html.Div([summary, table])
