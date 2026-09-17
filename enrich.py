from typing import Optional, List, Literal
from pydantic import BaseModel, Field

Category = Literal["fiction", "non_fiction", "poetry", "childrens", "biography", "other"]
QualityFlag = Literal["missing_description", "missing_rating", "short_description", "price_anomaly"]


class EnrichRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    price_gbp: float
    availability_text: str = Field(..., min_length=1)
    rating_text: Optional[str] = None
    description: Optional[str] = Field(default=None, max_length=3000)


class EnrichResponse(BaseModel):
    category: Category
    summary: str
    quality_flags: List[QualityFlag] = []
    confidence: float = Field(..., ge=0.0, le=1.0)


STUB_RESPONSE = EnrichResponse(
    category="fiction",
    summary="A stubbed response returned without calling the model.",
    quality_flags=["missing_rating"],
    confidence=0.42,
)