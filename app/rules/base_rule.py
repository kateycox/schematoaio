from abc import ABC, abstractmethod
from typing import Dict, Any
from app.models import GEORuleResult


class BaseRule(ABC):
    """Abstract base class for GEO rules."""
    
    def __init__(self, name: str, weight: float, description: str, config: Dict[str, Any]):
        """
        Initialize a GEO rule.
        
        Args:
            name: Rule identifier
            weight: Points this rule is worth (typically ~14.29 for equal weighting)
            description: Human-readable description
            config: Additional configuration from YAML
        """
        self.name = name
        self.weight = weight
        self.description = description
        self.config = config
    
    @abstractmethod
    def evaluate(self, content_analyzer, schemas: list) -> GEORuleResult:
        """
        Evaluate the rule against page content.
        
        Args:
            content_analyzer: ContentAnalyzer instance with parsed HTML
            schemas: List of JSON-LD schema objects
            
        Returns:
            GEORuleResult with score and details
        """
        pass
    
    def create_result(
        self, 
        score: float, 
        passed: bool, 
        message: str, 
        details: Dict[str, Any]
    ) -> GEORuleResult:
        """
        Helper to create a standardized rule result.
        
        Args:
            score: Points earned (0 to self.weight)
            passed: Whether the rule passed
            message: Human-readable result message
            details: Additional details about the evaluation
            
        Returns:
            GEORuleResult instance
        """
        return GEORuleResult(
            rule_name=self.name,
            score=round(score, 2),
            max_score=self.weight,
            passed=passed,
            message=message,
            details=details
        )

# Made with Bob
