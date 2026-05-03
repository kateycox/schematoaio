# Quick Start Guide

## Setup Instructions

### 1. Navigate to the project directory
```bash
cd schematoaio
```

### 2. Create a virtual environment
```bash
python -m venv venv
```

### 3. Activate the virtual environment

**On macOS/Linux:**
```bash
source venv/bin/activate
```

**On Windows:**
```bash
venv\Scripts\activate
```

### 4. Install dependencies
```bash
pip install -r requirements.txt
```

### 5. Set up environment variables
```bash
cp .env.example .env
```

Then edit `.env` and add your API keys (optional for Phase 1 testing):
```
IBM_API_KEY=your_ibm_api_key_here
IBM_PROJECT_ID=your_ibm_project_id_here
OPENAI_API_KEY=your_openai_api_key_here
```

**Note:** The LLM features use placeholder implementations, so the app will work without API keys for basic testing.

### 6. Run the application
```bash
uvicorn app.main:app --reload
```

### 7. Open in browser
Navigate to: http://localhost:8000

## Testing the Application

1. Enter a URL in the search bar (e.g., `https://example.com`)
2. Click "Analyze"
3. View the results:
   - **Schema Inventory**: Diagnostic report of schema types found
   - **GEO Readiness Score**: 0-100 score based on 7 content rules
   - **Issues**: Prioritized list of problems
   - **Content Recommendations**: Plain-English suggestions
   - **Schema Comparison**: Current vs. improved JSON-LD

## What's Working

✅ **Phase 1 Complete:**
- FastAPI backend with all core services
- Schema inventory (19 types)
- GEO scoring engine (7 rules)
- Content analysis
- Basic LLM service (placeholder implementations)
- Google-inspired frontend UI
- Full API endpoint

## Next Steps

- Add real LLM integration (IBM Granite + OpenAI)
- Add error handling improvements
- Add caching for repeated URLs
- Add rate limiting
- Write tests

## Troubleshooting

**Import errors?**
- Make sure you're in the virtual environment
- Run `pip install -r requirements.txt` again

**Port already in use?**
- Use a different port: `uvicorn app.main:app --reload --port 8001`

**Module not found errors?**
- Make sure you're running from the `schematoaio` directory
- Check that all files were created correctly