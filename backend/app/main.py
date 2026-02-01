from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from datetime import datetime, timezone
import httpx

from .core.settings import settings
from .core.security import hash_password
from .services.ai_engine import call_ollama_chat
from .services.llm_service import llm_service
from .routers import auth, users, projects, documents, project_options, summary, folders, analysis, topology
from .routers.summary import device_router
from .routers.analysis import overview_router
from .db.mongo import connect, close, db

# Configure security scheme for Swagger UI
security_scheme = HTTPBearer()

app = FastAPI(
    title="Manage Network Projects API",
    version="0.1.0",
    swagger_ui_init_oauth={
        "usePkceWithAuthorizationCodeGrant": False,
    }
)

# Add security scheme to OpenAPI schema
app.openapi_schema = None

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description="Network Project Management API with LLM-powered topology generation",
        routes=app.routes,
    )
    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter JWT token obtained from /auth/login endpoint"
        }
    }
    # Add security to all endpoints that require authentication
    for path, path_item in openapi_schema["paths"].items():
        for method, operation in path_item.items():
            if method in ["post", "get", "put", "delete", "patch"]:
                # Skip auth endpoints
                if "/auth/login" in path or "/auth/me" in path:
                    continue
                # Add security requirement
                if "security" not in operation:
                    operation["security"] = [{"bearerAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(documents.router)
app.include_router(project_options.router)
app.include_router(summary.router)
app.include_router(device_router)
app.include_router(folders.router)
app.include_router(analysis.router)
app.include_router(overview_router)
app.include_router(topology.router)
app.include_router(topology.test_router)


async def seed_admin():
    """Create default admin user if not exists."""
    try:
        existing = await db()["users"].find_one({"username": "admin"})
        if not existing:
            password = "admin123"
            password_hash = hash_password(password)
            doc = {
                "username": "admin",
                "email": "admin@net.app",
                "password_hash": password_hash,
                "role": "admin",
                "created_at": datetime.now(timezone.utc),
                "last_login_at": None,
            }
            await db()["users"].insert_one(doc)
            print("✅ Seeded admin user: admin / admin123")
        else:
            print("ℹ️  Admin user already exists")
    except Exception as e:
        print(f"⚠️  Warning: Could not seed admin user: {e}")
        import traceback
        traceback.print_exc()


@app.on_event("startup")
async def startup():
    await connect()
    await seed_admin()

@app.on_event("shutdown")
async def shutdown():
    await close()

@app.get("/")
async def root():
    return {
        "message": "MNP API running",
        "model": {
            "name": settings.AI_MODEL_NAME,
            "version": settings.AI_MODEL_VERSION,
        },
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/ai/test")
async def ai_test():
    reply = await call_ollama_chat("Say hello from Qwen running via Ollama.")
    return {
        "model": llm_service.model_name,
        "reply": reply,
    }


@app.get("/ai/hello")
async def ai_hello():
    """ส่ง Hello ไปที่ LLM แล้วคืนคำตอบกลับ (ใช้ตรวจสอบว่า LLM ใช้งานได้). ไม่ต้อง auth."""
    reply = await call_ollama_chat("Hello")
    return {
        "model": llm_service.model_name,
        "prompt": "Hello",
        "reply": reply,
    }

@app.get("/health/llm")
async def health_llm():
    """Check LLM service health (uses OLLAMA_BASE_URL / OLLAMA_MODEL from env)."""
    base_url = llm_service.base_url
    model_name = llm_service.model_name
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base_url}/api/tags")
            response.raise_for_status()
            models_data = response.json()
            models = [m.get("name", "") for m in models_data.get("models", [])]
            model_available = model_name in models

        return {
            "status": "healthy",
            "ollama_endpoint": base_url,
            "model_name": model_name,
            "model_available": model_available,
            "ollama_accessible": True,
        }
    except httpx.ConnectError:
        return {
            "status": "unhealthy",
            "ollama_endpoint": base_url,
            "model_name": model_name,
            "error": "Cannot connect to Ollama",
            "suggestion": f"Check OLLAMA_BASE_URL={base_url} and network connectivity.",
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "ollama_endpoint": base_url,
            "model_name": model_name,
            "error": str(e),
        }


