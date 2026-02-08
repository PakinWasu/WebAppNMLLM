"""Topology API endpoints for auto-generating network topology using LLM"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from ..db.mongo import db


def _iso_generated_at(dt) -> Optional[str]:
    """Serialize generated_at to ISO string so frontend polling can compare reliably."""
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)
from ..dependencies.auth import get_current_user, check_project_access, check_project_manager_or_admin
from ..services.topology_service import topology_service
from ..services.llm_lock import acquire_llm_lock, release_llm_lock
from ..models.topology import TopologyLayoutUpdate

router = APIRouter(prefix="/projects/{project_id}/topology", tags=["topology"])

# Fast topology (DB + rule-based only, no LLM) - for instant graph display
network_topology_router = APIRouter(prefix="/projects/{project_id}", tags=["topology"])


@network_topology_router.get("/network-topology")
async def get_network_topology(
    project_id: str,
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get network topology from database only (rule-based, no LLM).
    Returns immediately. Use for instant graph render.
    For AI analysis, call POST /topology/generate separately.
    """
    await check_project_access(project_id, user)
    result = await topology_service.get_network_topology_fast(project_id)
    return result


# Test router (no project_id required)
test_router = APIRouter(prefix="/topology", tags=["topology"])


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
    if not await acquire_llm_lock(project_id, user.get("username"), "topology"):
        raise HTTPException(
            status_code=409,
            detail="An LLM job is already running for this project (another user or tab). Please wait until it finishes.",
        )
    try:
        project = await db()["projects"].find_one({"project_id": project_id})
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        result = await topology_service.generate_topology(project_id)
        # Auto-save topology result to project (nodes and edges) - for backward compatibility
        if result.get("topology") and (result["topology"].get("nodes") or result["topology"].get("edges")):
            try:
                update_data = {
                    "topoNodes": result["topology"].get("nodes", []),
                    "topoEdges": result["topology"].get("edges", []),
                    "topology_llm_metrics": result.get("metrics"),  # Save LLM metrics to project (backward compat)
                    "topology_llm_summary": result.get("analysis_summary"),  # Save LLM summary (backward compat)
                    "updated_at": datetime.now(timezone.utc),
                    "updated_by": user["username"]
                }
                await db()["projects"].update_one(
                    {"project_id": project_id},
                    {"$set": update_data}
                )
                print(f"[Topology] Auto-saved topology result: {len(result['topology'].get('nodes', []))} nodes, {len(result['topology'].get('edges', []))} edges")
            except Exception as e:
                print(f"[Topology] Warning: Failed to auto-save topology result: {e}")
                # Don't fail the request if save fails
        return result
    finally:
        await release_llm_lock(project_id)


@router.get("")
async def get_topology(
    project_id: str,
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get saved topology for a project (if exists).
    
    Returns the topology stored in project metadata (topoNodes, topoEdges, topoPositions, topoLinks)
    and LLM metrics if available.
    """
    await check_project_access(project_id, user)
    
    project = await db()["projects"].find_one({"project_id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Try to get latest topology result from llm_results collection
    llm_result = await db()["llm_results"].find_one(
        {"project_id": project_id, "result_type": "topology"},
        sort=[("generated_at", -1)]
    )
    
    # Use topology from llm_results if available, otherwise fallback to project metadata
    if llm_result and llm_result.get("result_data"):
        return {
            "topology": llm_result.get("result_data"),
            "layout": {
                "positions": project.get("topoPositions", {}),
                "links": project.get("topoLinks", []),
                "node_labels": project.get("topoNodeLabels", {}),
                "node_roles": project.get("topoNodeRoles", {})
            },
            "llm_metrics": llm_result.get("metrics"),
            "llm_summary": llm_result.get("analysis_summary"),
            "llm_used": llm_result.get("llm_used", False),
            "generated_at": _iso_generated_at(llm_result.get("generated_at")),
            "saved": True
        }
    
    # Fallback to project metadata (backward compatibility)
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
        "llm_metrics": project.get("topology_llm_metrics"),
        "llm_summary": project.get("topology_llm_summary"),
        "saved": bool(project.get("topoNodes") or project.get("topoEdges") or project.get("topoPositions"))
    }


@test_router.post("/test-llm")
async def test_llm_connection(
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Test LLM connection and basic functionality (for debugging).
    This endpoint tests:
    1. Ollama connectivity
    2. Model availability
    3. Simple LLM call
    4. Topology LLM with sample data
    """
    import httpx
    import json
    from ..services.llm_service import llm_service

    base_url = llm_service.base_url
    model_name = llm_service.model_name
    results = {
        "ollama_accessible": False,
        "model_available": False,
        "model_name": model_name,
        "simple_call_works": False,
        "topology_call_works": False,
        "errors": []
    }

    # Test 1: Check Ollama connection
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/api/tags")
            response.raise_for_status()
            results["ollama_accessible"] = True

            models_data = response.json()
            models = [m.get("name", "") for m in models_data.get("models", [])]
            if model_name in models:
                results["model_available"] = True
            else:
                results["errors"].append(f"Model '{model_name}' not found. Available: {models}")
    except Exception as e:
        results["errors"].append(f"Ollama connection failed: {str(e)}")
        return results
    
    # Test 2: Simple LLM call
    # Note: Ollama has ~60s server-side timeout. Use 14b and short output to finish in time.
    if results["model_available"]:
        try:
            url = f"{base_url}/api/chat"
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "user", "content": "Reply with only this JSON, nothing else: {\"status\": \"ok\"}"}
                ],
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.1, "num_predict": 32}
            }
            
            # Client timeout: Ollama server has ~60s limit; we use 90s to catch response or 500
            timeout = httpx.Timeout(connect=30.0, read=90.0, write=60.0, pool=60.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                print(f"[Test LLM] Sending request to {url} (read_timeout=90s, model={model_name})")
                print(f"[Test LLM] Payload: {json.dumps(payload, indent=2)}")
                response = await client.post(url, json=payload)
                print(f"[Test LLM] Response status: {response.status_code}")
                print(f"[Test LLM] Response headers: {dict(response.headers)}")
                
                # Check response status before parsing
                if response.status_code != 200:
                    error_text = response.text[:1000]
                    results["errors"].append(f"Simple LLM HTTP error ({response.status_code}): {error_text}")
                    results["http_status"] = response.status_code
                    results["raw_response"] = error_text
                    return results
                
                try:
                    data = response.json()
                except json.JSONDecodeError as e:
                    error_text = response.text[:1000]
                    results["errors"].append(f"Simple LLM response is not JSON: {str(e)}")
                    results["raw_response"] = error_text
                    return results
                
                print(f"[Test LLM] Response data keys: {list(data.keys())}")
                
                content = data.get("message", {}).get("content", "")
                if not content:
                    results["errors"].append(f"Simple LLM response has no content. Full response: {json.dumps(data, indent=2)[:500]}")
                    results["raw_response"] = json.dumps(data, indent=2)
                    return results
                
                print(f"[Test LLM] Content preview: {content[:500]}")
                
                # Try to parse JSON
                try:
                    content_cleaned = content.strip().replace("```json", "").replace("```", "").strip()
                    parsed = json.loads(content_cleaned)
                    results["simple_call_works"] = True
                    results["simple_response"] = parsed
                except json.JSONDecodeError as json_err:
                    results["errors"].append(f"Simple call returned non-JSON: {str(json_err)}")
                    results["raw_simple_response"] = content[:500]
        except httpx.ReadTimeout:
            results["errors"].append(
                f"Simple LLM call timeout. Check OLLAMA_TIMEOUT (current: {llm_service.timeout_seconds}s) and model load on {base_url}."
            )
        except httpx.ConnectTimeout:
            results["errors"].append("Simple LLM connection timeout")
        except httpx.HTTPStatusError as e:
            error_text = e.response.text[:500] if e.response else str(e)
            results["errors"].append(f"Simple LLM HTTP error ({e.response.status_code if e.response else 'N/A'}): {error_text}")
            results["http_status"] = e.response.status_code if e.response else None
        except httpx.ConnectError as e:
            results["errors"].append(f"Simple LLM connection error: {str(e)}")
        except Exception as e:
            error_msg = f"Simple LLM call failed: {type(e).__name__}: {str(e)}"
            results["errors"].append(error_msg)
            import traceback
            results["traceback"] = traceback.format_exc()
            print(f"[Test LLM] Exception: {error_msg}")
            print(f"[Test LLM] Traceback: {results['traceback']}")
    
    # Test 3: Topology generation using Rule-Based method (fast, no LLM timeout)
    if results["simple_call_works"]:
        try:
            # Use rule-based topology generation (fast, deterministic, no LLM timeout)
            sample_devices = [
                {
                    "device_name": "SW1",
                    "device_overview": {"hostname": "SW1", "role": "Switch"},
                    "neighbors": [
                        {"device_name": "SW2", "local_port": "GE0/0/1", "remote_port": "GE0/0/2"}
                    ]
                },
                {
                    "device_name": "SW2",
                    "device_overview": {"hostname": "SW2", "role": "Switch"},
                    "neighbors": [
                        {"device_name": "SW1", "local_port": "GE0/0/2", "remote_port": "GE0/0/1"}
                    ]
                }
            ]
            
            # Generate topology using rule-based method (same as fallback in topology_service)
            nodes = []
            edges = []
            device_map = {}
            
            # Create nodes
            for device in sample_devices:
                device_name = device.get("device_name")
                if device_name:
                    device_map[device_name] = device
                    nodes.append({
                        "id": device_name,
                        "label": device_name,
                        "type": device.get("device_overview", {}).get("role", "Switch")
                    })
            
            # Create edges from neighbors
            edge_set = set()
            for device in sample_devices:
                device_name = device.get("device_name")
                neighbors = device.get("neighbors", [])
                
                for neighbor in neighbors:
                    neighbor_name = neighbor.get("device_name")
                    if neighbor_name and neighbor_name in device_map:
                        local_port = neighbor.get("local_port", "")
                        remote_port = neighbor.get("remote_port", "")
                        
                        # Create bidirectional edge
                        edge_key = tuple(sorted([device_name, neighbor_name]))
                        if edge_key not in edge_set:
                            edge_set.add(edge_key)
                            edges.append({
                                "from": device_name,
                                "to": neighbor_name,
                                "label": f"{local_port}-{remote_port}" if local_port and remote_port else "",
                                "evidence": f"LLDP/CDP neighbor: {device_name} sees {neighbor_name} on {local_port}"
                            })
            
            topology_data = {
                "nodes": nodes,
                "edges": edges,
                "analysis_summary": "Rule-based topology generated from neighbor data (fast, no LLM timeout)"
            }
            
            # Validate structure
            if isinstance(topology_data, dict) and "nodes" in topology_data and "edges" in topology_data:
                results["topology_call_works"] = True
                results["topology_method"] = "rule_based"
                results["sample_result"] = {
                    "nodes_count": len(topology_data.get("nodes", [])),
                    "edges_count": len(topology_data.get("edges", [])),
                    "preview": json.dumps(topology_data, indent=2, ensure_ascii=False)[:500]
                }
            else:
                results["errors"].append(f"Rule-based topology returned invalid structure: {topology_data}")
                    
        except Exception as e:
            error_msg = f"Rule-based topology generation failed: {type(e).__name__}: {str(e)}"
            results["errors"].append(error_msg)
            import traceback
            results["traceback"] = traceback.format_exc()
            print(f"[Test LLM] Rule-based Topology Exception: {error_msg}")
    
    return results


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
