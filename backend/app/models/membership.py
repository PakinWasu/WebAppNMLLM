from pydantic import BaseModel
from datetime import datetime
from typing import Literal

# Project roles (assigned per project, not per user account)
ProjectRole = Literal["manager", "engineer", "viewer"]

class MemberAdd(BaseModel):
    username: str
    role: ProjectRole

class ProjectMember(BaseModel):
    project_id: str
    username: str
    role: ProjectRole
    joined_at: datetime
