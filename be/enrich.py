"""
One-time enrichment script for TREC data portal samples.

Reads all samples from the 'data_portal' ES index, parses customFields and
relationships into top-level queryable fields, resolves parent-child sample
hierarchies, and writes enriched data back.

Usage:
    python enrich.py

Reads ES_URL, ES_USERNAME, ES_PASSWORD from .env file or environment.

Idempotent: safe to re-run.
"""

import os
import re
from dotenv import load_dotenv
from elasticsearch import Elasticsearch

load_dotenv()


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
    if target_analysis:
        lower = target_analysis.lower()
        if "metabolom" in lower:
            return "Metabolomics"
        if "imag" in lower or "microscop" in lower:
            return "Imaging"
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

    resolve_derived_sample_ids(es, index_name)

    print("Enrichment complete!")


if __name__ == "__main__":
    main()
