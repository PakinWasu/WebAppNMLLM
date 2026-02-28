"""Summary API endpoints for device configuration summary"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import re
import base64
from PIL import Image
import io

from ..db.mongo import db
from ..dependencies.auth import get_current_user, check_project_access, check_project_editor_or_admin

router = APIRouter(prefix="/projects/{project_id}/summary", tags=["summary"])
device_router = APIRouter(prefix="/projects/{project_id}/devices", tags=["devices"])


@device_router.post("/{device_name}/image")
async def upload_device_image(
    project_id: str,
    device_name: str,
    file: UploadFile = File(...),
    user=Depends(get_current_user)
):
    """Upload device image - stores as base64 in project metadata"""
    await check_project_access(project_id, user)
    
    # Check if user can edit project
    project = await db()["projects"].find_one({"project_id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check permissions
    project_member = next((m for m in project.get("members", []) if m.get("username") == user["username"]), None)
    is_manager = user["role"] == "admin" or (project_member and project_member.get("role") == "manager")
    if not is_manager:
        raise HTTPException(status_code=403, detail="Only managers can upload device images")
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Read and process image
    try:
        file_content = await file.read()
        
        # Open image with PIL to resize and optimize
        img = Image.open(io.BytesIO(file_content))
        
        # Check if image has transparency/alpha channel
        has_transparency = False
        original_mode = img.mode
        
        if img.mode in ("RGBA", "LA"):
            # Check if there are any transparent pixels
            if img.mode == "RGBA":
                alpha = img.split()[3]
                has_transparency = alpha.getextrema()[0] < 255
            elif img.mode == "LA":
                alpha = img.split()[1]
                has_transparency = alpha.getextrema()[0] < 255
        elif img.mode == "P":
            # Palette mode - check if transparency is in info
            has_transparency = "transparency" in img.info
            # Convert palette to RGBA to check transparency properly
            if has_transparency:
                img = img.convert("RGBA")
        
        # Resize to max 600x600 while maintaining aspect ratio (much larger for better visibility)
        max_size = 600
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        # Convert to base64 - always use PNG to preserve quality and potential transparency
        # PNG supports both transparent and opaque images, and has better quality
        buffer = io.BytesIO()
        if img.mode != "RGBA":
            # Convert to RGBA to support transparency if needed
            img = img.convert("RGBA")
        
        # Save as PNG - preserves transparency and has better quality than JPEG
        img.save(buffer, format="PNG", optimize=True)
        img_bytes = buffer.getvalue()
        img_base64 = base64.b64encode(img_bytes).decode("utf-8")
        
        # Store in project metadata
        device_images = project.get("device_images", {})
        device_images[device_name] = img_base64
        
        await db()["projects"].update_one(
            {"project_id": project_id},
            {"$set": {"device_images": device_images, "updated_at": datetime.now(timezone.utc)}}
        )
        
        return {"success": True, "message": "Device image uploaded successfully"}
    except Exception as e:
        print(f"Error processing image: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process image: {str(e)}")


@device_router.get("/{device_name}/image")
async def get_device_image(
    project_id: str,
    device_name: str,
    user=Depends(get_current_user)
):
    """Get device image as base64"""
    await check_project_access(project_id, user)
    
    project = await db()["projects"].find_one({"project_id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    device_images = project.get("device_images", {})
    img_data = device_images.get(device_name)
    
    if not img_data:
        raise HTTPException(status_code=404, detail="Device image not found")
    
    # Return image data (can be PNG or JPEG base64)
    return {"image": img_data}


@device_router.delete("/{device_name}/image")
async def delete_device_image(
    project_id: str,
    device_name: str,
    user=Depends(get_current_user)
):
    """Delete device image"""
    await check_project_access(project_id, user)
    
    project = await db()["projects"].find_one({"project_id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check permissions
    project_member = next((m for m in project.get("members", []) if m.get("username") == user["username"]), None)
    is_manager = user["role"] == "admin" or (project_member and project_member.get("role") == "manager")
    if not is_manager:
        raise HTTPException(status_code=403, detail="Only managers can delete device images")
    
    device_images = project.get("device_images", {})
    if device_name in device_images:
        del device_images[device_name]
        await db()["projects"].update_one(
            {"project_id": project_id},
            {"$set": {"device_images": device_images, "updated_at": datetime.now(timezone.utc)}}
        )
    
    return {"success": True, "message": "Device image deleted successfully"}


@device_router.delete("/{device_name}")
async def delete_device(
    project_id: str,
    device_name: str,
    user=Depends(get_current_user)
):
    """Delete a device and all its data: config documents (all versions), parsed_configs, device image, LLM results, and remove from topology. Viewer cannot delete."""
    await check_project_access(project_id, user)
    await check_project_editor_or_admin(project_id, user)

    project = await db()["projects"].find_one({"project_id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # 1. Delete all documents for this device (Config folder, all versions)
    from bson.regex import Regex
    name_pattern = Regex(f"^{re.escape(device_name)}(\\.|$|_)", "i")
    docs_result = await db()["documents"].delete_many(
        {
            "project_id": project_id,
            "folder_id": "Config",
            "$or": [
                {"device_name": device_name},
                {"filename": name_pattern},
            ],
        }
    )
    documents_deleted = docs_result.deleted_count

    # 2. Delete parsed_configs for this device
    try:
        parsed_result = await db()["parsed_configs"].delete_many(
            {"project_id": project_id, "device_name": device_name}
        )
        parsed_deleted = parsed_result.deleted_count
    except Exception:
        parsed_deleted = 0

    # 3. Remove device image from project
    device_images = dict(project.get("device_images") or {})
    if device_name in device_images:
        del device_images[device_name]
        await db()["projects"].update_one(
            {"project_id": project_id},
            {"$set": {"device_images": device_images, "updated_at": datetime.now(timezone.utc)}}
        )

    # 4. Delete LLM results for this device (device_overview, device_recommendations, device_config_drift)
    try:
        llm_result = await db()["llm_results"].delete_many(
            {"project_id": project_id, "result_data.device_name": device_name}
        )
        llm_deleted = llm_result.deleted_count
    except Exception:
        llm_deleted = 0

    # 5. Remove device from topology (positions, links, labels, roles)
    positions = dict(project.get("topoPositions") or {})
    links = list(project.get("topoLinks") or [])
    labels = dict(project.get("topoNodeLabels") or {})
    roles = dict(project.get("topoNodeRoles") or {})
    updated = False
    if device_name in positions:
        del positions[device_name]
        updated = True
    if device_name in labels:
        del labels[device_name]
        updated = True
    if device_name in roles:
        del roles[device_name]
        updated = True
    # Links: list of { from, to, ... } — remove any edge that has this device
    new_links = [e for e in links if e.get("from") != device_name and e.get("to") != device_name]
    if len(new_links) != len(links):
        links = new_links
        updated = True
    if updated:
        await db()["projects"].update_one(
            {"project_id": project_id},
            {
                "$set": {
                    "topoPositions": positions,
                    "topoLinks": links,
                    "topoNodeLabels": labels,
                    "topoNodeRoles": roles,
                    "updated_at": datetime.now(timezone.utc),
                }
            }
        )

    return {
        "success": True,
        "message": f"Device '{device_name}' and all its data deleted",
        "deleted": {
            "documents": documents_deleted,
            "parsed_configs": parsed_deleted,
            "llm_results": llm_deleted,
        },
    }


@device_router.get("/{device_id}/configs")
async def list_device_configs(
    project_id: str,
    device_id: str,
    user=Depends(get_current_user)
):
    """List available config versions for a device (for Compare Config UI). Returns flattened list of document_id, version, filename, created_at."""
    await check_project_access(project_id, user)
    device_lower = (device_id or "").strip().lower()
    if not device_lower:
        return {"configs": []}
    # Match filenames that contain device name (with common variants)
    key_variants = [
        device_lower,
        device_lower.replace("-", "_"),
        device_lower.replace("_", "-"),
        device_lower.replace("-", "").replace("_", ""),
    ]
    configs = []
    seen_doc_ids = set()
    async for doc in db()["documents"].find(
        {"project_id": project_id, "folder_id": "Config", "is_latest": True},
        {"document_id": 1, "filename": 1}
    ):
        name = (doc.get("filename") or "").lower()
        if not any(k in name for k in key_variants):
            continue
        document_id = doc["document_id"]
        if document_id in seen_doc_ids:
            continue
        seen_doc_ids.add(document_id)
        # Get all versions for this document
        async for v in db()["documents"].find(
            {"project_id": project_id, "document_id": document_id},
            {"version": 1, "filename": 1, "created_at": 1},
            sort=[("version", -1)]
        ):
            created = v.get("created_at")
            configs.append({
                "id": f"{document_id}_v{v['version']}",
                "document_id": document_id,
                "version": v["version"],
                "filename": v.get("filename", doc.get("filename", "")),
                "created_at": created.isoformat() if isinstance(created, datetime) else (created or ""),
            })
    configs.sort(key=lambda x: (x["filename"], -(x["version"])))
    return {"configs": configs}


def _device_status(latest: dict) -> str:
    """Derive status from parsed config (OK or not)."""
    return "OK"  # Can add drift/warning logic later


@router.get("/metrics")
async def get_summary_metrics(
    project_id: str,
    user=Depends(get_current_user)
):
    """Dashboard metrics for NOC: total devices, healthy, critical, core/dist/access counts."""
    await check_project_access(project_id, user)
    device_names = set()
    device_statuses = []  # list of (device_name, status)

    async for doc in db()["parsed_configs"].find(
        {"project_id": project_id},
        sort=[("device_name", 1), ("upload_timestamp", -1)]
    ):
        device_name = doc.get("device_name")
        if device_name and device_name not in device_names:
            device_names.add(device_name)
            latest = await db()["parsed_configs"].find_one(
                {"project_id": project_id, "device_name": device_name},
                sort=[("upload_timestamp", -1)]
            )
            if latest:
                status = _device_status(latest)
                device_statuses.append((device_name, status))

    # Fallback: documents collection
    async for doc in db()["documents"].find(
        {"project_id": project_id, "is_latest": True, "parsed_config": {"$exists": True}},
        sort=[("created_at", -1)]
    ):
        parsed_config = doc.get("parsed_config", {})
        device_name = parsed_config.get("device_name")
        if device_name and device_name not in device_names:
            device_names.add(device_name)
            status = _device_status(parsed_config)
            device_statuses.append((device_name, status))

    total_devices = len(device_statuses)
    healthy = sum(1 for _, s in device_statuses if (s or "").lower() == "ok")
    critical = total_devices - healthy

    def role(name):
        n = (name or "").lower()
        if "core" in n:
            return "core"
        if "dist" in n or "distribution" in n:
            return "dist"
        if "access" in n:
            return "access"
        return None

    core = sum(1 for name, _ in device_statuses if role(name) == "core")
    dist = sum(1 for name, _ in device_statuses if role(name) == "dist")
    access = sum(1 for name, _ in device_statuses if role(name) == "access")

    return {
        "total_devices": total_devices,
        "healthy": healthy,
        "critical": critical,
        "core": core,
        "dist": dist,
        "access": access,
    }


@router.get("")
async def get_summary(
    project_id: str,
    user=Depends(get_current_user)
):
    """Get summary table data for all devices in project"""
    await check_project_access(project_id, user)
    
    # Get latest parsed config for each device
    # Try parsed_configs collection first, then fallback to documents collection
    devices = []
    device_names = set()
    
    # First, try to get from parsed_configs collection
    async for doc in db()["parsed_configs"].find(
        {"project_id": project_id},
        sort=[("device_name", 1), ("upload_timestamp", -1)]
    ):
        device_name = doc.get("device_name")
        if device_name and device_name not in device_names:
            device_names.add(device_name)
            
            # Get latest config for this device
            latest = await db()["parsed_configs"].find_one(
                {"project_id": project_id, "device_name": device_name},
                sort=[("upload_timestamp", -1)]
            )
            
            if latest:
                # Remove MongoDB _id to avoid serialization issues
                latest.pop("_id", None)
                
                # Format for table display
                interfaces = latest.get("interfaces", [])
                vlans = latest.get("vlans", {})
                stp = latest.get("stp", {})
                routing = latest.get("routing", {})
                overview = latest.get("device_overview", {})
                
                # Calculate stats
                total_ifaces = len(interfaces)
                up_ifaces = sum(1 for i in interfaces if i.get("oper_status") == "up")
                down_ifaces = sum(1 for i in interfaces if i.get("oper_status") == "down")
                admin_down = sum(1 for i in interfaces if i.get("admin_status") == "down")
                
                access_ports = sum(1 for i in interfaces if i.get("port_mode") == "access")
                trunk_ports = sum(1 for i in interfaces if i.get("port_mode") == "trunk")
                unused_ports = sum(1 for i in interfaces if not i.get("port_mode") or i.get("port_mode") == "none")
                
                vlan_count = vlans.get("total_vlan_count", len(vlans.get("vlan_list", [])))
                
                # Get native VLAN (most common from trunk ports)
                native_vlans = [i.get("native_vlan") for i in interfaces if i.get("native_vlan")]
                native_vlan = native_vlans[0] if native_vlans else None
                
                # STP info - extract from stp.interfaces
                stp_mode = stp.get("stp_mode") or stp.get("mode") or "-"
                stp_interfaces = stp.get("interfaces", [])
                stp_roles = {}
                for stp_iface in stp_interfaces:
                    role = stp_iface.get("role")
                    if role:
                        stp_roles[role] = stp_roles.get(role, 0) + 1
                
                if stp_roles:
                    root_bridges = stp.get("root_bridges", [])
                    if root_bridges and len(root_bridges) > 0:
                        stp_role_summary = "Root"
                    elif "Root" in stp_roles:
                        stp_role_summary = f"R:{stp_roles.get('Root', 0)}/D:{stp_roles.get('Designated', 0)}"
                    elif "Designated" in stp_roles:
                        stp_role_summary = f"D:{stp_roles.get('Designated', 0)}"
                    else:
                        stp_role_summary = ", ".join([f"{k}:{v}" for k, v in list(stp_roles.items())[:2]])
                else:
                    stp_role_summary = "-"
                
                # Get trunk allowed VLANs summary - collect all unique VLANs from trunk ports
                all_trunk_vlans = set()
                has_all_vlans = False
                for iface in interfaces:
                    if iface.get("port_mode") == "trunk":
                        allowed = iface.get("allowed_vlans")
                        if allowed:
                            allowed_str = str(allowed).strip()
                            if allowed_str.upper() == "ALL" or allowed_str in ["1-4094", "1-4095"]:
                                has_all_vlans = True
                            else:
                                parts = allowed_str.replace(",", " ").split()
                                for part in parts:
                                    part = part.strip()
                                    if part.isdigit():
                                        all_trunk_vlans.add(int(part))
                
                if has_all_vlans:
                    trunk_allowed_summary = "ALL"
                elif all_trunk_vlans:
                    sorted_vlans = sorted(all_trunk_vlans)
                    trunk_allowed_summary = " ".join(str(v) for v in sorted_vlans)
                    if len(trunk_allowed_summary) > 20:
                        trunk_allowed_summary = trunk_allowed_summary[:17] + "..."
                else:
                    trunk_allowed_summary = "-"
                
                # OSPF neighbors - updated for new parser structure
                ospf = routing.get("ospf")
                if isinstance(ospf, dict):
                    ospf_neighbors = len(ospf.get("neighbors", []))
                else:
                    ospf_neighbors = 0
                
                # BGP info - updated for new parser structure
                bgp = routing.get("bgp")
                if isinstance(bgp, dict):
                    bgp_asn = bgp.get("as_number") or bgp.get("local_as") or "-"
                    bgp_neighbors = len(bgp.get("peers", []))
                else:
                    bgp_asn = "-"
                    bgp_neighbors = 0
                bgp_summary = f"{bgp_asn}/{bgp_neighbors}" if bgp_asn != "-" else "-/-"
                
                # Routing protocols - updated for new parser structure
                rt_protos = []
                if isinstance(ospf, dict) and ospf.get("process_id"):
                    rt_protos.append("OSPF")
                if isinstance(bgp, dict) and (bgp.get("as_number") or bgp.get("local_as")):
                    rt_protos.append("BGP")
                
                # Check for RIP
                rip = routing.get("rip")
                if isinstance(rip, dict) and (rip.get("version") or rip.get("networks") or rip.get("interfaces")):
                    rt_protos.append("RIP")
                
                # Check for EIGRP
                eigrp = routing.get("eigrp")
                if isinstance(eigrp, dict) and (eigrp.get("as_number") or eigrp.get("router_id")):
                    rt_protos.append("EIGRP")
                
                static_routes = routing.get("static", [])
                if isinstance(static_routes, list) and len(static_routes) > 0:
                    rt_protos.append("Static")
                elif isinstance(static_routes, dict) and static_routes.get("routes"):
                    rt_protos.append("Static")
                rt_proto_str = ", ".join(rt_protos) if rt_protos else "-"
                
                # Status (simplified - OK for now, can add drift detection later)
                status = "OK"
                
                # Format datetime
                upload_ts = latest.get("upload_timestamp")
                if isinstance(upload_ts, datetime):
                    upload_ts = upload_ts.isoformat()
                
                devices.append({
                    "device": latest.get("device_name", "-"),
                    "model": overview.get("model") or "-",
                    "serial": overview.get("serial_number") or "-",
                    "os_ver": overview.get("os_version") or "-",
                    "mgmt_ip": overview.get("management_ip") or overview.get("mgmt_ip") or "-",
                    "ifaces": f"{total_ifaces}/{up_ifaces}/{down_ifaces}/{admin_down}",
                    "access": access_ports,
                    "trunk": trunk_ports,
                    "unused": unused_ports,
                    "vlans": vlan_count,
                    "native_vlan": native_vlan or "-",
                    "trunk_allowed": trunk_allowed_summary,
                    "stp": stp_mode,
                    "stp_role": stp_role_summary,
                    "ospf_neigh": ospf_neighbors,
                    "bgp_asn_neigh": bgp_summary,
                    "rt_proto": rt_proto_str,
                    "cpu": overview.get("cpu_utilization") or overview.get("cpu_util") or "-",
                    "mem": overview.get("memory_usage") or overview.get("mem_util") or "-",
                    "status": status,
                    "upload_timestamp": upload_ts,
                })
    
    # Fallback: Also check documents collection for parsed_config metadata (Cisco may have only device_overview.hostname)
    async for doc in db()["documents"].find(
        {"project_id": project_id, "is_latest": True, "parsed_config": {"$exists": True}},
        sort=[("created_at", -1)]
    ):
        parsed_config = doc.get("parsed_config", {})
        device_name = parsed_config.get("device_name")
        if not device_name and isinstance(parsed_config.get("device_overview"), dict):
            device_name = parsed_config.get("device_overview").get("hostname")
        device_name = (device_name or "").strip() if isinstance(device_name, str) else None

        if device_name and device_name not in device_names:
            device_names.add(device_name)
            # Use parsed_config from documents collection - reuse the same formatting logic
            if parsed_config:
                # Remove MongoDB _id to avoid serialization issues
                parsed_config.pop("_id", None)
                
                # Format for table display (reuse same logic as above)
                interfaces = parsed_config.get("interfaces", [])
                vlans = parsed_config.get("vlans", {})
                stp = parsed_config.get("stp", {})
                routing = parsed_config.get("routing", {})
                overview = parsed_config.get("device_overview", {})
                
                # Calculate stats
                total_ifaces = len(interfaces)
                up_ifaces = sum(1 for i in interfaces if i.get("oper_status") == "up")
                down_ifaces = sum(1 for i in interfaces if i.get("oper_status") == "down")
                admin_down = sum(1 for i in interfaces if i.get("admin_status") == "down")
                
                access_ports = sum(1 for i in interfaces if i.get("port_mode") == "access")
                trunk_ports = sum(1 for i in interfaces if i.get("port_mode") == "trunk")
                unused_ports = sum(1 for i in interfaces if not i.get("port_mode") or i.get("port_mode") == "none")
                
                vlan_count = vlans.get("total_vlan_count", len(vlans.get("vlan_list", [])))
                
                # Get native VLAN (most common from trunk ports)
                native_vlans = [i.get("native_vlan") for i in interfaces if i.get("native_vlan")]
                native_vlan = native_vlans[0] if native_vlans else None
                
                # STP info - extract from stp.interfaces
                stp_mode = stp.get("stp_mode") or stp.get("mode") or "-"
                stp_interfaces = stp.get("interfaces", [])
                stp_roles = {}
                for stp_iface in stp_interfaces:
                    role = stp_iface.get("role")
                    if role:
                        stp_roles[role] = stp_roles.get(role, 0) + 1
                
                if stp_roles:
                    root_bridges = stp.get("root_bridges", [])
                    if root_bridges and len(root_bridges) > 0:
                        stp_role_summary = "Root"
                    elif "Root" in stp_roles:
                        stp_role_summary = f"R:{stp_roles.get('Root', 0)}/D:{stp_roles.get('Designated', 0)}"
                    elif "Designated" in stp_roles:
                        stp_role_summary = f"D:{stp_roles.get('Designated', 0)}"
                    else:
                        stp_role_summary = ", ".join([f"{k}:{v}" for k, v in list(stp_roles.items())[:2]])
                else:
                    stp_role_summary = "-"
                
                # Get trunk allowed VLANs summary - collect all unique VLANs from trunk ports
                all_trunk_vlans = set()
                has_all_vlans = False
                for iface in interfaces:
                    if iface.get("port_mode") == "trunk":
                        allowed = iface.get("allowed_vlans")
                        if allowed:
                            allowed_str = str(allowed).strip()
                            if allowed_str.upper() == "ALL" or allowed_str in ["1-4094", "1-4095"]:
                                has_all_vlans = True
                            else:
                                parts = allowed_str.replace(",", " ").split()
                                for part in parts:
                                    part = part.strip()
                                    if part.isdigit():
                                        all_trunk_vlans.add(int(part))
                
                if has_all_vlans:
                    trunk_allowed_summary = "ALL"
                elif all_trunk_vlans:
                    sorted_vlans = sorted(all_trunk_vlans)
                    trunk_allowed_summary = " ".join(str(v) for v in sorted_vlans)
                    if len(trunk_allowed_summary) > 20:
                        trunk_allowed_summary = trunk_allowed_summary[:17] + "..."
                else:
                    trunk_allowed_summary = "-"
                
                # OSPF neighbors - updated for new parser structure
                ospf = routing.get("ospf")
                if isinstance(ospf, dict):
                    ospf_neighbors = len(ospf.get("neighbors", []))
                else:
                    ospf_neighbors = 0
                
                # BGP info - updated for new parser structure
                bgp = routing.get("bgp")
                if isinstance(bgp, dict):
                    bgp_asn = bgp.get("as_number") or bgp.get("local_as") or "-"
                    bgp_neighbors = len(bgp.get("peers", []))
                else:
                    bgp_asn = "-"
                    bgp_neighbors = 0
                bgp_summary = f"{bgp_asn}/{bgp_neighbors}" if bgp_asn != "-" else "-/-"
                
                # Routing protocols - updated for new parser structure
                rt_protos = []
                if isinstance(ospf, dict) and ospf.get("process_id"):
                    rt_protos.append("OSPF")
                if isinstance(bgp, dict) and (bgp.get("as_number") or bgp.get("local_as")):
                    rt_protos.append("BGP")
                
                # Check for RIP
                rip = routing.get("rip")
                if isinstance(rip, dict) and (rip.get("version") or rip.get("networks") or rip.get("interfaces")):
                    rt_protos.append("RIP")
                
                # Check for EIGRP
                eigrp = routing.get("eigrp")
                if isinstance(eigrp, dict) and (eigrp.get("as_number") or eigrp.get("router_id")):
                    rt_protos.append("EIGRP")
                
                static_routes = routing.get("static", [])
                if isinstance(static_routes, list) and len(static_routes) > 0:
                    rt_protos.append("Static")
                elif isinstance(static_routes, dict) and static_routes.get("routes"):
                    rt_protos.append("Static")
                rt_proto_str = ", ".join(rt_protos) if rt_protos else "-"
                
                # Status (simplified - OK for now, can add drift detection later)
                status = "OK"
                
                # Format datetime
                upload_ts = parsed_config.get("upload_timestamp")
                if isinstance(upload_ts, datetime):
                    upload_ts = upload_ts.isoformat()
                
                devices.append({
                    "device": parsed_config.get("device_name", "-"),
                    "model": overview.get("model") or "-",
                    "serial": overview.get("serial_number") or "-",
                    "os_ver": overview.get("os_version") or "-",
                    "mgmt_ip": overview.get("management_ip") or overview.get("mgmt_ip") or "-",
                    "ifaces": f"{total_ifaces}/{up_ifaces}/{down_ifaces}/{admin_down}",
                    "access": access_ports,
                    "trunk": trunk_ports,
                    "unused": unused_ports,
                    "vlans": vlan_count,
                    "native_vlan": native_vlan or "-",
                    "trunk_allowed": trunk_allowed_summary,
                    "stp": stp_mode,
                    "stp_role": stp_role_summary,
                    "ospf_neigh": ospf_neighbors,
                    "bgp_asn_neigh": bgp_summary,
                    "rt_proto": rt_proto_str,
                    "cpu": overview.get("cpu_utilization") or overview.get("cpu_util") or "-",
                    "mem": overview.get("memory_usage") or overview.get("mem_util") or "-",
                    "status": status,
                    "upload_timestamp": upload_ts,
                })
    
    return {"summaryRows": devices, "count": len(devices)}


@router.get("/{device_name}")
async def get_device_details(
    project_id: str,
    device_name: str,
    user=Depends(get_current_user)
):
    """Get detailed parsed config for a specific device"""
    await check_project_access(project_id, user)
    
    # Get latest parsed config for this device (versioning system - get latest version)
    # Try parsed_configs collection first, then fallback to documents collection
    device = await db()["parsed_configs"].find_one(
        {"project_id": project_id, "device_name": device_name},
        sort=[("version", -1)]  # Get latest version
    )
    
    # Debug: Log what we found
    if device:
        print(f"📥 Found device {device_name} in parsed_configs:")
        print(f"   - Has neighbors field: {'neighbors' in device}")
        print(f"   - Neighbors count: {len(device.get('neighbors', []))}")
        print(f"   - Has original_content: {'original_content' in device}")
        print(f"   - All top-level keys: {list(device.keys())[:10]}...")  # First 10 keys
    else:
        print(f"⚠️ Device {device_name} not found in parsed_configs, trying documents collection...")
    
    # Fallback: Check documents collection for parsed_config metadata
    if not device:
        doc = await db()["documents"].find_one(
            {"project_id": project_id, "is_latest": True, "parsed_config.device_name": device_name},
            sort=[("created_at", -1)]
        )
        if doc and doc.get("parsed_config"):
            device = doc.get("parsed_config")
            print(f"📥 Found device {device_name} in documents collection (parsed_config):")
            print(f"   - Has neighbors field: {'neighbors' in device}")
            print(f"   - Neighbors count: {len(device.get('neighbors', []))}")
            print(f"   - Has original_content: {'original_content' in device}")
            # If original_content is not in parsed_config, try to read from file
            if not device.get("original_content") and doc.get("document_id"):
                try:
                    from ..services.document_storage import get_document_file_path
                    file_path = await get_document_file_path(project_id, doc["document_id"])
                    if file_path and file_path.exists():
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            device["original_content"] = f.read()
                except Exception as e:
                    print(f"Warning: Could not read original file content: {e}")
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # If original_content is still missing, try to read from document file
    if not device.get("original_content"):
        # Try to get document_id from device or find it
        document_id = device.get("document_id")
        if document_id:
            try:
                from ..services.document_storage import get_document_file_path
                file_path = await get_document_file_path(project_id, document_id)
                if file_path and file_path.exists():
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        device["original_content"] = f.read()
            except Exception as e:
                print(f"Warning: Could not read original file content from document: {e}")
    
    # Remove MongoDB _id
    device.pop("_id", None)
    
    # Convert datetime to ISO string
    for key in ["upload_timestamp", "created_at", "updated_at"]:
        if key in device and isinstance(device[key], datetime):
            device[key] = device[key].isoformat()
    
    # Debug: Log what we're returning
    neighbors_count = len(device.get("neighbors", []))
    has_original_content = bool(device.get("original_content"))
    print(f"📤 Returning device details for {device_name}:")
    print(f"   - neighbors count: {neighbors_count}")
    print(f"   - has original_content: {has_original_content}")
    print(f"   - neighbors sample: {device.get('neighbors', [])[:2] if neighbors_count > 0 else 'None'}")
    
    # Include original_content if available (may be large, but needed for Raw tab)
    # Note: original_content is stored as string in parsed_configs collection
    
    return device

