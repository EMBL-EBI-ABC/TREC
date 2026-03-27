# TREC Data Portal Redesign — Design Spec

## Problem

The current TREC data portal presents ~10,000 BioSamples as a flat table with four text filters (organism, depth, altitude, location). This hides the rich structure in the data:

- **Parent-child sample hierarchy** — source samples (a net tow, soil core, air sample) produce multiple derived samples processed with different protocols (MetaBGT, Metabolomics, Imaging, Ions)
- **Environmental context** — ontology-coded biome, local environment, and medium are buried in custom fields
- **Control relationships** — QC control/experiment links between samples are invisible
- **Linked datasets** — images in BioImage Archive (viewable via biongff-viewer) and future sequence data in ENA have no presence in the portal
- **Geographic/temporal narrative** — the expedition traversed European coastlines over months, but this journey isn't visible

## Audience

Two primary user groups:

1. **Data consumers** — researchers looking to find and access linked datasets (ENA sequences, BioImage Archive images) for specific sample types, locations, or protocols
2. **Project stakeholders / general public** — exploring what TREC collected, where, and what data is available

## Design

### Main Portal View: Hybrid Map + Station Panel

The portal's primary view is a single-page layout with three horizontal layers:

**1. Global Stats Banner**

A top bar showing key expedition metrics: total stations visited, countries covered, source samples, total samples, and number of linked data archives. These numbers are computed as Elasticsearch aggregations on page load.

**2. Map + Search (left side)**

An interactive map of European coastlines with sampling stations as clickable markers. Stations are clustered/colored by density or data availability. Below the map, an expedition timeline shows when each station was sampled, providing temporal context and acting as a time-range filter.

Above the map, a search bar with a collapsible filters panel:
- **Free text search** — full-text across all sample fields
- **Environment type** — marine, soil, aerosol (derived from the `broad-scale environmental context` ontology field)
- **Organism** — marine metagenome, soil metagenome, marine plankton, etc.
- **Analysis type** — Metagenomics, Metabolomics, Imaging, Ions (derived from `protocol label` / `target analysis type` fields)
- **Depth range** — numeric range filter
- **Country** — derived from the `geographic location` field
- **Has linked data** — filter to samples with BioImage Archive images or ENA sequences

Filters display as pill-style chips with document counts from Elasticsearch aggregations. Applied filters appear as dismissible chips above the results. Selecting filters updates both the map markers and the station panel.

**3. Station Detail Panel (right side)**

When a station is clicked on the map (or selected via search results), a detail panel appears on the right showing:

- **Station header** — location name, coordinates, collection date(s)
- **Summary counts** — source samples and total samples at this station
- **Available data types** — badges showing which protocols/analysis types are present (green = available, grey = coming soon)
- **Organism breakdown** — counts by organism type
- **Source samples list** — expandable accordion of source samples, each showing:
  - Source sample ID, collection device, depth/altitude, organism
  - Derived sample count
  - When expanded: list of derived samples with protocol badge and image indicator (if BioImage Archive link exists)

### Sample Detail View

Clicking a sample ID (source or derived) navigates to a full detail page with:

**Breadcrumb navigation:** Station > Source Sample > This Sample

**Left column — Metadata:**
- Sample ID with protocol and analysis type badges
- "Derived from" link to parent source sample (for derived samples)
- Environmental context table: organism, biome, local environment, medium, size fraction — showing human-readable ontology terms with codes displayed subtly
- Collection details: date/time, coordinates, depth, collection device, platform
- Sibling samples: quick-links to other derived samples from the same source, labeled by protocol

**Right column — Linked Data + Location:**
- Mini map showing the sample's location
- Linked data cards:
  - **BioSamples** — link to the original EBI BioSamples record
  - **BioImage Archive** — when images are available, shows an inline preview rendered via biongff-viewer (embedded as iframe with `?source=[ZARR_URL]`), plus an "Open viewer" button for the full viewer. The biongff-viewer URL is constructed from the sample's BioImage Archive accession.
  - **ENA** — link to sequence data when available, greyed out with "coming soon" when pending
  - **Quality Control** — link to the control sample (if the `has control` / `is control of` relationship exists)

### Dataset Availability Matrix

A dedicated view (accessible from navigation or a tab) showing a grid of stations (rows) vs data types (columns: Metagenomics, Metabolomics, Imaging, Ions, ENA). Cells contain sample counts where data exists, or a grey indicator where data is unavailable or pending. Station names link to the map/station panel view. Cell counts are clickable to filter to those specific samples.

This view answers the data consumer question: "which stations have imaging data?" or "where is metabolomics available?"

## Data Model Changes

### Backend: New Fields and Indexing

The current Elasticsearch index stores flat sample records. The redesign requires:

1. **Enrich sample records with parsed custom fields:**
   - `environment_type` — parsed from `broad-scale environmental context` (marine/soil/aerosol)
   - `analysis_type` — parsed from `target analysis type` or `protocol label` (Metagenomics, Metabolomics, Imaging, Ions)
   - `country` — parsed from `geographic location` field
   - `size_fraction_lower` / `size_fraction_upper` — numeric fields parsed from size fraction strings
   - `biome`, `local_environment`, `environmental_medium` — parsed from ontology-coded custom fields
   - `collection_device`, `sampling_platform` — promoted from custom fields to top-level

2. **Index parent-child relationships:**
   - `parent_sample_id` — the source sample this was derived from (from `derived from` relationship)
   - `is_source_sample` — boolean flag for source vs derived samples
   - `derived_sample_ids` — array of child sample IDs (on source samples)
   - `control_sample_id` / `controlled_sample_ids` — QC relationship links

3. **Linked data availability flags:**
   - `has_images` — boolean, true if linked to BioImage Archive
   - `image_zarr_url` — the Zarr URL for biongff-viewer (when available)
   - `has_ena_data` — boolean, true if linked to ENA
   - `ena_accession` — ENA accession when available

4. **Station-level aggregation:**
   - `station_name` — a human-readable station identifier (e.g., "Athens, Greece") derived from the existing `location` field (which already contains geographic location names like "Spain", "Greece:Athens"). Samples at the same coordinates or within a small radius share a station.
   - This enables grouping samples by station for the station panel and availability matrix

### Backend: New API Endpoints

- `GET /stations` — returns list of stations with summary aggregations (sample counts, available data types, coordinates). Used for map markers and availability matrix.
- `GET /stations/{station_id}` — returns station detail with source samples, aggregation breakdowns. Used for station panel.
- `GET /data_portal` — enhanced with new filter parameters: `environment_type`, `analysis_type`, `country`, `has_images`, `has_ena_data`, `is_source_sample`. Keep existing `q`, `start`, `size`, `sort_field`, `sort_order`.
- `GET /data_portal/{record_id}` — enhanced response includes parsed environmental context, sibling samples, linked data URLs, and control relationships.

### Frontend: Technology

Keep Dash + Dash Bootstrap Components. The map uses Plotly's `scatter_map`. The station panel, filters, and sample detail views use Dash callbacks for reactivity. The biongff-viewer is embedded as an `html.Iframe` component.

## Pages

1. **Data Portal** (main view) — map + search + station panel as described above. This replaces the current `/data` page.
2. **Sample Detail** — `/data-portal/<sample_id>` — full sample detail view. Replaces current detail page.
3. **Availability Matrix** — `/availability` — stations vs data types grid.
4. **Home** — keep existing landing page, update cards to reflect new portal structure.
5. **API** — keep existing ReDoc iframe.
6. **About** — keep existing.

## Out of Scope

- Bulk data download or export functionality
- User accounts or saved searches
- Direct ENA data display (just link out when available)
- Image gallery/grid views (inline preview only for now)
- Custom biongff-viewer embedding beyond iframe
- Automated data ingestion pipeline (sample enrichment is a one-time indexing step for now)
