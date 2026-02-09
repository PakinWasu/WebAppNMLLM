"""Script Generator API endpoints for device inventory and command template management"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from enum import Enum

from ..db.mongo import db
from ..dependencies.auth import get_current_user, check_project_access, check_project_editor_or_admin

router = APIRouter(prefix="/projects/{project_id}/script-settings", tags=["script-generator"])


# Default command templates
CISCO_DEFAULTS = """term len 0
! --- System Info ---
show version
show running-config
show processes cpu sorted
show memory statistics
! --- Interfaces & VLANs ---
show interfaces
show interfaces switchport
show vlan brief
show spanning-tree detail
! --- Routing & Neighbors ---
show ip route
show ip ospf neighbor
show cdp neighbors detail
show lldp neighbors detail
! --- Tables ---
show mac address-table
show ip arp
! --- Security & Management ---
show ssh
show ntp status
show logging
! --- HA ---
show etherchannel summary
show standby brief"""

HUAWEI_DEFAULTS = """screen-length 0 temporary
! --- System Info ---
display version
display current-configuration
display cpu-usage
display memory
! --- Interfaces & VLANs ---
display interface
display vlan
display stp
! --- Routing & Neighbors ---
display ip routing-table
display ospf peer
display lldp neighbor
! --- Tables ---
display mac-address
display arp
! --- Security & Management ---
display ssh server status
display ntp-service status
display info-center
! --- HA ---
display eth-trunk
display vrrp brief"""


class DeviceType(str, Enum):
    CISCO_IOS = "cisco_ios"
    HUAWEI_VRP = "huawei_vrp"


class DeviceInventoryItem(BaseModel):
    ip: str = Field(..., description="Device IP address")
    hostname: Optional[str] = Field(None, description="Device hostname")
    username: str = Field(..., description="SSH username")
    password: Optional[str] = Field(None, description="SSH password")
    secret: Optional[str] = Field(None, description="Enable secret (for Cisco)")
    port: int = Field(22, description="SSH port")
    device_type: DeviceType = Field(..., description="Device vendor/type")


class ScriptSettingsCreate(BaseModel):
    device_inventory: List[DeviceInventoryItem] = Field(default_factory=list)
    cisco_commands: str = Field(default="")
    huawei_commands: str = Field(default="")


class ScriptSettingsResponse(BaseModel):
    device_inventory: List[DeviceInventoryItem]
    cisco_commands: str
    huawei_commands: str
    last_updated: Optional[str] = None
    updated_by: Optional[str] = None


@router.get("", response_model=ScriptSettingsResponse)
async def get_script_settings(project_id: str, user=Depends(get_current_user)):
    """Get script generation settings for a project. Returns defaults if not exists."""
    await check_project_access(project_id, user)
    
    # Check if project exists
    project = await db()["projects"].find_one({"project_id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get settings from MongoDB
    settings_doc = await db()["script_generation_settings"].find_one({"project_id": project_id})
    
    if not settings_doc:
        # Return defaults
        return ScriptSettingsResponse(
            device_inventory=[],
            cisco_commands=CISCO_DEFAULTS,
            huawei_commands=HUAWEI_DEFAULTS,
            last_updated=None,
            updated_by=None
        )
    
    # Convert datetime to ISO string
    last_updated = settings_doc.get("last_updated")
    if isinstance(last_updated, datetime):
        last_updated = last_updated.isoformat()
    
    return ScriptSettingsResponse(
        device_inventory=settings_doc.get("device_inventory", []),
        cisco_commands=settings_doc.get("cisco_commands", CISCO_DEFAULTS),
        huawei_commands=settings_doc.get("huawei_commands", HUAWEI_DEFAULTS),
        last_updated=last_updated,
        updated_by=settings_doc.get("updated_by")
    )


@router.post("", response_model=ScriptSettingsResponse)
async def save_script_settings(
    project_id: str,
    body: ScriptSettingsCreate,
    user=Depends(get_current_user)
):
    """Save script generation settings for a project. Only admin, manager, or engineer can save."""
    await check_project_editor_or_admin(project_id, user)
    
    # Check if project exists
    project = await db()["projects"].find_one({"project_id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Prepare update data
    now = datetime.now(timezone.utc)
    update_data = {
        "project_id": project_id,
        "device_inventory": [item.dict() for item in body.device_inventory],
        "cisco_commands": body.cisco_commands or CISCO_DEFAULTS,
        "huawei_commands": body.huawei_commands or HUAWEI_DEFAULTS,
        "last_updated": now,
        "updated_by": user["username"]
    }
    
    # Upsert settings
    await db()["script_generation_settings"].update_one(
        {"project_id": project_id},
        {"$set": update_data},
        upsert=True
    )
    
    # Return updated settings
    return ScriptSettingsResponse(
        device_inventory=body.device_inventory,
        cisco_commands=body.cisco_commands or CISCO_DEFAULTS,
        huawei_commands=body.huawei_commands or HUAWEI_DEFAULTS,
        last_updated=now.isoformat(),
        updated_by=user["username"]
    )
