from pydantic import BaseModel, HttpUrl, field_validator
from typing import List, Dict, Optional, Any

from app.config import DEFAULT_TIER, MODEL_TIERS


class AnalyzeRequest(BaseModel):
    """Request model for URL analysis."""
    url: HttpUrl
    model: Optional[str] = DEFAULT_TIER

    @field_validator('model', mode='before')
    @classmethod
    def validate_model(cls, v):
        if not v:
            return DEFAULT_TIER
        if v not in MODEL_TIERS:
            return DEFAULT_TIER
        return v


class SchemaComponent(BaseModel):
    """Individual schema component (required field)."""
    name: str
    present: bool
    value: Optional[str] = None

    @field_validator('present', mode='before')
    @classmethod
    def validate_present(cls, v):
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return bool(v.strip())
        return bool(v)


class SchemaTypeInventory(BaseModel):
    type_name: str
    found: bool
    required_components: List[SchemaComponent]
    completeness_ratio: str
    status_message: str


class SchemaInventory(BaseModel):
    status: int
    types_found: List[SchemaTypeInventory]
    raw_jsonld: List[Dict[str, Any]]
    total_count: int


class GEORuleResult(BaseModel):
    rule_name: str
    score: float
    max_score: float
    passed: bool
    message: str
    details: Dict[str, Any]


class GEOScore(BaseModel):
    total_score: float
    max_score: float
    rules: List[GEORuleResult]


class ContentFreshness(BaseModel):
    status: str
    days_old: Optional[int] = None
    date_found: Optional[str] = None
    source_field: Optional[str] = None


class LlmsTxtStatus(BaseModel):
    status: str
    url: str
    content_length: Optional[int] = None


class Issue(BaseModel):
    severity: str
    title: str
    description: str


class AnalyzeResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    url: str
    schema_inventory: SchemaInventory
    geo_score: GEOScore
    content_freshness: ContentFreshness
    llms_txt: LlmsTxtStatus
    issues: List[Issue]
    current_jsonld: str
    improved_jsonld: str
    content_recommendations: List[str]
    all_content_recommendations: List[str] = []
    model_used: str
