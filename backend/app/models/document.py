from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class DocumentMetadata(BaseModel):
    """Metadata shared across all files in an upload batch"""
    who: str  # Responsible user
    what: str  # Activity type
    where: str | None = None  # Site
    when: str | None = None  # Operational timing
    why: str | None = None  # Purpose
    description: str | None = None  # Description

class DocumentCreate(BaseModel):
    """Request model for document upload"""
    folder_id: str | None = None  # Optional folder ID
    metadata: DocumentMetadata

class DocumentInDB(BaseModel):
    """Document model stored in MongoDB"""
    document_id: str
    project_id: str
    filename: str
    file_path: str
    file_hash: str  # SHA-256 hash
    size: int  # File size in bytes
    content_type: str
    uploader: str
    created_at: datetime
    updated_at: datetime
    version: int  # Version number (1, 2, 3, ...)
    parent_document_id: str | None = None  # Links to original document for versioning
    upload_batch_id: str  # Groups files uploaded together
    metadata: DocumentMetadata
    folder_id: str | None = None
    is_latest: bool  # True for latest version

class DocumentPublic(BaseModel):
    """Public document model (for API responses)"""
    document_id: str
    project_id: str
    filename: str
    size: int
    content_type: str
    uploader: str
    created_at: datetime
    updated_at: datetime
    version: int
    parent_document_id: str | None = None
    upload_batch_id: str
    metadata: DocumentMetadata
    folder_id: str | None = None
    is_latest: bool
    file_hash: str  # For version comparison

class DocumentVersionInfo(BaseModel):
    """Version information for a document"""
    document_id: str
    version: int
    filename: str
    size: int
    uploader: str
    created_at: datetime
    is_latest: bool
    file_hash: str

