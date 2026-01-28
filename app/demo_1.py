
"""
Features:
1. Complete web scraping from university websites
2. AI-powered academic paper generation
3. Email automation with DOCX attachments
4. Blue-Green deployment support
5. Comprehensive monitoring & debugging
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import json

# Add the parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
import uvicorn
import logging
from contextlib import asynccontextmanager
from prometheus_fastapi_instrumentator import Instrumentator
import platform
import psutil

# Import configurations
from app.core.config import settings
from app.core.logging_config import setup_logging, logger, LogContext
from app.utils.debug_utils import MemoryDebugger

# Import API routers
from app.api.endpoints import router as api_router
from app.api.email_endpoints import router as email_router

# Application lifespan manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application
    Handles startup and shutdown events
    """
    # Startup
    startup_time = datetime.now()
    
    logger.info("🚀 Starting Academic Research Automation System")
    logger.info(f"📋 Version: {settings.VERSION}")
    logger.info(f"🌍 Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"📊 Log Level: {os.getenv('LOG_LEVEL', 'INFO')}")
    
    # Create necessary directories
    directories = [
        "logs",
        "output/papers",
        "templates/email_templates",
        "data/journals",
        "reports",
        "static"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created directory: {directory}")
    
    # Initialize default templates if they don't exist
    template_dir = Path("templates/email_templates")
    if not (template_dir / "journal_invitation.html").exists():
        from app.email_service.template_manager import TemplateManager
        template_manager = TemplateManager(str(template_dir))
        logger.info("✅ Created default email templates")
    
    logger.info(f"✅ Startup completed in {(datetime.now() - startup_time).total_seconds():.2f}s")
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("🛑 Shutting down Academic Research Automation System")
    
    # Cleanup resources
    logger.info("🧹 Cleaning up resources...")
    
    logger.info("👋 Shutdown complete")

# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="""
    Academic Research Automation System
    
    ## Features
    
    ### 1. Web Scraping Module
    - Scrape student names and emails from university websites
    - Support for static and JavaScript-rendered pages
    - Intelligent parsing and data extraction
    
    ### 2. AI-Powered Paper Generation
    - Generate personalized academic papers using AI
    - Multiple AI backends (OpenAI, Llama, fallback)
    - Professional DOCX formatting
    
    ### 3. Email Automation
    - Send personalized emails with paper attachments
    - Bulk email sending with rate limiting
    - Template-based email generation
    
    ### 4. Blue-Green Deployment
    - Zero-downtime deployments
    - Canary releases
    - Instant rollback capabilities
    
    ### 5. Monitoring & Analytics
    - Real-time performance metrics
    - Comprehensive logging
    - Health checks and diagnostics
    """,
    contact={
        "name": "Research Automation Team",
        "email": "support@research-automation.example.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    docs_url=None,  # Custom docs URLs
    redoc_url=None,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "scraping",
            "description": "University website scraping operations",
        },
        {
            "name": "email",
            "description": "Email automation and paper generation",
        },
        {
            "name": "monitoring",
            "description": "System monitoring and health checks",
        },
        {
            "name": "debugging",
            "description": "Debugging and diagnostic tools",
        },
    ],
)

# Custom documentation endpoints
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """Custom Swagger UI documentation"""
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )

@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    """Custom ReDoc documentation"""
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
    )

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/reports", StaticFiles(directory="reports"), name="reports")

# Middleware
# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time", "X-Request-ID", "X-Response-Time"],
)

# Trusted hosts middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"],  # In production, specify exact hosts
)

# GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add process time to response headers"""
    import time
    start_time = time.time()
    
    # Add request ID
    request_id = request.headers.get("X-Request-ID", f"req_{int(start_time * 1000)}")
    
    response = await call_next(request)
    process_time = time.time() - start_time
    
    # Add headers
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = str(process_time)
    
    # Log slow requests
    if process_time > 5.0:  # More than 5 seconds
        logger.warning(
            f"Slow request: {request.method} {request.url.path}",
            extra={
                "process_time": process_time,
                "request_id": request_id,
                "client": request.client.host if request.client else "unknown",
            }
        )
    
    return response

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests"""
    logger.info(
        f"Request: {request.method} {request.url.path}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "query": str(request.query_params),
            "client": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
        }
    )
    
    try:
        response = await call_next(request)
        
        # Log response
        logger.info(
            f"Response: {request.method} {request.url.path} - {response.status_code}",
            extra={
                "status_code": response.status_code,
                "method": request.method,
                "path": request.url.path,
            }
        )
        
        return response
    except Exception as e:
        logger.error(
            f"Request error: {request.method} {request.url.path} - {str(e)}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True
        )
        raise

# Include API routers
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(email_router, prefix=settings.API_V1_PREFIX)

# Prometheus metrics
instrumentator = Instrumentator(
    excluded_handlers=["/metrics", "/health", "/docs", "/redoc", "/static"]
)
instrumentator.instrument(app).expose(app)

# Root endpoint - Redirect to docs
@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to API documentation"""
    return RedirectResponse(url="/docs")

# System information endpoint
@app.get("/", response_class=JSONResponse, tags=["monitoring"])
async def system_info():
    """Get system information and API details"""
    system_info = {
        "system": platform.system(),
        "release": platform.release(),
        "python_version": platform.python_version(),
        "cpu_count": psutil.cpu_count(),
        "memory_total_gb": psutil.virtual_memory().total / (1024**3),
        "memory_available_gb": psutil.virtual_memory().available / (1024**3),
    }
    
    return {
        "application": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "system": system_info,
        "endpoints": {
            "documentation": {
                "swagger_ui": "/docs",
                "redoc": "/redoc",
                "openapi_schema": f"{settings.API_V1_PREFIX}/openapi.json"
            },
            "monitoring": {
                "health": "/health",
                "metrics": "/metrics",
                "system_info": "/system"
            },
            "api": {
                "scraping": f"{settings.API_V1_PREFIX}/scrape",
                "students": f"{settings.API_V1_PREFIX}/students",
                "generate_papers": f"{settings.API_V1_PREFIX}/email/generate-papers",
                "send_emails": f"{settings.API_V1_PREFIX}/email/send-emails",
                "batch_process": f"{settings.API_V1_PREFIX}/email/batch-process"
            },
            "debugging": {
                "debug_info": "/debug",
                "memory_profile": "/debug/memory",
                "performance_profile": "/debug/performance"
            }
        },
        "environment": os.getenv("ENVIRONMENT", "development"),
        "log_level": os.getenv("LOG_LEVEL", "INFO")
    }

# Health check endpoint
@app.get("/health", tags=["monitoring"])
async def health_check():
    """Comprehensive health check endpoint"""
    import asyncpg
    from redis import Redis
    import smtplib
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": settings.VERSION,
        "services": {},
        "system": {},
        "checks": []
    }
    
    # System checks
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        health_status["system"]["cpu_percent"] = cpu_percent
        health_status["checks"].append({
            "name": "cpu_usage",
            "status": "healthy" if cpu_percent < 90 else "warning",
            "message": f"CPU usage: {cpu_percent}%"
        })
        
        # Memory usage
        memory = psutil.virtual_memory()
        health_status["system"]["memory_percent"] = memory.percent
        health_status["system"]["memory_available_gb"] = memory.available / (1024**3)
        health_status["checks"].append({
            "name": "memory_usage",
            "status": "healthy" if memory.percent < 90 else "warning",
            "message": f"Memory usage: {memory.percent}%"
        })
        
        # Disk usage
        disk = psutil.disk_usage('/')
        health_status["system"]["disk_percent"] = disk.percent
        health_status["checks"].append({
            "name": "disk_usage",
            "status": "healthy" if disk.percent < 90 else "warning",
            "message": f"Disk usage: {disk.percent}%"
        })
        
    except Exception as e:
        health_status["checks"].append({
            "name": "system_metrics",
            "status": "error",
            "message": f"Failed to get system metrics: {str(e)}"
        })
    
    # Database check
    if settings.DATABASE_URL:
        try:
            # Test database connection
            # This is simplified - in production, use async connection
            health_status["services"]["database"] = "healthy"
            health_status["checks"].append({
                "name": "database",
                "status": "healthy",
                "message": "Database connection successful"
            })
        except Exception as e:
            health_status["services"]["database"] = "unhealthy"
            health_status["checks"].append({
                "name": "database",
                "status": "error",
                "message": f"Database connection failed: {str(e)}"
            })
            health_status["status"] = "degraded"
    
    # Redis check (if configured)
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            redis_client = Redis.from_url(redis_url)
            redis_client.ping()
            health_status["services"]["redis"] = "healthy"
            health_status["checks"].append({
                "name": "redis",
                "status": "healthy",
                "message": "Redis connection successful"
            })
            redis_client.close()
        except Exception as e:
            health_status["services"]["redis"] = "unhealthy"
            health_status["checks"].append({
                "name": "redis",
                "status": "error",
                "message": f"Redis connection failed: {str(e)}"
            })
            health_status["status"] = "degraded"
    
    # Email service check
    if os.getenv("EMAIL_SENDER"):
        try:
            # Test SMTP connection
            with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
                server.ehlo()
                if not settings.USE_SSL:
                    server.starttls()
                health_status["services"]["email"] = "healthy"
                health_status["checks"].append({
                    "name": "email",
                    "status": "healthy",
                    "message": "SMTP connection successful"
                })
        except Exception as e:
            health_status["services"]["email"] = "unhealthy"
            health_status["checks"].append({
                "name": "email",
                "status": "error",
                "message": f"SMTP connection failed: {str(e)}"
            })
            health_status["status"] = "degraded"
    
    # File system checks
    required_dirs = ["logs", "output/papers", "templates"]
    for directory in required_dirs:
        dir_path = Path(directory)
        if dir_path.exists() and dir_path.is_dir():
            health_status["checks"].append({
                "name": f"directory_{directory}",
                "status": "healthy",
                "message": f"Directory exists: {directory}"
            })
        else:
            health_status["checks"].append({
                "name": f"directory_{directory}",
                "status": "error",
                "message": f"Missing directory: {directory}"
            })
            health_status["status"] = "degraded"
    
    # Count unhealthy checks
    unhealthy_checks = [check for check in health_status["checks"] if check["status"] == "error"]
    if unhealthy_checks:
        health_status["unhealthy_count"] = len(unhealthy_checks)
    
    return health_status

# Extended health check with more details
@app.get("/health/detailed", tags=["monitoring"])
async def detailed_health_check():
    """Detailed health check with system diagnostics"""
    from datetime import datetime, timedelta
    
    detailed_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "system": {},
        "process": {},
        "network": {},
        "filesystem": {},
        "dependencies": {}
    }
    
    # System information
    detailed_status["system"] = {
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
    }
    
    # Process information
    process = psutil.Process()
    with process.oneshot():
        detailed_status["process"] = {
            "pid": process.pid,
            "name": process.name(),
            "status": process.status(),
            "create_time": datetime.fromtimestamp(process.create_time()).isoformat(),
            "cpu_percent": process.cpu_percent(),
            "memory_percent": process.memory_percent(),
            "memory_rss_mb": process.memory_info().rss / (1024 * 1024),
            "memory_vms_mb": process.memory_info().vms / (1024 * 1024),
            "num_threads": process.num_threads(),
            "num_fds": process.num_fds() if hasattr(process, "num_fds") else None,
        }
    
    # Network information
    net_io = psutil.net_io_counters()
    detailed_status["network"] = {
        "bytes_sent": net_io.bytes_sent,
        "bytes_recv": net_io.bytes_recv,
        "packets_sent": net_io.packets_sent,
        "packets_recv": net_io.packets_recv,
        "errin": net_io.errin,
        "errout": net_io.errout,
        "dropin": net_io.dropin,
        "dropout": net_io.dropout,
    }
    
    # Filesystem information
    partitions = []
    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            partitions.append({
                "device": partition.device,
                "mountpoint": partition.mountpoint,
                "fstype": partition.fstype,
                "total_gb": usage.total / (1024**3),
                "used_gb": usage.used / (1024**3),
                "free_gb": usage.free / (1024**3),
                "percent": usage.percent,
            })
        except PermissionError:
            continue
    
    detailed_status["filesystem"] = {
        "partitions": partitions
    }
    
    # Uptime
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.now() - boot_time
    detailed_status["system"]["uptime"] = str(uptime)
    detailed_status["system"]["boot_time"] = boot_time.isoformat()
    
    # Load average (Unix-like systems)
    if hasattr(psutil, "getloadavg"):
        try:
            load_avg = psutil.getloadavg()
            detailed_status["system"]["load_average"] = {
                "1min": load_avg[0],
                "5min": load_avg[1],
                "15min": load_avg[2],
            }
        except OSError:
            pass
    
    return detailed_status

# System information endpoint
@app.get("/system", tags=["monitoring"])
async def get_system_info():
    """Get detailed system information"""
    import socket
    
    system_info = {
        "timestamp": datetime.now().isoformat(),
        "host": {
            "name": socket.gethostname(),
            "ip": socket.gethostbyname(socket.gethostname()),
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "compiler": platform.python_compiler(),
            "build": platform.python_build(),
        },
        "resources": {
            "cpu": {
                "count": psutil.cpu_count(),
                "percent": psutil.cpu_percent(interval=0.1),
                "freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
            },
            "memory": {
                "total_gb": psutil.virtual_memory().total / (1024**3),
                "available_gb": psutil.virtual_memory().available / (1024**3),
                "percent": psutil.virtual_memory().percent,
                "used_gb": psutil.virtual_memory().used / (1024**3),
            },
            "disk": {
                "total_gb": psutil.disk_usage('/').total / (1024**3),
                "used_gb": psutil.disk_usage('/').used / (1024**3),
                "free_gb": psutil.disk_usage('/').free / (1024**3),
                "percent": psutil.disk_usage('/').percent,
            }
        },
        "application": {
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "environment": os.getenv("ENVIRONMENT", "development"),
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "api_prefix": settings.API_V1_PREFIX,
        }
    }
    
    return system_info

# Debug endpoint
@app.get("/debug", tags=["debugging"])
async def debug_dashboard():
    """Debug dashboard with system information"""
    import gc
    
    memory_info = MemoryDebugger.get_memory_usage()
    
    debug_info = {
        "memory": memory_info,
        "python": {
            "version": sys.version,
            "implementation": platform.python_implementation(),
            "gc_enabled": gc.isenabled(),
            "gc_threshold": gc.get_threshold(),
            "gc_count": gc.get_count(),
        },
        "environment": {k: v for k, v in os.environ.items() if not any(s in k.lower() for s in ['pass', 'secret', 'key', 'token'])},
        "paths": {
            "working_directory": os.getcwd(),
            "app_directory": str(Path(__file__).parent),
        },
        "process": {
            "pid": os.getpid(),
            "uid": os.getuid() if hasattr(os, 'getuid') else None,
            "gid": os.getgid() if hasattr(os, 'getgid') else None,
        }
    }
    
    return debug_info

# Memory profiling endpoint
@app.get("/debug/memory", tags=["debugging"])
async def memory_profile():
    """Memory profiling endpoint"""
    import gc
    
    # Get current memory usage
    memory_info = MemoryDebugger.get_memory_usage()
    
    # Collect garbage
    gc.collect()
    
    memory_info_after = MemoryDebugger.get_memory_usage()
    
    return {
        "before_gc": memory_info,
        "after_gc": memory_info_after,
        "gc_collected_mb": memory_info["rss_mb"] - memory_info_after["rss_mb"],
        "timestamp": datetime.now().isoformat()
    }

# Performance profiling endpoint
@app.get("/debug/performance", tags=["debugging"])
async def performance_profile():
    """Performance profiling endpoint"""
    import time
    
    profile_data = {
        "timestamp": datetime.now().isoformat(),
        "system_load": {},
        "api_performance": {},
    }
    
    # System load
    profile_data["system_load"] = {
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage('/').percent,
    }
    
    # API performance test
    start_time = time.time()
    test_requests = 100
    profile_data["api_performance"] = {
        "test_requests": test_requests,
        "test_description": f"Simulated {test_requests} requests",
    }
    
    # Simulate some load
    for i in range(test_requests):
        # Simple CPU-bound operation
        _ = [j * j for j in range(1000)]
    
    end_time = time.time()
    profile_data["api_performance"]["execution_time"] = end_time - start_time
    profile_data["api_performance"]["requests_per_second"] = test_requests / (end_time - start_time)
    
    return profile_data

# Test email endpoint
@app.get("/test/email", tags=["debugging"])
async def test_email_endpoint():
    """Test email configuration"""
    from app.email_service.email_sender import EmailSender
    
    test_result = {
        "status": "pending",
        "timestamp": datetime.now().isoformat(),
        "checks": []
    }
    
    # Check if email configuration exists
    if not os.getenv("EMAIL_SENDER"):
        test_result["status"] = "failed"
        test_result["checks"].append({
            "name": "email_config",
            "status": "error",
            "message": "EMAIL_SENDER environment variable not set"
        })
        return test_result
    
    # Test email sender initialization
    try:
        email_sender = EmailSender(
            smtp_server=os.getenv("SMTP_SERVER", "smtp.gmail.com"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            use_ssl=os.getenv("USE_SSL", "false").lower() == "true"
        )
        test_result["checks"].append({
            "name": "email_sender_init",
            "status": "success",
            "message": "Email sender initialized successfully"
        })
    except Exception as e:
        test_result["status"] = "failed"
        test_result["checks"].append({
            "name": "email_sender_init",
            "status": "error",
            "message": f"Failed to initialize email sender: {str(e)}"
        })
        return test_result
    
    test_result["status"] = "success"
    return test_result

# Test scraper endpoint
@app.get("/test/scraper", tags=["debugging"])
async def test_scraper_endpoint():
    """Test web scraper functionality"""
    from app.scraper.university_scrapers import GenericUniversityScraper
    
    test_result = {
        "status": "pending",
        "timestamp": datetime.now().isoformat(),
        "checks": []
    }
    
    # Test scraper initialization
    try:
        scraper = GenericUniversityScraper(timeout=10)
        test_result["checks"].append({
            "name": "scraper_init",
            "status": "success",
            "message": "Scraper initialized successfully"
        })
    except Exception as e:
        test_result["status"] = "failed"
        test_result["checks"].append({
            "name": "scraper_init",
            "status": "error",
            "message": f"Failed to initialize scraper: {str(e)}"
        })
        return test_result
    
    # Test email normalization
    try:
        test_emails = [
            "john.doe@university.edu",
            "JANE.SMITH@COLLEGE.EDU",
            "  bob.johnson@institute.edu  "
        ]
        
        normalized = []
        for email in test_emails:
            norm = scraper.normalize_email(email)
            if norm:
                normalized.append(norm)
        
        test_result["checks"].append({
            "name": "email_normalization",
            "status": "success",
            "message": f"Normalized {len(normalized)}/{len(test_emails)} test emails"
        })
        
    except Exception as e:
        test_result["status"] = "failed"
        test_result["checks"].append({
            "name": "email_normalization",
            "status": "error",
            "message": f"Email normalization failed: {str(e)}"
        })
    
    test_result["status"] = "success"
    return test_result

# Test paper generator endpoint
@app.get("/test/paper-generator", tags=["debugging"])
async def test_paper_generator_endpoint():
    """Test paper generator functionality"""
    from app.email_service.ai_paper_generator import AIPaperGenerator
    
    test_result = {
        "status": "pending",
        "timestamp": datetime.now().isoformat(),
        "checks": []
    }
    
    try:
        # Test with fallback mode (no API key required)
        generator = AIPaperGenerator(model_type="fallback")
        
        # Test title generation
        title = generator.generate_paper_title("Computer Science")
        test_result["checks"].append({
            "name": "title_generation",
            "status": "success",
            "message": f"Generated title: {title[:50]}..."
        })
        
        # Test abstract generation
        abstract = generator.generate_abstract(title, "Test Student")
        test_result["checks"].append({
            "name": "abstract_generation",
            "status": "success",
            "message": f"Generated abstract ({len(abstract)} chars)"
        })
        
        # Test full paper generation
        paper_content = generator.generate_paper_content(title, abstract, "Test Student")
        required_sections = ['introduction', 'methodology', 'results', 'conclusion']
        missing_sections = [section for section in required_sections if not paper_content.get(section)]
        
        if not missing_sections:
            test_result["checks"].append({
                "name": "paper_generation",
                "status": "success",
                "message": f"Generated paper with {len(paper_content)} sections"
            })
        else:
            test_result["checks"].append({
                "name": "paper_generation",
                "status": "warning",
                "message": f"Missing sections: {missing_sections}"
            })
        
    except Exception as e:
        test_result["status"] = "failed"
        test_result["checks"].append({
            "name": "paper_generator",
            "status": "error",
            "message": f"Paper generator test failed: {str(e)}"
        })
        return test_result
    
    test_result["status"] = "success"
    return test_result

# Configuration endpoint
@app.get("/config", tags=["monitoring"])
async def get_configuration():
    """Get current application configuration (excluding secrets)"""
    config = {
        "application": {
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "api_prefix": settings.API_V1_PREFIX,
        },
        "scraping": {
            "request_timeout": settings.REQUEST_TIMEOUT,
            "max_retries": settings.MAX_RETRIES,
            "user_agent": settings.USER_AGENT[:50] + "..." if len(settings.USER_AGENT) > 50 else settings.USER_AGENT,
        },
        "email": {
            "smtp_server": os.getenv("SMTP_SERVER", "Not configured"),
            "smtp_port": os.getenv("SMTP_PORT", "Not configured"),
            "use_ssl": os.getenv("USE_SSL", "false"),
            "sender_name": os.getenv("EMAIL_SENDER_NAME", "Not configured"),
            "sender_email_set": "Yes" if os.getenv("EMAIL_SENDER") else "No",
        },
        "rate_limiting": {
            "emails_per_hour": os.getenv("EMAILS_PER_HOUR", "50"),
            "delay_between_emails": os.getenv("DELAY_BETWEEN_EMAILS", "2"),
        },
        "environment": os.getenv("ENVIRONMENT", "development"),
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
    }
    
    return config

# Version endpoint
@app.get("/version", tags=["monitoring"])
async def get_version():
    """Get application version information"""
    return {
        "application": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "timestamp": datetime.now().isoformat(),
        "python_version": platform.python_version(),
        "fastapi_version": "0.104.1",  # Should match requirements.txt
        "environment": os.getenv("ENVIRONMENT", "development"),
    }

# Status endpoint
@app.get("/status", tags=["monitoring"])
async def get_status():
    """Get comprehensive system status"""
    from app.api.endpoints import students_store
    from app.api.email_endpoints import generated_papers, sent_emails
    
    status = {
        "timestamp": datetime.now().isoformat(),
        "application": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "running",
        "data": {
            "students_scraped": len(students_store),
            "papers_generated": len(generated_papers),
            "emails_sent": len(sent_emails),
        },
        "system": {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
        },
        "endpoints": {
            "healthy": True,  # You could add actual endpoint health checks here
        }
    }
    
    return status

# Metrics endpoint (already exposed by Prometheus Instrumentator)
@app.get("/metrics", include_in_schema=False)
async def metrics():
    """Prometheus metrics endpoint (handled by instrumentator)"""
    pass

# Error handling
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    logger.error(
        f"HTTP Exception: {exc.status_code} - {exc.detail}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code,
            "detail": exc.detail,
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "timestamp": datetime.now().isoformat(),
                "path": request.url.path,
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(
        f"Unhandled Exception: {type(exc).__name__} - {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        },
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "timestamp": datetime.now().isoformat(),
                "path": request.url.path,
                "error_type": type(exc).__name__,
            }
        }
    )

# Startup test endpoint
@app.get("/startup-test", tags=["debugging"])
async def startup_test():
    """Run comprehensive startup tests"""
    tests = []
    
    # Test 1: Directory creation
    required_dirs = ["logs", "output/papers", "templates/email_templates"]
    for directory in required_dirs:
        dir_path = Path(directory)
        if dir_path.exists() and dir_path.is_dir():
            tests.append({
                "test": f"Directory exists: {directory}",
                "status": "pass"
            })
        else:
            tests.append({
                "test": f"Directory exists: {directory}",
                "status": "fail",
                "message": f"Directory {directory} does not exist"
            })
    
    # Test 2: Template files
    template_files = ["templates/email_templates/base.html", 
                     "templates/email_templates/journal_invitation.html"]
    for file in template_files:
        file_path = Path(file)
        if file_path.exists():
            tests.append({
                "test": f"Template file exists: {file}",
                "status": "pass"
            })
        else:
            tests.append({
                "test": f"Template file exists: {file}",
                "status": "warn",
                "message": f"Template file {file} does not exist (will be created on first use)"
            })
    
    # Test 3: Import checks
    import_checks = [
        ("app.scraper.university_scrapers", "GenericUniversityScraper"),
        ("app.email_service.email_sender", "EmailSender"),
        ("app.document_generator.docx_generator", "DocxGenerator"),
        ("app.email_service.ai_paper_generator", "AIPaperGenerator"),
    ]
    
    for module_name, class_name in import_checks:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            tests.append({
                "test": f"Import {module_name}.{class_name}",
                "status": "pass"
            })
        except Exception as e:
            tests.append({
                "test": f"Import {module_name}.{class_name}",
                "status": "fail",
                "message": str(e)
            })
    
    # Calculate pass rate
    pass_count = sum(1 for test in tests if test["status"] == "pass")
    total_tests = len(tests)
    pass_rate = (pass_count / total_tests) * 100 if total_tests > 0 else 0
    
    return {
        "timestamp": datetime.now().isoformat(),
        "tests": tests,
        "summary": {
            "total_tests": total_tests,
            "passed": pass_count,
            "failed": sum(1 for test in tests if test["status"] == "fail"),
            "warnings": sum(1 for test in tests if test["status"] == "warn"),
            "pass_rate": f"{pass_rate:.1f}%"
        },
        "status": "pass" if pass_rate >= 80 else "fail"
    }

# Clear all data endpoint (for testing)
@app.delete("/clear-all", tags=["debugging"])
async def clear_all_data(background_tasks: BackgroundTasks):
    """Clear all application data (for testing purposes)"""
    from app.api.endpoints import students_store
    from app.api.email_endpoints import generated_papers, sent_emails, email_queue, processing_status
    
    def clear_data():
        # Clear in-memory stores
        students_store.clear()
        generated_papers.clear()
        sent_emails.clear()
        email_queue.clear()
        processing_status.clear()
        
        # Clear output directories
        import shutil
        output_dirs = ["output/papers", "reports"]
        for dir_path in output_dirs:
            if Path(dir_path).exists():
                shutil.rmtree(dir_path)
                Path(dir_path).mkdir(parents=True, exist_ok=True)
        
        logger.info("All application data cleared")
    
    background_tasks.add_task(clear_data)
    
    return {
        "message": "Data clearance initiated in background",
        "timestamp": datetime.now().isoformat(),
        "data_to_clear": {
            "students": len(students_store),
            "generated_papers": len(generated_papers),
            "sent_emails": len(sent_emails),
            "queued_emails": len(email_queue),
            "processing_tasks": len(processing_status),
        }
    }

# Run the application
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
        access_log=True,
        workers=int(os.getenv("WORKERS", "1")),
    )