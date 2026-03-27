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


layout = dbc.Container([
    html.H3("Data Availability Across Stations", className="mt-3 mb-1"),
    html.P("Which data types are available at each sampling station",
           className="text-muted mb-3"),
    dbc.Spinner(html.Div(id="availability-matrix")),
], fluid=True)


@callback(
    Output("availability-matrix", "children"),
    Input("availability-matrix", "id"),
)
def build_matrix(_):
    try:
        resp = requests.get(f"{API_BASE_URL}/stations").json()
    except Exception as e:
        return html.P(f"Error loading stations: {e}",
                       className="text-danger")

    stations = resp.get("stations", [])
    if not stations:
        return html.P("No stations found", className="text-muted")

    # Sort stations by country then name
    stations.sort(key=lambda s: (s.get("country") or "", s["station_name"]))

    # Build table header
    header = html.Thead(html.Tr([
        html.Th("Station", style={"textAlign": "left"}),
        *[html.Th(at, className="text-center", style={"fontSize": "13px"})
          for at in ANALYSIS_TYPES],
        html.Th("ENA", className="text-center", style={"fontSize": "13px"}),
        html.Th("Images", className="text-center",
                style={"fontSize": "13px"}),
    ]))

    # Build rows
    rows = []
    for station in stations:
        available_types = set(station.get("analysis_types", []))
        cells = [
            html.Td(
                html.A(station["station_name"], href="/data",
                       className="text-decoration-none text-success"),
                style={"fontSize": "13px"},
            ),
        ]
        for at in ANALYSIS_TYPES:
            if at in available_types:
                cells.append(html.Td(
                    dbc.Badge("✓", color="success",
                              style={"fontSize": "11px"}),
                    className="text-center",
                ))
            else:
                cells.append(html.Td(
                    html.Span("—", className="text-muted",
                              style={"fontSize": "11px"}),
                    className="text-center",
                ))

        # ENA column
        if station.get("has_ena_data"):
            cells.append(html.Td(
                dbc.Badge("✓", color="success", style={"fontSize": "11px"}),
                className="text-center"))
        else:
            cells.append(html.Td(
                html.Span("—", className="text-muted",
                           style={"fontSize": "11px"}),
                className="text-center"))

        # Images column
        if station.get("has_images"):
            cells.append(html.Td(
                dbc.Badge("✓", color="success", style={"fontSize": "11px"}),
                className="text-center"))
        else:
            cells.append(html.Td(
                html.Span("—", className="text-muted",
                           style={"fontSize": "11px"}),
                className="text-center"))

        rows.append(html.Tr(cells))

    body = html.Tbody(rows)

    legend = html.Div([
        html.Span([
            dbc.Badge("✓", color="success",
                      style={"fontSize": "10px"}),
            " Available",
        ], className="me-3 small"),
        html.Span([
            html.Span("—", className="text-muted"),
            " Not available",
        ], className="small"),
    ], className="mt-2 mb-3")

    return html.Div([
        dbc.Table([header, body], striped=True, hover=True, responsive=True,
                  bordered=True, size="sm"),
        legend,
    ])
