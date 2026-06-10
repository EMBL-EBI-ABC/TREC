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
from pathlib import Path
from dotenv import load_dotenv
from elasticsearch import Elasticsearch

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


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
        if "genom" in lower:
            return "Genomics"
    if protocol_label:
        label = protocol_label.strip()
        mapping = {
            "MetaBGT": "Metagenomics",
            "Metagenomics analysis": "Metagenomics",
            "Metabarcoding analysis": "Metagenomics",
            "MB": "Metabolomics",
            "MB320": "Metabolomics",
            "MB033": "Metabolomics",
            "MB20": "Metabolomics",
            "HPF": "Imaging",
            "PK1": "Imaging",
            "Microscopy": "Imaging",
            "Ions": "Ions",
            "ASM": "Metagenomics",
            "eDNA": "Metagenomics",
            "SML-023": "Genomics",
            "SML-CP": "Genomics",
            "SML-320": "Genomics",
            "Biodiversity analysis": "Metagenomics",
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
    The location field in the existing index is already just the country
    name (e.g. 'Spain', 'Italy', 'Greece')."""
    if not location_str:
        return None
    return location_str.strip()


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


def build_station_name(country, locality, lat, lon):
    """Build a human-readable station name.
    The location field is just the country (e.g. 'Spain'). The locality
    comes from the 'geographic location (region and locality)' custom field
    (e.g. 'Lesina', 'Ancona'). Many samples have empty locality, so we
    fall back to country + rounded coordinates to distinguish stations
    within the same country."""
    if locality and country:
        return f"{locality}, {country}"
    if country and lat is not None and lon is not None:
        # Round to ~1km precision to cluster nearby samples into one station
        return f"{country} ({lat:.2f}°N, {lon:.2f}°E)"
    if country:
        return country
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
    collection_device_raw = get_custom_field(cf, "sample collection device")
    sampling_platform = get_custom_field(cf, "sampling platform")
    size_lower = get_custom_field(cf, "size-fraction lower threshold")
    size_upper = get_custom_field(cf, "size-fraction upper threshold")
    locality = get_custom_field(
        cf, "geographic location (region and locality)")

    biome = parse_ontology_label(biome_raw)
    local_environment = parse_ontology_label(local_env_raw)
    collection_device = parse_ontology_label(collection_device_raw)
    environmental_medium = parse_ontology_label(medium_raw)

    organism = source.get("organism", "")
    env_type = parse_environment_type(biome_raw)
    if not env_type:
        env_type = parse_environment_type(organism)

    analysis_type = parse_analysis_type(target_analysis, protocol_label)
    country = parse_country(source.get("location"))
    station_name = build_station_name(
        country, locality, source.get("lat"), source.get("lon"))
    geo_location = None
    if source.get("lat") is not None and source.get("lon") is not None:
        geo_location = {"lat": source.get("lat"), "lon": source.get("lon")}

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
        "geo_location": geo_location,
        "is_source_sample": is_source_sample,
        "parent_sample_id": parent_sample_id,
        "control_sample_id": control_sample_id,
        "controlled_sample_ids": controlled_sample_ids or None,
        # Don't touch has_images — it already exists as "Yes"/"No" string
        # in the index. Only update when BioImage Archive links are known.
        "has_ena_data": False,
        "image_zarr_url": None,
        "ena_accession": None,
    }


def resolve_derived_sample_ids(es, index_name):
    """Second pass: for each source sample, find all samples that reference
    it as parent and store their IDs in derived_sample_ids.

    Uses scroll to fetch all derived samples in bulk, groups them by parent
    in memory, then bulk-updates all source samples at once."""
    print("Resolving derived_sample_ids for source samples...")

    # Step 1: Scroll through all derived samples (those with a parent)
    # and build a map: parent_id -> [child_id, child_id, ...]
    parent_to_children = {}
    resp = es.search(
        index=index_name,
        body={
            "query": {"exists": {"field": "parent_sample_id"}},
            "_source": ["biosampleId", "parent_sample_id"],
            "size": 500,
        },
        scroll="5m",
    )
    scroll_id = resp["_scroll_id"]
    count = 0

    while True:
        hits = resp["hits"]["hits"]
        if not hits:
            break
        for hit in hits:
            src = hit["_source"]
            parent = src.get("parent_sample_id")
            child = src.get("biosampleId")
            if parent and child:
                parent_to_children.setdefault(parent, []).append(child)
        count += len(hits)
        resp = es.scroll(scroll_id=scroll_id, scroll="5m")

    print(f"  Found {count} derived samples across "
          f"{len(parent_to_children)} parents")

    if not parent_to_children:
        print("  No parent-child relationships found")
        return

    # Step 2: Scroll through source samples to get their ES doc _ids
    # and build bulk update body
    bulk_body = []
    resp = es.search(
        index=index_name,
        body={
            "query": {"term": {"is_source_sample": True}},
            "_source": ["biosampleId"],
            "size": 500,
        },
        scroll="5m",
    )
    scroll_id = resp["_scroll_id"]

    while True:
        hits = resp["hits"]["hits"]
        if not hits:
            break
        for hit in hits:
            biosample_id = hit["_source"]["biosampleId"]
            children = parent_to_children.get(biosample_id)
            if children:
                bulk_body.append({"update": {"_index": index_name,
                                             "_id": hit["_id"]}})
                bulk_body.append({"doc": {"derived_sample_ids": children}})
        resp = es.scroll(scroll_id=scroll_id, scroll="5m")

    # Step 3: Bulk update
    if bulk_body:
        # Send in chunks of 1000 updates
        chunk_size = 2000  # 1000 update pairs
        for i in range(0, len(bulk_body), chunk_size):
            es.bulk(body=bulk_body[i:i + chunk_size], refresh=False)
        es.indices.refresh(index=index_name)
        print(f"  Updated {len(bulk_body) // 2} source samples with "
              f"derived_sample_ids")
    else:
        print("  No source samples had children to link")


def main():
    es = Elasticsearch(
        [os.getenv("ES_URL")],
        http_auth=(os.getenv("ES_USERNAME"), os.getenv("ES_PASSWORD")),
        verify_certs=True,
    )

    index_name = os.getenv("ES_INDEX", "data_portal_development_5")

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
