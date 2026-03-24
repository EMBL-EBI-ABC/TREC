import dash
import requests

import dash_bootstrap_components as dbc
from dash import callback, Output, Input, html, dcc, ALL, ctx, State, MATCH

dash.register_page(
    __name__,
    path="/data",
    title="Data",
)


FILTER_CONFIGS = [
    {"id": "organism",        "title": "Organism"},
    {"id": "depth",           "title": "Depth"},
    {"id": "altitude",        "title": "Altitude"},
    {"id": "location",        "title": "Geographic Location"},
    {"id": "has_images",      "title": "Microscopy Images"},
    {"id": "collection_year", "title": "Collection Year"},
    {"id": "protocol",        "title": "Protocol"},
]

FILTER_IDS     = [f["id"] for f in FILTER_CONFIGS]
ROW_HEIGHT     = 34   # px
DEFAULT_ROWS   = 5
EXPANDED_ROWS  = 10

HEADER_STYLE = {
    "backgroundColor": "#c8e6e0",
    "padding": "7px 12px",
    "display": "flex",
    "justifyContent": "space-between",
    "alignItems": "center",
    "cursor": "pointer",
    "userSelect": "none",
    "borderRadius": "4px 4px 0 0",
}


def panel_style(expanded: bool, count: int) -> dict:
    visible_rows   = min(count, EXPANDED_ROWS if expanded else DEFAULT_ROWS)
    all_items_fit  = count <= (EXPANDED_ROWS if expanded else DEFAULT_ROWS)
    return {
        "height":     f"{visible_rows * ROW_HEIGHT}px",
        "overflowY":  "hidden" if all_items_fit else "auto",
        "transition": "height 0.2s ease",
    }


def make_filter_stores():
    return [
        dcc.Store(id={"type": "filter-store", "filter": f_id}, data=None)
        for f_id in FILTER_IDS
    ]


def make_expand_stores():
    return [
        dcc.Store(id={"type": "expand-store", "filter": f_id},
                  data={"expanded": False, "count": 0})
        for f_id in FILTER_IDS
    ]


def make_filter_card(f_id, title, include_search=False):
    body_content = []
    if include_search:
        body_content.append(
            dbc.Input(
                id="protocol-search",
                placeholder="Search protocols...",
                type="text",
                size="sm",
                style={"margin": "6px 8px 4px 8px", "width": "calc(100% - 16px)"},
            )
        )
    body_content.append(
        html.Div(
            id=f"{f_id}-filter-list",
            style={"height": "0px", "overflowY": "hidden", "transition": "height 0.2s ease"},
        )
    )

    return html.Div(
        [
            html.Div(
                [
                    html.Span(title, style={"fontWeight": "600", "fontSize": "0.9em"}),
                    html.Span(
                        "+",
                        id={"type": "expand-icon", "filter": f_id},
                        style={"fontWeight": "bold", "fontSize": "1.1em"},
                    ),
                ],
                id={"type": "expand-toggle", "filter": f_id},
                style=HEADER_STYLE,
                n_clicks=0,
            ),
            html.Div(
                body_content,
                style={
                    "border": "1px solid #dee2e6",
                    "borderTop": "none",
                    "borderRadius": "0 0 4px 4px",
                },
            ),
        ],
        style={"marginBottom": "14px"},
    )


def make_sidebar():
    return html.Div([
        make_filter_card(f["id"], f["title"], include_search=(f["id"] == "protocol"))
        for f in FILTER_CONFIGS
    ])


layout = dbc.Container(
    dbc.Row(
        [
            dbc.Col(
                [
                    *make_filter_stores(),
                    *make_expand_stores(),
                    dcc.Store(id="protocol-all-options"),
                    make_sidebar(),
                ],
                id="filters-card",
                md=3,
                style={"marginBottom": "5px"},
            ),
            dbc.Col(
                dbc.Spinner(
                    dbc.Stack(
                        [
                            dbc.Input(
                                id="input",
                                placeholder="Free text search, ex. soil metagenome...",
                                type="text",
                                debounce=True,
                            ),
                            html.Div(id="data_table"),
                            dbc.Pagination(
                                id="pagination",
                                max_value=1860,
                                first_last=True,
                                previous_next=True,
                                fully_expanded=False,
                            ),
                        ],
                        gap=3,
                    )
                ),
                md=9,
            ),
        ],
        style={"marginTop": "15px"},
    )
)


def generate_filters(aggregations: list) -> tuple[list, int]:
    options = []
    total_count = 0
    for bucket in aggregations:
        total_count += bucket["doc_count"]
        options.append({"label": f"{bucket['key']} - {bucket['doc_count']}",
                        "value": bucket["key"]})
    return options, total_count


def render_filter_items(options: list, selected_value, filter_id: str):
    if not options:
        return html.Div()

    items = []
    for opt in options:
        value      = str(opt["value"])
        label_str  = str(opt.get("label", value))
        label_text, count = (label_str.rsplit(" - ", 1)
                             if " - " in label_str else (label_str, ""))
        is_active  = selected_value is not None and str(selected_value) == value

        items.append(
            html.Div(
                [
                    html.Span(label_text, style={"fontSize": "0.88em"}),
                    html.Span(
                        count,
                        style={
                            "fontSize": "0.78em",
                            "color": "#0F6E56",
                            "backgroundColor": "#f0f0f0",
                            "borderRadius": "10px",
                            "padding": "1px 7px",
                            "minWidth": "32px",
                            "textAlign": "center",
                        },
                    ),
                ],
                id={"type": "filter-item", "filter": filter_id, "value": value},
                n_clicks=0,
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "center",
                    "height": f"{ROW_HEIGHT}px",
                    "padding": "0 12px",
                    "cursor": "pointer",
                    "backgroundColor": "#f4faf8" if is_active else "white",
                    "fontWeight": "600" if is_active else "normal",
                    "borderBottom": "1px solid #f5f5f5",
                    "flexShrink": "0",
                },
            )
        )
    return html.Div(items)


def return_sample_id_button(biosample_id: str) -> html.A:
    return html.A(
        biosample_id,
        style={"textDecoration": "none"},
        href=f"/data-portal/{biosample_id}",
    )


@callback(
    Output({"type": "expand-store", "filter": MATCH}, "data"),
    Output({"type": "expand-icon",  "filter": MATCH}, "children"),
    Input({"type": "expand-toggle", "filter": MATCH}, "n_clicks"),
    State({"type": "expand-store",  "filter": MATCH}, "data"),
    prevent_initial_call=True,
)
def toggle_expand(n_clicks, store_data):
    store_data  = store_data or {"expanded": False, "count": 0}
    new_expanded = not store_data["expanded"]
    count        = store_data["count"]
    new_store    = {"expanded": new_expanded, "count": count}
    icon         = "−" if new_expanded else "+"
    return new_store, icon


@callback(
    *[Output(f"{f_id}-filter-list", "style") for f_id in FILTER_IDS],
    *[Output({"type": "expand-icon",   "filter": f_id}, "style") for f_id in FILTER_IDS],
    *[Output({"type": "expand-toggle", "filter": f_id}, "style") for f_id in FILTER_IDS],
    *[Input({"type": "expand-store", "filter": f_id}, "data") for f_id in FILTER_IDS],
)
def update_panel_styles(*stores):
    list_styles   = []
    icon_styles   = []
    header_styles = []

    for s in stores:
        expanded = (s or {}).get("expanded", False)
        count    = (s or {}).get("count", 0)
        has_more = count > DEFAULT_ROWS

        list_styles.append(panel_style(expanded=expanded, count=count))

        # hide +/− icon when there's nothing extra to show
        icon_styles.append({"display": "none"} if not has_more else
                           {"fontWeight": "bold", "fontSize": "1.1em"})

        # make header non-clickable (keep styling) when toggle is irrelevant
        header_styles.append({**HEADER_STYLE, "cursor": "default"} if not has_more
                             else HEADER_STYLE)

    return (*list_styles, *icon_styles, *header_styles)



@callback(
    Output({"type": "filter-store", "filter": MATCH}, "data"),
    Input({"type": "filter-item",   "filter": MATCH, "value": ALL}, "n_clicks"),
    State({"type": "filter-store",  "filter": MATCH}, "data"),
    prevent_initial_call=True,
)
def handle_filter_click(n_clicks_list, current_value):
    if not ctx.triggered_id or not any(n for n in n_clicks_list if n):
        raise dash.exceptions.PreventUpdate
    clicked_value = ctx.triggered_id["value"]
    if current_value is not None and str(current_value) == str(clicked_value):
        return None
    return clicked_value



@callback(
    Output("data_table",                  "children"),
    Output("organism-filter-list",        "children"),
    Output("depth-filter-list",           "children"),
    Output("altitude-filter-list",        "children"),
    Output("location-filter-list",        "children"),
    Output("protocol-all-options",        "data"),
    Output("has_images-filter-list",      "children"),
    Output("collection_year-filter-list", "children"),
    Output("pagination",                  "max_value"),
    # update the count in each expand-store - preserve expanded state
    *[Output({"type": "expand-store", "filter": f_id}, "data",
             allow_duplicate=True) for f_id in FILTER_IDS],
    Input({"type": "filter-store", "filter": "organism"},        "data"),
    Input({"type": "filter-store", "filter": "depth"},           "data"),
    Input({"type": "filter-store", "filter": "altitude"},        "data"),
    Input({"type": "filter-store", "filter": "location"},        "data"),
    Input("input",                                               "value"),
    Input({"type": "filter-store", "filter": "protocol"},        "data"),
    Input({"type": "filter-store", "filter": "has_images"},      "data"),
    Input({"type": "filter-store", "filter": "collection_year"}, "data"),
    Input("pagination",                                          "active_page"),
    *[State({"type": "expand-store", "filter": f_id}, "data") for f_id in FILTER_IDS],
    running=[
        (Output("input",        "class_name"), "invisible", "visible"),
        (Output("pagination",   "class_name"), "invisible", "justify-content-end"),
        (Output("filters-card", "class_name"), "invisible", "card-title"),
    ],
    prevent_initial_call="initial_duplicate",
)
def create_update_data_table(
    organism_filter, depth_filter, altitude_filter, location_filter,
    input_value, protocol_filter, has_images_filter, collection_year_filter,
    pagination,
    *expand_states,
):
    start = 0 if (pagination is None or pagination == 1) else (pagination - 1) * 20
    params = {"size": 20, "start": start}

    for field_name, value in {
        "organism":        organism_filter,
        "depth":           depth_filter,
        "altitude":        altitude_filter,
        "location":        location_filter,
        "protocol":        protocol_filter,
        "has_images":      has_images_filter,
        "collection_year": collection_year_filter,
    }.items():
        if value is not None:
            params[field_name] = value

    if input_value:
        params["q"] = input_value

    response = requests.get("https://trec-be-test-868757013548.europe-west2.run.app/data_portal", params=params).json()

    # table
    table_header = [html.Thead(html.Tr([
        html.Th(col, className="text-center")
        for col in ["BioSample ID", "Organism", "Depth", "Altitude",
                    "Geographic Location", "Protocol"]
    ]))]
    table_body = [html.Tbody([
        html.Tr([
            html.Td(return_sample_id_button(row["biosampleId"]), className="text-center"),
            html.Td(row["organism"],  className="text-center"),
            html.Td(row["depth"],     className="text-center"),
            html.Td(row["altitude"],  className="text-center"),
            html.Td(row["location"],  className="text-center"),
            html.Td(
                next((f["value"] for f in (row.get("customFields") or [])
                      if f["name"] == "protocol label"), "N/A"),
                className="text-center",
            ),
        ])
        for row in response["results"]
    ])]
    table = dbc.Table(table_header + table_body,
                      striped=True, bordered=True, hover=True, responsive=True)

    # aggregations
    aggs = response["aggregations"]
    organism_opts,   total_count = generate_filters(aggs["organism"]["buckets"])
    depth_opts,      _           = generate_filters(aggs["depth"]["buckets"])
    altitude_opts,   _           = generate_filters(aggs["altitude"]["buckets"])
    location_opts,   _           = generate_filters(aggs["location"]["buckets"])
    protocol_opts,   _           = generate_filters(aggs["protocol"]["buckets"])
    has_images_opts, _           = generate_filters(aggs["has_images"]["buckets"])
    coll_year_opts,  _           = generate_filters(aggs["collection_year"]["buckets"])

    all_opts = {
        "organism":        organism_opts,
        "depth":           depth_opts,
        "altitude":        altitude_opts,
        "location":        location_opts,
        "protocol":        protocol_opts,
        "has_images":      has_images_opts,
        "collection_year": coll_year_opts,
    }

    # update expand-store counts
    new_expand_stores = []
    for i, f_id in enumerate(FILTER_IDS):
        current = expand_states[i] or {"expanded": False, "count": 0}
        new_expand_stores.append({
            "expanded": current.get("expanded", False),
            "count":    len(all_opts[f_id]),
        })

    filter_values = {
        "organism":        organism_filter,
        "depth":           depth_filter,
        "altitude":        altitude_filter,
        "location":        location_filter,
        "protocol":        protocol_filter,
        "has_images":      has_images_filter,
        "collection_year": collection_year_filter,
    }

    return (
        table,
        render_filter_items(organism_opts,   organism_filter,        "organism"),
        render_filter_items(depth_opts,      depth_filter,           "depth"),
        render_filter_items(altitude_opts,   altitude_filter,        "altitude"),
        render_filter_items(location_opts,   location_filter,        "location"),
        protocol_opts,
        render_filter_items(has_images_opts, has_images_filter,      "has_images"),
        render_filter_items(coll_year_opts,  collection_year_filter, "collection_year"),
        total_count // 20 + 1,
        *new_expand_stores,
    )



# protocol search box
@callback(
    Output("protocol-filter-list", "children"),
    Input("protocol-search",       "value"),
    Input("protocol-all-options",  "data"),
    Input({"type": "filter-store", "filter": "protocol"}, "data"),
)
def filter_protocol_options(search_value, all_options, selected_value):
    if not all_options:
        return html.Div()
    filtered = all_options
    if search_value:
        filtered = [o for o in all_options if search_value.lower() in o["label"].lower()]
    return render_filter_items(filtered, selected_value, "protocol")