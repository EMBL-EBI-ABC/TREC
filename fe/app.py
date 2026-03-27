import dash
from dash import html
import dash_bootstrap_components as dbc

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.MINTY],
    use_pages=True,
    suppress_callback_exceptions=True,
)

app.layout = html.Div([
    dbc.NavbarSimple(
        children=[
            dbc.NavItem(dbc.NavLink("Data Portal", href="/data")),
            dbc.NavItem(dbc.NavLink("Availability", href="/availability")),
            dbc.NavItem(dbc.NavLink("API", href="/api")),
            dbc.NavItem(dbc.NavLink("About", href="/about")),
        ],
        brand=dbc.Button("TREC",
                         href=f"{dash.page_registry['pages.home']['path']}",
                         outline=True, color="primary", size="lg"),
        color="white",
        dark=False,
    ),
    dash.page_container
])
server = app.server

if __name__ == "__main__":
    app.run_server(debug=True)
