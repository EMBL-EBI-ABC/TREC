import dash
from dash import html
import dash_bootstrap_components as dbc

TREC_LOGO = ("https://www.embl.org/about/info/trec/wp-content/uploads/2023/02/"
             "20230126_TREC_Tag_RGB-s.jpg")

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.MINTY],
    use_pages=True)

app.layout = html.Div([
    dbc.NavbarSimple(
        children=[
            dbc.NavItem(dbc.NavLink("Data Portal", href="#")),
            dbc.NavItem(dbc.NavLink("API", href="#")),
            dbc.NavItem(dbc.NavLink("About", href="#")),
        ],
        brand=html.Img(src=TREC_LOGO, height="60px"),
        brand_href=f"{dash.page_registry['pages.home']['path']}",
        color="white",
    ),
    dash.page_container
])
server = app.server

if __name__ == "__main__":
    app.run_server(debug=True)
