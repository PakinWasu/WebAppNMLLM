"""Topology API endpoints for auto-generating network topology using LLM"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from ..db.mongo import db
from ..dependencies.auth import get_current_user, check_project_access
from ..services.topology_service import topology_service

router = APIRouter(prefix="/projects/{project_id}/topology", tags=["topology"])


@router.post("/generate")
async def generate_topology(
    project_id: str,
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Generate network topology for a project using LLM analysis.
    
    Analyzes all devices in the project to identify:
    - Device nodes and their types (Core/Distribution/Access)
    - Links based on LLDP neighbors, subnet matching, and interface descriptions
    
    Returns:
        - topology: {nodes: [...], edges: [...]}
        - analysis_summary: Brief explanation
        - metrics: Performance metrics
    """
    await check_project_access(project_id, user)
    
    # Verify project exists
    project = await db()["projects"].find_one({"project_id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Generate topology using LLM
    result = await topology_service.generate_topology(project_id)
    
    return result


@router.get("")
async def get_topology(
    project_id: str,
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get saved topology for a project (if exists).
    
    Returns the topology stored in project metadata (topoNodes, topoEdges).
    """
    await check_project_access(project_id, user)
    
    project = await db()["projects"].find_one({"project_id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Return saved topology if exists
    return {
        "topology": {
            "nodes": project.get("topoNodes", []),
            "edges": project.get("topoEdges", [])
        },
        "saved": bool(project.get("topoNodes") or project.get("topoEdges"))
    }
