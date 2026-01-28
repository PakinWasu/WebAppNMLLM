
from fastapi import FastAPI, UploadFile, File, HTTPException
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import json
import re

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
    for line in ip_route.splitlines():
        line = line.strip()
        if not line or line.startswith("Gateway of last resort"):
            continue
        if line.startswith("S"):
            m = re.search(
                r"(S\\*?|S)\\s+([0-9\\.\\/]+)\\s+\\[([0-9]+)/([0-9]+)\\]\\s+via\\s+([0-9\\.]+),\\s*(\\S+)",
                line,
            )
            if m:
                prefix = m.group(2)
                ad = int(m.group(3))
                next_hop = m.group(5)
                iface = m.group(6)
                is_default = prefix.startswith("0.0.0.0/0")
                static_routes.append({
                    "destination": prefix,
                    "mask": None,
                    "next_hop": next_hop,
                    "exit_interface": iface,
                    "admin_distance": ad,
                    "is_default_route": is_default,
                })

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
    timeout = httpx.Timeout(
        connect=30.0,
        read=180.0,
        write=60.0,
        pool=60.0,
    )
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(OLLAMA_URL, json=payload)

    if resp.status_code != 200:
        raise RuntimeError(f"Ollama HTTP {resp.status_code}: {resp.text[:200]}")
    return resp.json()


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
