import os
import urllib.parse
from contextlib import asynccontextmanager
import json

from dotenv import load_dotenv
load_dotenv()

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
    StationSummary,
    StationListResponse,
    SourceSampleSummary,
    StationDetailResponse,
    GlobalStats,
)


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

async def elastic_search(index_name, params, data_class, aggregation_class):
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
                filters.append({"terms": {aggregation_field: [filter_value]}})

    # Combine query with filters.
    search_body = {
        "from": params.start,
        "size": params.size,
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
        index_name="data_portal",
        params=params,
        data_class=TRECData,
        aggregation_class=TRECAggregationResponse,
    )


@app.get("/data_portal/{record_id}")
async def trec_details(
        record_id: Annotated[str, Path(description="Record ID")],
) -> ElasticDetailsResponse[TRECData]:
    return await elastic_details(
        index_name="data_portal",
        record_id=record_id,
        data_class=TRECData,
    )


@app.get("/stations")
async def list_stations() -> StationListResponse:
    """List all sampling stations with summary aggregations."""
    search_body = {
        "size": 0,
        "aggs": {
            "stations": {
                "terms": {"field": "station_name.keyword", "size": 500},
                "aggs": {
                    "lat": {"avg": {"field": "lat"}},
                    "lon": {"avg": {"field": "lon"}},
                    "country": {"terms": {"field": "country.keyword",
                                          "size": 1}},
                    "source_count": {
                        "filter": {"term": {"is_source_sample": True}},
                    },
                    "analysis_types": {
                        "terms": {"field": "analysis_type.keyword",
                                  "size": 20},
                    },
                    "organism_types": {
                        "terms": {"field": "organism.keyword", "size": 20},
                    },
                    "has_any_images": {
                        "filter": {"term": {"has_images": True}},
                    },
                    "has_any_ena": {
                        "filter": {"term": {"has_ena_data": True}},
                    },
                    "min_date": {"min": {"field": "collection_date"}},
                    "max_date": {"max": {"field": "collection_date"}},
                },
            }
        },
    }
    try:
        response = await app.state.es_client.search(
            index="data_portal", body=search_body)
        stations = []
        for bucket in response["aggregations"]["stations"]["buckets"]:
            country_buckets = bucket["country"]["buckets"]
            country = country_buckets[0]["key"] if country_buckets else None
            stations.append(StationSummary(
                station_name=bucket["key"],
                lat=bucket["lat"]["value"] or 0.0,
                lon=bucket["lon"]["value"] or 0.0,
                country=country,
                sample_count=bucket["doc_count"],
                source_sample_count=bucket["source_count"]["doc_count"],
                analysis_types=[b["key"] for b in
                                bucket["analysis_types"]["buckets"]],
                organism_types=[b["key"] for b in
                                bucket["organism_types"]["buckets"]],
                has_images=bucket["has_any_images"]["doc_count"] > 0,
                has_ena_data=bucket["has_any_ena"]["doc_count"] > 0,
                min_collection_date=(
                    bucket["min_date"]["value_as_string"]
                    if bucket["min_date"]["value"] else None),
                max_collection_date=(
                    bucket["max_date"]["value_as_string"]
                    if bucket["max_date"]["value"] else None),
            ))
        return StationListResponse(stations=stations)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Station list error: {str(e)}")


@app.get("/stations/{station_name}")
async def station_detail(
        station_name: Annotated[str, Path(description="Station name")],
) -> StationDetailResponse:
    """Get detailed info for a single station including source samples."""
    try:
        # Get station summary aggregations
        summary_body = {
            "size": 0,
            "query": {"term": {"station_name.keyword": station_name}},
            "aggs": {
                "lat": {"avg": {"field": "lat"}},
                "lon": {"avg": {"field": "lon"}},
                "country": {"terms": {"field": "country.keyword", "size": 1}},
                "analysis_types": {
                    "terms": {"field": "analysis_type.keyword", "size": 20},
                },
                "organisms": {
                    "terms": {"field": "organism.keyword", "size": 50},
                },
            },
        }
        summary_resp = await app.state.es_client.search(
            index="data_portal", body=summary_body)
        total = summary_resp["hits"]["total"]["value"]
        aggs = summary_resp["aggregations"]
        country_buckets = aggs["country"]["buckets"]
        country = country_buckets[0]["key"] if country_buckets else None
        organism_counts = {b["key"]: b["doc_count"]
                          for b in aggs["organisms"]["buckets"]}

        # Get source samples at this station
        source_body = {
            "size": 200,
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"station_name.keyword": station_name}},
                        {"term": {"is_source_sample": True}},
                    ]
                }
            },
            "sort": [{"collection_date": {"order": "desc"}}],
            "_source": ["biosampleId", "organism", "collection_device",
                        "depth", "altitude", "derived_sample_ids"],
        }
        source_resp = await app.state.es_client.search(
            index="data_portal", body=source_body)
        source_count = source_resp["hits"]["total"]["value"]

        source_samples = []
        for hit in source_resp["hits"]["hits"]:
            src = hit["_source"]
            derived_ids = src.get("derived_sample_ids") or []
            # Fetch derived sample summaries
            derived_samples = []
            if derived_ids:
                derived_body = {
                    "size": len(derived_ids),
                    "query": {
                        "terms": {"biosampleId.keyword": derived_ids}
                    },
                    "_source": ["biosampleId", "analysis_type", "has_images"],
                }
                derived_resp = await app.state.es_client.search(
                    index="data_portal", body=derived_body)
                derived_samples = [
                    {
                        "biosampleId": d["_source"]["biosampleId"],
                        "analysis_type": d["_source"].get("analysis_type"),
                        "has_images": d["_source"].get("has_images", False),
                    }
                    for d in derived_resp["hits"]["hits"]
                ]

            source_samples.append(SourceSampleSummary(
                biosampleId=src["biosampleId"],
                organism=src.get("organism"),
                collection_device=src.get("collection_device"),
                depth=src.get("depth"),
                altitude=src.get("altitude"),
                derived_samples=derived_samples,
            ))

        return StationDetailResponse(
            station_name=station_name,
            lat=aggs["lat"]["value"] or 0.0,
            lon=aggs["lon"]["value"] or 0.0,
            country=country,
            sample_count=total,
            source_sample_count=source_count,
            analysis_types=[b["key"] for b in
                            aggs["analysis_types"]["buckets"]],
            organism_counts=organism_counts,
            source_samples=source_samples,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Station detail error: {str(e)}")


@app.get("/stats")
async def global_stats() -> GlobalStats:
    """Return global expedition statistics for the stats banner."""
    search_body = {
        "size": 0,
        "aggs": {
            "stations": {
                "cardinality": {"field": "station_name.keyword"}
            },
            "countries": {
                "cardinality": {"field": "country.keyword"}
            },
            "source_samples": {
                "filter": {"term": {"is_source_sample": True}}
            },
            "with_images": {
                "filter": {"term": {"has_images": True}}
            },
            "with_ena": {
                "filter": {"term": {"has_ena_data": True}}
            },
        },
    }
    try:
        response = await app.state.es_client.search(
            index="data_portal", body=search_body)
        total = response["hits"]["total"]["value"]
        aggs = response["aggregations"]
        return GlobalStats(
            total_stations=aggs["stations"]["value"],
            total_countries=aggs["countries"]["value"],
            total_source_samples=aggs["source_samples"]["doc_count"],
            total_samples=total,
            total_with_images=aggs["with_images"]["doc_count"],
            total_with_ena=aggs["with_ena"]["doc_count"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Stats error: {str(e)}")
