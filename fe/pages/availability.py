import dash
import requests
import dash_bootstrap_components as dbc
from dash import callback, Output, Input, State, html, dcc, ALL, ctx
from urllib.parse import quote
from api_config import API_BASE_URL

dash.register_page(
    __name__,
    path="/availability",
    title="Data Availability",
)

ANALYSIS_TYPES = ["Metagenomics", "Metabolomics", "Imaging", "Ions"]
PAGE_SIZE = 10

def available_cell():
    return html.Td(
        html.Span(
            html.Span("✓", className="trec-badge-glyph"),
            className="trec-badge trec-badge-available",
        ),
        className="text-center",
    )


def unavailable_cell():
    return html.Td(
        html.Span("—", className="text-muted small trec-muted-dash"),
        className="text-center",
    )


def _sort_arrow(col_id, sort_state):
    """Two stacked Bootstrap-Icon carets (matches the fa-sort look
    used internally by Dash DataTable on the samples table)."""
    state = sort_state or {}
    direction = (state.get("direction")
                 if state.get("column") == col_id else None)
    up_cls = "trec-sort-caret bi bi-caret-up-fill"
    down_cls = "trec-sort-caret bi bi-caret-down-fill"
    if direction == "asc":
        up_cls += " active"
    elif direction == "desc":
        down_cls += " active"
    return html.Span([
        html.I(className=up_cls),
        html.I(className=down_cls),
    ], className="trec-sort-arrow")


def _sortable_th(label, col_id, sort_state, extra_class=""):
    cls = ("trec-sortable " + extra_class).strip()
    return html.Th(
        html.Span([
            _sort_arrow(col_id, sort_state),
            html.Span(label, className="trec-sort-label"),
        ], className="trec-sort-trigger"),
        id={"type": "availability-sort-header", "column": col_id},
        scope="col",
        className=cls,
        n_clicks=0,
    )


layout = dbc.Container([
    html.H3("Data Availability Across Stations", className="mt-3 mb-1"),
    html.P("Which data types are available at each sampling station",
           className="text-muted mb-3"),
    dcc.Store(id="availability-sort", data={}),
    html.Label("Search stations", htmlFor="availability-search",
               className="visually-hidden"),
    dbc.Input(
        id="availability-search",
        placeholder="Search stations...",
        type="text",
        className="mb-3",
    ),
    dbc.Spinner(html.Div(id="availability-table")),
    dbc.Row([
        dbc.Col([
            html.Div([
                html.Span(
                    html.Span("✓", className="trec-badge-glyph"),
                    className="trec-badge trec-badge-available",
                ),
                html.Span("Available", className="small text-muted"),
            ], className="d-flex align-items-center",
                style={"gap": "0.45rem"}),
            html.Div([
                html.Span("—", className="text-muted"),
                html.Span("Not available", className="small text-muted"),
            ], className="d-flex align-items-center",
                style={"gap": "0.45rem"}),
        ], className="d-flex align-items-center",
            style={"gap": "1.75rem"}),
        dbc.Col(
            dbc.Pagination(
                id="availability-pagination",
                max_value=1,
                first_last=True,
                previous_next=True,
                fully_expanded=False,
                active_page=1,
                className="justify-content-end mb-0",
            ),
        ),
    ], className="mt-2 mb-3"),
], className="trec-page")


@callback(
    Output("availability-table", "children"),
    Output("availability-pagination", "max_value"),
    Output("availability-pagination", "active_page"),
    Input("availability-search", "value"),
    Input("availability-pagination", "active_page"),
    Input("availability-sort", "data"),
)
def build_matrix(search_value, page, sort_state):
    try:
        resp = requests.get(f"{API_BASE_URL}/stations").json()
    except Exception as e:
        return dbc.Alert(f"Error loading stations: {e}",
                         color="danger", className="mt-2"), 1, 1

    stations = resp.get("stations", [])
    if not stations:
        return dbc.Alert("No stations found",
                         color="secondary", className="mt-2"), 1, 1

    # Filter by search
    if search_value:
        q = search_value.lower()
        stations = [s for s in stations
                    if q in s["station_name"].lower()
                    or q in (s.get("country") or "").lower()]

    if not stations:
        return dbc.Alert("No stations match your search",
                         color="secondary", className="mt-2"), 1, 1

    # Sort: user-driven if set, else default (country, then station)
    if sort_state and sort_state.get("column"):
        col = sort_state["column"]
        reverse = sort_state.get("direction") == "desc"
        if col == "station":
            stations.sort(key=lambda s: s["station_name"].lower(),
                          reverse=reverse)
        elif col == "country":
            # Stable secondary sort by station name preserved within
            # each country block when toggling country direction.
            stations.sort(key=lambda s: s["station_name"].lower())
            stations.sort(key=lambda s: (s.get("country") or "").lower(),
                          reverse=reverse)
        elif col == "samples":
            stations.sort(key=lambda s: s.get("sample_count", 0),
                          reverse=reverse)
    else:
        stations.sort(key=lambda s: ((s.get("country") or "").lower(),
                                     s["station_name"].lower()))

    # Pagination
    total_pages = max(1, (len(stations) + PAGE_SIZE - 1) // PAGE_SIZE)
    # Reset to page 1 when search changes
    if dash.callback_context.triggered_id == "availability-search":
        page = 1
    page = min(page or 1, total_pages)
    start = (page - 1) * PAGE_SIZE
    page_stations = stations[start:start + PAGE_SIZE]

    # Build table
    header = html.Thead(html.Tr([
        _sortable_th("Station", "station", sort_state,
                     extra_class="text-start"),
        _sortable_th("Country", "country", sort_state,
                     extra_class="text-start"),
        _sortable_th("Samples", "samples", sort_state,
                     extra_class="text-center"),
        *[html.Th(at, className="text-center small", scope="col")
          for at in ANALYSIS_TYPES],
        html.Th("ENA", className="text-center small", scope="col"),
        html.Th("Images", className="text-center small", scope="col"),
    ]))

    rows = []
    for station in page_stations:
        available_types = set(station.get("analysis_types", []))
        cells = [
            html.Td(
                html.A(station["station_name"],
                       href=f"/data-portal?station={quote(station['station_name'])}"),
                className="small",
            ),
            html.Td(station.get("country") or "", className="small"),
            html.Td(str(station.get("sample_count", 0)),
                    className="text-center small"),
        ]
        for at in ANALYSIS_TYPES:
            cells.append(
                available_cell() if at in available_types
                else unavailable_cell())
        cells.append(
            available_cell() if station.get("has_ena_data")
            else unavailable_cell())
        cells.append(
            available_cell() if station.get("has_images")
            else unavailable_cell())
        rows.append(html.Tr(cells))

    table = dbc.Table(
        [header, html.Tbody(rows)],
        striped=True, hover=True, responsive=True,
        className="trec-table",
    )

    return table, total_pages, page


@callback(
    Output("availability-sort", "data"),
    Output("availability-pagination", "active_page",
           allow_duplicate=True),
    Input({"type": "availability-sort-header", "column": ALL}, "n_clicks"),
    State("availability-sort", "data"),
    prevent_initial_call=True,
)
def update_sort(_n_clicks_list, current):
    triggered = ctx.triggered_id
    if not triggered:
        raise dash.exceptions.PreventUpdate
    triggered_value = ctx.triggered[0].get("value") if ctx.triggered else None
    # Skip when headers re-mount on table rebuild (n_clicks fires None/0).
    if not triggered_value:
        raise dash.exceptions.PreventUpdate
    col = triggered["column"]
    cur = current or {}
    if cur.get("column") != col:
        return {"column": col, "direction": "asc"}, 1
    if cur.get("direction") == "asc":
        return {"column": col, "direction": "desc"}, 1
    return {"column": col, "direction": "asc"}, 1
