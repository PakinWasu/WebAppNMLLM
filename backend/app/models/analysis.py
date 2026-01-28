"""Models for AI Analysis and Human-in-the-Loop (HITL) Workflow"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum


class AnalysisStatus(str, Enum):
    """Status of analysis in HITL workflow"""
    PENDING_REVIEW = "pending_review"  # AI draft, waiting for human review
    VERIFIED = "verified"  # Human reviewed and confirmed
    REJECTED = "rejected"  # Human rejected the analysis


class AnalysisType(str, Enum):
    """Type of analysis requested"""
    SECURITY_AUDIT = "security_audit"
    PERFORMANCE_REVIEW = "performance_review"
    CONFIGURATION_COMPLIANCE = "configuration_compliance"
    NETWORK_TOPOLOGY = "network_topology"
    BEST_PRACTICES = "best_practices"
    CUSTOM = "custom"


class LLMMetrics(BaseModel):
    """Performance metrics for LLM inference"""
    inference_time_ms: float  # Time taken in milliseconds
    token_usage: Dict[str, int]  # {"prompt_tokens": X, "completion_tokens": Y, "total_tokens": Z}
    model_name: str
    model_version: Optional[str] = None
    timestamp: datetime


class AccuracyMetrics(BaseModel):
    """Accuracy tracking comparing AI output vs Human final version"""
    total_fields: int  # Total fields in analysis
    corrected_fields: int  # Fields that human had to correct
    accuracy_score: float  # Percentage: (total_fields - corrected_fields) / total_fields * 100
    field_changes: List[Dict[str, Any]]  # Detailed list of what was changed
    verified_at: datetime
    verified_by: str


class HumanReview(BaseModel):
    """Human review and edits"""
    reviewer: str
    reviewed_at: datetime
    comments: Optional[str] = None
    changes_made: Dict[str, Any]  # What fields were changed
    status: AnalysisStatus


class AnalysisCreate(BaseModel):
    """Request to create new analysis"""
    device_name: str
    analysis_type: AnalysisType
    custom_prompt: Optional[str] = None  # For CUSTOM analysis type
    include_original_content: bool = False  # Whether to include original_content in context


class AnalysisInDB(BaseModel):
    """Analysis document stored in MongoDB"""
    analysis_id: str
    project_id: str
    device_name: str
    analysis_type: AnalysisType
    
    # Context isolation - only data from this device/project
    context_data: Dict[str, Any]  # Contains parsed_data and optionally original_content
    
    # AI Output (Draft)
    ai_draft: Dict[str, Any]  # The raw AI response
    ai_draft_text: str  # Full text response from AI
    status: AnalysisStatus = AnalysisStatus.PENDING_REVIEW
    
    # Human Review (HITL)
    human_review: Optional[HumanReview] = None
    verified_version: Optional[Dict[str, Any]] = None  # Final version after human edits
    
    # Performance Metrics
    llm_metrics: LLMMetrics
    
    # Accuracy Tracking (only populated after verification)
    accuracy_metrics: Optional[AccuracyMetrics] = None
    
    # Metadata
    created_at: datetime
    created_by: str
    updated_at: datetime


class AnalysisVerifyRequest(BaseModel):
    """Request to verify/edit AI analysis"""
    analysis_id: str
    verified_content: Dict[str, Any]  # Human-edited version
    comments: Optional[str] = None
    status: AnalysisStatus = AnalysisStatus.VERIFIED


class AnalysisPublic(BaseModel):
    """Public analysis model (for API responses)"""
    analysis_id: str
    project_id: str
    device_name: str
    analysis_type: AnalysisType
    ai_draft: Dict[str, Any]
    ai_draft_text: str
    status: AnalysisStatus
    human_review: Optional[HumanReview] = None
    verified_version: Optional[Dict[str, Any]] = None
    llm_metrics: LLMMetrics
    accuracy_metrics: Optional[AccuracyMetrics] = None
    created_at: datetime
    created_by: str
    updated_at: datetime
    
    # Diff information for UI
    diff_summary: Optional[Dict[str, Any]] = None  # Summary of changes between AI draft and verified


class PerformanceLogEntry(BaseModel):
    """Performance log entry for dashboarding"""
    log_id: str
    analysis_id: str
    project_id: str
    device_name: str
    model_name: str
    inference_time_ms: float
    token_usage: Dict[str, int]
    accuracy_score: Optional[float] = None  # Only if verified
    timestamp: datetime
    created_by: str
