import datetime
import types

from pydantic import BaseModel, Field
from typing import Generic, Literal, TypeVar

T = TypeVar("T")  # Datasource data type
A = TypeVar("A")  # Datasource aggregation type


# Generic aggregation classes.


class AggregationBucket(BaseModel):
    key: int | str
    doc_count: int


class Aggregation(BaseModel):
    doc_count_error_upper_bound: int
    sum_other_doc_count: int
    buckets: list[AggregationBucket]


class CustomField(BaseModel):
    name: str
    value: str
    unit: str


class BioSamplesRelationships(BaseModel):
    source: str
    type: str
    target: str


def get_list_of_aggregations(aggregation_class):
    return sorted(aggregation_class.schema()["properties"].keys())


# Generic Elastic response classes.


class ElasticResponse(BaseModel, Generic[T, A]):
    total: int
    start: int
    size: int
    results: list[T]
    aggregations: A


class ElasticDetailsResponse(BaseModel, Generic[T]):
    results: list[T]


# Base Elastic query class.

class SearchParams(BaseModel):
    model_config = {
        "populate_by_name": True,
        "extra": "forbid",
    }
    # Basic query parameters.
    q: str | None = Field(None, description="Search query string")
    start: int = Field(0, description="Starting point of the results")
    size: int = Field(10, ge=0, description="Number of results per page")
    # No sorting by default, child classes can override this.
    sort_field: str | None = None
    sort_order: Literal["desc", "asc"] = "asc"


# Datasource definition.


class FieldDefinition:
    def __init__(self, name: str, type: type | types.UnionType,
                 filterable: bool = False):
        self.name = name
        self.type = type
        self.filterable = filterable


class DataSource:
    def __init__(
            self,
            name: str,
            fields: list[FieldDefinition],
            default_sort_field: str,
            default_sort_order: Literal["desc", "asc"],
    ):
        self.name = name
        self.fields = fields
        self.default_sort_field = default_sort_field
        self.default_sort_order = default_sort_order

    def generate_classes(self):
        fields = {field.name: (field.type, field.filterable) for field in self.fields}

        class Data(BaseModel):
            __annotations__ = {name: type for name, (type, _) in fields.items()}

        class AggregationResponse(BaseModel):
            __annotations__ = {
                name: Aggregation
                for name, (_, filterable) in fields.items()
                if filterable
            }

        class SearchParamsExtended(SearchParams):
            # Define filterable fields with default values
            locals().update(
                {
                    name: Field(None, description=f"{name} query", alias=name)
                    for name, (type_, filterable) in fields.items()
                    if filterable
                }
            )
            __annotations__ = {
                name: type_ | None
                for name, (type_, filterable) in fields.items()
                if filterable
            }
            # Define default sort field and order.
            sort_field: str | None = Field(
                self.default_sort_field, description="Sort field"
            )
            sort_order: Literal["desc", "asc"] = Field(
                self.default_sort_order, description="Sort order"
            )

        return Data, AggregationResponse, SearchParamsExtended


# TREC.
trec = DataSource(
    name="TREC",
    fields=[
        # Original fields (already in ES index)
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
        FieldDefinition(name="images", type=str | None),
        FieldDefinition(name="has_images", type=str | None),
        FieldDefinition(name="collection_year", type=str | None),
        FieldDefinition(name="protocol", type=str | None),
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


class GlobalStats(BaseModel):
    total_stations: int
    total_countries: int
    total_source_samples: int
    total_samples: int
    total_with_images: int
    total_with_ena: int
