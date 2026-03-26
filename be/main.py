import os
import urllib.parse
from contextlib import asynccontextmanager
import json
import httpx

from fastapi import FastAPI, HTTPException, Query, Path
from elasticsearch import AsyncElasticsearch
from fastapi.middleware.cors import CORSMiddleware
from collections import defaultdict
from typing import Annotated

from models import (
    get_list_of_aggregations,
    ElasticResponse,
    ElasticDetailsResponse,
    TRECData,
    TRECSearchParams,
    TRECAggregationResponse,
    TREC_NESTED_CONFIGS
)

from fastapi.responses import Response



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize AsyncElasticsearch.
    es_client = AsyncElasticsearch(
        [os.getenv("ES_URL")],
        http_auth=(os.getenv("ES_USERNAME"), os.getenv("ES_PASSWORD")),
        verify_certs=True,
    )
    # Pass the client to the app's state so it's accessible in routes.
    app.state.es_client = es_client
    yield
    # Clean up by closing the Elasticsearch client.
    await es_client.close()


# Initialize FastAPI with lifespan manager.
app = FastAPI(
    lifespan=lifespan,
    title="TREC Data Portal API",
    version="0.0.1",
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
)

# Allow all origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods
    allow_headers=["*"],  # Allows all headers
)


# Generic search methods.

async def elastic_search(index_name, params, data_class, aggregation_class, nested_configs=None):
    nested_configs = nested_configs or {}
    # Build the query body based on whether there is full text search.
    if params.q:
        query_body = {
            "multi_match": {"query": params.q, "fields": ["*"], "operator": "and", "fuzziness": "AUTO"},}
    else:
        query_body = {"match_all": {}}

    # Adding filters.
    filters = []
    aggregation_fields = get_list_of_aggregations(aggregation_class)

    if aggregation_fields:
        for aggregation_field in aggregation_fields:
            filter_value = getattr(params, aggregation_field)
            if filter_value:
                nested_cfg = nested_configs.get(aggregation_field)
                if nested_cfg:
                    filters.append({
                        "nested": {
                            "path": nested_cfg["path"],
                            "query": {
                                "bool": {
                                    "must": [
                                        {"term": {nested_cfg["name_field"]: nested_cfg["name_value"]}},
                                        {"term": {nested_cfg["value_field"]: filter_value}}
                                    ]
                                }
                            }
                        }
                    })
                else:
                    filters.append({"terms": {aggregation_field: [filter_value]}})

    # Combine query with filters.
    search_body = {
        "from": params.start,
        "size": params.size,
        "track_total_hits": True,
        "query": {
            "bool": {
                "must": query_body,
                "filter": filters,
            }
        },
        "aggs": defaultdict(dict),
    }

    # Adding aggregation fields.
    if aggregation_fields:
        for aggregation_field in aggregation_fields:
            nested_cfg = nested_configs.get(aggregation_field)
            if nested_cfg:
                search_body["aggs"][aggregation_field] = {
                    "nested": {"path": nested_cfg["path"]},
                    "aggs": {
                        "filtered": {
                            "filter": {"term": {nested_cfg["name_field"]: nested_cfg["name_value"]}},
                            "aggs": {
                                "values": {"terms": {"field": nested_cfg["value_field"], "size": 100}}
                            }
                        }
                    }
                }
            else:
                search_body["aggs"][aggregation_field] = {
                    "terms": {"field": aggregation_field, "size": 100}
                }


    # Adding sort field and sort order
    search_body["sort"] = [{params.sort_field: {"order": params.sort_order}}]

    # Performing the search.
    try:
        # Execute the async search request.
        response = await app.state.es_client.search(index=index_name, body=search_body)
        # Extract total count and hits.
        total = response["hits"]["total"]["value"]
        hits = [r["_source"] for r in response["hits"]["hits"]]
        aggregations = response["aggregations"]

        # normalise nested aggregations
        for field_name, nested_cfg in nested_configs.items():
            if field_name in aggregations:
                aggregations[field_name] = aggregations[field_name]["filtered"]["values"]

        # Return the results.
        return ElasticResponse[data_class, aggregation_class](
            total=total,
            start=params.start,
            size=params.size,
            results=hits,
            aggregations=aggregations,
        )

    except Exception as e:
        # Handle Elasticsearch errors.
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


async def elastic_details(index_name, record_id, data_class):
    try:
        # Quote the request, except for colons; they might appear in IDs.
        quoted_id = urllib.parse.quote(record_id).replace("%3A", ":")
        if ":" in quoted_id:
            quoted_id = '"' + quoted_id + '"'
        response = await app.state.es_client.search(
            index=index_name, query={"term": {"_id": quoted_id}}
        )
        hits = [r["_source"] for r in response["hits"]["hits"]]
        return ElasticDetailsResponse[data_class](results=hits)
    except Exception as e:
        # Handle Elasticsearch errors.
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


# MaveDB.


@app.get("/data_portal")
async def trec_search(
        params: Annotated[TRECSearchParams, Query()],
) -> ElasticResponse[TRECData, TRECAggregationResponse]:
    return await elastic_search(
        index_name="data_portal_development_3",
        params=params,
        data_class=TRECData,
        aggregation_class=TRECAggregationResponse,
        nested_configs=TREC_NESTED_CONFIGS,
    )


@app.get("/data_portal/{record_id}")
async def trec_details(
        record_id: Annotated[str, Path(description="Record ID")],
) -> ElasticDetailsResponse[TRECData]:
    return await elastic_details(
        index_name="data_portal_development_3",
        record_id=record_id,
        data_class=TRECData,
    )


@app.get("/expedition_timeline")
async def expedition_timeline():
    try:
        response = await app.state.es_client.search(
            index="data_portal_development_3",
            body={
                "size": 0,
                "aggs": {
                    "by_month": {
                        "terms": {
                            "field": "collection_month",
                            "size": 50,
                            "order": {"_key": "asc"}
                        },
                        "aggs": {
                            "locations": {
                                "top_hits": {
                                    "size": 100,
                                    "_source": ["lat", "lon", "location", "collection_month"]
                                }
                            }
                        }
                    }
                }
            }
        )

        results = []
        for month_bucket in response["aggregations"]["by_month"]["buckets"]:
            month = month_bucket["key"]
            seen = set()
            for hit in month_bucket["locations"]["hits"]["hits"]:
                src = hit["_source"]
                key = (src.get("lat"), src.get("lon"))
                if key not in seen and src.get("lat") and src.get("lon"):
                    seen.add(key)
                    results.append({
                        "month": month,
                        "lat": src["lat"],
                        "lon": src["lon"],
                        "location": src.get("location", ""),
                    })

        return {"results": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/zarr-proxy/{path:path}")
async def zarr_proxy(path: str):
    url = f"https://s3.embl.de/live-confocal-trec-super-plankton/{path}"
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
    return Response(
        content=r.content,
        status_code=r.status_code,
        media_type=r.headers.get("content-type", "application/octet-stream"),
        headers={"Access-Control-Allow-Origin": "*"}
    )