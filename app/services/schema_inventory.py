from bs4 import BeautifulSoup
import json
from typing import List, Dict, Any
from app.models import SchemaInventory, SchemaTypeInventory, SchemaComponent
from app.config import load_schema_config


class SchemaInventoryService:
    """Service for analyzing schema.org markup on web pages."""
    
    def __init__(self):
        """Initialize with schema configuration."""
        self.config = load_schema_config()
        self.types_with_requirements = self.config['schema_types']['types_with_requirements']
        self.presence_only_types = self.config['schema_types']['presence_only_types']
        self.ignored_types = self.config['schema_types'].get('ignored_types', [])
    
    def inventory_schemas(self, html: str) -> SchemaInventory:
        """
        Analyze HTML for schema.org markup.
        
        Args:
            html: HTML content to analyze
            
        Returns:
            SchemaInventory with status (0/1/2) and detailed findings
        """
        soup = BeautifulSoup(html, 'lxml')
        
        # Extract all JSON-LD scripts
        raw_jsonld = self._extract_jsonld(soup)
        
        # Analyze each schema type
        types_found = []
        
        # Check types with requirements
        for type_name, requirements in self.types_with_requirements.items():
            inventory = self._check_schema_type(type_name, requirements, raw_jsonld)
            types_found.append(inventory)
        
        # Check presence-only types
        for type_name in self.presence_only_types:
            inventory = self._check_presence_only(type_name, raw_jsonld)
            types_found.append(inventory)
        
        # Calculate overall status
        found_count = sum(1 for t in types_found if t.found)
        if found_count == 0:
            status = 0  # None
        elif found_count < 3:
            status = 1  # Some
        else:
            status = 2  # Multiple
        
        return SchemaInventory(
            status=status,
            types_found=types_found,
            raw_jsonld=raw_jsonld,
            total_count=len(raw_jsonld)
        )
    
    def _extract_jsonld(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract all JSON-LD scripts from HTML."""
        jsonld_scripts = soup.find_all('script', type='application/ld+json')
        schemas = []
        
        for script in jsonld_scripts:
            try:
                data = json.loads(script.string)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if isinstance(item, dict) and isinstance(item.get('@graph'), list):
                        schemas.extend(n for n in item['@graph'] if isinstance(n, dict))
                    elif isinstance(item, dict):
                        schemas.append(item)
            except (json.JSONDecodeError, AttributeError):
                continue
        
        return schemas
    
    def _check_schema_type(
        self, 
        type_name: str, 
        requirements: Dict[str, Any], 
        schemas: List[Dict]
    ) -> SchemaTypeInventory:
        """Check for a schema type with required components."""
        required_fields = requirements.get('required', [])
        aliases = requirements.get('aliases', [])
        all_names = [type_name] + aliases
        
        # Find matching schemas
        matching_schemas = []
        for schema in schemas:
            schema_type = schema.get('@type', '')
            if isinstance(schema_type, list):
                schema_type = schema_type[0] if schema_type else ''
            
            if schema_type in all_names:
                matching_schemas.append(schema)
        
        if not matching_schemas:
            return SchemaTypeInventory(
                type_name=type_name,
                found=False,
                required_components=[
                    SchemaComponent(name=field, present=False)
                    for field in required_fields
                ],
                completeness_ratio=f"0/{len(required_fields)}",
                status_message=f"{type_name} not found"
            )
        
        # Check components in the first matching schema
        schema = matching_schemas[0]
        components = []
        present_count = 0
        
        for field in required_fields:
            present = field in schema and schema[field]
            if present:
                present_count += 1
            
            value = str(schema.get(field, ''))[:50] if present else None
            components.append(SchemaComponent(
                name=field,
                present=present,
                value=value
            ))
        
        missing = [c.name for c in components if not c.present]
        if missing:
            status_msg = f"{type_name}: {present_count}/{len(required_fields)} components — missing {', '.join(missing)}"
        else:
            status_msg = f"{type_name}: Complete ({present_count}/{len(required_fields)} components)"
        
        return SchemaTypeInventory(
            type_name=type_name,
            found=True,
            required_components=components,
            completeness_ratio=f"{present_count}/{len(required_fields)}",
            status_message=status_msg
        )
    
    def _check_presence_only(
        self, 
        type_name: str, 
        schemas: List[Dict]
    ) -> SchemaTypeInventory:
        """Check for presence of a schema type (no component requirements)."""
        found = False
        
        for schema in schemas:
            schema_type = schema.get('@type', '')
            if isinstance(schema_type, list):
                schema_type = schema_type[0] if schema_type else ''
            
            if schema_type == type_name:
                found = True
                break
        
        status_msg = f"{type_name}: {'Present' if found else 'Not found'}"
        
        return SchemaTypeInventory(
            type_name=type_name,
            found=found,
            required_components=[],
            completeness_ratio="N/A",
            status_message=status_msg
        )
