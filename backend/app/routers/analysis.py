"""Analysis API endpoints for LLM-powered network configuration analysis with HITL workflow"""

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List, Optional
from datetime import datetime
import uuid

from ..db.mongo import db
from ..dependencies.auth import get_current_user, check_project_access
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

router = APIRouter(prefix="/projects/{project_id}/analysis", tags=["analysis"])


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
