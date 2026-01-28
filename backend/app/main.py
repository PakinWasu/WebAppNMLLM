from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone

from .core.settings import settings
from .core.security import hash_password
from .services.ai_engine import call_ollama_chat
from .routers import auth, users, projects, documents, project_options, summary, folders, analysis, topology
from .db.mongo import connect, close, db

app = FastAPI(
    title="Manage Network Projects API",
    version="0.1.0"
)

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
app.include_router(folders.router)
app.include_router(analysis.router)
app.include_router(topology.router)


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
        "model": settings.AI_MODEL_NAME,
        "reply": reply,
    }


