from fastapi import APIRouter, HTTPException
from app.models import AnalyzeRequest, AnalyzeResponse
from app.services.fetcher import fetch_url, FetchError
from app.services.schema_inventory import SchemaInventoryService
from app.services.geo_scorer import GEOScoringService
from app.services.llm_service import LLMService
from app.services.freshness_checker import FreshnessChecker
from app.services.llms_txt_checker import LlmsTxtChecker
import json

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_url(request: AnalyzeRequest):
    """
    Analyze a URL for AI search readiness.
    
    Returns schema inventory (diagnostic) and GEO score (0-100).
    """
    try:
        # 1. Fetch URL
        html, status_code = await fetch_url(str(request.url))
        
        # 2. Schema inventory (diagnostic - status 0/1/2)
        inventory_service = SchemaInventoryService()
        inventory = inventory_service.inventory_schemas(html)
        
        # 3. GEO scoring (0-100 from 7 rules)
        geo_service = GEOScoringService()
        geo_score = geo_service.score(html, inventory.raw_jsonld)
        
        # 4. Content freshness check (bonus signal, separate from GEO score)
        freshness_checker = FreshnessChecker()
        content_freshness = freshness_checker.check_freshness(inventory.raw_jsonld)
        
        # 5. llms.txt detection check (bonus signal)
        llms_txt_checker = LlmsTxtChecker()
        llms_txt_status = await llms_txt_checker.check_llms_txt(str(request.url))
        
        # 6. LLM dual output
        llm_service = LLMService()
        
        # Format current JSON-LD
        current_jsonld = json.dumps(inventory.raw_jsonld, indent=2) if inventory.raw_jsonld else "{}"
        
        # Generate improvements and recommendations
        schema_improvements = llm_service.generate_schema_improvements(
            inventory,
            str(request.url)
        )
        # Convert list to formatted string for improved_jsonld
        improved_jsonld = "\n".join(schema_improvements) if schema_improvements else "No improvements suggested"
        
        content_recommendations = llm_service.generate_content_recommendations(
            geo_score,
            str(request.url)
        )
        issues = llm_service.generate_issues(inventory, geo_score)
        
        return AnalyzeResponse(
            url=str(request.url),
            schema_inventory=inventory,
            geo_score=geo_score,
            content_freshness=content_freshness,
            llms_txt=llms_txt_status,
            issues=issues,
            current_jsonld=current_jsonld,
            improved_jsonld=improved_jsonld,
            content_recommendations=content_recommendations
        )
        
    except FetchError as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

# Made with Bob
