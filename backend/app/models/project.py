from pydantic import BaseModel
from datetime import datetime

class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    topo_url: str | None = None
    visibility: str | None = "Private"
    backup_interval: str | None = "Daily"

class ProjectUpdate(BaseModel):
    name: str
    description: str | None = None
    topo_url: str | None = None
    visibility: str | None = None
    backup_interval: str | None = None
    status: str | None = None

class ProjectInDB(BaseModel):
    project_id: str
    name: str
    description: str | None = None
    created_at: datetime
    created_by: str
