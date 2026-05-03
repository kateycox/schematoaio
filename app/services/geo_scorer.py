from app.models import GEOScore
from app.rules.rule_registry import registry
from app.services.content_analyzer import ContentAnalyzer
from app.config import load_geo_rules_config
from app.rules.geo_rules import register_all_rules


class GEOScoringService:
    """Service for calculating GEO readiness scores (0-100)."""
    
    def __init__(self):
        """Initialize the scoring service and register rules."""
        # Load config and register rules
        config = load_geo_rules_config()
        register_all_rules(config)
        self.rules = registry.get_all_rules()
    
    def score(self, html: str, schemas: list) -> GEOScore:
        """
        Calculate GEO readiness score for a page.
        
        Args:
            html: HTML content to analyze
            schemas: List of JSON-LD schema objects
            
        Returns:
            GEOScore with total score (0-100) and individual rule results
        """
        # Create content analyzer
        content_analyzer = ContentAnalyzer(html)
        
        # Evaluate each rule
        results = []
        total_score = 0.0
        
        for rule in self.rules:
            result = rule.evaluate(content_analyzer, schemas)
            results.append(result)
            total_score += result.score
        
        return GEOScore(
            total_score=round(total_score, 2),
            max_score=100.0,
            rules=results
        )

# Made with Bob
