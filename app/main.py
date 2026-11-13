from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from app.api import routes


app = FastAPI(
    title="SchematoAIO",
    description="AI Search Readiness Analyzer",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.router)

static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


@app.get("/")
async def root():
    html_path = Path(__file__).parent / "static" / "index.html"
    if html_path.exists():
        return FileResponse(html_path)
    return {"message": "SchematoAIO API - Visit /docs for API documentation"}


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "SchematoAIO",
        "version": "1.1.0",
    }
