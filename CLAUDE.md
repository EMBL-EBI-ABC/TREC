# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TREC (Traversing European Coastlines) is a data portal for exploring coastal ecosystem samples. It consists of two independent Python applications:

- **`be/`** - FastAPI backend serving search/detail APIs over Elasticsearch
- **`fe/`** - Dash (Plotly) frontend with interactive data browsing and map visualization

## Development Commands

### Backend
```bash
cd be
pip install -r requirements.txt
# Requires ES_URL, ES_USERNAME, ES_PASSWORD env vars
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

### Frontend
```bash
cd fe
pip install -r requirements.txt
python app.py  # Dev server on http://localhost:8050
```

### Docker
```bash
# Backend
cd be && docker build -t trec-backend . && docker run -e ES_URL=<url> -e ES_USERNAME=<user> -e ES_PASSWORD=<pass> -p 8080:8080 trec-backend

# Frontend
cd fe && docker build -t trec-frontend . && docker run -p 80:80 trec-frontend
```

### No test suite or linter is configured.

## Architecture

### Backend (`be/`)

Two files: `models.py` defines the data model, `main.py` has routes and search logic.

**DataSource pattern** (`models.py`): A generic `DataSource` class takes a list of `FieldDefinition`s and generates three Pydantic classes via `generate_classes()`:
- `Data` - response schema
- `AggregationResponse` - faceted search buckets (only for fields with `filterable=True`)
- `SearchParamsExtended` - query parameters including filter fields

The TREC datasource has filterable fields: `organism`, `depth`, `altitude`, `location`. Non-filterable: `collection_date`, `lat`, `lon`, `biosampleId`, `customFields`, `relationships`.

**Search logic** (`main.py`): Two generic async functions handle all Elasticsearch queries:
- `elastic_search()` - full-text multi-match with fuzzy matching, filter terms, aggregations, pagination (`start`/`size`), and sorting
- `elastic_details()` - single record lookup by ID with special colon-handling for BioSample IDs

**Endpoints**: `GET /data_portal` (search) and `GET /data_portal/{record_id}` (details).

### Frontend (`fe/`)

Dash multi-page app using `use_pages=True`. Pages live in `fe/pages/`:
- `home.py` - landing page
- `data_portal.py` - search interface with sidebar filters + paginated table (20 items/page)
- `data_portal_details.py` - individual sample view with map and relationships table
- `sampling_map.py` - interactive Plotly scatter map, reads from local `sampling_map.parquet`
- `api.py` - embeds backend ReDoc docs in iframe
- `about.py` - project info

The frontend calls the backend API directly via `requests.get()`. The backend URL is hardcoded to the production Cloud Run deployment: `https://trec-be-868757013548.europe-west2.run.app`.

### Key Libraries
- **Backend**: FastAPI, AsyncElasticsearch, Pydantic, Uvicorn
- **Frontend**: Dash (<3.0.0), Dash Bootstrap Components (Minty theme), Plotly, Pandas, Gunicorn
- **Python 3.12** for both

## Environment Variables (Backend)

| Variable | Purpose |
|----------|---------|
| `ES_URL` | Elasticsearch server URL |
| `ES_USERNAME` | Elasticsearch username |
| `ES_PASSWORD` | Elasticsearch password |
