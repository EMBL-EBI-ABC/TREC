import dash
import requests
import pandas as pd
import plotly.express as px
import dash_bootstrap_components as dbc
from dash import dcc, html, callback, Output, Input, clientside_callback

dash.register_page(
    __name__,
    path="/expedition-timeline",
    title="Expedition Timeline",
)


def layout(**kwargs):
    return dbc.Container([
        dbc.Row(
            dbc.Col([
                html.H3("Expedition Timeline",
                        style={"marginTop": "15px"}),
                html.P("Watch the TREC expedition unfold along European coastlines month by month.",
                       className="text-muted"),
            ], md=12)
        ),
        dbc.Row(
            dbc.Col(
                dbc.Spinner(dcc.Graph(id="timeline-map")),
                md=12
            )
        ),
    ])


@callback(
    Output("timeline-map", "figure"),
    Input("timeline-map", "id"),
)
def build_timeline_map(_):
    try:
        response = requests.get(
            "http://localhost:8080/expedition_timeline"
        ).json()

        df = pd.DataFrame(response["results"])

        # cumulative frames — each month shows all stops up to that point
        months = sorted(df["month"].unique())
        rows = []
        for month in months:
            cumulative = df[df["month"] <= month].copy()
            cumulative["frame"] = month
            # Mark current month points differently
            cumulative["status"] = cumulative["month"].apply(
                lambda m: "Current month" if m == month else "Previous stops"
            )
            rows.append(cumulative)

        df_cumulative = pd.concat(rows, ignore_index=True)

        fig = px.scatter_map(
            df_cumulative,
            lat="lat",
            lon="lon",
            color="status",
            animation_frame="frame",
            hover_name="location",
            hover_data=["month"],
            zoom=3,
            height=700,
            color_discrete_map={
                "Current month": "#e74c3c",
                "Previous stops": "#3498db",
            },
            category_orders={"status": ["Current month", "Previous stops"]}
        )

        fig.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = 800
        fig.layout.updatemenus[0].buttons[0].args[1]["transition"]["duration"] = 300

        fig.update_layout(legend_title_text="<b>Status</b>")

        return fig

    except Exception as e:
        return {}


