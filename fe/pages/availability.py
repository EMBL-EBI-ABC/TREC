import dash
import requests
import dash_bootstrap_components as dbc
from dash import callback, Output, Input, html
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
        dbc.Badge("✓", color="success", className="small"),
        className="text-center",
    )


def unavailable_cell():
    return html.Td(
        html.Span("—", className="text-muted small"),
        className="text-center",
    )


layout = dbc.Container([
    html.H3("Data Availability Across Stations", className="mt-3 mb-1"),
    html.P("Which data types are available at each sampling station",
           className="text-muted mb-3"),
    html.Label("Search stations", htmlFor="availability-search",
               className="visually-hidden"),
    dbc.Input(
        id="availability-search",
        placeholder="Search stations...",
        type="text", debounce=True,
        className="mb-3",
    ),
    dbc.Spinner(html.Div(id="availability-table")),
    dbc.Row([
        dbc.Col([
            dbc.Badge("✓", color="success", className="small"),
            html.Span(" Available", className="small me-3"),
            html.Span("—", className="text-muted me-1"),
            html.Span("Not available", className="small"),
        ], className="d-flex align-items-center"),
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
])


@callback(
    Output("availability-table", "children"),
    Output("availability-pagination", "max_value"),
    Output("availability-pagination", "active_page"),
    Input("availability-search", "value"),
    Input("availability-pagination", "active_page"),
)
def build_matrix(search_value, page):
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

    # Sort by country then name
    stations.sort(key=lambda s: (s.get("country") or "", s["station_name"]))

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
        html.Th("Station", className="text-start", scope="col"),
        html.Th("Country", className="text-start", scope="col"),
        html.Th("Samples", className="text-center", scope="col"),
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
                html.A(station["station_name"], href="/data",
                       className="text-decoration-none text-success"),
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
        striped=True, hover=True, responsive=True, bordered=True, size="sm",
    )

    return table, total_pages, page
