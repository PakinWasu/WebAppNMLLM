"""
Server-side LLM job lock: one running job per project, shared across all users and devices.
Used so that any client (same or different user/machine) sees "busy" and cannot start
overlapping LLM work. Lock is stored in MongoDB so it is global.
"""
from datetime import datetime, timedelta, timezone
from ..db.mongo import db

COLLECTION = "llm_job_locks"
LOCK_EXPIRE_MINUTES = 15  # Stale lock is ignored (e.g. crash/timeout)


async def ensure_index():
    """Create unique index on project_id so only one lock per project."""
    try:
        await db()[COLLECTION].create_index("project_id", unique=True)
    except Exception:
        pass  # Index may already exist


async def acquire_llm_lock(project_id: str, user_id: str = None, job_type: str = None) -> bool:
    """
    Try to acquire the LLM lock for this project. Returns True if acquired, False if
    another job is already running (same or different user/device).
    """
    await ensure_index()
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=LOCK_EXPIRE_MINUTES)
    coll = db()[COLLECTION]
    # Remove expired lock so we can take it
    await coll.delete_many({"project_id": project_id, "started_at": {"$lt": cutoff}})
    try:
        await coll.insert_one({
            "project_id": project_id,
            "started_at": now,
            "user_id": user_id,
            "job_type": job_type,
        })
        return True
    except Exception as e:
        # Duplicate key (project_id unique) → lock held by another request
        try:
            from pymongo.errors import DuplicateKeyError
            if isinstance(e, DuplicateKeyError):
                return False
        except ImportError:
            pass
        if "duplicate" in str(e).lower() or "E11000" in str(e):
            return False
        raise


async def release_llm_lock(project_id: str) -> None:
    """Release the LLM lock for this project. Idempotent."""
    await db()[COLLECTION].delete_many({"project_id": project_id})


def _job_type_label(job_type: str) -> str:
    """Human-readable label for tooltip when LLM button is disabled."""
    labels = {
        "project_overview": "Network Overview",
        "project_recommendations": "Recommendations",
        "device_overview": "Device Summary",
        "device_recommendations": "AI Recommendations",
        "device_config_drift": "Config Drift",
        "topology": "Topology",
    }
    return labels.get(job_type, job_type or "LLM task")


async def get_llm_status(project_id: str) -> dict:
    """
    Return current LLM busy status for the project (for all clients to poll).
    { "busy": bool, "since": iso string or null, "job_type": str, "job_label": str }
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=LOCK_EXPIRE_MINUTES)
    doc = await db()[COLLECTION].find_one(
        {"project_id": project_id, "started_at": {"$gte": cutoff}}
    )
    if not doc:
        return {"busy": False, "since": None, "job_type": None, "job_label": None}
    since = doc.get("started_at")
    if since and hasattr(since, "isoformat"):
        since = since.isoformat()
    job_type = doc.get("job_type")
    return {"busy": True, "since": since, "job_type": job_type, "job_label": _job_type_label(job_type)}
