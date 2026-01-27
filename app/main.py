from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import uvicorn

#from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
# import time
# import uvicorn

from app.core.config import settings
from app.api.endpoints import router as api_router
from app.api.email_endpoints import router as email_router

from app.core.config import settings
from app.api.endpoints import router as api_router
# Add at the top of your main script
import sys
import os
#sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware for request timing
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

@app.get("/")
async def root():
    return {
        "message": "University Student Scraper API",
        "version": settings.VERSION,
        "docs": "/docs",
        "endpoints": {
            "scrape": f"{settings.API_V1_PREFIX}/scrape",
            "students": f"{settings.API_V1_PREFIX}/students",
            "search": f"{settings.API_V1_PREFIX}/students/search",
            "universities": f"{settings.API_V1_PREFIX}/universities"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": time.time()}


    
    
    
    
    
      # NEW

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware for request timing
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Include API routers
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(email_router, prefix=settings.API_V1_PREFIX)  # NEW

@app.get("/")
async def root():
    return {
        "message": "University Student Scraper API with Email Automation",
        "version": settings.VERSION,
        "docs": "/docs",
        "endpoints": {
            "scraping": {
                "scrape": f"{settings.API_V1_PREFIX}/scrape",
                "students": f"{settings.API_V1_PREFIX}/students",
                "search": f"{settings.API_V1_PREFIX}/students/search"
            },
            "email_automation": {  # NEW
                "generate_papers": f"{settings.API_V1_PREFIX}/email/generate-papers",
                "send_emails": f"{settings.API_V1_PREFIX}/email/send-emails",
                "batch_process": f"{settings.API_V1_PREFIX}/email/batch-process",
                "templates": f"{settings.API_V1_PREFIX}/email/templates",
                "statistics": f"{settings.API_V1_PREFIX}/email/statistics"
            }
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": time.time()}

#if __name__ == "__main__":
    
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
    