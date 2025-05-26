import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse, FileResponse

# Import the app from the app module
from app.main import app as app_instance

# Create a new FastAPI app that will wrap the original app
app = FastAPI()

# Add CORS middleware with permissive settings for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200", "*"],  # Allow Angular dev server and any origin for testing
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["Authorization"],
    max_age=600  # Cache preflight requests for 10 minutes
)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mount the original app
app.mount("/api", app_instance)

# Custom OpenAPI and documentation endpoints
@app.get("/openapi.json")
async def get_open_api_endpoint():
    # Get OpenAPI schema from the mounted app
    openapi = get_openapi(
        title="Travel Request Management System API",
        version="1.0.0",
        description="API for managing travel requests with different types and workflows",
        routes=app_instance.routes,
    )
    
    # Update the paths to include the /api prefix
    paths = {}
    for path, path_item in openapi.get("paths", {}).items():
        paths["/api" + path] = path_item
    
    openapi["paths"] = paths
    return openapi

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="TMS API Documentation",
        swagger_js_url="/static/swagger-ui/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui/swagger-ui.css",
    )

@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url="/openapi.json",
        title="TMS API - ReDoc",
        redoc_js_url="/static/swagger-ui/swagger-ui-bundle.js", # Reusing the same JS file for simplicity
    )

@app.get("/")
async def root():
    return {"message": "Welcome to TMS API. Visit /docs for API documentation."}

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/favicon.png")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
