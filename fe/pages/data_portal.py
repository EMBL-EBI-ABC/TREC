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
                                dbc.Checklist(id="organism_filter")
                            ]
                        ),
                        style={"margin-bottom": "5px"},
                    ),
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H4("Depth", className="card-title"),
                                dbc.Checklist(id="depth_filter")
                            ]
                        ),
                        style={"margin-bottom": "5px"},
                    ),
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H4("Altitude", className="card-title"),
                                dbc.Checklist(id="altitude_filter")
                            ]
                        ),
                        style={"margin-bottom": "5px"},
                    ),
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H4("Geographic Location", className="card-title"),
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
                            dbc.Pagination(id="pagination", max_value=1,
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


def generate_filters(aggregations: list) -> list:
    options = []
    for bucket in aggregations:
        options.append(
            {"label": f"{bucket['key']} - {bucket['doc_count']}",
             "value": bucket['key']}
        )
    return options


@callback(
    Output("data_table", "children"),
    Output("organism_filter", "options"),
    Output("depth_filter", "options"),
    Output("altitude_filter", "options"),
    Output("location_filter", "options"),
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
    params = {"size": 30, "start": 0}
    print(
        f"{organism_filter=}\t{depth_filter=}\t{altitude_filter=}\t{location_filter=}")
    for field_name, values in {"organism": organism_filter, "depth": depth_filter,
                               "altitude": altitude_filter,
                               "location": location_filter}.items():
        if values is not None and len(values) > 0:
            params[field_name] = values[0]
    print(params)
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
                [html.Td(row["biosampleId"], className="text-center"),
                 html.Td(row["organism"], className="text-center"),
                 html.Td(row["depth"], className="text-center"),
                 html.Td(row["altitude"], className="text-center"),
                 html.Td(row["location"], className="text-center")])
                for
                row in response["results"]])
    ]
    table = dbc.Table(table_header + table_body, striped=True, bordered=True,
                      hover=True, responsive=True, )

    organism_options = generate_filters(response["aggregations"]["organism"]["buckets"])
    depth_options = generate_filters(response["aggregations"]["depth"]["buckets"])
    altitude_options = generate_filters(response["aggregations"]["altitude"]["buckets"])
    location_options = generate_filters(response["aggregations"]["location"]["buckets"])

    return table, organism_options, depth_options, altitude_options, location_options
