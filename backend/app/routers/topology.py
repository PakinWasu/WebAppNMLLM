"""Topology API endpoints for auto-generating network topology using LLM"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from datetime import datetime, timezone

from ..db.mongo import db
from ..dependencies.auth import get_current_user, check_project_access, check_project_manager_or_admin
from ..services.topology_service import topology_service
from ..models.topology import TopologyLayoutUpdate

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
    
    Returns the topology stored in project metadata (topoNodes, topoEdges, topoPositions, topoLinks).
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
        "layout": {
            "positions": project.get("topoPositions", {}),
            "links": project.get("topoLinks", []),
            "node_labels": project.get("topoNodeLabels", {}),
            "node_roles": project.get("topoNodeRoles", {})
        },
        "saved": bool(project.get("topoNodes") or project.get("topoEdges") or project.get("topoPositions"))
    }


@router.put("/layout")
async def save_topology_layout(
    project_id: str,
    layout: TopologyLayoutUpdate,
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Save topology layout (positions, links, labels, roles).
    
    Only project managers or admins can save layout.
    
    This endpoint saves:
    - Node positions (topoPositions)
    - Links/edges (topoLinks)
    - Node labels (topoNodeLabels)
    - Node roles (topoNodeRoles)
    """
    await check_project_manager_or_admin(project_id, user)
    
    # Verify project exists
    project = await db()["projects"].find_one({"project_id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Update project with topology layout
    updated_at = datetime.now(timezone.utc)
    update_data = {
        "topoPositions": layout.positions,
        "topoLinks": layout.links,
        "updated_at": updated_at,
        "updated_by": user["username"]
    }
    
    if layout.node_labels is not None:
        update_data["topoNodeLabels"] = layout.node_labels
    if layout.node_roles is not None:
        update_data["topoNodeRoles"] = layout.node_roles
    
    await db()["projects"].update_one(
        {"project_id": project_id},
        {"$set": update_data}
    )
    
    return {
        "success": True,
        "message": "Topology layout saved successfully",
        "positions_count": len(layout.positions),
        "links_count": len(layout.links)
    }
