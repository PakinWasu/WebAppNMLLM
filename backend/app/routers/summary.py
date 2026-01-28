"""Summary API endpoints for device configuration summary"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from datetime import datetime

from ..db.mongo import db
from ..dependencies.auth import get_current_user, check_project_access

router = APIRouter(prefix="/projects/{project_id}/summary", tags=["summary"])


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
                
                # STP info - updated for new parser structure
                stp_mode = stp.get("stp_mode") or "-"
                # New parser doesn't have port_roles, so set to "-"
                stp_role_summary = "-"
                
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
                    "trunk_allowed": "-",  # Can be calculated from interfaces if needed
                    "stp": stp_mode,
                    "stp_role": stp_role_summary,
                    "ospf_neigh": ospf_neighbors,
                    "bgp_asn_neigh": bgp_summary,
                    "rt_proto": rt_proto_str,
                    "cpu": overview.get("cpu_utilization") or overview.get("cpu_util") or "-",
                    "mem": overview.get("mem_util") or "-",  # New parser doesn't have mem_util
                    "status": status,
                    "upload_timestamp": upload_ts,
                })
    
    # Fallback: Also check documents collection for parsed_config metadata
    async for doc in db()["documents"].find(
        {"project_id": project_id, "is_latest": True, "parsed_config": {"$exists": True}},
        sort=[("created_at", -1)]
    ):
        parsed_config = doc.get("parsed_config", {})
        device_name = parsed_config.get("device_name")
        
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
                
                # STP info - updated for new parser structure
                stp_mode = stp.get("stp_mode") or "-"
                # New parser doesn't have port_roles, so set to "-"
                stp_role_summary = "-"
                
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
                    "trunk_allowed": "-",  # Can be calculated from interfaces if needed
                    "stp": stp_mode,
                    "stp_role": stp_role_summary,
                    "ospf_neigh": ospf_neighbors,
                    "bgp_asn_neigh": bgp_summary,
                    "rt_proto": rt_proto_str,
                    "cpu": overview.get("cpu_utilization") or overview.get("cpu_util") or "-",
                    "mem": overview.get("mem_util") or "-",  # New parser doesn't have mem_util
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

