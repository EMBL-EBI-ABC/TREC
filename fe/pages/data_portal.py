import dash
import requests
import dash_bootstrap_components as dbc
from dash import callback, Output, Input, State, html, dcc, dash_table, ALL, ctx
from urllib.parse import parse_qs, unquote
# from api_config import API_BASE_URL

# from dotenv import load_dotenv
# import os
# load_dotenv()
API_BASE_URL = "https://trec-be-test-868757013548.europe-west2.run.app"
# API_BASE_URL = "http://0.0.0.0:8080"

dash.register_page(
    __name__,
    path="/data",
    title="Data Portal",
)


def _badge_available():
    return ("<span class='trec-badge trec-badge-available'>"
            "<span class='trec-badge-glyph'>&#10003;</span>"
            "</span>")


def _muted_dash():
    return "<span class='trec-muted-dash'>&mdash;</span>"


def _badge_count(n):
    if not n:
        return _muted_dash()
    return f"<span class='trec-badge trec-badge-count'>{n}</span>"


def make_stats_banner():
    """Global stats cards — populated by callback on page load."""
    return dbc.Row(
        id="stats-banner-row",
        className="g-3 my-3",
    )


def make_filters_sidebar():
    """Filters sidebar — collapsible on mobile, always visible on desktop."""
    filter_content = [
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

        dcc.Store(id="protocol-all-options"),
        html.Label("Protocol", className="fw-bold small"),
        html.Label("Search protocols", htmlFor="protocol-search",
                   className="visually-hidden"),
        dbc.Input(
            id="protocol-search",
            placeholder="Search protocols...",
            type="text",
            size="sm",
            className="mb-2",
        ),
        dbc.Checklist(
            id="protocol-filter", className="small mb-3",
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
    ]

    return html.Div([
        dbc.Button(
            "Filters",
            id="filters-toggle",
            color="outline-secondary",
            size="sm",
            className="d-md-none mb-2 w-100",
            n_clicks=0,
        ),
        dbc.Collapse(filter_content, id="filters-collapse", is_open=True),
    ], className="p-3 border-end h-100")


layout = dbc.Container([
    # Stats banner
    make_stats_banner(),
    # Main layout: filters sidebar | map + station content
    dbc.Row([
        # Left: filters sidebar
        dbc.Col(
            make_filters_sidebar(),
            xs=12, md=2,
            className="pe-0",
        ),
        # Right: search + map + station detail
        dbc.Col([
            # Predictive-text search
            html.Label("Search countries, stations, or organisms",
                       htmlFor="predictive-search", className="visually-hidden"),
            dcc.Dropdown(
                id="predictive-search",
                options=[],
                value=None,
                placeholder="Search countries, stations, organisms, environments, analyses, protocols,...",
                searchable=True,
                clearable=True,
                optionHeight=44,
                className="trec-predictive-search mb-2 mt-2",
            ),
            dbc.RadioItems(
                id="colour-by",
                options=[
                    {"label": "All samples", "value": "none"},
                    {"label": "Environment type", "value": "environment_type"},
                    {"label": "Analysis type", "value": "analysis_type"},
                    {"label": "Has images", "value": "has_images"},
                ],
                value="none",
                inline=True,
                input_class_name="btn-check",
                label_class_name="btn btn-sm trec-chip",
                label_checked_class_name="active",
                class_name="btn-group mb-2",
            ),
            html.Div(id="active-filters-bar", className="d-flex flex-wrap gap-1 mb-2"),

            # Map
            dbc.Spinner(
                dcc.Graph(id="station-map", style={"height": "520px"}),
            ),
            # Station detail below map
            dbc.Spinner(
                html.Div(
                    id="station-panel",
                    children=html.P(
                        "Click a station on the map to view its samples",
                        className="text-muted text-center py-3",
                    ),
                ),
            ),
            # Samples table (always in DOM, hidden until station selected)
            dcc.Store(id="selected-station"),
            dcc.Store(id="table-sort-by", data=[]),
            dcc.Store(id="suggestions-data"),
            dcc.Location(id="url", refresh=False),
            dbc.Spinner(
                html.Div(id="samples-table-container"),
            ),
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
        ], xs=12, md=10),
    ], className="mt-2"),
])


# --- Callbacks ---

@callback(
    Output("stats-banner-row", "children"),
    Input("predictive-search", "id"),  # Trigger on page load
)
def load_stats(_):
    """Fetch global stats and render banner."""
    try:
        resp = requests.get(f"{API_BASE_URL}/stats").json()
    except Exception:
        return []
    stats = [
        ("Stations", resp.get("total_stations", 0), "bi-geo-alt-fill"),
        ("Countries", resp.get("total_countries", 0), "bi-globe-europe-africa"),
        ("Source Samples", resp.get("total_source_samples", 0), "bi-droplet-fill"),
        ("Total Samples", resp.get("total_samples", 0), "bi-collection-fill"),
    ]
    return [
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.I(className=f"bi {icon} text-success fs-5 d-block stat-icon"),
                    html.Div(f"{val:,}", className="stat-number"),
                    html.Div(label, className="text-uppercase text-muted small fw-semibold stat-label"),
                ], className="py-2 px-3"),
                className=(
                    "stat-card shadow-sm h-100 border-0 border-start "
                    "border-3 border-success"
                ),
            ),
            xs=6, md=3,
        )
        for label, val, icon in stats
    ]


def _suggestion_option(kind, type_label, name):
    """Build one dcc.Dropdown option with a rich label."""
    return {
        "label": html.Div(
            [
                html.Span(name, className="trec-suggest-name"),
                html.Span(type_label, className="trec-suggest-meta"),
            ],
            className="trec-suggest-option",
        ),
        "value": f"{kind}::{name}",
        "search": f"{name} {type_label}",
    }


# Cache of fully-built dcc.Dropdown options. Populated by load_suggestions
# on page load; read by filter_options on every keystroke. Per-worker, but
# read-only after construction so contention is a non-issue.
_SUGGEST_OPTIONS_CACHE = []


@callback(
    Output("suggestions-data", "data"),
    Input("predictive-search", "id"),  # Trigger once on page load
)
def load_suggestions(_):
    """Fetch unfiltered counts for the six named-value filters, build the
    full categorised options list once, and cache it."""
    global _SUGGEST_OPTIONS_CACHE

    countries, organisms, stations = [], [], []
    environments, analyses, protocols = [], [], []

    def _buckets(aggs, key):
        return [
            (b["key"], b["doc_count"])
            for b in aggs.get(key, {}).get("buckets", [])
            if b.get("key")
        ]

    try:
        agg_resp = requests.get(
            f"{API_BASE_URL}/data_portal", params={"size": 0}
        ).json()
        aggs = agg_resp.get("aggregations", {})
        countries = _buckets(aggs, "country")
        organisms = _buckets(aggs, "organism")
        environments = _buckets(aggs, "environment_type")
        analyses = _buckets(aggs, "analysis_type")
        protocols = _buckets(aggs, "protocol")
    except Exception:
        pass

    try:
        stations_resp = requests.get(f"{API_BASE_URL}/stations").json()
        stations = [
            (s["station_name"], s.get("sample_count", 0))
            for s in stations_resp.get("stations", [])
            if s.get("station_name")
        ]
    except Exception:
        pass

    for lst in (countries, stations, organisms,
                environments, analyses, protocols):
        lst.sort(key=lambda x: (-x[1], x[0].lower()))

    _SUGGEST_OPTIONS_CACHE = (
        [_suggestion_option("country", "country", n) for n, _ in countries]
        + [_suggestion_option("station", "station", n) for n, _ in stations]
        + [_suggestion_option("organism", "organism", n) for n, _ in organisms]
        + [_suggestion_option("environment", "environment", n)
           for n, _ in environments]
        + [_suggestion_option("analysis", "analysis", n) for n, _ in analyses]
        + [_suggestion_option("protocol", "protocol", n) for n, _ in protocols]
    )

    return {
        "countries": countries,
        "stations": stations,
        "organisms": organisms,
        "environments": environments,
        "analyses": analyses,
        "protocols": protocols,
    }


@callback(
    Output("predictive-search", "options"),
    Input("predictive-search", "search_value"),
)
def filter_options(search_value):
    """Show suggestions only when the user has typed something. dcc.Dropdown
    handles the actual substring filtering against each option's `search`
    field."""
    if not search_value:
        return []
    return _SUGGEST_OPTIONS_CACHE


@callback(
    Output("country-filter", "value", allow_duplicate=True),
    Output("organism-filter", "value", allow_duplicate=True),
    Output("env-type-filter", "value", allow_duplicate=True),
    Output("analysis-type-filter", "value", allow_duplicate=True),
    Output("protocol-filter", "value", allow_duplicate=True),
    Output("selected-station", "data", allow_duplicate=True),
    Output("predictive-search", "value"),
    Input("predictive-search", "value"),
    State("country-filter", "value"),
    State("organism-filter", "value"),
    State("env-type-filter", "value"),
    State("analysis-type-filter", "value"),
    State("protocol-filter", "value"),
    prevent_initial_call=True,
)
def apply_predictive_search(picked, country, organism, env_type,
                            analysis_type, protocol):
    """Translate a selected suggestion into the corresponding filter,
    then clear the dropdown."""
    if not picked or "::" not in picked:
        raise dash.exceptions.PreventUpdate

    kind, name = picked.split("::", 1)
    country = country or []
    organism = organism or []
    env_type = env_type or []
    analysis_type = analysis_type or []
    protocol = protocol or []
    NU = dash.no_update

    def _add(lst, val):
        return lst if val in lst else lst + [val]

    if kind == "country":
        return _add(country, name), NU, NU, NU, NU, NU, None
    if kind == "organism":
        return NU, _add(organism, name), NU, NU, NU, NU, None
    if kind == "environment":
        return NU, NU, _add(env_type, name), NU, NU, NU, None
    if kind == "analysis":
        return NU, NU, NU, _add(analysis_type, name), NU, NU, None
    if kind == "protocol":
        return NU, NU, NU, NU, _add(protocol, name), NU, None
    if kind == "station":
        return NU, NU, NU, NU, NU, name, None

    raise dash.exceptions.PreventUpdate


@callback(
    Output("station-map", "figure"),
    Output("env-type-filter", "options"),
    Output("organism-filter", "options"),
    Output("analysis-type-filter", "options"),
    Output("country-filter", "options"),
    Output("protocol-all-options", "data"),
    Input("predictive-search", "id"),
    Input("colour-by", "value"),
    Input("env-type-filter", "value"),
    Input("organism-filter", "value"),
    Input("analysis-type-filter", "value"),
    Input("country-filter", "value"),
    Input("protocol-filter", "value"),
    Input("source-filter", "value"),
    Input("linked-data-filter", "value"),
    Input("selected-station", "data"),
)
def load_map_and_filters(_, colour_by, env_type, organism, analysis_type,
                         country, protocol, source_filter, linked_data, selected_station):
    import plotly.graph_objects as go
    from collections import defaultdict

    try:
        stations_resp = requests.get(f"{API_BASE_URL}/stations").json()
    except Exception:
        stations_resp = {"stations": []}
    stations = stations_resp.get("stations", [])

    # find which stations have matching samples when filters are applied
    active_filters = {}
    if env_type:
        active_filters["environment_type"] = "|".join(env_type)
    if organism:
        active_filters["organism"] = "|".join(organism)
    if analysis_type:
        active_filters["analysis_type"] = "|".join(analysis_type)
    if country:
        active_filters["country"] = "|".join(country)
    if protocol:
        active_filters["protocol"] = "|".join(protocol)
    if source_filter == "source":
        active_filters["is_source_sample"] = True
    if linked_data:
        if "images" in linked_data:
            active_filters["has_images"] = "Yes"
        if "ena" in linked_data:
            active_filters["has_ena_data"] = "true"

    active_station_names = None
    if active_filters:
        try:
            # Fetch all matching samples to find which stations are represented
            filter_resp = requests.get(
                f"{API_BASE_URL}/data_portal",
                params={**active_filters, "size": 0}
            ).json()
            aggregations = filter_resp.get("aggregations")
            if aggregations:
                agg_stations = aggregations.get(
                    "station_name", {}).get("buckets", [])
                active_station_names = {b["key"] for b in agg_stations}
        except Exception:
            active_station_names = None


    # Colour logic
    COLOUR_MAPS = {
        "environment_type": {"marine": "#3498db", "soil": "#e67e22",
                              "aerosol": "#9b59b6"},
        "analysis_type": {"Metagenomics": "#2ecc71", "Metabolomics": "#e74c3c",
                          "Imaging": "#f39c12", "Ions": "#1abc9c"},
    }

    LABELS = {
        "none": {"#2c7a5c": "Stations", "#cccccc": "No matching samples"},
        "has_images": {"#f39c12": "Has images", "#95a5a6": "No images",
                       "#cccccc": "No matching samples"},
        "environment_type": {"#3498db": "Marine", "#e67e22": "Soil",
                             "#9b59b6": "Aerosol", "#95a5a6": "Unknown",
                             "#cccccc": "No matching samples"},
        "analysis_type": {"#2ecc71": "Metagenomics", "#e74c3c": "Metabolomics",
                          "#f39c12": "Imaging", "#1abc9c": "Ions",
                          "#95a5a6": "Unknown", "#cccccc": "No matching samples"},
    }

    def get_colour(station):
        # Grey out stations with no matching samples when filters are active
        if active_station_names is not None:
            if station["station_name"] not in active_station_names:
                return "#cccccc"
        if colour_by == "none":
            return "#2c7a5c"
        if colour_by == "has_images":
            return "#f39c12" if station.get("has_images") else "#95a5a6"
        if colour_by in COLOUR_MAPS:
            counts = station.get(
                "analysis_type_counts" if colour_by == "analysis_type"
                else "environment_type_counts", {}
            )
            if counts:
                dominant = max(counts, key=counts.get)
                return COLOUR_MAPS[colour_by].get(dominant, "#95a5a6")
        return "#95a5a6"

    lats = [s["lat"] for s in stations]
    lons = [s["lon"] for s in stations]
    names = [s["station_name"] for s in stations]
    colours = [get_colour(s) for s in stations]

    def get_dominant_label(station):
        if colour_by == "none" or colour_by == "has_images":
            return ""
        counts = station.get(
            "analysis_type_counts" if colour_by == "analysis_type"
            else "environment_type_counts", {}
        )
        if not counts:
            return ""
        dominant = max(counts, key=counts.get)
        pct = int(counts[dominant] / sum(counts.values()) * 100)
        return f"<br><b>Dominant: {dominant} ({pct}%)</b>"

    hover_texts = [
        f"{s['station_name']}<br>"
        f"{s['sample_count']} samples, {s['source_sample_count']} source<br>"
        f"Types: {', '.join(s['analysis_types'][:3])}"
        f"{get_dominant_label(s)}"
        for s in stations
    ]

    sizes = [max(8, min(20, s["sample_count"] // 10)) for s in stations]

    # Group stations by colour label for legend
    groups = defaultdict(list)
    for i, s in enumerate(stations):
        groups[colours[i]].append(i)

    fig = go.Figure()
    for colour, indices in groups.items():
        label = LABELS.get(colour_by, {}).get(colour, colour)
        fig.add_trace(go.Scattermap(
            lat=[lats[i] for i in indices],
            lon=[lons[i] for i in indices],
            mode="markers",
            marker=dict(size=[sizes[i] for i in indices],
                        color=colour, opacity=0.8),
            text=[names[i] for i in indices],
            hovertext=[hover_texts[i] for i in indices],
            hoverinfo="text",
            customdata=[names[i] for i in indices],
            name=label,
        ))

    # highlight selected station
    if selected_station:
        sel = next((s for s in stations
                    if s["station_name"] == selected_station), None)
        if sel:
            fig.add_trace(go.Scattermap(
                lat=[sel["lat"]],
                lon=[sel["lon"]],
                mode="markers",
                marker=dict(size=22, color="#FFD700", opacity=1.0),
                text=[sel["station_name"]],
                hovertext=[
                    f"{sel['station_name']}<br>"
                    f"{sel['sample_count']} samples, "
                    f"{sel['source_sample_count']} source<br>"
                    f"Types: {', '.join(sel['analysis_types'][:3])}"
                ],
                hoverinfo="text",
                name="Selected",
            ))

    fig.update_layout(
        map=dict(style="open-street-map",
                 center=dict(lat=43, lon=10), zoom=3.5),
        margin=dict(l=0, r=0, t=0, b=70),
        showlegend=colour_by != "none" or bool(selected_station),
        legend=dict(
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="#ccc",
            borderwidth=1,
            orientation="h",
            yanchor="top",
            y=-0.05,
            xanchor="center",
            x=0.5,
        ),
    )

    # Filter options
    try:
        agg_params = {"size": 0, **active_filters}
        if selected_station:
            agg_params["station_name"] = selected_station
        agg_resp = requests.get(f"{API_BASE_URL}/data_portal",
                                params=agg_params).json()
        aggs = agg_resp.get("aggregations", {})
    except Exception:
        aggs = {}

    def make_options(agg_key):
        if agg_key in aggs:
            return [
                {"label": f"{b['key']} ({b['doc_count']})", "value": b["key"]}
                for b in aggs[agg_key].get("buckets", [])
            ]
        return []

    return (
        fig,
        make_options("environment_type"),
        make_options("organism"),
        make_options("analysis_type"),
        make_options("country"),
        make_options("protocol"),
    )


@callback(
    Output("station-panel", "children", allow_duplicate=True),
    Output("samples-pagination", "max_value", allow_duplicate=True),
    Output("samples-pagination", "active_page", allow_duplicate=True),
    Output("samples-pagination", "style", allow_duplicate=True),
    Input("selected-station", "data"),
    prevent_initial_call=True,
)
def clear_station_panel(selected_station):
    if selected_station:
        raise dash.exceptions.PreventUpdate
    return (
        html.P("Click a station on the map to view its samples",
               className="text-muted text-center py-3"),
        1, 1, {"display": "none"},
    )

@callback(
    Output("station-panel", "children", allow_duplicate=True),
    Output("selected-station", "data", allow_duplicate=True),
    Output("samples-pagination", "max_value", allow_duplicate=True),
    Output("samples-pagination", "active_page", allow_duplicate=True),
    Output("samples-pagination", "style", allow_duplicate=True),
    Input("url", "search"),
    prevent_initial_call="initial_duplicate",
)
def initialize_from_url(search):
    hide_pagination = {"display": "none"}
    if not search:
        raise dash.exceptions.PreventUpdate
    params = parse_qs(search.lstrip("?"))
    station_name = params.get("station", [None])[0]
    if not station_name:
        raise dash.exceptions.PreventUpdate
    station_name = unquote(station_name)
    try:
        detail = requests.get(f"{API_BASE_URL}/stations/{station_name}").json()
    except Exception as e:
        return (dbc.Alert(f"Error loading station: {e}", color="danger",
                          className="mt-3"),
                None, 1, 1, hide_pagination)
    summary = dbc.Card(
        dbc.CardBody([
            html.H5(f"📍 {detail['station_name']}", className="mb-0"),
            html.Small(detail.get("country") or "", className="text-muted"),
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
        className="mt-3 mb-2 bg-success bg-opacity-10",
    )
    max_pages = max(1, (detail["source_sample_count"] + 9) // 10)
    return (summary, station_name, max_pages, 1,
            {"display": "flex", "justifyContent": "end", "marginTop": "8px"})


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
        return (dbc.Alert("Could not identify station",
                          color="warning", className="mt-3"),
                None, 1, 1, hide_pagination)

    try:
        detail = requests.get(
            f"{API_BASE_URL}/stations/{station_name}").json()
    except Exception as e:
        return (dbc.Alert(f"Error loading station: {e}",
                          color="danger", className="mt-3"),
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
        className="mt-3 mb-2 bg-success bg-opacity-10",
    )

    max_pages = max(1, (detail["source_sample_count"] + 9) // 10)

    return (summary, station_name, max_pages, 1,
            {"display": "flex", "justifyContent": "end", "marginTop": "8px"})


@callback(
    Output("samples-table-container", "children"),
    Output("samples-pagination", "max_value", allow_duplicate=True),
    Output("samples-pagination", "active_page", allow_duplicate=True),
    Output("samples-pagination", "style", allow_duplicate=True),
    Input("samples-pagination", "active_page"),
    Input("selected-station", "data"),
    Input("protocol-filter", "value"),
    Input("env-type-filter", "value"),
    Input("organism-filter", "value"),
    Input("analysis-type-filter", "value"),
    Input("country-filter", "value"),
    Input("source-filter", "value"),
    Input("linked-data-filter", "value"),
    Input("table-sort-by", "data"),
    prevent_initial_call=True,
)
def load_samples_page(page, station_name, protocol, env_type, organism,
                      analysis_type, country, source_filter, linked_data, sort_by):

    hide_pagination = {"display": "none"}
    show_pagination = {"display": "flex", "justifyContent": "end",
                       "marginTop": "8px"}

    active_filters = {}
    if protocol:
        active_filters["protocol"] = "|".join(protocol)
    if env_type:
        active_filters["environment_type"] = "|".join(env_type)
    if organism:
        active_filters["organism"] = "|".join(organism)
    if analysis_type:
        active_filters["analysis_type"] = "|".join(analysis_type)
    if country:
        active_filters["country"] = "|".join(country)
    if linked_data:
        if "images" in linked_data:
            active_filters["has_images"] = "Yes"
        if "ena" in linked_data:
            active_filters["has_ena_data"] = "true"

    has_filters = bool(active_filters)

    if not station_name and not has_filters:
        return None, 1, 1, hide_pagination

    if ctx.triggered_id != "samples-pagination":
        page = 1

    page = page or 1
    start = (page - 1) * 10

    sort_field = None
    sort_order = "asc"
    if sort_by and len(sort_by) > 0:
        sort_field = sort_by[0]["column_id"]
        sort_order = sort_by[0]["direction"]

    SORT_FIELD_MAP = {
        "biosampleId": "biosampleId.keyword",
        "organism": "organism.keyword",
        "station": "station_name",
    }
    sort_field = SORT_FIELD_MAP.get(sort_field, sort_field)

    params = {
        "size": 10,
        "start": start,
        **active_filters,
    }
    if sort_field:
        params["sort_field"] = sort_field
        params["sort_order"] = sort_order

    if station_name:
        params["station_name"] = station_name

    if source_filter == "source":
        params["is_source_sample"] = True

    try:
        resp = requests.get(
            f"{API_BASE_URL}/data_portal", params=params).json()
    except Exception as e:
        return dbc.Alert(f"Error: {e}", color="danger", className="mt-2"), 1, 1, hide_pagination

    results = resp.get("results", [])
    total = resp.get("total", 0)
    max_pages = max(1, (total + 9) // 10)

    if not results:
        return (dbc.Alert("No samples found for the selected filters.",
                          color="secondary", className="mt-2"),
                1, 1, hide_pagination)

    rows = []
    for s in results:
        rows.append({
            "biosampleId": f"[{s['biosampleId']}](/data-portal/"
                           f"{s['biosampleId']})",
            "organism": s.get("organism") or "",
            "depth": s.get("depth") or "",
            "collection_device": s.get("collection_device") or "",
            "station": s.get("station_name") or "",
            "has_images": _badge_available()
                          if s.get("has_images") == "Yes" else _muted_dash(),
            "has_ena": _badge_available()
                       if s.get("has_ena_data") else _muted_dash(),
        })

    table = html.Div([
        html.Small(f"{total:,} samples found", className="text-muted mb-2 d-block"),
        dash_table.DataTable(
            id="samples-table",
            columns=[
                {"name": "BioSample ID", "id": "biosampleId",
                 "presentation": "markdown"},
                {"name": "Organism", "id": "organism"},
                {"name": "Station", "id": "station"},
                {"name": "Depth", "id": "depth"},
                {"name": "Collection Device", "id": "collection_device"},
                {"name": "Images", "id": "has_images",
                 "presentation": "markdown"},
                {"name": "ENA", "id": "has_ena",
                 "presentation": "markdown"},
            ],
            data=rows,
            sort_action="custom",
            sort_mode="single",
            sort_by=sort_by or [],
            markdown_options={"html": True, "link_target": "_self"},
            style_table={"overflowX": "auto"},
            style_cell={
                "textAlign": "left",
                "fontSize": "13px",
                "padding": "10px 14px",
                "fontFamily": "inherit",
                "border": "none",
                "borderBottom": "1px solid #eef2f0",
            },
            style_header={
                "fontWeight": "600",
                "fontSize": "12px",
                "textTransform": "uppercase",
                "letterSpacing": "0.04em",
                "color": "#1d3a2e",
                "backgroundColor": "rgba(29, 94, 74, 0.06)",
                "borderBottom": "1px solid #d6e3df",
                "padding": "10px 14px 10px 18px",
            },
            style_data_conditional=[
                {"if": {"row_index": "odd"},
                 "backgroundColor": "rgba(29, 94, 74, 0.025)"},
                {"if": {"state": "active"},
                 "backgroundColor": "rgba(29, 94, 74, 0.10)",
                 "border": "1px solid rgba(29, 94, 74, 0.20)"},
                {"if": {"state": "selected"},
                 "backgroundColor": "rgba(29, 94, 74, 0.10)",
                 "border": "1px solid rgba(29, 94, 74, 0.20)"},
                {"if": {"column_id": ["has_images", "has_ena"]},
                 "textAlign": "center"},
            ],
            style_header_conditional=[
                {"if": {"column_id": ["has_images", "has_ena"]},
                 "textAlign": "center"},
            ],
            css=[
                {"selector": ".dash-spreadsheet-container",
                 "rule": "border-radius: 6px;"},
                {"selector": ".dash-cell p", "rule": "margin: 0;"},
                {"selector": ".dash-header p", "rule": "margin: 0;"},
                {"selector": ".dash-cell a",
                 "rule": "text-decoration: none; color: #1d5e4a; "
                         "border-bottom: 1px solid transparent; "
                         "transition: color .15s, border-color .15s;"},
                {"selector": ".dash-cell a:hover",
                 "rule": "color: #14463a; border-bottom-color: #1d5e4a;"},
                {"selector": ".dash-spreadsheet-inner tr:hover td.dash-cell",
                 "rule": "background-color: rgba(29, 94, 74, 0.08) "
                         "!important;"},
                {"selector": ".dash-header .column-header-name",
                 "rule": "vertical-align: middle; "
                         "display: inline-block;"},
            ],
        ),
    ])

    pagination_style = show_pagination if total > 10 else hide_pagination
    return table, max_pages, page, pagination_style


@callback(
    Output("table-sort-by", "data"),
    Input("samples-table", "sort_by"),
    State("table-sort-by", "data"),
    prevent_initial_call=True,
)
def capture_sort(sort_by, current_sort):
    new_sort = sort_by or []
    if new_sort == current_sort:
        raise dash.exceptions.PreventUpdate
    return new_sort


@callback(
    Output("protocol-filter", "options"),
    Input("protocol-search", "value"),
    Input("protocol-all-options", "data"),
)
def filter_protocol_options(search_value, all_options):
    if not all_options:
        return []
    if not search_value:
        return all_options
    search_lower = search_value.lower()
    return [
        opt for opt in all_options
        if search_lower in str(opt["label"]).lower()
    ]


@callback(
    Output("active-filters-bar", "children"),
    Input("env-type-filter", "value"),
    Input("organism-filter", "value"),
    Input("analysis-type-filter", "value"),
    Input("country-filter", "value"),
    Input("protocol-filter", "value"),
    Input("source-filter", "value"),
    Input("linked-data-filter", "value"),
    Input("selected-station", "data"),
)
def build_active_filters_bar(env_type, organism, analysis_type, country,
                              protocol, source_filter, linked_data, selected_station):
    badges = []

    if selected_station:
        badges.append(
            dbc.Badge(
                [f"📍 {selected_station} ✕"],
                id={"type": "filter-badge", "filter": "selected-station",
                    "value": selected_station},
                color="primary",
                className="me-1 mb-1 small",
                style={"cursor": "pointer"},
            )
        )

    filter_map = [
        ("env-type-filter", "Environment", env_type),
        ("organism-filter", "Organism", organism),
        ("analysis-type-filter", "Analysis", analysis_type),
        ("country-filter", "Country", country),
        ("protocol-filter", "Protocol", protocol),
        ("linked-data-filter", "Linked Data", linked_data),
    ]

    for filter_id, label, values in filter_map:
        if values:
            for val in values:
                badges.append(
                    dbc.Badge(
                        [f"{label}: {val} ✕"],
                        id={"type": "filter-badge", "filter": filter_id,
                            "value": val},
                        color="success",
                        className="me-1 mb-1 small",
                        style={"cursor": "pointer"},
                    )
                )

    if source_filter == "source":
        badges.append(
            dbc.Badge(
                ["Source only ✕"],
                id={"type": "filter-badge", "filter": "source-filter",
                    "value": "source"},
                color="secondary",
                className="me-1 mb-1 small",
                style={"cursor": "pointer"},
            )
        )

    return badges



@callback(
    Output("env-type-filter", "value"),
    Output("organism-filter", "value"),
    Output("analysis-type-filter", "value"),
    Output("country-filter", "value"),
    Output("protocol-filter", "value"),
    Output("source-filter", "value"),
    Output("linked-data-filter", "value"),
    Output("selected-station", "data", allow_duplicate=True),
    Output("url", "search", allow_duplicate=True),
    Input({"type": "filter-badge", "filter": ALL, "value": ALL}, "n_clicks"),
    State("env-type-filter", "value"),
    State("organism-filter", "value"),
    State("analysis-type-filter", "value"),
    State("country-filter", "value"),
    State("protocol-filter", "value"),
    State("source-filter", "value"),
    State("linked-data-filter", "value"),
    State("selected-station", "data"),
    prevent_initial_call=True,
)
def remove_filter_badge(n_clicks, env_type, organism, analysis_type,
                        country, protocol, source_filter, linked_data, selected_station):
    if not any(n_clicks):
        raise dash.exceptions.PreventUpdate

    triggered = ctx.triggered_id
    if not triggered:
        raise dash.exceptions.PreventUpdate

    filter_id = triggered["filter"]
    value = triggered["value"]
    clear_station_url = dash.no_update

    def remove(current, val):
        if not current:
            return []
        updated = [v for v in current if v != val]
        return updated

    if filter_id == "env-type-filter":
        env_type = remove(env_type, value)
    elif filter_id == "organism-filter":
        organism = remove(organism, value)
    elif filter_id == "analysis-type-filter":
        analysis_type = remove(analysis_type, value)
    elif filter_id == "country-filter":
        country = remove(country, value)
    elif filter_id == "protocol-filter":
        protocol = remove(protocol, value)
    elif filter_id == "source-filter":
        source_filter = "all"
    elif filter_id == "linked-data-filter":
        linked_data = remove(linked_data, value)
    elif filter_id == "selected-station":
        selected_station = None
        clear_station_url = ""

    return (
        env_type or [],
        organism or [],
        analysis_type or [],
        country or [],
        protocol or [],
        source_filter,
        linked_data or [],
        selected_station,
        clear_station_url,
    )


@callback(
    Output("filters-collapse", "is_open"),
    Input("filters-toggle", "n_clicks"),
    State("filters-collapse", "is_open"),
    prevent_initial_call=True,
)
def toggle_filters(n_clicks, is_open):
    return not is_open