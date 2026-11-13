from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from app.models import ContentFreshness


class FreshnessChecker:
    """Checks content freshness based on dateModified/datePublished in schema."""
    
    def check_freshness(self, schemas: List[Dict[str, Any]]) -> ContentFreshness:
        """
        Check content freshness from JSON-LD schemas.
        
        Args:
            schemas: List of JSON-LD schema objects
            
        Returns:
            ContentFreshness object with status: 'Fresh', 'Aging', 'Stale', or 'Unknown'
        """
        # Try to find a date in the schemas
        date_found = None
        source_field = None
        
        # Priority order: dateModified > datePublished > uploadDate
        date_fields = ['dateModified', 'datePublished', 'uploadDate']
        
        for schema in schemas:
            for field in date_fields:
                if field in schema:
                    try:
                        # Parse the date
                        date_str = schema[field]
                        # Handle ISO format with Z or timezone
                        date_found = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        source_field = field
                        break
                    except (ValueError, AttributeError):
                        continue
            
            if date_found:
                break
        
        # If no date found, return Unknown status
        if not date_found:
            return ContentFreshness(
                status='Unknown',
                days_old=None,
                date_found=None,
                source_field=None
            )
        
        # Calculate days old
        now = datetime.now(timezone.utc)
        # Ensure date_found is timezone-aware
        if date_found.tzinfo is None:
            date_found = date_found.replace(tzinfo=timezone.utc)
        
        days_old = (now - date_found).days
        
        # Determine status based on age
        if days_old < 30:
            status = 'Fresh'
        elif days_old < 60:
            status = 'Aging'
        else:
            status = 'Stale'
        
        return ContentFreshness(
            status=status,
            days_old=days_old,
            date_found=date_found.isoformat(),
            source_field=source_field
        )


