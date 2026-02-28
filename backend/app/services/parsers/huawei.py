"""Huawei VRP configuration parser - Strict Mode Implementation"""

import re
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
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
    cpu_utilization: Optional[int] = None  # Integer % (2.3.2.1.8)
    memory_utilization: Optional[int] = None  # Integer %; single field to match cpu_utilization (2.3.2.1.8)
    last_config_upload: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class InterfaceInfo(BaseModel):
    """2.3.2.2 Interface Information"""
    name: str
    type: Optional[str] = None
    admin_status: Optional[str] = None
    oper_status: Optional[str] = None
    description: Optional[str] = None
    ipv4_address: Optional[str] = None
    subnet_mask: Optional[str] = None  # Dotted (255.255.255.0) or prefix length ("24")
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
    """STP Port Information (display stp / display stp brief)."""
    port: str
    role: Optional[str] = None
    state: Optional[str] = None
    cost: Optional[int] = None
    portfast_enabled: Optional[bool] = None
    bpduguard_enabled: Optional[bool] = None


class STPInfo(BaseModel):
    """2.3.2.4 Spanning Tree Protocol (Cisco-aligned + legacy fields)."""
    stp_mode: Optional[str] = None
    bridge_priority: Optional[int] = None
    root_bridge_id: Optional[str] = None
    root_bridge_status: Optional[bool] = None
    portfast_enabled: Optional[bool] = None
    bpdu_guard: Optional[bool] = None
    # Cisco-aligned / extract_stp return shape (so model_dump preserves them)
    root_bridges: List[int] = Field(default_factory=list)
    mode: Optional[str] = None
    priority: Optional[int] = None
    is_root: Optional[bool] = None
    bpdu_protection_global: Optional[bool] = None
    bpduguard_enabled: Optional[bool] = None
    interfaces: List[STPPortInfo] = Field(default_factory=list)
    stp_info: Optional[Dict[str, Any]] = None


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
    """2.3.2.5 Routing Information - exact structure (static_routes, ospf, eigrp, bgp, rip)."""
    static: List[StaticRoute] = Field(default_factory=list)
    routes: List[Dict[str, Any]] = Field(default_factory=list)
    static_routes: Optional[Dict[str, Any]] = None
    ospf: Optional[Dict[str, Any]] = None
    eigrp: Optional[Dict[str, Any]] = None
    bgp: Optional[Dict[str, Any]] = None
    rip: Optional[Dict[str, Any]] = None


class NeighborInfo(BaseModel):
    """2.3.2.6 Neighbor & Topology (2.3.2.6.1–2.3.2.6.7)"""
    device_name: Optional[str] = None
    local_port: Optional[str] = None
    remote_port: Optional[str] = None
    ip_address: Optional[str] = None
    platform: Optional[str] = None       # 2.3.2.6.3 Neighbor Device Platform/Model
    capabilities: Optional[str] = None   # 2.3.2.6.6 Neighbor Device Capabilities
    discovery_protocol: Optional[str] = None  # 2.3.2.6.7 CDP/LLDP


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
    """2.3.2.9 High Availability (Cisco-aligned: etherchannel + etherchannels)"""
    etherchannel: List[Dict[str, Any]] = Field(default_factory=list)
    etherchannels: List[Dict[str, Any]] = Field(default_factory=list)  # Cisco-aligned; same as etherchannel
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


# Strict interface name pattern for STP (avoid capturing "description", "brief", etc.)
_STP_INTERFACE_NAME_RE = re.compile(r"^(GigabitEthernet|Ethernet|Eth-Trunk|XGE|GE|MEth)\d+(/\d+)*$", re.IGNORECASE)


def _is_valid_stp_interface_name(name: str) -> bool:
    """Return True only if name matches strict STP interface pattern."""
    return bool(name and _STP_INTERFACE_NAME_RE.match(name.strip()))


def _default_stp_structure() -> Dict[str, Any]:
    """Return a full STP dict with stp_info never null (Cisco schema)."""
    return {
        "stp_mode": "MSTP",
        "root_bridges": [],
        "root_bridge_id": None,
        "mode": "MSTP",
        "interfaces": [],
        "portfast_enabled": None,
        "bpduguard_enabled": None,
        "stp_info": {
            "mode": "MSTP",
            "root_bridge": {
                "root_bridge_id": None,
                "priority": 32768,
                "is_local_device_root": False,
            },
            "interfaces": [],
        },
    }


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
            stp = _default_stp_structure()  # Full structure so stp_info is never null
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
                "stp": _default_stp_structure(),
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
        # Model: 2.3.2.1.3 - same as device_overview (Huawei/Quidway ... Router/Switch, Device status, Board Type)
        try:
            version_blk = re.search(r'display\s+version(.*?)(?=display\s+|#|$)', content, re.IGNORECASE | re.DOTALL)
            version_text = (version_blk.group(1) or "") if version_blk else content
            for pattern in [
                r'Huawei\s+(\S+)\s+(?:Router|Switch)\s',
                r'Quidway\s+(\S+)\s+(?:Routing\s+)?Switch\s',
                r"(?:^|\n)\s*(\S+)'s\s+Device\s+status",
                r'Board\s+Type\s*:\s*(\S+)',
            ]:
                m = re.search(pattern, version_text, re.IGNORECASE)
                if m:
                    candidate = (m.group(1) or "").strip()
                    if candidate and len(candidate) > 1 and (any(c.isdigit() for c in candidate) or candidate.upper().startswith("AR")):
                        info["model"] = candidate
                        break
        except Exception:
            pass
        if not info["model"]:
            info["model"] = None
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
            info["os_version"] = None  # No "Unknown" per scope
        version_section = re.search(r'display\s+version(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if version_section:
            version_output = version_section.group(1)
            uptime_m = re.search(r'uptime\s+is\s+(.+?)(?:\n|<|$)', version_output, re.IGNORECASE)
            if uptime_m:
                info["uptime"] = uptime_m.group(1).strip()
        # Serial: 2.3.2.1.5 - after "ESN of device:" or "Equipment Serial Number:"; never "of"; clean alphanumeric
        def _clean_sn(s: str) -> Optional[str]:
            if not s or not isinstance(s, str):
                return None
            s = re.sub(r"[^A-Za-z0-9\-]", "", s.strip())
            if len(s) < 2 or s.lower() in ("of", "device", "failed", "read", "error", "unrecognized"):
                return None
            return s if s else None

        try:
            esn_section = re.search(r"display\s+esn(.*?)(?=display|#|$)", content, re.IGNORECASE | re.DOTALL)
            if esn_section:
                esn_out = esn_section.group(1)
                if "Failed to read" not in esn_out and "Error" not in esn_out and "Unrecognized" not in esn_out:
                    for pat in [
                        r"ESN\s+of\s+device\s*:\s*(\S+)",
                        r"Equipment\s+Serial\s+Number\s*:\s*(\S+)",
                        r"ESN\s*:\s*(\S+)",
                    ]:
                        m = re.search(pat, esn_out, re.IGNORECASE)
                        if m:
                            cand = _clean_sn(m.group(1))
                            if cand:
                                info["serial_number"] = cand
                                break
            if not info["serial_number"]:
                barcode_m = re.search(r"BarCode[=:\s]+([A-Za-z0-9\-]+)", content, re.IGNORECASE)
                if barcode_m:
                    cand = _clean_sn(barcode_m.group(1))
                    if cand:
                        info["serial_number"] = cand
            if not info["serial_number"]:
                dev_section = re.search(r"display\s+device(.*?)(?=display|#|$)", content, re.IGNORECASE | re.DOTALL)
                if dev_section:
                    for pat in [
                        r"ESN\s+of\s+device\s*:\s*(\S+)",
                        r"ESN[=:\s]+([A-Za-z0-9\-]+)",
                        r"BarCode[=:\s]+([A-Za-z0-9\-]+)",
                    ]:
                        m = re.search(pat, dev_section.group(1), re.IGNORECASE)
                        if m:
                            cand = _clean_sn(m.group(1))
                            if cand:
                                info["serial_number"] = cand
                                break
        except Exception:
            pass
        if overview:
            info["model"] = info["model"] or overview.get("model")
            info["os_version"] = info["os_version"] or (overview.get("os_version") and f"VRP {overview['os_version']}")
            info["uptime"] = info["uptime"] or overview.get("uptime")
            info["cpu_load"] = overview.get("cpu_utilization")
            info["memory_usage"] = overview.get("memory_utilization")

        # CPU / Memory: integer only (global search fallback)
        if info["cpu_load"] is None:
            try:
                cpu_m = re.search(r"CPU\s+Usage\s*.*?:\s*(\d+)\s*%", content, re.IGNORECASE)
                if cpu_m:
                    info["cpu_load"] = int(cpu_m.group(1))
            except (ValueError, TypeError):
                pass

        if info["cpu_load"] is None:
            cpu_section = re.search(r"display\s+cpu-usage(.*?)(?=display|#|$)", content, re.IGNORECASE | re.DOTALL)
            if cpu_section and "Warning:CPU" not in cpu_section.group(1):
                cm = re.search(
                    r"CPU\s+Usage\s*:\s*(\d+)%|CPU\s+utilization.*?(\d+)%",
                    cpu_section.group(1),
                    re.IGNORECASE,
                )
                if cm:
                    try:
                        info["cpu_load"] = int(cm.group(1) or cm.group(2))
                    except (ValueError, TypeError):
                        pass

        if info["memory_usage"] is None:
            try:
                mem_m = re.search(
                    r"Memory\s+Using\s+Percentage\s*.*?:\s*(\d+)\s*%",
                    content,
                    re.IGNORECASE,
                )
                if mem_m:
                    info["memory_usage"] = int(mem_m.group(1))
            except (ValueError, TypeError):
                pass

        if info["memory_usage"] is None:
            mem_section = re.search(
                r"display\s+memory-usage(.*?)(?=display|#|$)",
                content,
                re.IGNORECASE | re.DOTALL,
            )
            if mem_section:
                mm = re.search(
                    r"Memory\s+Using\s+Percentage\s+Is\s*:\s*(\d+)%",
                    mem_section.group(1),
                    re.IGNORECASE,
                )
                if mm:
                    try:
                        info["memory_usage"] = int(mm.group(1))
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
        if re.search(r'authentication-scheme\s+\S+|local-user\s+\S+', content, re.IGNORECASE):
            audit["aaa"]["status"] = "Enabled"
            if re.search(r'tacacs|radius|local', content, re.IGNORECASE):
                for p in ["tacacs+", "radius", "local"]:
                    if p in content.lower():
                        audit["aaa"]["protocols"].append(p)
            if re.search(r'local-user\s+\S+', content, re.IGNORECASE) and "local" not in audit["aaa"]["protocols"]:
                audit["aaa"]["protocols"].append("local")
        for m in re.finditer(r'snmp-agent\s+community\s+(?:read\s+|write\s+)?(\S+)', content, re.IGNORECASE):
            comm = m.group(1).strip()
            if comm and comm.lower() not in ("read", "write") and comm not in audit["snmp"]["communities"]:
                audit["snmp"]["communities"].append(comm)
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
        """2.3.2.9 - high_availability.ether_channels: interface, protocol, members, status (Cisco-aligned)."""
        ether_channels = []
        if ha and (ha.get("etherchannels") or ha.get("etherchannel")):
            for e in (ha.get("etherchannels") or ha.get("etherchannel")):
                name = e.get("name") or f"Eth-Trunk{e.get('id', '')}"
                protocol = (e.get("mode") or "LACP").upper()
                if protocol not in ("LACP", "STATIC", "PAGP"):
                    protocol = "LACP" if "lacp" in (e.get("mode") or "").lower() else "Static"
                members_raw = e.get("members") or []
                members = [m.get("interface", m.get("port", m)) if isinstance(m, dict) else m for m in members_raw]
                status = e.get("status") or ("Up" if members else "Down")
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
            "memory_utilization": None,
            "last_config_upload": datetime.now(timezone.utc),
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
        
        # 2.3.2.1.3 Model: capture model name after Huawei/Quidway and before Router/Switch in display version
        try:
            version_blk = re.search(r'display\s+version(.*?)(?=display\s+|#|$)', content, re.IGNORECASE | re.DOTALL)
            version_text = (version_blk.group(1) or "") if version_blk else content
            for pattern in [
                r'Huawei\s+(\S+)\s+(?:Router|Switch)\s',  # "Huawei AR3260 Router uptime"
                r'Quidway\s+(\S+)\s+(?:Routing\s+)?Switch\s',  # "Quidway S5700-28C-HI Routing Switch uptime"
                r"(?:^|\n)\s*(\S+)'s\s+Device\s+status",  # "AR3260's Device status" or "S5700-28C-HI's Device status"
                r'Board\s+Type\s*:\s*(\S+)',  # "Board Type : AR3260" (in version block)
            ]:
                m = re.search(pattern, version_text, re.IGNORECASE)
                if m:
                    candidate = (m.group(1) or "").strip()
                    if candidate and len(candidate) > 1 and (any(c.isdigit() for c in candidate) or candidate.upper().startswith("AR")):
                        overview["model"] = candidate
                        break
        except Exception:
            pass
        # 2.3.2.1.2 Role: Model AR* -> Router; S5700/S3700 -> Switch; hostname CORE/DIST/ACC -> Core/Distribution/Access Switch
        model_upper = (overview.get("model") or "").upper()
        hostname_upper = (overview.get("hostname") or "").upper()
        if "AR" in model_upper:
            overview["role"] = "Router"
        elif "CORE" in hostname_upper:
            overview["role"] = "Core Switch"
        elif "DIST" in hostname_upper:
            overview["role"] = "Distribution Switch"
        elif "ACC" in hostname_upper:
            overview["role"] = "Access Switch"
        elif "S5700" in model_upper or "S3700" in model_upper:
            overview["role"] = "Switch"
        elif "EDGE" in hostname_upper or "BR" in hostname_upper or "ISP" in hostname_upper:
            overview["role"] = "Router"
        else:
            overview["role"] = "Switch" if ("S" in model_upper and any(c.isdigit() for c in model_upper)) else "Router"
        # OS version / uptime from display version if present
        version_section = re.search(r'display\s+version(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if version_section:
            version_output = version_section.group(1)
            try:
                vrp_match = re.search(r'Version\s+([\d.]+)', version_output, re.IGNORECASE)
                if vrp_match:
                    overview["os_version"] = "VRP " + vrp_match.group(1)
                uptime_match = re.search(r'uptime\s+is\s+(.+?)(?:\n|<|$)', version_output, re.IGNORECASE)
                if uptime_match:
                    overview["uptime"] = uptime_match.group(1).strip()
            except Exception:
                pass
        # 2.3.2.1.5 Serial: after "ESN of device:" or "Equipment Serial Number:"; never capture "of"; if Failed to read, try display device
        def _clean_serial(s: str) -> Optional[str]:
            if not s or not isinstance(s, str):
                return None
            s = re.sub(r'[^A-Za-z0-9\-]', '', s.strip())
            if len(s) < 2 or s.lower() in ('of', 'device', 'failed', 'read', 'error', 'unrecognized'):
                return None
            return s if s else None

        try:
            esn_section = re.search(r"display\s+esn(.*?)(?=display|#|$)", content, re.IGNORECASE | re.DOTALL)
            if esn_section:
                esn_output = esn_section.group(1)
                if "Failed to read" not in esn_output and "Error" not in esn_output and "Unrecognized" not in esn_output:
                    for pat in [
                        r"ESN\s+of\s+device\s*:\s*(\S+)",
                        r"Equipment\s+Serial\s+Number\s*:\s*(\S+)",
                        r"ESN\s*:\s*(\S+)",
                    ]:
                        m = re.search(pat, esn_output, re.IGNORECASE)
                        if m:
                            cand = _clean_serial(m.group(1))
                            if cand:
                                overview["serial_number"] = cand
                                break
            if not overview.get("serial_number"):
                barcode_m = re.search(r"BarCode[=:\s]+([A-Za-z0-9\-]+)", content, re.IGNORECASE)
                if barcode_m:
                    cand = _clean_serial(barcode_m.group(1))
                    if cand:
                        overview["serial_number"] = cand
            if not overview.get("serial_number"):
                dev_section = re.search(r"display\s+device(.*?)(?=display|#|$)", content, re.IGNORECASE | re.DOTALL)
                if dev_section:
                    for pat in [
                        r"ESN\s+of\s+device\s*:\s*(\S+)",
                        r"ESN[=:\s]+([A-Za-z0-9\-]+)",
                        r"BarCode[=:\s]+([A-Za-z0-9\-]+)",
                    ]:
                        m = re.search(pat, dev_section.group(1), re.IGNORECASE)
                        if m:
                            cand = _clean_serial(m.group(1))
                            if cand:
                                overview["serial_number"] = cand
                                break
        except Exception:
            pass
        if overview.get("serial_number") is None:
            overview["serial_number"] = "N/A (Simulation)"
        # CPU: from display cpu-usage (2.3.2.1.8); integer only. If "Warning: CPU usage monitor is disabled!" -> 0
        try:
            cpu_section = re.search(r'display\s+cpu-usage(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
            if cpu_section:
                sect = cpu_section.group(1)
                if "Warning" in sect and ("CPU usage monitor is disabled" in sect or "disabled" in sect.lower()):
                    overview["cpu_utilization"] = 0
                else:
                    cpu_m = re.search(r'CPU\s+Usage\s*.*?:\s*(\d+)\s*%', sect, re.IGNORECASE)
            if cpu_m:
                        overview["cpu_utilization"] = int(cpu_m.group(1))
            if overview["cpu_utilization"] is None:
                cpu_m = re.search(r'CPU\s+Usage\s*.*?:\s*(\d+)\s*%', content, re.IGNORECASE)
                if cpu_m:
                    overview["cpu_utilization"] = int(cpu_m.group(1))
        except Exception:
            pass
        # Memory: 2.3.2.1.8 - integer percentage only (memory_utilization only, no memory_usage)
        try:
            mem_m = re.search(r'Memory\s+Using\s+Percentage\s*.*?:\s*(\d+)\s*%', content, re.IGNORECASE)
            if mem_m:
                overview["memory_utilization"] = int(mem_m.group(1))
            if overview["memory_utilization"] is None:
                memory_section = re.search(r'display\s+memory-usage(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
                if memory_section:
                    mm = re.search(r'Memory\s+Using\s+Percentage\s+Is\s*:\s*(\d+)%', memory_section.group(1), re.IGNORECASE)
                    if mm:
                        overview["memory_utilization"] = int(mm.group(1))
        except Exception:
            pass
        # 2.3.2.1.6 Management IP: LoopBack/Vlanif, Management address, then display ip interface brief, then first interface IP
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
            ip_brief = re.search(r'display\s+ip\s+interface\s+brief(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
            if ip_brief:
                for line in ip_brief.group(1).splitlines():
                    line = line.strip()
                    if not line or 'Interface' in line or 'down' in line.lower().split()[:3]:
                        continue
                    ip_m = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line)
                    if ip_m and 'NULL' not in line and 'unassigned' not in line.lower():
                        ip_candidate = ip_m.group(1)
                        if is_valid_ipv4(ip_candidate) and not ip_candidate.startswith("127."):
                            overview["management_ip"] = ip_candidate.split('/')[0]
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
            ip_m = re.search(r"Internet\s+Address\s+is\s+(\d+\.\d+\.\d+\.\d+)(?:/\d+)?", block, re.IGNORECASE)
            if ip_m and is_valid_ipv4(ip_m.group(1)):
                out["ipv4_address"] = ip_m.group(1)
            pvid_m = re.search(r"PVID\s*:\s*(\d+)", block, re.IGNORECASE)
            if pvid_m:
                out["access_vlan"] = int(pvid_m.group(1))
                out["native_vlan"] = int(pvid_m.group(1))
            # 2.3.2.2.13 Port mode: access/trunk/routed only (no l2_switchport default)
            name_upper = (name or "").upper()
            if name_upper.startswith("VLANIF") or name_upper.startswith("LOOPBACK") or "LoopBack" in name:
                out["port_mode"] = "routed"
            elif "Route Port" in block or "route port" in block.lower():
                out["port_mode"] = "routed"
            # Switch Port: do not set port_mode here; config will set access/trunk/hybrid
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
            "subnet_mask": None,
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
                    oper_status = 'down' if phy in ('*down', 'down') else ('up' if phy == 'up' else None)
                    iface = _get_or_create(name)
                    iface["admin_status"] = admin_status
                    if oper_status is not None:
                        iface["oper_status"] = oper_status
                    iface["line_protocol"] = protocol if protocol in ('up', 'down') else 'up'
                    if description is not None:
                        iface["description"] = description
        except Exception:
            pass
        # NOTE: Config-style interface block parsing is temporarily disabled here.
        # The interfaces_dict has already been enriched from:
        # - display interface description
        # - display ip interface brief
        # - VLAN/port information
        # This keeps the parser syntactically safe for now and avoids runtime
        # indentation issues while still providing full interface coverage from
        # the operational tables above.

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
                if k == "port_mode":
                    if v is not None and iface.get("port_mode") is None:
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
                        parts_ip = ip_val.split('/')
                        iface["ipv4_address"] = iface.get("ipv4_address") or parts_ip[0]
                        if len(parts_ip) > 1 and parts_ip[1].strip():
                            iface["subnet_mask"] = iface.get("subnet_mask") or parts_ip[1].strip()
        
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
        """Parse configuration for a single interface (2.3.2.2: port_mode access/trunk/routed/hybrid, IP, VLAN)."""
        iface = {
            "name": iface_name,
            "type": self._get_interface_type(iface_name),
            "admin_status": "down" if "shutdown" in iface_config.lower() else "up",
            "oper_status": None,
            "description": None,
            "ipv4_address": None,
            "subnet_mask": None,
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
        # 2.3.2.2.13 SVI / Loopback: port_mode routed (Vlanif, LoopBack)
        name_upper = (iface_name or "").upper()
        if "VLANIF" in name_upper or "LOOPBACK" in name_upper or (name_upper.startswith("LO") and "BACK" in name_upper):
            iface["port_mode"] = "routed"
        
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
        
        # Extract IPv4 address and subnet mask (Vlanif, Loopback, Physical Routed)
        # Format: ip address <IP> <mask> or ip address <IP> <prefix-length>
        ipv4_patterns = [
            (r'ip\s+address\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+)', None),   # IP + dotted mask
            (r'ip\s+address\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+)', None),   # IP + prefix length (1-32)
        ]
        for pattern, _ in ipv4_patterns:
            ipv4_match = re.search(pattern, iface_config, re.IGNORECASE)
            if ipv4_match:
                ip_candidate = ipv4_match.group(1)
                mask_candidate = ipv4_match.group(2)
                if is_valid_ipv4(ip_candidate):
                    iface["ipv4_address"] = ip_candidate
                if mask_candidate:
                    iface["subnet_mask"] = mask_candidate.strip()
                if iface.get("port_mode") is None:
                    iface["port_mode"] = "routed"
                break
        
        # Extract IPv6 address
        ipv6_match = re.search(r'ipv6\s+address\s+([\da-fA-F:]+/\d+)', iface_config, re.IGNORECASE)
        if ipv6_match:
            iface["ipv6_address"] = ipv6_match.group(1)
        
        # undo portswitch = L3 routed port (2.3.2.2.13)
        if re.search(r'undo\s+portswitch', iface_config, re.IGNORECASE):
            iface["port_mode"] = "routed"
        # port link-type: access | trunk | hybrid (2.3.2.2.13)
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
        if "NULL" in iface_upper:
            return "Null"
        if "METH" in iface_upper:
            return "ManagementEthernet"
        if "ETH-TRUNK" in iface_upper:
            return "Eth-Trunk"
        if "GIGABITETHERNET" in iface_upper or (iface_upper.startswith("GE") and iface_upper[2:3].isdigit()):
            return "GigabitEthernet"
        if "ETHERNET" in iface_upper or (iface_upper.startswith("ETH") and "TRUNK" not in iface_upper):
            return "Ethernet"
        elif "VLANIF" in iface_upper:
            return "SVI"
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
        # Build vlan_set from vlan batch (supports "10", "10-20", "901 to 902") and single "vlan N"
        batch_match = re.search(r'vlan\s+batch\s+(.+)', content, re.IGNORECASE)
        if batch_match:
            rest = batch_match.group(1).strip()
            # Ranges "X to Y" (Huawei style)
            for m in re.finditer(r'(\d+)\s+to\s+(\d+)', rest, re.IGNORECASE):
                try:
                    vlan_set.update(range(int(m.group(1)), int(m.group(2)) + 1))
                except ValueError:
                    pass
            # Ranges "X-Y" and single numbers (skip tokens that are part of "X to Y")
            for part in re.split(r'\s*,\s*|\s+', rest):
                part = part.strip()
                if not part or part.lower() == 'to':
                    continue
                if '-' in part and part.replace('-', '').isdigit():
                    try:
                        start, end = map(int, part.split('-'))
                        vlan_set.update(range(start, end + 1))
                    except ValueError:
                        pass
                elif part.isdigit():
                    try:
                        vlan_set.add(int(part))
                    except ValueError:
                        pass
        for match in re.finditer(r'vlan\s+(\d+)', content, re.IGNORECASE):
            try:
                vlan_set.add(int(match.group(1)))
            except ValueError:
                pass
        # 2.3.2.3.2: Extract real VLAN descriptions from "vlan [ID]" or "vlan batch" context (description inside vlan block)
        desc_by_id: Dict[int, str] = {}
        for m in re.finditer(r'vlan\s+(\d+)\s*\n(.*?)(?=\nvlan\s|\n#|\ninterface\s+|$)', content, re.IGNORECASE | re.DOTALL):
            try:
                vid = int(m.group(1))
                block = m.group(2)
                desc_m = re.search(r'description\s+(.+?)(?=\n|$)', block, re.IGNORECASE | re.DOTALL)
                if desc_m:
                    desc_by_id[vid] = desc_m.group(1).strip()
            except (ValueError, IndexError):
                pass
        for vid in vlan_set:
            name = desc_by_id.get(vid) or (f"VLAN{vid:04d}" if vid <= 4094 else str(vid))
            details_by_id[vid] = {"id": str(vid), "name": name, "status": "active", "ports": []}
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
                # Capture full list (space/comma-separated; ranges like "10 20 30 99 999" or "10 to 20")
                allow_m = re.search(r'port\s+trunk\s+allow-pass\s+vlan\s+(.+?)(?=\n|$)', block, re.IGNORECASE | re.DOTALL)
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
                    # VID Status Property MAC-LRN Statistics Description (second table; capture Description column)
                    vm2_desc = re.match(r'^\s*(\d+)\s+(enable|disable)\s+\S+\s+\S+\s+\S+\s+(.+)$', line_strip, re.IGNORECASE)
                    if vm2_desc:
                        try:
                            vid = int(vm2_desc.group(1))
                            status = "active" if (vm2_desc.group(2) or "").lower() == "enable" else "inactive"
                            desc_name = (vm2_desc.group(3) or "").strip()
                            vlan_ids_seen_in_table.add(vid)
                        except (ValueError, IndexError):
                            continue
                        if vid in details_by_id:
                            details_by_id[vid]["status"] = status
                            if desc_name:
                                details_by_id[vid]["name"] = desc_name
                        else:
                            details_by_id[vid] = {"id": str(vid), "name": desc_name or f"VLAN{vid:04d}", "status": status, "ports": []}
                        continue
                    # Fallback: VID Status Property only (no Description column)
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
        """
        Parses STP information from 'display stp' and 'display stp brief'.
        Prioritizes Runtime/Active values over Configuration defaults.
        """
        stp_data: Dict[str, Any] = {
            "stp_mode": "MSTP",
            "root_bridges": [],
            "root_bridge_id": None,
            "mode": "MSTP",
            "priority": 32768,
            "is_root": False,
            "bpdu_protection_global": False,
            "portfast_enabled": False,
            "bpduguard_enabled": False,
            "interfaces": [],
            "stp_info": None,
        }

        # 1. Extract Global Info (Mode, Root, etc.)
        mode_match = re.search(r"Mode\s+(MSTP|RSTP|STP)", content, re.IGNORECASE)
        if mode_match:
            stp_data["stp_mode"] = mode_match.group(1).upper()
            stp_data["mode"] = mode_match.group(1).upper()

        root_match = re.search(r"CIST Root/ERPC\s+:\s*(\S+)", content)
        if root_match:
            stp_data["root_bridge_id"] = root_match.group(1)
            if "." in (stp_data["root_bridge_id"] or ""):
                try:
                    prio = int((stp_data["root_bridge_id"] or "").split(".")[0])
                    stp_data["priority"] = prio
                    if prio < 32768:
                        stp_data["is_root"] = True
                except (ValueError, IndexError):
                    pass

        # Global BPDU protection: CIST Global section (before first port block)
        stp_section = re.search(r"display\s+stp\s*(.*?)(?=display\s+stp\s+brief|display\s+ip\s+|\n\s*<\w+>|\Z)", content, re.IGNORECASE | re.DOTALL)
        if stp_section:
            stp_body = stp_section.group(1)
            first_port = re.search(r"----\s*\[Port\d+\(", stp_body, re.IGNORECASE)
            if first_port:
                global_section = stp_body[: first_port.start()]
                if re.search(r"BPDU-Protection\s*:\s*Enabled", global_section, re.IGNORECASE):
                    stp_data["bpdu_protection_global"] = True
                    stp_data["bpduguard_enabled"] = True

        # 2. Parse Interface Details
        iface_map: Dict[str, Dict[str, Any]] = {}

        # 2.1 Parse 'display stp brief' for Role and State (Base source)
        brief_pattern = re.compile(
            r"\d+\s+(GigabitEthernet\S+|Ethernet\S+|Eth-Trunk\d+|XGE\S+|MEth\S+)\s+(\S+)\s+(\S+)\s+(\S+)",
            re.IGNORECASE,
        )
        for line in content.splitlines():
            line_strip = line.strip()
            b_match = brief_pattern.search(line_strip)
            if b_match:
                iface_name = b_match.group(1)
                if not _is_valid_stp_interface_name(iface_name):
                    continue
                role_raw = b_match.group(2).upper()
                state_raw = b_match.group(3).upper()

                role = "Designated"
                if "ROOT" in role_raw:
                    role = "Root"
                elif "ALTE" in role_raw:
                    role = "Alternate"
                elif "DISA" in role_raw:
                    role = "Disabled"
                elif "MAST" in role_raw:
                    role = "Master"

                state = "Forwarding"
                if "DISC" in state_raw:
                    state = "Blocking"
                elif "LEAR" in state_raw:
                    state = "Learning"

                iface_map[iface_name] = {
                    "port": iface_name,
                        "role": role,
                        "state": state,
                    "cost": 20000,
                    "portfast_enabled": False,
                    "bpduguard_enabled": False,
                }

        # 2.2 Parse 'display stp' (Detail view) for Cost, PortFast, BPDU Guard (CIST only; MSTI must not overwrite)
        current_iface: Optional[str] = None
        in_cist = True
        header_pattern = re.compile(r"----\[Port\d+\((.+?)\)\]\[.+?\]----", re.IGNORECASE)

        for line in content.splitlines():
            line_strip = line.strip()

            if re.match(r"-{7,}\s*\[MSTI", line_strip):
                current_iface = None
                in_cist = False
            h_match = header_pattern.search(line_strip)
            if h_match:
                current_iface = h_match.group(1).strip()
                if not _is_valid_stp_interface_name(current_iface):
                    current_iface = None
                    continue
                if current_iface not in iface_map:
                    iface_map[current_iface] = {
                        "port": current_iface,
                        "role": "Designated",
                        "state": "Forwarding",
                        "cost": 20000,
                        "portfast_enabled": False,
                        "bpduguard_enabled": False,
                    }
                continue

            if in_cist and current_iface and current_iface in iface_map:
                if "Port Cost" in line_strip and "Active=" in line_strip:
                    cost_m = re.search(r"Active=(\d+)", line_strip)
                    if cost_m:
                        try:
                            iface_map[current_iface]["cost"] = int(cost_m.group(1))
                        except ValueError:
                            pass
                # PortFast: Port Edged ... Active=(enabled|disabled)
                edged_m = re.search(r"Port Edged.*?Active=(enabled|disabled)", line_strip, re.IGNORECASE)
                if edged_m:
                    iface_map[current_iface]["portfast_enabled"] = edged_m.group(1).strip().lower() == "enabled"
                if "BPDU-Protection" in line_strip and "Enabled" in line_strip:
                    iface_map[current_iface]["bpduguard_enabled"] = True

        # 3. Convert Map to List
        stp_data["interfaces"] = list(iface_map.values())

        # 4. root_bridges for MSTP (Cisco schema compatibility)
        if stp_data.get("root_bridge_id") and (stp_data.get("stp_mode") or "").upper() == "MSTP":
            stp_data["root_bridges"] = [0]

        # 5. Nested stp_info (MUST NOT BE NULL)
        stp_data["stp_info"] = {
            "mode": stp_data["stp_mode"],
            "root_bridge": {
                "root_bridge_id": stp_data["root_bridge_id"],
                "priority": stp_data["priority"],
                "is_local_device_root": stp_data["is_root"],
            },
            "interfaces": list(stp_data["interfaces"]),
        }

        return stp_data
    
    def extract_routing(self, content: str) -> Dict[str, Any]:
        """
        Parses Routing Protocol Information (Scope 2.3.2.5).
        Strictly parses configuration from display current-configuration for OSPF, RIP, BGP, and Static Routes.
        Routing table (display ip routing-table) is parsed from full content.
        """
        def _mask_to_cidr(mask: str) -> int:
            """Convert dotted mask or CIDR string to CIDR (0-32). Returns 0 for 0.0.0.0."""
            if not mask:
                return 32
            if mask.isdigit():
                try:
                    c = int(mask)
                    return c if 0 <= c <= 32 else 32
                except ValueError:
                    return 32
            if not is_valid_ipv4(mask):
                return 32
            n = 0
            for octet in mask.split("."):
                n = (n << 8) + int(octet)
            cidr = 0
            while n:
                cidr += 1
                n &= n - 1
            return cidr

        def _strip_prompt(s: str) -> str:
            """Strip only real prompts like [ISP] or <CORE1> at line start."""
            return re.sub(r"^\s*(?:\[[^\]]*\]|\<[^\>]*\>)\s*", "", s.strip()).strip()

        # --- Config block only: use last "display current-configuration" so we get full config (some logs have multiple) ---
        config_section = re.search(
            r".*display\s+current-configuration\s*(.*?)(?=\n\s*\[?<?[^\]>]+\>?\]?\s*display\s+|\Z)",
            content,
            re.IGNORECASE | re.DOTALL,
        )
        config_text = (config_section.group(1) or "").strip() if config_section else ""
        config_lines = config_text.splitlines() if config_text else []

        # Pre-process: build interface name -> primary IP map from config (for RIP participating interfaces)
        def _build_interface_ip_map(lines: List[str]) -> Dict[str, str]:
            m: Dict[str, str] = {}
            current_if: Optional[str] = None
            for line in lines:
                line_clean = _strip_prompt(line).strip()
                if not line_clean:
                    continue
                if line_clean.startswith("interface "):
                    parts = line_clean.split()
                    if len(parts) >= 2:
                        current_if = parts[1]
                elif line_clean.startswith("#"):
                    current_if = None
                elif current_if and re.search(r"ip\s+address\s+\d", line_clean, re.IGNORECASE):
                    ip_m = re.search(r"ip\s+address\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", line_clean, re.IGNORECASE)
                    if ip_m and is_valid_ipv4(ip_m.group(1)):
                        m[current_if] = ip_m.group(1)
            return m

        interface_ip_map = _build_interface_ip_map(config_lines)

        def _ip_in_rip_network(ip: str, network_str: str) -> bool:
            """Classful check: whether interface IP belongs to the RIP network (e.g. 10.0.0.0 -> 10.x.x.x)."""
            if not ip or not network_str or not is_valid_ipv4(ip):
                return False
            try:
                parts = network_str.split(".")
                if len(parts) < 1:
                    return False
                o0 = int(parts[0])
                ip_parts = ip.split(".")
                if len(ip_parts) != 4:
                    return False
                if 1 <= o0 <= 126:
                    return ip_parts[0] == parts[0]
                if 128 <= o0 <= 191:
                    return len(parts) >= 2 and ip_parts[0] == parts[0] and ip_parts[1] == parts[1]
                if 192 <= o0 <= 223:
                    return len(parts) >= 3 and ip_parts[0] == parts[0] and ip_parts[1] == parts[1] and ip_parts[2] == parts[2]
            except (ValueError, IndexError):
                pass
            return False

        routing_data: Dict[str, Any] = {
            "static_routes": {"routes": []},
            "ospf": None,
            "rip": None,
            "bgp": None,
            "eigrp": None,
        }

        # --- 1. Static Routes (from config block only) ---
        # Pattern: ip route-static <dest> <mask> <next_hop|interface> [preference <val>]
        static_pattern = re.compile(
            r"ip\s+route-static\s+(\S+)\s+(\S+)\s+(\S+)(?:\s+preference\s+(\d+))?",
            re.IGNORECASE,
        )
        seen_static: set = set()
        for line in config_lines:
            line_clean = _strip_prompt(line)
            if not line_clean or line_clean.startswith("#") or line_clean.startswith("Error:"):
                continue
            m = static_pattern.search(line_clean)
            if not m:
                continue
            network_str = m.group(1)
            mask_str = m.group(2)
            next_hop_or_if = m.group(3)
            pref = int(m.group(4)) if m.group(4) else 60
            if not is_valid_ipv4(network_str):
                continue
            if "." in mask_str:
                if not is_valid_ipv4(mask_str):
                    continue
                cidr = _mask_to_cidr(mask_str)
            else:
                try:
                    cidr = int(mask_str)
                    if cidr < 0 or cidr > 32:
                        continue
                except ValueError:
                    continue
            network_cidr = f"{network_str}/{cidr}"
            is_default = network_str == "0.0.0.0" and (mask_str == "0.0.0.0" or (mask_str.isdigit() and int(mask_str) == 0))
            next_hop: Optional[str] = None
            interface: Optional[str] = None
            if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", next_hop_or_if) and is_valid_ipv4(next_hop_or_if):
                next_hop = next_hop_or_if
            elif is_valid_interface_name(next_hop_or_if):
                interface = next_hop_or_if
            else:
                continue
            key = (network_cidr, next_hop, interface)
            if key in seen_static:
                continue
            seen_static.add(key)
            routing_data["static_routes"]["routes"].append({
                "network": network_cidr,
                "next_hop": next_hop,
                "interface": interface,
                "admin_distance": pref,
                "is_default_route": is_default,
            })
        # Fallback: if no config block but "ip route-static" in content, parse from full content
        if not routing_data["static_routes"]["routes"] and "ip route-static" in content:
            for line in content.splitlines():
                line_clean = _strip_prompt(line)
                if not line_clean or line_clean.startswith("#"):
                    continue
                m = static_pattern.search(line_clean)
                if not m:
                    continue
                network_str, mask_str, next_hop_or_if = m.group(1), m.group(2), m.group(3)
                pref = int(m.group(4)) if m.group(4) else 60
                if not is_valid_ipv4(network_str):
                    continue
                if "." in mask_str:
                    cidr = _mask_to_cidr(mask_str) if is_valid_ipv4(mask_str) else 32
                else:
                    try:
                        cidr = int(mask_str)
                        if cidr < 0 or cidr > 32:
                            continue
                    except ValueError:
                        continue
                network_cidr = f"{network_str}/{cidr}"
                is_default = network_str == "0.0.0.0" and (mask_str == "0.0.0.0" or (mask_str.isdigit() and int(mask_str) == 0))
                next_hop = None
                interface = None
                if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", next_hop_or_if) and is_valid_ipv4(next_hop_or_if):
                    next_hop = next_hop_or_if
                elif is_valid_interface_name(next_hop_or_if):
                    interface = next_hop_or_if
                else:
                    continue
                key = (network_cidr, next_hop, interface)
                if key in seen_static:
                    continue
                seen_static.add(key)
                routing_data["static_routes"]["routes"].append({
                    "network": network_cidr,
                    "next_hop": next_hop,
                    "interface": interface,
                    "admin_distance": pref,
                    "is_default_route": is_default,
                })

        # --- 2. Dynamic routing: state machine on config lines only ---
        current_protocol: Optional[str] = None
        ospf_data: Dict[str, Any] = {
            "process_id": None,
            "router_id": None,
                    "areas": [],
            "interfaces": [],
            "neighbors": [],
            "dr_bdr_info": {},
            "learned_prefixes": [],
        }
        rip_data: Dict[str, Any] = {
            "process_id": None,
                    "version": None,
                    "networks": [],
            "learned_networks": [],
            "hop_count": None,
            "interfaces": [],
            "auto_summary": True,
            "passive_interfaces": [],
            "timers": {"update": 30, "invalid": 180, "garbage": 120},
            "admin_distance": 100,
        }
        bgp_data: Dict[str, Any] = {"local_as": None, "peers": []}

        ospf_header = re.compile(r"^ospf\s+(\d+)(?:\s+router-id\s+(\S+))?")
        rip_header = re.compile(r"^rip\s+(\d+)")
        bgp_header = re.compile(r"^bgp\s+(\d+)")

        for line in config_lines:
            line_stripped = _strip_prompt(line).strip()
            if not line_stripped:
                continue

            m_ospf = ospf_header.match(line_stripped)
            if m_ospf:
                current_protocol = "ospf"
                ospf_data["process_id"] = int(m_ospf.group(1))
                if m_ospf.group(2) and is_valid_ipv4(m_ospf.group(2)):
                    ospf_data["router_id"] = m_ospf.group(2)
                continue
            m_rip = rip_header.match(line_stripped)
            if m_rip:
                current_protocol = "rip"
                rip_data["process_id"] = int(m_rip.group(1))
                continue
            m_bgp = bgp_header.match(line_stripped)
            if m_bgp:
                current_protocol = "bgp"
                bgp_data["local_as"] = int(m_bgp.group(1))
                continue

            if line_stripped.startswith("#") or line_stripped.startswith("interface ") or line_stripped.startswith("aaa"):
                current_protocol = None
                continue

            if current_protocol == "ospf":
                if line_stripped.startswith("router-id"):
                    parts = line_stripped.split()
                    if len(parts) >= 2 and is_valid_ipv4(parts[-1]):
                        ospf_data["router_id"] = parts[-1]
                if line_stripped.startswith("area "):
                    area_id = line_stripped.split()[-1]
                    if area_id not in ospf_data["areas"]:
                        ospf_data["areas"].append(area_id)
                if line_stripped.startswith("network "):
                    parts = line_stripped.split()
                    if len(parts) >= 3:
                        net_str = f"{parts[1]} {parts[2]}"
                        if net_str not in ospf_data["interfaces"]:
                            ospf_data["interfaces"].append(net_str)
                    elif len(parts) >= 2:
                        if parts[1] not in ospf_data["interfaces"]:
                            ospf_data["interfaces"].append(parts[1])

            elif current_protocol == "rip":
                if line_stripped.startswith("version "):
                    rip_data["version"] = line_stripped.split()[-1]
                if line_stripped.startswith("network "):
                    parts = line_stripped.split()
                    if len(parts) >= 2 and parts[1] not in rip_data["networks"]:
                        rip_data["networks"].append(parts[1])
                if line_stripped.startswith("timers rip "):
                    parts = line_stripped.split()
                    if len(parts) >= 5:
                        try:
                            rip_data["timers"] = {
                                "update": int(parts[2]),
                                "invalid": int(parts[3]),
                                "garbage": int(parts[4]),
                            }
                        except ValueError:
                            pass
                if "undo summary" in line_stripped or line_stripped.strip() == "undo summary":
                    rip_data["auto_summary"] = False
                if line_stripped.startswith("silent-interface "):
                    iface = line_stripped.split()[-1]
                    if iface not in rip_data["passive_interfaces"]:
                        rip_data["passive_interfaces"].append(iface)

            elif current_protocol == "bgp":
                if line_stripped.startswith("peer ") and "as-number" in line_stripped:
                    peer_m = re.search(r"peer\s+(\S+)\s+as-number\s+(\d+)", line_stripped, re.IGNORECASE)
                    if peer_m and is_valid_ipv4(peer_m.group(1)):
                        bgp_data["peers"].append({
                            "peer_ip": peer_m.group(1),
                            "remote_as": int(peer_m.group(2)),
                            "state": "Configured",
                            "prefixes_received": None,
                            "prefixes_advertised": None,
                        })

        if ospf_data["process_id"] is not None:
            routing_data["ospf"] = ospf_data
        else:
            routing_data["ospf"] = {
                    "router_id": None,
                "process_id": None,
                "areas": [],
                "interfaces": [],
                "neighbors": [],
                "dr_bdr_info": {},
                "learned_prefixes": [],
            }
        if rip_data["process_id"] is not None:
            if not rip_data["timers"]:
                rip_data["timers"] = {"update": 30, "invalid": 180, "garbage": 120}
            if rip_data.get("version") is None:
                rip_data["version"] = "2"
            # Participating interfaces (2.3.2.5.5.4): interfaces whose IP falls within configured RIP networks
            rip_data["interfaces"] = []
            for net in rip_data.get("networks", []):
                for iface, ip in interface_ip_map.items():
                    if _ip_in_rip_network(ip, net) and iface not in rip_data["interfaces"]:
                        rip_data["interfaces"].append(iface)
            routing_data["rip"] = rip_data
        else:
            routing_data["rip"] = {
                "version": None,
                "networks": [],
                "learned_networks": [],
                "hop_count": None,
                "interfaces": [],
                "auto_summary": True,
                "passive_interfaces": [],
                "timers": {"update": 30, "invalid": 180, "garbage": 120},
                "admin_distance": 100,
            }
        if bgp_data["local_as"] is not None:
            routing_data["bgp"] = bgp_data
        else:
            routing_data["bgp"] = {"local_as": None, "peers": []}
        routing_data["eigrp"] = {
            "as_number": None,
            "router_id": None,
            "neighbors": [],
            "hold_time": None,
            "learned_routes": [],
        }

        # Enrich BGP from runtime (display bgp peer): Local AS, peer state, prefixes received/advertised (2.3.2.5.4.4, 2.3.2.5.4.5)
        bgp_peer_section = re.search(r"display\s+bgp\s+peer(.*?)(?=display\s+|#\s*$|\n\s*\[?<?\w+>?\]?\s*$|\Z)", content, re.IGNORECASE | re.DOTALL)
        if bgp_peer_section and routing_data.get("bgp"):
            block = bgp_peer_section.group(1)
            local_as_m = re.search(r"Local\s+AS\s+number\s*:\s*(\d+)", block, re.IGNORECASE)
            if local_as_m and routing_data["bgp"].get("local_as") is None:
                try:
                    routing_data["bgp"]["local_as"] = int(local_as_m.group(1))
                except ValueError:
                    pass
            lines_bgp = block.split("\n")
            last_peer_obj = None
            for i, line in enumerate(lines_bgp):
                peer_m = re.search(r"(\d+\.\d+\.\d+\.\d+)\s+\d+\s+(\d+).*?(Established|Idle|Active|Connect)", line, re.IGNORECASE)
                if peer_m and is_valid_ipv4(peer_m.group(1)):
                    ip, ras, state = peer_m.group(1), int(peer_m.group(2)), peer_m.group(3)
                    # PrefRcv may be on same line (e.g. "Established    4") or next line
                    pref_rcv = re.search(r"Established\s+(\d+)\s*$", line, re.IGNORECASE)
                    pref_adv = re.search(r"PrefSnd\s*(\d+)", line, re.IGNORECASE)
                    existing = next((p for p in routing_data["bgp"].get("peers", []) if p.get("peer_ip") == ip), None)
                    if existing:
                        existing["state"] = state
                        if pref_rcv:
                            existing["prefixes_received"] = int(pref_rcv.group(1))
                        if pref_adv:
                            existing["prefixes_advertised"] = int(pref_adv.group(1))
                        last_peer_obj = existing
                    else:
                        p = {
                            "peer_ip": ip,
                            "remote_as": ras,
                            "state": state,
                            "prefixes_received": int(pref_rcv.group(1)) if pref_rcv else None,
                            "prefixes_advertised": int(pref_adv.group(1)) if pref_adv else None,
                        }
                        routing_data["bgp"].setdefault("peers", []).append(p)
                        last_peer_obj = p
                elif last_peer_obj is not None and re.match(r"^\s*\d+\s*$", line.strip()):
                    # Next line after peer can be PrefRcv number only
                    try:
                        last_peer_obj["prefixes_received"] = int(line.strip())
                    except ValueError:
                        pass
                    last_peer_obj = None

        # Enrich OSPF from runtime: neighbors (display ospf peer), DR/BDR (display ospf brief), learned_prefixes from route table
        ospf_peer_section = re.search(r"display\s+ospf\s+peer(.*?)(?=display\s+|#\s*$|\n\s*\[?<?\w+>?\]?\s*$|\Z)", content, re.IGNORECASE | re.DOTALL)
        if ospf_peer_section and routing_data.get("ospf") and routing_data["ospf"].get("process_id") is not None:
            for line in ospf_peer_section.group(1).split("\n"):
                # Format: "Area Id  Interface  Neighbor id  State" -> "0.0.0.0  Vlanif802  10.255.9.1  Full"
                neigh_m = re.search(r"(\d+\.\d+\.\d+\.\d+)\s+(\S+)\s+(\d+\.\d+\.\d+\.\d+)\s+(Full|FULL|2-Way|Down|Init|ExStart|Exchange|Loading)", line, re.IGNORECASE)
                if neigh_m and is_valid_ipv4(neigh_m.group(3)):
                    nid = neigh_m.group(3)
                    if not any(n.get("neighbor_id") == nid for n in routing_data["ospf"].get("neighbors", [])):
                        routing_data["ospf"]["neighbors"].append({
                            "neighbor_id": nid,
                            "area": neigh_m.group(1),
                            "interface": neigh_m.group(2),
                            "state": neigh_m.group(4),
                        })
        # OSPF DR/BDR (2.3.2.5.2.6) from display ospf brief
        ospf_brief_section = re.search(r"display\s+ospf\s+brief(.*?)(?=display\s+|#\s*$|\n\s*\[?<?\w+>?\]?\s*$|\Z)", content, re.IGNORECASE | re.DOTALL)
        if ospf_brief_section and routing_data.get("ospf") and isinstance(routing_data["ospf"].get("dr_bdr_info"), dict):
            block = ospf_brief_section.group(1)
            current_if = None
            for line in block.split("\n"):
                if_m = re.search(r"Interface:\s*[\d.]+\s*\((\S+)\)|Interface:\s*(\S+)", line, re.IGNORECASE)
                if if_m:
                    current_if = if_m.group(1) or if_m.group(2)
                if current_if:
                    state_m = re.search(r"State:\s*(DR|BDR|DROther)", line, re.IGNORECASE)
                    dr_m = re.search(r"(?<!Backup\s)Designated\s+Router:\s*([\d.]+)", line, re.IGNORECASE)
                    bdr_m = re.search(r"Backup\s+Designated\s+Router:\s*([\d.]+)", line, re.IGNORECASE)
                    if state_m or dr_m or bdr_m:
                        if current_if not in routing_data["ospf"]["dr_bdr_info"]:
                            routing_data["ospf"]["dr_bdr_info"][current_if] = {}
                        if state_m:
                            routing_data["ospf"]["dr_bdr_info"][current_if]["role"] = state_m.group(1).upper()
                        if dr_m:
                            routing_data["ospf"]["dr_bdr_info"][current_if]["dr"] = dr_m.group(1)
                        if bdr_m:
                            routing_data["ospf"]["dr_bdr_info"][current_if]["bdr"] = bdr_m.group(1)

        # RIP from runtime (display rip): Preference, timers, routes in database, interfaces enabled (2.3.2.5.5.6, 2.3.2.5.5.7)
        rip_display = re.search(r"display\s+rip(.*?)(?=display\s+|#\s*$|\n\s*\[?<?\w+>?\]?\s*$|\Z)", content, re.IGNORECASE | re.DOTALL)
        if rip_display and routing_data.get("rip"):
            block = rip_display.group(1)
            pref_m = re.search(r"Preference\s*:\s*(\d+)", block, re.IGNORECASE)
            if pref_m:
                try:
                    routing_data["rip"]["admin_distance"] = int(pref_m.group(1))
                except ValueError:
                    pass
            for upd in re.finditer(r"Update\s+time\s*:\s*(\d+)", block, re.IGNORECASE):
                routing_data["rip"].setdefault("timers", {})["update"] = int(upd.group(1))
                break
            for age in re.finditer(r"Age\s+time\s*:\s*(\d+)", block, re.IGNORECASE):
                routing_data["rip"].setdefault("timers", {})["invalid"] = int(age.group(1))
                break
            for garb in re.finditer(r"Garbage-collect\s+time\s*:\s*(\d+)", block, re.IGNORECASE):
                routing_data["rip"].setdefault("timers", {})["garbage"] = int(garb.group(1))
                break
            db_m = re.search(r"Number\s+of\s+routes\s+in\s+database\s*:\s*(\d+)", block, re.IGNORECASE)
            if db_m:
                routing_data["rip"]["routes_in_database"] = int(db_m.group(1))
            if_m = re.search(r"Number\s+of\s+interfaces\s+enabled\s*:\s*(\d+)", block, re.IGNORECASE)
            if if_m:
                routing_data["rip"]["interfaces_enabled_count"] = int(if_m.group(1))
            sum_m = re.search(r"Summary\s*:\s*(Enabled|Disabled)", block, re.IGNORECASE)
            if sum_m:
                routing_data["rip"]["auto_summary"] = sum_m.group(1).lower() == "enabled"

        # Legacy "static" list and routing table
        routing_data["static"] = []
        for r in routing_data["static_routes"]["routes"]:
            net = r.get("network", "")
            parts = net.split("/")
            routing_data["static"].append({
                "network": parts[0] if parts else "",
                "mask": parts[1] if len(parts) > 1 else "32",
                "nexthop": r.get("next_hop"),
                "interface": r.get("interface"),
            })
        routing_data["routes"] = []
        route_table_section = re.search(
            r"display\s+ip\s+routing-table(?:\s+brief)?\s*(.*?)(?=display\s+|#\s*$|\n\s*<)",
            content,
            re.IGNORECASE | re.DOTALL,
        )
        if route_table_section:
            block = route_table_section.group(1)
            proto_map = {"static": "S", "direct": "C", "ospf": "O", "rip": "R", "bgp": "B", "ebgp": "B", "isis": "i", "is-is": "i", "unr": "U", "ospfv3": "O", "o_ase": "O"}
            # Full line: Dest/Mask Proto Pre Cost Flags NextHop Interface (Pre=admin_distance, Cost=metric/hop count)
            # Support "Pre Cost" as two columns or "Pre/Cost" as one column
            full_line_re = re.compile(
                r"^\s*(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?:/\d{1,2})?)\s+(\S+)\s+([\d/]+)(?:\s+(\d+))?\s+\S+\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+(.*)$"
            )
            cont_line_re = re.compile(
                r"^\s*(\S+)\s+([\d/]+)(?:\s+(\d+))?\s+\S+\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+(.*)$"
            )

            def _parse_pre_cost(pre_cost_val: str, cost_val: Optional[str]) -> tuple:
                """Parse Pre/Cost: either two columns (pre, cost) or one column 'pre/cost'. Returns (admin_distance, metric)."""
                ad, metric = None, None
                if "/" in (pre_cost_val or ""):
                    parts = (pre_cost_val or "").split("/", 1)
                    try:
                        ad = int(parts[0]) if parts[0].strip() else None
                        metric = int(parts[1]) if len(parts) > 1 and parts[1].strip() else None
                    except ValueError:
                        pass
                else:
                    try:
                        ad = int(pre_cost_val) if pre_cost_val and pre_cost_val.strip() else None
                    except ValueError:
                        pass
                    if cost_val is not None and cost_val.strip():
                        try:
                            metric = int(cost_val)
                        except ValueError:
                            pass
                return (ad, metric)

            last_network = None
            for line in block.split("\n"):
                line_stripped = line.strip()
                if not line_stripped or ("Destination" in line_stripped and "Mask" in line_stripped) or line_stripped.startswith("-") or "Route Flags" in line_stripped or "Routing Tables" in line_stripped or "Destinations " in line_stripped:
                    continue
                m = full_line_re.match(line_stripped)
                if m:
                    network = m.group(1)
                    proto_str = m.group(2)
                    pre_cost_val = m.group(3)
                    cost_val = m.group(4) if m.lastindex >= 4 else None
                    next_hop = m.group(5)
                    rest = m.group(6) if m.lastindex >= 6 else ""
                    iface = (rest or "").strip()
                    if not is_valid_ipv4(network.split("/")[0]):
                        continue
                    if "/" not in network and re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", network):
                        network = network + "/32"
                    last_network = network
                    proto = proto_map.get((proto_str or "").lower()) or (proto_str[:1].upper() if proto_str else "?")
                    admin_dist, metric = _parse_pre_cost(pre_cost_val, cost_val)
                    routing_data["routes"].append({
                        "protocol": proto,
                        "network": network,
                        "next_hop": next_hop if next_hop != "-" and is_valid_ipv4(next_hop) else "",
                        "interface": iface if iface and iface != "-" else "",
                        "admin_distance": admin_dist,
                        "metric": metric,
                    })
                    continue
                mc = cont_line_re.match(line_stripped)
                if mc and last_network:
                    proto_str = mc.group(1)
                    pre_cost_val = mc.group(2)
                    cost_val = mc.group(3) if mc.lastindex >= 3 else None
                    next_hop = mc.group(4)
                    rest = mc.group(5) if mc.lastindex >= 5 else ""
                    if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", proto_str):
                        continue
                    iface = (rest or "").strip()
                    proto = proto_map.get((proto_str or "").lower()) or (proto_str[:1].upper() if proto_str else "?")
                    admin_dist, metric = _parse_pre_cost(pre_cost_val, cost_val)
                    routing_data["routes"].append({
                        "protocol": proto,
                        "network": last_network,
                        "next_hop": next_hop if next_hop != "-" and is_valid_ipv4(next_hop) else "",
                        "interface": iface if iface and iface != "-" else "",
                        "admin_distance": admin_dist,
                        "metric": metric,
                    })

        # RIP learned networks (2.3.2.5.5.2) and hop count (2.3.2.5.5.3): from routing table protocol R
        if routing_data.get("rip") is not None:
            routing_data["rip"].setdefault("learned_networks", [])
            rip_routes = [r for r in routing_data.get("routes", []) if (r.get("protocol") or "").upper() == "R"]
            routing_data["rip"]["learned_networks"] = [r["network"] for r in rip_routes]
            metrics = [r["metric"] for r in rip_routes if r.get("metric") is not None]
            routing_data["rip"]["hop_count"] = max(metrics) if metrics else None

        # OSPF learned prefix summary (2.3.2.5.2.7): from routing table entries with protocol O
        if routing_data.get("ospf") and isinstance(routing_data["ospf"].get("learned_prefixes"), list):
            routing_data["ospf"]["learned_prefixes"] = [r["network"] for r in routing_data.get("routes", []) if r.get("protocol") == "O"]

        return routing_data
    
    def extract_neighbors(self, content: str) -> List[Dict[str, Any]]:
        """
        2.3.2.6 Neighbor & Topology (Scope 2.3.2.6.1–2.3.2.6.7).
        Huawei uses LLDP only. Output: device_name, ip_address, platform, local_port, remote_port, capabilities, discovery_protocol.
        """
        neighbors: List[Dict[str, Any]] = []
        # Use last "display lldp neighbor" block (without "brief") for full output
        full_matches = list(
            re.finditer(
                r"display\s+lldp\s+neighbor(?!\s+brief)\s*(.*?)(?=display\s+|#\s*$|\n\s*\[?<?\w+>?\]?\s*$|\Z)",
                content,
                re.IGNORECASE | re.DOTALL,
            )
        )
        lldp_output = (full_matches[-1].group(1) or "").strip() if full_matches else ""
        if not lldp_output or "No LLDP" in lldp_output:
            # Fallback: last "display lldp neighbor" (including brief)
            fallback_matches = list(
                re.finditer(
                    r"display\s+lldp\s+neighbor\s*(.*?)(?=display\s+|#\s*$|\n\s*\[?<?\w+>?\]?\s*$|\Z)",
                    content,
                    re.IGNORECASE | re.DOTALL,
                )
            )
            lldp_output = (fallback_matches[-1].group(1) or "").strip() if fallback_matches else ""

        def _make_neighbor(
            device_name: str,
            local_port: str,
            remote_port: Optional[str] = None,
            ip_address: Optional[str] = None,
            platform: Optional[str] = None,
            capabilities: Optional[str] = None,
        ) -> Dict[str, Any]:
            return {
                "device_name": device_name,
                "ip_address": ip_address,
                "platform": platform,
                "local_port": local_port,
                "remote_port": remote_port,
                "capabilities": capabilities,
                "discovery_protocol": "LLDP",
            }

        # 1) Parse detailed format: "Interface has N neighbors:" blocks (2.3.2.6.1–2.3.2.6.6)
        neighbor_pattern = re.compile(
            r"(\S+)\s+has\s+\d+\s+neighbors:(.*?)(?=\n\S+\s+has\s+\d+\s+neighbors|\ndisplay\s+|\n\s*<|\Z)",
            re.IGNORECASE | re.DOTALL,
        )
        for match in neighbor_pattern.finditer(lldp_output):
            local_port = match.group(1).strip()
            block = match.group(2)
            if not is_valid_interface_name(local_port):
                        continue
            system_name_m = re.search(r"System\s+name\s*:\s*(\S+)", block, re.IGNORECASE) or re.search(r"SysName\s*:\s*(\S+)", block, re.IGNORECASE)
            device_name = (system_name_m.group(1) or "").strip() if system_name_m else None
            if not device_name:
                continue
            port_id_m = re.search(r"Port\s+ID\s*:\s*(\S+)", block, re.IGNORECASE) or re.search(r"PortID\s*:\s*(\S+)", block, re.IGNORECASE)
            remote_port = (port_id_m.group(1) or "").strip() if port_id_m else None
            ip_m = re.search(r"Management\s+address\s*:\s*(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", block, re.IGNORECASE) or re.search(r"Management\s+Address\s*:\s*(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", block, re.IGNORECASE)
            ip_address = ip_m.group(1).strip() if ip_m and is_valid_ipv4(ip_m.group(1)) else None
            # Platform/Model (2.3.2.6.3): first line of System description
            desc_m = re.search(r"System\s+description\s*:\s*([^\n]+)", block, re.IGNORECASE)
            platform = (desc_m.group(1) or "").strip() if desc_m else None
            if platform and len(platform) > 80:
                platform = platform[:80].strip()
            # Capabilities (2.3.2.6.6): supported + enabled
            cap_sup = re.search(r"System\s+capabilities\s+supported\s*:\s*([^\n]+)", block, re.IGNORECASE)
            cap_en = re.search(r"System\s+capabilities\s+enabled\s*:\s*([^\n]+)", block, re.IGNORECASE)
            caps = []
            if cap_sup and cap_sup.group(1).strip():
                caps.append("supported: " + cap_sup.group(1).strip())
            if cap_en and cap_en.group(1).strip():
                caps.append("enabled: " + cap_en.group(1).strip())
            capabilities = "; ".join(caps) if caps else None
            key = (device_name, local_port)
            if not any((n.get("device_name"), n.get("local_port")) == key for n in neighbors):
                neighbors.append(_make_neighbor(device_name, local_port, remote_port, ip_address, platform, capabilities))

        # 2) Parse brief format and add any missing (no duplicate by device_name + local_port)
        brief_section = re.search(r"display\s+lldp\s+neighbor\s+brief(.*?)(?=display\s+|#\s*$|\n\s*\[?<?\w+>?\]?|\Z)", content, re.IGNORECASE | re.DOTALL)
        if brief_section:
            brief_text = brief_section.group(1)
            header = re.search(r"Local\s+Intf.*?Neighbor\s+Dev.*?Neighbor\s+Intf", brief_text, re.IGNORECASE)
            if header:
                for line in brief_text[header.end() :].split("\n"):
                    line = line.strip()
                    if not line or line.startswith("---") or any(k in line.lower() for k in ["local", "neighbor", "intf", "dev"]):
                        continue
                    parts = line.split()
                    if len(parts) >= 3:
                        local_port = parts[0]
                        device_name = parts[1]
                        remote_port = parts[2]
                        if not is_valid_interface_name(local_port):
                            continue
                        key = (device_name, local_port)
                        if not any((n.get("device_name"), n.get("local_port")) == key for n in neighbors):
                            neighbors.append(_make_neighbor(device_name, local_port, remote_port, None, None, None))
        
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
            
            # Extract privilege level from user config block (2.3.2.8)
            privilege_level = None
            privilege_match = re.search(r'privilege\s+level\s+(\d+)', user_config, re.IGNORECASE)
            if privilege_match:
                try:
                    privilege_level = int(privilege_match.group(1))
                except ValueError:
                    pass
            # Extract service-type (terminal, ssh, telnet, etc.)
            service_types = []
            for st_m in re.finditer(r'service-type\s+(\S+)', user_config, re.IGNORECASE):
                service_types.append(st_m.group(1).strip().lower())
            service_type_str = ",".join(service_types) if service_types else None
            
            # Check if user already exists
            existing_user = next((u for u in security["user_accounts"] if u.get("username") == username), None)
            if not existing_user:
                security["user_accounts"].append({
                    "username": username,
                    "privilege_level": privilege_level,
                    "service_type": service_type_str,
                })
            else:
                if privilege_level is not None and existing_user.get("privilege_level") is None:
                    existing_user["privilege_level"] = privilege_level
                if service_type_str and existing_user.get("service_type") is None:
                    existing_user["service_type"] = service_type_str
        
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
        
        # Parse display interface for Eth-Trunk status and member table (PortName Status Weight)
        eth_trunk_blocks = re.finditer(
            r'(Eth-Trunk\d+)\s+current\s+state\s*:\s*(UP|DOWN)(.*?)(?=\n\S+\s+current\s+state\s*:|\n<|\n$|$)',
            content,
            re.IGNORECASE | re.DOTALL,
        )
        trunk_status_by_name = {}
        trunk_member_status = {}  # name -> [(port, status), ...]
        for blk in eth_trunk_blocks:
            name = blk.group(1)
            state = (blk.group(2) or "").strip().upper()
            body = blk.group(3) or ""
            trunk_status_by_name[name] = "Up" if state == "UP" else "Down"
            members_list = []
            for line in body.split("\n"):
                line = line.strip()
                port_m = re.match(r"^(GigabitEthernet\d+/\d+/\d+|GE\d+/\d+/\d+|Ethernet\d+/\d+/\d+)\s+(UP|DOWN|Master)", line, re.IGNORECASE)
                if port_m:
                    port_name = port_m.group(1)
                    st = (port_m.group(2) or "UP").upper()
                    members_list.append({"interface": port_name, "status": "Bundled" if st == "UP" else "Down"})
            if members_list:
                trunk_member_status[name] = members_list

        # Build etherchannel list matching Cisco structure: name, mode, status, members: [{ interface, status }]
        etherchannel_list = []
        for trunk_id, trunk in sorted(ether_trunk_map.items(), key=lambda x: x[0]):
            name = trunk.get("name") or f"Eth-Trunk{trunk_id}"
            mode = (trunk.get("mode") or "LACP").upper()
            status = trunk_status_by_name.get(name)
            if status is None:
                status = "Up" if trunk.get("members") else "Down"
            members_raw = sorted(trunk["members"]) if isinstance(trunk["members"], (set, list)) else []
            member_list = trunk_member_status.get(name)
            if not member_list:
                member_list = [{"interface": m, "status": "Bundled"} for m in members_raw]
            etherchannel_list.append({
                "name": name,
                "mode": mode,
                "status": status,
                "members": member_list,
            })
        ha["etherchannel"] = etherchannel_list
        ha["etherchannels"] = etherchannel_list
        
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
