from typing import Optional, List, Literal
from pydantic import BaseModel, Field
import json
import re

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


def parse_model_json(raw_text: str) -> dict:
    """Strip markdown code fences and extract the first JSON object from raw text."""
    text = raw_text.strip()
    fence_match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("No JSON object found in model output")
    candidate = text[start:end + 1]
    return json.loads(candidate)