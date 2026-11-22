from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ExtractedStartup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    description: str | None = None
    website: str | None = None
    industry: str | None = None
    headquarters: str | None = None
    founded_year: int | None = Field(
        default=None,
        ge=1800,
        le=2100,
    )


class ExtractedProduct(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    description: str | None = None
    website: str | None = None
    category: str | None = None
    pricing_model: str | None = None


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    quote: str
    source_url: str


class ExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_type: Literal["startup", "product", "unknown"]

    startup: ExtractedStartup | None = None
    product: ExtractedProduct | None = None

    evidence: list[EvidenceItem] = Field(default_factory=list)

    needs_review: bool = True