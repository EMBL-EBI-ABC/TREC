import dash
import dash_bootstrap_components as dbc
from dash import html

dash.register_page(
    __name__,
    title="About",
)

layout = dbc.Container(
    dbc.Row(
        [
            dbc.Col([
                html.H3("A scientific voyage to address environmental challenges"),
                html.P("With TREC, we embark on a journey through European coastlines "
                       "to explore the biodiversity and molecular adaptability of "
                       "microbial communities as well as key selected organisms. We "
                       "focus on coastal habitats as they are the richest in species "
                       "biodiversity and they also often present the highest levels of "
                       "pollution. "),
                html.P("By combining the expertise and infrastructure of EMBL and our "
                       "multiple European partners, TREC aims to initiate a new era of "
                       "coastal ecosystems exploration. The goal is timely and "
                       "ambitious – to observe, model, and understand the effects of "
                       "changing environments on organisms and communities, at the "
                       "cellular and molecular levels."),
                html.P([
                    "You can read more about it ",
                    html.A("here",
                           href="https://www.embl.org/about/info/trec/",
                           style={"textDecoration": "none"}),
                ])
            ], md=8),
            dbc.Col(html.Img(
                src="https://www.embl.org/about/info/trec/wp-content/uploads/2023/02/"
                    "20230126_TREC_Tag_RGB-s.jpg",
                style={"width": "50%"}),
                md=4)
        ],
        style={"marginTop": "35px", "marginBottom": "15px"},
    )
)
