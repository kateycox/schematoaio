import json
from pathlib import Path
import os
from fastapi import APIRouter, HTTPException, Request

from app.config import MODEL_TIERS
from app.models import AnalyzeRequest, AnalyzeResponse
from app.services.fetcher import fetch_url, FetchError
from app.services.schema_inventory import SchemaInventoryService
from app.services.geo_scorer import GEOScoringService
from app.services.llm_service import LLMService, LLMOutOfCredits
from app.services.freshness_checker import FreshnessChecker
from app.services.llms_txt_checker import LlmsTxtChecker
from app.services.rate_limit import check_and_record, RateLimitExceeded


router = APIRouter()


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


LOGOS_DIR = Path(__file__).resolve().parent.parent / "static" / "logos"


@router.get("/logos")
async def list_logos():
    """Return all logo image URLs in the static/logos/ folder. Drop new files in to expand the rotation."""
    if not LOGOS_DIR.exists():
        return {"logos": []}
    files = sorted(
        f for f in LOGOS_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
    )
    base = os.getenv("APP_BASE_PATH", "")
    return {"logos": [f"{base}/static/logos/{f.name}?v={int(f.stat().st_mtime)}" for f in files]}


@router.get("/models")
async def list_models():
    """Return the list of model tiers available to the UI."""
    return {
        "tiers": [
            {
                "id": tier_id,
                "label": tier["label"],
                "description": tier["description"],
                "available": bool(tier["id"]),
            }
            for tier_id, tier in MODEL_TIERS.items()
        ]
    }


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_url(payload: AnalyzeRequest, request: Request):
    """Analyze a URL for AI search readiness."""
    try:
        check_and_record(_client_ip(request))
    except RateLimitExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))

    tier = payload.model

    try:
        html, _ = await fetch_url(str(payload.url))

        inventory_service = SchemaInventoryService()
        inventory = inventory_service.inventory_schemas(html)

        geo_service = GEOScoringService()
        geo_score = geo_service.score(html, inventory.raw_jsonld, url=str(payload.url))

        freshness_checker = FreshnessChecker()
        content_freshness = freshness_checker.check_freshness(inventory.raw_jsonld)

        llms_txt_checker = LlmsTxtChecker()
        llms_txt_status = await llms_txt_checker.check_llms_txt(str(payload.url))

        llm_service = LLMService()

        current_jsonld = json.dumps(inventory.raw_jsonld, indent=2) if inventory.raw_jsonld else "{}"

        schema_improvements = llm_service.generate_schema_improvements(
            inventory, str(payload.url), tier=tier,
        )
        improved_jsonld = "\n".join(schema_improvements) if schema_improvements else "No improvements suggested"

        content_recommendations = llm_service.generate_content_recommendations(
            geo_score, str(payload.url), tier=tier, limit=3,
        )
        all_content_recommendations = llm_service.generate_content_recommendations(
            geo_score, str(payload.url), tier=tier, limit=None,
        )
        issues = llm_service.generate_issues(inventory, geo_score, tier=tier)

        return AnalyzeResponse(
            url=str(payload.url),
            schema_inventory=inventory,
            geo_score=geo_score,
            content_freshness=content_freshness,
            llms_txt=llms_txt_status,
            issues=issues,
            current_jsonld=current_jsonld,
            improved_jsonld=improved_jsonld,
            content_recommendations=content_recommendations,
            all_content_recommendations=all_content_recommendations,
            model_used=tier,
        )

    except FetchError as e:
        msg = str(e)
        blocked_codes = ("401", "403", "429", "451", "503", "999")
        blocked_words = ("Forbidden", "Unauthorized", "blocked", "bot", "captcha")
        if any(code in msg for code in blocked_codes) or any(w.lower() in msg.lower() for w in blocked_words):
            raise HTTPException(
                status_code=400,
                detail="Some websites block crawlers like ours. This product works best on smaller business and non-profit websites.",
            )
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {msg}")
    except LLMOutOfCredits as e:
        raise HTTPException(status_code=503, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
