import dash
import requests
import dash_bootstrap_components as dbc
from dash import callback, Output, Input, State, html, dcc, dash_table
# from api_config import API_BASE_URL

from dotenv import load_dotenv
import os
load_dotenv()
API_BASE_URL = "http://0.0.0.0:8080"

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
            html.Div(
                id="station-panel",
                children=html.P(
                    "Click a station on the map to view its samples",
                    className="text-muted text-center py-3",
                ),
            ),
            # Samples table (always in DOM, hidden until station selected)
            dcc.Store(id="selected-station"),
            html.Div(id="samples-table-container"),
            dbc.Pagination(
                id="samples-pagination",
                max_value=1,
                first_last=True,
                previous_next=True,
                fully_expanded=False,
                active_page=1,
                className="justify-content-end mt-2",
                style={"display": "none"},
            ),
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
    Output("selected-station", "data"),
    Output("samples-pagination", "max_value"),
    Output("samples-pagination", "active_page"),
    Output("samples-pagination", "style"),
    Input("station-map", "clickData"),
    prevent_initial_call=True,
)
def show_station_panel(click_data):
    """When a station marker is clicked, show summary + trigger table load."""
    hide_pagination = {"display": "none"}

    if not click_data or "points" not in click_data:
        return None, None, 1, 1, hide_pagination

    station_name = click_data["points"][0].get("customdata")
    if not station_name:
        station_name = click_data["points"][0].get("text", "")
    if not station_name:
        return (html.P("Could not identify station",
                        className="text-muted text-center mt-3"),
                None, 1, 1, hide_pagination)

    try:
        detail = requests.get(
            f"{API_BASE_URL}/stations/{station_name}").json()
    except Exception as e:
        return (html.P(f"Error loading station: {e}",
                        className="text-danger text-center mt-3"),
                None, 1, 1, hide_pagination)

    # --- Summary ---
    summary = dbc.Card(
        dbc.CardBody([
            html.H5(f"📍 {detail['station_name']}", className="mb-0"),
            html.Small(
                detail.get("country") or "",
                className="text-muted",
            ),
            html.Div([
                html.Span(str(detail["source_sample_count"]),
                          className="fw-bold text-success"),
                html.Small(" source", className="text-muted"),
                html.Span(" / ", className="text-muted mx-1"),
                html.Span(str(detail["sample_count"]),
                          className="fw-bold text-success"),
                html.Small(" total samples", className="text-muted me-3"),
                *[dbc.Badge(t, color="success", className="me-1")
                  for t in detail.get("analysis_types", [])],
            ], className="mt-2"),
        ]),
        className="mt-3 mb-2",
        style={"background": "#f0f7f4"},
    )

    max_pages = max(1, (detail["source_sample_count"] + 9) // 10)

    return (summary, station_name, max_pages, 1,
            {"display": "flex", "justifyContent": "end", "marginTop": "8px"})


@callback(
    Output("samples-table-container", "children"),
    Input("samples-pagination", "active_page"),
    Input("selected-station", "data"),
    prevent_initial_call=True,
)
def load_samples_page(page, station_name):
    """Fetch a page of source samples for the selected station."""
    if not station_name:
        return None

    page = page or 1
    start = (page - 1) * 10
    try:
        resp = requests.get(f"{API_BASE_URL}/data_portal", params={
            "station_name": station_name,
            "size": 10,
            "start": start,
            "is_source_sample": True,
        }).json()
    except Exception as e:
        return html.P(f"Error: {e}", className="text-danger")

    results = resp.get("results", [])
    if not results:
        return html.P("No samples found", className="text-muted")

    rows = []
    for s in results:
        n_derived = len(s.get("derived_sample_ids") or [])
        rows.append({
            "biosampleId": f"[{s['biosampleId']}](/data-portal/"
                           f"{s['biosampleId']})",
            "organism": s.get("organism") or "",
            "depth": s.get("depth") or "",
            "collection_device": s.get("collection_device") or "",
            "derived": str(n_derived) if n_derived else "",
        })

    return dash_table.DataTable(
        columns=[
            {"name": "BioSample ID", "id": "biosampleId",
             "presentation": "markdown"},
            {"name": "Organism", "id": "organism"},
            {"name": "Depth", "id": "depth"},
            {"name": "Collection Device", "id": "collection_device"},
            {"name": "Derived Samples", "id": "derived"},
        ],
        data=rows,
        style_cell={"textAlign": "left", "fontSize": "13px",
                     "padding": "6px 10px"},
        style_header={"fontWeight": "bold", "fontSize": "13px"},
        css=[{"selector": "p", "rule": "margin: 0"},
             {"selector": "a",
              "rule": "text-decoration: none; color: #2c7a5c"}],
    )
