import os
import threading
import urllib.parse
from contextlib import asynccontextmanager
import json
import httpx
from cachetools import TTLCache
from fastapi.responses import Response

from pathlib import Path as FilePath
from dotenv import load_dotenv
# load_dotenv(FilePath(__file__).resolve().parent.parent / ".env")

# Load environment variables from .env file
load_dotenv()


ES_INDEX = os.getenv("ES_INDEX", "data_portal_development_5")

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
    TREC_NESTED_CONFIGS,
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

async def elastic_search(index_name, params, data_class, aggregation_class,
                         extra_filters=None, nested_configs=None):
    nested_configs = nested_configs or {}

    # Build the query body based on whether there is full text search.
    if params.q:
        query_body = {
            "multi_match": {"query": params.q, "fields": ["*"], "operator": "and", "fuzziness": "AUTO"},
        }
    else:
        query_body = {"match_all": {}}

    # Adding filters.
    filters = list(extra_filters or [])
    aggregation_fields = get_list_of_aggregations(aggregation_class)
    if aggregation_fields:
        for aggregation_field in aggregation_fields:
            filter_value = getattr(params, aggregation_field)
            if filter_value:
                # Support comma-separated multiple values
                values = [v.strip() for v in str(filter_value).split("|") if v.strip()]
                nested_cfg = nested_configs.get(aggregation_field)
                if nested_cfg:
                    filters.append({
                        "nested": {
                            "path": nested_cfg["path"],
                            "query": {
                                "bool": {
                                    "must": [
                                        {"term": {nested_cfg["name_field"]: nested_cfg["name_value"]}},
                                        {"terms": {nested_cfg["value_field"]: values}}
                                    ]
                                }
                            }
                        }
                    })
                else:
                    filters.append({"terms": {aggregation_field: values}})

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
        response = await app.state.es_client.search(index=index_name, body=search_body)
        total = response["hits"]["total"]["value"]
        hits = [r["_source"] for r in response["hits"]["hits"]]
        aggregations = response["aggregations"]

        # Normalise nested aggregations
        for field_name, nested_cfg in nested_configs.items():
            if field_name in aggregations:
                aggregations[field_name] = aggregations[field_name]["filtered"]["values"]

        return ElasticResponse[data_class, aggregation_class](
            total=total,
            start=params.start,
            size=params.size,
            results=hits,
            aggregations=aggregations,
        )

    except Exception as e:
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
    extra_filters = []
    if params.is_source_sample is not None:
        extra_filters.append(
            {"term": {"is_source_sample": params.is_source_sample}})
    if params.parent_sample_id is not None:
        extra_filters.append(
            {"term": {"parent_sample_id": params.parent_sample_id}})
    if params.has_images is not None:
        extra_filters.append(
            {"term": {"has_images": params.has_images}})
    if params.has_ena_data is not None:
        extra_filters.append(
            {"term": {"has_ena_data": params.has_ena_data}})
    return await elastic_search(
        index_name=ES_INDEX,
        params=params,
        data_class=TRECData,
        aggregation_class=TRECAggregationResponse,
        extra_filters=extra_filters or None,
        nested_configs=TREC_NESTED_CONFIGS,
    )


@app.get("/data_portal/{record_id}")
async def trec_details(
        record_id: Annotated[str, Path(description="Record ID")],
) -> ElasticDetailsResponse[TRECData]:
    return await elastic_details(
        index_name=ES_INDEX,
        record_id=record_id,
        data_class=TRECData,
    )


# Caches the full station list (all stations + aggregated metadata).
# TTL is 5 minutes — station data only changes when enrich.py is re-run,
# so this is conservative. Cache is per-process: each Cloud Run instance
# holds its own copy, which is acceptable since the data is read-only between
# re-index runs.
_stations_cache: TTLCache = TTLCache(maxsize=1, ttl=300)
_stations_lock = threading.Lock()


@app.get("/stations")
async def list_stations() -> StationListResponse:
    """List all sampling stations with summary aggregations."""
    _CACHE_KEY = "stations"

    with _stations_lock:
        cached = _stations_cache.get(_CACHE_KEY)
    if cached is not None:
        return cached

    search_body = {
        "size": 0,
        "aggs": {
            "stations": {
                "terms": {"field": "station_name", "size": 500},
                "aggs": {
                    "lat": {"avg": {"field": "lat"}},
                    "lon": {"avg": {"field": "lon"}},
                    "country": {"terms": {"field": "country",
                                          "size": 1}},
                    "source_count": {
                        "filter": {"term": {"is_source_sample": True}},
                    },
                    "analysis_types": {
                        "terms": {"field": "analysis_type",
                                  "size": 20},
                    },
                    "organism_types": {
                        "terms": {"field": "organism.keyword", "size": 20},
                    },
                    "environment_types": {
                        "terms": {"field": "environment_type", "size": 10},
                    },
                    "has_any_images": {
                        "filter": {"term": {"has_images": "Yes"}},
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
            index=ES_INDEX, body=search_body)
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
                environment_types=[b["key"] for b in
                                   bucket["environment_types"]["buckets"]],
                analysis_type_counts={b["key"]: b["doc_count"] for b in
                                      bucket["analysis_types"]["buckets"]},
                environment_type_counts={b["key"]: b["doc_count"] for b in
                                         bucket["environment_types"]["buckets"]},
                has_images=bucket["has_any_images"]["doc_count"] > 0,
                has_ena_data=bucket["has_any_ena"]["doc_count"] > 0,
                min_collection_date=(
                    bucket["min_date"]["value_as_string"]
                    if bucket["min_date"]["value"] else None),
                max_collection_date=(
                    bucket["max_date"]["value_as_string"]
                    if bucket["max_date"]["value"] else None),
            ))
        result = StationListResponse(stations=stations)
        with _stations_lock:
            _stations_cache[_CACHE_KEY] = result
        return result
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
            "query": {"term": {"station_name": station_name}},
            "aggs": {
                "lat": {"avg": {"field": "lat"}},
                "lon": {"avg": {"field": "lon"}},
                "country": {"terms": {"field": "country", "size": 1}},
                "analysis_types": {
                    "terms": {"field": "analysis_type", "size": 20},
                },
                "organisms": {
                    "terms": {"field": "organism.keyword", "size": 50},
                },
            },
        }
        summary_resp = await app.state.es_client.search(
            index=ES_INDEX, body=summary_body)
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
                        {"term": {"station_name": station_name}},
                        {"term": {"is_source_sample": True}},
                    ]
                }
            },
            "sort": [{"collection_date": {"order": "desc"}}],
            "_source": ["biosampleId", "organism", "collection_device",
                        "depth", "altitude", "derived_sample_ids"],
        }
        source_resp = await app.state.es_client.search(
            index=ES_INDEX, body=source_body)
        source_count = source_resp["hits"]["total"]["value"]

        source_hits = source_resp["hits"]["hits"]

        # Collect all derived IDs across all source samples in one pass
        all_derived_ids = []
        for hit in source_hits:
            all_derived_ids.extend(hit["_source"].get("derived_sample_ids") or [])

        # Fetch all derived samples in one batched terms query
        BATCH_SIZE = 10_000
        derived_lookup: dict[str, dict] = {}
        if all_derived_ids:
            for chunk_start in range(0, len(all_derived_ids), BATCH_SIZE):
                chunk = all_derived_ids[chunk_start:chunk_start + BATCH_SIZE]
                derived_body = {
                    "size": len(chunk),
                    "query": {"terms": {"biosampleId.keyword": chunk}},
                    "_source": ["biosampleId", "analysis_type", "has_images"],
                }
                derived_resp = await app.state.es_client.search(
                    index=ES_INDEX, body=derived_body)
                for d in derived_resp["hits"]["hits"]:
                    s = d["_source"]
                    derived_lookup[s["biosampleId"]] = {
                        "biosampleId": s["biosampleId"],
                        "analysis_type": s.get("analysis_type"),
                        "has_images": s.get("has_images", "No"),
                    }

        # Build source_samples list from the lookup — no further ES calls
        source_samples = []
        for hit in source_hits:
            src = hit["_source"]
            derived_ids = src.get("derived_sample_ids") or []
            derived_samples = [
                derived_lookup[did]
                for did in derived_ids
                if did in derived_lookup
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
        "track_total_hits": True,
        "aggs": {
            "stations": {
                "cardinality": {"field": "station_name"}
            },
            "countries": {
                "cardinality": {"field": "country"}
            },
            "source_samples": {
                "filter": {"term": {"is_source_sample": True}}
            },
            "with_images": {
                "filter": {"term": {"has_images": "Yes"}}
            },
            "with_ena": {
                "filter": {"term": {"has_ena_data": True}}
            },
        },
    }
    try:
        response = await app.state.es_client.search(
            index=ES_INDEX, body=search_body)
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