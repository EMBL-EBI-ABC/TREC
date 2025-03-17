from typing import Any

import dash
import requests

import dash_bootstrap_components as dbc
from dash import callback, Output, Input, html

dash.register_page(
    __name__,
    title="Data Portal",
)

layout = dbc.Container(
    dbc.Row(
        [
            dbc.Col(
                [
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H4("Organism", className="card-title"),
                                html.Hr(),
                                dbc.Checklist(id="organism_filter")
                            ]
                        ),
                        style={"margin-bottom": "5px"},
                    ),
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H4("Depth", className="card-title"),
                                html.Hr(),
                                dbc.Checklist(id="depth_filter")
                            ]
                        ),
                        style={"margin-bottom": "5px"},
                    ),
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H4("Altitude", className="card-title"),
                                html.Hr(),
                                dbc.Checklist(id="altitude_filter")
                            ]
                        ),
                        style={"margin-bottom": "5px"},
                    ),
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H4("Geographic Location", className="card-title"),
                                html.Hr(),
                                dbc.Checklist(id="location_filter")
                            ]
                        ),
                        style={"margin-bottom": "5px"},
                    )
                ],
                id="filters-card",
                md=3,
                style={"marginBottom": "5px"},
            ),
            dbc.Col(
                dbc.Spinner(
                    dbc.Stack(
                        [
                            dbc.Input(id="input", placeholder="Free text search, "
                                                              "ex. soil metagenome...",
                                      type="text", debounce=True),
                            html.Div(id="data_table"),
                            dbc.Pagination(id="pagination", max_value=1860,
                                           first_last=True,
                                           previous_next=True,
                                           fully_expanded=False),
                        ],
                        gap=3
                    )
                ),
                md=9),
        ],
        style={
            "marginTop": "15px",
        }
    )
)


def return_tax_id_button(scientific_name: str, tax_id: str) -> dbc.Button:
    return dbc.Button(
        scientific_name,
        outline=True,
        href=f"/data-portal/{tax_id}")


def return_badge_status(budge_text: str, color: str = None) -> dbc.Badge:
    if color is not None:
        return dbc.Badge(budge_text, pill=True, color=color)

    if budge_text == "Submitted to BioSamples":
        color = "secondary"
    elif budge_text == "Raw Data - Submitted":
        color = "primary"
    else:
        color = "success"
    return dbc.Badge(budge_text, pill=True, color=color)


def generate_filters(aggregations: list) -> tuple[list, int]:
    options = []
    total_count = 0
    for bucket in aggregations:
        total_count += bucket["doc_count"]
        options.append(
            {"label": f"{bucket['key']} - {bucket['doc_count']}",
             "value": bucket['key']}
        )
    return options, total_count


def return_sample_id_button(biosample_id: str) -> html.A:
    return html.A(
        biosample_id,
        style={"textDecoration": "none"},
        href=f"/data-portal/{biosample_id}"
    )


@callback(
    Output("data_table", "children"),
    Output("organism_filter", "options"),
    Output("depth_filter", "options"),
    Output("altitude_filter", "options"),
    Output("location_filter", "options"),
    Output("pagination", "max_value"),
    Input("organism_filter", "value"),
    Input("depth_filter", "value"),
    Input("altitude_filter", "value"),
    Input("location_filter", "value"),
    Input("input", "value"),
    Input("pagination", "active_page"),
    running=[
        (Output("input", "class_name"), "invisible",
         "visible"),
        (Output("pagination", "class_name"), "invisible",
         "justify-content-end"),
        (Output("filters-card", "class_name"), "invisible",
         "card-title")
    ]
)
def create_update_data_table(organism_filter, depth_filter, altitude_filter,
                             location_filter, input_value, pagination):
    if pagination is None or pagination == 1:
        start = 0
    else:
        start = (pagination - 1) * 30
    params = {"size": 30, "start": start}
    for field_name, values in {"organism": organism_filter, "depth": depth_filter,
                               "altitude": altitude_filter,
                               "location": location_filter}.items():
        if values is not None and len(values) > 0:
            params[field_name] = values[0]
    if input_value is not None:
        params["q"] = input_value
    response = requests.get(
        "https://trec-be-868757013548.europe-west2.run.app/data_portal",
        params=params).json()

    table_header = [
        html.Thead(html.Tr([html.Th(value, className="text-center") for value in
                            ["BioSample ID", "Organism", "Depth", "Altitude",
                             "Geographic Location"]]))]
    table_body = [
        html.Tbody(
            [html.Tr(
                [html.Td(return_sample_id_button(row["biosampleId"]),
                         className="text-center"),
                 html.Td(row["organism"], className="text-center"),
                 html.Td(row["depth"], className="text-center"),
                 html.Td(row["altitude"], className="text-center"),
                 html.Td(row["location"], className="text-center")])
                for
                row in response["results"]])
    ]
    table = dbc.Table(table_header + table_body, striped=True, bordered=True,
                      hover=True, responsive=True, )

    organism_options, total_count = generate_filters(
        response["aggregations"]["organism"]["buckets"])
    depth_options, _ = generate_filters(response["aggregations"]["depth"]["buckets"])
    altitude_options, _ = generate_filters(
        response["aggregations"]["altitude"]["buckets"])
    location_options, _ = generate_filters(
        response["aggregations"]["location"]["buckets"])

    return (table, organism_options, depth_options, altitude_options, location_options,
            total_count // 30 + 1)
