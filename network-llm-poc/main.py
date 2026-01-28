
from fastapi import FastAPI, UploadFile, File, HTTPException
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import json
import re
import difflib

import httpx  # pip install httpx


app = FastAPI(
    title="Network Config Parser (Rule-based + LLM Gap Filler/Validator)",
    description=(
        "Upload Cisco config/show text file and parse into JSON based on section 2.3.2.\n"
        "- Parsing uses only deterministic rules.\n"
        "- LLM is used ONLY to (1) validate completeness/consistency and (2) fill missing fields\n"
        "  *only if the value can be clearly read from the original config*. "
        "Existing non-empty values are never overwritten."
    ),
)

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

BACKUP_DIR = Path("backups")
BACKUP_DIR.mkdir(exist_ok=True)

# ---------- LLM CONFIG ----------
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL_NAME = "qwen2.5:7b-instruct"


# ---------- SECTION SPLITTER ----------

def split_sections(raw_text: str) -> Dict[str, str]:
    """
    Split file by marker lines of the form:
    ! ===== show xxx =====

    Returns dict: { "show running-config": "...", "show ip interface brief": "...", ... }
    """
    sections: Dict[str, List[str]] = {}
    current_key = "full_text"

    lines = raw_text.splitlines()
    for line in lines:
        m = re.match(r"!+\s*=====+\s*(show .+?)\s*=====+", line.strip(), re.IGNORECASE)
        if m:
            current_key = m.group(1).strip().lower()
            sections[current_key] = []
        else:
            sections.setdefault(current_key, []).append(line)

    joined = {k: "\n".join(v).strip() for k, v in sections.items()}
    return joined


# ---------- PARSERS (2.3.2.x) ----------

def parse_device_overview(sections: Dict[str, str], device_id: str, upload_timestamp: str) -> Dict[str, Any]:
    """
    2.3.2.1 Device Overview (rule-based only)
    """
    running = sections.get("show running-config", "")
    show_version = sections.get("show version", "")
    show_inventory = sections.get("show inventory", "")
    show_ip_int_br = sections.get("show ip interface brief", "")
    cpu_proc = sections.get("show processes cpu", "")
    mem_proc = sections.get("show processes memory", "")

    hostname = None
    role = None
    model_platform = None
    os_version = None
    serial_number = None
    management_ip = None
    uptime = None
    cpu_util = None
    mem_util = None

    # hostname
    m = re.search(r"^hostname\s+(\S+)", running, re.MULTILINE)
    if m:
        hostname = m.group(1).strip()

    # role (ROLE comment or rule-based guess, NOT LLM)
    m = re.search(r"^!+\s*ROLE:\s*(.+)$", running, re.MULTILINE | re.IGNORECASE)
    if m:
        role = m.group(1).strip()
    else:
        if "router ospf" in running or "router bgp" in running:
            role = "Core Router"
        elif "spanning-tree" in running and "switchport" in running:
            role = "Switch"
        else:
            role = "Router/Switch"

    # OS version
    m = re.search(r"^Cisco IOS.*Version\s+([^\r\n]+)", show_version, re.MULTILINE)
    if m:
        os_version = "Cisco IOS " + m.group(1).strip()
    elif show_version:
        first_line = show_version.splitlines()[0].strip()
        os_version = first_line

    # uptime
    m = re.search(r"uptime is\s+(.+)", show_version)
    if m:
        uptime = m.group(1).strip()

    # model + serial
    m = re.search(r"PID:\s*([^\s,]+).*SN:\s*([^\s]+)", show_inventory)
    if m:
        model_platform = m.group(1).strip()
        serial_number = m.group(2).strip()

    # management IP from show ip int brief
    mgmt_ip = None
    for line in show_ip_int_br.splitlines():
        parts = line.split()
        if len(parts) >= 6 and parts[0] != "Interface":
            iface, ip, *_rest = parts
            status = parts[-2]
            proto = parts[-1]
            if ip.lower() != "unassigned" and status.lower() == "up" and proto.lower() == "up":
                # If SVI (Vlan) assume management IP
                if iface.lower().startswith("vl"):
                    mgmt_ip = ip
                    break
                if mgmt_ip is None:
                    mgmt_ip = ip
    management_ip = mgmt_ip

    # CPU
    m = re.search(r"CPU utilization.*?:\s*([0-9]+)%", cpu_proc)
    if m:
        cpu_util = m.group(1) + "%"

    # Memory
    m = re.search(r"Processor Pool Total:\s*([0-9]+).*Used:\s*([0-9]+).*Free:\s*([0-9]+)", mem_proc)
    if m:
        total = int(m.group(1))
        used = int(m.group(2))
        if total > 0:
            percent = used * 100 // total
            mem_util = f"{percent}%"

    return {
        "hostname": hostname or device_id,
        "role": role,
        "model_platform": model_platform,
        "os_version": os_version,
        "serial_number": serial_number,
        "management_ip": management_ip,
        "uptime": uptime,
        "cpu_utilization": cpu_util,
        "memory_utilization": mem_util,
        "last_config_upload_timestamp": upload_timestamp,
    }


def parse_interfaces(sections: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    2.3.2.2 Interface Information
    Uses: show ip interface brief, show interfaces status, show interfaces switchport
    """
    ip_br = sections.get("show ip interface brief", "")
    int_status = sections.get("show interfaces status", "")
    switchport = sections.get("show interfaces switchport", "")

    interfaces: Dict[str, Dict[str, Any]] = {}

    # from show ip interface brief
    for line in ip_br.splitlines():
        if line.strip().startswith("Interface") or not line.strip():
            continue
        parts = line.split()
        if len(parts) < 6:
            continue
        name, ip, *_rest = parts
        status = parts[-2]
        proto = parts[-1]
        iface = interfaces.setdefault(name, {
            "name": name,
            "type": None,
            "admin_status": None,
            "oper_status": None,
            "line_protocol_status": None,
            "description": None,
            "ipv4_address": None,
            "ipv6_address": None,
            "mac_address": None,
            "speed": None,
            "duplex_mode": None,
            "mtu": None,
            "port_mode": None,
            "access_vlan": None,
            "native_vlan": None,
            "allowed_vlans": None,
        })
        iface["ipv4_address"] = None if ip.lower() == "unassigned" else ip
        iface["admin_status"] = status
        iface["oper_status"] = proto
        iface["line_protocol_status"] = proto

        if name.lower().startswith("vl"):
            iface["type"] = "Layer3"
        elif name.lower().startswith(("gi", "te", "fa")):
            iface["type"] = "Layer2/Layer3"
        else:
            iface["type"] = "Unknown"

    # from show interfaces status
    for line in int_status.splitlines():
        if line.strip().startswith("Port") or not line.strip():
            continue
        parts = line.split()
        if len(parts) < 7:
            continue
        name = parts[0]
        duplex = parts[4]
        speed = parts[5]

        iface = interfaces.setdefault(name, {
            "name": name,
            "type": None,
            "admin_status": None,
            "oper_status": None,
            "line_protocol_status": None,
            "description": None,
            "ipv4_address": None,
            "ipv6_address": None,
            "mac_address": None,
            "speed": None,
            "duplex_mode": None,
            "mtu": None,
            "port_mode": None,
            "access_vlan": None,
            "native_vlan": None,
            "allowed_vlans": None,
        })
        iface["speed"] = speed
        iface["duplex_mode"] = duplex

    # from show interfaces switchport
    current_if = None
    for line in switchport.splitlines():
        line = line.rstrip()
        m_name = re.match(r"Name:\s*(\S+)", line, re.IGNORECASE)
        if m_name:
            current_if = m_name.group(1)
            interfaces.setdefault(current_if, {
                "name": current_if,
                "type": None,
                "admin_status": None,
                "oper_status": None,
                "line_protocol_status": None,
                "description": None,
                "ipv4_address": None,
                "ipv6_address": None,
                "mac_address": None,
                "speed": None,
                "duplex_mode": None,
                "mtu": None,
                "port_mode": None,
                "access_vlan": None,
                "native_vlan": None,
                "allowed_vlans": None,
            })
            continue

        if not current_if:
            continue

        m = re.search(r"Administrative Mode:\s*(.+)", line, re.IGNORECASE)
        if m:
            mode = m.group(1).strip().lower()
            if "trunk" in mode:
                interfaces[current_if]["port_mode"] = "Trunk"
            elif "access" in mode:
                interfaces[current_if]["port_mode"] = "Access"

        m = re.search(r"Access Mode VLAN:\s*([0-9]+)", line, re.IGNORECASE)
        if m:
            interfaces[current_if]["access_vlan"] = m.group(1)

        m = re.search(r"Trunking Native Mode VLAN:\s*([0-9]+)", line, re.IGNORECASE)
        if m:
            interfaces[current_if]["native_vlan"] = m.group(1)

        m = re.search(r"Trunking VLANs Enabled:\s*(.+)", line, re.IGNORECASE)
        if m:
            interfaces[current_if]["allowed_vlans"] = m.group(1).strip()

    return list(interfaces.values())


def parse_vlans(sections: Dict[str, str]) -> Dict[str, Any]:
    """
    2.3.2.3 VLAN & Layer 2 Switching
    """
    vlan_brief = sections.get("show vlan brief", "")
    switchport = sections.get("show interfaces switchport", "")

    vlan_list = []
    access_ports = []
    trunk_ports = []
    native_vlans = []

    for line in vlan_brief.splitlines():
        stripped = line.strip()
        if not stripped or stripped.lower().startswith("vlan"):
            continue
        parts = stripped.split()
        if len(parts) < 3:
            continue
        vlan_id = parts[0]
        name = parts[1]
        status = parts[2]
        vlan_list.append({
            "vlan_id": vlan_id,
            "name": name,
            "status": status,
        })

    current_if = None
    for line in switchport.splitlines():
        line = line.rstrip()
        m = re.match(r"Name:\s*(\S+)", line, re.IGNORECASE)
        if m:
            current_if = m.group(1)
            continue

        if not current_if:
            continue

        m = re.search(r"Access Mode VLAN:\s*([0-9]+)", line, re.IGNORECASE)
        if m:
            access_ports.append({
                "interface": current_if,
                "vlan_id": m.group(1),
            })

        m = re.search(r"Trunking Native Mode VLAN:\s*([0-9]+)", line, re.IGNORECASE)
        if m:
            native_vlans.append({
                "interface": current_if,
                "native_vlan": m.group(1),
            })

        m = re.search(r"Trunking VLANs Enabled:\s*(.+)", line, re.IGNORECASE)
        if m:
            trunk_ports.append({
                "interface": current_if,
                "allowed_vlans": m.group(1).strip(),
            })

    return {
        "vlan_list": vlan_list,
        "access_ports": access_ports,
        "trunk_ports": trunk_ports,
        "native_vlans": native_vlans,
        "total_vlan_count": len(vlan_list),
    }


def parse_stp(sections: Dict[str, str]) -> Dict[str, Any]:
    """
    2.3.2.4 STP Information (simplified)
    """
    stp = sections.get("show spanning-tree", "")
    mode = None
    root_bridge_id = None
    root_priority = None
    is_root = False
    ports = []

    m = re.search(r"Spanning tree enabled protocol\s+(\S+)", stp, re.IGNORECASE)
    if m:
        mode = m.group(1).upper()

    m = re.search(r"Root ID\s+Priority\s+([0-9]+)\s*[\\r\\n]+[ \\t]*Address\s+([0-9a-fA-F\\.]+)", stp, re.MULTILINE)
    if m:
        root_priority = m.group(1)
        root_bridge_id = m.group(2)

    if "This bridge is the root" in stp:
        is_root = True

    for line in stp.splitlines():
        stripped = line.strip()
        if (
            not stripped
            or stripped.startswith(("Interface", "Spanning", "Root", "Bridge", "This"))
        ):
            continue

        parts = stripped.split()
        if len(parts) < 4:
            continue

        iface = parts[0]
        # Accept typical interface name patterns only
        if not re.match(r"(Gi|Te|Fa|Po|Eth|Hu)[0-9/]+", iface, re.IGNORECASE):
            continue

        role = parts[1]
        state = parts[2]
        cost = parts[3]
        ports.append({
            "interface": iface,
            "role": role,
            "state": state,
            "cost": cost,
            "portfast_enabled": None,
            "bpdu_guard_enabled": None,
        })

    return {
        "mode": mode,
        "root_bridge_id": root_bridge_id,
        "root_priority": root_priority,
        "is_root_bridge": is_root,
        "ports": ports,
    }


def parse_routing(sections: Dict[str, str]) -> Dict[str, Any]:
    """
    2.3.2.5 Routing Protocol Information (basic)
    """
    ip_route = sections.get("show ip route", "")
    ospf = sections.get("show ip ospf", "")
    ospf_nei = sections.get("show ip ospf neighbor", "")
    bgp_sum = sections.get("show ip bgp summary", "")

    static_routes = []

    # Static routes from show ip route
    for line in sections.get("show_ip_route", []):
        line = line.strip()
        if not line.startswith("S"):
            continue

        # ตัวอย่างบรรทัดที่รองรับ:
        # S* 0.0.0.0/0 [1/0] via 203.0.113.1, GigabitEthernet0/0/0
        m = re.search(
            r"(S\*|S)\s+([0-9./]+)\s+\[([0-9]+)/([0-9]+)\]\s+via\s+([0-9.]+),\s*(\S+)",
            line,
        )
        if m:
            flag = m.group(1)        # S หรือ S*
            prefix = m.group(2)      # 0.0.0.0/0
            admin_distance = int(m.group(3))
            metric = int(m.group(4))
            next_hop = m.group(5)
            exit_if = m.group(6)

            static_routes.append(
                {
                    "destination": prefix,
                    "mask": None,
                    "next_hop": next_hop,
                    "exit_interface": exit_if,
                    "admin_distance": admin_distance,
                    "is_default_route": prefix == "0.0.0.0/0",
                }
            )


    # OSPF info
    ospf_info = {
        "router_id": None,
        "process_id": None,
        "areas": [],
        "interfaces": [],
        "neighbors": [],
        "dr_bdr": [],
        "learned_prefix_summary": None,
    }

    m = re.search(r'Routing Process "ospf\\s+([0-9]+)" with ID ([0-9\\.]+)', ospf)
    if m:
        ospf_info["process_id"] = m.group(1)
        ospf_info["router_id"] = m.group(2)

    for line in ospf_nei.splitlines():
        if line.strip().startswith("Neighbor ID") or not line.strip():
            continue
        parts = line.split()
        if len(parts) < 6:
            continue
        neigh_id = parts[0]
        state = parts[2]
        addr = parts[4]
        iface = parts[5]
        ospf_info["neighbors"].append({
            "neighbor_id": neigh_id,
            "state": state,
            "address": addr,
            "interface": iface,
        })

    # BGP info
    bgp_info = {
        "local_as": None,
        "peers": [],
        "received_prefixes": None,
        "advertised_prefixes": None,
    }

    m = re.search(r"local AS number\\s+([0-9]+)", bgp_sum)
    if m:
        bgp_info["local_as"] = m.group(1)

    for line in bgp_sum.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("Neighbor"):
            continue

        if stripped.startswith("BGP router identifier"):
            continue

        parts = stripped.split()
        if len(parts) < 8:
            continue

        if not re.match(r"\\d+\\.\\d+\\.\\d+\\.\\d+", parts[0]):
            continue

        neighbor_ip = parts[0]
        peer_as = parts[2]
        pfx = parts[-1]
        bgp_info["peers"].append({
            "neighbor_ip": neighbor_ip,
            "remote_as": peer_as,
            "state_or_prefixes": pfx,
        })

    return {
        "static": {
            "routes": static_routes,
        },
        "ospf": ospf_info,
        "eigrp": {
            "as_number": None,
            "router_id": None,
            "neighbors": [],
            "hold_time": None,
            "learned_routes": [],
        },
        "bgp": bgp_info,
        "rip": {
            "version": None,
            "advertised_networks": [],
            "learned_networks": [],
            "routes": [],
            "timers": None,
            "admin_distance": None,
            "auto_summary": None,
            "passive_interfaces": [],
        },
    }


def parse_neighbors_topology(sections: Dict[str, str]) -> Dict[str, Any]:
    """
    2.3.2.6 Neighbor & Topology Information
    (from show cdp neighbors table)
    """
    cdp = sections.get("show cdp neighbors", "")
    neighbors = []

    for line in cdp.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("Device ID"):
            continue
        parts = stripped.split()
        if len(parts) < 6:
            continue
        neighbor_name = parts[0]
        local_int = parts[1]
        platform = parts[-2]
        remote_port = parts[-1]
        neighbors.append({
            "neighbor_device_name": neighbor_name,
            "neighbor_ip": None,
            "neighbor_platform": platform,
            "local_port": local_int,
            "remote_port": remote_port,
            "capabilities": None,
            "discovery_protocol": "CDP",
        })

    return {
        "neighbors": neighbors,
    }


def parse_mac_arp(sections: Dict[str, str]) -> Dict[str, Any]:
    """
    2.3.2.7 MAC & ARP
    """
    mac_tbl = sections.get("show mac address-table", "")
    arp_tbl = sections.get("show arp", "")

    mac_table = []
    arp_table = []

    # MAC table
    for line in mac_tbl.splitlines():
        stripped = line.strip()
        if (
            not stripped
            or "Mac Address Table" in stripped
            or "---" in stripped
            or stripped.lower().startswith("vlan")
        ):
            continue

        parts = stripped.split()
        if len(parts) < 4:
            continue

        vlan = parts[0]
        mac = parts[1]
        typ = parts[2]
        iface = parts[3]

        mac_table.append({
            "mac_address": mac,
            "vlan": vlan,
            "interface": iface,
            "type": typ,
        })

    # ARP table
    for line in arp_tbl.splitlines():
        stripped = line.strip()
        if not stripped or stripped.lower().startswith("protocol"):
            continue
        parts = stripped.split()
        if len(parts) < 6:
            continue
        ip = parts[1]
        age = parts[2]
        mac = parts[3]
        iface = parts[5]
        arp_table.append({
            "ip_address": ip,
            "mac_address": mac,
            "interface": iface,
            "age": age,
        })

    return {
        "mac_table": mac_table,
        "arp_table": arp_table,
    }


def parse_security_management(sections: Dict[str, str]) -> Dict[str, Any]:
    """
    2.3.2.8 Security & Management
    """
    running = sections.get("show running-config", "")

    user_accounts = []
    aaa = []
    ssh = {}
    snmp = []
    ntp = []
    syslog = []
    acls = []

    for m in re.finditer(r"^username\\s+(.+)$", running, re.MULTILINE):
        user_accounts.append(m.group(1).strip())

    for line in running.splitlines():
        stripped = line.strip()
        if stripped.startswith("aaa "):
            aaa.append(stripped)

    m = re.search(r"ip ssh version\\s+([0-9]+)", running)
    if m:
        ssh["version"] = m.group(1)
    else:
        ssh["version"] = None

    for line in running.splitlines():
        stripped = line.strip()
        if stripped.startswith("snmp-server "):
            snmp.append(stripped)

    for line in running.splitlines():
        stripped = line.strip()
        if stripped.startswith("ntp "):
            ntp.append(stripped)

    for line in running.splitlines():
        stripped = line.strip()
        if stripped.startswith("logging "):
            syslog.append(stripped)

    for line in running.splitlines():
        stripped = line.strip()
        if stripped.startswith("access-list "):
            acls.append(stripped)

    return {
        "user_accounts": user_accounts,
        "aaa": aaa,
        "ssh": ssh,
        "snmp": snmp,
        "ntp": ntp,
        "syslog": syslog,
        "acls": acls,
    }


def parse_high_availability(sections: Dict[str, str]) -> Dict[str, Any]:
    """
    2.3.2.9 High Availability (EtherChannel / HSRP / VRRP)
    """
    running = sections.get("show running-config", "")

    etherchannel = {"port_channels": []}
    hsrp = {"groups": []}
    vrrp = {"groups": []}

    po_ports: Dict[str, Dict[str, Any]] = {}
    current_int = None

    # EtherChannel: channel-group + Port-channel interface
    for line in running.splitlines():
        line = line.rstrip()

        # Port-channel interface
        m = re.match(r"^interface\\s+(Port-channel[0-9/]+)", line, re.IGNORECASE)
        if m:
            current_int = m.group(1)
            po_ports.setdefault(current_int, {
                "name": current_int,
                "mode": None,
                "member_interfaces": [],
                "status": "unknown",
            })
            continue

        # physical interface
        m2 = re.match(r"^interface\\s+([GTg][iI][0-9/\\.]+)", line)
        if m2:
            current_int = m2.group(1)
            continue

        if not current_int:
            continue

        # channel-group
        m = re.search(r"channel-group\\s+([0-9]+)\\s+mode\\s+(\\S+)", line, re.IGNORECASE)
        if m:
            group_id = m.group(1)
            mode = m.group(2).lower()
            po_name = f"Port-channel{group_id}"
            po = po_ports.setdefault(po_name, {
                "name": po_name,
                "mode": mode.upper(),
                "member_interfaces": [],
                "status": "up",
            })
            if current_int not in po["member_interfaces"]:
                po["member_interfaces"].append(current_int)

    etherchannel["port_channels"] = list(po_ports.values())

    # HSRP
    current_int = None
    for line in running.splitlines():
        line = line.rstrip()
        m = re.match(r"^interface\\s+(\\S+)", line, re.IGNORECASE)
        if m:
            current_int = m.group(1)
            continue
        if not current_int:
            continue

        m = re.search(r"standby\\s+([0-9]+)\\s+ip\\s+([0-9\\.]+)", line, re.IGNORECASE)
        if m:
            group = {
                "group_id": m.group(1),
                "interface": current_int,
                "virtual_ip": m.group(2),
                "state": None,
                "priority": None,
                "preempt": None,
            }
            hsrp["groups"].append(group)
        m = re.search(r"standby\\s+([0-9]+)\\s+priority\\s+([0-9]+)", line, re.IGNORECASE)
        if m:
            for g in hsrp["groups"]:
                if g["group_id"] == m.group(1) and g["interface"] == current_int:
                    g["priority"] = m.group(2)
        m = re.search(r"standby\\s+([0-9]+)\\s+preempt", line, re.IGNORECASE)
        if m:
            for g in hsrp["groups"]:
                if g["group_id"] == m.group(1) and g["interface"] == current_int:
                    g["preempt"] = True

    # VRRP (config-based, simplified)
    current_int = None
    for line in running.splitlines():
        line = line.rstrip()
        m = re.match(r"^interface\\s+(\\S+)", line, re.IGNORECASE)
        if m:
            current_int = m.group(1)
            continue
        if not current_int:
            continue

        m = re.search(r"vrrp\\s+([0-9]+)\\s+ip\\s+([0-9\\.]+)", line, re.IGNORECASE)
        if m:
            group = {
                "vrid": m.group(1),
                "interface": current_int,
                "virtual_ip": m.group(2),
                "state": None,
                "priority": None,
                "preempt": None,
            }
            vrrp["groups"].append(group)

    return {
        "etherchannel": etherchannel,
        "hsrp": hsrp,
        "vrrp": vrrp,
    }


def parse_config_to_json(raw_text: str, device_id: str, upload_timestamp: str) -> Dict[str, Any]:
    """
    Aggregate all parser outputs → JSON based on 2.3.2
    Rule-based only (no LLM here).
    """
    sections = split_sections(raw_text)

    result = {
        "device_id": device_id,
        "vendor": "cisco_ios",
        "upload_timestamp": upload_timestamp,
        "device_overview": parse_device_overview(sections, device_id, upload_timestamp),
        "interfaces": parse_interfaces(sections),
        "vlans": parse_vlans(sections),
        "stp": parse_stp(sections),
        "routing": parse_routing(sections),
        "neighbors_topology": parse_neighbors_topology(sections),
        "mac_arp": parse_mac_arp(sections),
        "security_management": parse_security_management(sections),
        "high_availability": parse_high_availability(sections),
    }

    return result


# ---------- LLM HELPERS (validation + gap filling only) ----------

async def call_ollama(payload: dict) -> dict:
    """
    Call Ollama /api/chat with a timeout suitable for local LLM.
    If it times out, we raise and handle it at a higher level.
    """
    # Increased timeout for complex analysis tasks
    # read=600 means 10 minutes for LLM to generate response
    timeout = httpx.Timeout(
        connect=30.0,
        read=600.0,  # 10 minutes for complex analysis
        write=120.0,
        pool=120.0,
    )
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(OLLAMA_URL, json=payload)

        if resp.status_code != 200:
            raise RuntimeError(f"Ollama HTTP {resp.status_code}: {resp.text[:200]}")
        return resp.json()
    except httpx.ReadTimeout:
        raise RuntimeError(
            "LLM request timed out. The model is taking too long to respond. "
            "This may happen with large datasets. Please try again or reduce the amount of data."
        )
    except httpx.ConnectTimeout:
        raise RuntimeError(
            "Connection to Ollama timed out. Please ensure Ollama is running and accessible."
        )
    except httpx.RequestError as e:
        raise RuntimeError(f"Failed to communicate with Ollama: {str(e)}")


def safe_parse_llm_json(content: str) -> dict:
    """
    Try very hard to parse JSON from LLM output:
    1) Direct json.loads
    2) Strip ```json ... ``` fences if present
    3) Extract substring between the first '{' and the last '}' and parse
    If everything fails → return {}.
    """
    raw = content.strip()

    # 1) direct attempt
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 2) strip code fences
    if raw.startswith("```"):
        raw2 = re.sub(r"^```[a-zA-Z0-9]*\\s*", "", raw)
        raw2 = re.sub(r"```$", "", raw2.strip())
        try:
            return json.loads(raw2)
        except json.JSONDecodeError:
            raw = raw2  # use this in step 3

    # 3) substring between first '{' and last '}'
    first = raw.find("{")
    last = raw.rfind("}")
    if first != -1 and last != -1 and last > first:
        snippet = raw[first:last+1]
        try:
            return json.loads(snippet)
        except json.JSONDecodeError:
            pass

    # 4) give up
    return {}


async def validate_and_recover_with_llm(base_json: Dict[str, Any], raw_config: str) -> Dict[str, Any]:
    """
    Use LLM to validate and optionally fill gaps ONLY when values are clearly present
    in the original configuration text.

    To avoid timeouts:
    - Only send a very small subset of the JSON to the LLM.
    - Truncate both JSON and config text.
    - Reduce num_predict.
    """
    # --- Build a SMALL subset for LLM ---
    interfaces_all = base_json.get("interfaces", []) or []
    interfaces_for_llm = interfaces_all[:5]  # limit to first 5 interfaces

    base_json_for_llm = {
        "device_id": base_json.get("device_id"),
        "device_overview": base_json.get("device_overview"),
        "interfaces": interfaces_for_llm,
        "vlans": base_json.get("vlans"),
        "routing": base_json.get("routing"),
        "neighbors_topology": base_json.get("neighbors_topology"),
        "high_availability": base_json.get("high_availability"),
    }

    base_json_snippet = json.dumps(base_json_for_llm, indent=2, ensure_ascii=False)
    if len(base_json_snippet) > 4000:
        base_json_snippet = base_json_snippet[:4000]

    config_snippet = raw_config[:3000]

    system_prompt = """
You are a senior network engineer validating and cross-checking a JSON summary
parsed from Cisco IOS configuration.

There are TWO tasks:

1) VALIDATE the JSON (coverage + consistency).
2) SUGGEST FIXES ONLY for fields that are currently missing or null in JSON,
   but you can clearly and unambiguously read their exact values from the raw
   configuration text.

STRICT RULES:
- DO NOT invent or guess any values.
- If you cannot clearly find a value in the config text, DO NOT include it in fix_suggestions.
- Never try to "improve" or change existing non-null values; we will only use your fixes to fill gaps.
- Keep your output schema EXACTLY as specified below.

Output MUST be a single JSON object with this structure:

{
  "validation": {
    "coverage_score": <integer 0-100>,
    "consistency_score": <integer 0-100>,
    "missing_important_items": [ "text...", ... ],
    "suspicious_values": [
      {
        "json_path": "device_overview.hostname",
        "reason": "text description"
      }
    ],
    "notes": "short overall comment"
  },
  "fix_suggestions": {
    "device_overview": {
      // Only include fields that are NULL or clearly wrong/missing in the input JSON,
      // AND whose exact values you can read directly from the config text.
    },
    "interfaces": [
      {
        "name": "GigabitEthernet0/0",
        "fields": {
          // Only include fields that are missing or null for this interface in JSON
          // and that you can directly read from the config text.
        }
      }
    ]
  }
}

If you are unsure about any value, simply do NOT include it in fix_suggestions.
"""

    user_prompt = f"""
Here is the parsed JSON (subset, rule-based only):

```json
{base_json_snippet}
```

Here is the original configuration text (truncated):

```
{config_snippet}
```

1) Evaluate coverage and consistency as described.
2) If you see important fields that are NULL/missing in JSON but have explicit values in the config,
   include them in fix_suggestions following the schema above.
3) Output ONLY the JSON object described in the system prompt.
"""

    payload = {
        "model": MODEL_NAME,
        "format": "json",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {
            "num_predict": 160,
            "temperature": 0.1,
        },
    }

    try:
        data = await call_ollama(payload)
        content = data.get("message", {}).get("content", "")

        # Debug: save raw LLM output
        device_id = base_json.get("device_id", "unknown")
        debug_path = OUTPUT_DIR / f"{device_id}_llm_raw.txt"
        debug_path.write_text(content, encoding="utf-8")

        result = safe_parse_llm_json(content)
        if not isinstance(result, dict):
            raise ValueError(f"LLM did not return a JSON object.")
        return result
    except Exception as e:
        return {
            "validation": {
                "coverage_score": 0,
                "consistency_score": 0,
                "missing_important_items": [],
                "suspicious_values": [],
                "notes": "LLM validation failed",
            },
            "fix_suggestions": {},
            "error": f"{type(e).__name__}: {e}",
        }


def apply_llm_fixes(base_json: Dict[str, Any], fixes: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge fix_suggestions from LLM into base_json.
    - Only fill fields that are currently None / "" / missing.
    - Never overwrite existing non-empty values.
    """
    if not isinstance(fixes, dict):
        return base_json

    result = json.loads(json.dumps(base_json))  # deep copy

    # device_overview
    dev_fix = fixes.get("device_overview")
    if isinstance(dev_fix, dict):
        dev = result.get("device_overview", {})
        for k, v in dev_fix.items():
            if v is None:
                continue
            if k not in dev or dev.get(k) in (None, "", "unknown"):
                dev[k] = v
        result["device_overview"] = dev

    # interfaces
    if_list_fix = fixes.get("interfaces")
    if isinstance(if_list_fix, list):
        if_map = {}
        for iface in result.get("interfaces", []):
            name = iface.get("name")
            if isinstance(name, str):
                if_map[name] = iface

        for fix in if_list_fix:
            if not isinstance(fix, dict):
                continue
            name = fix.get("name")
            fields = fix.get("fields")
            if not name or not isinstance(fields, dict):
                continue
            target = if_map.get(name)
            if not target:
                continue
            for k, v in fields.items():
                if v is None:
                    continue
                if k not in target or target.get(k) in (None, "", "unknown"):
                    target[k] = v

        result["interfaces"] = list(if_map.values())

    return result


# ---------- MAIN ENDPOINTS ----------

@app.post(
    "/api/upload-config",
    summary=(
        "Upload config/show text (.txt) → JSON (2.3.2, rule-based) "
        "+ LLM validation + limited gap filling"
    ),
)
async def upload_config(file: UploadFile = File(...)):
    """
    Upload a Cisco config/show text file. The API will:
    1) Parse it using rule-based logic to fill the JSON structure defined by 2.3.2.
    2) Call the LLM to validate coverage/consistency and suggest missing fields.
    3) Apply LLM fixes only for clearly present values in the config.
    4) Save the final JSON into outputs/<device_id>.json and return it.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename")

    raw_bytes = await file.read()
    raw_text = raw_bytes.decode("utf-8", errors="ignore")

    device_id = Path(file.filename).stem or "device"
    upload_timestamp = datetime.utcnow().isoformat(timespec="seconds") + "Z"

    # 1) rule-based parsing
    base_json = parse_config_to_json(raw_text, device_id, upload_timestamp)

    # 2) LLM validation + gap filling suggestions
    vr = await validate_and_recover_with_llm(base_json, raw_text)
    validation = vr.get("validation", {})
    fixes = vr.get("fix_suggestions", {})

    # 3) apply fixes
    enhanced_json = apply_llm_fixes(base_json, fixes)

    # 4) attach validation report
    enhanced_json["llm_validation"] = validation

    if "error" in vr:
        enhanced_json["llm_error"] = vr["error"]

    # 5) save JSON file
    out_path = OUTPUT_DIR / f"{device_id}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(enhanced_json, f, indent=2, ensure_ascii=False)

    # 6) save backup config file with timestamp
    backup_filename = f"{device_id}_{upload_timestamp.replace(':', '-').replace('Z', '')}.txt"
    backup_path = BACKUP_DIR / device_id / backup_filename
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    with backup_path.open("w", encoding="utf-8") as f:
        f.write(raw_text)
    
    # Store backup metadata in response
    enhanced_json["backup_file"] = str(backup_path.relative_to(BACKUP_DIR))
    enhanced_json["backup_timestamp"] = upload_timestamp

    return enhanced_json


@app.post("/api/test-llm", summary="Simple LLM connectivity and JSON-format test")
async def test_llm():
    """
    Quick endpoint to verify that the LLM can return valid JSON with the expected schema.
    """
    payload = {
        "model": MODEL_NAME,
        "format": "json",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Return ONLY a JSON object like "
                    '{"validation":{"coverage_score":100,"consistency_score":100,'
                    '"missing_important_items":[],"suspicious_values":[],"notes":"ok"},'
                    '"fix_suggestions":{"device_overview":{"hostname":"R1-CORE"}}}'
                    " without code fences or any extra text."
                ),
            },
            {
                "role": "user",
                "content": "Generate that JSON now.",
            },
        ],
        "stream": False,
        "options": {
            "num_predict": 80,
            "temperature": 0.1,
        },
    }

    data = await call_ollama(payload)
    return data

# ==========================
# Phase 2 – Network-wide analysis & LLM narrative summaries
# ==========================
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

# --------- helpers to load parsed device JSONs and build summary table ---------

def load_all_device_json() -> List[Dict[str, Any]]:
    """
    Load all parsed device JSON files from OUTPUT_DIR.

    Each file is expected to be the Phase 1 JSON for a single device.
    """
    devices: List[Dict[str, Any]] = []
    for path in OUTPUT_DIR.glob("*.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Ensure device_id is present
            data.setdefault("device_id", path.stem)
            devices.append(data)
        except Exception as e:
            print(f"[WARN] Failed to load {path}: {e}")
    return devices


def _safe_float_percent(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        v = value.strip().rstrip("%")
        return float(v)
    except Exception:
        return None


def build_summary_row(device: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build one row of the global summary table (2.3.5.7.x) from a single device JSON.
    """
    overview = device.get("device_overview", {}) or {}
    interfaces = device.get("interfaces", []) or []
    vlans = device.get("vlans", {}) or {}
    stp = device.get("stp", {}) or {}
    routing = device.get("routing", {}) or {}
    ospf = routing.get("ospf", {}) or {}
    bgp = routing.get("bgp", {}) or {}
    ha = device.get("high_availability", {}) or {}

    # Interface counters
    total_if = len(interfaces)
    up_if = sum(
        1
        for i in interfaces
        if (str(i.get("admin_status") or "").lower() == "up"
            or str(i.get("oper_status") or "").lower() == "up")
    )
    down_if = sum(
        1
        for i in interfaces
        if (str(i.get("admin_status") or "").lower() == "down"
            or str(i.get("oper_status") or "").lower() == "down")
    )
    admin_down_if = sum(
        1 for i in interfaces
        if str(i.get("admin_status") or "").lower() == "down"
    )

    access_ports = len(vlans.get("access_ports") or [])
    trunk_ports = len(vlans.get("trunk_ports") or [])

    # crude heuristic: unused = Layer2/Layer3 ports that are admin down and have no VLAN/IP
    unused_ports = 0
    for i in interfaces:
        if not (str(i.get("type") or "")).lower().startswith("layer"):
            continue
        if (
            str(i.get("admin_status") or "").lower() == "down"
            and not i.get("ipv4_address")
            and not i.get("access_vlan")
        ):
            unused_ports += 1

    vlan_count = vlans.get("total_vlan_count")
    if vlan_count is None:
        vlan_count = len(vlans.get("vlan_list") or [])

    # Native VLAN & trunk allowed summary: join unique values
    native_list = sorted(
        {
            str(x.get("native_vlan"))
            for x in (vlans.get("native_vlans") or [])
            if x.get("native_vlan")
        }
    )
    native_vlan = ",".join(native_list) if native_list else None

    trunk_allowed_list = sorted(
        {
            str(x.get("allowed_vlans"))
            for x in (vlans.get("trunk_ports") or [])
            if x.get("allowed_vlans")
        }
    )
    trunk_allowed = ",".join(trunk_allowed_list) if trunk_allowed_list else None

    stp_mode = stp.get("mode")
    # Build a compact STP role summary such as "ROOT:1, DESG:2"
    role_counts: Dict[str, int] = {}
    for p in stp.get("ports") or []:
        role = str(p.get("role") or "").upper()
        if not role:
            continue
        role_counts[role] = role_counts.get(role, 0) + 1
    if role_counts:
        stp_role_summary = ", ".join(
            f"{role}:{count}" for role, count in sorted(role_counts.items())
        )
    else:
        stp_role_summary = None

    ospf_neighbors = len(ospf.get("neighbors") or [])

    bgp_asn = bgp.get("local_as")
    bgp_neighbor_count = len(bgp.get("peers") or [])

    # Routing protocol summary
    routing_protocols: List[str] = []
    if ospf.get("process_id"):
        routing_protocols.append("OSPF")
    if (routing.get("eigrp") or {}).get("as_number"):
        routing_protocols.append("EIGRP")
    if bgp_asn:
        routing_protocols.append("BGP")
    if (routing.get("rip") or {}).get("version"):
        routing_protocols.append("RIP")
    if routing.get("static", {}).get("routes"):
        routing_protocols.append("STATIC")
    routing_proto_summary = ",".join(routing_protocols) if routing_protocols else None

    cpu_percent = _safe_float_percent(overview.get("cpu_utilization"))
    mem_percent = _safe_float_percent(overview.get("memory_utilization"))

    status = "OK"
    # simple risk flags
    if (cpu_percent is not None and cpu_percent > 80) or (
        mem_percent is not None and mem_percent > 80
    ):
        status = "HIGH-UTIL"
    if ospf_neighbors == 0 and "OSPF" in (routing_proto_summary or ""):
        status = "OSPF-ISSUE"

    return {
        "device_id": device.get("device_id") or overview.get("hostname"),
        "device_name": overview.get("hostname") or device.get("device_id"),
        "model": overview.get("model_platform"),
        "serial": overview.get("serial_number"),
        "os_version": overview.get("os_version"),
        "mgmt_ip": overview.get("management_ip"),
        "interfaces_T": total_if,
        "interfaces_U": up_if,
        "interfaces_D": down_if,
        "interfaces_A": admin_down_if,
        "access_ports": access_ports,
        "trunk_ports": trunk_ports,
        "unused_ports": unused_ports,
        "vlan_count": vlan_count,
        "native_vlan": native_vlan,
        "trunk_allowed": trunk_allowed,
        "stp_mode": stp_mode,
        "stp_role_summary": stp_role_summary,
        "ospf_neighbors": ospf_neighbors,
        "bgp_asn": bgp_asn,
        "bgp_neighbor_count": bgp_neighbor_count,
        "routing_protocols": routing_proto_summary,
        "cpu_percent": cpu_percent,
        "mem_percent": mem_percent,
        "status": status,
        "more": device.get("device_id"),
    }


def build_summary_table(devices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [build_summary_row(d) for d in devices]


# --------- generic helper to call LLM for natural-language markdown ---------

def _clean_markdown_response(text: str) -> str:
    """
    Clean up LLM response to ensure it's natural language markdown, not JSON.
    Removes JSON code blocks and extracts only the markdown content.
    """
    if not text:
        return ""
    
    # Remove JSON code blocks (```json ... ```)
    text = re.sub(r'```json\s*\n?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'```\s*\n?', '', text)
    
    # Try to detect if the entire response is JSON and extract meaningful content
    text_stripped = text.strip()
    
    # If it starts with { or [, it might be JSON - try to parse and extract
    if text_stripped.startswith(('{', '[')):
        try:
            # Try to parse as JSON
            parsed = json.loads(text_stripped)
            # If it's a dict with common JSON keys, it's likely raw JSON
            if isinstance(parsed, dict) and any(key in parsed for key in ['markdown', 'content', 'text', 'report', 'summary']):
                # Extract markdown content if it exists
                return parsed.get('markdown') or parsed.get('content') or parsed.get('text') or parsed.get('report') or parsed.get('summary') or text
            # If it's raw JSON, return the original text but warn
            return text
        except json.JSONDecodeError:
            # Not valid JSON, return as is
            pass
    
    return text.strip()


async def _generate_markdown_from_llm(system_prompt: str, user_payload: Dict[str, Any]) -> str:
    """
    Send a request to the LLM and return *only* markdown text in natural language.

    We deliberately do NOT use JSON mode here; the model must answer in free text.
    """
    # Create a clearer user message that emphasizes natural language output
    user_message = f"""Please analyze the following network data and provide your analysis in natural language markdown format.

**IMPORTANT:** 
- Output ONLY markdown text in natural, professional language
- Do NOT output raw JSON
- Do NOT wrap your response in code blocks
- Write as if you are explaining to a human reader

Network Data:
{json.dumps(user_payload, ensure_ascii=False, indent=2)}

Please provide your analysis now:"""
    
    messages = [
        {
            "role": "system",
            "content": system_prompt.strip(),
        },
        {
            "role": "user",
            "content": user_message,
        },
    ]
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False,
    }
    data = await call_ollama(payload)
    text = (data.get("message") or {}).get("content") or ""
    
    # Clean up the response to ensure it's natural language
    cleaned_text = _clean_markdown_response(text)
    return cleaned_text


# --------- 2.3.5.7 – summary table (JSON) ---------

@app.get("/api/network/summary-table", summary="Global Summary Table (2.3.5.7)")
async def api_summary_table() -> Dict[str, Any]:
    """
    Return the global summary table (JSON) for all devices – used to render the table in the UI.

    This endpoint is pure rule-based and does not call the LLM.
    """
    devices = load_all_device_json()
    rows = build_summary_table(devices)
    return {"device_count": len(rows), "summary_rows": rows}


# --------- 2.3.5.1 – global narrative summary (human text) ---------

# ในไฟล์ main.py ส่วนกำหนด PROMPT

GLOBAL_SUMMARY_SYSTEM_PROMPT = """
You are a Senior Network Consultant.
Your task is to analyze the provided network inventory and write a concise, structured **"Executive Network Summary Report"** in Markdown format.

**CRITICAL OUTPUT REQUIREMENTS:**
- You MUST output ONLY natural language markdown text
- Do NOT output JSON format
- Do NOT wrap your response in code blocks (no ```json or ```markdown)
- Do NOT echo back the input JSON data
- Write in a natural, flowing narrative style as if explaining to a human reader
- Use proper markdown formatting (headers, bullets, bold text)
- Keep each section CONCISE - 2-4 sentences per section, focus on key points only

**Objective:**
Provide a high-level overview of the network's current state across 9 key areas. Be concise and focus on the "Big Picture" - do not list every detail.

**Report Structure (Follow these 9 sections exactly):**

### 1. Device Overview (2.3.2.1)
   - Total number of devices and their roles (Core, Distribution, Access)
   - Overall health status (CPU/Memory usage, uptime)

### 2. Interface Information (2.3.2.2)
   - Summary of key interfaces across the network
   - Important connections and IP addressing scheme

### 3. VLAN & Port Mode (2.3.2.3)
   - Primary VLANs used across the network
   - Port mode distribution (Access vs Trunk)

### 4. Spanning Tree Protocol (2.3.2.4)
   - STP mode and configuration
   - Root Bridge information if applicable

### 5. Routing Protocols (2.3.2.5)
   - Active routing protocols (OSPF, BGP, EIGRP, Static)
   - Key routing information

### 6. Neighbor & Topology (2.3.2.6)
   - Network topology overview based on CDP/LLDP
   - Key device interconnections

### 7. MAC & ARP Information (2.3.2.7)
   - Summary of Layer 2 and Layer 3 connectivity
   - Key endpoints if relevant

### 8. Security & Management (2.3.2.8)
   - Security configuration overview (AAA, SSH, etc.)
   - Management protocols (SNMP, NTP, Syslog)

### 9. High Availability (2.3.2.9)
   - HA features in use (EtherChannel, HSRP, VRRP, StackWise)
   - Redundancy status

**Style Guidelines:**
- **Language:** English (Professional)
- **Format:** Clean Markdown with clear section headers
- **Length:** Keep each section to 2-4 sentences maximum
- **NO RAW DATA:** Do NOT output the raw JSON blocks
- **Output Format:** Start directly with your markdown content, no code blocks, no JSON structure
"""

# ---------------------------------------------------------
# 2. แก้ไข API Global Summary (ภาพรวมเครือข่าย)
# ---------------------------------------------------------
# ในไฟล์ main.py

@app.get("/api/network/global-summary-text", summary="Api Global Summary Text")
async def api_global_summary_text() -> Dict[str, Any]:
    """
    2.3.5.1 – Return a human-friendly Markdown description of the whole network.
    """
    try:
        devices = load_all_device_json()
        rows = build_summary_table(devices)
        
        # เตรียมข้อมูลสำหรับให้ AI สรุป (Context)
        payload = {
            "total_devices": len(rows),
            "summary_table": rows,
            "topology_hint": "Hierarchical Design (Core -> Dist -> Access)"
        }

        # เรียกใช้ Prompt สำหรับ Global Summary
        markdown_report = await _generate_markdown_from_llm(GLOBAL_SUMMARY_SYSTEM_PROMPT, payload)
        
        # --- จุดสำคัญ: ส่งกลับเฉพาะ Markdown ที่ AI สร้าง (ไม่ต้องต่อ Raw Data) ---
        return {"markdown": markdown_report}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# --------- 2.3.5.2 – issues / improvements summary (human text) ---------

ISSUES_SYSTEM_PROMPT = """
You are a Senior Network Security & Operations Consultant.
Your task is to analyze the provided network inventory and generate a prioritized **"Network Issues & Recommendations Report"** in Markdown format.

**CRITICAL OUTPUT REQUIREMENTS:**
- You MUST output ONLY natural language markdown text
- Do NOT output JSON format
- Do NOT wrap your response in code blocks (no ```json or ```markdown)
- Do NOT echo back the input JSON data
- Write in a natural, flowing narrative style as if explaining to a human reader
- Use proper markdown formatting (headers, bullets, bold text)
- Focus on ACTIONABLE recommendations - what should be fixed/improved and WHY

**Objective:**
Analyze the entire network and identify issues that need to be fixed or improved. Prioritize by risk level and business impact. Explain what is risky and what should be done first across the entire network.

**Report Structure (Strictly follow this order):**

### 🚨 1. Critical Risks (Immediate Action Required)
   - **Focus:** Vulnerabilities that compromise security or stability of the system (e.g., Telnet enabled, Default passwords, Missing AAA, STP Root conflicts, Loops)
   - **Format:** Bullet points with device names affected and explanation of why it's critical
   - **Example:** "Telnet is enabled on **R1-CORE**. This transmits passwords in cleartext, posing a severe security risk. Immediate migration to SSH is required."

### ⚠️ 2. Operational Blind Spots (High Priority)
   - **Focus:** Issues that hinder troubleshooting and visibility (e.g., Missing NTP, No Syslog, No SNMP, Clock unsynchronized)
   - **Context:** Explain that without these, root cause analysis is impossible during an outage
   - **Aggregation:** If all devices miss NTP, write one summary sentence: "All devices lack NTP synchronization..."

### 🔧 3. Configuration Best Practices (Optimization)
   - **Focus:** Hygiene and clean-up (e.g., Unused ports are Admin Up, Missing interface descriptions, Legacy configurations)
   - **Advice:** Suggest shutting down unused ports to prevent unauthorized access

**Guidelines:**
- **Language:** English (Professional)
- **Tone:** Professional, Advisory, and Direct
- **NO RAW JSON:** Do not dump the input data. Interpret it.
- **Synthesize:** Group similar issues together instead of listing them device by device repeatedly
- **Prioritize:** Rank by risk level and business impact
- **Output Format:** Start directly with your markdown content, no code blocks, no JSON structure
"""
@app.get("/api/network/issues-text", summary="Api Issues Text")
async def api_issues_text() -> Dict[str, Any]:
    """
    Analyze issues and recommendations for the entire network.
    Returns a prioritized list of problems that need to be fixed/improved.
    """
    try:
        devices = load_all_device_json()
        
        # รวบรวมข้อมูลที่จำเป็นสำหรับการวิเคราะห์ issues
        payload = {
            "total_devices": len(devices),
            "devices": [
                {
                    "hostname": (d.get("device_overview") or {}).get("hostname") or d.get("device_id"),
                    "device_id": d.get("device_id"),
                    "role": (d.get("device_overview") or {}).get("role"),
                    "model": (d.get("device_overview") or {}).get("model_platform"),
                    "security_management": d.get("security_management", {}),
                    "high_availability": d.get("high_availability", {}),
                    "spanning_tree": d.get("spanning_tree", {}),
                    "routing_protocols": d.get("routing_protocols", {}),
                    "interfaces": d.get("interfaces", []),
                    "vlans": d.get("vlans", [])
                } 
                for d in devices
            ]
        }

        markdown_report = await _generate_markdown_from_llm(ISSUES_SYSTEM_PROMPT, payload)
        
        return {"markdown": markdown_report}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# --------- 2.3.5.3 – per-device detailed analysis (human text) ---------

class DeviceDetailRequest(BaseModel):
    device_id: str

DEVICE_DETAIL_SYSTEM_PROMPT = """
You are an Expert Network Engineer. 
Your task is to analyze the provided JSON data for a specific device and generate a concise **"Technical Configuration Report"** in Markdown format.

**CRITICAL OUTPUT REQUIREMENTS:**
- You MUST output ONLY natural language markdown text
- Do NOT output JSON format
- Do NOT wrap your response in code blocks (no ```json or ```markdown)
- Do NOT echo back the input JSON data
- Write in a natural, flowing narrative style as if explaining to a human reader
- Use proper markdown formatting (headers, bullets, bold text)
- Keep each section CONCISE - 2-5 sentences per section, focus on key information only

**Requirement:** You MUST structure your response exactly according to these 9 sections (2.3.2.1 - 2.3.2.9). 
Do NOT output raw JSON. Write in a natural, professional English tone.

---

### 1. Device Overview (2.3.2.1)
   - Hostname, role, hardware model, serial number, OS version, and uptime
   - Resource usage (CPU/Memory) if available

### 2. Interface Information (2.3.2.2)
   - Summary of physical and logical interfaces
   - Total count and key interfaces that are 'UP' with their IP addresses

### 3. VLAN & Port Mode (2.3.2.3)
   - Active VLANs (ID and Name)
   - Port modes (Access vs. Trunk) and allowed VLANs on trunks

### 4. Spanning Tree Protocol (2.3.2.4)
   - STP mode (e.g., PVST, MST)
   - **Important:** State if this device is the **Root Bridge** for any VLAN

### 5. Routing Protocols (2.3.2.5)
   - Layer 3 protocols (OSPF, BGP, EIGRP, Static)
   - Router IDs, AS numbers, and neighbor counts

### 6. Neighbor & Topology (2.3.2.6)
   - Immediate topology based on CDP/LLDP neighbors
   - Device connections (who is connected to which port)

### 7. MAC & ARP Tables (2.3.2.7)
   - Layer 2 (MAC) and Layer 3 (ARP) table summaries
   - Total counts and any critical endpoints

### 8. Security & Management (2.3.2.8)
   - AAA, SSH, SNMP, NTP, and Syslog settings
   - Security configuration compliance status

### 9. High Availability (2.3.2.9)
   - Redundancy features: EtherChannel (LACP), HSRP, VRRP, or StackWise
   - Status of HA groups

---
**Tone:** Professional technical report, concise and clear.
**Output Format:** Start directly with your markdown content, no code blocks, no JSON structure.
**Length:** Keep each section concise (2-5 sentences), focus on essential information.
"""

# ---------------------------------------------------------
# 1. แก้ไข API Device Detail (เพื่อให้ได้ 9 หัวข้อตามต้องการ)
# ---------------------------------------------------------
@app.post("/api/network/device-detail", summary="Get device detail analysis")
async def api_device_detail(req: DeviceDetailRequest) -> Dict[str, Any]:
    try:
        devices = load_all_device_json()
        target = None
        for d in devices:
            if d.get("device_id") == req.device_id or (d.get("device_overview") or {}).get("hostname") == req.device_id:
                target = d
                break

        if target is None:
            raise HTTPException(status_code=404, detail=f"Device '{req.device_id}' not found")

        # เตรียม Payload
        payload = {
            "device": target
        }

        # เรียก LLM ด้วย Prompt แบบ 9 หัวข้อ (ไม่ต้องต่อ Raw Data เข้าไปใน Markdown)
        markdown_report = await _generate_markdown_from_llm(DEVICE_DETAIL_SYSTEM_PROMPT, payload)
        
        # ส่งคืนเฉพาะ Markdown ที่ AI สร้าง (สะอาดๆ)
        return {"markdown": markdown_report}
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# --------- 2.3.5.4 – per-device issues analysis (human text) ---------

DEVICE_ISSUES_SYSTEM_PROMPT = """
You are a Senior Network Security & Operations Consultant.
Your task is to analyze a specific device's configuration and identify issues that need to be fixed or improved.

**CRITICAL OUTPUT REQUIREMENTS:**
- You MUST output ONLY natural language markdown text
- Do NOT output JSON format
- Do NOT wrap your response in code blocks (no ```json or ```markdown)
- Do NOT echo back the input JSON data
- Write in a natural, flowing narrative style as if explaining to a human reader
- Use proper markdown formatting (headers, bullets, bold text)
- Focus on ACTIONABLE recommendations - what should be fixed/improved and WHY

**Objective:**
Analyze this specific device and identify issues that need to be fixed or improved. Prioritize by risk level. Explain what is risky and what should be done first for this device.

**Report Structure (Strictly follow this order):**

### 🚨 1. Critical Risks (Immediate Action Required)
   - **Focus:** Vulnerabilities that compromise security or stability of this device (e.g., Telnet enabled, Default passwords, Missing AAA, STP Root conflicts)
   - **Format:** Bullet points with explanation of why it's risky and how to fix it
   - **Example:** "Telnet is enabled on this device. This transmits passwords in cleartext, posing a severe security risk. Immediate migration to SSH is required."

### ⚠️ 2. Operational Blind Spots (High Priority)
   - **Focus:** Issues that hinder troubleshooting and visibility (e.g., Missing NTP, No Syslog, No SNMP, Clock unsynchronized)
   - **Context:** Explain that without these, root cause analysis is impossible during an outage

### 🔧 3. Configuration Best Practices (Optimization)
   - **Focus:** Hygiene and clean-up (e.g., Unused ports are Admin Up, Missing interface descriptions, Legacy configurations)
   - **Advice:** Suggest improvements that should be made

**Guidelines:**
- **Language:** English (Professional)
- **Tone:** Professional, Advisory, and Direct
- **NO RAW JSON:** Do not dump the input data. Interpret it.
- **Prioritize:** Rank by risk level and impact
- **Output Format:** Start directly with your markdown content, no code blocks, no JSON structure
- **Device-Specific:** Focus on issues specific to this device only, do not mention other devices
"""

@app.post("/api/network/device-issues", summary="Get device issues analysis")
async def api_device_issues(req: DeviceDetailRequest) -> Dict[str, Any]:
    """
    Analyze issues and recommendations for a specific device.
    Similar to device-detail but focuses on problems and improvements.
    """
    try:
        devices = load_all_device_json()
        target = None
        for d in devices:
            if d.get("device_id") == req.device_id or (d.get("device_overview") or {}).get("hostname") == req.device_id:
                target = d
                break

        if target is None:
            raise HTTPException(status_code=404, detail=f"Device '{req.device_id}' not found")

        # เตรียม Payload สำหรับการวิเคราะห์ issues
        payload = {
            "device": target
        }

        # เรียก LLM เพื่อวิเคราะห์ issues ของอุปกรณ์นี้
        markdown_report = await _generate_markdown_from_llm(DEVICE_ISSUES_SYSTEM_PROMPT, payload)
        
        return {"markdown": markdown_report}
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# --------- helper for frontend dropdown (device list) ---------

@app.get("/api/network/device-list", summary="List devices for dropdown")
async def api_device_list() -> Dict[str, Any]:
    """
    Simple helper for the UI: list all devices that have JSON data,
    so the frontend can show them in a dropdown.
    """
    devices = load_all_device_json()
    items = []
    for d in devices:
        overview = d.get("device_overview") or {}
        items.append(
            {
                "device_id": d.get("device_id"),
                "hostname": overview.get("hostname"),
                "role": overview.get("role"),
                "mgmt_ip": overview.get("management_ip"),
            }
        )
    return {"devices": items}


# --------- 2.3.5.5 – network topology generation (JSON for React) ---------

TOPOLOGY_SYSTEM_PROMPT = """
You are an Expert Network Topology Engineer.
Your task is to analyze network device data (CDP/LLDP neighbors, interfaces, and routing information) and generate a complete network topology structure in JSON format.

**CRITICAL OUTPUT REQUIREMENTS:**
- You MUST output ONLY valid JSON format
- Do NOT output markdown or natural language text
- Do NOT wrap your response in code blocks
- The output must be a valid JSON object that can be parsed directly

**Output Format:**
You must return a JSON object with this exact structure:

{
  "nodes": [
    {
      "id": "device_id_or_hostname",
      "label": "display_name",
      "type": "router|switch|access_switch|firewall|other",
      "role": "device_role_from_data",
      "ip": "management_ip_or_primary_ip",
      "model": "hardware_model",
      "layer": "L3|L2|L2/L3"
    }
  ],
  "edges": [
    {
      "from": "source_device_id",
      "to": "target_device_id",
      "fromInterface": "local_interface_name",
      "toInterface": "remote_interface_name",
      "protocol": "CDP|LLDP|OSPF|BGP|EIGRP|Static",
      "layer": "L2|L3",
      "ip": "interface_ip_if_available"
    }
  ]
}

**Analysis Guidelines:**
1. **Nodes (Devices):**
   - Create one node for each unique device
   - Use device_id or hostname as the "id"
   - Determine "type" based on device role and capabilities (router, switch, etc.)
   - Extract management IP or primary interface IP for "ip" field
   - Set "layer" based on device function (L3 for routers, L2 for switches, L2/L3 for multilayer)

2. **Edges (Connections):**
   - Create edges from CDP/LLDP neighbor information
   - Create edges from OSPF/BGP/EIGRP neighbor information (Layer 3 connections)
   - Match interfaces between devices based on neighbor data
   - Include interface names from both sides if available
   - Set "protocol" to the discovery/routing protocol used
   - Set "layer" to L2 for CDP/LLDP physical connections, L3 for routing protocol neighbors

3. **Data Sources:**
   - Primary: neighbors_topology.neighbors (CDP/LLDP)
   - Secondary: routing.ospf.neighbors, routing.bgp.peers, routing.eigrp.neighbors
   - Interface information for IP addresses and connection details

4. **Deduplication:**
   - Ensure each device appears only once in nodes array
   - Ensure bidirectional connections are represented correctly (may need to create edges in both directions or use a single edge)

**Important:**
- If a device is mentioned as a neighbor but not in the device list, still create a node for it
- Use the exact device IDs/hostnames from the input data
- Preserve interface names exactly as they appear in the data
- If IP address is available for an interface, include it in the edge
"""

async def _generate_topology_from_llm(system_prompt: str, user_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send a request to the LLM and return parsed JSON topology structure.
    This function uses JSON format mode to ensure valid JSON output.
    """
    user_message = f"""Analyze the following network device data and generate a complete topology structure.

Network Device Data:
{json.dumps(user_payload, ensure_ascii=False, indent=2)}

Please analyze the CDP/LLDP neighbors, interfaces, and routing information to create a complete network topology.
Return ONLY the JSON object with nodes and edges as specified in the system prompt."""

    messages = [
        {
            "role": "system",
            "content": system_prompt.strip(),
        },
        {
            "role": "user",
            "content": user_message,
        },
    ]
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False,
        "format": "json",  # Request JSON format output
    }
    
    try:
        data = await call_ollama(payload)
        content = (data.get("message") or {}).get("content") or ""
        
        # Try to parse JSON from response
        # Remove any markdown code blocks if present
        content_cleaned = content.strip()
        if content_cleaned.startswith("```"):
            # Remove code block markers
            lines = content_cleaned.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].strip() == "```":
                lines = lines[:-1]
            content_cleaned = "\n".join(lines)
        
        # Parse JSON
        try:
            topology = json.loads(content_cleaned)
            # Validate structure
            if not isinstance(topology, dict):
                raise ValueError("Topology must be a JSON object")
            if "nodes" not in topology or "edges" not in topology:
                raise ValueError("Topology must contain 'nodes' and 'edges' arrays")
            if not isinstance(topology["nodes"], list) or not isinstance(topology["edges"], list):
                raise ValueError("'nodes' and 'edges' must be arrays")
            
            return topology
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse JSON from LLM response: {str(e)}\nResponse: {content_cleaned[:500]}")
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Error generating topology: {str(e)}")


@app.get("/api/network/topology", summary="Generate network topology for React visualization")
async def api_network_topology() -> Dict[str, Any]:
    """
    Generate network topology structure from CDP/LLDP neighbors, interfaces, and routing information.
    Returns JSON structure with nodes and edges suitable for React topology visualization.
    
    This endpoint uses LLM to analyze device connections and create a complete topology map.
    """
    try:
        devices = load_all_device_json()
        
        if not devices:
            return {
                "nodes": [],
                "edges": [],
                "message": "No devices found"
            }
        
        # Prepare topology data for LLM analysis
        topology_data = {
            "total_devices": len(devices),
            "devices": []
        }
        
        for device in devices:
            device_info = {
                "device_id": device.get("device_id"),
                "hostname": (device.get("device_overview") or {}).get("hostname"),
                "role": (device.get("device_overview") or {}).get("role"),
                "model": (device.get("device_overview") or {}).get("model_platform"),
                "management_ip": (device.get("device_overview") or {}).get("management_ip"),
                "interfaces": [
                    {
                        "name": intf.get("name"),
                        "ipv4_address": intf.get("ipv4_address"),
                        "admin_status": intf.get("admin_status"),
                        "oper_status": intf.get("oper_status"),
                        "type": intf.get("type")
                    }
                    for intf in device.get("interfaces", [])
                    if intf.get("admin_status") == "up" and intf.get("oper_status") == "up"
                ],
                "neighbors": device.get("neighbors_topology", {}).get("neighbors", []),
                "routing": {
                    "ospf": {
                        "neighbors": device.get("routing", {}).get("ospf", {}).get("neighbors", [])
                    },
                    "bgp": {
                        "peers": device.get("routing", {}).get("bgp", {}).get("peers", [])
                    },
                    "eigrp": {
                        "neighbors": device.get("routing", {}).get("eigrp", {}).get("neighbors", [])
                    }
                }
            }
            topology_data["devices"].append(device_info)
        
        # Generate topology using LLM
        topology = await _generate_topology_from_llm(TOPOLOGY_SYSTEM_PROMPT, topology_data)
        
        return topology
        
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error generating topology: {str(e)}")


# --------- 2.3.5.4 & 2.3.5.5 – config diff and comparison ---------

def list_backup_files(device_id: str) -> List[Dict[str, Any]]:
    """
    List all backup files for a specific device.
    Returns list of backup file info sorted by timestamp (newest first).
    """
    device_backup_dir = BACKUP_DIR / device_id
    if not device_backup_dir.exists():
        return []
    
    backups = []
    for backup_file in device_backup_dir.glob("*.txt"):
        # Extract timestamp from filename: device_id_2025-11-30T15-16-14.txt
        filename = backup_file.stem
        parts = filename.split("_")
        if len(parts) >= 2:
            timestamp_str = "_".join(parts[1:])
            try:
                # Try to parse timestamp from filename
                timestamp = timestamp_str.replace("-", ":").replace("T", "T") + "Z"
            except:
                timestamp = datetime.fromtimestamp(backup_file.stat().st_mtime).isoformat() + "Z"
        else:
            timestamp = datetime.fromtimestamp(backup_file.stat().st_mtime).isoformat() + "Z"
        
        backups.append({
            "filename": backup_file.name,
            "path": str(backup_file.relative_to(BACKUP_DIR)),
            "timestamp": timestamp,
            "size": backup_file.stat().st_size
        })
    
    # Sort by timestamp (newest first)
    backups.sort(key=lambda x: x["timestamp"], reverse=True)
    return backups


@app.get("/api/network/config-backups/{device_id}", summary="List backup files for a device")
async def api_list_backups(device_id: str) -> Dict[str, Any]:
    """
    List all backup configuration files for a specific device.
    Returns list of backups sorted by timestamp (newest first).
    """
    backups = list_backup_files(device_id)
    return {
        "device_id": device_id,
        "backup_count": len(backups),
        "backups": backups
    }


CONFIG_DIFF_SUMMARY_PROMPT = """
You are an Expert Network Configuration Analyst.
Your task is to analyze two network device configuration files and generate a concise summary of the differences.

**CRITICAL OUTPUT REQUIREMENTS:**
- You MUST output ONLY valid JSON format
- Do NOT output markdown or natural language text
- Do NOT wrap your response in code blocks
- The output must be a valid JSON object that can be parsed directly

**Output Format:**
You must return a JSON object with this exact structure:

{
  "device": "device_name",
  "compare": "older_file → newer_file",
  "summary": {
    "added": [
      "Brief description of what was added (e.g., 'Added VLAN 30 on dist-sw2')"
    ],
    "modified": [
      "Brief description of what was modified (e.g., 'Gi1/0/24: access → trunk')"
    ],
    "removed": [
      "Brief description of what was removed (e.g., 'Removed logging host 10.10.1.10')"
    ]
  }
}

**Analysis Guidelines:**
1. **Added:** Identify new configurations, VLANs, interfaces, routes, or settings that appear in the newer file but not in the older one.
2. **Modified:** Identify configurations that changed between versions (e.g., interface mode changes, IP address changes, protocol settings).
3. **Removed:** Identify configurations that were present in the older file but removed in the newer one.

**Important:**
- Be concise but specific (include device/interface names, IPs, VLAN IDs when relevant)
- Focus on significant changes that affect network operation
- Group similar changes when possible
- Use clear, technical language
"""

async def _generate_diff_summary_from_llm(old_config: str, new_config: str, device_id: str, old_file: str, new_file: str) -> Dict[str, Any]:
    """
    Use LLM to analyze config differences and generate a summary.
    """
    user_message = f"""Analyze the differences between these two configuration files for device {device_id}.

Older Configuration File: {old_file}
{old_config[:5000]}

Newer Configuration File: {new_file}
{new_config[:5000]}

Please identify what was added, modified, and removed between these two versions.
Return ONLY the JSON object as specified in the system prompt."""

    messages = [
        {
            "role": "system",
            "content": CONFIG_DIFF_SUMMARY_PROMPT.strip(),
        },
        {
            "role": "user",
            "content": user_message,
        },
    ]
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False,
        "format": "json",
    }
    
    try:
        data = await call_ollama(payload)
        content = (data.get("message") or {}).get("content") or ""
        
        # Clean and parse JSON
        content_cleaned = content.strip()
        if content_cleaned.startswith("```"):
            lines = content_cleaned.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].strip() == "```":
                lines = lines[:-1]
            content_cleaned = "\n".join(lines)
        
        try:
            summary = json.loads(content_cleaned)
            if not isinstance(summary, dict):
                raise ValueError("Summary must be a JSON object")
            return summary
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse JSON from LLM response: {str(e)}\nResponse: {content_cleaned[:500]}")
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Error generating diff summary: {str(e)}")


def generate_line_by_line_diff(old_config: str, new_config: str) -> List[Dict[str, Any]]:
    """
    Generate line-by-line diff between two config files.
    Returns list of diff lines with type, old_content, and new_content for side-by-side comparison.
    """
    old_lines = old_config.splitlines(keepends=False)
    new_lines = new_config.splitlines(keepends=False)
    
    # Use SequenceMatcher for better diff
    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    
    diff_lines = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            # Identical lines
            for line in old_lines[i1:i2]:
                diff_lines.append({
                    "type": "=",
                    "old_content": line,
                    "new_content": line
                })
        elif tag == 'delete':
            # Lines only in old file
            for line in old_lines[i1:i2]:
                diff_lines.append({
                    "type": "-",
                    "old_content": line,
                    "new_content": ""
                })
        elif tag == 'insert':
            # Lines only in new file
            for line in new_lines[j1:j2]:
                diff_lines.append({
                    "type": "+",
                    "old_content": "",
                    "new_content": line
                })
        elif tag == 'replace':
            # Lines changed
            # Show old lines as removed
            for line in old_lines[i1:i2]:
                diff_lines.append({
                    "type": "-",
                    "old_content": line,
                    "new_content": ""
                })
            # Show new lines as added
            for line in new_lines[j1:j2]:
                diff_lines.append({
                    "type": "+",
                    "old_content": "",
                    "new_content": line
                })
    
    return diff_lines


@app.post("/api/network/config-diff-summary/{device_id}", summary="Get config diff summary (2.3.5.4)")
async def api_config_diff_summary(
    device_id: str,
    older_file: UploadFile = File(...),
    newer_file: UploadFile = File(...)
) -> Dict[str, Any]:
    """
    2.3.5.4 - Generate a summary of configuration differences between two config files.
    Accepts any config files (not limited to backups).
    Returns added, modified, and removed items in a structured format.
    """
    try:
        # Read config files from uploads
        older_bytes = await older_file.read()
        old_config = older_bytes.decode("utf-8", errors="ignore")
        older_filename = older_file.filename or "older_config.txt"
        
        newer_bytes = await newer_file.read()
        new_config = newer_bytes.decode("utf-8", errors="ignore")
        newer_filename = newer_file.filename or "newer_config.txt"
        
        # Generate summary using LLM
        summary = await _generate_diff_summary_from_llm(
            old_config, new_config, device_id,
            older_filename, newer_filename
        )
        
        return summary
        
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.post("/api/network/config-diff-line/{device_id}", summary="Get line-by-line config diff (2.3.5.5)")
async def api_config_diff_line(
    device_id: str,
    older_file: UploadFile = File(...),
    newer_file: UploadFile = File(...)
) -> Dict[str, Any]:
    """
    2.3.5.5 - Generate line-by-line comparison between two configuration files.
    Accepts any config files (not limited to backups).
    Returns diff with = (identical), - (removed), + (added) markers.
    """
    try:
        # Read config files from uploads
        older_bytes = await older_file.read()
        old_config = older_bytes.decode("utf-8", errors="ignore")
        older_filename = older_file.filename or "older_config.txt"
        
        newer_bytes = await newer_file.read()
        new_config = newer_bytes.decode("utf-8", errors="ignore")
        newer_filename = newer_file.filename or "newer_config.txt"
        
        # Generate line-by-line diff
        diff_lines = generate_line_by_line_diff(old_config, new_config)
        
        return {
            "device": device_id,
            "older_file": older_filename,
            "newer_file": newer_filename,
            "diff": diff_lines
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

# =========================
# Phase 2: AI Performance Evaluation Addon (EN)
# - Coverage Check
# - Accuracy Check (LLM-as-a-Judge vs raw JSON)
# - Quality Review (LLM-as-a-Judge)
# - Uses outputs from previous LLM endpoints by capturing responses (middleware)
# =========================

import os
import json
import time
import re
import urllib.request
import urllib.error
from typing import Any, Dict, Optional, List, Tuple

from fastapi import Body
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


# -------------------------
# Config
# -------------------------
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL_JUDGE = os.getenv("OLLAMA_MODEL_JUDGE", os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct"))
OLLAMA_TIMEOUT_SEC = float(os.getenv("OLLAMA_TIMEOUT_SEC", "120"))

# Endpoints whose outputs we want to reuse for evaluation
CAPTURE_PATHS = {
    "/api/network/global-summary-text": "global_summary",
    "/api/network/issues-text": "issues",
    "/api/network/device-detail-text": "device_detail",
}

# In-memory cache of latest LLM endpoint responses
# Structure:
# {
#   "global_summary": {"ts":..., "json":{...}, "text":"..."},
#   "issues": {"ts":..., "json":{...}, "text":"..."},
#   "device_detail": {
#        "ts":..., "items": {"R1-CORE": {"json":{...}, "text":"..."}}
#   }
# }
LLM_OUTPUT_CACHE: Dict[str, Any] = {
    "global_summary": None,
    "issues": None,
    "device_detail": {"ts": None, "items": {}},
}


# -------------------------
# Helpers: safe JSON / text extraction
# -------------------------
def _safe_json_loads(s: str) -> Optional[dict]:
    try:
        return json.loads(s)
    except Exception:
        return None


def _extract_text_from_payload(payload: dict) -> str:
    """
    Tries common keys that your endpoints might return.
    """
    if not isinstance(payload, dict):
        return ""
    for k in ["text", "markdown", "result", "summary", "output"]:
        v = payload.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    # fallback: stringify
    try:
        return json.dumps(payload, ensure_ascii=False)
    except Exception:
        return str(payload)


def _now_ts() -> float:
    return time.time()


# -------------------------
# Ollama call (no requests/httpx needed)
# -------------------------
def ollama_chat(model: str, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
    """
    Calls Ollama /api/chat and returns assistant message content.
    Uses urllib from stdlib to avoid dependency issues.
    """
    url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
        },
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT_SEC) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            j = _safe_json_loads(raw) or {}
            msg = j.get("message") or {}
            content = msg.get("content")
            return content.strip() if isinstance(content, str) else raw
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        raise RuntimeError(f"Ollama HTTPError {e.code}: {body}") from e
    except Exception as e:
        raise RuntimeError(f"Ollama request failed: {e}") from e


def _extract_json_block(text: str) -> Optional[dict]:
    """
    Attempts to parse a JSON object from an LLM response:
    - If response is already JSON -> parse
    - Else find first {...} block and parse
    """
    if not isinstance(text, str):
        return None
    text = text.strip()
    direct = _safe_json_loads(text)
    if isinstance(direct, dict):
        return direct

    # Try fenced code block ```json ... ```
    m = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if m:
        j = _safe_json_loads(m.group(1))
        if isinstance(j, dict):
            return j

    # Try first {...}
    m2 = re.search(r"(\{.*\})", text, flags=re.DOTALL)
    if m2:
        j = _safe_json_loads(m2.group(1))
        if isinstance(j, dict):
            return j
    return None


# -------------------------
# Middleware: capture LLM endpoint responses automatically
# -------------------------
class CaptureLLMOutputsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        path = request.url.path
        key = CAPTURE_PATHS.get(path)
        if not key:
            return response

        # Read response body safely and re-create response
        body_bytes = b""
        async for chunk in response.body_iterator:
            body_bytes += chunk

        # Rebuild response so client still receives it
        new_response = Response(
            content=body_bytes,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )

        # Store only JSON responses
        try:
            body_text = body_bytes.decode("utf-8", errors="replace")
            payload = _safe_json_loads(body_text)
            if isinstance(payload, dict):
                extracted_text = _extract_text_from_payload(payload)

                if key in ("global_summary", "issues"):
                    LLM_OUTPUT_CACHE[key] = {
                        "ts": _now_ts(),
                        "json": payload,
                        "text": extracted_text,
                    }
                elif key == "device_detail":
                    # try to identify device_id from request body (POST)
                    device_id = None
                    try:
                        req_body = await request.body()
                        req_json = _safe_json_loads(req_body.decode("utf-8", errors="replace")) if req_body else None
                        if isinstance(req_json, dict):
                            device_id = req_json.get("device_id")
                    except Exception:
                        pass

                    if not device_id:
                        device_id = payload.get("device_id") or payload.get("id") or "unknown"

                    LLM_OUTPUT_CACHE["device_detail"]["ts"] = _now_ts()
                    LLM_OUTPUT_CACHE["device_detail"]["items"][str(device_id)] = {
                        "json": payload,
                        "text": extracted_text,
                    }
        except Exception:
            # never break original endpoint if capture fails
            pass

        return new_response


# Register middleware only once
try:
    app.add_middleware(CaptureLLMOutputsMiddleware)
except Exception:
    # If app doesn't exist or middleware already added, ignore.
    pass


# -------------------------
# Coverage scoring (0-100)
# -------------------------
def compute_coverage_score(all_text: str) -> Tuple[int, List[str]]:
    """
    Simple coverage heuristic:
    Check if key domains are mentioned in combined outputs.
    Returns (score, missing_topics)
    """
    required_topics = [
        ("interfaces", ["interface", "port", "uplink", "downlink", "Gi", "Eth", "Vlan"]),
        ("routing", ["ospf", "bgp", "eigrp", "rip", "static route", "router-id", "neighbor"]),
        ("vlans", ["vlan", "trunk", "access vlan", "native vlan", "allowed vlan"]),
        ("stp", ["stp", "spanning-tree", "pvst", "root", "designated", "blocked"]),
        ("services", ["ntp", "snmp", "syslog", "aaa", "ssh", "radius", "tacacs"]),
        ("security", ["acl", "access-list", "security", "policy", "permit", "deny"]),
        ("health", ["cpu", "memory", "utilization", "uptime"]),
        ("topology", ["neighbor", "cdp", "lldp", "connected to", "link"]),
        ("issues", ["issue", "risk", "warning", "recommend", "should", "fix", "missing"]),
    ]

    text = (all_text or "").lower()
    missing = []
    hit = 0
    for name, keywords in required_topics:
        if any(k.lower() in text for k in keywords):
            hit += 1
        else:
            missing.append(name)

    # score by % topics covered
    score = int(round((hit / max(1, len(required_topics))) * 100))
    return score, missing


# -------------------------
# LLM Judge prompts (Accuracy + Quality)
# -------------------------
def judge_accuracy(raw_json: dict, llm_outputs: dict) -> dict:
    """
    LLM compares raw structured data with generated summaries and returns:
    {
      "accuracy_score": 0-100,
      "missing_items": [...],
      "suspicious_items": [...],
      "judge_notes": "..."
    }
    """
    system = (
        "You are a strict network engineering reviewer. "
        "Your job is to check whether the AI summaries match the provided raw structured network data. "
        "Be conservative: if you are unsure, mark as suspicious instead of claiming it is correct."
    )

    user = {
        "task": "Evaluate factual accuracy of AI outputs against raw network JSON.",
        "return_format": {
            "accuracy_score": "number 0-100 (higher is better)",
            "missing_items": "array of strings describing missing important facts that should have been mentioned",
            "suspicious_items": "array of strings describing contradictions, hallucinations, or unclear/unsupported claims",
            "judge_notes": "short paragraph"
        },
        "raw_network_json": raw_json,
        "ai_outputs": llm_outputs,
        "rules": [
            "Do NOT invent data.",
            "If the AI output claims something not in raw JSON -> suspicious.",
            "If important core facts exist in raw JSON but not mentioned -> missing.",
            "Focus on: device count, device roles, mgmt IPs, VLANs, trunks/native VLANs, STP root roles, OSPF neighbors, services (SNMP/NTP/Syslog/AAA), interface statuses."
        ]
    }

    resp = ollama_chat(
        model=OLLAMA_MODEL_JUDGE,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
        temperature=0.1,
    )

    j = _extract_json_block(resp)
    if not isinstance(j, dict):
        # fallback if model returns text
        return {
            "accuracy_score": 50,
            "missing_items": ["Judge returned non-JSON output; unable to parse detailed accuracy findings."],
            "suspicious_items": [],
            "judge_notes": resp[:500],
        }

    # normalize
    return {
        "accuracy_score": float(j.get("accuracy_score", 50)),
        "missing_items": j.get("missing_items", []) if isinstance(j.get("missing_items"), list) else [],
        "suspicious_items": j.get("suspicious_items", []) if isinstance(j.get("suspicious_items"), list) else [],
        "judge_notes": str(j.get("judge_notes", "")).strip(),
    }


def judge_quality(all_text: str) -> dict:
    """
    LLM rates clarity + logic + usefulness:
    {
      "quality_score": 0-10,
      "judge_notes": "..."
    }
    """
    system = (
        "You are a writing & reasoning reviewer for network operations reports. "
        "Rate clarity, structure, and logical explanations."
    )
    user = {
        "task": "Rate the quality of the combined AI outputs (clarity + logical reasoning + usefulness).",
        "output_requirements": {
            "quality_score": "number 0-10 (can be decimal)",
            "judge_notes": "short paragraph; mention one strong point and one improvement"
        },
        "text_to_review": all_text,
        "rules": [
            "Higher score if it is clear, structured, and actionable.",
            "Lower score if vague, repetitive, or missing reasoning.",
            "Mention if STP root selection or routing rationale is not justified."
        ]
    }

    resp = ollama_chat(
        model=OLLAMA_MODEL_JUDGE,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
        temperature=0.2,
    )

    j = _extract_json_block(resp)
    if not isinstance(j, dict):
        return {"quality_score": 5.0, "judge_notes": resp[:500]}

    return {
        "quality_score": float(j.get("quality_score", 5.0)),
        "judge_notes": str(j.get("judge_notes", "")).strip(),
    }


def compute_overall_score(coverage_score: float, accuracy_score: float, quality_score_0_10: float) -> float:
    """
    Weighted overall score (0-100).
    coverage 30%, accuracy 40%, quality 30% (quality mapped to 0-100)
    """
    quality_100 = max(0.0, min(10.0, quality_score_0_10)) * 10.0
    cov = max(0.0, min(100.0, coverage_score))
    acc = max(0.0, min(100.0, accuracy_score))
    overall = (0.30 * cov) + (0.40 * acc) + (0.30 * quality_100)
    return round(overall, 1)


# -------------------------
# Evaluation Endpoint
# -------------------------
@app.get(
    "/api/network/ai-performance-eval",
    summary="AI Performance Evaluation (Coverage + Accuracy + Quality) using previous LLM endpoint outputs",
)
def ai_performance_evaluation():
    """
    This endpoint evaluates the *latest* outputs captured from:
      - /api/network/global-summary-text
      - /api/network/issues-text
      - /api/network/device-detail-text

    If you haven't called those endpoints yet, call them first to populate the cache.
    """

    global_payload = LLM_OUTPUT_CACHE.get("global_summary")
    issues_payload = LLM_OUTPUT_CACHE.get("issues")
    detail_payload = LLM_OUTPUT_CACHE.get("device_detail") or {}

    if not global_payload or not issues_payload:
        return {
            "error": "Missing captured outputs. Call these first: "
                     "GET /api/network/global-summary-text and GET /api/network/issues-text "
                     "(and optionally POST /api/network/device-detail-text for each device)."
        }

    global_json = global_payload.get("json") or {}
    issues_json = issues_payload.get("json") or {}

    # Raw structured data should come from your global summary endpoint response.
    # If your endpoint uses different keys, adjust here.
    raw_json = {
        "device_count": global_json.get("device_count"),
        "summary_rows": global_json.get("summary_rows"),
        "devices_raw": global_json.get("devices_raw"),
    }

    # Collect LLM-generated outputs (text)
    device_detail_items = (detail_payload.get("items") or {})
    device_details_text_map = {
        dev_id: (item.get("text") if isinstance(item, dict) else "")
        for dev_id, item in device_detail_items.items()
    }

    llm_outputs = {
        "global_summary_text": global_payload.get("text", ""),
        "issues_text": issues_payload.get("text", ""),
        "device_detail_texts": device_details_text_map,  # map by device_id
    }

    # Combine all text for coverage/quality
    combined_text_parts = [
        llm_outputs.get("global_summary_text", ""),
        llm_outputs.get("issues_text", ""),
    ] + [t for t in device_details_text_map.values() if isinstance(t, str)]
    combined_text = "\n\n".join([p for p in combined_text_parts if isinstance(p, str) and p.strip()])

    # Coverage
    coverage_score, missing_topics = compute_coverage_score(combined_text)

    # Accuracy (LLM judge vs raw_json)
    acc_result = judge_accuracy(raw_json=raw_json, llm_outputs=llm_outputs)

    # Quality (LLM judge)
    qual_result = judge_quality(combined_text)

    # Findings structure (missing + suspicious)
    findings = {
        "missing_items": acc_result.get("missing_items", []),
        "suspicious_items": acc_result.get("suspicious_items", []),
    }

    # If coverage missed topics, treat them as missing too (but label)
    for t in missing_topics:
        findings["missing_items"].append(f"Coverage missing topic: {t}")

    # Scores
    accuracy_score = float(acc_result.get("accuracy_score", 50))
    quality_score = float(qual_result.get("quality_score", 5.0))
    overall_score = compute_overall_score(coverage_score, accuracy_score, quality_score)

    # Prefer quality judge notes if available, but also include accuracy notes
    judge_notes_parts = []
    if qual_result.get("judge_notes"):
        judge_notes_parts.append(qual_result["judge_notes"])
    if acc_result.get("judge_notes"):
        judge_notes_parts.append(acc_result["judge_notes"])
    judge_notes = " ".join([p for p in judge_notes_parts if p.strip()]).strip()

    return {
        "coverage_score": int(round(coverage_score)),
        "accuracy_score": int(round(accuracy_score)),
        "quality_score": round(quality_score, 1),
        "overall_score": overall_score,
        "findings": findings,
        "judge_notes": judge_notes,
    }
