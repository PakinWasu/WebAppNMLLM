"""Huawei VRP configuration parser - Strict Mode Implementation"""

import re
from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from .base import BaseParser


# ============================================================================
# Pydantic Models for Strict Data Structure
# ============================================================================

class DeviceOverview(BaseModel):
    """2.3.2.1 Device Overview"""
    hostname: Optional[str] = None
    role: Optional[str] = None
    model: Optional[str] = None
    os_version: Optional[str] = None
    serial_number: Optional[str] = None
    management_ip: Optional[str] = None
    uptime: Optional[str] = None
    cpu_utilization: Optional[float] = None
    memory_usage: Optional[float] = None  # Memory usage percentage
    last_config_upload: datetime = Field(default_factory=datetime.now)


class InterfaceInfo(BaseModel):
    """2.3.2.2 Interface Information"""
    name: str
    type: Optional[str] = None
    admin_status: Optional[str] = None
    oper_status: Optional[str] = None
    description: Optional[str] = None
    ipv4_address: Optional[str] = None
    ipv6_address: Optional[str] = None
    mac_address: Optional[str] = None
    speed: Optional[str] = None
    duplex: Optional[str] = None
    mtu: Optional[int] = None
    port_mode: Optional[str] = None
    access_vlan: Optional[int] = None
    native_vlan: Optional[int] = None
    allowed_vlans: Optional[str] = None
    stp_role: Optional[str] = None  # STP role from display stp brief
    stp_state: Optional[str] = None  # STP state from display stp brief
    stp_edged_port: Optional[bool] = None  # STP edged-port (portfast) enabled


class VlanL2Switching(BaseModel):
    """2.3.2.3 VLAN & L2 Switching"""
    vlan_list: List[int] = Field(default_factory=list)
    total_vlan_count: int = 0
    details: List[Dict[str, Any]] = Field(default_factory=list)
    access_ports: List[str] = Field(default_factory=list)
    trunk_ports: List[Dict[str, Any]] = Field(default_factory=list)


class STPPortInfo(BaseModel):
    """STP Port Information"""
    port: str
    role: Optional[str] = None
    state: Optional[str] = None


class STPInfo(BaseModel):
    """2.3.2.4 Spanning Tree Protocol"""
    stp_mode: Optional[str] = None
    bridge_priority: Optional[int] = None
    root_bridge_id: Optional[str] = None
    root_bridge_status: Optional[bool] = None
    portfast_enabled: Optional[bool] = None
    bpdu_guard: Optional[bool] = None
    interfaces: List[STPPortInfo] = Field(default_factory=list)


class StaticRoute(BaseModel):
    """Static route entry"""
    network: str
    mask: str
    nexthop: str
    interface: Optional[str] = None


class OSPFInfo(BaseModel):
    """OSPF configuration"""
    process_id: Optional[int] = None
    router_id: Optional[str] = None
    areas: List[str] = Field(default_factory=list)
    networks: List[str] = Field(default_factory=list)


class RIPInfo(BaseModel):
    """RIP configuration"""
    process_id: Optional[int] = None
    version: Optional[int] = None
    networks: List[str] = Field(default_factory=list)


class BGPInfo(BaseModel):
    """BGP configuration"""
    as_number: Optional[int] = None
    router_id: Optional[str] = None
    peers: List[Dict[str, Any]] = Field(default_factory=list)


class RoutingInfo(BaseModel):
    """2.3.2.5 Routing Information"""
    static: List[StaticRoute] = Field(default_factory=list)
    ospf: Optional[OSPFInfo] = None
    rip: Optional[RIPInfo] = None
    bgp: Optional[BGPInfo] = None


class NeighborInfo(BaseModel):
    """2.3.2.6 Neighbor & Topology"""
    device_name: Optional[str] = None
    local_port: Optional[str] = None
    remote_port: Optional[str] = None
    ip_address: Optional[str] = None


class MacArpInfo(BaseModel):
    """2.3.2.7 MAC & ARP"""
    mac_table: Optional[List[Dict[str, Any]]] = None
    arp_table: Optional[List[Dict[str, Any]]] = None


class ACLRule(BaseModel):
    """ACL Rule"""
    id: Optional[str] = None
    action: Optional[str] = None  # permit, deny
    protocol: Optional[str] = None  # tcp, udp, icmp, ip, etc.
    source: Optional[str] = None  # source IP/network
    destination: Optional[str] = None  # destination IP/network


class ACLInfo(BaseModel):
    """ACL Information"""
    acl_number: str
    rules: List[ACLRule] = Field(default_factory=list)


class UserAccount(BaseModel):
    """User Account with Privilege Level"""
    username: str
    privilege_level: Optional[int] = None


class SecurityManagement(BaseModel):
    """2.3.2.8 Security & Management"""
    user_accounts: List[UserAccount] = Field(default_factory=list)
    ssh_enabled: Optional[bool] = None
    snmp_settings: Optional[Dict[str, Any]] = None
    ntp_server: Optional[str] = None
    syslog: Optional[str] = None
    acls: Optional[List[ACLInfo]] = None


class HAInfo(BaseModel):
    """2.3.2.9 High Availability"""
    etherchannel: List[Dict[str, Any]] = Field(default_factory=list)
    vrrp: List[Dict[str, Any]] = Field(default_factory=list)


class DeviceConfig(BaseModel):
    """Root device configuration model"""
    device_overview: DeviceOverview
    interfaces: List[InterfaceInfo]
    vlans: VlanL2Switching
    stp: STPInfo
    routing: RoutingInfo
    neighbors: List[NeighborInfo] = Field(default_factory=list)
    mac_arp: MacArpInfo
    security: SecurityManagement
    ha: HAInfo


# ============================================================================
# Helper Functions for Validation
# ============================================================================

def is_valid_ipv4(ip_str: str) -> bool:
    """Validate IPv4 address format"""
    if not ip_str or not isinstance(ip_str, str):
        return False
    # Strict IPv4 pattern: 1-3 digits, 4 groups separated by dots
    pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
    if not re.match(pattern, ip_str):
        return False
    # Validate each octet is 0-255
    try:
        parts = ip_str.split('.')
        if len(parts) != 4:
            return False
        for part in parts:
            num = int(part)
            if num < 0 or num > 255:
                return False
        return True
    except (ValueError, AttributeError):
        return False


def _canonical_interface_name_huawei(name: str) -> str:
    """Normalize Huawei interface name so GE0/0/1 and GigabitEthernet0/0/1 map to the same key (no duplicates)."""
    if not name or not name[0].isalpha():
        return name
    s = name.strip()
    lower = s.lower()
    if lower.startswith("ge") and (len(s) == 2 or s[2:3].isdigit()):
        return "GigabitEthernet" + s[2:]
    if lower.startswith("gigabitethernet"):
        return s
    # Eth0/0/1 (display interface description table) -> same key as GigabitEthernet0/0/1
    if lower.startswith("eth") and len(s) > 3 and s[3:4].isdigit():
        return "GigabitEthernet" + s[3:]
    if lower.startswith("eth-trunk"):
        return s
    if lower.startswith("vlanif"):
        return s
    if lower.startswith("loopback"):
        return s
    if lower.startswith("meth"):
        return s
    # Ethernet0/0/1 (display interface) = same as GigabitEthernet0/0/1 / Eth0/0/1 for merge
    if lower.startswith("ethernet") and len(s) > 8:
        return "GigabitEthernet" + s[8:]
    return s


def is_valid_interface_name(iface_str: str) -> bool:
    """Validate interface name format"""
    if not iface_str or not isinstance(iface_str, str):
        return False
    # Must start with a letter and contain alphanumeric characters
    if len(iface_str) < 2:
        return False
    # Must start with letter (GE, Eth, Vlan, Gigabit, etc.)
    if not iface_str[0].isalpha():
        return False
    # Must contain at least one number
    if not any(c.isdigit() for c in iface_str):
        return False
    # Common interface prefixes
    valid_prefixes = ['GE', 'Gi', 'Eth', 'Fa', 'Te', 'Se', 'Lo', 'Vl', 'Po', 'Tu', 'MEth', 'GigabitEthernet', 'Ethernet', 'Vlanif', 'LoopBack', 'Eth-Trunk']
    iface_upper = iface_str.upper()
    return any(iface_upper.startswith(prefix.upper()) for prefix in valid_prefixes)


# Standard speed/duplex inference when display interface has no explicit Speed:/Duplex: lines
INTERFACE_STANDARDS = {
    "TenGigabitEthernet": {"speed": "10Gbps", "duplex": "full"},
    "XGigabitEthernet": {"speed": "10Gbps", "duplex": "full"},
    "GigabitEthernet": {"speed": "1Gbps", "duplex": "full"},
    "FastEthernet": {"speed": "100Mbps", "duplex": "full"},
    "Ethernet": {"speed": "10Mbps", "duplex": "full"},
    "Eth-Trunk": {"duplex": "full"},  # Aggregates are logically full duplex; speed from Current BW when present
}


def is_valid_username(username: str) -> bool:
    """Validate username - filter out separators and garbage"""
    if not username or not isinstance(username, str):
        return False
    username = username.strip()
    # Reject if only dashes or special characters
    if set(username) == {'-'} or not username[0].isalnum():
        return False
    # Reject if it's just a single character or digit
    if len(username) < 2:
        return False
    # Reject common separator patterns
    if username.startswith('---') or username.startswith('==='):
        return False
    return True


def is_valid_mac_address(mac_str: str) -> bool:
    """Validate MAC address format - Huawei format: XXXX-XXXX-XXXX"""
    if not mac_str or not isinstance(mac_str, str):
        return False
    # Huawei MAC format: 4 hex digits, dash, 4 hex digits, dash, 4 hex digits
    pattern = r'^[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}$'
    return bool(re.match(pattern, mac_str))


# ============================================================================
# Huawei Parser Implementation
# ============================================================================

class HuaweiParser(BaseParser):
    """Parser for Huawei VRP device configurations - Strict Mode"""
    
    def detect_vendor(self, content: str) -> bool:
        """Detect if this is a Huawei configuration"""
        strong_indicators = [
            r'display\s+version',
            r'VRP\s+\(R\)',
            r'Huawei\s+Versatile',
            r'sysname\s+\S+',
            r'port\s+link-type',
            r'vrrp\s+vrid',
            r'local-user\s+\S+',
        ]
        
        strong_matches = sum(1 for pattern in strong_indicators if re.search(pattern, content, re.IGNORECASE))
        return strong_matches >= 2
    
    def parse(self, content: str, filename: str) -> Dict[str, Any]:
        """Parse complete Huawei configuration. Multi-Source Inference: pass full original_content to all helpers."""
        self.original_content = content
        full = self.original_content
        try:
            # Extract each section with individual error handling
            device_overview = {}
            interfaces = []
            vlans = {"vlan_list": [], "total_vlan_count": 0}
            stp = {"interfaces": []}  # Ensure interfaces list exists
            routing = {"static": [], "ospf": None, "rip": None, "bgp": None}
            neighbors = []
            mac_arp = {"mac_table": None, "arp_table": None}
            security = {"user_accounts": [], "acls": []}  # Ensure lists exist
            ha = {"etherchannel": [], "vrrp": []}
            
            # Extract each section with try-except to prevent one failure from breaking everything
            try:
                device_overview = self.extract_device_overview(full)
            except Exception as e:
                print(f"⚠️ Error extracting device overview from {filename}: {e}")
                import traceback
                traceback.print_exc()

            try:
                interfaces = self.extract_interfaces(full)
            except Exception as e:
                print(f"⚠️ Error extracting interfaces from {filename}: {e}")
                import traceback
                traceback.print_exc()

            try:
                vlans = self.extract_vlans(full)
            except Exception as e:
                print(f"⚠️ Error extracting VLANs from {filename}: {e}")
                import traceback
                traceback.print_exc()

            try:
                stp = self.extract_stp(full)
            except Exception as e:
                print(f"⚠️ Error extracting STP from {filename}: {e}")
                import traceback
                traceback.print_exc()

            try:
                routing = self.extract_routing(full)
            except Exception as e:
                print(f"⚠️ Error extracting routing from {filename}: {e}")
                import traceback
                traceback.print_exc()

            try:
                neighbors = self.extract_neighbors(full)
            except Exception as e:
                print(f"⚠️ Error extracting neighbors from {filename}: {e}")
                import traceback
                traceback.print_exc()

            try:
                mac_arp = self.extract_mac_arp(full)
            except Exception as e:
                print(f"⚠️ Error extracting MAC/ARP from {filename}: {e}")
                import traceback
                traceback.print_exc()

            try:
                security = self.extract_security(full)
            except Exception as e:
                print(f"⚠️ Error extracting security from {filename}: {e}")
                import traceback
                traceback.print_exc()

            try:
                ha = self.extract_ha(full)
            except Exception as e:
                print(f"⚠️ Error extracting HA from {filename}: {e}")
                import traceback
                traceback.print_exc()

            # Management IP: first-available from interfaces (Loopback > Vlanif > Management > first physical)
            mgmt_ip = None
            try:
                mgmt_ip = self._get_management_ip(interfaces)
            except Exception:
                pass
            if mgmt_ip:
                device_overview["management_ip"] = mgmt_ip

            # New schema (2.3.2.1–2.3.2.9): device_info, security_audit, high_availability
            device_info = {}
            security_audit = {}
            high_availability = {"ether_channels": []}
            try:
                device_info = self.extract_device_info(full, device_overview)
            except Exception:
                pass
            if device_info is not None:
                device_info["management_ip"] = device_info.get("management_ip") or mgmt_ip
            try:
                security_audit = self.extract_security_audit(full, security)
            except Exception:
                pass
            try:
                high_availability = self.extract_high_availability(full, ha)
            except Exception:
                pass
            
            # Build config object
            try:
                # VlanL2Switching expects vlan_list: List[int]; extract_vlans returns vlan_list as list of {id,name,status}
                vlans_for_config = {
                    "vlan_list": [int(x["id"]) for x in (vlans.get("vlan_list") or []) if str(x.get("id") or "").isdigit()],
                    "total_vlan_count": vlans.get("total_vlan_count") or vlans.get("total_count") or 0,
                    "details": vlans.get("details", []),
                    "access_ports": vlans.get("access_ports", []),
                    "trunk_ports": vlans.get("trunk_ports", []),
                }
                config = DeviceConfig(
                    device_overview=device_overview,
                    interfaces=interfaces,
                    vlans=vlans_for_config,
                    stp=stp,
                    routing=routing,
                    neighbors=neighbors,
                    mac_arp=mac_arp,
                    security=security,
                    ha=ha,
                )
                out = config.model_dump(mode='python')
                out["device_info"] = device_info
                out["security_audit"] = security_audit
                out["high_availability"] = high_availability
                return out
            except Exception as e:
                print(f"⚠️ Error building DeviceConfig from {filename}: {e}")
                import traceback
                traceback.print_exc()
                # Return partial structure
                return {
                    "device_info": device_info,
                    "security_audit": security_audit,
                    "high_availability": high_availability,
                    "device_overview": device_overview,
                    "interfaces": interfaces,
                    "vlans": vlans,
                    "stp": stp,
                    "routing": routing,
                    "neighbors": neighbors,
                    "mac_arp": mac_arp,
                    "security": security,
                    "ha": ha,
                }
        except Exception as e:
            # Final fallback - return minimal structure
            print(f"❌ Critical error parsing {filename}: {e}")
            import traceback
            traceback.print_exc()
            return {
                "device_info": {},
                "security_audit": {},
                "high_availability": {"ether_channels": []},
                "device_overview": {"hostname": None},
                "interfaces": [],
                "vlans": {"vlan_list": [], "total_vlan_count": 0},
                "stp": {"interfaces": []},
                "routing": {"static": [], "ospf": None, "rip": None, "bgp": None},
                "neighbors": [],
                "mac_arp": {"mac_table": None, "arp_table": None},
                "security": {"user_accounts": [], "acls": []},
                "ha": {"etherchannel": [], "vrrp": []},
            }

    def _get_management_ip(self, interfaces_list: List[Dict[str, Any]]) -> Optional[str]:
        """Smart selection: Priority 1 Loopback, 2 Vlanif, 3 Management/MEth, 4 first physical with IP. Ignore 127.x."""
        return self._determine_management_ip(interfaces_list)

    def _determine_management_ip(self, interfaces_list: List[Dict[str, Any]]) -> Optional[str]:
        """First-available management IP: Loopback > Vlanif > Management/MEth > first physical with IP. Ignore 127.0.0.x."""
        def _normalize_ip(ip: Any) -> Optional[str]:
            if not ip or not isinstance(ip, str):
                return None
            addr = (ip.split()[0] if ip.split() else ip).split("/")[0].strip()
            if not re.match(r"\d+\.\d+\.\d+\.\d+", addr) or addr.startswith("127."):
                return None
            return addr

        loopback, vlan, mgmt, physical = [], [], [], []
        for i in interfaces_list or []:
            ip = i.get("ipv4_address") or i.get("ip_address")
            addr = _normalize_ip(ip)
            if not addr:
                continue
            name = (i.get("name") or "").lower()
            if "loopback" in name or "lo" == name[:2]:
                loopback.append(addr)
            elif "vlanif" in name or "vlan" in name:
                vlan.append(addr)
            elif "management" in name or "meth" in name:
                mgmt.append(addr)
            elif any(name.startswith(p) for p in ("gigabit", "ge", "ethernet", "eth", "eth-trunk")):
                physical.append(addr)
        for cand in (loopback, vlan, mgmt, physical):
            if cand:
                return cand[0]
        return None

    def extract_device_info(self, content: str, overview: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """2.3.2.1 - device_info: hostname, vendor, model, os_version, serial_number, uptime, cpu_load, memory_usage. Virtual/simulator support."""
        info = {
            "hostname": (overview or {}).get("hostname"),
            "vendor": "Huawei",
            "model": None,
            "os_version": None,
            "serial_number": None,
            "uptime": None,
            "cpu_load": None,
            "memory_usage": None,
        }
        if not info["hostname"]:
            sysname_match = re.search(r'^\s*(?:\[\w+\])?\s*sysname\s+(\S+)', content, re.MULTILINE | re.IGNORECASE)
            if sysname_match:
                info["hostname"] = sysname_match.group(1)
            else:
                prompt_match = re.search(r'<(\S+)>', content)
                if prompt_match and prompt_match.group(1).upper() != "HUAWEI":
                    info["hostname"] = prompt_match.group(1)
        # Model: Quidway (\S+), HUAWEI (\S+), Router Built-in (virtual/simulator)
        try:
            for pattern in [
                r'Quidway\s+(\S+)\s+.*?uptime',
                r'HUAWEI\s+(\S+)\s+.*?uptime',
                r"(\S+-\d+\S*)'s\s+Device\s+status",
                r'Router\s+Built-in',
                r'Device\s+status\s+(\S+)',
            ]:
                m = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
                if m:
                    candidate = (m.group(1) or "Router Built-in").strip() if m.lastindex else "Router Built-in"
                    if candidate and (candidate == "Router Built-in" or (len(candidate) > 2 and any(c.isdigit() for c in candidate))):
                        info["model"] = candidate
                        break
        except Exception:
            pass
        if not info["model"]:
            info["model"] = "Huawei VRP (Unknown)"
        # Firmware: VRP (R) software, Version (\S+)
        try:
            vrp_m = re.search(r'VRP\s*\(R\)\s+software,?\s*Version\s+([^\s,\)]+)', content, re.IGNORECASE)
            if vrp_m:
                info["os_version"] = "VRP " + vrp_m.group(1)
            if not info["os_version"]:
                vrp_m = re.search(r'Version\s+([\d.]+)', content, re.IGNORECASE)
                if vrp_m:
                    info["os_version"] = "VRP " + vrp_m.group(1)
        except Exception:
            pass
        if not info["os_version"]:
            info["os_version"] = "VRP (Unknown)"
        version_section = re.search(r'display\s+version(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if version_section:
            version_output = version_section.group(1)
            uptime_m = re.search(r'uptime\s+is\s+(.+?)(?:\n|<|$)', version_output, re.IGNORECASE)
            if uptime_m:
                info["uptime"] = uptime_m.group(1).strip()
        # Serial: display device \d+\s+\S+\s+(\S+)\s+Present; ESN/BarCode; fallback N/A (Simulator)
        try:
            dev_section = re.search(r'display\s+device(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
            if dev_section:
                dm = re.search(r'\d+\s+\S+\s+(\S+)\s+Present', dev_section.group(1), re.IGNORECASE)
                if dm:
                    info["serial_number"] = dm.group(1)
            if not info["serial_number"]:
                barcode_m = re.search(r'BarCode[=:\s]+(\w+)', content, re.IGNORECASE)
                if barcode_m:
                    info["serial_number"] = barcode_m.group(1)
            if not info["serial_number"]:
                esn_section = re.search(r'display\s+esn(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
                if esn_section and "Error" not in esn_section.group(1) and "Unrecognized" not in esn_section.group(1):
                    sn_m = re.search(r'ESN[:\s]+(\S+)|Equipment\s+Serial\s+Number\s*[:\s]+(\w+)', esn_section.group(1), re.IGNORECASE)
                    if sn_m:
                        cand = (sn_m.group(1) or sn_m.group(2) or "").strip()
                        if cand and cand != "^":
                            info["serial_number"] = cand
            if not info["serial_number"]:
                info["serial_number"] = "Virtual-Device-ID"
        except Exception:
            info["serial_number"] = "Virtual-Device-ID"
        if overview:
            info["model"] = info["model"] or overview.get("model")
            info["os_version"] = info["os_version"] or (overview.get("os_version") and f"VRP {overview['os_version']}")
            info["uptime"] = info["uptime"] or overview.get("uptime")
            info["cpu_load"] = overview.get("cpu_utilization")
            info["memory_usage"] = overview.get("memory_usage")
        # CPU / Memory: global search (anywhere in content)
        if info["cpu_load"] is None:
            try:
                cpu_m = re.search(r'CPU\s+Usage\s*.*?:\s*(\d+)\s*%', content, re.IGNORECASE)
                if cpu_m:
                    info["cpu_load"] = float(cpu_m.group(1))
            except (ValueError, TypeError):
                pass
            if info["cpu_load"] is None:
                cpu_section = re.search(r'display\s+cpu-usage(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
                if cpu_section and "Warning:CPU" not in cpu_section.group(1):
                    cm = re.search(r'CPU\s+Usage\s*:\s*(\d+)%|CPU\s+utilization.*?(\d+)%', cpu_section.group(1), re.IGNORECASE)
                    if cm:
                        try:
                            info["cpu_load"] = float(cm.group(1) or cm.group(2))
                        except (ValueError, TypeError):
                            pass
        if info["memory_usage"] is None:
            try:
                mem_m = re.search(r'Memory\s+Using\s+Percentage\s*.*?:\s*(\d+)\s*%', content, re.IGNORECASE)
                if mem_m:
                    info["memory_usage"] = float(mem_m.group(1))
            except (ValueError, TypeError):
                pass
            if info["memory_usage"] is None:
                mem_section = re.search(r'display\s+memory-usage(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
                if mem_section:
                    mm = re.search(r'Memory\s+Using\s+Percentage\s+Is\s*:\s*(\d+)%', mem_section.group(1), re.IGNORECASE)
                    if mm:
                        try:
                            info["memory_usage"] = float(mm.group(1))
                        except (ValueError, TypeError):
                            pass
        return info

    def extract_security_audit(self, content: str, security: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """2.3.2.8 - security_audit: never null. Use Enabled/Disabled, [] or None for missing."""
        audit = {
            "ssh": {"status": "Disabled", "version": "2.0"},
            "telnet": {"status": "Disabled"},
            "aaa": {"status": "Disabled", "protocols": []},
            "snmp": {"status": "Disabled", "version": None, "communities": []},
            "ntp": {"servers": [], "status": "None"},
            "logging": {"syslog_servers": [], "console_logging": False},
            "acls": [],
        }
        if re.search(r'stelnet\s+server\s+enable|ssh\s+server\s+version\s+2\.0|protocol\s+inbound\s+ssh', content, re.IGNORECASE):
            audit["ssh"]["status"] = "Enabled"
            ver_m = re.search(r'ssh\s+server\s+version\s+([\d.]+)', content, re.IGNORECASE)
            audit["ssh"]["version"] = ver_m.group(1) if ver_m else "2.0"
        if re.search(r'telnet\s+server\s+enable|protocol\s+inbound\s+telnet', content, re.IGNORECASE):
            audit["telnet"]["status"] = "Enabled"
        if re.search(r'authentication-scheme\s+\S+', content, re.IGNORECASE):
            audit["aaa"]["status"] = "Enabled"
            if re.search(r'tacacs|radius|local', content, re.IGNORECASE):
                for p in ["tacacs+", "radius", "local"]:
                    if p in content.lower():
                        audit["aaa"]["protocols"].append(p)
        for m in re.finditer(r'snmp-agent\s+community\s+(?:read\s+)?(\S+)', content, re.IGNORECASE):
            audit["snmp"]["communities"].append(m.group(1))
        if audit["snmp"]["communities"] or "snmp-agent" in content.lower():
            audit["snmp"]["status"] = "Enabled"
            audit["snmp"]["version"] = "v2c"
        else:
            audit["snmp"]["status"] = "Disabled"
        for m in re.finditer(r'ntp-service\s+unicast-server\s+(\S+)', content, re.IGNORECASE):
            s = m.group(1)
            if re.match(r'\d+\.\d+\.\d+\.\d+', s) and s not in audit["ntp"]["servers"]:
                audit["ntp"]["servers"].append(s)
        if audit["ntp"]["servers"]:
            audit["ntp"]["status"] = "Configured"
        for m in re.finditer(r'info-center\s+loghost\s+(\S+)', content, re.IGNORECASE):
            audit["logging"]["syslog_servers"].append(m.group(1))
        acl_map = {}
        for m in re.finditer(r'acl\s+(?:number\s+)?(\d+)\s+rule\s+\d+', content, re.IGNORECASE):
            acl_id = m.group(1)
            acl_map[acl_id] = acl_map.get(acl_id, 0) + 1
        for acl_id, count in acl_map.items():
            audit["acls"].append({"name": acl_id, "type": "Extended" if int(acl_id) >= 3000 else "Standard", "rule_count": count})
        if security and security.get("acls"):
            for acl in security["acls"]:
                name = acl.get("acl_number") if isinstance(acl, dict) else str(acl)
                if name and not any(a.get("name") == name for a in audit["acls"]):
                    audit["acls"].append({"name": name, "type": "Extended", "rule_count": 0})
        return audit

    def extract_high_availability(self, content: str, ha: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """2.3.2.9 - high_availability.ether_channels: interface, protocol, members, status."""
        ether_channels = []
        if ha and ha.get("etherchannel"):
            for e in ha["etherchannel"]:
                name = e.get("name") or f"Eth-Trunk{e.get('id', '')}"
                protocol = (e.get("mode") or "LACP").upper()
                if protocol not in ("LACP", "STATIC", "PAGP"):
                    protocol = "LACP" if "lacp" in (e.get("mode") or "").lower() else "Static"
                members = e.get("members") or []
                status = "Up" if members else "Down"
                ether_channels.append({"interface": name, "protocol": protocol, "members": members, "status": status})
        # Status from display eth-trunk or display interface Eth-Trunk
        display_trunk = re.search(r'display\s+eth-trunk\s*\d*(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if display_trunk:
            for line in display_trunk.group(1).split("\n"):
                if "current state" in line.lower() and "UP" in line.upper():
                    for ec in ether_channels:
                        if ec["interface"].lower() in line.lower():
                            ec["status"] = "Up"
                            break
        return {"ether_channels": ether_channels}

    def extract_device_overview(self, content: str) -> Dict[str, Any]:
        """2.3.2.1 Device Overview"""
        overview = {
            "hostname": None,
            "role": None,
            "model": None,
            "os_version": None,
            "serial_number": None,
            "management_ip": None,
            "uptime": None,
            "cpu_utilization": None,
            "memory_usage": None,
            "last_config_upload": datetime.now(),
        }
        
        # Extract hostname - PRIORITIZE sysname command over prompt
        # Look for sysname command (may be in [Huawei]sysname ACC4 format or just sysname ACC4)
        # Use MULTILINE flag to match start of line, and allow optional brackets before sysname
        sysname_match = re.search(r'^\s*(?:\[\w+\])?\s*sysname\s+(\S+)', content, re.MULTILINE | re.IGNORECASE)
        if sysname_match:
            overview["hostname"] = sysname_match.group(1)
        else:
            # Fallback: Try prompt format <HOSTNAME> (but exclude default <Huawei>)
            prompt_match = re.search(r'<(\S+)>', content)
            if prompt_match:
                hostname_candidate = prompt_match.group(1)
                # Reject default "Huawei" prompt - only use if it's not the default
                if hostname_candidate.upper() != "HUAWEI":
                    overview["hostname"] = hostname_candidate
        
        # Infer role from hostname
        if overview["hostname"]:
            hostname_upper = overview["hostname"].upper()
            if "CORE" in hostname_upper:
                overview["role"] = "Core"
            elif "DIST" in hostname_upper:
                overview["role"] = "Distribution"
            elif "ACC" in hostname_upper:
                overview["role"] = "Access"
            elif "EDGE" in hostname_upper or "BR" in hostname_upper:
                overview["role"] = "Router"
            else:
                overview["role"] = "Switch"
        
        # Multi-Source Inference (2.3.2.1): Model - search anywhere. Quidway (\S+) OR HUAWEI (\S+) OR Device status (\S+)
        try:
            for pattern in [
                r'Quidway\s+(\S+)\s+.*?uptime',
                r'HUAWEI\s+(\S+)\s+.*?uptime',
                r"(\S+-\d+\S*)'s\s+Device\s+status",
                r'Device\s+status\s+(\S+)',
                r'Quidway\s+(\S+)\s+uptime',
                r'HUAWEI\s+(\S+)\s+uptime',
            ]:
                m = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
                if m:
                    candidate = (m.group(1) or "").strip()
                    if candidate and len(candidate) > 2 and any(c.isdigit() for c in candidate):
                        overview["model"] = candidate
                        break
        except Exception:
            pass
        # OS version / uptime from display version if present
        version_section = re.search(r'display\s+version(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if version_section:
            version_output = version_section.group(1)
            try:
                vrp_match = re.search(r'Version\s+([\d.]+)', version_output, re.IGNORECASE)
                if vrp_match:
                    overview["os_version"] = vrp_match.group(1)
                uptime_match = re.search(r'uptime\s+is\s+(.+?)(?:\n|<|$)', version_output, re.IGNORECASE)
                if uptime_match:
                    overview["uptime"] = uptime_match.group(1).strip()
            except Exception:
                pass
        # Serial: global search anywhere - BarCode=(\w+) OR ESN: (\w+)
        try:
            if not overview.get("serial_number"):
                for pattern in [r'BarCode[=:\s]+(\w+)', r'ESN[:\s]+(\w+)', r'Equipment\s+Serial\s+Number\s*[:\s]+(\w+)']:
                    m = re.search(pattern, content, re.IGNORECASE)
                    if m:
                        cand = (m.group(1) or "").strip()
                        if cand and cand != "^" and "Error" not in cand:
                            overview["serial_number"] = cand
                            break
            esn_section = re.search(r'display\s+esn(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
            if esn_section and not overview.get("serial_number"):
                esn_output = esn_section.group(1)
                if "Error" not in esn_output and "Failed to read ESN" not in esn_output:
                    esn_value = re.search(r'ESN[:\s]+(\S+)', esn_output, re.IGNORECASE)
                    if esn_value:
                        cand = esn_value.group(1).strip()
                        if cand != "^":
                            overview["serial_number"] = cand
        except Exception:
            pass
        # CPU: global search - CPU Usage.*:\s*(\d+)% anywhere
        try:
            cpu_m = re.search(r'CPU\s+Usage\s*.*?:\s*(\d+)\s*%', content, re.IGNORECASE)
            if cpu_m:
                overview["cpu_utilization"] = float(cpu_m.group(1))
            if overview["cpu_utilization"] is None:
                cpu_section = re.search(r'display\s+cpu-usage(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
                if cpu_section and "Warning:CPU" not in cpu_section.group(1):
                    cm = re.search(r'CPU\s+Usage\s*:\s*(\d+)%|CPU\s+utilization.*?(\d+)%', cpu_section.group(1), re.IGNORECASE)
                    if cm:
                        overview["cpu_utilization"] = float(cm.group(1) or cm.group(2))
        except Exception:
            pass
        # Memory: global search - Memory Using Percentage.*:\s*(\d+)% anywhere
        try:
            mem_m = re.search(r'Memory\s+Using\s+Percentage\s*.*?:\s*(\d+)\s*%', content, re.IGNORECASE)
            if mem_m:
                overview["memory_usage"] = float(mem_m.group(1))
            if overview["memory_usage"] is None:
                memory_section = re.search(r'display\s+memory-usage(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
                if memory_section:
                    mm = re.search(r'Memory\s+Using\s+Percentage\s+Is\s*:\s*(\d+)%', memory_section.group(1), re.IGNORECASE)
                    if mm:
                        overview["memory_usage"] = float(mm.group(1))
        except Exception:
            pass
        # Extract management IP: LoopBack0, Vlanif, then "Management address : X.X.X.X", then any interface IP (no 127.x)
        mgmt_patterns = [
            r'Management\s+address\s*:\s*(\d+\.\d+\.\d+\.\d+)',
            r'interface\s+LoopBack0.*?ip\s+address\s+(\d+\.\d+\.\d+\.\d+)',
            r'interface\s+Vlanif1\s*\n.*?ip\s+address\s+(\d+\.\d+\.\d+\.\d+)',
            r'interface\s+Vlanif\d+.*?ip\s+address\s+(\d+\.\d+\.\d+\.\d+)',
        ]
        for pattern in mgmt_patterns:
            mgmt_match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if mgmt_match:
                ip_candidate = mgmt_match.group(1)
                if is_valid_ipv4(ip_candidate) and not ip_candidate.startswith("127."):
                    overview["management_ip"] = ip_candidate
                    break
        if not overview["management_ip"]:
            for m in re.finditer(r'interface\s+Vlanif\d+.*?ip\s+address\s+(\d+\.\d+\.\d+\.\d+)', content, re.IGNORECASE | re.DOTALL):
                if is_valid_ipv4(m.group(1)) and not m.group(1).startswith("127."):
                    overview["management_ip"] = m.group(1)
                    break
        if not overview["management_ip"]:
            first_ip = re.search(r'ip\s+address\s+(\d+\.\d+\.\d+\.\d+)', content, re.IGNORECASE)
            if first_ip and is_valid_ipv4(first_ip.group(1)) and not first_ip.group(1).startswith("127."):
                overview["management_ip"] = first_ip.group(1)
        return overview
    
    def _normalize_mac_huawei(self, mac: str) -> str:
        """Normalize Huawei MAC (e.g. 4c1f-cc7f-6d12) to XX:XX:XX:XX:XX:XX."""
        if not mac:
            return ""
        try:
            s = re.sub(r"[\s.-]", "", mac).lower()
            if len(s) == 12 and all(c in "0123456789abcdef" for c in s):
                return ":".join(s[i : i + 2] for i in range(0, 12, 2))
        except Exception:
            pass
        return mac

    def _parse_one_display_interface_block(self, block: str) -> Optional[Dict[str, Any]]:
        """Extract fields from one 'display interface' block. Returns dict of updates."""
        if not block or not block.strip():
            return None
        try:
            name_m = re.match(r"^(\S+)\s+current\s+state\s*:\s*(UP|DOWN|ADM.*)", block, re.IGNORECASE)
            if not name_m:
                return None
            name = name_m.group(1)
            state = (name_m.group(2) or "").upper()
            admin_status = "down" if "DOWN" in state or "ADM" in state else "up"
            line_proto = re.search(r"Line\s+protocol\s+current\s+state\s*:\s*(\w+)", block, re.IGNORECASE)
            oper_status = (line_proto.group(1) or "up").lower() if line_proto else "up"
            out: Dict[str, Any] = {"name": name, "admin_status": admin_status, "oper_status": oper_status, "line_protocol": oper_status}
            desc_m = re.search(r"Description\s*:\s*(.*?)(?:\n|$)", block, re.IGNORECASE | re.DOTALL)
            if desc_m:
                desc = desc_m.group(1).strip()
                if desc:
                    out["description"] = desc
            mac_m = re.search(r"Hardware\s+address\s+is\s+([\w\-]+)", block, re.IGNORECASE)
            if mac_m:
                out["mac_address"] = self._normalize_mac_huawei(mac_m.group(1))
            ip_m = re.search(r"Internet\s+Address\s+is\s+(\d+\.\d+\.\d+\.\d+/\d+)", block, re.IGNORECASE)
            if ip_m:
                out["ipv4_address"] = ip_m.group(1)
            pvid_m = re.search(r"PVID\s*:\s*(\d+)", block, re.IGNORECASE)
            if pvid_m:
                out["access_vlan"] = int(pvid_m.group(1))
                out["native_vlan"] = int(pvid_m.group(1))
            if "Switch Port" in block or "switch port" in block.lower():
                out["port_mode"] = "l2_switchport"
            elif "Route Port" in block or "route port" in block.lower():
                out["port_mode"] = "l3_routed"
            # Speed/Bandwidth: Pattern A Current BW / Maximal BW (Eth-Trunk), Pattern B Speed : (\d+)
            bw_m = re.search(r"(?:Current|Maximal)\s+BW[:\s]*(\d+)\s*([GMK])", block, re.IGNORECASE)
            if bw_m:
                num, unit = int(bw_m.group(1)), (bw_m.group(2) or "M").upper()
                if unit == "G":
                    out["speed"] = f"{num}Gbps"
                elif unit == "M":
                    out["speed"] = f"{num}Mbps"
                else:
                    out["speed"] = f"{num}Kbps"
            if not out.get("speed"):
                speed_line_m = re.search(r"Speed\s*:\s*(\d+)", block, re.IGNORECASE)
                if speed_line_m:
                    val = int(speed_line_m.group(1))
                    if val >= 1000:
                        out["speed"] = f"{val // 1000}Gbps"
                    else:
                        out["speed"] = f"{val}Mbps"
            # Duplex: Duplex : (FULL|HALF|AUTO)
            duplex_m = re.search(r"Duplex\s*:\s*(FULL|HALF|AUTO)", block, re.IGNORECASE)
            if duplex_m:
                out["duplex"] = duplex_m.group(1).lower()
            # Description already extracted above; ensure strip
            if out.get("description"):
                out["description"] = out["description"].strip()
            mtu_m = re.search(r"(?:Maximum\s+Frame\s+Length\s+is|MTU\s+is)\s+(\d+)", block, re.IGNORECASE)
            if mtu_m:
                out["mtu"] = int(mtu_m.group(1))
            # Eth-Trunk members: table "PortName Status Weight" (optional)
            members = []
            for line in block.split("\n"):
                line = line.strip()
                if re.match(r"^(GigabitEthernet|GE|Ethernet)\d+/\d+/\d+", line, re.IGNORECASE) and ("Up" in line or "DOWN" in line or "Master" in line):
                    parts = line.split()
                    if parts and is_valid_interface_name(parts[0]):
                        members.append(parts[0])
            if members:
                out["eth_trunk_members"] = members
            # Inference: when speed/duplex are null, infer from interface name (INTERFACE_STANDARDS)
            iface_name = out.get("name") or ""
            # Match longest prefix first (e.g. TenGigabitEthernet before GigabitEthernet before Ethernet)
            for prefix in sorted(INTERFACE_STANDARDS.keys(), key=len, reverse=True):
                if iface_name.startswith(prefix):
                    std = INTERFACE_STANDARDS[prefix]
                    if out.get("speed") is None and std.get("speed"):
                        out["speed"] = std["speed"]
                    if out.get("duplex") is None and std.get("duplex"):
                        out["duplex"] = std["duplex"]
                    break
            # Eth-Trunk: if speed was parsed (e.g. "2Gbps" from Current BW) but duplex is still None, force full
            if "Eth-Trunk" in iface_name or iface_name.startswith("Eth-Trunk"):
                if out.get("speed") and out.get("duplex") is None:
                    out["duplex"] = "full"
            return out
        except Exception:
            return None

    def _parse_display_interface_blocks(self, content: str) -> Dict[str, Dict[str, Any]]:
        """Block-based parser: find 'display interface' (not 'display interface description') section, split by 'current state :', extract each block."""
        # Prefer section that contains detailed blocks (current state : UP/DOWN), not the description table
        for pattern in [
            r'display\s+interface(?!\s+description)(\s*.*?)(?=display\s+|\n\s*<|$)',  # display interface without "description"
            r'display\s+interface\s*(.*?)(?=display\s+|\n\s*<|$)',
        ]:
            disp = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if disp:
                text = (disp.group(1) or "").strip()
                if "current state" in text and ("UP" in text or "DOWN" in text):
                    break
        else:
            disp = re.search(r'display\s+interface\s*(.*?)(?=display\s+|\n\s*<|$)', content, re.IGNORECASE | re.DOTALL)
            text = (disp.group(1) or "").strip() if disp else ""
        if not text or "current state" not in text:
            return {}
        blocks: Dict[str, Dict[str, Any]] = {}
        pattern = re.compile(r"^(\S+)\s+current\s+state\s*:\s*(UP|DOWN|ADM.*)", re.IGNORECASE | re.MULTILINE)
        starts = [m.start() for m in pattern.finditer(text)]
        for i, start in enumerate(starts):
            end = starts[i + 1] if i + 1 < len(starts) else len(text)
            block_text = text[start:end].strip()
            data = self._parse_one_display_interface_block(block_text)
            if data and data.get("name"):
                blocks[data["name"]] = data
        return blocks

    def _init_interface_huawei(self, canonical_name: str) -> Dict[str, Any]:
        """Return a single default interface record. Used so we never append; we only merge by key."""
        return {
            "name": canonical_name,
            "admin_status": "up",
            "oper_status": None,
            "line_protocol": None,
            "description": None,
            "ipv4_address": None,
            "ipv6_address": None,
            "mac_address": None,
            "speed": None,
            "duplex": None,
            "mtu": None,
            "port_mode": None,
            "access_vlan": None,
            "native_vlan": None,
            "allowed_vlans": None,
            "stp_role": None,
            "stp_state": None,
            "stp_edged_port": None,
        }

    def extract_interfaces(self, content: str) -> List[Dict[str, Any]]:
        """2.3.2.2 - Dictionary merging: one dict keyed by canonical interface name. Source A = config, Source B = status; merge into same entry. No duplicates."""
        interfaces_dict: Dict[str, Dict[str, Any]] = {}

        def _get_or_create(raw_name: str) -> Dict[str, Any]:
            key = _canonical_interface_name_huawei(raw_name)
            if key not in interfaces_dict:
                interfaces_dict[key] = self._init_interface_huawei(key)
            return interfaces_dict[key]

        # Source A: display interface description (Interface, PHY, Protocol, Description) - init/update by canonical key
        try:
            desc_section = re.search(r'display\s+interface\s+description(.*?)(?=display\s+|#\s*$|\n\s*<)', content, re.IGNORECASE | re.DOTALL)
            if desc_section:
                block = desc_section.group(1)
                for line in block.split('\n'):
                    line_stripped = line.strip()
                    if not line_stripped or ('PHY' in line_stripped and 'Protocol' in line_stripped):
                        continue
                    if line_stripped.startswith('*') or line_stripped.startswith('(') or line_stripped.startswith('-'):
                        continue
                    parts = line_stripped.split()
                    if len(parts) < 2:
                        continue
                    name = parts[0]
                    if not is_valid_interface_name(name) or 'NULL' in name.upper():
                        continue
                    phy = parts[1].lower() if len(parts) > 1 else 'up'
                    protocol = parts[2].lower() if len(parts) > 2 else 'up'
                    description = ' '.join(parts[3:]).strip() if len(parts) > 3 else None
                    if description and (description.startswith('*') or description == 'down' or description.startswith('---')):
                        description = None
                    admin_status = 'down' if phy in ('*down', 'down') else 'up'
                    iface = _get_or_create(name)
                    iface["admin_status"] = admin_status
                    iface["oper_status"] = phy if phy in ('up', 'down') else 'up'
                    iface["line_protocol"] = protocol if protocol in ('up', 'down') else 'up'
                    if description is not None:
                        iface["description"] = description
        except Exception:
            pass
        # Split content into lines for state machine processing (config interface blocks)
        lines = content.split('\n')
        current_interface = None
        current_config_lines = []
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # Check if this line starts a new interface block (config-style only; skip table headers)
            interface_match = re.match(r'^interface\s+(\S+)', line_stripped, re.IGNORECASE)
            if interface_match:
                candidate = interface_match.group(1)
                # Skip table headers and invalid names (PHY, IP, Protocol, Description, etc.)
                if not is_valid_interface_name(candidate):
                    if current_interface:
                        iface_config = '\n'.join(current_config_lines)
                        new_entry = self._parse_interface_config(current_interface, iface_config)
                        iface = _get_or_create(current_interface)
                        for k, v in new_entry.items():
                            if v is not None:
                                iface[k] = v
                    current_interface = None
                    current_config_lines = []
                    continue
                # Save previous interface if exists
                if current_interface:
                    iface_config = '\n'.join(current_config_lines)
                    new_entry = self._parse_interface_config(current_interface, iface_config)
                    iface = _get_or_create(current_interface)
                    for k, v in new_entry.items():
                        if v is not None:
                            iface[k] = v
                # Start new interface
                current_interface = candidate
                current_config_lines = []
                # Skip NULL0 and similar
                if "NULL" in (current_interface or "").upper():
                    current_interface = None
                    current_config_lines = []
                    continue
            elif line_stripped == '#' and current_interface:
                iface_config = '\n'.join(current_config_lines)
                iface = _get_or_create(current_interface)
                new_entry = self._parse_interface_config(current_interface, iface_config)
                for k, v in new_entry.items():
                    if v is not None:
                        iface[k] = v
                current_interface = None
                current_config_lines = []
            elif current_interface:
                current_config_lines.append(line)
        
        if current_interface:
            iface_config = '\n'.join(current_config_lines)
            iface = _get_or_create(current_interface)
            new_entry = self._parse_interface_config(current_interface, iface_config)
            for k, v in new_entry.items():
                if v is not None:
                    iface[k] = v
        
        # Enrich from "display interface description" (merge by canonical key)
        desc_section = re.search(r'display\s+interface\s+description(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if desc_section:
            for line in desc_section.group(1).split('\n'):
                parts = line.split()
                if len(parts) >= 3 and is_valid_interface_name(parts[0]):
                    name = parts[0]
                    key = _canonical_interface_name_huawei(name)
                    if key in interfaces_dict:
                        iface = interfaces_dict[key]
                        phy = parts[1].lower() if len(parts) > 1 else None
                        protocol = parts[2].lower() if len(parts) > 2 else None
                        if phy in ('up', 'down'):
                            iface["oper_status"] = phy
                        if protocol in ('up', 'down'):
                            iface["line_protocol"] = protocol
                        if len(parts) > 3 and parts[3] and not parts[3].startswith('*') and parts[3] != 'down':
                            desc = ' '.join(parts[3:]).strip()
                            if desc and len(desc) < 200 and not desc.startswith('---'):
                                iface["description"] = iface.get("description") or desc
        
        # Block-based "display interface" deep parse: Description, MAC (normalized), IP, PVID, port_mode, speed, Eth-Trunk members
        deep_blocks = self._parse_display_interface_blocks(content)
        def _is_real_description(s: str) -> bool:
            if not s or not isinstance(s, str):
                return False
            s = s.strip()
            if "Switch Port" in s or "PVID" in s or "Route Port" in s or "TPID" in s or "Maximum Frame" in s:
                return False
            return len(s) > 0 and len(s) < 200
        for raw_name, block_data in deep_blocks.items():
            key = _canonical_interface_name_huawei(raw_name)
            iface = _get_or_create(key)
            for k, v in block_data.items():
                if k == "name":
                    continue
                if k == "description":
                    if _is_real_description(v):
                        iface[k] = v
                    continue
                if v is not None and (iface.get(k) is None or (isinstance(v, (list, str)) and v)):
                    iface[k] = v
        
        # Source B: display ip interface brief - merge oper_status, line_protocol, ip (same key = update)
        ip_brief = re.search(r'display\s+ip\s+interface\s+brief(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if ip_brief:
            for line in ip_brief.group(1).split('\n'):
                parts = line.split()
                if len(parts) >= 4 and is_valid_interface_name(parts[0]):
                    name = parts[0]
                    ip_val = parts[1] if len(parts) > 1 else None
                    phy = parts[2].lower() if len(parts) > 2 else None
                    proto = parts[3].lower() if len(parts) > 3 else None
                    iface = _get_or_create(name)
                    if phy in ('up', 'down'):
                        iface["oper_status"] = iface.get("oper_status") or phy
                    if proto in ('up', 'down'):
                        iface["line_protocol"] = iface.get("line_protocol") or proto
                    if ip_val and ip_val != 'unassigned' and re.match(r'\d+\.\d+\.\d+\.\d+', ip_val):
                        iface["ipv4_address"] = iface.get("ipv4_address") or ip_val.split('/')[0]
        
        # Enrich interfaces with STP information from "display stp brief"
        # Format: MSTID  Port                        Role  STP State     Protection
        # Example:   0    GigabitEthernet0/0/1        DESI  FORWARDING      NONE
        stp_brief_section = re.search(r'display\s+stp\s+brief(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if stp_brief_section:
            brief_output = stp_brief_section.group(1)
            # Parse STP brief table to create a map of port -> (role, state)
            stp_port_map = {}
            lines = brief_output.split('\n')
            for line in lines:
                line_stripped = line.strip()
                # Skip header lines and separators
                if not line_stripped or 'MSTID' in line_stripped or ('Port' in line_stripped and 'Role' in line_stripped):
                    continue
                if line_stripped.startswith('---') or line_stripped.startswith('===') or line_stripped.startswith('<'):
                    continue
                
                parts = [p for p in line_stripped.split() if p]
                # Handle format: MSTID Port Role State Protection
                # MSTID is usually first (numeric), then Port, Role, State
                if len(parts) >= 4:
                    # Check if first part is numeric (MSTID)
                    if parts[0].isdigit():
                        # Format: "0    GigabitEthernet0/0/1        DESI  FORWARDING      NONE"
                        port = parts[1]
                        role = parts[2]
                        state = parts[3]
                    else:
                        # Format without MSTID: "Port Role State Protection"
                        port = parts[0]
                        role = parts[1]
                        state = parts[2]
                    
                    # Validate port name and role/state values
                    if is_valid_interface_name(port):
                        # Normalize role values (ROOT, DESI, ALTN, BACK, MAST)
                        role_upper = role.upper()
                        if role_upper in ['ROOT', 'DESI', 'ALTN', 'BACK', 'MAST', 'DISABLED']:
                            # Normalize state values (FORWARDING, DISCARDING, LEARNING, DISABLED)
                            state_upper = state.upper()
                            if state_upper in ['FORWARDING', 'DISCARDING', 'LEARNING', 'DISABLED', 'BLOCKING']:
                                stp_port_map[port] = {"role": role_upper, "state": state_upper}
            
            # Update interfaces with STP information
            # Handle interface name variations (e.g., "Ethernet0/0/1" vs "Eth0/0/1", "GigabitEthernet0/0/1" vs "GE0/0/1")
            for iface in interfaces_dict.values():
                iface_name = iface.get("name")
                if not iface_name:
                    continue
                
                # Try exact match first
                if iface_name in stp_port_map:
                    iface["stp_role"] = stp_port_map[iface_name]["role"]
                    iface["stp_state"] = stp_port_map[iface_name]["state"]
                else:
                    # Try normalized name matching for variations
                    # Normalize interface name for matching
                    normalized_name = iface_name.upper()
                    # Try different variations
                    name_variations = [
                        normalized_name,
                        normalized_name.replace("GIGABITETHERNET", "GE"),
                        normalized_name.replace("GE", "GIGABITETHERNET"),
                        normalized_name.replace("ETHERNET", "ETH"),
                        normalized_name.replace("ETH", "ETHERNET"),
                    ]
                    
                    # Find matching STP port
                    matched = False
                    for stp_port_name in stp_port_map.keys():
                        stp_port_normalized = stp_port_name.upper()
                        # Check if any variation matches
                        for variation in name_variations:
                            if variation == stp_port_normalized:
                                iface["stp_role"] = stp_port_map[stp_port_name]["role"]
                                iface["stp_state"] = stp_port_map[stp_port_name]["state"]
                                matched = True
                                break
                        if matched:
                            break
        
        # Final fallback: infer speed/duplex from INTERFACE_STANDARDS for any interface still missing them
        for iface in interfaces_dict.values():
            name = (iface.get("name") or "")
            if not name:
                continue
            for prefix in sorted(INTERFACE_STANDARDS.keys(), key=len, reverse=True):
                if name.startswith(prefix):
                    std = INTERFACE_STANDARDS[prefix]
                    if iface.get("speed") is None and std.get("speed"):
                        iface["speed"] = std["speed"]
                    if iface.get("duplex") is None and std.get("duplex"):
                        iface["duplex"] = std["duplex"]
                    break
            if "Eth-Trunk" in name or name.startswith("Eth-Trunk"):
                if iface.get("speed") and iface.get("duplex") is None:
                    iface["duplex"] = "full"
        
        # Convert dictionary values to list
        return list(interfaces_dict.values())
    
    def _parse_interface_config(self, iface_name: str, iface_config: str) -> Dict[str, Any]:
        """Parse configuration for a single interface"""
        iface = {
            "name": iface_name,
            "type": self._get_interface_type(iface_name),
            "admin_status": "down" if "shutdown" in iface_config.lower() else "up",
            "oper_status": None,  # Cannot be determined from config alone
            "description": None,
            "ipv4_address": None,
            "ipv6_address": None,
            "mac_address": None,
            "speed": None,
            "duplex": None,
            "mtu": None,
            "port_mode": None,
            "access_vlan": None,
            "native_vlan": None,
            "allowed_vlans": None,
            "stp_role": None,  # Will be populated from display stp brief
            "stp_state": None,  # Will be populated from display stp brief
            "stp_edged_port": None,  # Check if stp edged-port enable is configured
        }
        
        # Check for STP edged-port (portfast) on this interface
        if re.search(r'stp\s+edged-port\s+enable', iface_config, re.IGNORECASE):
            iface["stp_edged_port"] = True
        elif re.search(r'stp\s+edged-port\s+disable', iface_config, re.IGNORECASE):
            iface["stp_edged_port"] = False
        
        # Extract VRRP configuration from interface block
        # Format: "vrrp vrid <ID> virtual-ip <IP>"
        vrrp_vip_match = re.search(r'vrrp\s+vrid\s+(\d+)\s+virtual-ip\s+(\d+\.\d+\.\d+\.\d+)', iface_config, re.IGNORECASE)
        if vrrp_vip_match:
            vrid = vrrp_vip_match.group(1)
            virtual_ip = vrrp_vip_match.group(2)
            if is_valid_ipv4(virtual_ip):
                # Extract priority if present
                priority = None
                priority_match = re.search(r'vrrp\s+vrid\s+' + vrid + r'\s+priority\s+(\d+)', iface_config, re.IGNORECASE)
                if priority_match:
                    try:
                        priority = int(priority_match.group(1))
                    except ValueError:
                        pass
                
                # Store VRRP info in interface (will be extracted to HA section later)
                iface["vrrp_vrid"] = vrid
                iface["vrrp_virtual_ip"] = virtual_ip
                iface["vrrp_priority"] = priority
        
        # Extract description - improved regex to capture full description line
        # Format: "description TO-CORE1" or "description UPLINK_TO-DIST1_GE0/0/6"
        desc_match = re.search(r'description\s+(.+?)(?:\n|#|$)', iface_config, re.IGNORECASE | re.MULTILINE)
        if desc_match:
            description = desc_match.group(1).strip()
            # Remove any trailing whitespace or special characters
            description = description.rstrip()
            if description:
                iface["description"] = description
        
        # Extract IPv4 address - improved regex to handle various formats
        # Format: ip address <IP> <mask> or ip address <IP> <mask-length>
        ipv4_patterns = [
            r'ip\s+address\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+)',  # IP + subnet mask
            r'ip\s+address\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+)',  # IP + mask length
        ]
        for pattern in ipv4_patterns:
            ipv4_match = re.search(pattern, iface_config, re.IGNORECASE)
            if ipv4_match:
                ip_candidate = ipv4_match.group(1)
                # Validate IP address
                if is_valid_ipv4(ip_candidate):
                    iface["ipv4_address"] = ip_candidate
                iface["port_mode"] = "routed"
                break
        
        # Extract IPv6 address
        ipv6_match = re.search(r'ipv6\s+address\s+([\da-fA-F:]+/\d+)', iface_config, re.IGNORECASE)
        if ipv6_match:
            iface["ipv6_address"] = ipv6_match.group(1)
        
        # Extract port mode
        port_mode_match = re.search(r'port\s+link-type\s+(access|trunk|hybrid)', iface_config, re.IGNORECASE)
        if port_mode_match:
            iface["port_mode"] = port_mode_match.group(1).lower()
        
        # Extract access VLAN
        access_vlan_match = re.search(r'port\s+default\s+vlan\s+(\d+)', iface_config, re.IGNORECASE)
        if access_vlan_match:
            try:
                iface["access_vlan"] = int(access_vlan_match.group(1))
            except ValueError:
                pass
        
        # Extract native VLAN (PVID)
        native_vlan_match = re.search(r'port\s+trunk\s+pvid\s+vlan\s+(\d+)', iface_config, re.IGNORECASE)
        if native_vlan_match:
            try:
                iface["native_vlan"] = int(native_vlan_match.group(1))
            except ValueError:
                pass
        
        # Extract allowed VLANs
        allowed_vlans_match = re.search(r'port\s+trunk\s+allow-pass\s+vlan\s+(.+)', iface_config, re.IGNORECASE)
        if allowed_vlans_match:
            iface["allowed_vlans"] = allowed_vlans_match.group(1).strip()
        
        # Extract speed
        speed_match = re.search(r'speed\s+(\d+)', iface_config, re.IGNORECASE)
        if speed_match:
            iface["speed"] = speed_match.group(1)
        
        # Extract duplex
        duplex_match = re.search(r'duplex\s+(full|half|auto)', iface_config, re.IGNORECASE)
        if duplex_match:
            iface["duplex"] = duplex_match.group(1).lower()
        
        # Extract MTU
        mtu_match = re.search(r'mtu\s+(\d+)', iface_config, re.IGNORECASE)
        if mtu_match:
            try:
                iface["mtu"] = int(mtu_match.group(1))
            except ValueError:
                pass
        
        return iface
    
    def _get_interface_type(self, iface_name: str) -> Optional[str]:
        """Determine interface type from name (check Eth-Trunk before GE/ETH to avoid false match)"""
        iface_upper = iface_name.upper()
        if "ETH-TRUNK" in iface_upper:
            return "Eth-Trunk"
        if "GIGABITETHERNET" in iface_upper or (iface_upper.startswith("GE") and iface_upper[2:3].isdigit()):
            return "GigabitEthernet"
        if "ETHERNET" in iface_upper or (iface_upper.startswith("ETH") and "TRUNK" not in iface_upper):
            return "Ethernet"
        elif "VLANIF" in iface_upper:
            return "VLAN"
        elif "LOOPBACK" in iface_upper:
            return "Loopback"
        else:
            return None
    
    def _extract_vrrp_from_interface(self, interface_name: str, interface_config: str, vrrp_map: Dict[str, Any]):
        """Extract VRRP configuration from an interface config block"""
        # Parse VRRP virtual-ip: "vrrp vrid <ID> virtual-ip <IP>"
        vrrp_vip_pattern = r'vrrp\s+vrid\s+(\d+)\s+virtual-ip\s+(\d+\.\d+\.\d+\.\d+)'
        for vip_match in re.finditer(vrrp_vip_pattern, interface_config, re.IGNORECASE):
            vrid = vip_match.group(1)
            virtual_ip = vip_match.group(2)
            
            # Validate virtual IP
            if is_valid_ipv4(virtual_ip):
                # Use vrid as key to prevent duplicates
                if vrid not in vrrp_map:
                    vrrp_map[vrid] = {
                        "vrid": vrid,
                        "interface": interface_name,
                        "virtual_ip": virtual_ip,
                        "priority": None,  # Will be updated if found
                    }
                else:
                    # Update interface if not set
                    if not vrrp_map[vrid].get("interface"):
                        vrrp_map[vrid]["interface"] = interface_name
                    # Update virtual_ip if not set
                    if not vrrp_map[vrid].get("virtual_ip"):
                        vrrp_map[vrid]["virtual_ip"] = virtual_ip
        
        # Parse VRRP priority: "vrrp vrid <ID> priority <PRIORITY>"
        vrrp_priority_pattern = r'vrrp\s+vrid\s+(\d+)\s+priority\s+(\d+)'
        for priority_match in re.finditer(vrrp_priority_pattern, interface_config, re.IGNORECASE):
            vrid = priority_match.group(1)
            priority = priority_match.group(2)
            
            try:
                priority_int = int(priority)
                if vrid in vrrp_map:
                    vrrp_map[vrid]["priority"] = priority_int
                else:
                    # VRRP vrid exists but virtual-ip not found yet
                    vrrp_map[vrid] = {
                        "vrid": vrid,
                        "interface": interface_name,
                        "virtual_ip": None,
                        "priority": priority_int,
                    }
            except ValueError:
                pass
    
    def extract_vlans(self, content: str) -> Dict[str, Any]:
        """2.3.2.3 VLAN name, status, port memberships. Multi-source: config first, then display vlan."""
        details_by_id: Dict[int, Dict[str, Any]] = {}
        access_ports: List[str] = []
        trunk_ports: List[Dict[str, Any]] = []
        vlan_set = set()
        # Source 1 (Config): vlan batch, vlan N; interface blocks for access/trunk
        batch_match = re.search(r'vlan\s+batch\s+(.+)', content, re.IGNORECASE)
        if batch_match:
            for part in batch_match.group(1).strip().split():
                if '-' in part:
                    try:
                        start, end = map(int, part.split('-'))
                        vlan_set.update(range(start, end + 1))
                    except ValueError:
                        pass
                else:
                    try:
                        vlan_set.add(int(part))
                    except ValueError:
                        pass
        for match in re.finditer(r'vlan\s+(\d+)', content, re.IGNORECASE):
            try:
                vlan_set.add(int(match.group(1)))
            except ValueError:
                pass
        for vid in vlan_set:
            details_by_id[vid] = {"id": str(vid), "name": f"VLAN{vid:04d}" if vid <= 4094 else str(vid), "status": "active", "ports": []}
        for m in re.finditer(r'interface\s+(\S+)\s*\n(.*?)(?=\ninterface\s+|#\s*$|$)', content, re.IGNORECASE | re.DOTALL):
            iface_name, block = m.group(1), m.group(2)
            if "NULL" in (iface_name or "").upper():
                continue
            if re.search(r'port\s+link-type\s+access', block, re.IGNORECASE):
                access_ports.append(iface_name)
                def_vlan = re.search(r'port\s+default\s+vlan\s+(\d+)', block, re.IGNORECASE)
                if def_vlan:
                    vid = int(def_vlan.group(1))
                    if vid in details_by_id:
                        details_by_id[vid].setdefault("ports", []).append(iface_name)
            elif re.search(r'port\s+link-type\s+trunk', block, re.IGNORECASE):
                pvid_m = re.search(r'port\s+trunk\s+pvid\s+vlan\s+(\d+)', block, re.IGNORECASE)
                allow_m = re.search(r'port\s+trunk\s+allow-pass\s+vlan\s+(.+)', block, re.IGNORECASE)
                trunk_ports.append({
                    "port": iface_name,
                    "native_vlan": pvid_m.group(1) if pvid_m else "1",
                    "allowed_vlans": allow_m.group(1).strip() if allow_m else "all",
                })
        # Source 2 (Verbose): display vlan - skip headers (VID, Type, Ports, ----); ^(\d+)\s+(\S+)\s+(common)\s+(enable|disable) or ^(\d+)\s+(enable|disable)
        disp_vlan = re.search(r'display\s+vlan(.*?)(?=display\s+|#\s*$|\n\s*<)', content, re.IGNORECASE | re.DOTALL)
        vlan_ids_seen_in_table = set()
        if disp_vlan:
            block = disp_vlan.group(1)
            for line in block.split('\n'):
                line_strip = line.strip()
                if line_strip.startswith('VID') or line_strip.startswith('---') or line_strip.startswith('U:') or 'Ports' in line_strip and 'Type' in line_strip:
                    continue
                # VID Name common enable|disable
                vm = re.match(r'^\s*(\d+)\s+(\S+)\s+(common)\s+(enable|disable)', line_strip, re.IGNORECASE)
                if vm:
                    try:
                        vid = int(vm.group(1))
                        name = vm.group(2)
                        status = "active" if (vm.group(4) or "").lower() == "enable" else "inactive"
                        vlan_ids_seen_in_table.add(vid)
                    except (ValueError, IndexError):
                        continue
                    if vid not in details_by_id:
                        details_by_id[vid] = {"id": str(vid), "name": name, "status": status, "ports": []}
                    else:
                        details_by_id[vid]["name"] = name
                        details_by_id[vid]["status"] = status
                else:
                    # VID Status Property (e.g. "1    enable  default")
                    vm2 = re.match(r'^\s*(\d+)\s+(enable|disable)\s+(\S+)', line_strip, re.IGNORECASE)
                    if vm2:
                        try:
                            vid = int(vm2.group(1))
                            status = "active" if (vm2.group(2) or "").lower() == "enable" else "inactive"
                            vlan_ids_seen_in_table.add(vid)
                        except (ValueError, IndexError):
                            continue
                        if vid in details_by_id:
                            details_by_id[vid]["status"] = status
                        else:
                            details_by_id[vid] = {"id": str(vid), "name": f"VLAN{vid:04d}", "status": status, "ports": []}
        # Config-only VLANs: status = "Configured (Inactive)" when not in display vlan table
        if disp_vlan and vlan_ids_seen_in_table:
            for vid, d in list(details_by_id.items()):
                if vid not in vlan_ids_seen_in_table and d.get("status") == "active":
                    d["status"] = "Configured (Inactive)"
        vlan_list = [{"id": str(vid), "name": d["name"], "status": d.get("status", "active")} for vid, d in sorted(details_by_id.items())]
        details = [{"id": d["id"], "name": d["name"], "status": d.get("status", "active"), "ports": d.get("ports") or []} for d in sorted(details_by_id.values(), key=lambda x: int(x["id"]) if x["id"].isdigit() else 9999)]
        return {
            "vlan_list": vlan_list,
            "details": details,
            "access_ports": access_ports,
            "trunk_ports": trunk_ports,
            "total_vlan_count": len(details_by_id),
        }
    
    def extract_stp(self, content: str) -> Dict[str, Any]:
        """2.3.2.4 Spanning Tree Protocol"""
        stp = {
            "stp_mode": None,
            "bridge_priority": None,
            "root_bridge_id": None,
            "root_bridge_status": None,
            "portfast_enabled": None,
            "bpdu_guard": None,
            "interfaces": [],
        }
        
        # Extract STP mode from "display stp" output
        stp_section = re.search(r'display\s+stp(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if stp_section:
            stp_output = stp_section.group(1)
            
            # Extract STP mode: "Mode MSTP" or "Mode STP" or "Mode RSTP"
            mode_match = re.search(r'Mode\s+(STP|RSTP|MSTP)', stp_output, re.IGNORECASE)
            if mode_match:
                stp["stp_mode"] = mode_match.group(1).upper()
            
            # Extract bridge priority from "CIST Bridge :32768.4c1f-ccef-523c"
            bridge_match = re.search(r'CIST\s+Bridge\s*:\s*(\d+)\.', stp_output, re.IGNORECASE)
            if bridge_match:
                try:
                    stp["bridge_priority"] = int(bridge_match.group(1))
                except ValueError:
                    pass
            
            # Extract root bridge ID from "CIST Root/ERPC :32768.4c1f-cc46-27e4 / 10000"
            root_match = re.search(r'CIST\s+Root/ERPC\s*:\s*(\d+\.[\da-fA-F-]+)', stp_output, re.IGNORECASE)
            if root_match:
                stp["root_bridge_id"] = root_match.group(1)
                # Determine if this device is the root bridge
                # Compare root bridge ID with local bridge ID
                local_bridge_match = re.search(r'CIST\s+Bridge\s*:\s*([\d.]+)', stp_output, re.IGNORECASE)
                if local_bridge_match:
                    local_bridge_id = local_bridge_match.group(1)
                    root_bridge_id = root_match.group(1)
                    # If root bridge ID matches local bridge ID, this is the root
                    if root_bridge_id == local_bridge_id:
                        stp["root_bridge_status"] = True
                    else:
                        stp["root_bridge_status"] = False
        
        # Also check config for STP mode
        if not stp["stp_mode"]:
            stp_mode_match = re.search(r'stp\s+mode\s+(stp|rstp|mstp)', content, re.IGNORECASE)
            if stp_mode_match:
                stp["stp_mode"] = stp_mode_match.group(1).upper()
        
        # Extract STP interfaces from "display stp brief" - regex ^(\S+)\s+(DESI|ROOT|ALTE)\s+(FORWARDING|DISCARDING)
        stp_brief_section = re.search(r'display\s+stp\s+brief(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if stp_brief_section:
            brief_output = stp_brief_section.group(1)
            # Format: "0  GigabitEthernet0/0/1  DESI  FORWARDING" (MSTID optional first column)
            port_line_re = re.compile(r'^\s*(?:\d+\s+)?(\S+)\s+(DESI|ROOT|ALTE|BACK)\s+(FORWARDING|DISCARDING|LEARNING)', re.IGNORECASE)
            lines = brief_output.split('\n')
            for line in lines:
                line_stripped = line.strip()
                if not line_stripped:
                    continue
                if line_stripped.startswith('MSTID') or ('Port' in line_stripped and 'Role' in line_stripped) or line_stripped.startswith('---') or line_stripped.startswith('===') or line_stripped.startswith('<'):
                    continue
                pm = port_line_re.match(line_stripped)
                if pm:
                    port, role, state = pm.group(1), pm.group(2).upper(), pm.group(3).upper()
                    if is_valid_interface_name(port) and not any(x.get("port") == port for x in stp["interfaces"]):
                        stp["interfaces"].append({"port": port, "role": role, "state": state})
                else:
                    parts = [p for p in line_stripped.split() if p]
                    if len(parts) >= 4 and is_valid_interface_name(parts[1]):
                        port, role, state = parts[1], parts[2], parts[3]
                        if not any(x.get("port") == port for x in stp["interfaces"]):
                            stp["interfaces"].append({"port": port, "role": role, "state": state})
        
        # Check for portfast (edged-port)
        if re.search(r'stp\s+edged-port\s+default', content, re.IGNORECASE):
            stp["portfast_enabled"] = True
        elif re.search(r'stp\s+edged-port\s+enable', content, re.IGNORECASE):
            stp["portfast_enabled"] = True
        
        # Check for BPDU guard
        if re.search(r'stp\s+bpdu-protection', content, re.IGNORECASE):
            stp["bpdu_guard"] = True
        
        return stp
    
    def extract_routing(self, content: str) -> Dict[str, Any]:
        """2.3.2.5 Routing Information"""
        routing = {
            "static": [],
            "ospf": None,
            "rip": None,
            "bgp": None,
        }
        
        # Parse static routes - CRITICAL FIX: Column shift bug
        # Format: ip route-static <network> <mask> <nexthop|interface>
        # Example: ip route-static 0.0.0.0 0.0.0.0 203.0.113.1
        #          ip route-static 10.10.30.0 255.255.255.0 203.0.113.2
        #          ip route-static 10.10.0.0 24 GigabitEthernet0/0/1
        # STRICT REGEX: Matches exactly 3 groups - network (IP), mask (IP or CIDR), nexthop/interface
        static_pattern = r'ip\s+route-static\s+(\d{1,3}(?:\.\d{1,3}){3})\s+(\d{1,3}(?:\.\d{1,3}){3}|\d{1,2})\s+(\S+)'
        
        # Process line by line for better control
        lines = content.split('\n')
        for line in lines:
            line_stripped = line.strip()
            
            # Skip error lines and comments
            if line_stripped.startswith('Error:') or line_stripped.startswith('#') or not line_stripped:
                continue
            
            match = re.search(static_pattern, line_stripped, re.IGNORECASE)
            if not match:
                continue
            
            network = match.group(1)
            mask_candidate = match.group(2)
            next_hop_candidate = match.group(3)
            
            # Validate network is a valid IP address
            if not is_valid_ipv4(network):
                continue
            
            # Validate and normalize mask
            mask = None
            if '.' in mask_candidate:
                # Subnet mask format (e.g., 255.255.255.0)
                if is_valid_ipv4(mask_candidate):
                    mask = mask_candidate
                else:
                    continue  # Invalid mask format - skip
            elif mask_candidate.isdigit():
                # CIDR format (e.g., 24) - validate range 0-32
                try:
                    cidr = int(mask_candidate)
                    if 0 <= cidr <= 32:
                        mask = mask_candidate
                    else:
                        continue  # Invalid CIDR - skip
                except ValueError:
                    continue  # Not a valid number - skip
            else:
                continue  # Invalid mask format - skip
            
            # CRITICAL: Determine if next_hop_candidate is IP or interface
            # Use strict IP validation regex
            ip_pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
            nexthop = None
            interface = None
            
            if re.match(ip_pattern, next_hop_candidate):
                # It's a valid IP address format - validate it properly
                if is_valid_ipv4(next_hop_candidate):
                    nexthop = next_hop_candidate
                    interface = None
                else:
                    # Invalid IP format - skip this route
                    continue
            else:
                # It's NOT an IP - must be an interface name
                if is_valid_interface_name(next_hop_candidate):
                    interface = next_hop_candidate
                    nexthop = None
                else:
                    # Invalid interface name - skip this route
                    continue
            
            # Sanity check: Ensure mask is NEVER assigned to nexthop
            if mask == nexthop:
                # This should never happen, but if it does, skip
                continue
            
            routing["static"].append({
                "network": network,
                "mask": mask,
                "nexthop": nexthop,
                "interface": interface,
                "admin_distance": 60,
            })
        
        # Parse OSPF config + operational (display ospf peer)
        ospf_config_m = re.search(r'ospf\s+(\d+)\s+router-id\s+(\d+\.\d+\.\d+\.\d+)\s*(.*?)(?=\n#|$)', content, re.IGNORECASE | re.DOTALL)
        if ospf_config_m:
            try:
                process_id = int(ospf_config_m.group(1))
                router_id_candidate = ospf_config_m.group(2)
                body = ospf_config_m.group(3)
                ospf_info = {
                    "process_id": process_id,
                    "router_id": router_id_candidate if is_valid_ipv4(router_id_candidate) else None,
                    "areas": [],
                    "networks": [],
                    "neighbors": [],
                }
                for area_match in re.finditer(r'area\s+(\d+(?:\.\d+)*)', body, re.IGNORECASE):
                    area = area_match.group(1)
                    if area not in ospf_info["areas"]:
                        ospf_info["areas"].append(area)
                for net_match in re.finditer(r'network\s+(\S+)', body, re.IGNORECASE):
                    network = net_match.group(1)
                    if network not in ospf_info["networks"]:
                        ospf_info["networks"].append(network)
                routing["ospf"] = ospf_info
            except (ValueError, AttributeError):
                pass
        # OSPF operational: display ospf peer - Neighbor ID Pri State Dead Time Address Interface
        ospf_peer = re.search(r'display\s+ospf\s+peer(.*?)(?=display\s+|#\s*$|\n\s*<)', content, re.IGNORECASE | re.DOTALL)
        if ospf_peer and routing.get("ospf"):
            block = ospf_peer.group(1)
            for line in block.split('\n'):
                # (\d+\.\d+\.\d+\.\d+)\s+(\d+)\s+(FULL|2-Way|Down|...)
                neigh_m = re.search(r'(\d+\.\d+\.\d+\.\d+)\s+(\d+)\s+(FULL|2-Way|Down|Init|ExStart|Exchange|Loading)', line, re.IGNORECASE)
                if neigh_m and is_valid_ipv4(neigh_m.group(1)):
                    routing["ospf"]["neighbors"].append({
                        "neighbor_id": neigh_m.group(1),
                        "priority": int(neigh_m.group(2)),
                        "state": neigh_m.group(3),
                    })
        
        # Parse RIP
        rip_match = re.search(r'rip\s+(\d+)', content, re.IGNORECASE)
        if rip_match:
            try:
                process_id = int(rip_match.group(1))
                rip_info = {
                    "process_id": process_id,
                    "version": None,
                    "networks": [],
                    "passive_interfaces": [],
                }
                rip_section = re.search(r'rip\s+\d+(.*?)(?=\n\w+\s+\d+|#|$)', content, re.IGNORECASE | re.DOTALL)
                if rip_section:
                    for pass_m in re.finditer(r'silent-interface\s+(\S+)', rip_section.group(1), re.IGNORECASE):
                        rip_info["passive_interfaces"].append(pass_m.group(1))
                # Extract version
                version_match = re.search(r'rip\s+\d+.*?version\s+(\d+)', content, re.IGNORECASE | re.DOTALL)
                if version_match:
                    try:
                        rip_info["version"] = int(version_match.group(1))
                    except ValueError:
                        pass
                
                # Extract networks
                rip_section = re.search(r'rip\s+\d+(.*?)(?=\n\w+\s+\d+|#|$)', content, re.IGNORECASE | re.DOTALL)
                if rip_section:
                    network_matches = re.finditer(r'network\s+(\S+)', rip_section.group(1), re.IGNORECASE)
                    for net_match in network_matches:
                        network = net_match.group(1)
                        if network not in rip_info["networks"]:
                            rip_info["networks"].append(network)
                
                routing["rip"] = rip_info
            except (ValueError, AttributeError):
                pass
        
        # Parse BGP - Extract AS number, router-id, and peers
        bgp_match = re.search(r'bgp\s+(\d+)', content, re.IGNORECASE)
        if bgp_match:
            try:
                as_number = int(bgp_match.group(1))
                bgp_info = {
                    "as_number": as_number,
                    "router_id": None,
                    "peers": [],
                }
                
                # Extract BGP section to find router-id and peers within the same BGP process
                bgp_section = re.search(r'bgp\s+\d+(.*?)(?=\n\w+\s+\d+|#|$)', content, re.IGNORECASE | re.DOTALL)
                if bgp_section:
                    bgp_config = bgp_section.group(1)
                    
                    # Extract router-id from BGP section
                    router_id_match = re.search(r'router-id\s+(\S+)', bgp_config, re.IGNORECASE)
                    if router_id_match:
                        router_id_candidate = router_id_match.group(1)
                        # Validate router-id is a valid IP address
                        if is_valid_ipv4(router_id_candidate):
                            bgp_info["router_id"] = router_id_candidate
                    
                    # Extract peers from BGP section
                    # Format: "peer <IP> as-number <AS>"
                    peer_pattern = r'peer\s+(\S+)\s+as-number\s+(\d+)'
                    for peer_match in re.finditer(peer_pattern, bgp_config, re.IGNORECASE):
                        try:
                            peer_ip = peer_match.group(1)
                            remote_as = int(peer_match.group(2))
                            
                            # Validate peer IP
                            if is_valid_ipv4(peer_ip):
                                # Check if peer already exists
                                if not any(p.get("peer") == peer_ip for p in bgp_info["peers"]):
                                    bgp_info["peers"].append({
                                        "peer": peer_ip,
                                        "remote_as": remote_as,
                                        "state": "configured_but_down",
                                        "prefixes_received": None,
                                    })
                        except ValueError:
                            pass
                
                routing["bgp"] = bgp_info
            except (ValueError, AttributeError):
                pass
        # BGP operational: display bgp peer - Neighbor IP, State, PfxRcd
        bgp_peer = re.search(r'display\s+bgp\s+peer(.*?)(?=display\s+|#\s*$|\n\s*<)', content, re.IGNORECASE | re.DOTALL)
        if bgp_peer and routing.get("bgp"):
            block = bgp_peer.group(1)
            for line in block.split('\n'):
                peer_m = re.search(r'(\d+\.\d+\.\d+\.\d+)\s+\d+\s+(\d+).*?(Established|Idle|Active|Connect)', line, re.IGNORECASE)
                if peer_m and is_valid_ipv4(peer_m.group(1)):
                    ip, ras, state = peer_m.group(1), int(peer_m.group(2)), peer_m.group(3)
                    pfxs = re.search(r'(\d+)\s*$', line)
                    existing = next((p for p in routing["bgp"]["peers"] if p.get("peer") == ip), None)
                    if existing:
                        existing["state"] = state
                        existing["prefixes_received"] = int(pfxs.group(1)) if pfxs else None
                    else:
                        routing["bgp"]["peers"].append({"peer": ip, "remote_as": ras, "state": state, "prefixes_received": int(pfxs.group(1)) if pfxs else None})
        
        # Parse "display ip routing-table" / "display ip routing-table brief" for full route table (same as Cisco)
        route_table_section = re.search(
            r"display\s+ip\s+routing-table(?:\s+brief)?\s*(.*?)(?=display\s+|#\s*$|\n\s*<)",
            content,
            re.IGNORECASE | re.DOTALL,
        )
        if route_table_section:
            block = route_table_section.group(1)
            # Proto mapping: Huawei -> single letter (match Cisco); O_ASE = OSPF external
            proto_map = {
                "static": "S", "direct": "C", "ospf": "O", "rip": "R", "bgp": "B",
                "isis": "i", "is-is": "i", "unr": "U", "ospfv3": "O",
                "o_ase": "O",
            }
            # Full line: Destination/Mask Proto Pre Cost Flags NextHop Interface
            full_line_re = re.compile(
                r"^\s*(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?:/\d{1,2})?)\s+(\S+)\s+\d+\s+\d+\s+\S+\s+(\S+)\s+(\S+)\s*$",
            )
            # Continuation line (same destination, multi-path): spaces then Proto Pre Cost Flags NextHop Interface
            cont_line_re = re.compile(r"^\s*(\S+)\s+\d+\s+\d+\s+\S+\s+(\S+)\s+(\S+)\s*$")
            routes = []
            last_network = None
            for line in block.split("\n"):
                line_stripped = line.strip()
                if not line_stripped:
                    continue
                if "Destination" in line_stripped and "Mask" in line_stripped:
                    continue
                if line_stripped.startswith("-") or "Route Flags" in line_stripped or "Routing Tables" in line_stripped or "Destinations " in line_stripped:
                    continue
                m = full_line_re.match(line_stripped)
                if m:
                    network, proto_str, next_hop, interface = m.group(1), m.group(2), m.group(3), m.group(4)
                    if not is_valid_ipv4(network.split("/")[0]):
                        continue
                    if "/" not in network and re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", network):
                        network = network + "/32"
                    last_network = network
                    proto = proto_map.get((proto_str or "").lower()) or (proto_str[:1].upper() if proto_str else "?")
                    next_hop_val = next_hop if (next_hop and next_hop != "-" and is_valid_ipv4(next_hop)) else ""
                    iface_val = (interface or "").strip() if (interface and interface != "-") else ""
                    routes.append({
                        "protocol": proto,
                        "network": network,
                        "next_hop": next_hop_val,
                        "interface": iface_val,
                    })
                    continue
                mc = cont_line_re.match(line_stripped)
                if mc and last_network:
                    proto_str, next_hop, interface = mc.group(1), mc.group(2), mc.group(3)
                    # Continuation: first token must be protocol name (no leading digit like an IP)
                    if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", proto_str):
                        continue
                    proto = proto_map.get((proto_str or "").lower()) or (proto_str[:1].upper() if proto_str else "?")
                    next_hop_val = next_hop if (next_hop and next_hop != "-" and is_valid_ipv4(next_hop)) else ""
                    iface_val = (interface or "").strip() if (interface and interface != "-") else ""
                    routes.append({
                        "protocol": proto,
                        "network": last_network,
                        "next_hop": next_hop_val,
                        "interface": iface_val,
                    })
            if routes:
                routing["routes"] = routes
        
        return routing
    
    def extract_neighbors(self, content: str) -> List[Dict[str, Any]]:
        """2.3.2.6 Neighbor & Topology"""
        neighbors = []
        
        # Check for display lldp neighbor output - Parse with strict column structure
        lldp_section = re.search(r'display\s+lldp\s+neighbor\s+brief(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if not lldp_section:
            # Try without "brief"
            lldp_section = re.search(r'display\s+lldp\s+neighbor(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
        
        if lldp_section and "No LLDP" not in lldp_section.group(1):
            lldp_output = lldp_section.group(1)
            
            # Parse brief format: "Local Intf | Neighbor Dev | Neighbor Intf"
            # Look for header line first
            header_match = re.search(r'Local\s+Intf.*?Neighbor\s+Dev.*?Neighbor\s+Intf', lldp_output, re.IGNORECASE)
            if header_match:
                # Find the data lines after header
                header_end = header_match.end()
                data_section = lldp_output[header_end:]
                # Skip separator lines (---)
                data_lines = [line.strip() for line in data_section.split('\n') if line.strip() and not line.strip().startswith('---')]
                
                for line in data_lines:
                    # Skip header lines
                    if any(kw in line.lower() for kw in ['local', 'neighbor', 'intf', 'dev']):
                        continue
                    parts = [p for p in line.split() if p]
                    if len(parts) >= 3:
                        local_port = parts[0]
                        device_name = parts[1]
                        remote_port = parts[2]
                        # Validate local_port is an interface name
                        if not is_valid_interface_name(local_port):
                            continue
                        # Check if already added (prevent duplicates)
                        if not any(n.get("device_name") == device_name and n.get("local_port") == local_port for n in neighbors):
                            neighbors.append({
                                "device_name": device_name,
                                "local_port": local_port,
                                "remote_port": remote_port,
                                "ip_address": None,
                            })
            
            # Also parse detailed format if brief format didn't find anything
            if not neighbors:
                neighbor_pattern = r'(\S+)\s+has\s+\d+\s+neighbors:(.*?)(?=\n\S+\s+has\s+\d+\s+neighbors:|display|#|$)'
                for match in re.finditer(neighbor_pattern, lldp_output, re.IGNORECASE | re.DOTALL):
                    local_port = match.group(1)
                    neighbor_details = match.group(2)
                    # Validate local_port
                    if not is_valid_interface_name(local_port):
                        continue
                    # Extract system name (SysName: or System name:)
                    system_name_match = re.search(r'SysName\s*:\s*(\S+)', neighbor_details, re.IGNORECASE)
                    if not system_name_match:
                        system_name_match = re.search(r'System\s+name\s*:\s*(\S+)', neighbor_details, re.IGNORECASE)
                    device_name = system_name_match.group(1) if system_name_match else None
                    if not device_name:
                        continue
                    # Extract remote port (PortID: or Port ID:)
                    port_id_match = re.search(r'PortID\s*:\s*(\S+)', neighbor_details, re.IGNORECASE)
                    if not port_id_match:
                        port_id_match = re.search(r'Port\s+ID\s*:\s*(\S+)', neighbor_details, re.IGNORECASE)
                    remote_port = port_id_match.group(1) if port_id_match else None
                    # Extract IP (Management Address : or Management address :)
                    ip_match = re.search(r'Management\s+Address\s*:\s*(\d+\.\d+\.\d+\.\d+)', neighbor_details, re.IGNORECASE)
                    if not ip_match:
                        ip_match = re.search(r'Management\s+address\s*:\s*(\d+\.\d+\.\d+\.\d+)', neighbor_details, re.IGNORECASE)
                    ip_address = ip_match.group(1) if ip_match and is_valid_ipv4(ip_match.group(1)) else None
                    # Check if already added
                    if not any(n.get("device_name") == device_name and n.get("local_port") == local_port for n in neighbors):
                        neighbors.append({
                            "device_name": device_name,
                            "local_port": local_port,
                            "remote_port": remote_port,
                            "ip_address": ip_address,
                        })
        
        return neighbors
    
    def extract_mac_arp(self, content: str) -> Dict[str, Any]:
        """2.3.2.7 MAC & ARP - Filter garbage data"""
        mac_arp = {
            "mac_table": None,
            "arp_table": None,
        }
        
        # Check for display mac-address - skip header lines (Vlan, Mac Address, Type, Interface, ----, Total)
        mac_section = re.search(r'display\s+mac-address(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if mac_section and "No MAC" not in mac_section.group(1):
            mac_table = []
            mac_lines = mac_section.group(1).strip().split('\n')
            for line in mac_lines:
                line = line.strip()
                if not line:
                    continue
                if any(kw in line for kw in ('----', 'Vlan', 'Mac Address', 'Type', 'Interface', 'Total', 'Protocol', 'Address')):
                    continue
                if line.startswith('---'):
                    continue
                # Regex: MAC (XXXX-XXXX-XXXX) VLAN port type - ([0-9a-f-]{14}) \s+ (\d+|-)\s+(\S+)\s+(\S+)
                mac_m = re.match(r'([0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4})\s+(\d+|-)\s+(\S+)\s+(\S+)', line)
                if mac_m:
                    mac_addr, vlan_s, col3, col4 = mac_m.group(1), mac_m.group(2), mac_m.group(3), mac_m.group(4)
                    if not is_valid_mac_address(mac_addr):
                        continue
                    vlan = int(vlan_s) if vlan_s != '-' and vlan_s.isdigit() else None
                    port = col3 if is_valid_interface_name(col3) else (col4 if is_valid_interface_name(col4) else None)
                    mac_table.append({"mac_address": mac_addr, "vlan": vlan, "port": port})
                else:
                    # Fallback: column-based
                    parts = line.split()
                    if len(parts) >= 3 and is_valid_mac_address(parts[0]):
                        vlan = int(parts[1]) if parts[1].isdigit() else None
                        port = None
                        for i in range(2, min(len(parts), 6)):
                            if is_valid_interface_name(parts[i]):
                                port = parts[i]
                                break
                        if not port and len(parts) > 2 and is_valid_interface_name(parts[-1]):
                            port = parts[-1]
                        mac_table.append({"mac_address": parts[0], "vlan": vlan, "port": port})
            if mac_table:
                mac_arp["mac_table"] = mac_table
        
        # Check for display arp
        arp_section = re.search(r'display\s+arp(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if arp_section and "No ARP" not in arp_section.group(1):
            arp_table = []
            arp_lines = arp_section.group(1).strip().split('\n')
            for line in arp_lines:
                line = line.strip()
                
                # Guard clauses: Filter garbage lines
                if not line:
                    continue
                if line.startswith('---') or '---' in line:
                    continue
                if any(keyword in line for keyword in ['IP ADDRESS', 'Total:', 'Dynamic:', 'Static:', 'Interface:', 'Slot', 'Type', 'Protocol', 'Address', 'Vlan']):
                    continue
                
                parts = line.split()
                if len(parts) >= 2:
                    ip_candidate = parts[0]
                    mac_addr = parts[1]
                    
                    # Strict IP validation - reject "Total:10" or similar
                    if not is_valid_ipv4(ip_candidate):
                        continue
                    # CRITICAL: Validate MAC address format - reject garbage
                    if not is_valid_mac_address(mac_addr):
                        continue
                    
                    # Find interface dynamically - usually last or second-to-last column
                    # ARP format: IP MAC [EXPIRE] TYPE INTERFACE [VLAN]
                    interface = None
                    
                    # Try last column first (most common position)
                    if len(parts) > 2:
                        for i in range(len(parts) - 1, 1, -1):  # Start from end, go backwards
                            candidate = parts[i]
                            if is_valid_interface_name(candidate):
                                interface = candidate
                                break
                    
                    # If not found, try second-to-last (in case VLAN is last)
                    if not interface and len(parts) > 3:
                        for i in range(len(parts) - 2, 1, -1):
                            candidate = parts[i]
                            if is_valid_interface_name(candidate):
                                interface = candidate
                                break
                    
                    arp_table.append({
                        "ip_address": ip_candidate,
                        "mac_address": mac_addr,
                        "interface": interface,  # Can be None if not found
                    })
            
            if arp_table:
                mac_arp["arp_table"] = arp_table
        
        return mac_arp
    
    def extract_security(self, content: str) -> Dict[str, Any]:
        """2.3.2.8 Security & Management"""
        security = {
            "user_accounts": [],
            "ssh_enabled": None,
            "snmp_settings": None,
            "ntp_server": None,
            "syslog": None,
            "acls": None,
        }
        
        # Extract user accounts with privilege levels - Filter separator usernames
        # Parse local-user blocks to extract username and privilege level
        user_pattern = r'local-user\s+(\S+)(.*?)(?=local-user|#|$)'
        for match in re.finditer(user_pattern, content, re.IGNORECASE | re.DOTALL):
            username = match.group(1)
            user_config = match.group(2)
            
            # Validate username - filter out separators and garbage
            if not is_valid_username(username):
                    continue
            
            # Extract privilege level from user config block
            privilege_level = None
            privilege_match = re.search(r'privilege\s+level\s+(\d+)', user_config, re.IGNORECASE)
            if privilege_match:
                try:
                    privilege_level = int(privilege_match.group(1))
                except ValueError:
                    pass
            
            # Check if user already exists
            existing_user = next((u for u in security["user_accounts"] if u.get("username") == username), None)
            if not existing_user:
                security["user_accounts"].append({
                    "username": username,
                    "privilege_level": privilege_level,
                })
            elif privilege_level is not None and existing_user.get("privilege_level") is None:
                # Update privilege level if not set
                existing_user["privilege_level"] = privilege_level
        
        # Check SSH enabled
        if re.search(r'stelnet\s+server\s+enable', content, re.IGNORECASE):
            security["ssh_enabled"] = True
        elif re.search(r'protocol\s+inbound\s+ssh', content, re.IGNORECASE):
            security["ssh_enabled"] = True
        else:
            security["ssh_enabled"] = False
        
        # Extract SNMP settings
        snmp_community_match = re.search(r'snmp-agent\s+community\s+read\s+(\S+)', content, re.IGNORECASE)
        if snmp_community_match:
            snmp_settings = {
                "community": snmp_community_match.group(1),
                "version": None,
            }
            
            # Extract version
            version_match = re.search(r'snmp-agent\s+sys-info\s+version\s+(.+)', content, re.IGNORECASE)
            if version_match:
                snmp_settings["version"] = version_match.group(1).strip()
            
            security["snmp_settings"] = snmp_settings
        
        # Extract NTP server
        ntp_match = re.search(r'ntp-service\s+unicast-server\s+(\S+)', content, re.IGNORECASE)
        if ntp_match:
            security["ntp_server"] = ntp_match.group(1)
        
        # Extract syslog
        syslog_match = re.search(r'info-center\s+loghost\s+(\S+)', content, re.IGNORECASE)
        if syslog_match:
            security["syslog"] = syslog_match.group(1)
        
        # Extract ACLs with rules - Use dictionary to prevent duplicates
        acl_map = {}
        
        # Parse ACL blocks: "acl number X" or "acl name X" ... "rule Y permit/deny protocol ..."
        lines = content.split('\n')
        current_acl = None
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Skip comments and empty lines
            if not line_stripped or line_stripped.startswith('!'):
                continue
            
            # Check if this line starts a new ACL block - acl (name|number) (\S+)
            acl_start_match = re.match(r'acl\s+(?:name|number)\s+(\S+)', line_stripped, re.IGNORECASE)
            if not acl_start_match:
                acl_start_match = re.match(r'acl\s+(\d+)(?:\s|$)', line_stripped)  # acl 3000
            if acl_start_match:
                acl_id = acl_start_match.group(1)
                # Filter out garbage keywords
                if acl_id.lower() not in ['is', 'name', 'number', 'advance', 'basic', 'match-order']:
                    current_acl = acl_id
                    # Ensure ACL exists in map
                    if current_acl not in acl_map:
                        acl_map[current_acl] = {
                            "acl_number": current_acl,
                            "rules": [],
                        }
            elif line_stripped == '#' and current_acl:
                # End of ACL block
                current_acl = None
            elif current_acl and current_acl in acl_map:
                # Parse rule within ACL block
                # Format: "rule <id> permit/deny [protocol] [source <network> <mask>] [destination <network> <mask>]"
                # Examples:
                #   "rule 5 permit tcp source 10.0.0.0 0.0.0.255 destination 20.0.0.0 0.0.0.255"
                #   "rule 10 deny ip source 192.168.1.0 0.0.0.255"
                #   "rule 15 permit icmp"
                #   "rule 5 permit source 10.0.0.0 0.0.0.255"  # Simpler format without protocol
                
                # Initialize variables
                rule_id = None
                action = None
                protocol = None
                source = None
                destination = None
                
                # Try comprehensive pattern first
                rule_match = re.search(r'rule\s+(\d+)\s+(permit|deny)(?:\s+(\S+))?(?:\s+source\s+(\S+)(?:\s+(\S+))?)?(?:\s+destination\s+(\S+)(?:\s+(\S+))?)?', line_stripped, re.IGNORECASE)
                
                if rule_match and len(rule_match.groups()) >= 7:
                    # Comprehensive pattern matched
                    rule_id = rule_match.group(1)
                    action = rule_match.group(2).lower()
                    protocol_candidate = rule_match.group(3) if rule_match.group(3) else None
                    source_network = rule_match.group(4) if rule_match.group(4) else None
                    source_mask = rule_match.group(5) if rule_match.group(5) else None
                    dest_network = rule_match.group(6) if rule_match.group(6) else None
                    dest_mask = rule_match.group(7) if rule_match.group(7) else None
                    
                    # Determine protocol - common protocols
                    if protocol_candidate:
                        protocol_lower = protocol_candidate.lower()
                        if protocol_lower in ['tcp', 'udp', 'icmp', 'ip', 'gre', 'ospf', 'bgp']:
                            protocol = protocol_lower
                        elif is_valid_ipv4(protocol_candidate) or '/' in protocol_candidate:
                            # It's an IP address or network, protocol might be implicit (ip)
                            protocol = "ip"
                    
                    # Format source and destination
                    if source_network:
                        if source_mask and is_valid_ipv4(source_mask):
                            source = f"{source_network} {source_mask}"
                        elif source_mask and source_mask.isdigit():
                            source = f"{source_network}/{source_mask}"
                        else:
                            source = source_network
                    if dest_network:
                        if dest_mask and is_valid_ipv4(dest_mask):
                            destination = f"{dest_network} {dest_mask}"
                        elif dest_mask and dest_mask.isdigit():
                            destination = f"{dest_network}/{dest_mask}"
                        else:
                            destination = dest_network
                else:
                    # Try simpler pattern: "rule <id> permit/deny source <network> <mask>"
                    simple_match = re.search(r'rule\s+(\d+)\s+(permit|deny)\s+source\s+(\S+)(?:\s+(\S+))?', line_stripped, re.IGNORECASE)
                    if simple_match:
                        rule_id = simple_match.group(1)
                        action = simple_match.group(2).lower()
                        source_network = simple_match.group(3)
                        source_mask = simple_match.group(4) if simple_match.group(4) else None
                        
                        # Format source
                        if source_mask and is_valid_ipv4(source_mask):
                            source = f"{source_network} {source_mask}"
                        elif source_mask and source_mask.isdigit():
                            source = f"{source_network}/{source_mask}"
                        else:
                            source = source_network
                        protocol = "ip"  # Default to IP when protocol not specified
                
                # If we found a rule, add it
                if rule_id and action:
                    # Check if rule already exists
                    existing_rule = next((r for r in acl_map[current_acl]["rules"] if r.get("id") == rule_id), None)
                    if not existing_rule:
                        # Extract source IP and mask separately for detailed analysis
                        source_ip = None
                        source_mask = None
                        if source:
                            # Parse "10.0.10.0 0.0.0.255" or "10.0.10.0/24"
                            source_parts = source.split()
                            if len(source_parts) == 2:
                                source_ip = source_parts[0]
                                source_mask = source_parts[1]
                            elif '/' in source:
                                source_ip, source_mask = source.split('/', 1)
                            else:
                                source_ip = source
                        
                        # Extract destination IP and mask separately
                        dest_ip = None
                        dest_mask = None
                        if destination:
                            dest_parts = destination.split()
                            if len(dest_parts) == 2:
                                dest_ip = dest_parts[0]
                                dest_mask = dest_parts[1]
                            elif '/' in destination:
                                dest_ip, dest_mask = destination.split('/', 1)
                            else:
                                dest_ip = destination
                        
                        # Ensure action and source are always present (required fields)
                        rule_obj = {
                            "id": rule_id,
                            "action": action,  # Required: permit or deny
                            "protocol": protocol or "N/A",
                            "source": source or None,  # Required field
                            "source_ip": source_ip,
                            "source_mask": source_mask,
                            "destination": destination,
                            "destination_ip": dest_ip,
                            "destination_mask": dest_mask,
                        }
                        
                        # Only add if action and source are valid
                        if action and (source or source_ip):  # At least source or source_ip should be present
                            acl_map[current_acl]["rules"].append(rule_obj)
        
        # Return empty list if no ACLs found (for consistency)
        # Ensure each ACL has a rules list (even if empty)
        acl_list = []
        for acl in acl_map.values():
            # Ensure rules is always a list
            if "rules" not in acl:
                acl["rules"] = []
            # Only include ACLs that have at least one rule or are explicitly defined
            if acl.get("rules") or acl.get("acl_number"):
                acl_list.append(acl)
        security["acls"] = acl_list
        
        return security
    
    def extract_ha(self, content: str) -> Dict[str, Any]:
        """2.3.2.9 High Availability - Dictionary-based to prevent duplicates"""
        ha = {
            "etherchannel": [],
            "vrrp": [],
        }
        
        # Dictionary keyed by trunk ID to prevent duplicates
        ether_trunk_map = {}
        
        # First pass: Extract Eth-Trunk interface definitions
        lines = content.split('\n')
        current_trunk_id = None
        current_trunk_config = []
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Check if this line starts a new Eth-Trunk interface
            trunk_match = re.match(r'^interface\s+Eth-Trunk\s*(\d+)', line_stripped, re.IGNORECASE)
            if trunk_match:
                # Save previous trunk if exists
                if current_trunk_id and current_trunk_id not in ether_trunk_map:
                    trunk_config = '\n'.join(current_trunk_config)
                    mode = None
                    if "mode lacp" in trunk_config.lower() or "mode lacp-static" in trunk_config.lower():
                        mode = "LACP"
                    elif "mode manual" in trunk_config.lower() or "mode manual-load-balance" in trunk_config.lower():
                        mode = "STATIC"
                    members = set()
                    for m in re.finditer(r'trunkport\s+(GigabitEthernet\S+|GE\S+|Ethernet\S+)', trunk_config, re.IGNORECASE):
                        members.add(m.group(1))
                    ether_trunk_map[current_trunk_id] = {
                        "id": current_trunk_id,
                        "name": f"Eth-Trunk{current_trunk_id}",
                        "mode": mode,
                        "members": members,
                    }
                # Start new trunk
                current_trunk_id = trunk_match.group(1)
                current_trunk_config = []
            elif line_stripped == '#' and current_trunk_id:
                # End of trunk interface block
                if current_trunk_id not in ether_trunk_map:
                    trunk_config = '\n'.join(current_trunk_config)
                    mode = None
                    if "mode lacp" in trunk_config.lower() or "mode lacp-static" in trunk_config.lower():
                        mode = "LACP"
                    elif "mode manual" in trunk_config.lower() or "mode manual-load-balance" in trunk_config.lower():
                        mode = "STATIC"
                    members = set()
                    for m in re.finditer(r'trunkport\s+(GigabitEthernet\S+|GE\S+|Ethernet\S+)', trunk_config, re.IGNORECASE):
                        members.add(m.group(1))
                    ether_trunk_map[current_trunk_id] = {
                        "id": current_trunk_id,
                        "name": f"Eth-Trunk{current_trunk_id}",
                        "mode": mode,
                        "members": members,
                    }
                current_trunk_id = None
                current_trunk_config = []
            elif current_trunk_id:
                # Accumulate config lines for current trunk
                current_trunk_config.append(line)
        
        # Handle last trunk if file doesn't end with #
        if current_trunk_id and current_trunk_id not in ether_trunk_map:
            trunk_config = '\n'.join(current_trunk_config)
            mode = None
            if "mode lacp" in trunk_config.lower() or "mode lacp-static" in trunk_config.lower():
                mode = "LACP"
            elif "mode manual" in trunk_config.lower() or "mode manual-load-balance" in trunk_config.lower():
                mode = "STATIC"
            members = set()
            for m in re.finditer(r'trunkport\s+(GigabitEthernet\S+|GE\S+|Ethernet\S+)', trunk_config, re.IGNORECASE):
                members.add(m.group(1))
            ether_trunk_map[current_trunk_id] = {
                "id": current_trunk_id,
                "name": f"Eth-Trunk{current_trunk_id}",
                "mode": mode,
                "members": members,
            }
        
        # Second pass: Find member ports for each trunk
        current_interface = None
        current_interface_config = []
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Check if this line starts a new interface block
            interface_match = re.match(r'^interface\s+(\S+)', line_stripped, re.IGNORECASE)
            if interface_match:
                # Process previous interface if it had eth-trunk config
                if current_interface:
                    interface_config = '\n'.join(current_interface_config)
                    # Check for eth-trunk assignment
                    eth_trunk_match = re.search(r'eth-trunk\s+(\d+)', interface_config, re.IGNORECASE)
                    if eth_trunk_match:
                        trunk_id = eth_trunk_match.group(1)
                        if trunk_id in ether_trunk_map:
                            # Use .add() for set to prevent duplicate members
                            ether_trunk_map[trunk_id]["members"].add(current_interface)
                
                # Start new interface
                current_interface = interface_match.group(1)
                current_interface_config = []
            elif line_stripped == '#' and current_interface:
                # End of interface block
                interface_config = '\n'.join(current_interface_config)
                # Check for eth-trunk assignment
                eth_trunk_match = re.search(r'eth-trunk\s+(\d+)', interface_config, re.IGNORECASE)
                if eth_trunk_match:
                    trunk_id = eth_trunk_match.group(1)
                    if trunk_id in ether_trunk_map:
                        # Use set to prevent duplicate members
                        ether_trunk_map[trunk_id]["members"].add(current_interface)
                current_interface = None
                current_interface_config = []
            elif current_interface:
                # Accumulate config lines for current interface
                current_interface_config.append(line)
        
        # Handle last interface if file doesn't end with #
        if current_interface:
            interface_config = '\n'.join(current_interface_config)
            eth_trunk_match = re.search(r'eth-trunk\s+(\d+)', interface_config, re.IGNORECASE)
            if eth_trunk_match:
                trunk_id = eth_trunk_match.group(1)
                if trunk_id in ether_trunk_map:
                    # Use .add() for set, not .append()
                    ether_trunk_map[trunk_id]["members"].add(current_interface)
        
        # Convert dictionary values to list and convert sets to lists
        etherchannel_list = []
        for trunk in ether_trunk_map.values():
            trunk_copy = trunk.copy()
            trunk_copy["members"] = sorted(list(trunk["members"]))  # Convert set to sorted list
            etherchannel_list.append(trunk_copy)
        ha["etherchannel"] = etherchannel_list
        
        # Extract VRRP - Use dictionary to prevent duplicates
        # Parse VRRP from interface blocks: "interface VlanifX" ... "vrrp vrid Y virtual-ip Z" ... "vrrp vrid Y priority P"
        vrrp_map = {}
        lines = content.split('\n')
        current_interface = None
        current_interface_config = []
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Check if this line starts a new interface block
            interface_match = re.match(r'^interface\s+(\S+)', line_stripped, re.IGNORECASE)
            if interface_match:
                # Process previous interface if exists
                if current_interface:
                    interface_config = '\n'.join(current_interface_config)
                    # Parse VRRP from this interface's config block
                    self._extract_vrrp_from_interface(current_interface, interface_config, vrrp_map)
                
                # Start new interface
                current_interface = interface_match.group(1)
                current_interface_config = []
            elif line_stripped == '#' and current_interface:
                # End of interface block - process it
                interface_config = '\n'.join(current_interface_config)
                self._extract_vrrp_from_interface(current_interface, interface_config, vrrp_map)
                current_interface = None
                current_interface_config = []
            elif current_interface:
                # Accumulate config lines for current interface
                current_interface_config.append(line)
        
        # Handle last interface if file doesn't end with #
        if current_interface:
            interface_config = '\n'.join(current_interface_config)
            self._extract_vrrp_from_interface(current_interface, interface_config, vrrp_map)
        
        # Parse display vrrp / display vrrp brief when present - only add if virtual_ip is valid IP
        vrrp_brief = re.search(r'display\s+vrrp\s+brief(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if not vrrp_brief:
            vrrp_brief = re.search(r'display\s+vrrp(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if vrrp_brief:
            for line in vrrp_brief.group(1).strip().splitlines():
                line_strip = line.strip()
                if not line_strip or 'Interface' in line_strip and 'VRID' in line_strip or line_strip.startswith('---'):
                    continue
                # Interface VRID State Virtual IP
                m = re.match(r'^(\S+)\s+(\d+)\s+(\S+)\s+(\d+\.\d+\.\d+\.\d+)$', line_strip)
                if m and is_valid_ipv4(m.group(4)):
                    iface, vrid, state, vip = m.group(1), m.group(2), m.group(3), m.group(4)
                    key = f"{iface}_{vrid}"
                    if key not in vrrp_map:
                        vrrp_map[key] = {"interface": iface, "vrid": vrid, "state": state, "virtual_ip": vip, "priority": None}
                    else:
                        vrrp_map[key]["state"] = state
                        vrrp_map[key]["virtual_ip"] = vip
        
        # Only include VRRP entries with valid virtual_ip (no header/garbage)
        ha["vrrp"] = [v for v in vrrp_map.values() if v.get("virtual_ip") and is_valid_ipv4(str(v["virtual_ip"]))]
        
        return ha
