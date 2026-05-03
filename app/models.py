from pydantic import BaseModel, HttpUrl, field_validator
from typing import List, Dict, Optional, Any


class AnalyzeRequest(BaseModel):
    """Request model for URL analysis."""
    url: HttpUrl


class SchemaComponent(BaseModel):
    """Individual schema component (required field)."""
    name: str
    present: bool
    value: Optional[str] = None
    
    @field_validator('present', mode='before')
    @classmethod
    def validate_present(cls, v):
        """Convert any truthy value to boolean."""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return bool(v.strip())
        return bool(v)


class SchemaTypeInventory(BaseModel):
    """Inventory result for a single schema type."""
    type_name: str
    found: bool
    required_components: List[SchemaComponent]
    completeness_ratio: str
    status_message: str


class SchemaInventory(BaseModel):
    """Complete schema inventory for a page."""
    status: int  # 0 (none), 1 (some), or 2 (multiple) - NOT scored
    types_found: List[SchemaTypeInventory]
    raw_jsonld: List[Dict[str, Any]]
    total_count: int  # Total number of schema instances found


class GEORuleResult(BaseModel):
    """Result from evaluating a single GEO rule."""
    rule_name: str
    score: float
    max_score: float
    passed: bool
    message: str
    details: Dict[str, Any]


class GEOScore(BaseModel):
    """Complete GEO scoring result (0-100)."""
    total_score: float  # 0-100
    max_score: float    # 100.0
    rules: List[GEORuleResult]


class ContentFreshness(BaseModel):
    """Content freshness status based on dateModified/datePublished."""
    status: str  # 'Fresh', 'Aging', 'Stale', or 'Unknown'
    days_old: Optional[int] = None
    date_found: Optional[str] = None
    source_field: Optional[str] = None  # 'dateModified', 'datePublished', etc.


class LlmsTxtStatus(BaseModel):
    """Status of llms.txt file on the domain."""
    status: str  # 'Present' or 'Missing'
    url: str  # The llms.txt URL that was checked
    content_length: Optional[int] = None  # Length of content if present


class Issue(BaseModel):
    """Actionable issue identified by analysis."""
    severity: str  # high, medium, low
    title: str
    description: str


class AnalyzeResponse(BaseModel):
    """Complete analysis response."""
    url: str
    schema_inventory: SchemaInventory
    geo_score: GEOScore
    content_freshness: ContentFreshness  # Bonus signal, separate from GEO score
    llms_txt: LlmsTxtStatus  # Bonus signal for llms.txt detection
    issues: List[Issue]
    current_jsonld: str
    improved_jsonld: str
    content_recommendations: List[str]

# Made with Bob
