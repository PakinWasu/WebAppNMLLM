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


def _mask_to_cidr(mask: str) -> Optional[int]:
    """Convert dotted-decimal mask to CIDR prefix length (e.g. 255.255.255.0 -> 24)."""
    try:
        parts = [int(x) for x in mask.split(".")]
        if len(parts) != 4 or any(p < 0 or p > 255 for p in parts):
            return None
        n = (parts[0] << 24) | (parts[1] << 16) | (parts[2] << 8) | parts[3]
        if n == 0:
            return 0
        return bin(n).count("1")
    except (ValueError, AttributeError):
        return None


def _section_content(content: str) -> Dict[str, str]:
    """
    Section content by command headers so regex is applied to the right block.
    Returns dict with keys: version_text, config_text, cpu_text, memory_text,
    interface_text, etherchannel_text (each may be empty string if not found).
    """
    sections = {
        "version_text": "",
        "config_text": "",
        "cpu_text": "",
        "memory_text": "",
        "interface_text": "",
        "etherchannel_text": "",
    }
    # Match prompt then command; capture until next prompt (Hostname# or Hostname>)
    # Include "show memory statistics" and "show processes cpu sorted" by matching prefix
    prompt_cmd = re.compile(
        r"(?:^|\n)\s*(\S+)#\s*(show\s+version|show\s+running-config|show\s+processes\s+cpu|show\s+memory(?:\s+statistics)?|show\s+interfaces|show\s+etherchannel\s+summary)\s*(.*?)(?=\n\s*\S+#|\n\s*\S+>|$)",
        re.IGNORECASE | re.DOTALL,
    )
    for m in prompt_cmd.finditer(content):
        cmd = (m.group(2) or "").strip().lower()
        body = (m.group(3) or "").strip()
        if "show version" in cmd:
            sections["version_text"] = body
        elif "running-config" in cmd or "running config" in cmd:
            sections["config_text"] = body
        elif "processes cpu" in cmd:
            sections["cpu_text"] = body
        elif "show memory" in cmd or "memory statistics" in cmd or "processes memory" in cmd:
            if not sections["memory_text"]:
                sections["memory_text"] = body
            else:
                sections["memory_text"] = sections["memory_text"] + "\n" + body
        elif "show interfaces" in cmd and "etherchannel" not in cmd:
            sections["interface_text"] = body
        elif "etherchannel summary" in cmd:
            sections["etherchannel_text"] = body
    # config often appears as "show running-config" ... "Building configuration" ... "Current configuration"
    if not sections["config_text"]:
        config_m = re.search(
            r"show\s+running-config\s*(.*?)(?=show\s+|\n\s*[\w-]+#|$)",
            content,
            re.IGNORECASE | re.DOTALL,
        )
        if config_m:
            sections["config_text"] = config_m.group(1).strip()
    return sections


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
        """Return spec structure with device_info, security_audit, high_availability (2.3.2.1–2.3.2.9). On any extract failure, return partial result."""
        def _safe(fn, default=None):
            try:
                return fn()
            except Exception:
                return default
        sections = _section_content(content)
        device_info = _safe(lambda: self.extract_device_info(content, sections), None)
        if not device_info:
            device_info = _safe(lambda: self._device_info_from_overview(self.extract_device_overview(content)), {})
        security_audit = _safe(lambda: self.extract_security_audit(content), None)
        if not security_audit:
            security_audit = _safe(lambda: self._security_audit_from_legacy(self.extract_security(content)), {})
        high_availability = _safe(lambda: self.extract_high_availability(content, sections), None)
        if not high_availability:
            high_availability = _safe(lambda: self._ha_from_legacy(self.extract_ha(content)), {})
        overview = _safe(lambda: self.extract_device_overview(content), {})
        interfaces = _safe(lambda: self.extract_interfaces(content), [])
        vlans = _safe(lambda: self.extract_vlans(content), {})
        vlan_list = vlans.get("vlan_list", []) if isinstance(vlans, dict) else []
        ha_legacy = _safe(lambda: self.extract_ha(content), {})
        sec_legacy = _safe(lambda: self.extract_security(content), {})
        return {
            "device_info": device_info or {},
            "security_audit": security_audit or {},
            "high_availability": high_availability or {},
            "device_overview": overview or {},
            "interfaces": interfaces or [],
            "vlans": vlan_list,
            "routing": _safe(lambda: self.extract_routing(content), {"routes": []}),
            "arp_mac_table": _safe(lambda: self.extract_mac_arp(content), {}),
            "neighbors": _safe(lambda: self.extract_neighbors(content), []),
            "stp": _safe(lambda: self.extract_stp(content), {}),
            "security_mgmt": sec_legacy or {},
            "ha": ha_legacy or {},
        }
    
    def extract_device_info(self, content: str, sections: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """2.3.2.1 - device_info: hostname, vendor, model, os_version, serial_number, uptime, cpu_load, memory_usage. Use sectioned text when provided."""
        info = {
            "hostname": None,
            "vendor": "Cisco",
            "model": None,
            "os_version": None,
            "serial_number": None,
            "uptime": None,
            "cpu_load": None,
            "memory_usage": None,
        }
        if sections is None:
            sections = _section_content(content)
        version_text = sections.get("version_text") or _get_section(content, r"show\s+version") or content
        config_text = sections.get("config_text") or content
        # Hostname
        hostname_match = re.search(r"hostname\s+(\S+)", config_text, re.IGNORECASE)
        if hostname_match:
            info["hostname"] = hostname_match.group(1)
        if not info["hostname"]:
            prompt_match = re.search(r"^(\S+)#", content, re.MULTILINE)
            if prompt_match:
                info["hostname"] = prompt_match.group(1)
        # Model: cisco XXX ... processor or Cisco IOSv (revision...)
        model_m = re.search(r"cisco\s+([^\s,]+)\s+.*?processor", version_text, re.IGNORECASE)
        if model_m:
            info["model"] = model_m.group(1)
        if not info["model"]:
            model_m2 = re.search(r"Cisco\s+(\S+)\s+\(revision", version_text, re.IGNORECASE)
            if model_m2:
                info["model"] = model_m2.group(1)
        if not info["model"]:
            model_m3 = re.search(r"(?:Model\s+[Nn]umber|Processor\s+board\s+ID)[:\s]+(\S+)", version_text, re.IGNORECASE)
            if model_m3:
                info["model"] = model_m3.group(1)
        # OS version
        os_m = re.search(r"Cisco\s+IOS\s+Software.*?Version\s+([^\s,]+)", version_text, re.IGNORECASE)
        if os_m:
            info["os_version"] = os_m.group(1).strip()
        if not info["os_version"]:
            ver_m = re.search(r"version\s+([\d.()]+)", config_text, re.IGNORECASE)
            if ver_m:
                info["os_version"] = ver_m.group(1)
        # Serial: Processor board ID (\w+)
        serial_m = re.search(r"Processor\s+board\s+ID\s+(\w+)", version_text, re.IGNORECASE)
        if serial_m:
            info["serial_number"] = serial_m.group(1)
        if not info["serial_number"]:
            serial_m2 = re.search(r"Serial\s+[Nn]umber[:\s]+(\S+)", version_text, re.IGNORECASE)
            if serial_m2:
                info["serial_number"] = serial_m2.group(1)
        # Uptime: uptime is (.*)
        uptime_m = re.search(r"uptime\s+is\s+(.+?)(?:\n|$)", version_text, re.IGNORECASE)
        if uptime_m:
            info["uptime"] = uptime_m.group(1).strip()
        # CPU and Memory via robust helpers (search section then full content)
        info["cpu_load"] = self._parse_cpu_load(content, sections)
        info["memory_usage"] = self._parse_memory_usage(content, sections)
        return info

    def _device_info_from_overview(self, overview: Dict[str, Any]) -> Dict[str, Any]:
        """Build device_info from legacy device_overview for fallback."""
        if not overview:
            return {}
        return {
            "hostname": overview.get("hostname"),
            "vendor": "Cisco",
            "model": overview.get("model"),
            "os_version": overview.get("os_version"),
            "serial_number": overview.get("serial_number"),
            "uptime": overview.get("uptime"),
            "cpu_load": overview.get("cpu_utilization"),
            "memory_usage": overview.get("memory_utilization"),
        }

    def _parse_cpu_load(self, content: str, sections: Optional[Dict[str, str]] = None) -> Optional[int]:
        """
        Extract CPU utilization (five seconds) from Cisco IOS output.
        Primary: CPU utilization for five seconds:\s+(\d+)%
        Fallback: CPU utilization for five seconds:\s+(\d+)%\/(\d+)% (use first number).
        Searches section first; if empty or no match, searches entire content.
        Returns integer (e.g. 5) or None.
        """
        try:
            search_text = None
            if sections:
                search_text = (sections.get("cpu_text") or "").strip()
            if not search_text:
                search_text = _get_section(content, r"show\s+processes\s+cpu") or ""
            if not search_text:
                search_text = content
            # Primary: CPU utilization for five seconds: 19%
            m = re.search(r"CPU\s+utilization\s+for\s+five\s+seconds\s*:\s*(\d+)\s*%", search_text, re.IGNORECASE)
            if m:
                return int(m.group(1))
            # Fallback: CPU utilization for five seconds: 19%/0%
            m = re.search(r"CPU\s+utilization\s+for\s+five\s+seconds\s*:\s*(\d+)\s*%\s*/\s*(\d+)\s*%", search_text, re.IGNORECASE)
            if m:
                return int(m.group(1))
            return None
        except (ValueError, TypeError, IndexError):
            return None

    def _parse_memory_usage(self, content: str, sections: Optional[Dict[str, str]] = None) -> Optional[int]:
        """
        Extract memory usage percentage from Cisco IOS/IOS-XE output.
        Primary (IOS): Processor Pool Total:\s+(\d+)\s+Used:\s+(\d+) -> (Used/Total)*100
        Fallback (show memory statistics table): Processor\s+\S+\s+(\d+)\s+(\d+)\s+(\d+) -> Used/Total*100
        Fallback (IOS-XE/XR): System Memory\s*:\s*(\d+)K.*?Used\s*:\s*(\d+)K
        Returns integer (e.g. 45) or None.
        """
        try:
            search_text = None
            if sections:
                search_text = (sections.get("memory_text") or "").strip()
            if not search_text:
                search_text = _get_section(content, r"show\s+memory") or _get_section(content, r"show\s+processes\s+memory") or ""
            if not search_text:
                search_text = content
            # Primary (IOS): Processor Pool Total: <bytes> Used: <bytes>
            m = re.search(r"Processor\s+Pool\s+Total\s*:\s*(\d+)\s+Used\s*:\s*(\d+)", search_text, re.IGNORECASE)
            if m:
                total = int(m.group(1))
                used = int(m.group(2))
                if total > 0:
                    return int(round(100.0 * used / total))
            # Fallback: show memory statistics table (Processor line: Total(b) Used(b) Free(b))
            m = re.search(r"Processor\s+\S+\s+(\d+)\s+(\d+)\s+(\d+)", search_text, re.IGNORECASE)
            if m:
                total = int(m.group(1))
                used = int(m.group(2))
                if total > 0:
                    return int(round(100.0 * used / total))
            # Fallback: Used(b) and Free(b) or Total(b) elsewhere in block
            used_m = re.search(r"Used\s*\(\s*b\s*\)\s*:\s*(\d+)|Used\s*\(\s*b\s*\)\s+(\d+)", search_text, re.IGNORECASE)
            total_m = re.search(r"Total\s*\(\s*b\s*\)\s*:\s*(\d+)|Total\s*\(\s*b\s*\)\s+(\d+)", search_text, re.IGNORECASE)
            if used_m and total_m:
                used = int(used_m.group(1) or used_m.group(2))
                total = int(total_m.group(1) or total_m.group(2))
                if total > 0:
                    return int(round(100.0 * used / total))
            # Fallback (IOS-XE/XR): System Memory : XK ... Used : YK
            m = re.search(r"System\s+Memory\s*:\s*(\d+)\s*K.*?Used\s*:\s*(\d+)\s*K", search_text, re.IGNORECASE | re.DOTALL)
            if m:
                total = int(m.group(1))
                used = int(m.group(2))
                if total > 0:
                    return int(round(100.0 * used / total))
            return None
        except (ValueError, TypeError, IndexError, ZeroDivisionError):
            return None

    def extract_device_overview(self, content: str) -> Dict[str, Any]:
        """2.3.2.1 - hostname, role, model, os_version, serial_number, management_ip, uptime, cpu_utilization, memory_utilization."""
        sections = _section_content(content)
        info = self.extract_device_info(content, sections)
        overview = {
            "hostname": info.get("hostname"),
            "role": None,
            "model": info.get("model"),
            "os_version": info.get("os_version"),
            "serial_number": info.get("serial_number"),
            "management_ip": None,
            "uptime": info.get("uptime"),
            "cpu_utilization": info.get("cpu_load"),
            "memory_utilization": info.get("memory_usage"),
        }
        if overview.get("hostname"):
            h = (overview["hostname"] or "").lower()
            if "core" in h:
                overview["role"] = "Core"
            elif "dist" in h or "distribution" in h:
                overview["role"] = "Distribution"
            elif "access" in h or "acc" in h:
                overview["role"] = "Access"
            else:
                overview["role"] = "Switch"
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
        if not overview["management_ip"]:
            first_ip = re.search(r"interface\s+\S+\s*\n.*?ip\s+address\s+(\d+\.\d+\.\d+\.\d+)", content, re.IGNORECASE | re.DOTALL)
            if first_ip:
                overview["management_ip"] = first_ip.group(1)
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
            for line in route_block.split("\n"):
                line_stripped = line.strip()
                if not line_stripped or line_stripped.startswith("Codes:") or line_stripped.startswith("Gateway"):
                    continue
                # Skip "X.0.0.0/8 is subnetted" / "is variably subnetted" (not a route line)
                if " is subnetted" in line_stripped or " is variably subnetted" in line_stripped:
                    continue
                # Skip continuation line: only "[metric] via ..." (multi-path), no protocol+network
                if re.match(r"^\s*\[\d+/\d+\]\s+via\s+", line):
                    continue
                # Protocol code can be O*E2, IA, S*, etc. Require first char to be protocol letter.
                proto_m = re.match(r"^\s*(\S+)\s+(\d+\.\d+\.\d+\.\d+(?:/\d+)?)\s", line_stripped)
                if not proto_m:
                    continue
                protocol_code = proto_m.group(1).replace("*", "").strip()
                if not protocol_code or protocol_code[0] not in "LCOBDSRIMN":
                    continue
                protocol = protocol_code[0].upper()
                network = proto_m.group(2)
                next_hop = None
                interface = None
                if "directly connected" in line_stripped.lower():
                    if_m = re.search(r"directly\s+connected,?\s*(\S+)", line_stripped, re.IGNORECASE)
                    if if_m:
                        interface = if_m.group(1)
                else:
                    via_m = re.search(r"via\s+(\d+\.\d+\.\d+\.\d+)", line_stripped)
                    if via_m:
                        next_hop = via_m.group(1)
                    if_m = re.search(r",\s*(\S+)\s*$", line_stripped)
                    if if_m:
                        interface = if_m.group(1)
                routes.append({"protocol": protocol, "network": network, "next_hop": next_hop or "", "interface": interface or ""})
        # Static from config: ip route <network> <mask> <next_hop> [interface]; only in config block to avoid false matches (e.g. "PPP IP Route" in show processes)
        config_block = _get_section(content, r"show\s+running-config") or content
        for m in re.finditer(
            r"ip\s+route\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+)(?:\s+(\S+))?",
            config_block,
            re.IGNORECASE,
        ):
            network_addr, mask, next_hop, fourth = m.group(1), m.group(2), m.group(3), (m.group(4) or "")
            # Fourth token is interface only if it looks like one (Gi, Fa, Lo, etc.); else "track", "name", etc. are options
            interface = fourth if fourth and re.match(r"^(Gi|Fa|Eth|Te|Se|Lo|Vl|Po|Serial|GigabitEthernet)", fourth, re.IGNORECASE) else ""
            cidr = _mask_to_cidr(mask)
            network = f"{network_addr}/{cidr}" if cidr is not None else network_addr
            if next((r for r in routes if r["network"] == network and r.get("protocol") == "S"), None):
                continue
            routes.append({"protocol": "S", "network": network, "next_hop": next_hop, "interface": interface})
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

    def extract_security_audit(self, content: str) -> Dict[str, Any]:
        """2.3.2.8 - security_audit: ssh, telnet, aaa, snmp, ntp, logging, acls (nested)."""
        cfg = content.lower()
        audit: Dict[str, Any] = {
            "ssh": {"status": "Disabled", "version": None},
            "telnet": {"status": "Disabled"},
            "aaa": {"status": "Disabled", "protocols": []},
            "snmp": {"status": "Disabled", "version": None, "communities": []},
            "ntp": {"servers": [], "status": None},
            "logging": {"syslog_servers": [], "console_logging": False},
            "acls": [],
        }
        # SSH: ip ssh version 2 / transport input ssh
        if "ip ssh version 2" in cfg or "ip ssh version 1.99" in cfg:
            audit["ssh"]["status"] = "Enabled"
            ver_m = re.search(r"ip\s+ssh\s+version\s+([\d.]+)", content, re.IGNORECASE)
            if ver_m:
                audit["ssh"]["version"] = ver_m.group(1)
        elif "transport input ssh" in cfg or "transport input telnet ssh" in cfg:
            audit["ssh"]["status"] = "Enabled"
            if not audit["ssh"]["version"]:
                audit["ssh"]["version"] = "2"
        # Telnet
        if "transport input telnet" in cfg and "transport input ssh" not in cfg:
            audit["telnet"]["status"] = "Enabled"
        elif "transport input all" in cfg or "transport input none" not in cfg:
            if "line vty" in cfg and "transport input ssh" not in cfg:
                audit["telnet"]["status"] = "Enabled"
        # AAA: aaa new-model
        if "aaa new-model" in cfg:
            audit["aaa"]["status"] = "Enabled"
            if re.search(r"tacacs|tacacs\+", cfg):
                audit["aaa"]["protocols"].append("tacacs+")
            if "radius" in cfg:
                audit["aaa"]["protocols"].append("radius")
            if "local" in cfg and ("aaa authentication" in cfg or "login local" in cfg):
                audit["aaa"]["protocols"].append("local")
        # SNMP: snmp-server community
        for m in re.finditer(r"snmp-server\s+community\s+(\S+)", content, re.IGNORECASE):
            audit["snmp"]["communities"].append(m.group(1))
        if audit["snmp"]["communities"] or "snmp-server" in cfg:
            audit["snmp"]["status"] = "Enabled"
            if "snmp-server group" in cfg and "v3" in cfg:
                audit["snmp"]["version"] = "v3"
            else:
                audit["snmp"]["version"] = "v2c"
        # NTP
        for m in re.finditer(r"ntp\s+server\s+(\S+)", content, re.IGNORECASE):
            s = m.group(1)
            if re.match(r"\d+\.\d+\.\d+\.\d+", s) and s not in audit["ntp"]["servers"]:
                audit["ntp"]["servers"].append(s)
        ntp_status = _get_section(content, r"show\s+ntp\s+status")
        if ntp_status and "synchronized" in ntp_status.lower():
            audit["ntp"]["status"] = "Synchronized"
        elif ntp_status:
            audit["ntp"]["status"] = "Unsynchronized"
        # Logging
        for m in re.finditer(r"logging\s+host\s+(\d+\.\d+\.\d+\.\d+|\S+)", content, re.IGNORECASE):
            audit["logging"]["syslog_servers"].append(m.group(1))
        if "logging console" in cfg and "no logging console" not in cfg:
            audit["logging"]["console_logging"] = True
        # ACLs: name, type (Standard/Extended), rule_count
        acl_ids: List[str] = []
        for m in re.finditer(r"ip\s+access-group\s+(\S+)\s+\w+", content, re.IGNORECASE):
            acl_ids.append(m.group(1))
        for m in re.finditer(r"access-list\s+(\d+)\s+(\w+)", content, re.IGNORECASE):
            acl_id = m.group(1)
            if acl_id not in acl_ids:
                acl_ids.append(acl_id)
        for acl_id in acl_ids:
            try:
                num = int(acl_id)
                acl_type = "Standard" if 1 <= num <= 99 else "Extended"
            except ValueError:
                acl_type = "Extended"
            rule_count = len(re.findall(r"access-list\s+" + re.escape(acl_id) + r"\s+\w+", content, re.IGNORECASE))
            if rule_count == 0:
                rule_count = len(re.findall(r"ip\s+access-list\s+(?:extended|standard)\s+" + re.escape(acl_id) + r"\s*\n.*?(?=\n(?:ip\s+access-list|\d|$)", content, re.IGNORECASE | re.DOTALL))
            audit["acls"].append({"name": acl_id, "type": acl_type, "rule_count": rule_count})
        return audit

    def _security_audit_from_legacy(self, sec: Dict[str, Any]) -> Dict[str, Any]:
        """Build security_audit from legacy security_mgmt."""
        if not sec:
            return {}
        return {
            "ssh": {"status": "Enabled" if sec.get("ssh_enabled") else "Disabled", "version": str(sec.get("ssh_version")) if sec.get("ssh_version") else None},
            "telnet": {"status": "Disabled"},
            "aaa": {"status": "Disabled", "protocols": []},
            "snmp": {"status": "Enabled" if sec.get("snmp_enabled") else "Disabled", "version": "v2c", "communities": []},
            "ntp": {"servers": sec.get("ntp_servers") or [], "status": None},
            "logging": {"syslog_servers": [sec["logging_host"]] if sec.get("logging_host") else [], "console_logging": False},
            "acls": [{"name": a, "type": "Extended", "rule_count": 0} for a in (sec.get("acls") or [])],
        }

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

    def extract_high_availability(self, content: str, sections: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """2.3.2.9 - high_availability.ether_channels: interface, protocol, members, status."""
        ec_text = (sections or {}).get("etherchannel_text") or _get_section(content, r"show\s+etherchannel\s+summary") or ""
        ether_channels: List[Dict[str, Any]] = []
        # From show etherchannel summary: "1      Po1(SU)         LACP      Gi1/0(P)    Gi1/1(P)"
        if ec_text:
            for line in ec_text.split("\n"):
                line = line.strip()
                if not line or "Group" in line and "Port-channel" in line:
                    continue
                grp_m = re.search(r"(\d+)\s+(Po\d+|\S+?)(?:\([^)]*\))?\s+(\S+)\s+(.+)", line, re.IGNORECASE)
                if grp_m:
                    grp_id = grp_m.group(1)
                    po_name = grp_m.group(2).strip()
                    if not re.match(r"Po\d+", po_name, re.IGNORECASE):
                        po_name = f"Po{grp_id}"
                    proto = grp_m.group(3).upper()
                    if proto in ("LACP", "PAGP", "ON", "STATIC"):
                        pass
                    elif "lacp" in proto.lower():
                        proto = "LACP"
                    elif "pagp" in proto.lower():
                        proto = "PAGP"
                    else:
                        proto = "Static"
                    rest = grp_m.group(4)
                    members = re.findall(r"(?:Gi|Fa|Te|Eth)\S*(?:\(\w+\))?", rest, re.IGNORECASE)
                    members = [re.sub(r"\([^)]*\)$", "", m).strip() for m in members]
                    status = "Up" if "(P)" in rest or "(SU)" in line else "Down"
                    ether_channels.append({
                        "interface": po_name,
                        "protocol": proto,
                        "members": members,
                        "status": status,
                    })
        # From config: channel-group on physical interfaces -> build Port-channel members
        if not ether_channels:
            pc_by_id: Dict[int, Dict[str, Any]] = {}
            for m in re.finditer(r"interface\s+(\S+)\s*\n(.*?)(?=\ninterface\s+|$)", content, re.IGNORECASE | re.DOTALL):
                iface_name, block = m.group(1), m.group(2)
                ch_m = re.search(r"channel-group\s+(\d+)\s+mode\s+(\S+)", block, re.IGNORECASE)
                if ch_m:
                    grp_id = int(ch_m.group(1))
                    mode = ch_m.group(2).upper()
                    if mode in ("ACTIVE", "PASSIVE"):
                        proto = "LACP"
                    elif mode in ("DESIRABLE", "AUTO"):
                        proto = "PAGP"
                    else:
                        proto = "Static"
                    if grp_id not in pc_by_id:
                        pc_by_id[grp_id] = {"interface": f"Po{grp_id}", "protocol": proto, "members": [], "status": "Up"}
                    pc_by_id[grp_id]["members"].append(iface_name)
            ether_channels = list(pc_by_id.values())
        return {"ether_channels": ether_channels}

    def _ha_from_legacy(self, ha: Dict[str, Any]) -> Dict[str, Any]:
        """Build high_availability from legacy ha."""
        if not ha:
            return {"ether_channels": []}
        ec_list = []
        for e in ha.get("etherchannels") or []:
            ec_list.append({
                "interface": f"Po{e.get('id', 0)}",
                "protocol": (e.get("protocol") or "LACP").upper(),
                "members": e.get("members") or [],
                "status": "Up" if e.get("members") else "Down",
            })
        return {"ether_channels": ec_list}


# Alias for backward compatibility; ConfigParser can use CiscoIOSParser.
CiscoParser = CiscoIOSParser
