from typing import List
from app.rules.base_rule import BaseRule


class RuleRegistry:
    """Registry for managing GEO rules."""
    
    def __init__(self):
        """Initialize empty registry."""
        self._rules: List[BaseRule] = []
    
    def register(self, rule: BaseRule) -> None:
        """
        Register a rule.
        
        Args:
            rule: BaseRule instance to register
        """
        self._rules.append(rule)
    
    def get_all_rules(self) -> List[BaseRule]:
        """
        Get all registered rules.
        
        Returns:
            List of all registered rules
        """
        return self._rules.copy()
    
    def clear(self) -> None:
        """Clear all registered rules."""
        self._rules.clear()


# Global registry instance
registry = RuleRegistry()

# Made with Bob
