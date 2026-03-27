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


def make_filters_panel():
    """Collapsible filters panel."""
    return dbc.Collapse(
        dbc.Card(
            dbc.CardBody(
                dbc.Row([
                    dbc.Col([
                        html.Label("Environment", className="fw-bold small"),
                        dbc.Checklist(id="env-type-filter", className="small"),
                    ], md=2),
                    dbc.Col([
                        html.Label("Organism", className="fw-bold small"),
                        dbc.Checklist(
                            id="organism-filter", className="small",
                            style={"maxHeight": "10em", "overflowY": "auto"}),
                    ], md=2),
                    dbc.Col([
                        html.Label("Analysis Type", className="fw-bold small"),
                        dbc.Checklist(
                            id="analysis-type-filter", className="small"),
                    ], md=2),
                    dbc.Col([
                        html.Label("Country", className="fw-bold small"),
                        dbc.Checklist(
                            id="country-filter", className="small",
                            style={"maxHeight": "10em", "overflowY": "auto"}),
                    ], md=2),
                    dbc.Col([
                        html.Label("Linked Data", className="fw-bold small"),
                        dbc.Checklist(
                            id="linked-data-filter",
                            options=[
                                {"label": "Has images", "value": "images"},
                                {"label": "Has sequences", "value": "ena"},
                            ],
                            className="small",
                        ),
                    ], md=2),
                    dbc.Col([
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
                    ], md=2),
                ]),
            ),
            className="mb-2",
        ),
        id="filters-collapse",
        is_open=False,
    )


layout = dbc.Container([
    # Stats banner
    make_stats_banner(),
    # Search + filters
    dbc.Row(
        dbc.Col([
            dbc.InputGroup([
                dbc.Input(
                    id="search-input",
                    placeholder="Search samples, organisms, locations...",
                    type="text", debounce=True,
                ),
                dbc.Button("Filters ▾", id="filters-toggle",
                           outline=True, color="secondary", size="sm"),
            ], className="mb-2"),
            make_filters_panel(),
        ]),
        className="mt-3",
    ),
    # Map + Station panel
    dbc.Spinner(
        dbc.Row([
            # Map column
            dbc.Col([
                dcc.Graph(id="station-map", style={"height": "500px"}),
            ], md=7),
            # Station panel column
            dbc.Col(
                html.Div(
                    id="station-panel",
                    children=[
                        html.Div(
                            html.P("Click a station on the map to see details",
                                   className="text-muted text-center mt-5"),
                        )
                    ],
                    style={"maxHeight": "500px", "overflowY": "auto"},
                ),
                md=5,
            ),
        ]),
    ),
])


# --- Callbacks ---

@callback(
    Output("filters-collapse", "is_open"),
    Input("filters-toggle", "n_clicks"),
    State("filters-collapse", "is_open"),
    prevent_initial_call=True,
)
def toggle_filters(n_clicks, is_open):
    return not is_open


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
    """When a station marker is clicked, fetch and display station detail."""
    if not click_data or "points" not in click_data:
        return html.P("Click a station on the map to see details",
                       className="text-muted text-center mt-5")

    station_name = click_data["points"][0].get("customdata")
    if not station_name:
        station_name = click_data["points"][0].get("text", "")
    if not station_name:
        return html.P("Could not identify station",
                       className="text-muted text-center mt-5")

    try:
        detail = requests.get(
            f"{API_BASE_URL}/stations/{station_name}").json()
    except Exception as e:
        return html.P(f"Error loading station: {e}",
                       className="text-danger text-center mt-3")

    # Station header
    header = html.Div([
        html.H5(f"📍 {detail['station_name']}", className="mb-1"),
        html.Small(
            f"{detail['lat']:.4f}°N, {detail['lon']:.4f}°E"
            + (f" · {detail['country']}" if detail.get("country") else ""),
            className="text-muted",
        ),
    ], className="p-3", style={"background": "#f0f7f4",
                                "borderBottom": "1px solid #e0e0e0"})

    # Summary counts
    counts = dbc.Row([
        dbc.Col(html.Div([
            html.Div(str(detail["source_sample_count"]),
                     className="fw-bold fs-4 text-success"),
            html.Small("Source samples", className="text-muted"),
        ], className="text-center p-2 bg-light rounded"), md=6),
        dbc.Col(html.Div([
            html.Div(str(detail["sample_count"]),
                     className="fw-bold fs-4 text-success"),
            html.Small("Total samples", className="text-muted"),
        ], className="text-center p-2 bg-light rounded"), md=6),
    ], className="g-2 p-3")

    # Available analysis types badges
    type_badges = html.Div([
        html.Small("AVAILABLE DATA", className="text-muted d-block mb-2"),
        html.Div([
            dbc.Badge(t, color="success", className="me-1 mb-1")
            for t in detail.get("analysis_types", [])
        ]),
    ], className="px-3 pb-3")

    # Organism breakdown
    org_list = html.Div([
        html.Small("ORGANISMS", className="text-muted d-block mb-2"),
        *[
            html.Div([
                html.Span(org, className="small"),
                html.Span(f"{count}", className="small text-muted float-end"),
            ], className="mb-1")
            for org, count in detail.get("organism_counts", {}).items()
        ],
    ], className="px-3 pb-3")

    # Source samples accordion
    source_items = []
    for src in detail.get("source_samples", []):
        derived = src.get("derived_samples", [])
        derived_list = html.Div([
            html.Div([
                html.A(
                    d["biosampleId"],
                    href=f"/data-portal/{d['biosampleId']}",
                    className="text-decoration-none text-success small",
                ),
                html.Span([
                    dbc.Badge(d.get("analysis_type") or "?",
                              color="info", className="ms-2",
                              style={"fontSize": "10px"}),
                    dbc.Badge("🖼️", color="warning", className="ms-1",
                              style={"fontSize": "10px"})
                    if d.get("has_images") == "Yes" else None,
                ]),
            ], className="d-flex justify-content-between align-items-center "
                         "py-1 border-bottom")
            for d in derived
        ]) if derived else html.Small("No derived samples",
                                       className="text-muted")

        subtitle = " · ".join(filter(None, [
            src.get("collection_device"),
            f"{src['depth']} depth" if src.get("depth") else None,
            src.get("organism"),
        ]))

        source_items.append(dbc.AccordionItem(
            html.Div([
                html.A("View sample details →",
                       href=f"/data-portal/{src['biosampleId']}",
                       className="text-decoration-none text-success small "
                                 "d-block mb-2"),
                derived_list,
            ]),
            title=html.Div([
                html.Span(src["biosampleId"], className="fw-bold small"),
                html.Br(),
                html.Small(subtitle, className="text-muted"),
            ]),
            item_id=src["biosampleId"],
        ))

    sources_section = html.Div([
        html.Small("SOURCE SAMPLES", className="text-muted d-block mb-2"),
        dbc.Accordion(source_items, flush=True, start_collapsed=True),
    ], className="px-3 pb-3") if source_items else html.Div()

    return html.Div([header, counts, type_badges, org_list, sources_section])
