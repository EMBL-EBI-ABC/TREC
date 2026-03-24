import dash
import requests
import pandas as pd
import plotly.express as px
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
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
            "https://trec-be-test-868757013548.europe-west2.run.app/expedition_timeline"
        ).json()

        df = pd.DataFrame(response["results"])
        months = sorted(df["month"].unique())

        route = df.groupby("month").first().reset_index().sort_values("month")

        frames = []
        for month in months:
            cumulative = df[df["month"] <= month]
            current = df[df["month"] == month]
            route_so_far = route[route["month"] <= month]

            frame_data = [
                # route line
                go.Scattermap(
                    lat=route_so_far["lat"].tolist(),
                    lon=route_so_far["lon"].tolist(),
                    mode="lines",
                    line=dict(width=2, color="#95a5a6"),
                    name="Route",
                    hoverinfo="skip",
                    showlegend=False,
                ),
                # previous stops
                go.Scattermap(
                    lat=cumulative[cumulative["month"] < month]["lat"].tolist(),
                    lon=cumulative[cumulative["month"] < month]["lon"].tolist(),
                    mode="markers",
                    marker=dict(size=8, color="#3498db"),
                    name="Previous stops",
                    text=cumulative[cumulative["month"] < month]["location"].tolist(),
                    hovertemplate="<b>%{text}</b><extra></extra>",
                ),
                # current month stops
                go.Scattermap(
                    lat=current["lat"].tolist(),
                    lon=current["lon"].tolist(),
                    mode="markers",
                    marker=dict(size=10, color="#e74c3c"),
                    name="Current month",
                    text=current["location"].tolist(),
                    hovertemplate="<b>%{text}</b><br>" + month + "<extra></extra>",
                ),
            ]
            frames.append(go.Frame(data=frame_data, name=month))

        first_month = months[0]
        first_route = route[route["month"] <= first_month]
        first_current = df[df["month"] == first_month]

        fig = go.Figure(
            data=[
                go.Scattermap(
                    lat=first_route["lat"].tolist(),
                    lon=first_route["lon"].tolist(),
                    mode="lines",
                    line=dict(width=2, color="#95a5a6"),
                    name="Route",
                    hoverinfo="skip",
                    showlegend=False,
                ),
                go.Scattermap(
                    lat=[],
                    lon=[],
                    mode="markers",
                    marker=dict(size=8, color="#3498db"),
                    name="Previous stops",
                ),
                go.Scattermap(
                    lat=first_current["lat"].tolist(),
                    lon=first_current["lon"].tolist(),
                    mode="markers",
                    marker=dict(size=10, color="#e74c3c"),
                    name="Current month",
                    text=first_current["location"].tolist(),
                    hovertemplate="<b>%{text}</b><extra></extra>",
                ),
            ],
            frames=frames,
        )

        fig.update_layout(
            map=dict(style="carto-positron", zoom=2.5, center=dict(lat=52, lon=15)),
            height=700,
            legend_title_text="<b>Status</b>",
            updatemenus=[dict(
                type="buttons",
                showactive=False,
                y=-0.05,
                x=0.5,
                xanchor="center",
                yanchor="top",
                buttons=[
                    dict(
                        label="▶ Play",
                        method="animate",
                        args=[None, dict(
                            frame=dict(duration=800, redraw=True),
                            transition=dict(duration=300),
                            fromcurrent=True,
                        )]
                    ),
                    dict(
                        label="⏸ Pause",
                        method="animate",
                        args=[[None], dict(
                            frame=dict(duration=0, redraw=False),
                            mode="immediate",
                            transition=dict(duration=0),
                        )]
                    ),
                ]
            )],
            sliders=[dict(
                steps=[
                    dict(
                        method="animate",
                        args=[[month], dict(
                            frame=dict(duration=800, redraw=True),
                            mode="immediate",
                            transition=dict(duration=300),
                        )],
                        label=month,
                    )
                    for month in months
                ],
                x=0.05,
                y=0,
                len=0.9,
                pad=dict(t=80),
            )]
        )

        return fig

    except Exception as e:
        return {}


