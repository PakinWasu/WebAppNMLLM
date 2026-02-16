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
    return s


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
            ip_m = re.search(r"Internet\s+address\s+is\s+(\d+\.\d+\.\d+\.\d+/\d+)", block, re.IGNORECASE)
            if ip_m:
                out["ip_address"] = ip_m.group(1)
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
            "description": None,
            "ip_address": None,
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
                ip_m = re.search(r"ip\s+address\s+(\d+\.\d+\.\d+\.\d+\s+\d+\.\d+\.\d+\.\d+|\d+\.\d+\.\d+\.\d+/\d+)", block, re.IGNORECASE)
                if ip_m:
                    iface["ip_address"] = ip_m.group(1).strip()
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
                try:
                    acc_m = re.search(r"switchport\s+access\s+vlan\s+(\d+)", block, re.IGNORECASE)
                    if acc_m:
                        iface["access_vlan"] = int(acc_m.group(1))
                except Exception:
                    pass
            elif "switchport mode trunk" in block.lower():
                iface["mode"] = "trunk"
                try:
                    trunk_m = re.search(r"switchport\s+trunk\s+allowed\s+vlan\s+(.+)", block, re.IGNORECASE)
                    if trunk_m:
                        iface["allowed_vlans"] = trunk_m.group(1).strip()
                    native_m = re.search(r"switchport\s+trunk\s+native\s+vlan\s+(\d+)", block, re.IGNORECASE)
                    if native_m:
                        iface["native_vlan"] = int(native_m.group(1))
                except Exception:
                    pass
            elif "no switchport" in block.lower() or iface.get("ip_address"):
                iface["mode"] = "routed"
        # Source B: show ip interface brief - merge oper_status / admin_status (same key = update, no new row)
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
                iface = _get_or_create(name)
                if ip_val and ip_val != "unassigned":
                    iface["ip_address"] = ip_val if "/" in ip_val or " " in ip_val else ip_val
                if status:
                    iface["status"] = status.lower()
                if protocol:
                    iface["protocol"] = protocol.lower()
        # Deep parse: block-based extraction from "show interfaces" (Description, MAC, IP, MTU, BW, Duplex, Speed, Media, Encapsulation)
        deep_blocks = self._parse_show_interfaces_blocks(content)
        for name, data in deep_blocks.items():
            if name.startswith("Null") or "NULL" in name.upper():
                continue
            iface = _get_or_create(name)
            for k, v in data.items():
                if k == "name":
                    continue
                if v is not None and (v != "" or k in ("description",)):
                    iface[k] = v
        # show interfaces switchport for mode if not set (merge by canonical name)
        switchport = _get_section(content, r"show\s+interfaces\s+switchport")
        if switchport:
            for block in re.split(r"\n(?=\w)", switchport):
                name_m = re.search(r"Name\s*:\s*(\S+)", block, re.IGNORECASE)
                mode_m = re.search(r"Switchport\s+Mode[:\s]+(\w+)", block, re.IGNORECASE)
                if name_m and mode_m:
                    key = _canonical_interface_name(name_m.group(1))
                    if key in interfaces_dict and interfaces_dict[key].get("mode") is None:
                        mode_val = mode_m.group(1).lower()
                        if "access" in mode_val:
                            interfaces_dict[key]["mode"] = "access"
                        elif "trunk" in mode_val:
                            interfaces_dict[key]["mode"] = "trunk"
                        else:
                            interfaces_dict[key]["mode"] = "routed"
        return list(interfaces_dict.values())
    
    def extract_vlans(self, content: str) -> Dict[str, Any]:
        """2.3.2.3 - VLAN name, status, port memberships. Multi-source: config first, then show vlan / show vlan brief."""
        details_by_id: Dict[int, Dict[str, Any]] = {}
        access_ports: List[str] = []
        trunk_ports: List[Dict[str, Any]] = []
        config_block = _get_section(content, r"show\s+running-config") or content
        # Source 1 (Config): vlan <id> name <name>; interface blocks for access/trunk
        for m in re.finditer(r"vlan\s+(\d+)\s*\n(.*?)(?=\nvlan\s+|^end\s|$)", config_block, re.IGNORECASE | re.DOTALL):
            try:
                vid = int(m.group(1))
            except ValueError:
                continue
            block = m.group(2)
            name_m = re.search(r"name\s+(\S+)", block, re.IGNORECASE)
            if vid not in details_by_id:
                details_by_id[vid] = {"id": str(vid), "name": name_m.group(1) if name_m else str(vid), "status": "active", "ports": []}
        for m in re.finditer(r"interface\s+(\S+)\s*\n(.*?)(?=\ninterface\s+|^end\s|$)", config_block, re.IGNORECASE | re.DOTALL):
            iface_name, block = m.group(1), m.group(2)
            if "NULL" in (iface_name or "").upper():
                continue
            if "switchport mode access" in block.lower():
                access_ports.append(iface_name)
                acc_m = re.search(r"switchport\s+access\s+vlan\s+(\d+)", block, re.IGNORECASE)
                if acc_m and details_by_id.get(int(acc_m.group(1))) is not None:
                    details_by_id[int(acc_m.group(1))].setdefault("ports", []).append(iface_name)
            elif "switchport mode trunk" in block.lower():
                native_m = re.search(r"switchport\s+trunk\s+native\s+vlan\s+(\d+)", block, re.IGNORECASE)
                allow_m = re.search(r"switchport\s+trunk\s+allowed\s+vlan\s+(.+)", block, re.IGNORECASE)
                trunk_ports.append({
                    "port": iface_name,
                    "native_vlan": (native_m.group(1) if native_m else "1"),
                    "allowed_vlans": (allow_m.group(1).strip() if allow_m else "all"),
                })
        # Source 2 (Verbose): show vlan or show vlan brief - ^(\d+)\s+(\S+)\s+(active|act/lshut|suspend|act/unsup)
        # Skip header lines: VLAN, VID, Type, Ports, ----, etc. Do not parse "Vlan" as VLAN id.
        show_vlan = _get_section(content, r"show\s+vlan\s+brief") or _get_section(content, r"show\s+vlan\s")
        vlan_ids_seen_in_table = set()
        if show_vlan:
            status_re = re.compile(r"^(\d+)\s+(\S+)\s+(active|act/lshut|suspend|act/unsup)", re.IGNORECASE)
            lines = show_vlan.split("\n")
            i = 0
            while i < len(lines):
                line = lines[i]
                line_strip = line.strip()
                if line_strip.startswith("VLAN") or line_strip.startswith("VID") or line_strip.startswith("----") or (line_strip.startswith("Vlan") and not line_strip[4:5].isdigit()):
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
                    ports_str = line[mm.end():].strip() if mm.end() < len(line) else ""
                    i += 1
                    while i < len(lines) and lines[i].strip() and not status_re.match(lines[i].strip()) and re.search(r"Gi\d|Fa\d|Eth\d|Po\d", lines[i], re.IGNORECASE):
                        ports_str += " " + lines[i].strip()
                        i += 1
                    port_list = re.findall(r"(?:Gi|Fa|Eth|Po|GigabitEthernet|FastEthernet|Port-channel)\S*", ports_str, re.IGNORECASE)
                    vlan_ids_seen_in_table.add(vid)
                    if vid not in details_by_id:
                        details_by_id[vid] = {"id": str(vid), "name": name, "status": status, "ports": []}
                    else:
                        details_by_id[vid]["name"] = name
                        details_by_id[vid]["status"] = status
                    if port_list:
                        details_by_id[vid]["ports"] = list(dict.fromkeys(port_list))
                i += 1
        # Config-only VLANs: if show was parsed, set status to "Configured (Inactive)" when not in table
        if show_vlan and vlan_ids_seen_in_table:
            for vid, d in list(details_by_id.items()):
                try:
                    v = int(d["id"])
                    if v not in vlan_ids_seen_in_table and d.get("status") == "active":
                        d["status"] = "Configured (Inactive)"
                except (ValueError, TypeError):
                    pass
        vlan_list = [{"id": d["id"], "name": d["name"], "status": d.get("status", "active")} for d in sorted(details_by_id.values(), key=lambda d: int(d["id"]) if d["id"].isdigit() else 9999) if d["id"].isdigit()]
        details = [{"id": d["id"], "name": d["name"], "status": d.get("status", "active"), "ports": d.get("ports") or []} for d in sorted(details_by_id.values(), key=lambda d: int(d["id"]) if d["id"].isdigit() else 9999)]
        return {
            "vlan_list": vlan_list,
            "details": details,
            "access_ports": access_ports,
            "trunk_ports": trunk_ports,
            "total_count": len(details_by_id),
        }
    
    def extract_stp(self, content: str) -> Dict[str, Any]:
        """2.3.2.4 - Root Bridge, port roles/states, cost, priority; PortFast from config. Multi-source: config + show spanning-tree."""
        stp: Dict[str, Any] = {"mode": None, "root_bridges": [], "root_bridge_id": None, "interfaces": [], "portfast_enabled": None}
        config_block = _get_section(content, r"show\s+running-config") or content
        mode_m = re.search(r"spanning-tree\s+mode\s+(\S+)", config_block, re.IGNORECASE)
        if mode_m:
            stp["mode"] = mode_m.group(1).upper()
        if re.search(r"spanning-tree\s+portfast", config_block, re.IGNORECASE):
            stp["portfast_enabled"] = True
        show_stp = _get_section(content, r"show\s+spanning-tree")
        if not show_stp:
            show_stp = re.search(r"show\s+spanning-tree\s*(.*?)(?=\n\s*\S+#|\n\s*\S+>|$)", content, re.IGNORECASE | re.DOTALL)
            show_stp = (show_stp.group(1) or "").strip() if show_stp else ""
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
            # Port table (line-based): skip headers; regex ^(\S+)\s+(Desg|Root|Altn|Back)\s+(FWD|BLK|LRN)\s+(\d+)\s+(\d+\.\d+)
            port_line_re = re.compile(r"^(\S+)\s+(Desg|Root|Altn|Back)\s+(FWD|BLK|LRN)\s+(\d+)\s+(\d+\.\d+)", re.IGNORECASE)
            for line in show_stp.split("\n"):
                line_strip = line.strip()
                if not line_strip or line_strip.startswith("Port") and "Role" in line_strip or line_strip.startswith("----"):
                    continue
                pm = port_line_re.match(line_strip)
                if pm:
                    port_name, role, state = pm.group(1), pm.group(2), pm.group(3)
                    cost_val = int(pm.group(4)) if pm.group(4).isdigit() else None
                    prio_val = float(pm.group(5)) if pm.group(5) else None
                    rec = {"port": port_name, "role": role, "state": state}
                    if cost_val is not None:
                        rec["cost"] = cost_val
                    if prio_val is not None:
                        rec["priority"] = int(prio_val)
                    if not any(x.get("port") == port_name for x in stp["interfaces"]):
                        stp["interfaces"].append(rec)
            # Fallback: block-style "Port N (Gi0/0) of VLAN0001 is designated forwarding"
            if not stp["interfaces"]:
                port_block_re = re.compile(r"Port\s+\d+\s+\((\S+)\)\s+of\s+VLAN\d+\s+is\s+(\w+)\s+(\w+)", re.IGNORECASE)
                for pm in port_block_re.finditer(show_stp):
                    port_name = pm.group(1)
                    role_raw = (pm.group(2) or "").lower()
                    state_raw = (pm.group(3) or "").lower()
                    role = "Desg" if "designated" in role_raw or "desg" in role_raw else "Root" if "root" in role_raw else "Altn" if "alternate" in role_raw else "Back" if "backup" in role_raw else role_raw[:4].capitalize()
                    state = "FWD" if "forward" in state_raw else "BLK" if "block" in state_raw else "LRN" if "learn" in state_raw else state_raw[:3].upper()
                    cost_m = re.search(re.escape(port_name) + r".*?Port\s+path\s+cost\s+(\d+)", show_stp, re.IGNORECASE | re.DOTALL)
                    prio_m = re.search(re.escape(port_name) + r".*?Port\s+priority\s+(\d+)", show_stp, re.IGNORECASE | re.DOTALL)
                    edge_m = re.search(re.escape(port_name) + r".*?Edge\s+P2p|portfast", show_stp, re.IGNORECASE | re.DOTALL)
                    rec = {"port": port_name, "role": role, "state": state}
                    if cost_m:
                        rec["cost"] = int(cost_m.group(1))
                    if prio_m:
                        rec["priority"] = int(prio_m.group(1))
                    if edge_m:
                        rec["edge_p2p"] = True
                    stp["interfaces"].append(rec)
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
        # Static from config: ip route <network> <mask> <next_hop> [ad] [interface]; AD default 1
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
            routes.append({"protocol": "S", "network": network, "next_hop": next_hop, "interface": interface, "admin_distance": ad})

        # OSPF / EIGRP / BGP from config + operational (neighbors, state)
        ospf = {"router_id": None, "process_id": None, "areas": [], "interfaces": [], "neighbors": [], "dr_bdr": {}}
        eigrp = {"as_number": None, "router_id": None, "neighbors": [], "hold_time": None, "learned_routes": []}
        bgp = {"local_as": None, "peers": [], "router_id": None}
        # OSPF config: router ospf 1 / router-id / network ... area
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
                    for area_m in re.finditer(r"network\s+\S+\s+\S+\s+area\s+(\S+)", body, re.IGNORECASE):
                        a = area_m.group(1)
                        if a not in ospf["areas"]:
                            ospf["areas"].append(a)
            except (ValueError, TypeError):
                pass
        # OSPF operational: show ip ospf neighbor - Neighbor ID Pri State Dead Time Address Interface
        ospf_neigh_section = _get_section(content, r"show\s+ip\s+ospf\s+neighbor")
        if ospf_neigh_section:
            for line in ospf_neigh_section.split("\n"):
                # (\d+\.\d+\.\d+\.\d+)\s+(\d+)\s+(FULL|2WAY|EXSTART|...)
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
        # EIGRP: router eigrp 1 / router-id / network
        eigrp_m = re.search(r"router\s+eigrp\s+(\d+)", config_block, re.IGNORECASE)
        if eigrp_m:
            try:
                eigrp["as_number"] = int(eigrp_m.group(1))
                rid_m = re.search(r"router\s+eigrp\s+\d+.*?router-id\s+(\d+\.\d+\.\d+\.\d+)", config_block, re.IGNORECASE | re.DOTALL)
                if rid_m:
                    eigrp["router_id"] = rid_m.group(1)
            except (ValueError, TypeError):
                pass
        # BGP config: router bgp / router-id / neighbor
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
                    bgp["peers"].append({"peer": nb_m.group(1), "remote_as": int(nb_m.group(2)), "state": "configured_but_down", "prefixes_received": None})
            except (ValueError, TypeError):
                pass
        # BGP operational: show ip bgp summary - Neighbor V AS MsgRcvd MsgSent TblVer ... State PfxRcd
        bgp_summary = _get_section(content, r"show\s+ip\s+bgp\s+summary")
        if bgp_summary:
            for line in bgp_summary.split("\n"):
                # (\d+\.\d+\.\d+\.\d+)\s+(\d+)\s+.*(Established|Idle|Active)\s+(\d+)
                peer_m = re.search(r"(\d+\.\d+\.\d+\.\d+)\s+(\d+)\s+\d+\s+\d+\s+\d+.*?(Established|Idle|Active|Connect|OpenSent|OpenConfirm)\s+(\d*)", line, re.IGNORECASE)
                if peer_m:
                    ip, ras, state, pfxs = peer_m.group(1), int(peer_m.group(2)), peer_m.group(3), (peer_m.group(4) or "").strip()
                    existing = next((p for p in bgp["peers"] if p.get("peer") == ip), None)
                    if existing:
                        existing["state"] = state
                        existing["prefixes_received"] = int(pfxs) if pfxs.isdigit() else None
                    else:
                        bgp["peers"].append({"peer": ip, "remote_as": ras, "state": state, "prefixes_received": int(pfxs) if pfxs.isdigit() else None})
        # RIP: passive interface from config
        rip = {"version": None, "networks": [], "passive_interfaces": []}
        rip_m = re.search(r"router\s+rip", config_block, re.IGNORECASE)
        if rip_m:
            section = re.search(r"router\s+rip(.*?)(?=router\s+|ip\s+|^!\s*$|\n\s*end\s*$|$)", config_block, re.IGNORECASE | re.DOTALL)
            if section:
                body = section.group(1)
                ver_m = re.search(r"version\s+(\d+)", body, re.IGNORECASE)
                if ver_m:
                    rip["version"] = int(ver_m.group(1))
                for net_m in re.finditer(r"network\s+(\S+)", body, re.IGNORECASE):
                    if net_m.group(1) not in rip["networks"]:
                        rip["networks"].append(net_m.group(1))
                for pass_m in re.finditer(r"passive-interface\s+(\S+)", body, re.IGNORECASE):
                    rip["passive_interfaces"].append(pass_m.group(1))

        return {"routes": routes, "ospf": ospf, "eigrp": eigrp, "bgp": bgp, "rip": rip}

    def extract_neighbors(self, content: str) -> List[Dict[str, Any]]:
        """2.3.2.6 - Neighbor name, IP, platform, ports, capabilities. Source: show cdp neighbors detail; fallback: show cdp neighbors (IP=Unknown)."""
        neighbors: List[Dict[str, Any]] = []
        # CDP neighbors detail: Device ID, IP address, Platform, Interface, Port ID (outgoing port), Capabilities
        detail_block = _get_section(content, r"show\s+cdp\s+neighbors\s+detail")
        if detail_block:
            for section in re.split(r"(?=-------------------------|Device ID:)", detail_block):
                if "Device ID:" not in section:
                    continue
                dev_m = re.search(r"Device\s+ID:\s*(\S+)", section, re.IGNORECASE)
                ip_m = re.search(r"IP\s+address:\s*(\d+\.\d+\.\d+\.\d+)", section, re.IGNORECASE)
                plat_m = re.search(r"Platform:\s*(.*?),", section, re.IGNORECASE)
                intf_port_m = re.search(r"Interface:\s*(\S+),\s*Port\s+ID\s*\(outgoing\s+port\):\s*(\S+)", section, re.IGNORECASE)
                cap_m = re.search(r"Capabilities:\s*(.*?)(?:\n|$)", section, re.IGNORECASE | re.DOTALL)
                if dev_m and (intf_port_m or re.search(r"Interface:\s*(\S+)", section, re.IGNORECASE)):
                    intf = intf_port_m.group(1) if intf_port_m else re.search(r"Interface:\s*(\S+)", section, re.IGNORECASE).group(1)
                    port_id = intf_port_m.group(2) if intf_port_m else (re.search(r"Port\s+ID\s*\(outgoing\s+port\):\s*(\S+)", section, re.IGNORECASE).group(1) if re.search(r"Port\s+ID", section, re.IGNORECASE) else None)
                    plat = (plat_m.group(1).strip() if plat_m else None)
                    neighbors.append({
                        "local_interface": intf,
                        "neighbor_id": dev_m.group(1),
                        "platform": plat or None,
                        "remote_interface": port_id,
                        "ip_address": ip_m.group(1) if ip_m else None,
                        "capabilities": cap_m.group(1).strip() if cap_m and cap_m.group(1).strip() else None,
                    })
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
                            "ip_address": "Unknown",
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
                    if not any(n["local_interface"] == x.get("local_interface") and n["neighbor_id"] == x.get("neighbor_id") for x in neighbors):
                        neighbors.append(n)
        return neighbors
    
    def extract_mac_arp(self, content: str) -> Dict[str, Any]:
        """2.3.2.7 - MAC & ARP tables; filter headers (Vlan, Mac Address, Type, Interface, ----, Total)."""
        arp_entries: List[Dict[str, Any]] = []
        mac_entries: List[Dict[str, Any]] = []
        _skip = lambda line: any(kw in line for kw in ("Vlan", "Mac Address", "Type", "Interface", "Protocol", "Address", "----", "Total")) or not line.strip()
        # show ip arp: Internet  IP  Age  Hardware Addr  Type  Interface
        arp_block = _get_section(content, r"show\s+ip\s+arp") or _get_section(content, r"show\s+arp")
        if arp_block:
            for line in arp_block.split("\n"):
                if _skip(line):
                    continue
                m = re.search(r"Internet\s+(\d+\.\d+\.\d+\.\d+)\s+(-|\d+)\s+(\S+)\s+(\w+)\s+(\S+)", line, re.IGNORECASE)
                if m:
                    ip_addr, age, hw, typ, iface = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
                    if hw.lower() == "incomplete" or not re.match(r"[\da-fA-F\.\-]{12,}", hw.replace(".", "").replace("-", "")):
                        continue
                    arp_entries.append({"ip_address": ip_addr, "age": age, "mac_address": hw, "type": typ, "interface": iface})
        # show mac address-table: VLAN MAC Type Port
        mac_block = _get_section(content, r"show\s+mac(?:\s+address-table|address-table)")
        if not mac_block:
            mac_block = _get_section(content, r"show\s+mac\s+address-table")
        if mac_block:
            for line in mac_block.split("\n"):
                if _skip(line):
                    continue
                m = re.search(r"^\s*(\d+)\s+([0-9a-fA-F\.]+)\s+(\w+)\s+(\S+)", line)
                if m:
                    vlan_s, mac, typ, port = m.group(1), m.group(2), m.group(3), m.group(4)
                    if vlan_s.lower() == "vlan" or not re.match(r"[\da-fA-F\.]{12,}", mac.replace(".", "").replace("-", "")):
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
        # NTP: if ntp server <ip> in config -> status "Configured", servers list; never null
        for m in re.finditer(r"ntp\s+server\s+(\S+)", content, re.IGNORECASE):
            s = m.group(1)
            if re.match(r"\d+\.\d+\.\d+\.\d+", s) and s not in audit["ntp"]["servers"]:
                audit["ntp"]["servers"].append(s)
        if audit["ntp"]["servers"]:
            audit["ntp"]["status"] = "Configured"
        else:
            ntp_status = _get_section(content, r"show\s+ntp\s+status")
            if ntp_status and "synchronized" in ntp_status.lower():
                audit["ntp"]["status"] = "Synchronized"
            elif ntp_status:
                audit["ntp"]["status"] = "Unsynchronized"
            else:
                audit["ntp"]["status"] = "None"
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
        """2.3.2.9 - EtherChannel from show etherchannel summary (filter headers); HSRP from show standby brief (validate virtual_ip). Config fallback for both."""
        ha: Dict[str, Any] = {"etherchannels": [], "hsrp_vrrp": []}
        config_block = _get_section(content, r"show\s+running-config") or content
        if not config_block or not config_block.strip():
            config_block = content

        # --- EtherChannel: prefer show etherchannel summary; filter header lines ---
        ec_show = _get_section(content, r"show\s+etherchannel\s+summary")
        if ec_show:
            for line in ec_show.splitlines():
                line_strip = line.strip()
                if not line_strip:
                    continue
                if "Group" in line and "Port-channel" in line:
                    continue
                if "Port-channel" in line and line_strip.startswith("------"):
                    continue
                if "Number of" in line or "Flags:" in line or line_strip.startswith("------"):
                    continue
                ec_m = re.match(r"^\s*(\d+)\s+(Po\d+)\((\w+)\)\s+(\w+)\s+(.*)$", line)
                if ec_m:
                    grp_id = int(ec_m.group(1))
                    po_name = ec_m.group(2)
                    flags = ec_m.group(3)
                    protocol = ec_m.group(4)
                    rest = ec_m.group(5)
                    if "SU" in flags or "RU" in flags:
                        status = "Up"
                    elif "D" in flags:
                        status = "Down"
                    else:
                        status = "Up"
                    members = re.findall(r"(Gi\d+/\d+|Fa\d+/\d+|Te\d+/\d+)(?:\([^)]*\))?", rest)
                    if not members:
                        members = [s.strip("()") for s in re.findall(r"\S+", rest) if re.match(r"^(Gi|Fa|Te)\d+/\d+", s)]
                    ha["etherchannels"].append({"id": grp_id, "interface": po_name, "protocol": protocol, "status": status, "members": members})
        # Config fallback for EtherChannel when no show output
        if not ha["etherchannels"]:
            pc_ids = set()
            try:
                for m in re.finditer(r"interface\s+Port-channel\s*(\d+)", config_block, re.IGNORECASE):
                    pc_ids.add(int(m.group(1)))
            except Exception:
                pass
            for grp_id in sorted(pc_ids):
                members = []
                proto = "LACP"
                try:
                    for m2 in re.finditer(r"interface\s+(\S+)\s*\n(.*?)(?=\ninterface\s+|$)", config_block, re.IGNORECASE | re.DOTALL):
                        block = m2.group(2)
                        if f"channel-group {grp_id}" not in block.lower():
                            continue
                        members.append(m2.group(1))
                        mode_m = re.search(r"channel-group\s+\d+\s+mode\s+(active|passive|on|desirable|auto)", block, re.IGNORECASE)
                        if mode_m:
                            mode = mode_m.group(1).upper()
                            if mode in ("ACTIVE", "PASSIVE"):
                                proto = "LACP"
                            elif mode in ("DESIRABLE", "AUTO"):
                                proto = "PAGP"
                            else:
                                proto = "Static"
                except Exception:
                    pass
                ha["etherchannels"].append({"id": grp_id, "protocol": proto, "members": members})

        # --- HSRP: show standby brief; skip header; only add if virtual_ip is valid IP ---
        def _is_valid_ip(s: str) -> bool:
            return bool(s and re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", s))

        show_standby = _get_section(content, r"show\s+standby\s+brief")
        if show_standby:
            for line in show_standby.splitlines():
                line_strip = line.strip()
                if not line_strip or line_strip.startswith("Interface") or line_strip.startswith("Grp") or "P indicates" in line:
                    continue
                # Interface Grp Pri P State Active Standby Virtual IP
                m = re.match(r"^(\S+)\s+(\d+)\s+(\d+)\s+(?:P\s+)?(\S+)\s+(\S+)\s+(\S+)\s+(\d+\.\d+\.\d+\.\d+)$", line_strip)
                if m:
                    iface, grp, pri, state, active, standby, vip = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4), m.group(5), m.group(6), m.group(7)
                    if _is_valid_ip(vip):
                        ha["hsrp_vrrp"].append({
                            "interface": iface,
                            "group": grp,
                            "priority": pri,
                            "state": state,
                            "virtual_ip": vip,
                            "active": active,
                            "standby": standby,
                        })
        if not ha["hsrp_vrrp"]:
            for m in re.finditer(r"standby\s+(\d+)\s+ip\s+(\d+\.\d+\.\d+\.\d+)", content, re.IGNORECASE):
                vip = m.group(2)
                if _is_valid_ip(vip):
                    ha["hsrp_vrrp"].append({"interface": None, "group": int(m.group(1)), "virtual_ip": vip, "state": None})
        for m in re.finditer(r"vrrp\s+(\d+)\s+ip\s+(\d+\.\d+\.\d+\.\d+)", content, re.IGNORECASE):
            vip = m.group(2)
            if _is_valid_ip(vip) and not any(e.get("group") == int(m.group(1)) and e.get("virtual_ip") == vip for e in ha["hsrp_vrrp"]):
                ha["hsrp_vrrp"].append({"interface": None, "group": int(m.group(1)), "virtual_ip": vip, "state": "Active"})
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
