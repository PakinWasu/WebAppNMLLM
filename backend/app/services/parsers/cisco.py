"""Cisco IOS/IOS-XE configuration parser - spec 2.3.2.1 through 2.3.2.9"""

import re
from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel
from .base import BaseParser

class RIPTimer(BaseModel):
    """2.3.2.5.5.6 - RIP Timers"""
    update: Optional[int] = None
    invalid: Optional[int] = None
    hold_down: Optional[int] = None
    flush: Optional[int] = None

class RIPRoute(BaseModel):
    """2.3.2.5.5.3 - Learned RIP Route"""
    network: str
    admin_distance: Optional[int] = None
    hop_count: Optional[int] = None
    next_hop: Optional[str] = None
    uptime: Optional[str] = None

class RIPV2Info(BaseModel):
    """2.3.2.5.5 - Comprehensive RIP Information"""
    version: Optional[int] = None
    advertised_networks: List[str] = []
    learned_routes: List[RIPRoute] = []
    participating_interfaces: List[Dict[str, Any]] = []
    auto_summary: Optional[bool] = None
    passive_interfaces: List[str] = []
    timers: RIPTimer = RIPTimer()
    admin_distance: Optional[int] = None


def _get_section(content: str, command_pattern: str) -> Optional[str]:
    """Extract command output from content: from command line until next prompt or next 'show'."""
    pattern = re.compile(
        command_pattern + r"\s*(.*?)(?=show\s+|\n\s*[\w-]+#|$)",
        re.IGNORECASE | re.DOTALL,
    )
    m = pattern.search(content)
    return m.group(1).strip() if m else None


def _search_global(content: str, patterns: List[tuple]) -> Optional[str]:
    """Multi-Source Inference: search anywhere in content. patterns = [(regex, group_index), ...]. Returns first match."""
    for pat, group in patterns:
        try:
            m = re.search(pat, content, re.IGNORECASE | re.DOTALL)
            if m:
                out = (m.group(group) or "").strip()
                if out:
                    return out
        except (IndexError, AttributeError):
            continue
    return None


def _search_global_int(content: str, patterns: List[tuple]) -> Optional[int]:
    """Like _search_global but returns int or None."""
    val = _search_global(content, patterns)
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _canonical_interface_name(name: str) -> str:
    """Normalize interface name so Gi0/0 and GigabitEthernet0/0 map to the same key (no duplicates)."""
    if not name or not name[0].isalpha():
        return name
    s = name.strip()
    # Expand common Cisco abbreviations to full form
    lower = s.lower()
    if lower.startswith("gi") and (len(s) == 2 or s[2:3].isdigit()):
        return "GigabitEthernet" + s[2:]
    if lower.startswith("gigabitethernet"):
        return s
    if lower.startswith("fa") and (len(s) == 2 or s[2:3].isdigit()):
        return "FastEthernet" + s[2:]
    if lower.startswith("fastethernet"):
        return s
    if lower.startswith("te") and (len(s) == 2 or s[2:3].isdigit()):
        return "TenGigabitEthernet" + s[2:]
    if lower.startswith("tengigabitethernet"):
        return s
    if lower.startswith("po") and (len(s) == 2 or s[2:3].isdigit()):
        return "Port-channel" + s[2:]
    if lower.startswith("port-channel"):
        return s
    if lower.startswith("vl") and (len(s) == 2 or s[2:3].isdigit()):
        return "Vlan" + s[2:]
    if lower.startswith("vlan"):
        return s
    if lower.startswith("lo") and (len(s) == 2 or s[2:3].isdigit()):
        return "Loopback" + s[2:]
    if lower.startswith("loopback"):
        return s
    if lower.startswith("et") and (len(s) == 2 or s[2:3].isdigit()):
        return "Ethernet" + s[2:]
    if lower.startswith("ethernet"):
        return s
    if lower.startswith("se") and (len(s) == 2 or s[2:3].isdigit()):
        return "Serial" + s[2:]
    if lower.startswith("serial"):
        return s
    if lower.startswith("tu") and (len(s) == 2 or s[2:3].isdigit()):
        return "Tunnel" + s[2:]
    if lower.startswith("tunnel"):
        return s
    return s


def _determine_interface_type(name: str) -> Optional[str]:
    """
    Determine interface type based on interface name.
    
    Returns:
        - "Physical" for GigabitEthernet, FastEthernet, Ethernet, TenGigabitEthernet (and abbreviations)
        - "Port-Channel" for Port-channel (or Po)
        - "SVI" for Vlan interfaces
        - "Loopback" for Loopback interfaces (or Lo)
        - "Tunnel" for Tunnel interfaces (or Tu)
        - None for unknown types
    """
    if not name:
        return None
    
    normalized = _canonical_interface_name(name)
    lower = normalized.lower()
    
    if "null" in lower:
        return "Null"
    if "meth" in lower:
        return "ManagementEthernet"
    
    # Physical interfaces
    if (lower.startswith("gigabitethernet") or 
        lower.startswith("fastethernet") or 
        lower.startswith("ethernet") or 
        lower.startswith("tengigabitethernet")):
        return "Physical"
    
    # Port-Channel
    if lower.startswith("port-channel"):
        return "Port-Channel"
    
    # SVI (Switched Virtual Interface)
    if lower.startswith("vlan"):
        return "SVI"
    
    # Loopback
    if lower.startswith("loopback"):
        return "Loopback"
    
    # Tunnel
    if lower.startswith("tunnel"):
        return "Tunnel"
    
    return None


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


def _ip_to_int(ip_str: str) -> Optional[int]:
    """Convert dotted-decimal IP to 32-bit int."""
    try:
        parts = [int(x) for x in ip_str.strip().split(".")]
        if len(parts) != 4 or any(p < 0 or p > 255 for p in parts):
            return None
        return (parts[0] << 24) | (parts[1] << 16) | (parts[2] << 8) | parts[3]
    except (ValueError, AttributeError):
        return None


def _ip_in_ospf_network(ip_str: str, network_str: str, wildcard_str: str) -> bool:
    """Return True if IP matches OSPF network/wildcard (network A B area Z)."""
    ip_i = _ip_to_int(ip_str)
    net_i = _ip_to_int(network_str)
    wc_i = _ip_to_int(wildcard_str)
    if ip_i is None or net_i is None or wc_i is None:
        return False
    return (ip_i & ~wc_i) == (net_i & ~wc_i)


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
        """Return spec structure with device_info, security_audit, high_availability (2.3.2.1–2.3.2.9). Multi-Source Inference: pass full original_content to all helpers."""
        self.original_content = content
        full = self.original_content

        def _safe(fn, default=None):
            try:
                return fn()
            except Exception:
                return default
        # Do not rely on sectioning for global stats (CPU/Memory/Model); use full content
        device_info = _safe(lambda: self.extract_device_info(full, None), None)
        if not device_info:
            device_info = _safe(lambda: self._device_info_from_overview(self.extract_device_overview(full)), {})
        security_audit = _safe(lambda: self.extract_security_audit(full), None)
        if not security_audit:
            security_audit = _safe(lambda: self._security_audit_from_legacy(self.extract_security(full)), {})
        high_availability = _safe(lambda: self.extract_high_availability(full, None), None)
        if not high_availability:
            high_availability = _safe(lambda: self._ha_from_legacy(self.extract_ha(full)), {})
        overview = _safe(lambda: self.extract_device_overview(full), {})
        interfaces = _safe(lambda: self.extract_interfaces(full), [])
        # Management IP: smart selection via _get_management_ip(interfaces)
        mgmt_ip = _safe(lambda: self._get_management_ip(interfaces), None)
        if device_info is not None:
            device_info["management_ip"] = device_info.get("management_ip") or mgmt_ip
        if overview is not None:
            overview["management_ip"] = overview.get("management_ip") or mgmt_ip
        vlans = _safe(lambda: self.extract_vlans(full), {})
        if not isinstance(vlans, dict):
            vlans = {"vlan_list": [], "details": [], "access_ports": [], "trunk_ports": [], "total_count": 0}
        ha_legacy = _safe(lambda: self.extract_ha(full), {})
        sec_legacy = _safe(lambda: self.extract_security(full), {})
        return {
            "device_info": device_info or {},
            "security_audit": security_audit or {},
            "high_availability": high_availability or {},
            "device_overview": overview or {},
            "interfaces": interfaces or [],
            "vlans": vlans,
            "routing": _safe(lambda: self.extract_routing(full), {"routes": []}),
            "arp_mac_table": _safe(lambda: self.extract_mac_arp(full), {}),
            "neighbors": _safe(lambda: self.extract_neighbors(full), []),
            "stp": _safe(lambda: self.extract_stp(full), {}),
            "security_mgmt": sec_legacy or {},
            "ha": ha_legacy or {},
        }
    
    def extract_device_info(self, content: str, sections: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """2.3.2.1 - device_info. Multi-Source Inference: search full content first for model/serial/cpu/memory/uptime."""
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
        config_text = (sections or {}).get("config_text") or _get_section(content, r"show\s+running-config") or content
        if not config_text:
            config_text = content
        # Hostname: config or prompt
        try:
            hostname_match = re.search(r"hostname\s+(\S+)", config_text, re.IGNORECASE)
            if hostname_match:
                info["hostname"] = hostname_match.group(1)
            if not info["hostname"]:
                prompt_match = re.search(r"^(\S+)#", content, re.MULTILINE)
                if prompt_match:
                    info["hostname"] = prompt_match.group(1)
        except Exception:
            pass
        # Model: IOSv/vios -> "Cisco IOSv (Virtual)"; else Cisco IOS Software string or Model number; never null
        try:
            if "iosv" in content.lower() or re.search(r"\bvios\b", content, re.IGNORECASE):
                info["model"] = "Cisco IOSv (Virtual)"
            if not info["model"]:
                m = re.search(r"Cisco\s+IOS\s+Software,\s*(\S+)\s+Software", content, re.IGNORECASE)
                if m:
                    info["model"] = m.group(1)
            if not info["model"]:
                info["model"] = _search_global(content, [
                    (r"Model\s+number\s*:\s*(\S+)", 1),
                    (r"cisco\s+(\S+)\s+.*?processor", 1),
                    (r"Cisco\s+(\S+)\s+\(revision", 1),
                ])
            if not info["model"]:
                info["model"] = "Cisco IOS (Unknown)"
        except Exception:
            info["model"] = "Cisco IOS (Unknown)"
        # OS version: config or version block
        try:
            info["os_version"] = _search_global(content, [
                (r"Cisco\s+IOS\s+Software.*?Version\s+([^\s,]+)", 1),
                (r"version\s+([\d.()]+)", 1),
            ])
        except Exception:
            pass
        # Serial: Processor board ID; never null - use Virtual-Device-ID or N/A for virtual/simulator
        try:
            info["serial_number"] = _search_global(content, [
                (r"Processor\s+board\s+ID\s+(\w+)", 1),
                (r"System\s+Serial\s+Number\s*:\s*(\w+)", 1),
                (r"Serial\s+[Nn]umber[:\s]+(\S+)", 1),
            ])
            if not info["serial_number"]:
                info["serial_number"] = "Virtual-Device-ID"
        except Exception:
            info["serial_number"] = "Virtual-Device-ID"
        # Uptime: global search
        try:
            info["uptime"] = _search_global(content, [
                (r"uptime\s+is\s+(.+?)(?:\n|$)", 1),
            ])
        except Exception:
            pass
        # CPU: global search only (anywhere in file - no sectioning)
        try:
            cpu_val = _search_global_int(content, [
                (r"CPU\s+utilization\s+for\s+five\s+seconds\s*:\s*(\d+)\s*%", 1),
                (r"CPU\s+utilization\s+for\s+five\s+seconds\s*:\s*(\d+)\s*%/\s*\d+\s*%", 1),
            ])
            if cpu_val is not None:
                info["cpu_load"] = cpu_val
            else:
                info["cpu_load"] = self._parse_cpu_load(content, None)
        except Exception:
            info["cpu_load"] = self._parse_cpu_load(content, None)
        # Memory: global search (Processor Pool Total/Used or System Memory ... Used)
        try:
            mem_pct = None
            m = re.search(r"Processor\s+Pool\s+Total\s*:\s*(\d+)\s+Used\s*:\s*(\d+)", content, re.IGNORECASE)
            if m:
                total, used = int(m.group(1)), int(m.group(2))
                if total > 0:
                    mem_pct = int(round(100.0 * used / total))
            if mem_pct is None:
                m = re.search(r"System\s+Memory\s*:\s*(\d+)K\s+total.*?(\d+)K\s+used", content, re.IGNORECASE | re.DOTALL)
                if m:
                    total, used = int(m.group(1)), int(m.group(2))
                    if total > 0:
                        mem_pct = int(round(100.0 * used / total))
            if mem_pct is not None:
                info["memory_usage"] = mem_pct
            else:
                info["memory_usage"] = self._parse_memory_usage(content, None)
        except Exception:
            info["memory_usage"] = self._parse_memory_usage(content, None)
        return info

    def _get_management_ip(self, interfaces_list: List[Dict[str, Any]]) -> Optional[str]:
        """Smart selection: Priority 1 Loopback, 2 Vlan/Vlanif, 3 Management/MEth, 4 first physical with IP. Ignore 127.x."""
        return self._determine_management_ip(interfaces_list)

    def _determine_management_ip(self, interfaces_list: List[Dict[str, Any]]) -> Optional[str]:
        """First-available management IP: Loopback > Vlan/Vlanif > Management/MEth > first physical with IP. Ignore 127.0.0.x. Guaranteed reachability IP."""
        def _normalize_ip(ip: Any) -> Optional[str]:
            if not ip or not isinstance(ip, str):
                return None
            # Take first token (IP only; strip mask like "192.168.1.1 255.255.255.0" or "192.168.1.1/24")
            addr = (ip.split()[0] if ip.split() else ip).split("/")[0].strip()
            if not re.match(r"\d+\.\d+\.\d+\.\d+", addr) or addr.startswith("127."):
                return None
            return addr

        loopback, vlan, mgmt, physical = [], [], [], []
        for i in interfaces_list or []:
            ip = i.get("ip_address") or i.get("ipv4_address")
            addr = _normalize_ip(ip)
            if not addr:
                continue
            name = (i.get("name") or "").lower()
            if "loopback" in name or "lo" == name[:2]:
                loopback.append(addr)
            elif "vlan" in name or "vlanif" in name:
                vlan.append(addr)
            elif "management" in name or "meth" in name:
                mgmt.append(addr)
            elif any(name.startswith(p) for p in ("gigabit", "gi", "fast", "fa", "ethernet", "eth", "ten", "te")):
                physical.append(addr)
        for cand in (loopback, vlan, mgmt, physical):
            if cand:
                return cand[0]
        return None

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
        Extract CPU utilization (five seconds). Global regex search - do not rely on section headers.
        Returns integer (e.g. 5) or None.
        """
        try:
            # Prefer full content for Multi-Source Inference (messy logs)
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
        Extract memory usage percentage. Global regex search - do not rely on section headers.
        Returns integer (e.g. 45) or None.
        """
        try:
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
        """2.3.2.1 - hostname, role, model, os_version, serial_number, management_ip, uptime, cpu_utilization, memory_utilization. Uses full content."""
        info = self.extract_device_info(content, None)
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
        # Management IP: best-effort from config; parse() will overwrite with _determine_management_ip(interfaces) for first-available
        for pattern in [
            r"interface\s+Loopback\s*0\s*\n.*?ip\s+address\s+(\d+\.\d+\.\d+\.\d+)",
            r"interface\s+Vlan\s*1\s*\n.*?ip\s+address\s+(\d+\.\d+\.\d+\.\d+)",
            r"interface\s+Loopback0\s*\n.*?ip\s+address\s+(\d+\.\d+\.\d+\.\d+)",
            r"interface\s+Vlan\s*\d+\s*\n.*?ip\s+address\s+(\d+\.\d+\.\d+\.\d+)",
        ]:
            m = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if m and not (m.group(1) or "").startswith("127."):
                overview["management_ip"] = m.group(1)
                break
        if not overview["management_ip"]:
            first_ip = re.search(r"interface\s+\S+\s*\n.*?ip\s+address\s+(\d+\.\d+\.\d+\.\d+)", content, re.IGNORECASE | re.DOTALL)
            if first_ip and not (first_ip.group(1) or "").startswith("127."):
                overview["management_ip"] = first_ip.group(1)
        return overview
    
    def _normalize_mac_cisco(self, mac: str) -> str:
        """Normalize Cisco MAC (e.g. 5000.0003.0000) to XX:XX:XX:XX:XX:XX."""
        if not mac:
            return ""
        try:
            # Cisco format: aaaa.bbbb.cccc or aa.bb.cc.dd.ee.ff (dots)
            s = re.sub(r"[\s.-]", "", mac).lower()
            if len(s) == 12 and s.isalnum():
                return ":".join(s[i : i + 2] for i in range(0, 12, 2))
            parts = mac.replace(".", ":").split(":")
            if len(parts) >= 6:
                return ":".join(p.zfill(2) if len(p) == 1 else p for p in parts[:6])
        except Exception:
            pass
        return mac

    def _parse_one_show_interface_block(self, block: str) -> Optional[Dict[str, Any]]:
        """Extract fields from one 'show interfaces' block. Returns dict of updates (name, description, mac_address, ip_address, mtu, speed, duplex, etc.)."""
        if not block or not block.strip():
            return None
        try:
            name_m = re.match(r"^(\S+)\s+is\s+(up|down|administratively\s+down).*?line\s+protocol\s+is\s+(up|down)", block, re.IGNORECASE | re.DOTALL)
            if not name_m:
                return None
            name = name_m.group(1)
            status = "down" if "down" in (name_m.group(2) or "").lower() else "up"
            protocol = (name_m.group(3) or "up").lower()
            out: Dict[str, Any] = {"name": name, "status": status, "protocol": protocol}
            desc_m = re.search(r"^\s+Description:\s*(.+?)(?:\n|$)", block, re.IGNORECASE | re.MULTILINE)
            if desc_m:
                out["description"] = desc_m.group(1).strip()
            # MAC: address is XXXX.XXXX.XXXX (normalize to XX:XX:XX:XX:XX:XX); fallback to any address is
            mac_m = re.search(r"address\s+is\s+(\w{4}\.\w{4}\.\w{4})", block, re.IGNORECASE)
            if not mac_m:
                mac_m = re.search(r"address\s+is\s+([\da-fA-F.]+)", block, re.IGNORECASE)
            if mac_m:
                out["mac_address"] = self._normalize_mac_cisco(mac_m.group(1))
            ip_m = re.search(r"Internet\s+address\s+is\s+(\d+\.\d+\.\d+\.\d+)(?:/(\d+))?", block, re.IGNORECASE)
            if ip_m:
                out["ip_address"] = ip_m.group(1)
                if ip_m.group(2):
                    out["subnet_mask"] = ip_m.group(2)
            mtu_m = re.search(r"MTU\s+(\d+)\s+bytes", block, re.IGNORECASE)
            if mtu_m:
                out["mtu"] = int(mtu_m.group(1))
            # Bandwidth: BW (\d+) Kbit/sec -> explicit unit conversion (Kbit is Kbit, not Gbit)
            bw_m = re.search(r"BW\s+(\d+)\s*Kbit/sec", block, re.IGNORECASE)
            if bw_m:
                value = int(bw_m.group(1))
                if value >= 1_000_000:
                    out["speed"] = f"{value / 1_000_000:.0f}Gbps"
                elif value >= 1_000:
                    out["speed"] = f"{value / 1_000:.0f}Mbps"
                else:
                    out["speed"] = f"{value}Kbps"
            if not out.get("speed"):
                bw_m = re.search(r"BW\s+(\d+)\s*Mbit", block, re.IGNORECASE)
                if bw_m:
                    out["speed"] = f"{bw_m.group(1)}Mbps"
                else:
                    bw_m = re.search(r"BW\s+(\d+)\s*Gbit", block, re.IGNORECASE)
                    if bw_m:
                        out["speed"] = f"{bw_m.group(1)}Gbps"
            # Duplex: (Auto|Full|Half)[- ]Duplex -> prefer from BW when BW exists
            dup_m = re.search(r"(Auto|Full|Half)[-\s]*Duplex", block, re.IGNORECASE)
            if dup_m:
                out["duplex"] = (dup_m.group(1) or "auto").lower()
            # Speed setting: (Auto|\d+)[- ]Speed -> use only if BW line was missing
            speed_setting_m = re.search(r"(Auto|\d+)[-\s]*Speed", block, re.IGNORECASE)
            if speed_setting_m and not out.get("speed"):
                if speed_setting_m.group(1).lower() == "auto":
                    out["speed"] = "Auto"
                else:
                    try:
                        out["speed"] = f"{int(speed_setting_m.group(1))}Mbps"
                    except ValueError:
                        out["speed"] = "Auto"
            elif speed_setting_m and speed_setting_m.group(1).lower() != "auto":
                try:
                    num = int(speed_setting_m.group(1))
                    if num >= 1000:
                        out["speed"] = f"{num // 1000}Gbps"
                    else:
                        out["speed"] = f"{num}Mbps"
                except ValueError:
                    pass
            media_m = re.search(r"media\s+type\s+is\s+(\S+)", block, re.IGNORECASE)
            if media_m:
                out["media_type"] = media_m.group(1)
            enc_m = re.search(r"Encapsulation\s+(\w+)", block, re.IGNORECASE)
            if enc_m:
                out["encapsulation"] = enc_m.group(1)
            return out
        except Exception:
            return None

    def _parse_show_interfaces_blocks(self, content: str) -> Dict[str, Dict[str, Any]]:
        """Block-based parser: find 'show interfaces' section, split by interface header, extract each block. Returns dict name -> extracted data. Targets all interface types (GigabitEthernet, Loopback, Vlan, etc.)."""
        # Stop at next prompt only (not at "show " inside output e.g. "show interface" in counter text)
        show_m = re.search(r"show\s+interfaces\s*(.*?)(?=\n\s*\S+#|\n\s*\S+>|$)", content, re.IGNORECASE | re.DOTALL)
        show_int = (show_m.group(1) or "").strip() if show_m else ""
        if not show_int:
            return {}
        blocks: Dict[str, Dict[str, Any]] = {}
        pattern = re.compile(r"^(\S+)\s+is\s+(up|down|administratively\s+down).*?line\s+protocol\s+is\s+(up|down)", re.IGNORECASE | re.MULTILINE)
        starts = [m.start() for m in pattern.finditer(show_int)]
        for i, start in enumerate(starts):
            end = starts[i + 1] if i + 1 < len(starts) else len(show_int)
            block_text = show_int[start:end].strip()
            data = self._parse_one_show_interface_block(block_text)
            if data and data.get("name"):
                blocks[data["name"]] = data
        return blocks

    def _init_interface(self, canonical_name: str) -> Dict[str, Any]:
        """Return a single default interface record. Used so we never append; we only merge by key."""
        return {
            "name": canonical_name,
            "type": _determine_interface_type(canonical_name),
            "description": None,
            "ip_address": None,
            "subnet_mask": None,
            "status": "up",
            "protocol": "up",
            "mac_address": None,
            "speed": None,
            "duplex": None,
            "mode": None,
            "mtu": None,
            "access_vlan": None,
            "native_vlan": None,
            "allowed_vlans": None,
        }

    def extract_interfaces(self, content: str) -> List[Dict[str, Any]]:
        """2.3.2.2 - Dictionary merging: one dict keyed by canonical interface name. Source A = config, Source B = status; merge into same entry. No duplicates."""
        interfaces_dict: Dict[str, Dict[str, Any]] = {}
        config_block = _get_section(content, r"show\s+running-config") or content
        if not config_block.strip():
            config_block = content

        def _get_or_create(raw_name: str) -> Dict[str, Any]:
            key = _canonical_interface_name(raw_name)
            if key not in interfaces_dict:
                interfaces_dict[key] = self._init_interface(key)
            return interfaces_dict[key]

        # Source A: Configuration (most detailed) - update by canonical key
        for m in re.finditer(r"interface\s+(\S+)\s*\n(.*?)(?=\ninterface\s+|$)", config_block, re.IGNORECASE | re.DOTALL):
            name, block = m.group(1), m.group(2)
            if name.startswith("Null") or "NULL" in name.upper():
                continue
            iface = _get_or_create(name)
            if "shutdown" in block.lower():
                iface["status"] = "down"
                iface["protocol"] = "down"
            try:
                desc_m = re.search(r"description\s+(.+?)(?:\n|$)", block, re.IGNORECASE)
                if desc_m:
                    iface["description"] = desc_m.group(1).strip()
            except Exception:
                pass
            try:
                ip_m = re.search(r"ip\s+address\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+|\d+)", block, re.IGNORECASE)
                if not ip_m:
                    ip_m = re.search(r"ip\s+address\s+(\d+\.\d+\.\d+\.\d+)/(\d+)", block, re.IGNORECASE)
                if ip_m:
                    iface["ip_address"] = ip_m.group(1).strip()
                    mask_val = ip_m.group(2).strip() if ip_m.lastindex >= 2 else None
                    if mask_val:
                        iface["subnet_mask"] = mask_val  # dotted (255.255.255.0), prefix (24), or from CIDR
            except Exception:
                pass
            try:
                mtu_m = re.search(r"mtu\s+(\d+)", block, re.IGNORECASE)
                if mtu_m:
                    iface["mtu"] = int(mtu_m.group(1))
            except Exception:
                pass
            try:
                speed_m = re.search(r"speed\s+(\d+)", block, re.IGNORECASE)
                if speed_m:
                    iface["speed"] = f"{speed_m.group(1)}Mbps"
                elif "speed auto" in block.lower():
                    iface["speed"] = "auto"
            except Exception:
                pass
            try:
                dup_m = re.search(r"duplex\s+(full|half|auto)", block, re.IGNORECASE)
                if dup_m:
                    iface["duplex"] = dup_m.group(1).lower()
            except Exception:
                pass
            if "switchport mode access" in block.lower():
                iface["mode"] = "access"
                # For access mode, allowed_vlans should be None
                iface["allowed_vlans"] = None
                try:
                    acc_m = re.search(r"switchport\s+access\s+vlan\s+(\d+)", block, re.IGNORECASE)
                    if acc_m:
                        iface["access_vlan"] = int(acc_m.group(1))
                except Exception:
                    pass
            elif "switchport mode trunk" in block.lower():
                iface["mode"] = "trunk"
                try:
                    # Extract allowed VLANs from running-config
                    # Pattern: switchport trunk allowed vlan <vlan_list>
                    # vlan_list can be: 1,2,3 or 1-100 or 1-100,200-300 or "all" or "none"
                    trunk_m = re.search(r"switchport\s+trunk\s+allowed\s+vlan\s+(.+?)(?:\n|$)", block, re.IGNORECASE | re.MULTILINE)
                    if trunk_m:
                        allowed_vlans_str = trunk_m.group(1).strip()
                        # Handle "all", "none", or specific VLAN ranges
                        if allowed_vlans_str.lower() in ["all", "none"]:
                            iface["allowed_vlans"] = allowed_vlans_str.lower()
                        else:
                            # Normalize whitespace in VLAN list (e.g., "1, 2, 3" -> "1,2,3")
                            iface["allowed_vlans"] = re.sub(r'\s+', '', allowed_vlans_str)
                    else:
                        # Default: if trunk mode but no explicit allowed vlan line, allow all (1-4094)
                        iface["allowed_vlans"] = "1-4094"
                    native_m = re.search(r"switchport\s+trunk\s+native\s+vlan\s+(\d+)", block, re.IGNORECASE)
                    if native_m:
                        iface["native_vlan"] = int(native_m.group(1))
                except Exception:
                    # On error, default to "1-4094" for trunk mode
                    iface["allowed_vlans"] = "1-4094"
            elif "no switchport" in block.lower() or iface.get("ip_address"):
                iface["mode"] = "routed"
                # For routed ports, allowed_vlans should be None
                iface["allowed_vlans"] = None
        # Source B: show ip interface brief - merge oper_status / admin_status (same key = update, no new row)
        # Note: Interface names here may be short (Gi0/1), so we normalize them before lookup
        brief = _get_section(content, r"show\s+ip\s+interface\s+brief")
        if not brief:
            brief = re.search(r"show\s+ip\s+interface\s+brief\s*(.*?)(?=show\s+|\n\s*[\w-]+#|$)", content, re.IGNORECASE | re.DOTALL)
            brief = brief.group(1).strip() if brief else None
        if brief:
            for line in brief.split("\n")[1:]:
                parts = line.split()
                if len(parts) < 4:
                    continue
                name = parts[0]
                ip_val = parts[1] if len(parts) > 1 else None
                status = parts[3] if len(parts) > 3 else None
                protocol = parts[4] if len(parts) > 4 else None
                # Normalize interface name (short -> canonical) before lookup
                iface = _get_or_create(name)
                # Ensure type is set if not already set
                if not iface.get("type"):
                    iface["type"] = _determine_interface_type(iface["name"])
                if ip_val and ip_val != "unassigned":
                    if "/" in ip_val:
                        a, _, b = ip_val.partition("/")
                        iface["ip_address"] = a.strip()
                        if b.strip():
                            iface["subnet_mask"] = b.strip()
                    elif " " in ip_val:
                        parts_ip = ip_val.split(None, 1)
                        iface["ip_address"] = parts_ip[0]
                        if len(parts_ip) > 1 and parts_ip[1].strip():
                            iface["subnet_mask"] = parts_ip[1].strip()
                    else:
                        iface["ip_address"] = ip_val
                if status:
                    iface["status"] = status.lower()
                if protocol:
                    iface["protocol"] = protocol.lower()
        # Deep parse: block-based extraction from "show interfaces" (Description, MAC, IP, MTU, BW, Duplex, Speed, Media, Encapsulation)
        # Note: Interface names here may be short (Gi0/1), so we normalize them before lookup
        deep_blocks = self._parse_show_interfaces_blocks(content)
        for name, data in deep_blocks.items():
            if name.startswith("Null") or "NULL" in name.upper():
                continue
            iface = _get_or_create(name)
            # Ensure type is set if not already set
            if not iface.get("type"):
                iface["type"] = _determine_interface_type(iface["name"])
            for k, v in data.items():
                if k == "name":
                    continue
                if v is not None and (v != "" or k in ("description",)):
                    iface[k] = v
        # show interfaces switchport for mode if not set (merge by canonical name)
        # Also extract allowed_vlans from switchport output if not already set from config
        switchport = _get_section(content, r"show\s+interfaces\s+switchport")
        if switchport:
            for block in re.split(r"\n(?=\w)", switchport):
                name_m = re.search(r"Name\s*:\s*(\S+)", block, re.IGNORECASE)
                mode_m = re.search(r"Switchport\s+Mode[:\s]+(\w+)", block, re.IGNORECASE)
                if name_m:
                    key = _canonical_interface_name(name_m.group(1))
                    if key in interfaces_dict:
                        iface = interfaces_dict[key]
                        # Ensure type is set
                        if not iface.get("type"):
                            iface["type"] = _determine_interface_type(key)
                        # Set mode if not already set
                        if mode_m and iface.get("mode") is None:
                            mode_val = mode_m.group(1).lower()
                            if "access" in mode_val:
                                iface["mode"] = "access"
                                iface["allowed_vlans"] = None
                            elif "trunk" in mode_val:
                                iface["mode"] = "trunk"
                                # Try to extract allowed VLANs from switchport output
                                allowed_m = re.search(r"Trunking\s+VLANs\s+Enabled[:\s]+(.+?)(?:\n|$)", block, re.IGNORECASE | re.MULTILINE)
                                if allowed_m:
                                    allowed_str = allowed_m.group(1).strip()
                                    if allowed_str.lower() in ["all", "none"]:
                                        iface["allowed_vlans"] = allowed_str.lower()
                                    else:
                                        # Normalize whitespace
                                        iface["allowed_vlans"] = re.sub(r'\s+', '', allowed_str)
                                elif iface.get("allowed_vlans") is None:
                                    # Default for trunk mode
                                    iface["allowed_vlans"] = "1-4094"
                            else:
                                iface["mode"] = "routed"
                                iface["allowed_vlans"] = None
        
        # Final pass: ensure type is set for all interfaces and handle allowed_vlans defaults
        for iface in interfaces_dict.values():
            # Ensure type is set
            if not iface.get("type"):
                iface["type"] = _determine_interface_type(iface["name"])
            
            # Final allowed_vlans logic: set to None for access/routed, default "1-4094" for trunk without explicit setting
            mode = iface.get("mode")
            if mode == "access" or mode == "routed":
                iface["allowed_vlans"] = None
            elif mode == "trunk" and iface.get("allowed_vlans") is None:
                iface["allowed_vlans"] = "1-4094"
        
        return list(interfaces_dict.values())
    
    def _parse_vlan_brief_ports(self, ports_str: str) -> List[str]:
        """Parse ports string from 'show vlan brief' (e.g. 'Gi0/2, Gi0/3, Gi1/0'). Clean trailing commas, normalize to full names."""
        if not ports_str or not ports_str.strip():
            return []
        # Remove trailing commas and normalize whitespace
        cleaned = re.sub(r",\s*$", "", ports_str.strip())
        cleaned = re.sub(r"\s+", " ", cleaned)
        # Match Cisco interface tokens (short or full): Gi0/1, Fa0/1, Eth0/1, Po1, GigabitEthernet0/1, etc.
        raw_tokens = re.findall(
            r"(?:Gi|Fa|Eth|Te|Po|Lo|GigabitEthernet|FastEthernet|Ethernet|TenGigabitEthernet|Port-channel|Loopback)\S*",
            cleaned,
            re.IGNORECASE,
        )
        # Normalize each to canonical name and deduplicate preserving order
        seen = set()
        result: List[str] = []
        for token in raw_tokens:
            token = token.strip().rstrip(",")
            if not token:
                continue
            canonical = _canonical_interface_name(token)
            if canonical not in seen:
                seen.add(canonical)
                result.append(canonical)
        return result

    def extract_vlans(self, content: str) -> Dict[str, Any]:
        """
        2.3.2.3 - VLAN and Layer 2 Switching.
        Produces: total_vlan_count, vlan_list (IDs as strings), details (per-VLAN id/name/status/access_ports),
        trunk_ports (port, native_vlan, allowed_vlans). Port names normalized (Gi0/1 -> GigabitEthernet0/1).
        Access ports: from show vlan brief AND verified by switchport mode access in running-config.
        """
        details_by_id: Dict[int, Dict[str, Any]] = {}
        config_block = _get_section(content, r"show\s+running-config") or content
        if not config_block.strip():
            config_block = content

        # Build: which interfaces are in access mode (canonical name -> True)
        access_mode_interfaces: Dict[str, bool] = {}
        # Build: interface -> access vlan id (for mapping port to VLAN when building details)
        interface_to_access_vlan: Dict[str, int] = {}
        trunk_entries: List[Dict[str, Any]] = []

        for m in re.finditer(r"interface\s+(\S+)\s*\n(.*?)(?=\ninterface\s+|^end\s|$)", config_block, re.IGNORECASE | re.DOTALL):
            iface_name, block = m.group(1), m.group(2)
            if "NULL" in (iface_name or "").upper():
                continue
            canonical = _canonical_interface_name(iface_name)
            if "switchport mode access" in block.lower():
                access_mode_interfaces[canonical] = True
                acc_m = re.search(r"switchport\s+access\s+vlan\s+(\d+)", block, re.IGNORECASE)
                if acc_m:
                    try:
                        interface_to_access_vlan[canonical] = int(acc_m.group(1))
                    except ValueError:
                        pass
            elif "switchport mode trunk" in block.lower():
                native_m = re.search(r"switchport\s+trunk\s+native\s+vlan\s+(\d+)", block, re.IGNORECASE)
                allow_m = re.search(r"switchport\s+trunk\s+allowed\s+vlan\s+(.+?)(?:\n|$)", block, re.IGNORECASE | re.MULTILINE)
                allowed_str = (allow_m.group(1).strip() if allow_m else "1-4094")
                if allowed_str.lower() in ("all", "none"):
                    allowed_str = allowed_str.lower()
                else:
                    allowed_str = re.sub(r"\s+", "", allowed_str)
                trunk_entries.append({
                    "port": canonical,
                    "native_vlan": (native_m.group(1) if native_m else "1"),
                    "allowed_vlans": allowed_str,
                })

        # Config-only VLAN definitions (vlan X / name Y)
        for m in re.finditer(r"vlan\s+(\d+)\s*\n(.*?)(?=\nvlan\s+|^end\s|$)", config_block, re.IGNORECASE | re.DOTALL):
            try:
                vid = int(m.group(1))
            except ValueError:
                continue
            block = m.group(2)
            name_m = re.search(r"name\s+(\S+)", block, re.IGNORECASE)
            if vid not in details_by_id:
                details_by_id[vid] = {"id": str(vid), "name": name_m.group(1) if name_m else str(vid), "status": "active", "access_ports": []}

        # Parse show vlan brief: VLAN inventory (id, name, status) and port assignments
        show_vlan = _get_section(content, r"show\s+vlan\s+brief") or _get_section(content, r"show\s+vlan\s")
        vlan_ids_seen_in_table: set = set()
        if show_vlan:
            # Match: VID (digits), name (single token), status (active|act/unsup|suspend|etc)
            status_re = re.compile(
                r"^(\d+)\s+(\S+)\s+(active|act/lshut|suspend|act/unsup)",
                re.IGNORECASE,
            )
            lines = show_vlan.split("\n")
            i = 0
            while i < len(lines):
                line = lines[i]
                line_strip = line.strip()
                if line_strip.startswith("VLAN") or line_strip.startswith("VID") or line_strip.startswith("----") or (line_strip.startswith("Vlan") and len(line_strip) > 4 and not line_strip[4:5].isdigit()):
                    i += 1
                    continue
                mm = status_re.search(line_strip)
                if mm:
                    try:
                        vid = int(mm.group(1))
                        name = mm.group(2)
                        status = mm.group(3).lower()
                    except (ValueError, IndexError):
                        i += 1
                        continue
                    # Ports: rest of line, then continuation lines (no leading VLAN number)
                    ports_str = line[mm.end():].strip() if mm.end() < len(line) else ""
                    j = i + 1
                    while j < len(lines):
                        next_line = lines[j].strip()
                        if not next_line:
                            j += 1
                            continue
                        if status_re.match(next_line):
                            break
                        if re.search(r"^(?:Gi|Fa|Eth|Te|Po|GigabitEthernet|FastEthernet|Port-channel)\S", next_line, re.IGNORECASE):
                            ports_str += " " + next_line
                            j += 1
                        else:
                            j += 1
                            break
                    i = j
                    port_list_raw = self._parse_vlan_brief_ports(ports_str)
                    vlan_ids_seen_in_table.add(vid)
                    if vid not in details_by_id:
                        details_by_id[vid] = {"id": str(vid), "name": name, "status": status, "access_ports": []}
                    else:
                        details_by_id[vid]["name"] = name
                        details_by_id[vid]["status"] = status
                    # Only include ports that are in access mode AND assigned to this VLAN in running-config
                    access_ports_for_vlan = [
                        p for p in port_list_raw
                        if access_mode_interfaces.get(p) and interface_to_access_vlan.get(p) == vid
                    ]
                    details_by_id[vid]["access_ports"] = list(dict.fromkeys(access_ports_for_vlan))
                else:
                    i += 1

        # If we only have config (no show vlan brief), still assign access_ports from config
        if not vlan_ids_seen_in_table and interface_to_access_vlan:
            for canonical, vlan_id in interface_to_access_vlan.items():
                if vlan_id not in details_by_id:
                    details_by_id[vlan_id] = {"id": str(vlan_id), "name": str(vlan_id), "status": "active", "access_ports": []}
                if canonical not in details_by_id[vlan_id]["access_ports"]:
                    details_by_id[vlan_id]["access_ports"].append(canonical)

        # Config-only VLANs: in config but not in show vlan brief -> "Configured (Inactive)"
        if show_vlan and vlan_ids_seen_in_table:
            for vid, d in list(details_by_id.items()):
                try:
                    v = int(d["id"])
                    if v not in vlan_ids_seen_in_table and d.get("status") == "active":
                        d["status"] = "Configured (Inactive)"
                except (ValueError, TypeError):
                    pass

        # Build sorted vlan_list (IDs as strings) and details with access_ports only
        sorted_details = sorted(
            details_by_id.values(),
            key=lambda d: int(d["id"]) if (isinstance(d["id"], str) and d["id"].isdigit()) else 9999,
        )
        vlan_list_ids = [d["id"] for d in sorted_details if isinstance(d["id"], str) and d["id"].isdigit()]
        details = [
            {
                "id": d["id"],
                "name": d.get("name") or d["id"],
                "status": d.get("status", "active"),
                "access_ports": list(d.get("access_ports") or []),
            }
            for d in sorted_details
        ]
        # Flat list of all access-mode interfaces (canonical names) for backward compatibility
        access_ports_flat = sorted(access_mode_interfaces.keys())

        return {
            "total_vlan_count": len(details_by_id),
            "vlan_list": vlan_list_ids,
            "details": details,
            "access_ports": access_ports_flat,
            "trunk_ports": trunk_entries,
            "total_count": len(details_by_id),
        }
    
    def _parse_stp_detail_blocks(self, detail_text: str, config_block: str) -> Dict[str, Any]:
        """
        Parse 'show spanning-tree detail' output block-by-block (per VLAN).
        Returns dict with mode, root_bridge (id, priority, is_local_device_root), and per-interface
        role/state/cost/portfast/bpduguard. Aggregates by interface name (prioritize Root role, Forwarding state).
        """
        result: Dict[str, Any] = {
            "mode": None,
            "root_bridge_id": None,
            "root_bridge_priority": None,
            "is_local_device_root": False,
            "root_bridges": [],
            "port_data_by_iface": {},  # canonical_name -> {role, state, cost, portfast_enabled, bpduguard_enabled}
        }
        # Protocol name -> mode mapping
        def protocol_to_mode(proto: str) -> str:
            if not proto:
                return None
            p = proto.lower()
            if "rstp" in p or "rapid" in p:
                return "RAPID-PVST"
            if "mst" in p or "mstp" in p:
                return "MST"
            if "ieee" in p or "pvst" in p:
                return "PVST"
            return proto.upper() if proto else None

        # Split into VLAN blocks (VLAN0001 is executing ... until next VLAN or end)
        vlan_blocks = re.split(r"\n(?=\s*VLAN\d+\s+is\s+executing)", detail_text, re.IGNORECASE)
        for block in vlan_blocks:
            if not block.strip():
                continue
            # Mode: "VLAN0001 is executing the rstp compatible Spanning Tree protocol"
            mode_m = re.search(r"VLAN\d+\s+is\s+executing\s+the\s+(.+?)\s+[Ss]panning\s+[Tt]ree\s+protocol", block, re.IGNORECASE)
            if mode_m and not result["mode"]:
                result["mode"] = protocol_to_mode(mode_m.group(1))

            # Current root: "Current root has priority 32769, address 5000.0003.0000"
            current_root_m = re.search(r"Current\s+root\s+has\s+priority\s+(\d+),\s*address\s+([0-9a-fA-F.]+)", block, re.IGNORECASE)
            # Local bridge: "Bridge Identifier has priority 32768, sysid 1, address 5000.0004.0000"
            bridge_m = re.search(r"Bridge\s+Identifier\s+has\s+priority\s+(\d+).*?address\s+([0-9a-fA-F.]+)", block, re.IGNORECASE | re.DOTALL)
            # "We are the root of the spanning tree"
            we_are_root = bool(re.search(r"We\s+are\s+the\s+root\s+of\s+the\s+spanning\s+tree", block, re.IGNORECASE))

            root_priority = None
            root_address = None
            local_priority = None
            local_address = None
            if current_root_m:
                root_priority = int(current_root_m.group(1))
                root_address = (current_root_m.group(2) or "").strip().lower()
            if bridge_m:
                local_priority = int(bridge_m.group(1))
                local_address = (bridge_m.group(2) or "").strip().lower()
            if we_are_root and bridge_m:
                root_priority = local_priority
                root_address = local_address
                result["is_local_device_root"] = True
                vlan_num_m = re.search(r"VLAN(\d+)", block, re.IGNORECASE)
                if vlan_num_m:
                    try:
                        v = int(vlan_num_m.group(1))
                        if v not in result["root_bridges"]:
                            result["root_bridges"].append(v)
                    except ValueError:
                        pass
            if root_address and result["root_bridge_id"] is None:
                result["root_bridge_id"] = root_address
            if root_priority is not None and result["root_bridge_priority"] is None:
                result["root_bridge_priority"] = root_priority

            # Port lines: "Port 2 (GigabitEthernet0/1) of VLAN0001 is root forwarding"
            port_line_re = re.compile(r"Port\s+\d+\s+\((.+?)\)\s+of\s+VLAN\d+\s+is\s+(\w+)\s+(\w+)", re.IGNORECASE)
            for pm in port_line_re.finditer(block):
                iface_raw = (pm.group(1) or "").strip()
                role_raw = (pm.group(2) or "").lower()
                state_raw = (pm.group(3) or "").lower()
                canonical = _canonical_interface_name(iface_raw)
                # Role: root | designated | alternate | backup
                role = "Root" if "root" in role_raw else "Designated" if "designated" in role_raw or "desg" in role_raw else "Alternate" if "alternate" in role_raw else "Backup" if "backup" in role_raw else role_raw.capitalize()
                state = "Forwarding" if "forward" in state_raw else "Blocking" if "block" in state_raw else "Learning" if "learn" in state_raw else "Discarding" if "discard" in state_raw else state_raw.capitalize()
                # Sub-attributes: indented "Port path cost 4"
                port_block_start = pm.start()
                port_block_end = pm.end()
                next_port = port_line_re.search(block, port_block_end)
                port_block = block[port_block_start : next_port.start() if next_port else len(block)]
                cost_m = re.search(r"Port\s+path\s+cost\s+(\d+)", port_block, re.IGNORECASE)
                cost = int(cost_m.group(1)) if cost_m else None
                portfast = bool(re.search(r"port\s+is\s+in\s+the\s+portfast\s+(?:edge\s+)?mode", port_block, re.IGNORECASE))
                bpduguard = bool(re.search(r"[Bb]pdu\s+guard\s+is\s+enabled", port_block, re.IGNORECASE))

                if canonical not in result["port_data_by_iface"]:
                    result["port_data_by_iface"][canonical] = {"role": role, "state": state, "cost": cost, "portfast_enabled": portfast, "bpduguard_enabled": bpduguard}
                else:
                    cur = result["port_data_by_iface"][canonical]
                    # Prefer Root over Designated over Alternate over Backup
                    role_order = {"Root": 0, "Designated": 1, "Alternate": 2, "Backup": 3}
                    if role_order.get(role, 99) < role_order.get(cur["role"], 99):
                        cur["role"] = role
                    if state == "Forwarding":
                        cur["state"] = "Forwarding"
                    elif cur["state"] != "Forwarding" and state == "Learning":
                        cur["state"] = "Learning"
                    elif cur["state"] not in ("Forwarding", "Learning") and state in ("Blocking", "Discarding"):
                        cur["state"] = state
                    if cost is not None and cur.get("cost") is None:
                        cur["cost"] = cost
                    cur["portfast_enabled"] = cur.get("portfast_enabled") or portfast
                    cur["bpduguard_enabled"] = cur.get("bpduguard_enabled") or bpduguard
        return result

    def extract_stp(self, content: str) -> Dict[str, Any]:
        """2.3.2.4 - STP: mode, root bridge (id, priority, is_root), port role/state/cost, PortFast, BPDU Guard. Supports show spanning-tree detail."""
        stp: Dict[str, Any] = {"mode": None, "root_bridges": [], "root_bridge_id": None, "interfaces": [], "portfast_enabled": None, "bpduguard_enabled": None}
        config_block = _get_section(content, r"show\s+running-config") or content
        if not config_block.strip():
            config_block = content
        mode_m = re.search(r"spanning-tree\s+mode\s+(\S+)", config_block, re.IGNORECASE)
        if mode_m:
            raw = mode_m.group(1).upper()
            stp["mode"] = "RAPID-PVST" if "RAPID" in raw or "RPVST" in raw else "MST" if "MST" in raw else raw
        if re.search(r"spanning-tree\s+portfast", config_block, re.IGNORECASE):
            stp["portfast_enabled"] = True
        if re.search(r"spanning-tree\s+bpduguard\s+enable", config_block, re.IGNORECASE):
            stp["bpduguard_enabled"] = True

        # Prefer 'show spanning-tree detail' when summary is not available
        show_detail = _get_section(content, r"show\s+spanning-tree\s+detail")
        if not show_detail:
            show_detail = re.search(r"show\s+spanning-tree\s+detail\s*(.*?)(?=\n\s*\S+#|\n\s*\S+>|$)", content, re.IGNORECASE | re.DOTALL)
            show_detail = (show_detail.group(1) or "").strip() if show_detail else ""
        show_stp = _get_section(content, r"show\s+spanning-tree(?:\s+detail)?")
        if not show_stp:
            show_stp = re.search(r"show\s+spanning-tree(?:\s+detail)?\s*(.*?)(?=\n\s*\S+#|\n\s*\S+>|$)", content, re.IGNORECASE | re.DOTALL)
            show_stp = (show_stp.group(1) or "").strip() if show_stp else ""

        if show_detail:
            parsed = self._parse_stp_detail_blocks(show_detail, config_block)
            if parsed.get("mode"):
                stp["mode"] = parsed["mode"]
            if parsed.get("root_bridge_id"):
                stp["root_bridge_id"] = parsed["root_bridge_id"]
            if parsed.get("root_bridges"):
                stp["root_bridges"] = parsed["root_bridges"]
            if parsed.get("port_data_by_iface"):
                for canonical, data in parsed["port_data_by_iface"].items():
                    rec = {
                        "port": canonical,
                        "role": data.get("role"),
                        "state": data.get("state"),
                        "cost": data.get("cost"),
                        "portfast_enabled": data.get("portfast_enabled", False),
                        "bpduguard_enabled": data.get("bpduguard_enabled", False),
                    }
                    stp["interfaces"].append(rec)
                    if data.get("portfast_enabled"):
                        stp["portfast_enabled"] = True
                    if data.get("bpduguard_enabled"):
                        stp["bpduguard_enabled"] = True
            if parsed.get("is_local_device_root") and not stp["root_bridges"]:
                stp["root_bridges"].append(1)
            stp["stp_info"] = {
                "mode": stp["mode"],
                "root_bridge": {
                    "root_bridge_id": stp.get("root_bridge_id"),
                    "priority": parsed.get("root_bridge_priority"),
                    "is_local_device_root": parsed.get("is_local_device_root", False),
                },
                "interfaces": [
                    {
                        "port": r["port"],
                        "role": r.get("role"),
                        "state": r.get("state"),
                        "cost": r.get("cost"),
                        "portfast_enabled": r.get("portfast_enabled", False),
                        "bpduguard_enabled": r.get("bpduguard_enabled", False),
                    }
                    for r in stp["interfaces"]
                ],
            }
            return stp

        # Fallback: if only "show spanning-tree" block exists but it looks like detail (VLANxxxx is executing), parse as detail
        if not show_detail and show_stp and re.search(r"VLAN\d+\s+is\s+executing", show_stp, re.IGNORECASE):
            show_detail = show_stp
            parsed = self._parse_stp_detail_blocks(show_detail, config_block)
            if parsed.get("mode"):
                stp["mode"] = parsed["mode"]
            if parsed.get("root_bridge_id"):
                stp["root_bridge_id"] = parsed["root_bridge_id"]
            if parsed.get("root_bridges"):
                stp["root_bridges"] = parsed["root_bridges"]
            if parsed.get("port_data_by_iface"):
                for canonical, data in parsed["port_data_by_iface"].items():
                    rec = {
                        "port": canonical,
                        "role": data.get("role"),
                        "state": data.get("state"),
                        "cost": data.get("cost"),
                        "portfast_enabled": data.get("portfast_enabled", False),
                        "bpduguard_enabled": data.get("bpduguard_enabled", False),
                    }
                    stp["interfaces"].append(rec)
                    if data.get("portfast_enabled"):
                        stp["portfast_enabled"] = True
                    if data.get("bpduguard_enabled"):
                        stp["bpduguard_enabled"] = True
            if parsed.get("is_local_device_root") and not stp["root_bridges"]:
                stp["root_bridges"].append(1)
            stp["stp_info"] = {
                "mode": stp["mode"],
                "root_bridge": {
                    "root_bridge_id": stp.get("root_bridge_id"),
                    "priority": parsed.get("root_bridge_priority"),
                    "is_local_device_root": parsed.get("is_local_device_root", False),
                },
                "interfaces": [
                    {"port": r["port"], "role": r.get("role"), "state": r.get("state"), "cost": r.get("cost"), "portfast_enabled": r.get("portfast_enabled", False), "bpduguard_enabled": r.get("bpduguard_enabled", False)}
                    for r in stp["interfaces"]
                ],
            }
            return stp

        # Legacy: summary output (show spanning-tree without detail)
        if show_stp:
            root_id_m = re.search(r"Root\s+ID\s+.*?Address\s+([\da-fA-F.]+)", show_stp, re.IGNORECASE)
            if root_id_m:
                stp["root_bridge_id"] = root_id_m.group(1)
            for m in re.finditer(r"(?:VLAN\s*)?(\d+).*?[Tt]his\s+bridge\s+is\s+the\s+root", show_stp, re.IGNORECASE | re.DOTALL):
                try:
                    v = int(m.group(1))
                    if v not in stp["root_bridges"]:
                        stp["root_bridges"].append(v)
                except ValueError:
                    pass
            if "this bridge is the root" in show_stp.lower() and not stp["root_bridges"]:
                stp["root_bridges"].append(1)
            port_line_re = re.compile(r"^(\S+)\s+(Desg|Root|Altn|Back)\s+(FWD|BLK|LRN)\s+(\d+)\s+(\d+\.\d+)", re.IGNORECASE)
            for line in show_stp.split("\n"):
                line_strip = line.strip()
                if not line_strip or (line_strip.startswith("Port") and "Role" in line_strip) or line_strip.startswith("----"):
                    continue
                pm = port_line_re.match(line_strip)
                if pm:
                    port_name, role, state = pm.group(1), pm.group(2), pm.group(3)
                    cost_val = int(pm.group(4)) if pm.group(4).isdigit() else None
                    rec = {"port": _canonical_interface_name(port_name), "role": role, "state": state, "cost": cost_val, "portfast_enabled": False, "bpduguard_enabled": False}
                    if not any(x.get("port") == rec["port"] for x in stp["interfaces"]):
                        stp["interfaces"].append(rec)
            if not stp["interfaces"]:
                port_block_re = re.compile(r"Port\s+\d+\s+\((\S+)\)\s+of\s+VLAN\d+\s+is\s+(\w+)\s+(\w+)", re.IGNORECASE)
                for pm in port_block_re.finditer(show_stp):
                    port_name = _canonical_interface_name(pm.group(1))
                    role_raw = (pm.group(2) or "").lower()
                    state_raw = (pm.group(3) or "").lower()
                    role = "Designated" if "designated" in role_raw or "desg" in role_raw else "Root" if "root" in role_raw else "Alternate" if "alternate" in role_raw else "Backup" if "backup" in role_raw else role_raw.capitalize()
                    state = "Forwarding" if "forward" in state_raw else "Blocking" if "block" in state_raw else "Learning" if "learn" in state_raw else state_raw.capitalize()
                    rec = {"port": port_name, "role": role, "state": state, "cost": None, "portfast_enabled": stp.get("portfast_enabled") or False, "bpduguard_enabled": stp.get("bpduguard_enabled") or False}
                    stp["interfaces"].append(rec)
        return stp
    
    def extract_routing(self, content: str) -> Dict[str, Any]:
        """2.3.2.5 - routes (with distance/metric), ospf (interfaces, learned_prefix_count), eigrp, bgp, rip."""
        routes: List[Dict[str, Any]] = []
        route_block = _get_section(content, r"show\s+ip\s+route")
        if route_block:
            for line in route_block.split("\n"):
                line_stripped = line.strip()
                if not line_stripped or line_stripped.startswith("Codes:") or line_stripped.startswith("Gateway"):
                    continue
                if " is subnetted" in line_stripped or " is variably subnetted" in line_stripped:
                    continue
                if re.match(r"^\s*\[\d+/\d+\]\s+via\s+", line):
                    continue
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
                distance = None
                metric = None
                ad_metric_m = re.search(r"\[\s*(\d+)\s*/\s*(\d+)\s*\]", line_stripped)
                if ad_metric_m:
                    distance = int(ad_metric_m.group(1))
                    metric = int(ad_metric_m.group(2))
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
                routes.append({
                    "protocol": protocol,
                    "network": network,
                    "next_hop": next_hop or "",
                    "interface": interface or "",
                    "distance": distance,
                    "metric": metric,
                })
        config_block = _get_section(content, r"show\s+running-config") or content
        for m in re.finditer(
            r"ip\s+route\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+)(?:\s+(\d+))?(?:\s+(\S+))?",
            config_block,
            re.IGNORECASE,
        ):
            network_addr, mask, next_hop = m.group(1), m.group(2), m.group(3)
            fourth, fifth = (m.group(4) or "").strip(), (m.group(5) or "").strip()
            ad = 1
            interface = ""
            if fourth:
                if fourth.isdigit():
                    ad = int(fourth)
                    if fifth and re.match(r"^(Gi|Fa|Eth|Te|Se|Lo|Vl|Po|Serial|GigabitEthernet)", fifth, re.IGNORECASE):
                        interface = fifth
                elif re.match(r"^(Gi|Fa|Eth|Te|Se|Lo|Vl|Po|Serial|GigabitEthernet)", fourth, re.IGNORECASE):
                    interface = fourth
            cidr = _mask_to_cidr(mask)
            network = f"{network_addr}/{cidr}" if cidr is not None else network_addr
            if next((r for r in routes if r["network"] == network and r.get("protocol") == "S"), None):
                continue
            routes.append({"protocol": "S", "network": network, "next_hop": next_hop, "interface": interface, "distance": ad, "metric": 0})

        ospf = {"router_id": None, "process_id": None, "areas": [], "interfaces": [], "neighbors": [], "dr_bdr": {}, "learned_prefix_count": None}
        eigrp = {"as_number": None, "router_id": None, "neighbors": [], "hold_time": None, "learned_routes": []}
        bgp = {"local_as": None, "peers": [], "router_id": None}
        rip = {
            "version": None,
            "advertised_networks": [],
            "learned_routes": [],
            "participating_interfaces": [],
            "auto_summary": None,
            "passive_interfaces": [],
            "timers": {
                "update": None,
                "invalid": None,
                "hold": None,        # Legacy
                "hold_down": None,   # 2.3.2.5.5.6
                "flush": None,
            },
            "admin_distance": None,
            "interfaces": [],        # Legacy
        }

        # --- OSPF (Scope 2.3.2.5.2) ---
        ospf_m = re.search(r"router\s+ospf\s+(\d+)", config_block, re.IGNORECASE)
        if ospf_m:
            try:
                ospf["process_id"] = int(ospf_m.group(1))
                rid_m = re.search(r"router\s+ospf\s+\d+.*?router-id\s+(\d+\.\d+\.\d+\.\d+)", config_block, re.IGNORECASE | re.DOTALL)
                if rid_m:
                    ospf["router_id"] = rid_m.group(1)
                section = re.search(r"router\s+ospf\s+\d+(.*?)(?=router\s+|ip\s+|^!\s*$|\n\s*end\s*$|$)", config_block, re.IGNORECASE | re.DOTALL)
                if section:
                    body = section.group(1)
                    for area_m in re.finditer(r"network\s+(\S+)\s+(\S+)\s+area\s+(\S+)", body, re.IGNORECASE):
                        a = area_m.group(3)
                        if a not in ospf["areas"]:
                            ospf["areas"].append(a)
            except (ValueError, TypeError):
                pass
        ospf_interfaces_by_name: Dict[str, str] = {}
        for if_m in re.finditer(r"interface\s+(\S+)\s*\n(.*?)(?=\ninterface\s+|^!\s*$|\n\s*end\s*$|$)", config_block, re.IGNORECASE | re.DOTALL):
            iface_name, block = if_m.group(1), if_m.group(2)
            ip_ospf_m = re.search(r"ip\s+ospf\s+\d+\s+area\s+(\S+)", block, re.IGNORECASE)
            if ip_ospf_m:
                ospf_interfaces_by_name[iface_name] = ip_ospf_m.group(1)
        ospf_section = re.search(r"router\s+ospf\s+\d+(.*?)(?=router\s+|ip\s+|^!\s*$|\n\s*end\s*$|$)", config_block, re.IGNORECASE | re.DOTALL)
        if ospf_section:
            body = ospf_section.group(1)
            net_area_list = [(m.group(1), m.group(2), m.group(3)) for m in re.finditer(r"network\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+)\s+area\s+(\S+)", body, re.IGNORECASE)]
            for if_m2 in re.finditer(r"interface\s+(\S+)\s*\n(.*?)(?=\ninterface\s+|^!\s*$|\n\s*end\s*$|$)", config_block, re.IGNORECASE | re.DOTALL):
                iface_name, block = if_m2.group(1), if_m2.group(2)
                if iface_name in ospf_interfaces_by_name:
                    continue
                ip_m = re.search(r"ip\s+address\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+)", block, re.IGNORECASE)
                if not ip_m:
                    continue
                for net_addr, wildcard, area in net_area_list:
                    if _ip_in_ospf_network(ip_m.group(1), net_addr, wildcard):
                        ospf_interfaces_by_name[iface_name] = area
                        break
        for iface, area in ospf_interfaces_by_name.items():
            ospf["interfaces"].append({"interface": iface, "area": area})
        ospf_neigh_section = _get_section(content, r"show\s+ip\s+ospf\s+neighbor")
        if ospf_neigh_section:
            for line in ospf_neigh_section.split("\n"):
                neigh_m = re.search(r"(\d+\.\d+\.\d+\.\d+)\s+(\d+)\s+(FULL|2WAY|EXSTART|INIT|DOWN|LOADING|EXCHANGE)\s*[/\s]*(\w*)", line, re.IGNORECASE)
                if neigh_m:
                    nbr = {"neighbor_id": neigh_m.group(1), "priority": int(neigh_m.group(2)), "state": (neigh_m.group(3) or "").upper()}
                    if neigh_m.group(4):
                        nbr["dr_bdr"] = neigh_m.group(4).upper()
                    addr_if = re.search(r"(\d+\.\d+\.\d+\.\d+)\s+(\S+)\s*$", line)
                    if addr_if:
                        nbr["address"] = addr_if.group(1)
                        nbr["interface"] = addr_if.group(2)
                    ospf["neighbors"].append(nbr)
        ospf["learned_prefix_count"] = sum(1 for r in routes if (r.get("protocol") or "").startswith("O"))

        # --- EIGRP (Scope 2.3.2.5.3) ---
        eigrp_m = re.search(r"router\s+eigrp\s+(\d+)", config_block, re.IGNORECASE)
        if eigrp_m:
            try:
                eigrp["as_number"] = int(eigrp_m.group(1))
                rid_m = re.search(r"eigrp\s+router-id\s+(\d+\.\d+\.\d+\.\d+)", config_block, re.IGNORECASE)
                if not rid_m:
                    rid_m = re.search(r"router\s+eigrp\s+\d+.*?router-id\s+(\d+\.\d+\.\d+\.\d+)", config_block, re.IGNORECASE | re.DOTALL)
                if rid_m:
                    eigrp["router_id"] = rid_m.group(1)
            except (ValueError, TypeError):
                pass
        ip_protocols = _get_section(content, r"show\s+ip\s+protocols")
        if ip_protocols and eigrp["as_number"] is None:
            eigrp_as = re.search(r'Routing\s+Protocol\s+is\s+"eigrp\s+(\d+)"', ip_protocols, re.IGNORECASE)
            if eigrp_as:
                eigrp["as_number"] = int(eigrp_as.group(1))
        eigrp_neigh_section = _get_section(content, r"show\s+ip\s+eigrp\s+neighbors")
        if not eigrp_neigh_section:
            eigrp_neigh_section = _get_section(content, r"show\s+ip\s+eigrp\s+neighbour")
        if eigrp_neigh_section:
            for line in eigrp_neigh_section.split("\n"):
                line_strip = line.strip()
                if not line_strip or "Address" in line_strip and "Interface" in line_strip:
                    continue
                nbr_m = re.match(r"(\d+\.\d+\.\d+\.\d+)\s+(\S+)\s+(\d+)", line_strip)
                if nbr_m:
                    eigrp["neighbors"].append({
                        "address": nbr_m.group(1),
                        "interface": nbr_m.group(2),
                        "hold_time": int(nbr_m.group(3)),
                    })
        eigrp["learned_routes"] = [r for r in routes if (r.get("protocol") or "").strip().startswith("D")]

        # --- BGP (Scope 2.3.2.5.4) ---
        bgp_m = re.search(r"router\s+bgp\s+(\d+)", config_block, re.IGNORECASE)
        if bgp_m:
            try:
                bgp["local_as"] = int(bgp_m.group(1))
                rid_m = re.search(r"router\s+bgp\s+\d+.*?bgp\s+router-id\s+(\d+\.\d+\.\d+\.\d+)", config_block, re.IGNORECASE | re.DOTALL)
                if not rid_m:
                    rid_m = re.search(r"router\s+bgp\s+\d+.*?router-id\s+(\d+\.\d+\.\d+\.\d+)", config_block, re.IGNORECASE | re.DOTALL)
                if rid_m:
                    bgp["router_id"] = rid_m.group(1)
                for nb_m in re.finditer(r"neighbor\s+(\d+\.\d+\.\d+\.\d+)\s+remote-as\s+(\d+)", config_block, re.IGNORECASE):
                    bgp["peers"].append({"neighbor_ip": nb_m.group(1), "remote_as": int(nb_m.group(2)), "state": "configured_but_down", "prefixes_received": None})
            except (ValueError, TypeError):
                pass
        bgp_summary = _get_section(content, r"show\s+ip\s+bgp\s+summary")
        if bgp_summary:
            for line in bgp_summary.split("\n"):
                line_strip = line.strip()
                if not line_strip or line_strip.startswith("Neighbor") or line_strip.startswith("BGP"):
                    continue
                tokens = line_strip.split()
                if len(tokens) >= 3 and re.match(r"^\d+\.\d+\.\d+\.\d+$", tokens[0]):
                    neighbor_ip = tokens[0]
                    remote_as = int(tokens[2]) if tokens[2].isdigit() else None
                    state = None
                    prefixes_received = None
                    if len(tokens) >= 10:
                        last1, last2 = tokens[-1], tokens[-2]
                        if last1.isdigit():
                            prefixes_received = int(last1)
                            state = last2 if not last2.isdigit() else "Established"
                        else:
                            state = last1
                            if last2.isdigit():
                                prefixes_received = int(last2)
                    elif len(tokens) >= 9:
                        last = tokens[-1]
                        if last.isdigit():
                            prefixes_received = int(last)
                            state = "Established"
                        else:
                            state = last
                    existing = next((p for p in bgp["peers"] if p.get("neighbor_ip") == neighbor_ip or p.get("peer") == neighbor_ip), None)
                    if existing:
                        if state is not None:
                            existing["state"] = state
                        if prefixes_received is not None:
                            existing["prefixes_received"] = prefixes_received
                        if "neighbor_ip" not in existing:
                            existing["neighbor_ip"] = neighbor_ip
                    else:
                        bgp["peers"].append({"neighbor_ip": neighbor_ip, "remote_as": remote_as, "state": state or "Unknown", "prefixes_received": prefixes_received})
        for p in bgp["peers"]:
            if "neighbor_ip" not in p and p.get("peer"):
                p["neighbor_ip"] = p["peer"]

        # --- RIP / RIPv2 (Scope 2.3.2.5.5) ---
        rip_found = False

        # --- Source 1: running-config (router rip section) ---
        rip_config_m = re.search(r"router\s+rip", config_block, re.IGNORECASE)
        if rip_config_m:
            rip_found = True
            # Extract the router rip section body (until next 'router', top-level 'ip', '!' or 'end')
            rip_section = re.search(
                r"router\s+rip\s*\n(.*?)(?=\nrouter\s+|\n!\s*\n|\nend\s*$|\nip\s+(?:route|prefix|access|name))",
                config_block, re.IGNORECASE | re.DOTALL
            )
            if rip_section:
                rip_body = rip_section.group(1)

                # 2.3.2.5.5.1 - Version
                ver_m = re.search(r"version\s+(\d+)", rip_body, re.IGNORECASE)
                if ver_m:
                    rip["version"] = int(ver_m.group(1))

                # 2.3.2.5.5.2 - Advertised networks (from 'network x.x.x.x')
                for net_m in re.finditer(r"^\s*network\s+(\d+\.\d+\.\d+\.\d+)", rip_body, re.IGNORECASE | re.MULTILINE):
                    net = net_m.group(1)
                    if net not in rip["advertised_networks"]:
                        rip["advertised_networks"].append(net)

                # 2.3.2.5.5.5 - Auto-summary (default is enabled; 'no auto-summary' disables)
                if re.search(r"no\s+auto-summary", rip_body, re.IGNORECASE):
                    rip["auto_summary"] = False
                else:
                    rip["auto_summary"] = True

                # 2.3.2.5.5.5 - Passive interfaces
                passive_default = bool(re.search(r"passive-interface\s+default", rip_body, re.IGNORECASE))
                if passive_default:
                    rip["passive_interfaces"] = ["default"]
                else:
                    for pass_m in re.finditer(r"passive-interface\s+(\S+)", rip_body, re.IGNORECASE):
                        iface = pass_m.group(1)
                        if iface.lower() != "default" and iface not in rip["passive_interfaces"]:
                            rip["passive_interfaces"].append(iface)

        # --- Source 2: show ip protocols (RIP section only - section splitting) ---
        if ip_protocols:
            protocol_blocks = re.split(
                r'(?=Routing\s+Protocol\s+is\s+")',
                ip_protocols, flags=re.IGNORECASE
            )
            rip_protocol_block = ""
            for pblock in protocol_blocks:
                if re.match(r'\s*Routing\s+Protocol\s+is\s+"rip"', pblock, re.IGNORECASE):
                    rip_protocol_block = pblock
                    rip_found = True
                    break

            if rip_protocol_block:
                # 2.3.2.5.5.1 - Version from show ip protocols
                send_ver_m = re.search(r"Default\s+version\s+control:\s+send\s+version\s+(\d+),\s*receive\s+version\s+(\d+)", rip_protocol_block, re.IGNORECASE)
                if send_ver_m and rip["version"] is None:
                    rip["version"] = int(send_ver_m.group(1))

                # 2.3.2.5.5.4 - Participating Interfaces with send/recv versions
                iface_header_m = re.search(
                    r"Interface\s+Send\s+Recv[^\n]*\n((?:\s+\S+\s+\d+\s+\d+[^\n]*\n?)+)",
                    rip_protocol_block, re.IGNORECASE
                )
                if iface_header_m:
                    iface_lines = iface_header_m.group(1)
                    for ifl in iface_lines.strip().split("\n"):
                        ifl = ifl.strip()
                        ifm = re.match(r"(\S+)\s+(\d+)\s+(\d+)", ifl)
                        if ifm:
                            rip["participating_interfaces"].append({
                                "name": ifm.group(1),
                                "send": ifm.group(2),
                                "recv": ifm.group(3),
                            })
                            if ifm.group(1) not in rip["interfaces"]:
                                rip["interfaces"].append(ifm.group(1))

                # 2.3.2.5.5.2 - Routing for Networks (from show ip protocols)
                routing_for_m = re.search(
                    r"Routing\s+for\s+Networks:\s*\n(.*?)(?:\n\s*(?:Passive|Routing\s+Information|Default\s+version|Maximum|Automatic|Distance)|\n\s*\n)",
                    rip_protocol_block, re.IGNORECASE | re.DOTALL
                )
                if routing_for_m:
                    for nl in routing_for_m.group(1).strip().split("\n"):
                        net = nl.strip().rstrip("/")
                        if re.match(r"^\d+\.\d+\.\d+\.\d+(?:/\d+)?$", net) and net not in rip["advertised_networks"]:
                            rip["advertised_networks"].append(net)

                # 2.3.2.5.5.5 - Auto-summary from show ip protocols
                auto_m = re.search(r"Automatic\s+network\s+summarization\s+is\s+(in\s+effect|not\s+in\s+effect)", rip_protocol_block, re.IGNORECASE)
                if auto_m:
                    rip["auto_summary"] = "not" not in auto_m.group(1).lower()

                # 2.3.2.5.5.5 - Passive interfaces from show ip protocols
                passive_section_m = re.search(
                    r"Passive\s+Interface\(s\):\s*\n(.*?)(?:\n\s*(?:Routing|Default|Maximum|Distance|Address)|\n\s*\n)",
                    rip_protocol_block, re.IGNORECASE | re.DOTALL
                )
                if passive_section_m:
                    for pl in passive_section_m.group(1).strip().split("\n"):
                        iface = pl.strip()
                        if iface and re.match(r"^[A-Za-z]", iface) and iface not in rip["passive_interfaces"]:
                            rip["passive_interfaces"].append(iface)

                # 2.3.2.5.5.6 - Timers
                update_m = re.search(r"Sending\s+updates\s+every\s+(\d+)\s+seconds", rip_protocol_block, re.IGNORECASE)
                if update_m:
                    rip["timers"]["update"] = int(update_m.group(1))
                inv_m = re.search(r"Invalid\s+after\s+(\d+)\s+seconds", rip_protocol_block, re.IGNORECASE)
                if inv_m:
                    rip["timers"]["invalid"] = int(inv_m.group(1))
                hold_m = re.search(r"hold\s*down\s+(\d+)", rip_protocol_block, re.IGNORECASE)
                if hold_m:
                    rip["timers"]["hold"] = int(hold_m.group(1))
                    rip["timers"]["hold_down"] = int(hold_m.group(1))
                flush_m = re.search(r"flushed\s+after\s+(\d+)", rip_protocol_block, re.IGNORECASE)
                if flush_m:
                    rip["timers"]["flush"] = int(flush_m.group(1))

                # 2.3.2.5.5.7 - Administrative Distance
                dist_m = re.search(r"(?:Default\s+)?[Dd]istance.*?(\d+)", rip_protocol_block, re.IGNORECASE)
                if dist_m:
                    rip["admin_distance"] = int(dist_m.group(1))

                # Fallback interfaces
                if not rip["participating_interfaces"]:
                    on_m = re.search(
                        r"Sending\s+updates\s+every\s+\d+\s+seconds[^.]*\.\s*on\s+([^\n]+)",
                        rip_protocol_block, re.IGNORECASE | re.DOTALL
                    )
                    if on_m:
                        if_str = on_m.group(1).strip()
                        for iname in re.split(r"[\s,]+", if_str):
                            iname = iname.strip()
                            if iname and re.match(r"^(Gi|Fa|Eth|Te|Se|Lo|Vl|Serial|GigabitEthernet|FastEthernet|Loopback|Vlan)", iname, re.IGNORECASE):
                                rip["participating_interfaces"].append({
                                    "name": iname,
                                    "send": str(rip["version"] or ""),
                                    "recv": str(rip["version"] or ""),
                                })
                                if iname not in rip["interfaces"]:
                                    rip["interfaces"].append(iname)

        # --- Source 3: Routing table (filtered for RIP 'R') ---
        # Prioritize show ip route; fallback to show ip route rip
        rip_data_source = route_block if route_block else _get_section(content, r"show\s+ip\s+route\s+rip")
        if rip_data_source:
            for line in rip_data_source.split("\n"):
                line_strip = line.strip()
                # 2.3.2.5.5.3 - Learned routes (Network, [AD/Metric], Next-hop, Uptime, Interface)
                # Format: R 10.10.1.0/30 [120/1] via 10.20.1.2, 00:00:20, GigabitEthernet0/0
                m = re.match(
                    r"^\s*[R*]+\s+([\d.]+(?:/\d+)?)\s+\[(\d+)/(\d+)\]\s+via\s+([\d.]+)(?:,\s*(\d+:\d+:\d+))?(?:,\s*(\S+))?",
                    line_strip
                )
                if m:
                    rip["learned_routes"].append({
                        "network": m.group(1),
                        "admin_distance": int(m.group(2)),
                        "hop_count": int(m.group(3)),
                        "next_hop": m.group(4),
                        "uptime": m.group(5) or "",
                        "interface": m.group(6) or "",
                    })

        if not rip["learned_routes"]:
            for r in routes:
                if (r.get("protocol") or "").upper() == "R":
                    rip["learned_routes"].append({
                        "network": r.get("network", ""),
                        "admin_distance": r.get("distance"),
                        "hop_count": r.get("metric"),
                        "next_hop": r.get("next_hop", ""),
                        "uptime": "",
                    })

        if rip["admin_distance"] is None and rip_found:
            rip["admin_distance"] = 120

        # Sync legacy interfaces
        if not rip["interfaces"] and rip["participating_interfaces"]:
            rip["interfaces"] = [p["name"] for p in rip["participating_interfaces"]]

        result = {"routes": routes, "ospf": ospf, "eigrp": eigrp, "bgp": bgp, "rip": rip}
        if rip_found:
            result["rip_v2_info"] = rip
        return result

    def _normalize_neighbor_device_name(self, name: str) -> str:
        """Remove domain suffix for display (e.g. CORE1.lab.local -> CORE1). Keeps FQDN if no dot after hostname."""
        if not name or not isinstance(name, str):
            return name
        s = name.strip()
        if "." in s:
            return s.split(".")[0]
        return s

    def _parse_capabilities_string(self, cap_str: str) -> List[str]:
        """Parse 'Router Source-Route-Bridge' or 'Switch IGMP' into list ['Router', 'Switch', 'IGMP']."""
        if not cap_str or not isinstance(cap_str, str):
            return []
        # Split on spaces; filter empty; capitalize first letter per token
        parts = [p.strip() for p in cap_str.split() if p.strip()]
        return parts

    def _parse_cdp_neighbors_detail(self, detail_text: str) -> List[Dict[str, Any]]:
        """Parse 'show cdp neighbors detail'. Split by separator line, extract 7 fields per neighbor."""
        neighbors: List[Dict[str, Any]] = []
        blocks = re.split(r"-------------------------", detail_text)
        for block in blocks:
            block = block.strip()
            if not block or "Device ID:" not in block:
                continue
            dev_m = re.search(r"Device\s+ID:\s*([^\n\r]+)", block, re.IGNORECASE)
            if not dev_m:
                continue
            device_id_raw = dev_m.group(1).strip()
            neighbor_device_name = device_id_raw
            neighbor_name_normalized = self._normalize_neighbor_device_name(device_id_raw)

            ip_m = re.search(r"IP\s+address:\s*(\d+\.\d+\.\d+\.\d+)", block, re.IGNORECASE)
            neighbor_ip = ip_m.group(1) if ip_m else None

            plat_m = re.search(r"Platform:\s*([^,\n]+)", block, re.IGNORECASE)
            platform = (plat_m.group(1).strip().rstrip(",") if plat_m else None) or None

            intf_port_m = re.search(r"Interface:\s*(\S+),\s*Port\s+ID\s*\(outgoing\s+port\):\s*(\S+)", block, re.IGNORECASE)
            if not intf_port_m:
                intf_m = re.search(r"Interface:\s*(\S+)", block, re.IGNORECASE)
                port_m = re.search(r"Port\s+ID\s*\(outgoing\s+port\):\s*(\S+)", block, re.IGNORECASE)
                local_port_raw = intf_m.group(1) if intf_m else None
                remote_port_raw = port_m.group(1) if port_m else None
            else:
                local_port_raw = intf_port_m.group(1)
                remote_port_raw = intf_port_m.group(2)
            local_port = _canonical_interface_name(local_port_raw) if local_port_raw else None
            remote_port = _canonical_interface_name(remote_port_raw) if remote_port_raw else None

            cap_m = re.search(r"Capabilities:\s*([^\n]+)", block, re.IGNORECASE)
            capabilities_raw = (cap_m.group(1).strip() if cap_m else "") or ""
            capabilities = self._parse_capabilities_string(capabilities_raw)

            rec = {
                "neighbor_device_name": neighbor_name_normalized,
                "neighbor_ip": neighbor_ip,
                "platform": platform,
                "local_port": local_port,
                "remote_port": remote_port,
                "capabilities": capabilities,
                "discovery_protocol": "CDP",
                "neighbor_id": device_id_raw,
                "local_interface": local_port,
                "remote_interface": remote_port,
                "ip_address": neighbor_ip,
            }
            neighbors.append(rec)
        return neighbors

    def _parse_lldp_neighbors_detail(self, detail_text: str) -> List[Dict[str, Any]]:
        """Parse 'show lldp neighbors detail'. Separator is long dash line; System Name, Management IP, Local Intf, Port id."""
        neighbors: List[Dict[str, Any]] = []
        blocks = re.split(r"------------------------------------------------", detail_text)
        for block in blocks:
            block = block.strip()
            if not block or "Local Intf:" not in block:
                continue
            sys_m = re.search(r"System\s+[Nn]ame:\s*([^\n\r]+)", block, re.IGNORECASE)
            neighbor_device_name = (sys_m.group(1).strip() if sys_m else None) or None
            neighbor_name_normalized = self._normalize_neighbor_device_name(neighbor_device_name) if neighbor_device_name else None

            ip_m = re.search(r"IP:\s*(\d+\.\d+\.\d+\.\d+)", block, re.IGNORECASE)
            if not ip_m:
                ip_m = re.search(r"Management\s+[Aa]ddress(?:es)?:\s*\n\s*IP:\s*(\d+\.\d+\.\d+\.\d+)", block, re.IGNORECASE | re.MULTILINE)
            neighbor_ip = ip_m.group(1) if ip_m else None

            local_m = re.search(r"Local\s+[Ii]ntf:\s*(\S+)", block, re.IGNORECASE)
            port_m = re.search(r"Port\s+id:\s*(\S+)", block, re.IGNORECASE)
            local_port_raw = local_m.group(1) if local_m else None
            remote_port_raw = port_m.group(1) if port_m else None
            local_port = _canonical_interface_name(local_port_raw) if local_port_raw else None
            remote_port = _canonical_interface_name(remote_port_raw) if remote_port_raw else None

            cap_m = re.search(r"(?:System\s+)?[Cc]apabilities:\s*([^\n]+)", block, re.IGNORECASE)
            cap_str = (cap_m.group(1).strip() if cap_m else "") or ""
            enabled_m = re.search(r"Enabled\s+[Cc]apabilities:\s*([^\n]+)", block, re.IGNORECASE)
            if enabled_m:
                cap_str = enabled_m.group(1).strip() or cap_str
            capabilities = self._parse_capabilities_string(cap_str.replace(",", " "))

            if not neighbor_device_name and not local_port:
                continue
            rec = {
                "neighbor_device_name": neighbor_name_normalized or neighbor_device_name,
                "neighbor_ip": neighbor_ip,
                "platform": None,
                "local_port": local_port,
                "remote_port": remote_port,
                "capabilities": capabilities,
                "discovery_protocol": "LLDP",
                "neighbor_id": neighbor_device_name,
                "local_interface": local_port,
                "remote_interface": remote_port,
                "ip_address": neighbor_ip,
            }
            neighbors.append(rec)
        return neighbors

    def extract_neighbors(self, content: str) -> List[Dict[str, Any]]:
        """2.3.2.6 - Neighbor & Topology: neighbor_device_name, neighbor_ip, platform, local_port, remote_port, capabilities, discovery_protocol. Source: show cdp/lldp neighbors detail."""
        neighbors: List[Dict[str, Any]] = []
        seen_key: set = set()

        def _add_unique(n: Dict[str, Any]) -> None:
            key = (n.get("local_port"), n.get("neighbor_device_name") or n.get("neighbor_id"), n.get("discovery_protocol"))
            if key in seen_key:
                return
            seen_key.add(key)
            neighbors.append(n)

        cdp_block = _get_section(content, r"show\s+cdp\s+neighbors\s+detail")
        if not cdp_block:
            cdp_block = re.search(r"show\s+cdp\s+neighbors\s+detail\s*(.*?)(?=\n\s*\S+#|\n\s*\S+>|show\s+lldp|$)", content, re.IGNORECASE | re.DOTALL)
            cdp_block = (cdp_block.group(1) or "").strip() if cdp_block else ""
        if cdp_block:
            for n in self._parse_cdp_neighbors_detail(cdp_block):
                _add_unique(n)

        if not neighbors:
            brief = _get_section(content, r"show\s+cdp\s+neighbors(?!\s+detail)")
            if brief:
                for line in brief.split("\n"):
                    if re.match(r"^(Device|Capability|-----)", line, re.IGNORECASE):
                        continue
                    parts = line.split()
                    if len(parts) >= 4 and re.search(r"(Gi|Fa|Eth|Te|Se|Lo|Vl|Po)", parts[1], re.IGNORECASE):
                        local_port = _canonical_interface_name(parts[1])
                        rec = {
                            "neighbor_device_name": self._normalize_neighbor_device_name(parts[0]),
                            "neighbor_ip": "Unknown",
                            "platform": parts[-2] if len(parts) > 4 else None,
                            "local_port": local_port,
                            "remote_port": _canonical_interface_name(parts[-1]) if len(parts) >= 4 else None,
                            "capabilities": [],
                            "discovery_protocol": "CDP",
                            "neighbor_id": parts[0],
                            "local_interface": local_port,
                            "remote_interface": parts[-1] if len(parts) >= 4 else None,
                            "ip_address": "Unknown",
                        }
                        _add_unique(rec)
        lldp_block = _get_section(content, r"show\s+lldp\s+neighbors\s+detail")
        if not lldp_block:
            lldp_block = re.search(r"show\s+lldp\s+neighbors\s+detail\s*(.*?)(?=\n\s*\S+#|\n\s*\S+>|show\s+|$)", content, re.IGNORECASE | re.DOTALL)
            lldp_block = (lldp_block.group(1) or "").strip() if lldp_block else ""
        if lldp_block:
            for n in self._parse_lldp_neighbors_detail(lldp_block):
                _add_unique(n)
        return neighbors
    
    def extract_mac_arp(self, content: str) -> Dict[str, Any]:
        """2.3.2.7 - MAC & ARP tables; filter headers (Vlan, Mac Address, Type, Interface, ----, Total)."""
        arp_entries: List[Dict[str, Any]] = []
        mac_entries: List[Dict[str, Any]] = []
        
        # ARP skip: header lines that contain "Protocol" "Address" together (header row)
        def _skip_arp(line: str) -> bool:
            line_lower = line.lower()
            if not line.strip():
                return True
            if "protocol" in line_lower and "address" in line_lower:
                return True
            if line.strip().startswith("---"):
                return True
            return False
        
        # MAC skip: generic headers
        _skip_mac = lambda line: any(kw in line for kw in ("Vlan", "Mac Address", "Type", "Interface", "----", "Total")) or not line.strip()
        
        # show ip arp: Internet  IP  Age  Hardware Addr  Type  Interface
        arp_block = _get_section(content, r"show\s+ip\s+arp") or _get_section(content, r"show\s+arp")
        if arp_block:
            for line in arp_block.split("\n"):
                if _skip_arp(line):
                    continue
                # Pattern: Internet  IP  Age(or -)  MAC  Type  Interface
                m = re.search(r"Internet\s+(\d+\.\d+\.\d+\.\d+)\s+(-|\d+)\s+([0-9a-fA-F\.\-:]+)\s+(\w+)\s+(\S+)", line, re.IGNORECASE)
                if m:
                    ip_addr, age, hw, typ, iface = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
                    # Skip incomplete entries
                    if hw.lower() == "incomplete":
                        continue
                    # Validate MAC has at least 12 hex chars (ignoring separators)
                    mac_clean = re.sub(r'[.\-:]', '', hw)
                    if not re.match(r'^[0-9a-fA-F]{12,}$', mac_clean):
                        continue
                    arp_entries.append({"ip_address": ip_addr, "age": age, "mac_address": hw, "type": typ, "interface": iface})
        # show mac address-table: VLAN MAC Type Port
        mac_block = _get_section(content, r"show\s+mac(?:\s+address-table|address-table)")
        if not mac_block:
            mac_block = _get_section(content, r"show\s+mac\s+address-table")
        if mac_block:
            for line in mac_block.split("\n"):
                if _skip_mac(line):
                    continue
                m = re.search(r"^\s*(\d+)\s+([0-9a-fA-F\.\-:]+)\s+(\w+)\s+(\S+)", line)
                if m:
                    vlan_s, mac, typ, port = m.group(1), m.group(2), m.group(3), m.group(4)
                    if vlan_s.lower() == "vlan":
                        continue
                    # Validate MAC has at least 12 hex chars
                    mac_clean = re.sub(r'[.\-:]', '', mac)
                    if not re.match(r'^[0-9a-fA-F]{12,}$', mac_clean):
                        continue
                    try:
                        vlan = int(vlan_s)
                    except ValueError:
                        continue
                    mac_entries.append({"vlan": vlan, "mac_address": mac, "type": typ, "port": port})
        return {"arp_entries": arp_entries, "mac_entries": mac_entries}
    
    def extract_security(self, content: str) -> Dict[str, Any]:
        """2.3.2.8 - security_mgmt: ssh, users (username privilege N), ntp, snmp, logging host, acls (names/IDs), aaa."""
        sec: Dict[str, Any] = {
            "ssh_enabled": False,
            "ssh_version": None,
            "users": [],
            "ntp_servers": [],
            "snmp_enabled": False,
            "logging_host": None,
            "acls": [],
            "aaa_protocols": [],
        }
        if "transport input ssh" in content.lower() or "transport input telnet ssh" in content.lower():
            sec["ssh_enabled"] = True
        ver_m = re.search(r"ip\s+ssh\s+version\s+(\d+)", content, re.IGNORECASE)
        if ver_m:
            sec["ssh_version"] = ver_m.group(1)
            sec["ssh_enabled"] = True
        for m in re.finditer(r"username\s+(\S+)\s+privilege\s+(\d+)", content, re.IGNORECASE):
            sec["users"].append({"username": m.group(1), "privilege": int(m.group(2))})
        for m in re.finditer(r"username\s+(\S+)\s+(?:secret|password)", content, re.IGNORECASE):
            if not any(u.get("username") == m.group(1) for u in sec["users"]):
                sec["users"].append({"username": m.group(1), "privilege": 1})
        for m in re.finditer(r"ntp\s+server\s+(\S+)", content, re.IGNORECASE):
            sec["ntp_servers"].append(m.group(1))
        if "snmp-server" in content.lower():
            sec["snmp_enabled"] = True
        log_m = re.search(r"logging\s+host\s+(\S+)", content, re.IGNORECASE)
        if log_m:
            sec["logging_host"] = log_m.group(1)
        for m in re.finditer(r"(?:ip\s+)?access-list\s+(?:standard|extended)\s+(\S+)", content, re.IGNORECASE):
            acl = m.group(1)
            if acl not in sec["acls"]:
                sec["acls"].append(acl)
        for m in re.finditer(r"access-list\s+(\d+)\s+\w+", content, re.IGNORECASE):
            acl = m.group(1)
            if acl not in sec["acls"]:
                sec["acls"].append(acl)
        for m in re.finditer(r"ip\s+access-group\s+(\S+)\s+\w+", content, re.IGNORECASE):
            acl = m.group(1)
            if acl not in sec["acls"]:
                sec["acls"].append(acl)
        for m in re.finditer(r"aaa\s+authentication\s+(\S+)", content, re.IGNORECASE):
            p = m.group(1)
            if p not in sec["aaa_protocols"]:
                sec["aaa_protocols"].append(p)
        return sec

    def extract_security_audit(self, content: str) -> Dict[str, Any]:
        """2.3.2.8 - security_audit: never null. Use Enabled/Disabled, [] or None for missing."""
        cfg = content.lower()
        audit: Dict[str, Any] = {
            "ssh": {"status": "Disabled", "version": "2"},
            "telnet": {"status": "Disabled"},
            "aaa": {"status": "Disabled", "protocols": []},
            "snmp": {"status": "Disabled", "version": None, "communities": []},
            "ntp": {"servers": [], "status": "None"},
            "logging": {"syslog_servers": [], "console_logging": False},
            "acls": [],
        }
        # SSH (2.3.2.8.3): Enabled if transport input ssh OR ip ssh version anywhere; Version from ip ssh version (\d)
        try:
            ver_m = re.search(r"ip\s+ssh\s+version\s+(\d)", content, re.IGNORECASE)
            if ver_m:
                audit["ssh"]["version"] = ver_m.group(1)
            if "transport input ssh" in cfg or "transport input telnet ssh" in cfg or "ip ssh version" in cfg:
                audit["ssh"]["status"] = "Enabled"
                if not audit["ssh"]["version"]:
                    audit["ssh"]["version"] = "2"
        except Exception:
            pass
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
        # SNMP: if snmp-server lines exist extract community; else Disabled
        for m in re.finditer(r"snmp-server\s+community\s+(\S+)", content, re.IGNORECASE):
            audit["snmp"]["communities"].append(m.group(1))
        if audit["snmp"]["communities"] or "snmp-server" in cfg:
            audit["snmp"]["status"] = "Enabled"
            audit["snmp"]["version"] = "v3" if ("snmp-server group" in cfg and "v3" in cfg) else "v2c"
        else:
            audit["snmp"]["status"] = "Disabled"
        # NTP: servers from config; sync_status from show ntp status (2.3.2.8.5)
        for m in re.finditer(r"ntp\s+server\s+(\S+)", content, re.IGNORECASE):
            s = m.group(1)
            if re.match(r"\d+\.\d+\.\d+\.\d+", s) and s not in audit["ntp"]["servers"]:
                audit["ntp"]["servers"].append(s)
        if audit["ntp"]["servers"]:
            audit["ntp"]["status"] = "Configured"
        ntp_status_block = _get_section(content, r"show\s+ntp\s+status")
        if not ntp_status_block:
            ntp_status_block = re.search(r"show\s+ntp\s+status\s*(.*?)(?=\n\s*\S+#|\n\s*\S+>|$)", content, re.IGNORECASE | re.DOTALL)
            ntp_status_block = (ntp_status_block.group(1) or "").strip() if ntp_status_block else ""
        if ntp_status_block:
            ntp_lower = ntp_status_block.lower()
            if "clock is synchronized" in ntp_lower:
                audit["ntp"]["sync_status"] = "synchronized"
            elif "clock is unsynchronized" in ntp_lower or "clock is 'nset'" in ntp_lower:
                audit["ntp"]["sync_status"] = "unsynchronized"
            else:
                audit["ntp"]["sync_status"] = "unsynchronized"
        else:
            audit["ntp"]["sync_status"] = "unknown"
        if not audit["ntp"].get("status") or audit["ntp"]["status"] == "None":
            if audit["ntp"].get("sync_status") == "synchronized":
                audit["ntp"]["status"] = "Synchronized"
            elif audit["ntp"].get("sync_status") == "unsynchronized":
                audit["ntp"]["status"] = "Unsynchronized"
        # Logging (2.3.2.8.6): show logging block for Syslog enabled and console level
        show_logging_block = _get_section(content, r"show\s+logging")
        if not show_logging_block:
            show_logging_block = re.search(r"show\s+logging\s*(.*?)(?=\n\s*\S+#|\n\s*\S+>|$)", content, re.IGNORECASE | re.DOTALL)
            show_logging_block = (show_logging_block.group(1) or "").strip() if show_logging_block else ""
        if show_logging_block:
            if re.search(r"^\s*Syslog\s+logging:\s+enabled\b", show_logging_block, re.IGNORECASE | re.MULTILINE):
                audit["logging"]["syslog_enabled"] = True
            console_level_m = re.search(r"Console\s+logging:\s+level\s+(\w+)", show_logging_block, re.IGNORECASE)
            if console_level_m:
                audit["logging"]["console_level"] = console_level_m.group(1).strip().lower()
        for m in re.finditer(r"logging\s+host\s+(\d+\.\d+\.\d+\.\d+|\S+)", content, re.IGNORECASE):
            audit["logging"]["syslog_servers"].append(m.group(1))
        if "logging console" in cfg and "no logging console" not in cfg:
            audit["logging"]["console_logging"] = True
        if not audit["logging"].get("syslog_enabled") and audit["logging"].get("syslog_servers"):
            audit["logging"]["syslog_enabled"] = True
        # ACLs (2.3.2.8.7): name, type (Standard/Extended), rules[] - full rule text per ACL
        config_block = _get_section(content, r"show\s+running-config") or content
        acl_by_name: Dict[str, Dict[str, Any]] = {}

        # 1) Numbered ACLs: access-list <id> <permit|deny> ...
        for m in re.finditer(r"access-list\s+(\d+)\s+(permit|deny)\s+(.+)", config_block, re.IGNORECASE):
            acl_id = m.group(1)
            action = (m.group(2) or "").strip().lower()
            rest = (m.group(3) or "").strip()
            rule_text = f"{action} {rest}".strip()
            if acl_id not in acl_by_name:
                try:
                    num = int(acl_id)
                    acl_type = "Standard" if 1 <= num <= 99 else "Extended"
                except ValueError:
                    acl_type = "Extended"
                acl_by_name[acl_id] = {"name": acl_id, "type": acl_type, "rules": []}
            acl_by_name[acl_id]["rules"].append(rule_text)

        # 2) Named ACLs: ip access-list standard|extended <name> ... then indented permit/deny lines
        named_blocks = re.finditer(
            r"ip\s+access-list\s+(standard|extended)\s+(\S+)\s*\n(.*?)(?=\n(?:ip\s+access-list\s|access-list\s+\d+|interface\s+|router\s+|line\s+|!\s*$|end\s*$)|$)",
            config_block,
            re.IGNORECASE | re.DOTALL,
        )
        for nb in named_blocks:
            kind, name, block = (nb.group(1) or "").strip(), (nb.group(2) or "").strip(), (nb.group(3) or "").strip()
            acl_type = "Standard" if kind.lower() == "standard" else "Extended"
            rules: List[str] = []
            for line in block.splitlines():
                line = line.strip()
                if not line or line.startswith("!"):
                    continue
                rule_m = re.match(r"^(permit|deny)\s+(.+)$", line, re.IGNORECASE)
                if rule_m:
                    rules.append(f"{rule_m.group(1).lower()} {rule_m.group(2).strip()}".strip())
            if name not in acl_by_name:
                acl_by_name[name] = {"name": name, "type": acl_type, "rules": []}
            acl_by_name[name]["rules"] = rules

        # Referenced ACLs (ip access-group X in/out) not yet in acl_by_name: add with empty rules
        for m in re.finditer(r"ip\s+access-group\s+(\S+)\s+\w+", config_block, re.IGNORECASE):
            acl_id = m.group(1)
            if acl_id not in acl_by_name:
                try:
                    num = int(acl_id)
                    acl_type = "Standard" if 1 <= num <= 99 else "Extended"
                except ValueError:
                    acl_type = "Extended"
                acl_by_name[acl_id] = {"name": acl_id, "type": acl_type, "rules": []}
        audit["acls"] = list(acl_by_name.values())
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
            "acls": [{"name": a, "type": "Extended", "rules": []} for a in (sec.get("acls") or [])],
        }

    def _decode_etherchannel_flags(self, flags: str) -> str:
        """Decode Cisco etherchannel summary flags. S=Layer2, R=Layer3, U=In Use, D=Down, s=Suspended."""
        if not flags:
            return "Unknown"
        parts: List[str] = []
        f = flags.upper()
        if "S" in f:
            parts.append("Layer2")
        if "R" in f:
            parts.append("Layer3")
        if "U" in f:
            parts.append("In Use")
        if "D" in f:
            parts.append("Down")
        if "s" in flags:
            parts.append("Suspended")
        return ", ".join(parts) if parts else "Up"

    def _decode_member_port_status(self, member_flags: str) -> str:
        """Decode member port flags: P = Bundled in port-channel, D = Down, s = Suspended, etc."""
        if not member_flags:
            return "Bundled"
        f = (member_flags or "").upper()
        if "P" in f:
            return "Bundled"
        if "D" in f:
            return "Down"
        if "s" in (member_flags or ""):
            return "Suspended"
        return "Up"

    def extract_ha(self, content: str) -> Dict[str, Any]:
        """2.3.2.9 - etherchannels (from show etherchannel summary), hsrp (show standby brief), vrrp (show vrrp brief/detail)."""
        ha: Dict[str, Any] = {"etherchannels": [], "hsrp": [], "vrrp": []}
        config_block = _get_section(content, r"show\s+running-config") or content
        if not config_block or not config_block.strip():
            config_block = content

        def _is_valid_ip(s: str) -> bool:
            return bool(s and re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", str(s)))

        # --- EtherChannel (2.3.2.9.1): show etherchannel summary ---
        ec_show = _get_section(content, r"show\s+etherchannel\s+summary")
        if ec_show:
            for line in ec_show.splitlines():
                line_strip = line.strip()
                if not line_strip or "Group" in line and "Port-channel" in line or "Number of" in line or "Flags:" in line or line_strip.startswith("------"):
                    continue
                ec_m = re.match(r"^\s*(\d+)\s+(Po\d+)\(([^)]*)\)\s+(\S+)\s+(.*)$", line)
                if ec_m:
                    grp_id = int(ec_m.group(1))
                    po_name = ec_m.group(2)
                    flags = ec_m.group(3)
                    protocol = (ec_m.group(4) or "").strip()
                    rest = (ec_m.group(5) or "").strip()
                    status = self._decode_etherchannel_flags(flags)
                    member_entries = re.findall(r"(Gi\d+/\d+|Fa\d+/\d+|Te\d+/\d+|Ethernet\d+/\d+)(?:\(([^)]*)\))?", rest, re.IGNORECASE)
                    members = []
                    for port_part, mflags in member_entries:
                        iface_short = port_part
                        members.append({"interface": iface_short, "status": self._decode_member_port_status(mflags)})
                    if not members:
                        raw = re.findall(r"(Gi\d+/\d+|Fa\d+/\d+|Te\d+/\d+)(?:\([^)]*\))?", rest, re.IGNORECASE)
                        members = [{"interface": p, "status": "Bundled"} for p in raw]
                    ha["etherchannels"].append({
                        "group": grp_id,
                        "name": po_name,
                        "protocol": protocol,
                        "status": status,
                        "members": members,
                    })
        if not ha["etherchannels"]:
            pc_ids = set()
            for m in re.finditer(r"interface\s+Port-channel\s*(\d+)", config_block, re.IGNORECASE):
                try:
                    pc_ids.add(int(m.group(1)))
                except ValueError:
                    pass
            for grp_id in sorted(pc_ids):
                members = []
                proto = "LACP"
                for m2 in re.finditer(r"interface\s+(\S+)\s*\n(.*?)(?=\ninterface\s+|$)", config_block, re.IGNORECASE | re.DOTALL):
                    block = m2.group(2)
                    if f"channel-group {grp_id}" not in block.lower():
                        continue
                    iface_name = m2.group(1)
                    members.append({"interface": iface_name, "status": "Bundled"})
                    mode_m = re.search(r"channel-group\s+\d+\s+mode\s+(active|passive|on|desirable|auto)", block, re.IGNORECASE)
                    if mode_m:
                        mode = mode_m.group(1).upper()
                        proto = "LACP" if mode in ("ACTIVE", "PASSIVE") else "PAGP" if mode in ("DESIRABLE", "AUTO") else "Static"
                ha["etherchannels"].append({"group": grp_id, "name": f"Po{grp_id}", "protocol": proto, "status": "Up" if members else "Down", "members": members})

        # --- HSRP (2.3.2.9.2): show standby brief; extract priority and preempt ---
        show_standby = _get_section(content, r"show\s+standby\s+brief")
        if show_standby:
            for line in show_standby.splitlines():
                line_strip = line.strip()
                if not line_strip or line_strip.startswith("Interface") or line_strip.startswith("Grp") or "P indicates" in line or "Virtual IP" in line and "Active" in line:
                    continue
                # Interface Grp Pri P State Active Standby Virtual IP  -> P is optional (preempt)
                m = re.match(r"^(\S+)\s+(\d+)\s+(\d+)\s+(P)?\s*(\S+)\s+(\S+)\s+(\S+)\s+(\d+\.\d+\.\d+\.\d+)\s*$", line_strip)
                if m:
                    iface, grp, pri, preempt_char, state, active, standby, vip = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4), m.group(5), m.group(6), m.group(7), m.group(8)
                    if _is_valid_ip(vip):
                        ha["hsrp"].append({
                            "interface": iface,
                            "group": grp,
                            "virtual_ip": vip,
                            "state": state,
                            "priority": pri,
                            "preempt": preempt_char == "P",
                        })
        if not ha["hsrp"]:
            for m in re.finditer(r"standby\s+(\d+)\s+ip\s+(\d+\.\d+\.\d+\.\d+)", content, re.IGNORECASE):
                if _is_valid_ip(m.group(2)):
                    ha["hsrp"].append({"interface": None, "group": int(m.group(1)), "virtual_ip": m.group(2), "state": None, "priority": None, "preempt": None})

        # --- VRRP (2.3.2.9.3): show vrrp brief / show vrrp detail (predictive) ---
        vrrp_brief = _get_section(content, r"show\s+vrrp\s+brief")
        if not vrrp_brief:
            vrrp_brief = re.search(r"show\s+vrrp\s+brief\s*(.*?)(?=\n\s*\S+#|\n\s*\S+>|$)", content, re.IGNORECASE | re.DOTALL)
            vrrp_brief = (vrrp_brief.group(1) or "").strip() if vrrp_brief else ""
        vrrp_detail = _get_section(content, r"show\s+vrrp\s+detail")
        if not vrrp_detail:
            vrrp_detail = re.search(r"show\s+vrrp(?:\s+detail)?\s*(.*?)(?=\n\s*\S+#|\n\s*\S+>|$)", content, re.IGNORECASE | re.DOTALL)
            vrrp_detail = (vrrp_detail.group(1) or "").strip() if vrrp_detail else ""

        if vrrp_brief:
            for line in vrrp_brief.splitlines():
                line_strip = line.strip()
                if not line_strip or "Interface" in line and "Grp" in line or "State" in line and "Master" in line:
                    continue
                m = re.match(r"^(\S+)\s+(\d+)\s+(\d+)\s+\S+\s+\S+\s+([YP]?)\s+(\w+)\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+)?", line_strip)
                if m:
                    iface, grp, pri, preempt_char, state, master_or_vip, group_addr = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4), m.group(5), m.group(6), m.group(7)
                    virtual_ip = group_addr if _is_valid_ip(group_addr) else master_or_vip
                    if _is_valid_ip(virtual_ip):
                        ha["vrrp"].append({"interface": iface, "group": grp, "virtual_ip": virtual_ip, "state": state, "priority": pri, "preempt": preempt_char in ("Y", "P")})
        elif vrrp_detail:
            current = {}
            for line in vrrp_detail.splitlines():
                line_strip = line.strip()
                grp_m = re.match(r"Group\s+(\d+)", line_strip, re.IGNORECASE)
                state_m = re.search(r"State\s+is\s+(\w+)", line_strip, re.IGNORECASE)
                vip_m = re.search(r"Virtual\s+IP\s+address\s+is\s+(\d+\.\d+\.\d+\.\d+)", line_strip, re.IGNORECASE)
                pri_m = re.search(r"Priority\s+(\d+)", line_strip, re.IGNORECASE)
                preempt_m = re.search(r"Preemption\s+(?:is\s+)?enabled", line_strip, re.IGNORECASE)
                if grp_m:
                    if current and current.get("group") is not None and _is_valid_ip(current.get("virtual_ip")):
                        ha["vrrp"].append(current)
                    current = {"group": int(grp_m.group(1)), "interface": None, "virtual_ip": None, "state": None, "priority": None, "preempt": False}
                if state_m:
                    current["state"] = state_m.group(1)
                if vip_m:
                    current["virtual_ip"] = vip_m.group(1)
                if pri_m:
                    current["priority"] = int(pri_m.group(1))
                if preempt_m:
                    current["preempt"] = True
            if current and current.get("group") is not None and _is_valid_ip(current.get("virtual_ip")):
                ha["vrrp"].append(current)
        else:
            for m in re.finditer(r"vrrp\s+(\d+)\s+ip\s+(\d+\.\d+\.\d+\.\d+)", content, re.IGNORECASE):
                if _is_valid_ip(m.group(2)):
                    ha["vrrp"].append({"interface": None, "group": int(m.group(1)), "virtual_ip": m.group(2), "state": None, "priority": None, "preempt": None})
        return ha

    def extract_high_availability(self, content: str, sections: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """2.3.2.9 - Config-only EtherChannel: build from interface Port-channel N + channel-group N mode (full content)."""
        config_block = _get_section(content, r"show\s+running-config") or content
        if not config_block or not config_block.strip():
            config_block = content
        ether_channels: List[Dict[str, Any]] = []
        pc_by_id: Dict[int, Dict[str, Any]] = {}
        try:
            for m in re.finditer(r"interface\s+(\S+)\s*\n(.*?)(?=\ninterface\s+|$)", config_block, re.IGNORECASE | re.DOTALL):
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
            # Only add if we found Port-channel definition (optional: some configs only have channel-group)
            for pc_m in re.finditer(r"interface\s+Port-channel\s*(\d+)", config_block, re.IGNORECASE):
                gid = int(pc_m.group(1))
                if gid not in pc_by_id:
                    pc_by_id[gid] = {"interface": f"Po{gid}", "protocol": "LACP", "members": [], "status": "Down"}
            ether_channels = list(pc_by_id.values())
        except Exception:
            pass
        return {"ether_channels": ether_channels}

    def _ha_from_legacy(self, ha: Dict[str, Any]) -> Dict[str, Any]:
        """Build high_availability from ha.etherchannels (group/name/protocol/status/members with interface)."""
        if not ha:
            return {"ether_channels": []}
        ec_list = []
        for e in ha.get("etherchannels") or []:
            name = e.get("name") or f"Po{e.get('group', e.get('id', 0))}"
            members_raw = e.get("members") or []
            if members_raw and isinstance(members_raw[0], dict):
                members = [m.get("interface", m.get("port", m)) if isinstance(m, dict) else m for m in members_raw]
            else:
                members = list(members_raw)
            ec_list.append({
                "interface": name,
                "protocol": (e.get("protocol") or e.get("mode") or "LACP").upper(),
                "members": members,
                "status": e.get("status") or ("Up" if members else "Down"),
            })
        return {"ether_channels": ec_list}


# Alias for backward compatibility; ConfigParser can use CiscoIOSParser.
CiscoParser = CiscoIOSParser
