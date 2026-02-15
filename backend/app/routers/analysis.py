"""Analysis API endpoints for LLM-powered network configuration analysis with HITL workflow"""

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List, Optional
from datetime import datetime
import uuid
import logging

from ..db.mongo import db
from ..dependencies.auth import get_current_user, check_project_access

logger = logging.getLogger(__name__)

# Max devices sent to LLM to keep prompt size and inference time manageable
MAX_DEVICES_FOR_LLM = 20


def _iso_generated_at(dt) -> Optional[str]:
    """Serialize generated_at to ISO string so frontend polling can compare reliably."""
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)


async def _get_latest_configs_per_device(project_id: str):
    """
    Fetch latest parsed config per device in one aggregation (no N+1).
    Returns list of docs with _id removed, sorted by device_name.
    """
    pipeline = [
        {"$match": {"project_id": project_id}},
        {"$sort": {"device_name": 1, "upload_timestamp": -1}},
        {"$group": {"_id": "$device_name", "doc": {"$first": "$$ROOT"}}},
        {"$replaceRoot": {"newRoot": "$doc"}},
        {"$sort": {"device_name": 1}},
    ]
    cursor = db()["parsed_configs"].aggregate(pipeline)
    devices_data = []
    async for doc in cursor:
        doc.pop("_id", None)
        devices_data.append(doc)
    return devices_data


async def _get_latest_config_for_device(project_id: str, device_name: str):
    """
    Fetch latest parsed config for a single device. Returns one doc (dict) or None.
    """
    pipeline = [
        {"$match": {"project_id": project_id, "device_name": device_name}},
        {"$sort": {"upload_timestamp": -1}},
        {"$limit": 1},
    ]
    cursor = db()["parsed_configs"].aggregate(pipeline)
    async for doc in cursor:
        doc.pop("_id", None)
        return doc
    return None
from ..models.analysis import (
    AnalysisCreate,
    AnalysisInDB,
    AnalysisPublic,
    AnalysisVerifyRequest,
    AnalysisStatus,
    AnalysisType,
    LLMMetrics,
    AccuracyMetrics,
    HumanReview
)
from ..services.llm_service import llm_service
from ..services.accuracy_tracker import accuracy_tracker
from ..services.llm_lock import acquire_llm_lock, release_llm_lock, get_llm_status as get_llm_lock_status

router = APIRouter(prefix="/projects/{project_id}/analysis", tags=["analysis"])

# Project-Level Analysis Router
overview_router = APIRouter(prefix="/projects/{project_id}/analyze", tags=["analyze"])


@overview_router.get("/llm-status")
async def get_project_llm_status(
    project_id: str,
    user=Depends(get_current_user),
):
    """Return whether an LLM job is currently running for this project (any user/device). Used to sync UI across clients."""
    await check_project_access(project_id, user)
    return await get_llm_lock_status(project_id)


@overview_router.get("/overview")
async def get_project_overview(
    project_id: str,
    user=Depends(get_current_user)
):
    """Get saved project overview from database."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        await check_project_access(project_id, user)
        
        # Get saved result from database
        saved_result = await db()["llm_results"].find_one(
            {"project_id": project_id, "result_type": "project_overview"},
            sort=[("generated_at", -1)]
        )
        
        if not saved_result:
            raise HTTPException(
                status_code=404,
                detail="No saved overview found. Generate one first."
            )
        
        result_data = saved_result.get("result_data", {})
        # New format: structured overview (topology, stats, protocols, etc.)
        if result_data.get("topology") is not None or result_data.get("key_insights") is not None:
            overview = result_data
            overview_text = None
        else:
            overview = None
            overview_text = result_data.get("overview_text", "No overview available.")
        
        return {
            "overview": overview,
            "overview_text": overview_text,
            "metrics": saved_result.get("metrics", {}),
            "devices_analyzed": saved_result.get("result_data", {}).get("devices_analyzed", 0),
            "project_id": project_id,
            "generated_at": saved_result.get("generated_at")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching project overview for project {project_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch overview: {str(e)}"
        )


@overview_router.get("/device-overview")
async def get_device_overview(
    project_id: str,
    device_name: str,
    user=Depends(get_current_user)
):
    """Get saved per-device overview from database."""
    try:
        await check_project_access(project_id, user)
        saved_result = await db()["llm_results"].find_one(
            {
                "project_id": project_id,
                "result_type": "device_overview",
                "result_data.device_name": device_name,
            },
            sort=[("generated_at", -1)],
        )
        if not saved_result:
            raise HTTPException(
                status_code=404,
                detail="No saved overview for this device. Generate one first.",
            )
        result_data = saved_result.get("result_data", {})
        if result_data.get("role") is not None or result_data.get("config_highlights") is not None:
            overview = {k: v for k, v in result_data.items() if k != "device_name"}
            overview_text = None
        else:
            overview = None
            overview_text = result_data.get("overview_text", "No overview available.")
        return {
            "overview": overview,
            "overview_text": overview_text,
            "metrics": saved_result.get("metrics", {}),
            "project_id": project_id,
            "device_name": device_name,
            "generated_at": _iso_generated_at(saved_result.get("generated_at")),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching device overview for project {project_id} device {device_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch device overview: {str(e)}")


@overview_router.post("/device-overview")
async def analyze_device_overview(
    project_id: str,
    body: dict = Body(default=None),
    user=Depends(get_current_user),
):
    """
    Per-device analysis: LLM summary for a single device (More Detail page - Device Summary tab).
    Body: { "device_name": "CORE1" }
    """
    device_name = (body or {}).get("device_name") or (body or {}).get("device_id")
    if not device_name:
        raise HTTPException(status_code=400, detail="device_name (or device_id) required in body.")
    await check_project_access(project_id, user)
    if not await acquire_llm_lock(project_id, user.get("username"), "device_overview"):
        raise HTTPException(
            status_code=409,
            detail="An LLM job is already running for this project (another user or tab). Please wait until it finishes.",
        )
    try:
        doc = await _get_latest_config_for_device(project_id, device_name)
        if not doc:
            raise HTTPException(
                status_code=404,
                detail=f"No configuration found for device '{device_name}'. Upload config first.",
            )
        # Build same shape as _get_latest_configs_per_device for LLM
        device_data = {
            "device_name": doc.get("device_name"),
            "device_overview": doc.get("device_overview", {}),
            "interfaces": doc.get("interfaces", []),
            "neighbors": doc.get("neighbors", []),
            "routing": doc.get("routing", {}),
            "vlans": doc.get("vlans", {}),
            "stp": doc.get("stp", {}),
        }
        result = await llm_service.analyze_device_overview(
            [device_data],
            project_id=project_id,
            device_name=device_name,
        )
        if "error" in result.get("parsed_response", {}):
            raise HTTPException(
                status_code=500,
                detail=result.get("content", "LLM device analysis failed."),
            )
        overview_data = result.get("parsed_response") or {}
        overview_data["device_name"] = device_name
        metrics = result.get("metrics", {})
        summary = overview_data.get("role") or (overview_data.get("config_highlights") or [None])[0] or "Device overview"
        summary_str = summary[:500] if isinstance(summary, str) else str(summary)[:500]
        from ..services.topology_service import topology_service
        await topology_service._save_llm_result(
            project_id=project_id,
            result_type="device_overview",
            result_data=overview_data,
            analysis_summary=summary_str,
            metrics=metrics,
            llm_used=True,
        )
        await db()["llm_results"].update_one(
            {
                "project_id": project_id,
                "result_type": "device_overview",
                "result_data.device_name": device_name,
            },
            {
                "$set": {
                    "result_data": overview_data,
                    "analysis_summary": summary_str,
                    "metrics": metrics,
                    "llm_used": True,
                    "generated_at": datetime.utcnow(),
                }
            },
            upsert=True,
        )
        return {
            "overview": {k: v for k, v in overview_data.items() if k != "device_name"},
            "overview_text": None,
            "metrics": metrics,
            "project_id": project_id,
            "device_name": device_name,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error in analyze_device_overview for project {project_id} device {device_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Device overview analysis failed: {str(e)}")
    finally:
        await release_llm_lock(project_id)


@overview_router.get("/device-recommendations")
async def get_device_recommendations(
    project_id: str,
    device_name: str,
    user=Depends(get_current_user),
):
    """Get saved per-device recommendations from database."""
    try:
        await check_project_access(project_id, user)
        saved_result = await db()["llm_results"].find_one(
            {
                "project_id": project_id,
                "result_type": "device_recommendations",
                "result_data.device_name": device_name,
            },
            sort=[("generated_at", -1)],
        )
        if not saved_result:
            raise HTTPException(
                status_code=404,
                detail="No saved recommendations for this device. Generate one first.",
            )
        result_data = saved_result.get("result_data", {})
        recommendations = result_data.get("recommendations", [])
        return {
            "recommendations": recommendations,
            "metrics": saved_result.get("metrics", {}),
            "project_id": project_id,
            "device_name": device_name,
            "generated_at": _iso_generated_at(saved_result.get("generated_at")),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching device recommendations for project {project_id} device {device_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch device recommendations: {str(e)}")


@overview_router.post("/device-recommendations")
async def analyze_device_recommendations(
    project_id: str,
    body: dict = Body(default=None),
    user=Depends(get_current_user),
):
    """
    Per-device recommendations: LLM finds flaws and recommends improvements (More Detail - AI Recommendations tab).
    Body: { "device_name": "CORE1" }
    """
    device_name = (body or {}).get("device_name") or (body or {}).get("device_id")
    if not device_name:
        raise HTTPException(status_code=400, detail="device_name (or device_id) required in body.")
    await check_project_access(project_id, user)
    if not await acquire_llm_lock(project_id, user.get("username"), "device_recommendations"):
        raise HTTPException(
            status_code=409,
            detail="An LLM job is already running for this project (another user or tab). Please wait until it finishes.",
        )
    try:
        doc = await _get_latest_config_for_device(project_id, device_name)
        if not doc:
            raise HTTPException(
                status_code=404,
                detail=f"No configuration found for device '{device_name}'. Upload config first.",
            )
        device_data = {
            "device_name": doc.get("device_name"),
            "device_overview": doc.get("device_overview", {}),
            "interfaces": doc.get("interfaces", []),
            "neighbors": doc.get("neighbors", []),
            "routing": doc.get("routing", {}),
            "vlans": doc.get("vlans", {}),
            "stp": doc.get("stp", {}),
        }
        result = await llm_service.analyze_device_recommendations(
            [device_data],
            project_id=project_id,
            device_name=device_name,
        )
        if "error" in result.get("parsed_response", {}):
            raise HTTPException(
                status_code=500,
                detail=result.get("content", "LLM device recommendations failed."),
            )
        recommendations = (result.get("parsed_response") or {}).get("recommendations", [])
        metrics = result.get("metrics", {})
        validated = []
        for rec in recommendations:
            if isinstance(rec, dict):
                validated.append({
                    "severity": (rec.get("severity") or "medium").lower(),
                    "issue": (rec.get("issue") or "").strip(),
                    "recommendation": (rec.get("recommendation") or "").strip(),
                })
        from ..services.topology_service import topology_service
        await topology_service._save_llm_result(
            project_id=project_id,
            result_type="device_recommendations",
            result_data={"recommendations": validated, "device_name": device_name},
            analysis_summary=f"{len(validated)} recommendations",
            metrics=metrics,
            llm_used=True,
        )
        await db()["llm_results"].update_one(
            {
                "project_id": project_id,
                "result_type": "device_recommendations",
                "result_data.device_name": device_name,
            },
            {
                "$set": {
                    "result_data": {"recommendations": validated, "device_name": device_name},
                    "analysis_summary": f"{len(validated)} recommendations",
                    "metrics": metrics,
                    "llm_used": True,
                    "generated_at": datetime.utcnow(),
                }
            },
            upsert=True,
        )
        return {
            "recommendations": validated,
            "metrics": metrics,
            "project_id": project_id,
            "device_name": device_name,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error in analyze_device_recommendations for project {project_id} device {device_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Device recommendations analysis failed: {str(e)}")
    finally:
        await release_llm_lock(project_id)


@overview_router.get("/device-config-drift")
async def get_device_config_drift(
    project_id: str,
    device_name: str,
    user=Depends(get_current_user),
):
    """Get saved config drift summary for device (latest vs previous config)."""
    try:
        await check_project_access(project_id, user)
        saved_result = await db()["llm_results"].find_one(
            {
                "project_id": project_id,
                "result_type": "device_config_drift",
                "result_data.device_name": device_name,
            },
            sort=[("generated_at", -1)],
        )
        if not saved_result:
            raise HTTPException(
                status_code=404,
                detail="No saved config drift for this device. Generate one first.",
            )
        result_data = saved_result.get("result_data", {})
        return {
            "device_name": device_name,
            "from_filename": result_data.get("from_filename"),
            "to_filename": result_data.get("to_filename"),
            "changes": result_data.get("changes", []),
            "metrics": saved_result.get("metrics", {}),
            "project_id": project_id,
            "generated_at": _iso_generated_at(saved_result.get("generated_at")),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching device config drift for project {project_id} device {device_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch config drift: {str(e)}")


@overview_router.post("/device-config-drift")
async def analyze_device_config_drift(
    project_id: str,
    body: dict = Body(default=None),
    user=Depends(get_current_user),
):
    """
    Summarize config drift between two raw config files (More Detail - Config Drift tab).
    Uses raw uploaded file content, not parsed data.
    Body (option A - two versions of same document):
      { "device_name": "CORE1", "document_id": "...", "from_version": 1, "to_version": 2 }
      from_version = older, to_version = newer (e.g. v1 and v2).
    Body (option B - two documents):
      { "device_name": "CORE1", "from_document_id": "...", "to_document_id": "..." }
    """
    data = body or {}
    device_name = data.get("device_name") or data.get("device_id")
    if not device_name:
        raise HTTPException(status_code=400, detail="device_name (or device_id) required in body.")
    await check_project_access(project_id, user)
    if not await acquire_llm_lock(project_id, user.get("username"), "device_config_drift"):
        raise HTTPException(
            status_code=409,
            detail="An LLM job is already running for this project (another user or tab). Please wait until it finishes.",
        )
    try:
        from ..services.document_storage import read_document_file

        document_id = data.get("document_id")
        from_version = data.get("from_version")
        to_version = data.get("to_version")
        from_doc_id = data.get("from_document_id")
        to_doc_id = data.get("to_document_id")

        if document_id is not None and from_version is not None and to_version is not None:
            # Option A: two versions of the same document (raw config from version history)
            old_raw = await read_document_file(project_id, document_id, int(from_version))
            new_raw = await read_document_file(project_id, document_id, int(to_version))
            if not old_raw or not new_raw:
                raise HTTPException(
                    status_code=404,
                    detail="Could not read one or both document versions. Check document_id and version numbers.",
                )
            old_content = old_raw.decode("utf-8", errors="replace")
            new_content = new_raw.decode("utf-8", errors="replace")
            doc = await db()["documents"].find_one({"project_id": project_id, "document_id": document_id})
            base_name = (doc or {}).get("filename", "config")
            from_filename = f"{base_name} (v{from_version})"
            to_filename = f"{base_name} (v{to_version})"
        elif from_doc_id and to_doc_id:
            # Option B: two different documents (legacy)
            old_raw = await read_document_file(project_id, from_doc_id)
            new_raw = await read_document_file(project_id, to_doc_id)
            if not old_raw or not new_raw:
                raise HTTPException(
                    status_code=404,
                    detail="Could not read one or both document files. Check document IDs.",
                )
            old_content = old_raw.decode("utf-8", errors="replace")
            new_content = new_raw.decode("utf-8", errors="replace")
            from_doc = await db()["documents"].find_one({"project_id": project_id, "document_id": from_doc_id})
            to_doc = await db()["documents"].find_one({"project_id": project_id, "document_id": to_doc_id})
            from_filename = (from_doc or {}).get("filename", "backup-old.txt")
            to_filename = (to_doc or {}).get("filename", "backup-new.txt")
        else:
            raise HTTPException(
                status_code=400,
                detail="Provide either (document_id, from_version, to_version) for version history, or (from_document_id, to_document_id).",
            )

        result = await llm_service.analyze_config_drift(
            old_content,
            new_content,
            device_name,
            from_filename=from_filename,
            to_filename=to_filename,
        )
        if "error" in result.get("parsed_response", {}):
            raise HTTPException(
                status_code=500,
                detail=result.get("content", "LLM config drift analysis failed."),
            )
        changes = (result.get("parsed_response") or {}).get("changes", [])
        metrics = result.get("metrics", {})

        from ..services.topology_service import topology_service
        await topology_service._save_llm_result(
            project_id=project_id,
            result_type="device_config_drift",
            result_data={
                "device_name": device_name,
                "from_filename": from_filename,
                "to_filename": to_filename,
                "changes": changes,
            },
            analysis_summary=f"{len(changes)} changes",
            metrics=metrics,
            llm_used=True,
        )
        await db()["llm_results"].update_one(
            {
                "project_id": project_id,
                "result_type": "device_config_drift",
                "result_data.device_name": device_name,
            },
            {
                "$set": {
                    "result_data": {
                        "device_name": device_name,
                        "from_filename": from_filename,
                        "to_filename": to_filename,
                        "changes": changes,
                    },
                    "analysis_summary": f"{len(changes)} changes",
                    "metrics": metrics,
                    "llm_used": True,
                    "generated_at": datetime.utcnow(),
                }
            },
            upsert=True,
        )
        return {
            "device_name": device_name,
            "from_filename": from_filename,
            "to_filename": to_filename,
            "changes": changes,
            "metrics": metrics,
            "project_id": project_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error in analyze_device_config_drift for project {project_id} device {device_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Config drift analysis failed: {str(e)}")
    finally:
        await release_llm_lock(project_id)


@overview_router.get("/recommendations")
async def get_project_recommendations(
    project_id: str,
    user=Depends(get_current_user)
):
    """Get saved project recommendations from database."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        await check_project_access(project_id, user)
        
        # Get saved result from database
        saved_result = await db()["llm_results"].find_one(
            {"project_id": project_id, "result_type": "project_recommendations"},
            sort=[("generated_at", -1)]
        )
        
        if not saved_result:
            raise HTTPException(
                status_code=404,
                detail="No saved recommendations found. Generate one first."
            )
        
        result_data = saved_result.get("result_data", {})
        recommendations = result_data.get("recommendations", [])
        
        return {
            "recommendations": recommendations,
            "metrics": saved_result.get("metrics", {}),
            "devices_analyzed": saved_result.get("result_data", {}).get("devices_analyzed", 0),
            "project_id": project_id,
            "generated_at": _iso_generated_at(saved_result.get("generated_at"))
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching project recommendations for project {project_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch recommendations: {str(e)}"
        )


@overview_router.post("/overview")
async def analyze_project_overview(
    project_id: str,
    user=Depends(get_current_user)
):
    """
    Project-Level Analysis - Network Overview only (Scope 2.3.5.1).
    Analyzes ALL devices in the project collectively to provide:
    - Network Overview: Architecture, topology style, key protocols
    """
    import logging
    logger = logging.getLogger(__name__)
    
    await check_project_access(project_id, user)
    if not await acquire_llm_lock(project_id, user.get("username"), "project_overview"):
        raise HTTPException(
            status_code=409,
            detail="An LLM job is already running for this project (another user or tab). Please wait until it finishes.",
        )
    try:
        try:
            devices_data = await _get_latest_configs_per_device(project_id)
        except Exception as db_error:
            logger.exception(f"Database error while fetching devices for project {project_id}: {db_error}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch device configurations from database: {str(db_error)}"
            )
        
        if not devices_data:
            raise HTTPException(
                status_code=404,
                detail="No devices found in project. Upload configuration files first."
            )
        
        total_devices = len(devices_data)
        if total_devices > MAX_DEVICES_FOR_LLM:
            devices_data = devices_data[:MAX_DEVICES_FOR_LLM]
            logger.info(f"Project {project_id}: limiting LLM overview to first {MAX_DEVICES_FOR_LLM} of {total_devices} devices")
        
        logger.info(f"Calling LLM service for project overview. Project: {project_id}, Devices: {len(devices_data)}")
        
        # Call LLM service for project-level overview analysis
        try:
            result = await llm_service.analyze_project_overview(
                devices_data=devices_data,
                project_id=project_id
            )
        except Exception as llm_error:
            logger.exception(f"LLM service error for project {project_id}: {llm_error}")
            raise HTTPException(
                status_code=500,
                detail=f"LLM analysis failed: {str(llm_error)}"
            )
        
        # Check for errors in the result
        parsed_response = result.get("parsed_response", {})
        if "error" in parsed_response:
            error_message = result.get("content", "LLM analysis failed")
            logger.error(f"LLM returned error for project {project_id}: {error_message}")
            raise HTTPException(
                status_code=500,
                detail=error_message
            )
        
        # Parsed response is the normalized structure (topology, stats, protocols, health_status, key_insights, recommendations)
        overview_data = parsed_response
        
        # Save to database for persistence
        try:
            from ..services.topology_service import topology_service
            summary = overview_data.get("health_status") or (overview_data.get("key_insights") or [None])[0] or "Overview"
            await topology_service._save_llm_result(
                project_id=project_id,
                result_type="project_overview",
                result_data=overview_data,
                analysis_summary=summary[:500] if isinstance(summary, str) else str(summary)[:500],
                metrics=result.get("metrics", {}),
                llm_used=True
            )
            logger.info(f"Saved project overview to database for project {project_id}")
        except Exception as save_error:
            logger.warning(f"Failed to save project overview to database: {save_error}")
        
        logger.info(f"Successfully generated overview for project {project_id}")
        
        return {
            "overview": overview_data,
            "overview_text": None,
            "metrics": result.get("metrics", {}),
            "devices_analyzed": len(devices_data),
            "project_id": project_id,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in analyze_project_overview for project {project_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
    finally:
        await release_llm_lock(project_id)


# Full Project Analysis endpoints removed - use /analyze/overview and /analyze/recommendations separately

@overview_router.post("/recommendations")
async def analyze_project_recommendations(
    project_id: str,
    user=Depends(get_current_user)
):
    """
    Project-Level Analysis - Recommendations only (Scope 2.3.5.2).
    Analyzes ALL devices in the project collectively to provide:
    - Gap & Integrity Analysis: Missing configurations, errors, actionable fixes
    """
    import logging
    logger = logging.getLogger(__name__)
    
    await check_project_access(project_id, user)
    if not await acquire_llm_lock(project_id, user.get("username"), "project_recommendations"):
        raise HTTPException(
            status_code=409,
            detail="An LLM job is already running for this project (another user or tab). Please wait until it finishes.",
        )
    try:
        try:
            devices_data = await _get_latest_configs_per_device(project_id)
        except Exception as db_error:
            logger.exception(f"Database error while fetching devices for project {project_id}: {db_error}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch device configurations from database: {str(db_error)}"
            )
        
        if not devices_data:
            raise HTTPException(
                status_code=404,
                detail="No devices found in project. Upload configuration files first."
            )
        
        total_devices = len(devices_data)
        if total_devices > MAX_DEVICES_FOR_LLM:
            devices_data = devices_data[:MAX_DEVICES_FOR_LLM]
            logger.info(f"Project {project_id}: limiting LLM recommendations to first {MAX_DEVICES_FOR_LLM} of {total_devices} devices")
        
        logger.info(f"Calling LLM service for project recommendations. Project: {project_id}, Devices: {len(devices_data)}")
        
        try:
            result = await llm_service.analyze_project_recommendations(
                devices_data=devices_data,
                project_id=project_id
            )
        except Exception as llm_error:
            logger.exception(f"LLM service error for project {project_id}: {llm_error}")
            raise HTTPException(
                status_code=500,
                detail=f"LLM analysis failed: {str(llm_error)}"
            )
        
        # Check for errors in the result
        parsed_response = result.get("parsed_response", {})
        if "error" in parsed_response:
            error_message = result.get("content", "LLM analysis failed")
            logger.error(f"LLM returned error for project {project_id}: {error_message}")
            raise HTTPException(
                status_code=500,
                detail=error_message
            )
        
        # Extract parsed response
        recommendations = parsed_response.get("recommendations", [])
        
        # Ensure recommendations is a list
        if not isinstance(recommendations, list):
            logger.warning(f"LLM returned non-list recommendations for project {project_id}: {type(recommendations)}")
            recommendations = []
        
        # Validate recommendation structure (issue + recommendation for UI; keep message for backward compat)
        validated_recommendations = []
        for rec in recommendations:
            if isinstance(rec, dict):
                issue = (rec.get("issue") or "").strip()
                recommendation = (rec.get("recommendation") or rec.get("message") or "").strip()
                validated_recommendations.append({
                    "severity": (rec.get("severity") or "medium").lower(),
                    "issue": issue,
                    "recommendation": recommendation,
                    "message": recommendation or issue,
                    "device": rec.get("device", "all"),
                })
            else:
                logger.warning(f"Invalid recommendation format: {rec}")
        
        # Save to database for persistence
        try:
            from ..services.topology_service import topology_service
            await topology_service._save_llm_result(
                project_id=project_id,
                result_type="project_recommendations",
                result_data={"recommendations": validated_recommendations},
                analysis_summary=f"{len(validated_recommendations)} recommendations generated",
                metrics=result.get("metrics", {}),
                llm_used=True
            )
            logger.info(f"Saved project recommendations to database for project {project_id}")
        except Exception as save_error:
            logger.warning(f"Failed to save project recommendations to database: {save_error}")
            # Continue even if save fails
        
        logger.info(f"Successfully generated {len(validated_recommendations)} recommendations for project {project_id}")
        
        return {
            "recommendations": validated_recommendations,
            "metrics": result.get("metrics", {}),
            "devices_analyzed": len(devices_data),
            "project_id": project_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in analyze_project_recommendations for project {project_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
    finally:
        await release_llm_lock(project_id)


@router.post("", response_model=AnalysisPublic)
async def create_analysis(
    project_id: str,
    request: AnalysisCreate,
    user=Depends(get_current_user)
):
    """
    Create a new AI analysis for a device configuration.
    Implements context isolation - only analyzes data from the specified device.
    """
    await check_project_access(project_id, user)
    
    # Get device configuration data (strict context isolation)
    device_config = await db()["parsed_configs"].find_one(
        {
            "project_id": project_id,
            "device_name": request.device_name
        },
        sort=[("upload_timestamp", -1)]  # Get latest version
    )
    
    if not device_config:
        raise HTTPException(
            status_code=404,
            detail=f"Device '{request.device_name}' not found in project"
        )
    
    # Extract context data (only from this device/project)
    parsed_data = device_config.get("parsed_data", {})
    original_content = None
    
    if request.include_original_content:
        original_content = device_config.get("original_content")
    
    # Call LLM service for analysis
    result = await llm_service.analyze_configuration(
        parsed_data=parsed_data,
        original_content=original_content,
        analysis_type=request.analysis_type.value,
        device_name=request.device_name,
        custom_prompt=request.custom_prompt,
        include_original=request.include_original_content
    )
    
    # Create analysis document
    analysis_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    llm_metrics = LLMMetrics(
        inference_time_ms=result["metrics"]["inference_time_ms"],
        token_usage=result["metrics"]["token_usage"],
        model_name=result["metrics"]["model_name"],
        timestamp=result["metrics"]["timestamp"]
    )
    
    analysis_doc = {
        "analysis_id": analysis_id,
        "project_id": project_id,
        "device_name": request.device_name,
        "analysis_type": request.analysis_type.value,
        "context_data": {
            "parsed_data": parsed_data,
            "original_content_included": request.include_original_content
        },
        "ai_draft": result["parsed_response"],
        "ai_draft_text": result["content"],
        "status": AnalysisStatus.PENDING_REVIEW.value,
        "human_review": None,
        "verified_version": None,
        "llm_metrics": llm_metrics.dict(),
        "accuracy_metrics": None,
        "created_at": now,
        "created_by": user["username"],
        "updated_at": now
    }
    
    # Save to MongoDB
    await db()["analyses"].insert_one(analysis_doc)
    
    # Log performance metrics
    await _log_performance_metrics(
        analysis_id=analysis_id,
        project_id=project_id,
        device_name=request.device_name,
        llm_metrics=llm_metrics,
        user=user["username"]
    )
    
    # Return public model
    return AnalysisPublic(**analysis_doc)


@router.post("/verify", response_model=AnalysisPublic)
async def verify_analysis(
    project_id: str,
    request: AnalysisVerifyRequest,
    user=Depends(get_current_user)
):
    """
    Human-in-the-Loop: Verify, edit, and confirm AI analysis.
    Calculates accuracy metrics comparing AI draft vs human final version.
    """
    await check_project_access(project_id, user)
    
    # Get analysis
    analysis = await db()["analyses"].find_one({
        "analysis_id": request.analysis_id,
        "project_id": project_id
    })
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    if analysis["status"] == AnalysisStatus.VERIFIED.value:
        raise HTTPException(
            status_code=400,
            detail="Analysis already verified"
        )
    
    # Calculate accuracy metrics
    ai_draft = analysis.get("ai_draft", {})
    accuracy_data = accuracy_tracker.calculate_accuracy(
        ai_draft=ai_draft,
        verified_version=request.verified_content,
        reviewer=user["username"]
    )
    
    # Generate diff summary for UI
    diff_summary = accuracy_tracker.generate_diff_summary(
        ai_draft=ai_draft,
        verified_version=request.verified_content
    )
    
    # Create human review
    human_review = HumanReview(
        reviewer=user["username"],
        reviewed_at=datetime.utcnow(),
        comments=request.comments,
        changes_made=diff_summary,
        status=request.status
    )
    
    # Update analysis
    update_data = {
        "status": request.status.value,
        "human_review": human_review.dict(),
        "verified_version": request.verified_content,
        "accuracy_metrics": AccuracyMetrics(**accuracy_data).dict(),
        "updated_at": datetime.utcnow()
    }
    
    await db()["analyses"].update_one(
        {"analysis_id": request.analysis_id},
        {"$set": update_data}
    )
    
    # Update performance log with accuracy score
    await db()["performance_logs"].update_one(
        {"analysis_id": request.analysis_id},
        {"$set": {"accuracy_score": accuracy_data["accuracy_score"]}}
    )
    
    # Get updated analysis
    updated_analysis = await db()["analyses"].find_one({
        "analysis_id": request.analysis_id
    })
    updated_analysis.pop("_id", None)
    
    # Add diff summary for UI
    updated_analysis["diff_summary"] = diff_summary
    
    return AnalysisPublic(**updated_analysis)


@router.get("", response_model=List[AnalysisPublic])
async def list_analyses(
    project_id: str,
    device_name: Optional[str] = None,
    status: Optional[AnalysisStatus] = None,
    analysis_type: Optional[AnalysisType] = None,
    user=Depends(get_current_user)
):
    """List all analyses for a project with optional filters"""
    await check_project_access(project_id, user)
    
    query = {"project_id": project_id}
    
    if device_name:
        query["device_name"] = device_name
    if status:
        query["status"] = status.value
    if analysis_type:
        query["analysis_type"] = analysis_type.value
    
    analyses = []
    async for doc in db()["analyses"].find(
        query,
        sort=[("created_at", -1)]
    ):
        doc.pop("_id", None)
        
        # Generate diff summary if verified
        if doc.get("status") == AnalysisStatus.VERIFIED.value and doc.get("verified_version"):
            diff_summary = accuracy_tracker.generate_diff_summary(
                doc.get("ai_draft", {}),
                doc.get("verified_version", {})
            )
            doc["diff_summary"] = diff_summary
        
        analyses.append(AnalysisPublic(**doc))
    
    return analyses


@router.get("/{analysis_id}", response_model=AnalysisPublic)
async def get_analysis(
    project_id: str,
    analysis_id: str,
    user=Depends(get_current_user)
):
    """Get a specific analysis by ID"""
    await check_project_access(project_id, user)
    
    analysis = await db()["analyses"].find_one({
        "analysis_id": analysis_id,
        "project_id": project_id
    })
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    analysis.pop("_id", None)
    
    # Generate diff summary if verified
    if analysis.get("status") == AnalysisStatus.VERIFIED.value and analysis.get("verified_version"):
        diff_summary = accuracy_tracker.generate_diff_summary(
            analysis.get("ai_draft", {}),
            analysis.get("verified_version", {})
        )
        analysis["diff_summary"] = diff_summary
    
    return AnalysisPublic(**analysis)


@router.get("/performance/metrics", response_model=List[dict])
async def get_performance_metrics(
    project_id: str,
    device_name: Optional[str] = None,
    limit: int = 100,
    user=Depends(get_current_user)
):
    """Get performance metrics for dashboarding"""
    await check_project_access(project_id, user)
    
    query = {"project_id": project_id}
    if device_name:
        query["device_name"] = device_name
    
    metrics = []
    async for doc in db()["performance_logs"].find(
        query,
        sort=[("timestamp", -1)],
        limit=limit
    ):
        doc.pop("_id", None)
        metrics.append(doc)
    
    return metrics


async def _log_performance_metrics(
    analysis_id: str,
    project_id: str,
    device_name: str,
    llm_metrics: LLMMetrics,
    user: str
):
    """Log performance metrics to performance_logs collection"""
    log_id = str(uuid.uuid4())
    
    log_entry = {
        "log_id": log_id,
        "analysis_id": analysis_id,
        "project_id": project_id,
        "device_name": device_name,
        "model_name": llm_metrics.model_name,
        "inference_time_ms": llm_metrics.inference_time_ms,
        "token_usage": llm_metrics.token_usage,
        "accuracy_score": None,  # Will be updated after verification
        "timestamp": llm_metrics.timestamp,
        "created_by": user
    }
    
    await db()["performance_logs"].insert_one(log_entry)
