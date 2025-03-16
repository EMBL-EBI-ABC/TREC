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
    typ: str
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
    size: int = Field(10, gt=0, description="Number of results per page")
    # No sorting by default, child classes can override this.
    sort_field: str | None = None
    sort_order: Literal["desc", "asc"] = "asc"


# Datasource definition.


class FieldDefinition:
    def __init__(self, name: str, type: type|types.UnionType, filterable: bool = False):
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
        FieldDefinition(name="altitude", type=str, filterable=True),
        FieldDefinition(name="collection_date", type=datetime.datetime|None),
        FieldDefinition(name="depth", type=str, filterable=True),
        FieldDefinition(name="location", type=str, filterable=True),
        FieldDefinition(name="lat", type=float|None),
        FieldDefinition(name="lon", type=float|None),
        FieldDefinition(name="organism", type=str, filterable=True),
        FieldDefinition(name="biosampleId", type=str),
        FieldDefinition(name="customFields", type=list[CustomField]|None),
        FieldDefinition(name="relationships", type=list[BioSamplesRelationships]|None),
    ],
    default_sort_field="collection_date",
    default_sort_order="desc",
)
TRECData, TRECAggregationResponse, TRECSearchParams = trec.generate_classes()
