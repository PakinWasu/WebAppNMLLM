import hashlib
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import UploadFile
import aiofiles

from ..db.mongo import db
from ..models.document import DocumentInDB, DocumentMetadata

STORAGE_BASE = Path("storage")
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
            "is_latest": True,
        }
        
        # Save to MongoDB - if this fails, file is already saved but we'll raise error
        try:
            await db()["documents"].insert_one(document_doc)
        except Exception as e:
            # File was saved but database insert failed - this is a critical error
            raise Exception(f"File saved but failed to save document record to database: {str(e)}")
        
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

