"""
FastAPI application main file
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
import logging
import traceback
from api.routes import companies, invoices, vendors, buyers, bank_statements, reconciliation, reports, auth, users

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Bookkeeping API",
    description="Real-time bookkeeping system with invoice processing and bank reconciliation",
    version="1.0.0"
)

# Global exception handler for unhandled exceptions (not HTTPException)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions - log details but return generic message"""
    # Skip HTTPException - those are handled by FastAPI
    from fastapi import HTTPException as FastAPIHTTPException
    if isinstance(exc, FastAPIHTTPException):
        raise exc
    
    # Log the full error with traceback
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {str(exc)}\n"
        f"Path: {request.url.path}\n"
        f"Method: {request.method}\n"
        f"Traceback: {traceback.format_exc()}"
    )
    
    # Return generic error message to client
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal server error occurred. Please try again later or contact support."
        }
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
# Public routes (no auth required)
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])

# Protected routes (auth required)
app.include_router(companies.router, prefix="/api", tags=["companies"])
app.include_router(invoices.router, prefix="/api", tags=["invoices"])
app.include_router(vendors.router, prefix="/api", tags=["vendors"])
app.include_router(buyers.router, prefix="/api", tags=["buyers"])
app.include_router(bank_statements.router, prefix="/api", tags=["bank-statements"])
app.include_router(reconciliation.router, prefix="/api", tags=["reconciliation"])
app.include_router(reports.router, prefix="/api", tags=["reports"])
app.include_router(users.router, prefix="/api", tags=["users"])


@app.get("/api/health")
async def health():
    return {"status": "healthy"}


# Serve static files (after API routes to avoid conflicts)
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    @app.get("/")
    async def index():
        return FileResponse(str(static_dir / "index.html"))
    
    # Serve HTML files directly
    @app.get("/{filename}")
    async def serve_html(filename: str):
        # Don't catch static file requests or API routes
        if filename.startswith('static') or filename.startswith('api') or filename in ['api.js', 'styles.css', 'dashboard.js']:
            raise HTTPException(status_code=404)
        if filename.endswith('.html'):
            file_path = static_dir / filename
            if file_path.exists():
                return FileResponse(str(file_path))
        raise HTTPException(status_code=404)
else:
    @app.get("/")
    async def root():
        return {
            "message": "Bookkeeping API",
            "docs": "/docs",
            "version": "1.0.0"
        }

