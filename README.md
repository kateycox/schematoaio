# SchematoAIO - AI Search Readiness Analyzer

Analyze your web pages for AI search readiness using empirical GEO (Generative Engine Optimization) research.

## Overview

**SchematoAIO** evaluates web pages using two separate analyses:

1. **Schema Inventory** (Diagnostic) - Reports which of 19 schema types are present and component completeness. Status: 0 (none), 1 (some), or 2 (multiple). NOT scored.

2. **GEO Readiness Score** (0-100) - Evaluates 7 content-level signals based on empirical GEO research. Each rule worth ~14.29 points.

**Core Insight**: AI search engines retrieve passages, not pages. Content must be structured for easy extraction and citation.

## Features

- ✅ **Schema Inventory**: Detects 19 schema types with component completeness analysis
- ✅ **GEO Scoring**: 7 content rules producing 0-100 score based on research
- ✅ **Dual LLM Output**: 
  - Improved JSON-LD suggestions (based on schema inventory)
  - Plain-English content recommendations (based on GEO rule scores)
- ✅ **Configuration-Driven**: SEO teammate can modify YAML files without touching code
- ✅ **Google-Inspired UI**: Playful reference to Google's visual language

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd schematoaio
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your API key:
```
GEMINI_API_KEY=your_gemini_api_key_here
```

Get your free Gemini API key at: https://aistudio.google.com/app/apikey

### 5. Run the Application

```bash
uvicorn app.main:app --reload
```

Open http://localhost:8000 in your browser.

## Project Structure

```
schematoaio/
├── app/
│   ├── main.py                      # FastAPI entry point
│   ├── models.py                    # Pydantic models
│   ├── config.py                    # Settings & config loaders
│   ├── api/
│   │   └── routes.py                # /analyze endpoint
│   ├── services/
│   │   ├── fetcher.py               # URL fetching
│   │   ├── schema_inventory.py     # 19 types (diagnostic)
│   │   ├── content_analyzer.py     # HTML extraction
│   │   ├── geo_scorer.py            # 7 rules → 0-100
│   │   └── llm_service.py           # Dual output
│   ├── rules/
│   │   ├── base_rule.py             # Abstract base class
│   │   ├── rule_registry.py        # Rule registration
│   │   └── geo_rules.py             # 7 GEO rule implementations
│   └── static/
│       ├── index.html               # Single-page UI
│       ├── styles.css               # Google-inspired styling
│       └── app.js                   # Frontend logic
├── config/
│   ├── schema_config.yaml           # 19 schema types
│   └── geo_rules_config.yaml        # 7 GEO rules
├── tests/
├── requirements.txt
└── README.md
```

## Configuration

### Adding a New Schema Type

Edit `config/schema_config.yaml`:

```yaml
types_with_requirements:
  Course:
    required: [name, description, provider]
    description: "Online course"
```

### Adjusting GEO Rule Weights

Edit `config/geo_rules_config.yaml`:

```yaml
geo_rules:
  answer_first_content:
    weight: 20.0  # Increase importance
  content_freshness:
    weight: 10.0  # Decrease importance
```

Note: Weights should total ~100 for accurate scoring.

## API Endpoints

### POST /analyze

Analyze a URL for AI search readiness.

**Request:**
```json
{
  "url": "https://example.com"
}
```

**Response:**
```json
{
  "url": "https://example.com",
  "schema_inventory": {
    "status": 2,
    "types_found": [...],
    "raw_jsonld": [...]
  },
  "geo_score": {
    "total_score": 85.5,
    "max_score": 100.0,
    "rules": [...]
  },
  "issues": [...],
  "current_jsonld": "...",
  "improved_jsonld": "...",
  "content_recommendations": [...]
}
```

### GET /health

Health check endpoint.

## The 7 GEO Rules

1. **Answer-First Content** - Clear summary in first 200 words (33% more likely to be cited)
2. **Quotable Chunks** - Short paragraphs and structured lists (30% increase in visibility)
3. **Definitional Phrasing** - "X is..." patterns (2x more likely to be cited)
4. **Sourced Statistics** - Numerical data and statistics (30-40% increase in visibility)
5. **Question-Format Headings** - H2/H3 tags matching user queries
6. **Content Freshness** - Recent modification signals
7. **FAQ Content Blocks** - Q&A structured content

## The 19 Schema Types

### Types with Component Checks (11)
- Organization, Article, BlogPosting, NewsArticle
- FAQPage, BreadcrumbList, Person/Author
- HowTo, Product, Event, Recipe

### Presence-Only Types (8)
- Offer, AggregateRating, Review, WebPage
- SoftwareApplication, VideoObject, LocalBusiness, ImageObject

## Development

### Running Tests

```bash
pytest
```

### Running with Debug Mode

```bash
DEBUG=True uvicorn app.main:app --reload
```

## Tech Stack

- **Backend**: Python FastAPI
- **Frontend**: HTML/CSS/JavaScript (single-page, no build)
- **Parsing**: BeautifulSoup4
- **LLM**: Google Gemini 1.5 Flash (free, 1500 requests/day)
- **Config**: YAML

## Architecture Principles

1. **Separation of Concerns**: Schema inventory (diagnostic) vs. GEO scoring (0-100)
2. **Configuration-Driven**: All schema types and rules in YAML
3. **Modular Rule Engine**: Each GEO rule is a separate class
4. **Abstract LLM Client**: Provider-agnostic interface
5. **Dual LLM Output**: Both schema improvements AND content recommendations

## Contributing

This is a hackathon project. For production use, consider:
- Rate limiting
- Caching
- Error recovery
- More comprehensive testing
- Security hardening

## License

MIT License - See LICENSE file for details

## Acknowledgments

Based on empirical GEO research showing that AI systems retrieve passages, not pages. Content needs to be easy to match, extract, and cite.

---

Built for hackathon - AI Search Readiness Analyzer