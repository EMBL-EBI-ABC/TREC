# TREC Data Portal Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the TREC data portal with a hybrid map + station panel layout, hierarchical sample grouping, scientifically meaningful filters, dataset availability matrix, and BioImage Archive image integration.

**Architecture:** The backend (FastAPI + Elasticsearch) gets new enriched fields on the data model, new station-level endpoints, and enhanced filtering. The frontend (Dash) gets a complete rewrite of the data portal and sample detail pages, plus a new availability matrix page. A one-time enrichment script parses custom fields and relationships into queryable top-level fields.

**Tech Stack:** Python 3.12, FastAPI, AsyncElasticsearch, Pydantic, Dash 2.x, Dash Bootstrap Components, Plotly

**Spec:** `docs/superpowers/specs/2026-03-27-trec-data-portal-redesign-design.md`

**Backend API base URL:** Currently hardcoded in frontend as `https://trec-be-868757013548.europe-west2.run.app`. This plan introduces an `API_BASE_URL` environment variable in the frontend so the URL is configurable.

---

### Task 1: Update Backend Data Model

**Files:**
- Modify: `be/models.py`

This task updates the Pydantic models and DataSource definition to include the new enriched fields that the enrichment script (Task 2) will populate and the new API endpoints (Tasks 3-4) will serve.

- [ ] **Step 1: Update the TREC DataSource fields in `be/models.py`**

Replace the existing `trec` DataSource definition and class generation (lines 134-153) with an expanded version that includes all new fields. Also add the new `StationSummary` and `StationDetail` response models.

```python
# --- Replace everything from line 134 ("# TREC.") to end of file ---

# TREC.
trec = DataSource(
    name="TREC",
    fields=[
        # Original fields
        FieldDefinition(name="altitude", type=str, filterable=False),
        FieldDefinition(name="collection_date", type=datetime.datetime | None),
        FieldDefinition(name="depth", type=str, filterable=False),
        FieldDefinition(name="location", type=str, filterable=False),
        FieldDefinition(name="lat", type=float | None),
        FieldDefinition(name="lon", type=float | None),
        FieldDefinition(name="organism", type=str, filterable=True),
        FieldDefinition(name="biosampleId", type=str),
        FieldDefinition(name="customFields", type=list[CustomField] | None),
        FieldDefinition(name="relationships",
                        type=list[BioSamplesRelationships] | None),
        # Enriched fields - parsed from customFields
        FieldDefinition(name="environment_type", type=str | None,
                        filterable=True),
        FieldDefinition(name="analysis_type", type=str | None,
                        filterable=True),
        FieldDefinition(name="country", type=str | None, filterable=True),
        FieldDefinition(name="biome", type=str | None),
        FieldDefinition(name="local_environment", type=str | None),
        FieldDefinition(name="environmental_medium", type=str | None),
        FieldDefinition(name="collection_device", type=str | None),
        FieldDefinition(name="sampling_platform", type=str | None),
        FieldDefinition(name="size_fraction_lower", type=float | None),
        FieldDefinition(name="size_fraction_upper", type=float | None),
        # Hierarchy fields
        FieldDefinition(name="station_name", type=str | None,
                        filterable=True),
        FieldDefinition(name="is_source_sample", type=bool | None),
        FieldDefinition(name="parent_sample_id", type=str | None),
        FieldDefinition(name="derived_sample_ids", type=list[str] | None),
        FieldDefinition(name="control_sample_id", type=str | None),
        FieldDefinition(name="controlled_sample_ids", type=list[str] | None),
        # Linked data flags
        FieldDefinition(name="has_images", type=bool | None),
        FieldDefinition(name="image_zarr_url", type=str | None),
        FieldDefinition(name="has_ena_data", type=bool | None),
        FieldDefinition(name="ena_accession", type=str | None),
    ],
    default_sort_field="collection_date",
    default_sort_order="desc",
)
TRECData, TRECAggregationResponse, TRECSearchParams = trec.generate_classes()


# Station response models.

class StationSummary(BaseModel):
    station_name: str
    lat: float
    lon: float
    country: str | None
    sample_count: int
    source_sample_count: int
    analysis_types: list[str]
    organism_types: list[str]
    has_images: bool
    has_ena_data: bool
    min_collection_date: str | None
    max_collection_date: str | None


class StationListResponse(BaseModel):
    stations: list[StationSummary]


class SourceSampleSummary(BaseModel):
    biosampleId: str
    organism: str | None
    collection_device: str | None
    depth: str | None
    altitude: str | None
    derived_samples: list[dict]  # [{biosampleId, analysis_type, has_images}]


class StationDetailResponse(BaseModel):
    station_name: str
    lat: float
    lon: float
    country: str | None
    sample_count: int
    source_sample_count: int
    analysis_types: list[str]
    organism_counts: dict[str, int]
    source_samples: list[SourceSampleSummary]
```

- [ ] **Step 2: Verify the models module loads without errors**

Run: `cd /Users/alexey/TREC/be && python -c "from models import TRECData, TRECAggregationResponse, TRECSearchParams, StationSummary, StationListResponse, StationDetailResponse; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add be/models.py
git commit -m "feat: expand TREC data model with enriched fields, hierarchy, and station models"
```

---

### Task 2: Create Data Enrichment Script

**Files:**
- Create: `be/enrich.py`

This script reads all samples from the Elasticsearch `data_portal` index, parses their `customFields` and `relationships` arrays to extract top-level enriched fields, resolves parent-child hierarchies, assigns station names, and writes the enriched data back to ES. It's designed to be run once (or re-run idempotently).

- [ ] **Step 1: Create `be/enrich.py`**

```python
"""
One-time enrichment script for TREC data portal samples.

Reads all samples from the 'data_portal' ES index, parses customFields and
relationships into top-level queryable fields, resolves parent-child sample
hierarchies, and writes enriched data back.

Usage:
    ES_URL=... ES_USERNAME=... ES_PASSWORD=... python enrich.py

Idempotent: safe to re-run.
"""

import os
import re
from elasticsearch import Elasticsearch


def get_custom_field(custom_fields, name):
    """Extract a value from the customFields array by field name."""
    if not custom_fields:
        return None
    for field in custom_fields:
        if field.get("name", "").lower() == name.lower():
            val = field.get("value", "").strip()
            return val if val and val.lower() not in ("not provided",
                                                       "not applicable") else None
    return None


def parse_environment_type(biome_str):
    """Derive environment_type (marine/soil/aerosol) from broad-scale
    environmental context or organism."""
    if not biome_str:
        return None
    lower = biome_str.lower()
    if "marine" in lower or "ocean" in lower or "sea" in lower:
        return "marine"
    if "soil" in lower or "terrestrial" in lower or "land" in lower:
        return "soil"
    if "aerosol" in lower or "air" in lower or "atmosph" in lower:
        return "aerosol"
    return None


def parse_analysis_type(target_analysis, protocol_label):
    """Map target analysis type / protocol label to a standard analysis
    type category."""
    # Check target analysis first
    if target_analysis:
        lower = target_analysis.lower()
        if "metabolom" in lower:
            return "Metabolomics"
        if "imag" in lower or "microscop" in lower:
            return "Imaging"
    # Fall back to protocol label mapping
    if protocol_label:
        label = protocol_label.strip()
        mapping = {
            "MetaBGT": "Metagenomics",
            "MB": "Metabolomics",
            "HPF": "Imaging",
            "Ions": "Ions",
            "ASM": "Metagenomics",
            "PK1": "Imaging",
            "Microscopy": "Imaging",
        }
        if label in mapping:
            return mapping[label]
        # Heuristic fallback
        lower = label.lower()
        if "meta" in lower and "gen" in lower:
            return "Metagenomics"
        if "metab" in lower:
            return "Metabolomics"
        if "ion" in lower:
            return "Ions"
        if "micr" in lower or "imag" in lower or "hpf" in lower:
            return "Imaging"
    return None


def parse_country(location_str):
    """Extract country from geographic location string.
    Formats seen: 'Spain', 'Greece:Athens', 'Italy:Calabria'."""
    if not location_str:
        return None
    return location_str.split(":")[0].strip()


def parse_ontology_label(ontology_str):
    """Extract human-readable label from ontology-coded string.
    E.g. 'marine biome [ENVO:00000447]' -> 'marine biome'."""
    if not ontology_str:
        return None
    match = re.match(r"^(.*?)(?:\s*\[.*\])?\s*$", ontology_str)
    return match.group(1).strip() if match else ontology_str.strip()


def parse_size_fraction(value_str):
    """Parse a numeric size fraction value like '10 µm' -> 10.0."""
    if not value_str:
        return None
    match = re.match(r"([\d.]+)", value_str.strip())
    return float(match.group(1)) if match else None


def build_station_name(location_str, lat, lon):
    """Build a human-readable station name from location and coordinates.
    Uses the location field directly — it already contains names like
    'Spain', 'Greece:Athens', etc."""
    if location_str:
        parts = location_str.split(":")
        if len(parts) >= 2:
            return f"{parts[1].strip()}, {parts[0].strip()}"
        return location_str.strip()
    if lat is not None and lon is not None:
        return f"{lat:.2f}°N, {lon:.2f}°E"
    return "Unknown"


def enrich_sample(source):
    """Parse customFields and relationships into top-level enriched fields."""
    cf = source.get("customFields") or []
    relationships = source.get("relationships") or []

    # Parse ontology fields from customFields
    biome_raw = get_custom_field(cf, "broad-scale environmental context")
    local_env_raw = get_custom_field(cf, "local environmental context")
    medium_raw = get_custom_field(cf, "environmental medium")
    target_analysis = get_custom_field(cf, "target analysis type")
    protocol_label = get_custom_field(cf, "protocol label")
    collection_device = get_custom_field(cf, "collection device")
    sampling_platform = get_custom_field(cf, "sampling platform")
    size_lower = get_custom_field(cf, "size-fraction lower threshold")
    size_upper = get_custom_field(cf, "size-fraction upper threshold")

    biome = parse_ontology_label(biome_raw)
    local_environment = parse_ontology_label(local_env_raw)
    environmental_medium = parse_ontology_label(medium_raw)

    organism = source.get("organism", "")
    env_type = parse_environment_type(biome_raw)
    if not env_type:
        env_type = parse_environment_type(organism)

    analysis_type = parse_analysis_type(target_analysis, protocol_label)
    country = parse_country(source.get("location"))
    station_name = build_station_name(
        source.get("location"), source.get("lat"), source.get("lon"))

    # Parse relationships for parent/child and control links
    parent_sample_id = None
    control_sample_id = None
    controlled_sample_ids = []
    for rel in relationships:
        rel_type = (rel.get("type") or "").lower()
        if "derived from" in rel_type:
            parent_sample_id = rel.get("target")
        if "has control" in rel_type:
            control_sample_id = rel.get("target")
        if "is control of" in rel_type:
            controlled_sample_ids.append(rel.get("target"))

    is_source_sample = parent_sample_id is None

    return {
        "environment_type": env_type,
        "analysis_type": analysis_type,
        "country": country,
        "biome": biome,
        "local_environment": local_environment,
        "environmental_medium": environmental_medium,
        "collection_device": collection_device,
        "sampling_platform": sampling_platform,
        "size_fraction_lower": parse_size_fraction(size_lower),
        "size_fraction_upper": parse_size_fraction(size_upper),
        "station_name": station_name,
        "is_source_sample": is_source_sample,
        "parent_sample_id": parent_sample_id,
        "control_sample_id": control_sample_id,
        "controlled_sample_ids": controlled_sample_ids or None,
        # Linked data flags — defaulting to False/None, to be updated
        # separately when BioImage Archive / ENA links are known
        "has_images": False,
        "has_ena_data": False,
        "image_zarr_url": None,
        "ena_accession": None,
    }


def resolve_derived_sample_ids(es, index_name):
    """Second pass: for each source sample, find all samples that reference
    it as parent and store their IDs in derived_sample_ids."""
    print("Resolving derived_sample_ids for source samples...")
    query = {"query": {"term": {"is_source_sample": True}}, "size": 0,
             "aggs": {"sources": {"terms": {"field": "biosampleId.keyword",
                                            "size": 50000}}}}
    resp = es.search(index=index_name, body=query)
    source_ids = [b["key"] for b in
                  resp["aggregations"]["sources"]["buckets"]]

    bulk_body = []
    for source_id in source_ids:
        children_query = {
            "query": {"term": {"parent_sample_id.keyword": source_id}},
            "_source": ["biosampleId"],
            "size": 100,
        }
        children_resp = es.search(index=index_name, body=children_query)
        child_ids = [h["_source"]["biosampleId"]
                     for h in children_resp["hits"]["hits"]]
        if child_ids:
            # Find the ES doc _id for this source sample
            source_resp = es.search(
                index=index_name,
                query={"term": {"biosampleId.keyword": source_id}},
                size=1,
            )
            if source_resp["hits"]["hits"]:
                doc_id = source_resp["hits"]["hits"][0]["_id"]
                bulk_body.append({"update": {"_index": index_name,
                                             "_id": doc_id}})
                bulk_body.append({"doc": {"derived_sample_ids": child_ids}})

    if bulk_body:
        es.bulk(body=bulk_body, refresh=True)
        print(f"  Updated {len(bulk_body) // 2} source samples with "
              f"derived_sample_ids")
    else:
        print("  No source samples found to update")


def main():
    es = Elasticsearch(
        [os.getenv("ES_URL")],
        http_auth=(os.getenv("ES_USERNAME"), os.getenv("ES_PASSWORD")),
        verify_certs=True,
    )

    index_name = "data_portal"

    # First pass: enrich all samples with parsed fields
    print(f"Enriching samples in '{index_name}' index...")
    scroll_resp = es.search(
        index=index_name,
        body={"query": {"match_all": {}}, "size": 500},
        scroll="5m",
    )
    scroll_id = scroll_resp["_scroll_id"]
    total = scroll_resp["hits"]["total"]["value"]
    processed = 0

    while True:
        hits = scroll_resp["hits"]["hits"]
        if not hits:
            break

        bulk_body = []
        for hit in hits:
            enriched = enrich_sample(hit["_source"])
            bulk_body.append({"update": {"_index": index_name,
                                         "_id": hit["_id"]}})
            bulk_body.append({"doc": enriched})

        if bulk_body:
            es.bulk(body=bulk_body, refresh=False)

        processed += len(hits)
        print(f"  Processed {processed}/{total} samples")
        scroll_resp = es.scroll(scroll_id=scroll_id, scroll="5m")

    es.indices.refresh(index=index_name)
    print(f"First pass complete: {processed} samples enriched")

    # Second pass: resolve derived_sample_ids on source samples
    resolve_derived_sample_ids(es, index_name)

    print("Enrichment complete!")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify the script loads without syntax errors**

Run: `cd /Users/alexey/TREC/be && python -c "import enrich; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add be/enrich.py
git commit -m "feat: add one-time data enrichment script for parsing custom fields and resolving sample hierarchy"
```

---

### Task 3: Add Station API Endpoints

**Files:**
- Modify: `be/main.py`

Add two new endpoints: `GET /stations` (list all stations with summaries for map markers and availability matrix) and `GET /stations/{station_name}` (station detail with source samples).

- [ ] **Step 1: Add station imports and endpoints to `be/main.py`**

First, update the imports from models (line 12-18):

```python
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
)
```

Then add the two station endpoints after the existing `trec_details` endpoint (after line 161):

```python
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
```

- [ ] **Step 2: Verify the app loads**

Run: `cd /Users/alexey/TREC/be && python -c "from main import app; print('Routes:', [r.path for r in app.routes])"`

Expected: Output includes `/stations` and `/stations/{station_name}`

- [ ] **Step 3: Commit**

```bash
git add be/main.py
git commit -m "feat: add station list and station detail API endpoints"
```

---

### Task 4: Add Global Stats Endpoint

**Files:**
- Modify: `be/main.py`
- Modify: `be/models.py`

Add a `GET /stats` endpoint that returns global expedition metrics for the stats banner.

- [ ] **Step 1: Add `GlobalStats` model to `be/models.py`**

Add this class after `StationDetailResponse` at the end of the file:

```python
class GlobalStats(BaseModel):
    total_stations: int
    total_countries: int
    total_source_samples: int
    total_samples: int
    total_with_images: int
    total_with_ena: int
```

- [ ] **Step 2: Add the stats endpoint to `be/main.py`**

Add the import of `GlobalStats` to the import block:

```python
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
```

Add the endpoint after the station endpoints:

```python
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
```

- [ ] **Step 3: Verify**

Run: `cd /Users/alexey/TREC/be && python -c "from main import app; print([r.path for r in app.routes if 'stats' in str(r.path)])"`

Expected: `['/stats']`

- [ ] **Step 4: Commit**

```bash
git add be/models.py be/main.py
git commit -m "feat: add global stats endpoint for expedition metrics banner"
```

---

### Task 5: Create Frontend API Config and Update App Shell

**Files:**
- Create: `fe/api_config.py`
- Modify: `fe/app.py`

Extract the hardcoded API URL into a configurable module and update the navbar to reflect the new page structure (removing the separate "Sampling Map" link since the map is now part of the data portal, adding "Availability").

- [ ] **Step 1: Create `fe/api_config.py`**

```python
import os

API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "https://trec-be-868757013548.europe-west2.run.app"
)
```

- [ ] **Step 2: Update `fe/app.py`**

Replace the entire file with:

```python
import dash
from dash import html
import dash_bootstrap_components as dbc

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.MINTY],
    use_pages=True,
    suppress_callback_exceptions=True,
)

app.layout = html.Div([
    dbc.NavbarSimple(
        children=[
            dbc.NavItem(dbc.NavLink("Data Portal", href="/data")),
            dbc.NavItem(dbc.NavLink("Availability", href="/availability")),
            dbc.NavItem(dbc.NavLink("API", href="/api")),
            dbc.NavItem(dbc.NavLink("About", href="/about")),
        ],
        brand=dbc.Button("TREC",
                         href=f"{dash.page_registry['pages.home']['path']}",
                         outline=True, color="primary", size="lg"),
        color="white",
        dark=False,
    ),
    dash.page_container
])
server = app.server

if __name__ == "__main__":
    app.run_server(debug=True)
```

- [ ] **Step 3: Commit**

```bash
git add fe/api_config.py fe/app.py
git commit -m "feat: add API config module and update navbar for redesigned portal"
```

---

### Task 6: Rewrite Data Portal Page — Map + Station Panel

**Files:**
- Modify: `fe/pages/data_portal.py`

This is the largest task. Replace the flat table view with the hybrid map + station panel layout. The page has:
- A global stats banner at top
- A search bar with collapsible filters panel
- An interactive map (left) with station markers
- An expedition timeline below the map
- A station detail panel (right) that appears when a station is clicked

- [ ] **Step 1: Replace `fe/pages/data_portal.py` entirely**

```python
import dash
import requests
import dash_bootstrap_components as dbc
from dash import callback, Output, Input, State, html, dcc
from api_config import API_BASE_URL

dash.register_page(
    __name__,
    path="/data",
    title="Data Portal",
)


def make_stats_banner():
    """Global stats banner — populated by callback on page load."""
    return html.Div(
        dbc.Row(
            id="stats-banner-row",
            className="g-0 justify-content-center",
            style={"padding": "12px 24px"},
        ),
        style={
            "background": "linear-gradient(135deg, #2c7a5c, #3da87a)",
            "color": "white",
        },
    )


def make_filters_panel():
    """Collapsible filters panel."""
    return dbc.Collapse(
        dbc.Card(
            dbc.CardBody(
                dbc.Row([
                    dbc.Col([
                        html.Label("Environment", className="fw-bold small"),
                        dbc.Checklist(id="env-type-filter", className="small"),
                    ], md=2),
                    dbc.Col([
                        html.Label("Organism", className="fw-bold small"),
                        dbc.Checklist(
                            id="organism-filter", className="small",
                            style={"maxHeight": "10em", "overflowY": "auto"}),
                    ], md=2),
                    dbc.Col([
                        html.Label("Analysis Type", className="fw-bold small"),
                        dbc.Checklist(
                            id="analysis-type-filter", className="small"),
                    ], md=2),
                    dbc.Col([
                        html.Label("Country", className="fw-bold small"),
                        dbc.Checklist(
                            id="country-filter", className="small",
                            style={"maxHeight": "10em", "overflowY": "auto"}),
                    ], md=2),
                    dbc.Col([
                        html.Label("Linked Data", className="fw-bold small"),
                        dbc.Checklist(
                            id="linked-data-filter",
                            options=[
                                {"label": "Has images", "value": "images"},
                                {"label": "Has sequences", "value": "ena"},
                            ],
                            className="small",
                        ),
                    ], md=2),
                    dbc.Col([
                        html.Label("Sample Type", className="fw-bold small"),
                        dbc.RadioItems(
                            id="source-filter",
                            options=[
                                {"label": "All", "value": "all"},
                                {"label": "Source only", "value": "source"},
                            ],
                            value="all",
                            className="small",
                        ),
                    ], md=2),
                ]),
            ),
            className="mb-2",
        ),
        id="filters-collapse",
        is_open=False,
    )


layout = dbc.Container([
    # Stats banner
    make_stats_banner(),
    # Search + filters
    dbc.Row(
        dbc.Col([
            dbc.InputGroup([
                dbc.Input(
                    id="search-input",
                    placeholder="Search samples, organisms, locations...",
                    type="text", debounce=True,
                ),
                dbc.Button("Filters ▾", id="filters-toggle",
                           outline=True, color="secondary", size="sm"),
            ], className="mb-2"),
            make_filters_panel(),
        ]),
        className="mt-3",
    ),
    # Map + Station panel
    dbc.Spinner(
        dbc.Row([
            # Map column
            dbc.Col([
                dcc.Graph(id="station-map", style={"height": "500px"}),
            ], md=7),
            # Station panel column
            dbc.Col(
                html.Div(
                    id="station-panel",
                    children=[
                        html.Div(
                            html.P("Click a station on the map to see details",
                                   className="text-muted text-center mt-5"),
                        )
                    ],
                    style={"maxHeight": "500px", "overflowY": "auto"},
                ),
                md=5,
            ),
        ]),
    ),
], fluid=True)


# --- Callbacks ---

@callback(
    Output("filters-collapse", "is_open"),
    Input("filters-toggle", "n_clicks"),
    State("filters-collapse", "is_open"),
    prevent_initial_call=True,
)
def toggle_filters(n_clicks, is_open):
    return not is_open


@callback(
    Output("stats-banner-row", "children"),
    Input("search-input", "id"),  # Trigger on page load
)
def load_stats(_):
    """Fetch global stats and render banner."""
    try:
        resp = requests.get(f"{API_BASE_URL}/stats").json()
    except Exception:
        return []
    stats = [
        ("Stations", resp.get("total_stations", 0)),
        ("Countries", resp.get("total_countries", 0)),
        ("Source Samples", f"~{resp.get('total_source_samples', 0):,}"),
        ("Total Samples", f"~{resp.get('total_samples', 0):,}"),
    ]
    return [
        dbc.Col(
            html.Div([
                html.Div(str(val), style={"fontSize": "28px",
                                          "fontWeight": "bold"}),
                html.Div(label, style={"fontSize": "12px", "opacity": "0.85"}),
            ], className="text-center"),
            width="auto",
            className="px-4",
        )
        for label, val in stats
    ]


@callback(
    Output("station-map", "figure"),
    Output("env-type-filter", "options"),
    Output("organism-filter", "options"),
    Output("analysis-type-filter", "options"),
    Output("country-filter", "options"),
    Input("search-input", "id"),  # Trigger on page load
)
def load_map_and_filters(_):
    """Fetch stations and build map + filter options."""
    import plotly.graph_objects as go

    try:
        stations_resp = requests.get(f"{API_BASE_URL}/stations").json()
    except Exception:
        stations_resp = {"stations": []}
    stations = stations_resp.get("stations", [])

    # Build map
    lats = [s["lat"] for s in stations]
    lons = [s["lon"] for s in stations]
    names = [s["station_name"] for s in stations]
    hover_texts = [
        f"{s['station_name']}<br>"
        f"{s['sample_count']} samples, {s['source_sample_count']} source<br>"
        f"Types: {', '.join(s['analysis_types'][:3])}"
        for s in stations
    ]
    sizes = [max(8, min(20, s["sample_count"] // 10)) for s in stations]

    fig = go.Figure(go.Scattermap(
        lat=lats, lon=lons,
        mode="markers",
        marker=dict(size=sizes, color="#2c7a5c", opacity=0.8),
        text=names,
        hovertext=hover_texts,
        hoverinfo="text",
        customdata=names,
    ))
    fig.update_layout(
        map=dict(style="open-street-map",
                 center=dict(lat=43, lon=10), zoom=3.5),
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
    )

    # Build filter options from aggregations
    # Collect unique values across all stations
    env_types = set()
    organisms = set()
    analysis_types = set()
    countries = set()
    for s in stations:
        if s.get("country"):
            countries.add(s["country"])
        for o in s.get("organism_types", []):
            organisms.add(o)
        for a in s.get("analysis_types", []):
            analysis_types.add(a)

    # Also fetch aggregations from the data_portal endpoint for counts
    try:
        agg_resp = requests.get(f"{API_BASE_URL}/data_portal",
                                params={"size": 0}).json()
        aggs = agg_resp.get("aggregations", {})
    except Exception:
        aggs = {}

    def make_options(agg_key):
        if agg_key in aggs:
            return [
                {"label": f"{b['key']} ({b['doc_count']})",
                 "value": b["key"]}
                for b in aggs[agg_key].get("buckets", [])
            ]
        return []

    return (
        fig,
        make_options("environment_type"),
        make_options("organism"),
        make_options("analysis_type"),
        make_options("country"),
    )


@callback(
    Output("station-panel", "children"),
    Input("station-map", "clickData"),
    prevent_initial_call=True,
)
def show_station_panel(click_data):
    """When a station marker is clicked, fetch and display station detail."""
    if not click_data or "points" not in click_data:
        return html.P("Click a station on the map to see details",
                       className="text-muted text-center mt-5")

    station_name = click_data["points"][0].get("customdata")
    if not station_name:
        station_name = click_data["points"][0].get("text", "")
    if not station_name:
        return html.P("Could not identify station",
                       className="text-muted text-center mt-5")

    try:
        detail = requests.get(
            f"{API_BASE_URL}/stations/{station_name}").json()
    except Exception as e:
        return html.P(f"Error loading station: {e}",
                       className="text-danger text-center mt-3")

    # Station header
    header = html.Div([
        html.H5(f"📍 {detail['station_name']}", className="mb-1"),
        html.Small(
            f"{detail['lat']:.4f}°N, {detail['lon']:.4f}°E"
            + (f" · {detail['country']}" if detail.get("country") else ""),
            className="text-muted",
        ),
    ], className="p-3", style={"background": "#f0f7f4",
                                "borderBottom": "1px solid #e0e0e0"})

    # Summary counts
    counts = dbc.Row([
        dbc.Col(html.Div([
            html.Div(str(detail["source_sample_count"]),
                     className="fw-bold fs-4 text-success"),
            html.Small("Source samples", className="text-muted"),
        ], className="text-center p-2 bg-light rounded"), md=6),
        dbc.Col(html.Div([
            html.Div(str(detail["sample_count"]),
                     className="fw-bold fs-4 text-success"),
            html.Small("Total samples", className="text-muted"),
        ], className="text-center p-2 bg-light rounded"), md=6),
    ], className="g-2 p-3")

    # Available analysis types badges
    type_badges = html.Div([
        html.Small("AVAILABLE DATA", className="text-muted d-block mb-2"),
        html.Div([
            dbc.Badge(t, color="success", className="me-1 mb-1")
            for t in detail.get("analysis_types", [])
        ]),
    ], className="px-3 pb-3")

    # Organism breakdown
    org_list = html.Div([
        html.Small("ORGANISMS", className="text-muted d-block mb-2"),
        *[
            html.Div([
                html.Span(org, className="small"),
                html.Span(f"{count}", className="small text-muted float-end"),
            ], className="mb-1")
            for org, count in detail.get("organism_counts", {}).items()
        ],
    ], className="px-3 pb-3")

    # Source samples accordion
    source_items = []
    for src in detail.get("source_samples", []):
        derived = src.get("derived_samples", [])
        derived_list = html.Div([
            html.Div([
                html.A(
                    d["biosampleId"],
                    href=f"/data-portal/{d['biosampleId']}",
                    className="text-decoration-none text-success small",
                ),
                html.Span([
                    dbc.Badge(d.get("analysis_type") or "?",
                              color="info", className="ms-2",
                              style={"fontSize": "10px"}),
                    dbc.Badge("🖼️", color="warning", className="ms-1",
                              style={"fontSize": "10px"})
                    if d.get("has_images") else None,
                ]),
            ], className="d-flex justify-content-between align-items-center "
                         "py-1 border-bottom")
            for d in derived
        ]) if derived else html.Small("No derived samples",
                                       className="text-muted")

        subtitle = " · ".join(filter(None, [
            src.get("collection_device"),
            f"{src['depth']} depth" if src.get("depth") else None,
            src.get("organism"),
        ]))

        source_items.append(dbc.AccordionItem(
            derived_list,
            title=html.Div([
                html.Span(src["biosampleId"], className="fw-bold small"),
                html.Br(),
                html.Small(subtitle, className="text-muted"),
            ]),
            item_id=src["biosampleId"],
        ))

    sources_section = html.Div([
        html.Small("SOURCE SAMPLES", className="text-muted d-block mb-2"),
        dbc.Accordion(source_items, flush=True, start_collapsed=True),
    ], className="px-3 pb-3") if source_items else html.Div()

    return html.Div([header, counts, type_badges, org_list, sources_section])
```

- [ ] **Step 2: Verify the page module loads**

Run: `cd /Users/alexey/TREC/fe && python -c "from pages import data_portal; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add fe/pages/data_portal.py
git commit -m "feat: rewrite data portal with hybrid map + station panel layout"
```

---

### Task 7: Rewrite Sample Detail Page

**Files:**
- Modify: `fe/pages/data_portal_details.py`

Replace the current flat metadata view with the two-column layout: metadata + environmental context on the left, linked data + map on the right. Add breadcrumb navigation and sibling sample links.

- [ ] **Step 1: Replace `fe/pages/data_portal_details.py` entirely**

```python
import requests
import dash
import plotly.express as px
import pandas as pd
import dash_bootstrap_components as dbc
from dash import callback, html, Output, Input, dcc
from api_config import API_BASE_URL

dash.register_page(
    __name__,
    path_template="/data-portal/<sample_id>",
    title="Sample Details",
)

BIONGFF_VIEWER_URL = "https://biongff.github.io/biongff-viewer/"


def layout(sample_id=None, **kwargs):
    return dbc.Container(
        dbc.Spinner(html.Div(id="detail-content", key=sample_id)),
        className="mt-3",
    )


def make_breadcrumb(sample, station_name, parent_id):
    """Build breadcrumb: Station > Source Sample > This Sample."""
    items = []
    if station_name:
        items.append(
            dbc.BreadcrumbItem(
                html.A(f"📍 {station_name}", href="/data",
                       className="text-decoration-none")))
    if parent_id:
        items.append(
            dbc.BreadcrumbItem(
                html.A(parent_id,
                       href=f"/data-portal/{parent_id}",
                       className="text-decoration-none")))
    items.append(
        dbc.BreadcrumbItem(sample["biosampleId"], active=True))
    return dbc.Breadcrumb(items=[], id="bc-placeholder",
                          children=html.Ol(
                              [html.Li(item, className="breadcrumb-item")
                               for item in items],
                              className="breadcrumb"))


def make_metadata_table(label, rows):
    """Build a labeled metadata table."""
    return html.Div([
        html.Small(label, className="text-muted d-block mb-2 fw-bold"),
        dbc.Table([
            html.Tbody([
                html.Tr([
                    html.Td(k, className="text-muted",
                            style={"width": "160px", "fontSize": "13px"}),
                    html.Td(v, style={"fontSize": "13px"}),
                ])
                for k, v in rows if v
            ])
        ], borderless=True, size="sm"),
    ], className="mb-3")


def get_field(custom_fields, name):
    """Extract a value from customFields by name."""
    if not custom_fields:
        return None
    for f in custom_fields:
        if f.get("name", "").lower() == name.lower():
            val = f.get("value", "").strip()
            if val and val.lower() not in ("not provided", "not applicable"):
                return val
    return None


@callback(
    Output("detail-content", "children"),
    Input("detail-content", "key"),
)
def build_detail_page(sample_id):
    if not sample_id:
        return html.P("No sample ID provided", className="text-danger")

    try:
        resp = requests.get(
            f"{API_BASE_URL}/data_portal/{sample_id}").json()
    except Exception as e:
        return html.P(f"Error: {e}", className="text-danger")

    if not resp.get("results"):
        return html.P("Sample not found", className="text-danger")

    sample = resp["results"][0]
    cf = sample.get("customFields") or []

    parent_id = sample.get("parent_sample_id")
    station_name = sample.get("station_name")
    is_source = sample.get("is_source_sample", False)

    # --- Breadcrumb ---
    breadcrumb = make_breadcrumb(sample, station_name, parent_id)

    # --- Sample identity ---
    badges = []
    if sample.get("analysis_type"):
        badges.append(dbc.Badge(sample["analysis_type"], color="success",
                                className="me-1"))
    protocol = get_field(cf, "protocol label")
    if protocol:
        badges.append(dbc.Badge(f"{protocol} protocol", color="info",
                                className="me-1"))
    if is_source:
        badges.append(dbc.Badge("Source sample", color="secondary",
                                className="me-1"))

    identity = html.Div([
        html.H4(sample["biosampleId"], className="mb-1"),
        html.Div(badges, className="mb-2"),
        html.Small([
            "Derived from ",
            html.A(parent_id, href=f"/data-portal/{parent_id}",
                   className="text-decoration-none text-success"),
        ], className="text-muted") if parent_id else None,
    ], className="mb-3")

    # --- Environmental context ---
    biome = sample.get("biome") or get_field(cf,
                                              "broad-scale environmental "
                                              "context")
    local_env = sample.get("local_environment") or get_field(
        cf, "local environmental context")
    medium = sample.get("environmental_medium") or get_field(
        cf, "environmental medium")
    size_lower = sample.get("size_fraction_lower")
    size_upper = sample.get("size_fraction_upper")
    size_str = None
    if size_lower is not None and size_upper is not None:
        size_str = f"{size_lower}–{size_upper} µm"
    elif size_lower is not None:
        size_str = f"≥{size_lower} µm"

    env_table = make_metadata_table("ENVIRONMENTAL CONTEXT", [
        ("Organism", sample.get("organism")),
        ("Biome", biome),
        ("Local environment", local_env),
        ("Medium", medium),
        ("Environment type", sample.get("environment_type")),
        ("Size fraction", size_str),
    ])

    # --- Collection details ---
    date_str = sample.get("collection_date")
    if date_str:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            date_str = dt.strftime("%d %B %Y, %H:%M UTC")
        except (ValueError, AttributeError):
            pass

    collection_table = make_metadata_table("COLLECTION", [
        ("Date", date_str),
        ("Location", f"{sample.get('lat', '')}°N, {sample.get('lon', '')}°E"
         if sample.get("lat") else None),
        ("Depth", sample.get("depth")),
        ("Altitude", sample.get("altitude")),
        ("Collection device", sample.get("collection_device")
         or get_field(cf, "collection device")),
        ("Platform", sample.get("sampling_platform")
         or get_field(cf, "sampling platform")),
    ])

    # --- Sibling samples ---
    siblings_section = html.Div()
    if parent_id:
        try:
            parent_resp = requests.get(
                f"{API_BASE_URL}/data_portal/{parent_id}").json()
            if parent_resp.get("results"):
                parent = parent_resp["results"][0]
                derived_ids = parent.get("derived_sample_ids") or []
                sibling_ids = [sid for sid in derived_ids
                               if sid != sample["biosampleId"]]
                if sibling_ids:
                    # Fetch sibling analysis types
                    sibling_badges = []
                    for sid in sibling_ids[:10]:
                        try:
                            sib_resp = requests.get(
                                f"{API_BASE_URL}/data_portal/{sid}").json()
                            if sib_resp.get("results"):
                                sib = sib_resp["results"][0]
                                at = sib.get("analysis_type") or "?"
                                sibling_badges.append(
                                    html.A(
                                        [html.Span(sid),
                                         html.Small(f" {at}",
                                                    className="text-muted")],
                                        href=f"/data-portal/{sid}",
                                        className="text-decoration-none "
                                                  "text-success border "
                                                  "rounded px-2 py-1 me-1 "
                                                  "mb-1 d-inline-block small",
                                    ))
                        except Exception:
                            sibling_badges.append(
                                html.A(sid, href=f"/data-portal/{sid}",
                                       className="text-decoration-none "
                                                 "text-success small me-2"))

                    siblings_section = html.Div([
                        html.Small("SIBLING SAMPLES (same source)",
                                   className="text-muted d-block mb-2 "
                                             "fw-bold"),
                        html.Div(sibling_badges),
                    ], className="mb-3")
        except Exception:
            pass

    # --- Left column ---
    left_col = dbc.Col([identity, env_table, collection_table,
                        siblings_section], md=7)

    # --- Right column: map + linked data ---

    # Mini map
    map_section = html.Div()
    if sample.get("lat") and sample.get("lon"):
        df = pd.DataFrame([{"lat": sample["lat"], "lon": sample["lon"]}])
        fig = px.scatter_map(df, lat="lat", lon="lon", zoom=9)
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=180)
        map_section = dcc.Graph(figure=fig, config={"scrollZoom": False},
                                style={"marginBottom": "16px"})

    # Linked data cards
    linked_cards = []

    # BioSamples link
    linked_cards.append(dbc.Card(dbc.CardBody(dbc.Row([
        dbc.Col([
            html.Div("BioSamples", className="fw-bold small"),
            html.Small("Original record at EBI", className="text-muted"),
        ]),
        dbc.Col(
            dbc.Button("View →", color="success", size="sm",
                       href=f"https://www.ebi.ac.uk/biosamples/samples/"
                            f"{sample['biosampleId']}",
                       external_link=True, target="_blank"),
            width="auto", className="d-flex align-items-center",
        ),
    ])), className="mb-2"))

    # BioImage Archive
    if sample.get("has_images") and sample.get("image_zarr_url"):
        viewer_url = (f"{BIONGFF_VIEWER_URL}?source="
                      f"{sample['image_zarr_url']}")
        linked_cards.append(dbc.Card(dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Div("🖼️ BioImage Archive", className="fw-bold small"),
                    html.Small("Microscopy images available",
                               className="text-muted"),
                ]),
                dbc.Col(
                    dbc.Button("Open viewer →", color="success", size="sm",
                               href=viewer_url, external_link=True,
                               target="_blank"),
                    width="auto", className="d-flex align-items-center",
                ),
            ]),
            html.Iframe(
                src=viewer_url,
                style={"width": "100%", "height": "160px", "border": "none",
                       "borderRadius": "4px", "marginTop": "10px",
                       "background": "#1a1a2e"},
            ),
        ]), className="mb-2", style={"background": "#fffdf0"}))
    elif sample.get("has_images"):
        linked_cards.append(dbc.Card(dbc.CardBody(dbc.Row([
            dbc.Col([
                html.Div("🖼️ BioImage Archive", className="fw-bold small"),
                html.Small("Images available", className="text-muted"),
            ]),
        ])), className="mb-2"))

    # ENA
    ena_accession = sample.get("ena_accession")
    if sample.get("has_ena_data") and ena_accession:
        linked_cards.append(dbc.Card(dbc.CardBody(dbc.Row([
            dbc.Col([
                html.Div("ENA", className="fw-bold small"),
                html.Small("Sequence data", className="text-muted"),
            ]),
            dbc.Col(
                dbc.Button("View →", color="success", size="sm",
                           href=f"https://www.ebi.ac.uk/ena/browser/view/"
                                f"{ena_accession}",
                           external_link=True, target="_blank"),
                width="auto", className="d-flex align-items-center",
            ),
        ])), className="mb-2"))
    else:
        linked_cards.append(dbc.Card(dbc.CardBody(dbc.Row([
            dbc.Col([
                html.Div("ENA", className="fw-bold small"),
                html.Small("Sequence data (coming soon)",
                           className="text-muted"),
            ]),
            dbc.Col(
                dbc.Badge("Pending", color="secondary"),
                width="auto", className="d-flex align-items-center",
            ),
        ])), className="mb-2"))

    # QC control relationship
    control_id = sample.get("control_sample_id")
    controlled_ids = sample.get("controlled_sample_ids") or []
    if control_id or controlled_ids:
        qc_content = []
        if control_id:
            qc_content.append(html.Div([
                html.Small("Control: ", className="text-muted"),
                html.A(control_id, href=f"/data-portal/{control_id}",
                       className="text-decoration-none text-success small"),
            ]))
        if controlled_ids:
            qc_content.append(html.Div([
                html.Small("Is control of: ", className="text-muted"),
                *[html.A(cid, href=f"/data-portal/{cid}",
                         className="text-decoration-none text-success "
                                   "small me-1")
                  for cid in controlled_ids],
            ]))
        linked_cards.append(dbc.Card(dbc.CardBody([
            html.Div("Quality Control", className="fw-bold small mb-1"),
            *qc_content,
        ]), className="mb-2"))

    right_col = dbc.Col([
        html.Div([
            html.Small("LINKED DATA",
                       className="text-muted d-block mb-2 fw-bold"),
            map_section,
            *linked_cards,
        ]),
    ], md=5)

    return html.Div([breadcrumb, dbc.Row([left_col, right_col])])
```

- [ ] **Step 2: Verify the module loads**

Run: `cd /Users/alexey/TREC/fe && python -c "from pages import data_portal_details; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add fe/pages/data_portal_details.py
git commit -m "feat: rewrite sample detail page with breadcrumbs, environmental context, and linked data"
```

---

### Task 8: Create Availability Matrix Page

**Files:**
- Create: `fe/pages/availability.py`

A new page at `/availability` showing a grid of stations (rows) vs data types (columns) with sample counts.

- [ ] **Step 1: Create `fe/pages/availability.py`**

```python
import dash
import requests
import dash_bootstrap_components as dbc
from dash import callback, Output, Input, html
from api_config import API_BASE_URL

dash.register_page(
    __name__,
    path="/availability",
    title="Data Availability",
)

ANALYSIS_TYPES = ["Metagenomics", "Metabolomics", "Imaging", "Ions"]


layout = dbc.Container([
    html.H3("Data Availability Across Stations", className="mt-3 mb-1"),
    html.P("Which data types are available at each sampling station",
           className="text-muted mb-3"),
    dbc.Spinner(html.Div(id="availability-matrix")),
], fluid=True)


@callback(
    Output("availability-matrix", "children"),
    Input("availability-matrix", "id"),
)
def build_matrix(_):
    try:
        resp = requests.get(f"{API_BASE_URL}/stations").json()
    except Exception as e:
        return html.P(f"Error loading stations: {e}",
                       className="text-danger")

    stations = resp.get("stations", [])
    if not stations:
        return html.P("No stations found", className="text-muted")

    # Sort stations by country then name
    stations.sort(key=lambda s: (s.get("country") or "", s["station_name"]))

    # Build table header
    header = html.Thead(html.Tr([
        html.Th("Station", style={"textAlign": "left"}),
        *[html.Th(at, className="text-center", style={"fontSize": "13px"})
          for at in ANALYSIS_TYPES],
        html.Th("ENA", className="text-center", style={"fontSize": "13px"}),
        html.Th("Images", className="text-center",
                style={"fontSize": "13px"}),
    ]))

    # Build rows
    rows = []
    for station in stations:
        available_types = set(station.get("analysis_types", []))
        cells = [
            html.Td(
                html.A(station["station_name"], href="/data",
                       className="text-decoration-none text-success"),
                style={"fontSize": "13px"},
            ),
        ]
        for at in ANALYSIS_TYPES:
            if at in available_types:
                cells.append(html.Td(
                    dbc.Badge("✓", color="success",
                              style={"fontSize": "11px"}),
                    className="text-center",
                ))
            else:
                cells.append(html.Td(
                    html.Span("—", className="text-muted",
                              style={"fontSize": "11px"}),
                    className="text-center",
                ))

        # ENA column
        if station.get("has_ena_data"):
            cells.append(html.Td(
                dbc.Badge("✓", color="success", style={"fontSize": "11px"}),
                className="text-center"))
        else:
            cells.append(html.Td(
                html.Span("—", className="text-muted",
                           style={"fontSize": "11px"}),
                className="text-center"))

        # Images column
        if station.get("has_images"):
            cells.append(html.Td(
                dbc.Badge("✓", color="success", style={"fontSize": "11px"}),
                className="text-center"))
        else:
            cells.append(html.Td(
                html.Span("—", className="text-muted",
                           style={"fontSize": "11px"}),
                className="text-center"))

        rows.append(html.Tr(cells))

    body = html.Tbody(rows)

    legend = html.Div([
        html.Span([
            dbc.Badge("✓", color="success",
                      style={"fontSize": "10px"}),
            " Available",
        ], className="me-3 small"),
        html.Span([
            html.Span("—", className="text-muted"),
            " Not available",
        ], className="small"),
    ], className="mt-2 mb-3")

    return html.Div([
        dbc.Table([header, body], striped=True, hover=True, responsive=True,
                  bordered=True, size="sm"),
        legend,
    ])
```

- [ ] **Step 2: Verify the module loads**

Run: `cd /Users/alexey/TREC/fe && python -c "from pages import availability; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add fe/pages/availability.py
git commit -m "feat: add dataset availability matrix page"
```

---

### Task 9: Update Home Page and Clean Up

**Files:**
- Modify: `fe/pages/home.py`
- Delete: `fe/pages/sampling_map.py` (map is now integrated into data portal)

Update the home page cards to reflect the new portal structure. Remove the standalone sampling map page since the map is now part of the data portal.

- [ ] **Step 1: Update `fe/pages/home.py`**

Replace the card functions and layout (keeping the banner unchanged):

```python
import dash
import dash_bootstrap_components as dbc
from dash import html

dash.register_page(
    __name__,
    title="Home",
    path="/"
)

BACKGROUND_URL = (
    "https://www.embl.org/about/info/trec/wp-content/uploads/2022/02/"
    "TREC-web-banner.jpg")

banner = html.Div(
    dbc.Container(
        dbc.Row(
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.H1("TREC Data Portal", className="display-3",
                                    style={"textAlign": "center"}),
                            html.H2("Traversing European Coastlines",
                                    style={"textAlign": "center"}),
                            html.H4(
                                "An expedition to study coastal ecosystems "
                                "and their response to the environment, from "
                                "molecules to communities",
                                style={"textAlign": "center"}),
                        ]
                    ),
                    color="light",
                ),
                style={"marginTop": "2em"},
            )
        )
    ),
    style={
        'backgroundImage': f'url({BACKGROUND_URL})',
        'backgroundPosition': 'center',
        'backgroundRepeat': 'no-repeat',
        'background-size': 'cover',
        'height': '20em',
    }
)

layout = html.Div([
    banner,
    dbc.Container([
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.H4("Data Portal", className="card-title"),
                    html.P("Explore TREC sampling stations on an interactive "
                           "map, search and filter samples by environment, "
                           "organism, and analysis type.",
                           className="card-text"),
                ]),
                dbc.CardFooter(dbc.Button(
                    "Explore Data", color="primary", href="/data")),
            ]), md=4, style={"marginTop": "1em"}),
            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.H4("Data Availability", className="card-title"),
                    html.P("See which data types are available at each "
                           "station — metagenomics, metabolomics, imaging, "
                           "and more.",
                           className="card-text"),
                ]),
                dbc.CardFooter(dbc.Button(
                    "View Availability", color="primary",
                    href="/availability")),
            ]), md=4, style={"marginTop": "1em"}),
            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.H4("API Documentation", className="card-title"),
                    html.P("Access TREC data programmatically through our "
                           "REST API.",
                           className="card-text"),
                ]),
                dbc.CardFooter(dbc.Button(
                    "API Documentation", color="primary", href="/api")),
            ]), md=4, style={"marginTop": "1em"}),
        ], style={"marginBottom": "1em", "marginTop": "2em"}),
        dbc.Row(
            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.H4("About", className="card-title"),
                    html.P("Learn about the TREC expedition and its mission "
                           "to explore coastal ecosystems across Europe.",
                           className="card-text"),
                ]),
                dbc.CardFooter(dbc.Button(
                    "About", color="primary", href="/about")),
            ]), md=4),
            style={"marginBottom": "2em"},
        ),
    ]),
])
```

- [ ] **Step 2: Remove the standalone sampling map page**

Delete `fe/pages/sampling_map.py` — the map is now part of the data portal page.

```bash
git rm fe/pages/sampling_map.py
```

Note: The `fe/pages/sampling_map.parquet` file can be kept for now (it's not imported by anything after this change) or removed if no longer needed.

- [ ] **Step 3: Verify the frontend loads**

Run: `cd /Users/alexey/TREC/fe && python -c "from pages import home; print('OK')"`

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add fe/pages/home.py
git commit -m "feat: update home page cards and remove standalone sampling map page"
```

---

### Task 10: Add .superpowers to .gitignore and Final Verification

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Add `.superpowers/` to `.gitignore`**

Append to the end of `.gitignore`:

```
# Superpowers brainstorming
.superpowers/
```

- [ ] **Step 2: Run a full import check on both backend and frontend**

Backend:
```bash
cd /Users/alexey/TREC/be && python -c "
from models import (TRECData, TRECAggregationResponse, TRECSearchParams,
                    StationSummary, StationListResponse, StationDetailResponse,
                    GlobalStats)
from main import app
routes = [r.path for r in app.routes if not r.path.startswith('/openapi')]
print('Backend routes:', sorted(routes))
print('Backend OK')
"
```

Expected: Routes include `/data_portal`, `/data_portal/{record_id}`, `/stations`, `/stations/{station_name}`, `/stats`

Frontend:
```bash
cd /Users/alexey/TREC/fe && python -c "
from pages import home, data_portal, data_portal_details, availability, api, about
print('Frontend OK')
"
```

Expected: `Frontend OK`

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: add .superpowers to gitignore"
```

---

## Post-Implementation Notes

### Running the enrichment script

Before the new portal will work, the enrichment script must be run against the Elasticsearch index:

```bash
cd /Users/alexey/TREC/be
ES_URL=<url> ES_USERNAME=<user> ES_PASSWORD=<pass> python enrich.py
```

This is idempotent and can be re-run safely.

### Elasticsearch mapping considerations

The new fields (`environment_type`, `analysis_type`, `country`, `station_name`, `is_source_sample`, `parent_sample_id`, `derived_sample_ids`, `has_images`, `has_ena_data`, etc.) will be auto-mapped by Elasticsearch when the enrichment script writes them. For aggregations on text fields to work, ES must map them as `keyword` type. If ES auto-maps them as `text`, you may need to add explicit mappings:

```bash
PUT /data_portal/_mapping
{
  "properties": {
    "environment_type": {"type": "keyword"},
    "analysis_type": {"type": "keyword"},
    "country": {"type": "keyword"},
    "station_name": {"type": "keyword"},
    "parent_sample_id": {"type": "keyword"},
    "is_source_sample": {"type": "boolean"},
    "has_images": {"type": "boolean"},
    "has_ena_data": {"type": "boolean"}
  }
}
```

Run this mapping update BEFORE the enrichment script if the index already exists.

### BioImage Archive integration

The `has_images` and `image_zarr_url` fields default to `false`/`null` in the enrichment script. To populate them, you'll need a separate step that cross-references TREC sample IDs with BioImage Archive records and updates the ES index. This is outside the scope of this plan but the data model is ready for it.

### ENA integration

Similarly, `has_ena_data` and `ena_accession` default to `false`/`null`. When ENA data becomes public, update these fields in ES.

### Not yet implemented (follow-up iterations)

These spec features are deferred to keep the initial build focused:

- **Expedition timeline** — the spec calls for a visual timeline below the map showing when each station was sampled. The data is available (`min_collection_date`/`max_collection_date` on stations). Implementation would be a Plotly timeline/scatter chart acting as a time-range filter.
- **Filter → map wiring** — the filters UI is built and the data to power it exists, but changing filter values doesn't yet re-filter which stations appear on the map. Next step: add a callback that filters stations client-side based on their `analysis_types`, `organism_types`, `country`, `has_images`, `has_ena_data` attributes.
- **Depth range filter** — the spec mentions a numeric depth range filter. The current generic ES filter mechanism uses `terms` queries (exact match), not `range` queries. Implementing this requires a custom query path in `elastic_search()`.
