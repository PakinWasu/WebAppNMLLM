import hashlib
import uuid
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from fastapi import UploadFile
import aiofiles

from ..db.mongo import db
from ..models.document import DocumentInDB, DocumentMetadata

STORAGE_BASE = Path("storage")


# ============================================================================
# Smart Date Extraction from Filenames
# ============================================================================

# Regex patterns for date extraction (ordered by specificity)
DATE_PATTERNS = [
    # ISO format: YYYY-MM-DD or YYYY_MM_DD (with optional time)
    (r'(\d{4})[-_](\d{2})[-_](\d{2})(?:[-_T](\d{2})[-_:](\d{2})(?:[-_:](\d{2}))?)?', 'YMD'),
    # Compact ISO: YYYYMMDD (with optional time HHMMSS)
    (r'(\d{4})(\d{2})(\d{2})(?:[-_T]?(\d{2})(\d{2})(\d{2}))?', 'YMD_COMPACT'),
    # European/Thai: DD-MM-YYYY or DD_MM_YYYY
    (r'(\d{2})[-_](\d{2})[-_](\d{4})', 'DMY'),
    # Compact European: DDMMYYYY
    (r'(\d{2})(\d{2})(\d{4})', 'DMY_COMPACT'),
    # US format: MM-DD-YYYY or MM_DD_YYYY
    (r'(\d{2})[-_](\d{2})[-_](\d{4})', 'MDY'),
]


def extract_date_from_filename(filename: str) -> Optional[datetime]:
    """
    Extract date/time from filename using multiple regex patterns.
    Returns datetime object if found, None otherwise.
    
    Supports formats:
    - YYYY-MM-DD, YYYY_MM_DD, YYYYMMDD
    - YYYY-MM-DD_HH-MM-SS, YYYYMMDD_HHMMSS
    - DD-MM-YYYY, DD_MM_YYYY, DDMMYYYY
    - 2026-01-27_topo_realEDGE.log -> 2026-01-27
    - CORE2_20260215.txt -> 2026-02-15
    """
    if not filename:
        return None
    
    # Remove extension for cleaner matching
    name_without_ext = Path(filename).stem
    
    # Try each pattern
    for pattern, fmt in DATE_PATTERNS:
        match = re.search(pattern, name_without_ext)
        if match:
            groups = match.groups()
            try:
                if fmt == 'YMD':
                    year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                    hour = int(groups[3]) if groups[3] else 0
                    minute = int(groups[4]) if groups[4] else 0
                    second = int(groups[5]) if groups[5] else 0
                elif fmt == 'YMD_COMPACT':
                    year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                    hour = int(groups[3]) if groups[3] else 0
                    minute = int(groups[4]) if groups[4] else 0
                    second = int(groups[5]) if groups[5] else 0
                elif fmt == 'DMY' or fmt == 'DMY_COMPACT':
                    day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
                    hour, minute, second = 0, 0, 0
                elif fmt == 'MDY':
                    month, day, year = int(groups[0]), int(groups[1]), int(groups[2])
                    hour, minute, second = 0, 0, 0
                else:
                    continue
                
                # Validate date components
                if 1 <= month <= 12 and 1 <= day <= 31 and 1990 <= year <= 2100:
                    if 0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59:
                        return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue
    
    return None


def get_filename_prefix(filename: str) -> str:
    """
    Get the device name or prefix from filename for grouping versions.
    Examples:
    - "CORE2.txt" -> "CORE2"
    - "2026-01-27_topo_realEDGE.log" -> "EDGE" or "realEDGE"
    - "CORE2_20260215.txt" -> "CORE2"
    """
    if not filename:
        return ""
    
    name = Path(filename).stem
    
    # Remove date patterns to get the device name
    # Remove ISO dates
    name = re.sub(r'\d{4}[-_]?\d{2}[-_]?\d{2}([-_T]?\d{2}[-_:]?\d{2}([-_:]?\d{2})?)?', '', name)
    # Remove time patterns
    name = re.sub(r'[-_]?\d{2}[-_:]?\d{2}[-_:]?\d{2}', '', name)
    
    # Clean up multiple underscores/hyphens
    name = re.sub(r'[-_]+', '_', name)
    name = name.strip('_-')
    
    # If "topo_real" prefix exists, extract device name after it
    if 'topo_real' in name.lower():
        match = re.search(r'topo_real(\w+)', name, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    return name.upper() if name else Path(filename).stem.upper()


async def determine_is_latest(
    project_id: str,
    document_id: str,
    new_extracted_date: Optional[datetime],
    new_upload_time: datetime,
    folder_id: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Determine if the new document should be marked as is_latest based on:
    1. Extracted date from filename (Source of Truth if available)
    2. Upload time (fallback)
    
    Returns: (should_be_latest, reason)
    
    Logic:
    - Case A (Both have dates): Most recent extracted_date wins
    - Case B (New has date, Old doesn't): New is latest
    - Case C (New has no date, Old has date): Old remains latest
    - Case D (Neither has date): Most recent upload_time wins
    """
    # Find current is_latest document for this document_id
    current_latest = await db()["documents"].find_one({
        "project_id": project_id,
        "document_id": document_id,
        "is_latest": True
    })
    
    if not current_latest:
        # No existing version, new one is latest
        return True, "first_version"
    
    current_extracted_date = current_latest.get("extracted_date")
    if isinstance(current_extracted_date, str):
        try:
            current_extracted_date = datetime.fromisoformat(current_extracted_date.replace('Z', '+00:00'))
        except ValueError:
            current_extracted_date = None
    
    current_upload_time = current_latest.get("created_at") or current_latest.get("updated_at")
    
    # Case A: Both have extracted dates
    if new_extracted_date and current_extracted_date:
        if new_extracted_date > current_extracted_date:
            return True, "newer_extracted_date"
        elif new_extracted_date < current_extracted_date:
            return False, "older_extracted_date"
        else:
            # Same date, use upload time as tiebreaker
            if new_upload_time > current_upload_time:
                return True, "same_date_newer_upload"
            return False, "same_date_older_upload"
    
    # Case B: New has date, Old doesn't
    if new_extracted_date and not current_extracted_date:
        return True, "new_has_date_old_doesnt"
    
    # Case C: New doesn't have date, Old has date
    if not new_extracted_date and current_extracted_date:
        return False, "old_has_date_new_doesnt"
    
    # Case D: Neither has date - use upload time
    if new_upload_time > current_upload_time:
        return True, "newer_upload_time"
    return False, "older_upload_time"


async def update_is_latest_for_document(
    project_id: str,
    document_id: str,
    new_version: int,
    new_extracted_date: Optional[datetime],
    new_upload_time: datetime
):
    """
    Update is_latest flags for all versions of a document based on smart date logic.
    Called after inserting a new version.
    """
    # Get all versions of this document
    versions = []
    async for doc in db()["documents"].find({
        "project_id": project_id,
        "document_id": document_id
    }):
        extracted_date = doc.get("extracted_date")
        if isinstance(extracted_date, str):
            try:
                extracted_date = datetime.fromisoformat(extracted_date.replace('Z', '+00:00'))
            except ValueError:
                extracted_date = None
        
        versions.append({
            "version": doc["version"],
            "extracted_date": extracted_date,
            "upload_time": doc.get("created_at") or doc.get("updated_at"),
            "_id": doc["_id"]
        })
    
    if not versions:
        return
    
    # Determine which version should be latest
    def sort_key(v):
        # Priority: extracted_date (if exists) > upload_time
        # Higher values = more recent = should be latest
        ed = v["extracted_date"]
        ut = v["upload_time"]
        
        if ed:
            # Has extracted date: use it as primary, upload_time as secondary
            return (1, ed, ut or datetime.min.replace(tzinfo=timezone.utc))
        else:
            # No extracted date: use upload_time only
            return (0, datetime.min.replace(tzinfo=timezone.utc), ut or datetime.min.replace(tzinfo=timezone.utc))
    
    # Sort versions by the key (newest first)
    versions.sort(key=sort_key, reverse=True)
    
    # The first one should be is_latest=True, others is_latest=False
    latest_id = versions[0]["_id"]
    
    # Update all to is_latest=False first
    await db()["documents"].update_many(
        {"project_id": project_id, "document_id": document_id},
        {"$set": {"is_latest": False}}
    )
    
    # Set the latest one to is_latest=True
    await db()["documents"].update_one(
        {"_id": latest_id},
        {"$set": {"is_latest": True}}
    )
# No file size limit - removed for flexibility

# Ensure storage base directory exists with proper permissions
def ensure_storage_base():
    """Ensure storage base directory exists with proper permissions for cross-platform compatibility"""
    try:
        import os
        import stat
        import platform
        
        # Use absolute path to avoid issues
        abs_storage = STORAGE_BASE.resolve()
        abs_storage.mkdir(parents=True, exist_ok=True)
        
        # Try to set permissions (works on Linux/Ubuntu, may fail on Windows)
        try:
            # Set full permissions (777) for Docker compatibility
            os.chmod(abs_storage, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
            
            # On Linux, also try to fix permissions recursively
            if platform.system() != "Windows":
                for root, dirs, files in os.walk(abs_storage):
                    for d in dirs:
                        try:
                            os.chmod(os.path.join(root, d), stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
                        except (OSError, PermissionError):
                            pass
                    for f in files:
                        try:
                            os.chmod(os.path.join(root, f), stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH)
                        except (OSError, PermissionError):
                            pass
        except (OSError, AttributeError, PermissionError) as e:
            # Ignore permission errors - directory creation is what matters
            # On Windows, permissions are handled differently
            if platform.system() != "Windows":
                print(f"Warning: Could not set storage permissions: {e}")
    except Exception as e:
        print(f"Warning: Could not create storage base directory: {e}")

# Initialize storage base on module load
ensure_storage_base()


async def calculate_file_hash(file_content: bytes) -> str:
    """Calculate SHA-256 hash of file content"""
    return hashlib.sha256(file_content).hexdigest()


async def save_document_file(
    project_id: str,
    document_id: str,
    version: int,
    filename: str,
    file_content: bytes
) -> Path:
    """Save document file to storage directory"""
    # storage/{project_id}/documents/{document_id}/{version}/{filename}
    # Use absolute path to avoid permission issues
    file_path = STORAGE_BASE.resolve() / project_id / "documents" / document_id / str(version) / filename
    
    # Create directory with proper permissions
    try:
        # Create all parent directories
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Try to set permissions (may fail on Windows or in Docker without proper setup)
        try:
            import os
            import stat
            # Set full permissions (777) for Docker compatibility
            os.chmod(file_path.parent, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
        except (OSError, AttributeError):
            # Ignore permission errors - directory creation is what matters
            pass
    except OSError as e:
        raise Exception(f"Failed to create directory {file_path.parent}: {str(e)}. Check storage permissions.")
    except Exception as e:
        raise Exception(f"Failed to create directory: {str(e)}")
    
    # Write file with proper error handling
    try:
        # Use aiofiles to write asynchronously
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file_content)
        
        # Try to set file permissions (may fail on Windows or in Docker)
        try:
            import os
            import stat
            # Set full permissions (666) for Docker compatibility
            os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH)
        except (OSError, AttributeError):
            # Ignore permission errors - file write is what matters
            pass
    except PermissionError as e:
        raise Exception(f"Permission denied: Cannot write to {file_path}. Check file permissions. Error: {str(e)}")
    except OSError as e:
        raise Exception(f"OS error writing file: {str(e)}")
    except Exception as e:
        raise Exception(f"Failed to save file: {str(e)}")
    
    return file_path


async def get_latest_version(project_id: str, filename: str) -> int:
    """Get the latest version number for a filename in a project"""
    # Find all documents with this filename in the project
    query = {
        "project_id": project_id,
        "filename": filename,
        "is_latest": True
    }
    
    latest_doc = await db()["documents"].find_one(query, sort=[("version", -1)])
    if latest_doc:
        return latest_doc.get("version", 0)
    return 0


async def mark_previous_versions_not_latest(project_id: str, document_id: str):
    """Mark all previous versions of a document as not latest"""
    await db()["documents"].update_many(
        {
            "project_id": project_id,
            "document_id": document_id,
            "is_latest": True
        },
        {"$set": {"is_latest": False}}
    )


async def get_parent_document_id(project_id: str, filename: str) -> Optional[str]:
    """Get the parent document ID (original document) for versioning"""
    query = {
        "project_id": project_id,
        "filename": filename,
        "version": 1
    }
    parent = await db()["documents"].find_one(query)
    if parent:
        return parent.get("document_id")
    return None


async def upload_documents(
    project_id: str,
    files: List[UploadFile],
    uploader: str,
    metadata: DocumentMetadata,
    folder_id: Optional[str] = None
) -> List[dict]:
    """
    Upload multiple documents in a single batch.
    Returns list of document info with batch_id.
    """
    if not files:
        raise ValueError("No files provided")
    
    # Generate batch ID for grouping
    batch_id = str(uuid.uuid4())
    uploaded_docs = []
    
    for file in files:
        # Read file content (no size limit)
        file_content = await file.read()
        
        # Reset file pointer for later use
        await file.seek(0)
        
        # Calculate hash
        file_hash = await calculate_file_hash(file_content)
        
        # Get or create document ID
        filename = file.filename or "unnamed"
        
        # Check if file with same name exists in the same folder
        # First, try to find existing document with same filename and folder_id
        parent_document_id = None
        document_id = None
        
        # Build query to find existing document
        find_query = {
            "project_id": project_id,
            "filename": filename,
            "is_latest": True
        }
        # If folder_id is provided, also match by folder_id
        # If folder_id is None, match documents with folder_id = None or missing
        if folder_id is not None:
            find_query["folder_id"] = folder_id
        else:
            # Match documents with folder_id = None or missing
            find_query["$or"] = [
                {"folder_id": None},
                {"folder_id": {"$exists": False}}
            ]
        
        # Find existing document with same filename and folder
        existing_doc = await db()["documents"].find_one(find_query)
        
        if existing_doc:
            # File with same name exists in same folder - create new version
            document_id = existing_doc["document_id"]
            parent_document_id = document_id
            
            # Get latest version for this document_id
            latest_version_doc = await db()["documents"].find_one(
                {"document_id": document_id, "project_id": project_id},
                sort=[("version", -1)]
            )
            new_version = (latest_version_doc.get("version", 0) if latest_version_doc else 0) + 1
            
            # Preserve folder_id from existing document
            if folder_id is None:
                folder_id = existing_doc.get("folder_id")
            
            # Mark previous versions as not latest
            await mark_previous_versions_not_latest(project_id, document_id)
        else:
            # First version of this filename in this folder - generate new document ID
            document_id = str(uuid.uuid4())
            new_version = 1
        
        # Save file to storage
        try:
            file_path = await save_document_file(
                project_id, document_id, new_version, filename, file_content
            )
        except Exception as e:
            # If file save fails, raise error immediately
            error_msg = str(e)
            if "Operation not permitted" in error_msg or "Permission denied" in error_msg:
                raise Exception(f"Storage permission error: {error_msg}. Please check storage directory permissions in Docker.")
            raise Exception(f"Failed to save file {filename}: {error_msg}")
        
        # Create document record
        now = datetime.now(timezone.utc)
        # Calculate relative path for storage in database
        try:
            relative_path = str(file_path.relative_to(STORAGE_BASE.resolve()))
        except ValueError:
            # Fallback: use relative path from STORAGE_BASE
            relative_path = str(Path(project_id) / "documents" / document_id / str(new_version) / filename)
        
        # Determine content type - check extension for text files if content_type is not set or is generic
        content_type = file.content_type or "application/octet-stream"
        if content_type == "application/octet-stream" or not content_type:
            # Check file extension for common text/config file types
            filename_lower = filename.lower()
            if filename_lower.endswith(('.txt', '.cfg', '.conf', '.log')):
                content_type = "text/plain"
        
        # Smart date extraction from filename
        extracted_date = extract_date_from_filename(filename)
        filename_prefix = get_filename_prefix(filename)
        
        # Temporarily set is_latest=True (will be updated after insert)
        document_doc = {
            "document_id": document_id,
            "project_id": project_id,
            "filename": filename,
            "file_path": relative_path,
            "file_hash": file_hash,
            "size": len(file_content),
            "content_type": content_type,
            "uploader": uploader,
            "created_at": now,
            "updated_at": now,
            "version": new_version,
            "parent_document_id": parent_document_id,
            "upload_batch_id": batch_id,
            "metadata": {
                "who": metadata.who,
                "what": metadata.what,
                "where": metadata.where,
                "when": metadata.when,
                "why": metadata.why,
                "description": metadata.description,
            },
            "folder_id": folder_id,
            "is_latest": True,  # Temporary, will be recalculated
            "extracted_date": extracted_date,  # Store extracted date for future sorting
            "filename_prefix": filename_prefix,  # Store device name/prefix for grouping
        }
        
        # Save to MongoDB - if this fails, file is already saved but we'll raise error
        try:
            await db()["documents"].insert_one(document_doc)
        except Exception as e:
            # File was saved but database insert failed - this is a critical error
            raise Exception(f"File saved but failed to save document record to database: {str(e)}")
        
        # Update is_latest flags using smart date logic
        await update_is_latest_for_document(
            project_id, document_id, new_version, extracted_date, now
        )
        
        # Log the version decision
        print(f"[Version] {filename}: version={new_version}, extracted_date={extracted_date}, prefix={filename_prefix}")
        
        uploaded_docs.append({
            "document_id": document_id,
            "filename": filename,
            "version": new_version,
            "size": len(file_content),
            "content_type": file.content_type,
            "upload_batch_id": batch_id,
        })
    
    return uploaded_docs


async def get_document_file_path(project_id: str, document_id: str, version: Optional[int] = None) -> Optional[Path]:
    """Get file path for a document. If version is None, get latest version."""
    query = {"document_id": document_id, "project_id": project_id}
    if version:
        query["version"] = version
    else:
        query["is_latest"] = True
    
    doc = await db()["documents"].find_one(query)
    if not doc:
        return None
    
    # Use absolute path to avoid permission issues
    file_path = STORAGE_BASE.resolve() / doc["file_path"]
    if file_path.exists():
        return file_path
    return None


async def read_document_file(project_id: str, document_id: str, version: Optional[int] = None) -> Optional[bytes]:
    """Read document file content"""
    file_path = await get_document_file_path(project_id, document_id, version)
    if not file_path:
        return None
    
    async with aiofiles.open(file_path, 'rb') as f:
        return await f.read()

