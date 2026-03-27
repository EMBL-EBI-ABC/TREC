import dash
import requests
import dash_bootstrap_components as dbc
from dash import callback, Output, Input, html, dcc, dash_table
from api_config import API_BASE_URL

dash.register_page(
    __name__,
    path="/availability",
    title="Data Availability",
)

ANALYSIS_TYPES = ["Metagenomics", "Metabolomics", "Imaging", "Ions"]


layout = dbc.Container([
    html.H3("Data Availability Across Stations", className="mt-3 mb-1"),
    html.P("Which data types are available at each sampling station",
           className="text-muted mb-3"),
    dbc.Input(
        id="availability-search",
        placeholder="Search stations...",
        type="text", debounce=True,
        className="mb-3",
    ),
    dbc.Spinner(html.Div(id="availability-matrix")),
])


@callback(
    Output("availability-matrix", "children"),
    Input("availability-search", "value"),
)
def build_matrix(search_value):
    try:
        resp = requests.get(f"{API_BASE_URL}/stations").json()
    except Exception as e:
        return html.P(f"Error loading stations: {e}",
                       className="text-danger")

    stations = resp.get("stations", [])
    if not stations:
        return html.P("No stations found", className="text-muted")

    # Filter by search
    if search_value:
        q = search_value.lower()
        stations = [s for s in stations
                    if q in s["station_name"].lower()
                    or q in (s.get("country") or "").lower()]

    # Sort by country then name
    stations.sort(key=lambda s: (s.get("country") or "", s["station_name"]))

    # Build rows for DataTable
    rows = []
    for s in stations:
        available = set(s.get("analysis_types", []))
        row = {
            "station": s["station_name"],
            "country": s.get("country") or "",
            "samples": s.get("sample_count", 0),
        }
        for at in ANALYSIS_TYPES:
            row[at] = "✓" if at in available else "—"
        row["ENA"] = "✓" if s.get("has_ena_data") else "—"
        row["Images"] = "✓" if s.get("has_images") else "—"
        rows.append(row)

    if not rows:
        return html.P("No stations match your search", className="text-muted")

    return html.Div([
        dash_table.DataTable(
            columns=[
                {"name": "Station", "id": "station"},
                {"name": "Country", "id": "country"},
                {"name": "Samples", "id": "samples"},
                *[{"name": at, "id": at} for at in ANALYSIS_TYPES],
                {"name": "ENA", "id": "ENA"},
                {"name": "Images", "id": "Images"},
            ],
            data=rows,
            page_size=10,
            page_action="native",
            style_cell={"textAlign": "center", "fontSize": "13px",
                         "padding": "6px 10px"},
            style_cell_conditional=[
                {"if": {"column_id": "station"}, "textAlign": "left"},
                {"if": {"column_id": "country"}, "textAlign": "left"},
            ],
            style_header={"fontWeight": "bold", "fontSize": "13px"},
            style_data_conditional=[
                {"if": {"filter_query": '{{{col}}} = "✓"'.format(col=col),
                        "column_id": col},
                 "color": "#2c7a5c", "fontWeight": "bold"}
                for col in ANALYSIS_TYPES + ["ENA", "Images"]
            ],
        ),
        html.Div([
            html.Span("✓", className="text-success fw-bold me-1"),
            html.Span("Available", className="small me-3"),
            html.Span("—", className="text-muted me-1"),
            html.Span("Not available", className="small"),
        ], className="mt-2 mb-3"),
    ])
