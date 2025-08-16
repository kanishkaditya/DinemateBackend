from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from config import settings
from api.v1.router import api_router
from database import startup_db_client, shutdown_db_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await startup_db_client()
    yield
    # Shutdown
    await shutdown_db_client()


# Create FastAPI instance
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="DineMate - Intelligent Group Restaurant Recommendations",
    debug=settings.debug,
    lifespan=lifespan
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint for health check"""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "status": "healthy"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "environment": settings.environment}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
