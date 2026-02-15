"""Cisco IOS/IOS-XE configuration parser - spec 2.3.2.1 through 2.3.2.9"""

import re
from typing import Dict, List, Any, Optional
from .base import BaseParser


def _get_section(content: str, command_pattern: str) -> Optional[str]:
    """Extract command output from content: from command line until next prompt or next 'show'."""
    pattern = re.compile(
        command_pattern + r"\s*(.*?)(?=show\s+|\n\s*[\w-]+#|$)",
        re.IGNORECASE | re.DOTALL,
    )
    m = pattern.search(content)
    return m.group(1).strip() if m else None


class CiscoIOSParser(BaseParser):
    """
    Parser for Cisco IOS device outputs (concatenated show commands).
    Returns exact JSON spec: device_overview, interfaces, vlans (list), routing.routes,
    arp_mac_table, neighbors, stp, security_mgmt, ha.
    """
    
    def detect_vendor(self, content: str) -> bool:
        """Detect if this is a Cisco configuration or command output."""
        indicators = [
            r"hostname\s+\S+",
            r"version\s+\d+",
            r"!.*Cisco",
            r"switchport\s+mode",
            r"spanning-tree",
            r"router\s+ospf",
            r"router\s+bgp",
            r"show\s+running-config",
            r"show\s+version",
            r"interface\s+(GigabitEthernet|FastEthernet|Ethernet|TenGigabitEthernet)",
            r"Cisco\s+IOS\s+Software",
        ]
        return sum(1 for p in indicators if re.search(p, content, re.IGNORECASE)) >= 2
    
    def parse(self, content: str, filename: str) -> Dict[str, Any]:
        """Return exact spec structure (2.3.2.1-2.3.2.9). On any extract failure, return partial result so device at least has hostname for topology."""
        def _safe(fn, default=None):
            try:
                return fn()
            except Exception:
                return default
        overview = _safe(lambda: self.extract_device_overview(content), {})
        interfaces = _safe(lambda: self.extract_interfaces(content), [])
        vlans = _safe(lambda: self.extract_vlans(content), {})
        vlan_list = vlans.get("vlan_list", []) if isinstance(vlans, dict) else []
        return {
            "device_overview": overview or {},
            "interfaces": interfaces or [],
            "vlans": vlan_list,
            "routing": _safe(lambda: self.extract_routing(content), {"routes": []}),
            "arp_mac_table": _safe(lambda: self.extract_mac_arp(content), {}),
            "neighbors": _safe(lambda: self.extract_neighbors(content), []),
            "stp": _safe(lambda: self.extract_stp(content), {}),
            "security_mgmt": _safe(lambda: self.extract_security(content), {}),
            "ha": _safe(lambda: self.extract_ha(content), {}),
        }
    
    def extract_device_overview(self, content: str) -> Dict[str, Any]:
        """2.3.2.1 - hostname, role, model, os_version, serial_number, management_ip, uptime, cpu_utilization, memory_utilization."""
        overview = {
            "hostname": None,
            "role": None,
            "model": None,
            "os_version": None,
            "serial_number": None,
            "management_ip": None,
            "uptime": None,
            "cpu_utilization": None,
            "memory_utilization": None,
        }
        # Hostname from config or prompt (.*)#
        hostname_match = re.search(r"hostname\s+(\S+)", content, re.IGNORECASE)
        if hostname_match:
            overview["hostname"] = hostname_match.group(1)
        if not overview["hostname"]:
            prompt_match = re.search(r"^(\S+)#", content, re.MULTILINE)
            if prompt_match:
                overview["hostname"] = prompt_match.group(1)
        # Role: infer from hostname
        if overview.get("hostname"):
            h = overview["hostname"].lower()
            if "core" in h:
                    overview["role"] = "Core"
            elif "dist" in h or "distribution" in h:
                    overview["role"] = "Distribution"
            elif "access" in h or "acc" in h:
                    overview["role"] = "Access"
            else:
                    overview["role"] = "Switch"
        # show version section
        version_block = _get_section(content, r"show\s+version")
        if version_block:
            # Cisco IOS Software, Version ...
            os_m = re.search(r"Cisco\s+IOS\s+Software.*?Version\s+([^\s,]+)", version_block, re.IGNORECASE)
            if os_m:
                overview["os_version"] = os_m.group(1).strip()
            if not overview["os_version"]:
                ver_m = re.search(r"version\s+([\d.]+)", content, re.IGNORECASE)
                if ver_m:
                    overview["os_version"] = ver_m.group(1)
            # Model number / Processor board ID
            model_m = re.search(r"(?:Model\s+[Nn]umber|Processor\s+board\s+ID)[:\s]+(\S+)", version_block, re.IGNORECASE)
            if model_m:
                overview["model"] = model_m.group(1)
            if not overview["model"]:
                model_m2 = re.search(r"(?:cisco|Model)\s+(\S+)", version_block, re.IGNORECASE)
                if model_m2:
                    overview["model"] = model_m2.group(1)
            # Serial
            serial_m = re.search(r"(?:Processor\s+board\s+ID|Serial\s+[Nn]umber)[:\s]+(\S+)", version_block, re.IGNORECASE)
            if serial_m:
                overview["serial_number"] = serial_m.group(1)
            # Uptime
            uptime_m = re.search(r"uptime\s+is\s+(.+?)(?:\n|$)", version_block, re.IGNORECASE)
            if uptime_m:
                overview["uptime"] = uptime_m.group(1).strip()
        # Management IP: Loopback0 or Vlan1
        for pattern in [
            r"interface\s+Loopback\s*0\s*\n.*?ip\s+address\s+(\d+\.\d+\.\d+\.\d+)",
            r"interface\s+Vlan\s*1\s*\n.*?ip\s+address\s+(\d+\.\d+\.\d+\.\d+)",
            r"interface\s+Loopback0\s*\n.*?ip\s+address\s+(\d+\.\d+\.\d+\.\d+)",
            r"interface\s+Vlan1\s*\n.*?ip\s+address\s+(\d+\.\d+\.\d+\.\d+)",
        ]:
            m = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if m:
                overview["management_ip"] = m.group(1)
                break
        if not overview["management_ip"]:
            brief = _get_section(content, r"show\s+ip\s+interface\s+brief")
            if brief:
                for line in brief.split("\n")[1:]:
                    parts = line.split()
                    if len(parts) >= 2 and parts[1] != "unassigned" and re.match(r"\d+\.\d+\.\d+\.\d+", parts[1]):
                        overview["management_ip"] = parts[1].split("/")[0]
                        break
        # CPU: show processes cpu - five seconds: X%/Y%
        cpu_block = _get_section(content, r"show\s+processes\s+cpu")
        if cpu_block:
            cpu_m = re.search(r"five\s+seconds[:\s]+(?:\d+%\s*/\s*)?(\d+(?:\.\d+)?)\s*%", cpu_block, re.IGNORECASE)
            if cpu_m:
                try:
                    overview["cpu_utilization"] = float(cpu_m.group(1))
                except ValueError:
                    pass
        if overview["cpu_utilization"] is None:
            cpu_m = re.search(r"CPU\s+utilization.*?(\d+(?:\.\d+)?)\s*%", content, re.IGNORECASE)
            if cpu_m:
                try:
                    overview["cpu_utilization"] = float(cpu_m.group(1))
                except ValueError:
                    pass
        # Memory: show memory - used/total or percentage
        mem_block = _get_section(content, r"show\s+memory")
        if mem_block:
            used_m = re.search(r"(?:Total\s+)?(?:used|Used)\s*[=:]\s*(\d+)", mem_block, re.IGNORECASE)
            total_m = re.search(r"(?:Total\s+)?(?:free|Free)\s*[=:]\s*(\d+)|total\s*[=:]\s*(\d+)", mem_block, re.IGNORECASE)
            if used_m and total_m:
                try:
                    used = int(used_m.group(1))
                    total = int(total_m.group(1) or total_m.group(2) or 0)
                    if total and total > 0:
                        overview["memory_utilization"] = round(100.0 * used / (used + total), 2)
                except (ValueError, TypeError):
                    pass
            if overview["memory_utilization"] is None:
                pct_m = re.search(r"(\d+(?:\.\d+)?)\s*%", mem_block)
                if pct_m:
                    try:
                        overview["memory_utilization"] = float(pct_m.group(1))
                    except ValueError:
                        pass
        if overview["memory_utilization"] is None:
            mem_m = re.search(r"[Mm]emory\s+utilization.*?(\d+(?:\.\d+)?)\s*%", content, re.IGNORECASE)
            if mem_m:
                try:
                    overview["memory_utilization"] = float(mem_m.group(1))
                except ValueError:
                    pass
        return overview
    
    def extract_interfaces(self, content: str) -> List[Dict[str, Any]]:
        """2.3.2.2 - name, description, ip_address, status, protocol, mac_address, speed, duplex, mode (access/trunk/routed)."""
        iface_map: Dict[str, Dict[str, Any]] = {}
        # From config: interface blocks
        for m in re.finditer(r"interface\s+(\S+)\s*\n(.*?)(?=\ninterface\s+|$)", content, re.IGNORECASE | re.DOTALL):
            name, block = m.group(1), m.group(2)
            if name.startswith("Null") or "NULL" in name.upper():
                continue
            if name not in iface_map:
                iface_map[name] = {
                    "name": name,
                "description": None,
                    "ip_address": None,
                    "status": "up",
                    "protocol": "up",
                "mac_address": None,
                "speed": None,
                "duplex": None,
                    "mode": None,
                }
            iface = iface_map[name]
            if "shutdown" in block.lower():
                iface["status"] = "down"
                iface["protocol"] = "down"
            desc_m = re.search(r"description\s+(.+?)(?:\n|$)", block, re.IGNORECASE)
            if desc_m:
                iface["description"] = desc_m.group(1).strip()
            ip_m = re.search(r"ip\s+address\s+(\d+\.\d+\.\d+\.\d+\s+\d+\.\d+\.\d+\.\d+|\d+\.\d+\.\d+\.\d+/\d+)", block, re.IGNORECASE)
            if ip_m:
                iface["ip_address"] = ip_m.group(1).strip()
            if "switchport mode access" in block.lower():
                iface["mode"] = "access"
            elif "switchport mode trunk" in block.lower():
                iface["mode"] = "trunk"
            elif "no switchport" in block.lower() or iface.get("ip_address"):
                iface["mode"] = "routed"
        # show ip interface brief
        brief = _get_section(content, r"show\s+ip\s+interface\s+brief")
        if brief:
            for line in brief.split("\n")[1:]:
                parts = line.split()
                if len(parts) < 4:
                    continue
                name, ip_val, status, protocol = parts[0], parts[1] if len(parts) > 1 else None, parts[3] if len(parts) > 3 else None, parts[4] if len(parts) > 4 else None
                if name not in iface_map:
                    iface_map[name] = {"name": name, "description": None, "ip_address": None, "status": "up", "protocol": "up", "mac_address": None, "speed": None, "duplex": None, "mode": None}
                iface = iface_map[name]
                if ip_val and ip_val != "unassigned":
                    iface["ip_address"] = ip_val if "/" in ip_val or " " in ip_val else ip_val
                if status:
                    iface["status"] = status.lower()
                if protocol:
                    iface["protocol"] = protocol.lower()
        # show interfaces: status, protocol, MAC, speed, duplex
        show_int = _get_section(content, r"show\s+interfaces")
        if show_int:
            current_name = None
            for line in show_int.split("\n"):
                line_strip = line.strip()
                if not line_strip:
                    continue
                if line_strip.startswith("Vlan") or line_strip.startswith("GigabitEthernet") or line_strip.startswith("FastEthernet") or line_strip.startswith("Ethernet") or line_strip.startswith("Loopback") or line_strip.startswith("Port-channel"):
                    parts = line_strip.split()
                    if parts and "is" in line_strip:
                        name = parts[0]
                        current_name = name
                        if name not in iface_map:
                            iface_map[name] = {"name": name, "description": None, "ip_address": None, "status": "up", "protocol": "up", "mac_address": None, "speed": None, "duplex": None, "mode": None}
                        iface = iface_map[name]
                        if "administratively down" in line_strip or "down" in line_strip:
                            iface["status"] = "down"
                    continue
                if current_name and current_name in iface_map:
                    iface = iface_map[current_name]
                    if "line protocol is" in line_strip.lower():
                        if "down" in line_strip.lower():
                            iface["protocol"] = "down"
                    if "address is" in line_strip.lower():
                        mac_m = re.search(r"address\s+is\s+([\da-fA-F.]+)", line_strip, re.IGNORECASE)
                        if mac_m:
                            iface["mac_address"] = mac_m.group(1)
                    if "BW " in line_strip or "Mbit" in line_strip or "Gbit" in line_strip:
                        bw_m = re.search(r"BW\s+(\d+)\s*(Kbit|Mbit|Gbit)", line_strip, re.IGNORECASE)
                        if bw_m:
                            u = bw_m.group(2).upper()
                            if "GBIT" in u:
                                iface["speed"] = f"{bw_m.group(1)}Gbps"
                            elif "MBIT" in u:
                                iface["speed"] = f"{bw_m.group(1)}Mbps"
                            else:
                                iface["speed"] = f"{bw_m.group(1)}Kbps"
                    if "duplex" in line_strip.lower():
                        dup_m = re.search(r"(Full|Half)[-\s]*[Dd]uplex", line_strip)
                        if dup_m:
                            iface["duplex"] = dup_m.group(1).lower()
        # show interfaces switchport for mode if not set
        switchport = _get_section(content, r"show\s+interfaces\s+switchport")
        if switchport:
            for block in re.split(r"\n(?=\w)", switchport):
                name_m = re.match(r"(\S+).*?Switchport\s+Mode[:\s]+(\w+)", block, re.IGNORECASE | re.DOTALL)
                if name_m and name_m.group(1) in iface_map and iface_map[name_m.group(1)].get("mode") is None:
                    mode_val = name_m.group(2).lower()
                    if "access" in mode_val:
                        iface_map[name_m.group(1)]["mode"] = "access"
                    elif "trunk" in mode_val:
                        iface_map[name_m.group(1)]["mode"] = "trunk"
                    else:
                        iface_map[name_m.group(1)]["mode"] = "routed"
        return list(iface_map.values())
    
    def extract_vlans(self, content: str) -> Dict[str, Any]:
        """2.3.2.3 - return dict with vlan_list: [{id (int), name, status}]."""
        vlan_list: List[Dict[str, Any]] = []
        seen: set = set()
        # vlan <id> name <name>
        for m in re.finditer(r"vlan\s+(\d+)\s*\n(.*?)(?=\nvlan\s+|^end\s|$)", content, re.IGNORECASE | re.DOTALL):
            vid = int(m.group(1))
            if vid in seen:
                continue
            seen.add(vid)
            block = m.group(2)
            name_m = re.search(r"name\s+(\S+)", block, re.IGNORECASE)
            vlan_list.append({"id": vid, "name": name_m.group(1) if name_m else str(vid), "status": "active"})
        # show vlan brief
        brief = _get_section(content, r"show\s+vlan\s+brief")
        if brief:
            for line in brief.split("\n")[1:]:
                parts = line.split()
                if len(parts) < 2:
                    continue
                try:
                    vid = int(parts[0])
                except ValueError:
                    continue
                if vid in seen:
                    continue
                seen.add(vid)
                name = parts[1] if len(parts) > 1 else str(vid)
                status = parts[2].lower() if len(parts) > 2 else "active"
                vlan_list.append({"id": vid, "name": name, "status": status})
        return {"vlan_list": vlan_list}
    
    def extract_stp(self, content: str) -> Dict[str, Any]:
        """2.3.2 - mode (PVST/MST), root_bridges (list of VLANs where this device is root)."""
        stp: Dict[str, Any] = {"mode": None, "root_bridges": []}
        mode_m = re.search(r"spanning-tree\s+mode\s+(\S+)", content, re.IGNORECASE)
        if mode_m:
            stp["mode"] = mode_m.group(1).upper()
        show_stp = _get_section(content, r"show\s+spanning-tree")
        if show_stp:
            # "This bridge is the root" or "VLANxxxx ... This bridge is the root"
            for m in re.finditer(r"(?:VLAN\s*)?(\d+).*?[Tt]his\s+bridge\s+is\s+the\s+root", show_stp, re.IGNORECASE | re.DOTALL):
                try:
                    v = int(m.group(1))
                    if v not in stp["root_bridges"]:
                        stp["root_bridges"].append(v)
                except ValueError:
                    pass
            if "this bridge is the root" in show_stp.lower() and not stp["root_bridges"]:
                stp["root_bridges"].append(1)
        return stp
    
    def extract_routing(self, content: str) -> Dict[str, Any]:
        """2.3.2.4 - routes: [{protocol, network, next_hop, interface}] (protocol C, S, O, B, L)."""
        routes: List[Dict[str, Any]] = []
        route_block = _get_section(content, r"show\s+ip\s+route")
        if route_block:
            # Gateway of last resort ...
            for line in route_block.split("\n"):
                line = line.strip()
                if not line or line.startswith("Codes:") or line.startswith("Gateway"):
                    continue
                # C 10.0.0.0/8 is directly connected, GigabitEthernet0/0
                # S* 0.0.0.0/0 [1/0] via 192.168.1.1
                # O 10.1.1.0/24 [110/2] via 10.0.0.2, 00:00:15, GigabitEthernet0/0
                proto_m = re.match(r"^([LCOBDSR\*]+)\s+(\d+\.\d+\.\d+\.\d+(?:/\d+)?)", line)
                if not proto_m:
                    continue
                protocol_code = proto_m.group(1).replace("*", "").strip()
                if not protocol_code:
                    continue
                protocol = protocol_code[0]
                network = proto_m.group(2)
                next_hop = None
                interface = None
                if "directly connected" in line.lower():
                    if_m = re.search(r"directly\s+connected,?\s*(\S+)", line, re.IGNORECASE)
                    if if_m:
                        interface = if_m.group(1)
                else:
                    via_m = re.search(r"via\s+(\d+\.\d+\.\d+\.\d+)", line)
                    if via_m:
                        next_hop = via_m.group(1)
                    if_m = re.search(r",\s*(\S+)\s*$", line)
                    if if_m:
                        interface = if_m.group(1)
                routes.append({"protocol": protocol, "network": network, "next_hop": next_hop or "", "interface": interface or ""})
        # Static from config
        for m in re.finditer(r"ip\s+route\s+(\S+)\s+(\S+)(?:\s+(\S+))?", content, re.IGNORECASE):
            net, nh, iface = m.group(1), m.group(2), m.group(3) or ""
            if next((r for r in routes if r["network"] == net and r.get("protocol") == "S"), None):
                continue
            routes.append({"protocol": "S", "network": net, "next_hop": nh, "interface": iface})
        return {"routes": routes}

    def extract_neighbors(self, content: str) -> List[Dict[str, Any]]:
        """2.3.2.6 - local_interface, neighbor_id, platform, remote_interface, ip_address (CDP/LLDP detail)."""
        neighbors: List[Dict[str, Any]] = []
        # CDP neighbors detail
        detail_block = _get_section(content, r"show\s+cdp\s+neighbors\s+detail")
        if detail_block:
            for section in re.split(r"(?=-------------------------|Device ID:)", detail_block):
                if "Device ID:" not in section:
                    continue
                dev_m = re.search(r"Device\s+ID:\s*(\S+)", section, re.IGNORECASE)
                ip_m = re.search(r"IP\s+address:\s*(\d+\.\d+\.\d+\.\d+)", section, re.IGNORECASE)
                plat_m = re.search(r"Platform:\s*(\S+)", section, re.IGNORECASE)
                port_m = re.search(r"Port\s+ID\s*\(outgoing\s+port\):\s*(\S+)", section, re.IGNORECASE)
                intf_m = re.search(r"Interface:\s*(\S+)", section, re.IGNORECASE)
                if dev_m and intf_m:
                    neighbors.append({
                        "local_interface": intf_m.group(1),
                        "neighbor_id": dev_m.group(1),
                        "platform": plat_m.group(1) if plat_m else None,
                        "remote_interface": port_m.group(1) if port_m else None,
                        "ip_address": ip_m.group(1) if ip_m else None,
                    })
        # CDP brief fallback
        if not neighbors:
            brief = _get_section(content, r"show\s+cdp\s+neighbors")
            if brief:
                for line in brief.split("\n"):
                    if re.match(r"^(Device|Capability|-----)", line, re.IGNORECASE):
                        continue
                    parts = line.split()
                    if len(parts) >= 4 and re.search(r"(Gi|Fa|Eth|Te|Se|Lo|Vl|Po)", parts[1], re.IGNORECASE):
                        neighbors.append({
                            "local_interface": parts[1],
                            "neighbor_id": parts[0],
                            "platform": parts[-2] if len(parts) > 4 else None,
                            "remote_interface": parts[-1] if len(parts) >= 4 else None,
                            "ip_address": None,
                        })
        # LLDP neighbors detail
        lldp_block = _get_section(content, r"show\s+lldp\s+neighbors\s+detail")
        if lldp_block:
            for section in re.split(r"(?=-------------------------|Chassis id:)", lldp_block):
                if "Chassis id:" not in section and "Local Intf:" not in section:
                    continue
                sys_m = re.search(r"System\s+name:\s*(\S+)", section, re.IGNORECASE)
                ip_m = re.search(r"Management\s+address:\s*(\d+\.\d+\.\d+\.\d+)", section, re.IGNORECASE)
                port_m = re.search(r"Port\s+id:\s*(\S+)", section, re.IGNORECASE)
                local_m = re.search(r"Local\s+intf:\s*(\S+)", section, re.IGNORECASE)
                if sys_m and local_m:
                    n = {
                        "local_interface": local_m.group(1),
                        "neighbor_id": sys_m.group(1),
                            "platform": None,
                        "remote_interface": port_m.group(1) if port_m else None,
                        "ip_address": ip_m.group(1) if ip_m else None,
                    }
                    if not any(n["local_interface"] == x["local_interface"] and n["neighbor_id"] == x["neighbor_id"] for x in neighbors):
                        neighbors.append(n)
        return neighbors
    
    def extract_mac_arp(self, content: str) -> Dict[str, Any]:
        """2.3.2.5 - arp_mac_table: { arp_entries: [], mac_entries: [] }."""
        arp_entries: List[Dict[str, Any]] = []
        mac_entries: List[Dict[str, Any]] = []
        # show arp
        arp_block = _get_section(content, r"show\s+arp")
        if arp_block:
            for line in arp_block.split("\n")[1:]:
                parts = line.split()
                if len(parts) >= 4 and re.match(r"\d+\.\d+\.\d+\.\d+", parts[1]):
                    arp_entries.append({
                        "ip_address": parts[1],
                        "mac_address": parts[3] if len(parts) > 3 else None,
                        "interface": parts[-1] if len(parts) > 4 else None,
                    })
        # show mac address-table
        mac_block = _get_section(content, r"show\s+mac(?:\s+address-table|address-table)")
        if not mac_block:
            mac_block = _get_section(content, r"show\s+mac\s+address-table")
        if mac_block:
            for line in mac_block.split("\n")[1:]:
                parts = line.split()
                if len(parts) >= 3:
                    mac_entries.append({
                        "vlan": parts[0],
                        "mac_address": parts[1],
                        "type": parts[2] if len(parts) > 2 else "DYNAMIC",
                        "port": parts[3] if len(parts) > 3 else None,
                    })
        return {"arp_entries": arp_entries, "mac_entries": mac_entries}
    
    def extract_security(self, content: str) -> Dict[str, Any]:
        """2.3.2.8 - security_mgmt: ssh_enabled, ssh_version, users, ntp_servers, snmp_enabled, logging_host, acls."""
        sec: Dict[str, Any] = {
            "ssh_enabled": False,
            "ssh_version": None,
            "users": [],
            "ntp_servers": [],
            "snmp_enabled": False,
            "logging_host": None,
            "acls": [],
        }
        if "transport input ssh" in content.lower() or "transport input telnet ssh" in content.lower():
            sec["ssh_enabled"] = True
        ver_m = re.search(r"ip\s+ssh\s+version\s+(\d+)", content, re.IGNORECASE)
        if ver_m:
            sec["ssh_version"] = ver_m.group(1)
            sec["ssh_enabled"] = True
        for m in re.finditer(r"username\s+(\S+)\s+(?:privilege\s+(\d+))?\s*(?:secret|password)", content, re.IGNORECASE):
            sec["users"].append({"username": m.group(1), "privilege": int(m.group(2)) if m.group(2) else 1})
        for m in re.finditer(r"ntp\s+server\s+(\S+)", content, re.IGNORECASE):
            sec["ntp_servers"].append(m.group(1))
        if "snmp-server" in content.lower():
            sec["snmp_enabled"] = True
        log_m = re.search(r"logging\s+host\s+(\d+\.\d+\.\d+\.\d+|\S+)", content, re.IGNORECASE)
        if log_m:
            sec["logging_host"] = log_m.group(1)
        for m in re.finditer(r"ip\s+access-group\s+(\S+)\s+\w+", content, re.IGNORECASE):
            acl = m.group(1)
            if acl not in sec["acls"]:
                sec["acls"].append(acl)
        for m in re.finditer(r"access-list\s+(\d+)\s+\w+", content, re.IGNORECASE):
            acl = m.group(1)
            if acl not in sec["acls"]:
                sec["acls"].append(acl)
        return sec
    
    def extract_ha(self, content: str) -> Dict[str, Any]:
        """2.3.2.9 - etherchannels [{id, protocol, members}], hsrp_vrrp [{interface, group, virtual_ip, state}]."""
        ha: Dict[str, Any] = {"etherchannels": [], "hsrp_vrrp": []}
        # show etherchannel summary
        ec_block = _get_section(content, r"show\s+etherchannel\s+summary")
        if ec_block:
            for line in ec_block.split("\n"):
                if "Po" in line or "port-channel" in line.lower():
                    # Group  Port-channel  Protocol  Ports
                    grp_m = re.search(r"(\d+)\s+(Po\d+|\S+)\s+(\S+)\s+(.+)", line, re.IGNORECASE)
                    if grp_m:
                        grp_id = int(grp_m.group(1))
                        proto = grp_m.group(3).upper()
                        rest = grp_m.group(4)
                        members = re.findall(r"(?:Gi|Fa|Te|Eth)\S*", rest, re.IGNORECASE)
                        ha["etherchannels"].append({"id": grp_id, "protocol": proto, "members": members})
        # From config: channel-group
        for m in re.finditer(r"interface\s+(Port-channel|port-channel)\s*(\d+)\s*\n(.*?)(?=\ninterface\s+|$)", content, re.IGNORECASE | re.DOTALL):
            grp_id = int(m.group(2))
            if any(e.get("id") == grp_id for e in ha["etherchannels"]):
                continue
            members = []
            proto = "LACP"
            for m2 in re.finditer(r"interface\s+(\S+)\s*\n(.*?)(?=\ninterface\s+|$)", content, re.IGNORECASE | re.DOTALL):
                if f"channel-group {grp_id}" in m2.group(2).lower():
                    members.append(m2.group(1))
                    mode_m = re.search(r"channel-group\s+\d+\s+mode\s+(\S+)", m2.group(2), re.IGNORECASE)
                    if mode_m:
                        proto = mode_m.group(1).upper()
            ha["etherchannels"].append({"id": grp_id, "protocol": proto, "members": members})
        # HSRP / standby
        for m in re.finditer(r"standby\s+(\d+)\s+ip\s+(\d+\.\d+\.\d+\.\d+)", content, re.IGNORECASE):
            ha["hsrp_vrrp"].append({"interface": None, "group": int(m.group(1)), "virtual_ip": m.group(2), "state": None})
        show_standby = _get_section(content, r"show\s+standby\s+brief")
        if show_standby:
            for line in show_standby.split("\n")[1:]:
                parts = line.split()
                if len(parts) >= 4:
                    ha["hsrp_vrrp"].append({
                        "interface": parts[0],
                        "group": int(parts[1]) if parts[1].isdigit() else None,
                        "virtual_ip": parts[2] if re.match(r"\d+\.\d+\.\d+\.\d+", parts[2]) else None,
                        "state": parts[3] if len(parts) > 3 else None,
                    })
        # VRRP
        for m in re.finditer(r"vrrp\s+(\d+)\s+ip\s+(\d+\.\d+\.\d+\.\d+)", content, re.IGNORECASE):
            ha["hsrp_vrrp"].append({"interface": None, "group": int(m.group(1)), "virtual_ip": m.group(2), "state": "Active"})
        return ha


# Alias for backward compatibility; ConfigParser can use CiscoIOSParser.
CiscoParser = CiscoIOSParser
