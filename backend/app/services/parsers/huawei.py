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
        """Parse complete Huawei configuration - with comprehensive error handling"""
        try:
            # Extract each section with individual error handling
            # Initialize with default values for consistency (empty lists instead of None where appropriate)
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
                device_overview = self.extract_device_overview(content)
            except Exception as e:
                print(f"⚠️ Error extracting device overview from {filename}: {e}")
                import traceback
                traceback.print_exc()
            
            try:
                interfaces = self.extract_interfaces(content)
            except Exception as e:
                print(f"⚠️ Error extracting interfaces from {filename}: {e}")
                import traceback
                traceback.print_exc()
            
            try:
                vlans = self.extract_vlans(content)
            except Exception as e:
                print(f"⚠️ Error extracting VLANs from {filename}: {e}")
                import traceback
                traceback.print_exc()
            
            try:
                stp = self.extract_stp(content)
            except Exception as e:
                print(f"⚠️ Error extracting STP from {filename}: {e}")
                import traceback
                traceback.print_exc()
            
            try:
                routing = self.extract_routing(content)
            except Exception as e:
                print(f"⚠️ Error extracting routing from {filename}: {e}")
                import traceback
                traceback.print_exc()
            
            try:
                neighbors = self.extract_neighbors(content)
            except Exception as e:
                print(f"⚠️ Error extracting neighbors from {filename}: {e}")
                import traceback
                traceback.print_exc()
            
            try:
                mac_arp = self.extract_mac_arp(content)
            except Exception as e:
                print(f"⚠️ Error extracting MAC/ARP from {filename}: {e}")
                import traceback
                traceback.print_exc()
            
            try:
                security = self.extract_security(content)
            except Exception as e:
                print(f"⚠️ Error extracting security from {filename}: {e}")
                import traceback
                traceback.print_exc()
            
            try:
                ha = self.extract_ha(content)
            except Exception as e:
                print(f"⚠️ Error extracting HA from {filename}: {e}")
                import traceback
                traceback.print_exc()
            
            # Build config object
            try:
                config = DeviceConfig(
                    device_overview=device_overview,
                    interfaces=interfaces,
                    vlans=vlans,
                    stp=stp,
                    routing=routing,
                    neighbors=neighbors,
                    mac_arp=mac_arp,
                    security=security,
                    ha=ha,
                )
                return config.model_dump(mode='python')
            except Exception as e:
                print(f"⚠️ Error building DeviceConfig from {filename}: {e}")
                import traceback
                traceback.print_exc()
                # Return partial structure
                return {
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
        
        # Extract from display version
        version_section = re.search(r'display\s+version(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if version_section:
            version_output = version_section.group(1)
            
            # Extract model - try multiple patterns
            model_patterns = [
                r'Quidway\s+(\S+)\s+uptime',
                r'HUAWEI\s+(\S+)\s+uptime',
                r'(\S+-\d+\S*)\'s\s+Device\s+status',
            ]
            for pattern in model_patterns:
                model_match = re.search(pattern, version_output, re.IGNORECASE)
                if model_match:
                    overview["model"] = model_match.group(1)
                    break
            
            # Extract OS version
            vrp_match = re.search(r'Version\s+([\d.]+)', version_output, re.IGNORECASE)
            if vrp_match:
                overview["os_version"] = vrp_match.group(1)
            
            # Extract uptime
            uptime_match = re.search(r'uptime\s+is\s+(.+?)(?:\n|<|$)', version_output, re.IGNORECASE)
            if uptime_match:
                overview["uptime"] = uptime_match.group(1).strip()
        
        # Extract serial number from display esn (if present)
        # Handle simulator artifacts: "Failed to read ESN" or "Error: Unrecognized command"
        esn_section = re.search(r'display\s+esn(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if esn_section:
            esn_output = esn_section.group(1)
            # Guard clause: If contains error, set to "Unknown" for better UI display
            if "Error" in esn_output or "Failed to read ESN" in esn_output or "Unrecognized command" in esn_output:
                overview["serial_number"] = "Unknown"
            else:
                # Try to extract ESN value
                esn_value = re.search(r'ESN[:\s]+(\S+)', esn_output, re.IGNORECASE)
                if esn_value:
                    esn_candidate = esn_value.group(1)
                    # Reject error markers like "^"
                    if esn_candidate != "^" and not esn_candidate.startswith("Error"):
                        overview["serial_number"] = esn_candidate
        
        # Extract management IP from LoopBack0 or Vlanif1
        mgmt_patterns = [
            r'interface\s+LoopBack0.*?ip\s+address\s+(\d+\.\d+\.\d+\.\d+)',
            r'interface\s+Vlanif1.*?ip\s+address\s+(\d+\.\d+\.\d+\.\d+)',
        ]
        for pattern in mgmt_patterns:
            mgmt_match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if mgmt_match:
                ip_candidate = mgmt_match.group(1)
                # Validate IP address
                if is_valid_ipv4(ip_candidate):
                    overview["management_ip"] = ip_candidate
                    break
        
        # Extract CPU utilization from display cpu-usage
        # Handle simulator artifacts: "Warning:CPU usage monitor is disabled"
        cpu_section = re.search(r'display\s+cpu-usage(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if cpu_section:
            cpu_output = cpu_section.group(1)
            # Guard clause: If CPU monitor is disabled, set to 0.0
            if "Warning:CPU usage monitor is disabled" in cpu_output or "Warning:CPU usage monitor is disabled!" in cpu_output:
                overview["cpu_utilization"] = 0.0
            else:
                # Try multiple patterns to extract CPU usage percentage
                # Pattern 1: "CPU Usage            : 1% Max: 100%" (with spaces before colon)
                cpu_match = re.search(r'CPU\s+Usage\s+:\s*(\d+)%', cpu_output, re.IGNORECASE)
                if not cpu_match:
                    # Pattern 2: "CPU Usage: 1%" (standard format)
                    cpu_match = re.search(r'CPU\s+Usage\s*:\s*(\d+)%', cpu_output, re.IGNORECASE)
                if not cpu_match:
                    # Pattern 3: "CPU utilization for five seconds: 1%"
                    cpu_match = re.search(r'CPU\s+utilization.*?(\d+)%', cpu_output, re.IGNORECASE)
                if cpu_match:
                    try:
                        overview["cpu_utilization"] = float(cpu_match.group(1))
                    except (ValueError, AttributeError):
                        pass
        
        # Extract memory usage from display memory-usage
        memory_section = re.search(r'display\s+memory-usage(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if memory_section:
            memory_output = memory_section.group(1)
            # Extract memory usage percentage: "Memory Using Percentage Is: 72%"
            memory_match = re.search(r'Memory\s+Using\s+Percentage\s+Is\s*:\s*(\d+)%', memory_output, re.IGNORECASE)
            if memory_match:
                try:
                    overview["memory_usage"] = float(memory_match.group(1))
                except (ValueError, AttributeError):
                    pass
        
        return overview
    
    def extract_interfaces(self, content: str) -> List[Dict[str, Any]]:
        """2.3.2.2 Interface Information - Dictionary-based to prevent duplicates"""
        # Dictionary keyed by interface name to prevent duplicates
        interfaces_map = {}
        
        # Split content into lines for state machine processing
        lines = content.split('\n')
        current_interface = None
        current_config_lines = []
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Check if this line starts a new interface block
            interface_match = re.match(r'^interface\s+(\S+)', line_stripped, re.IGNORECASE)
            if interface_match:
                # Save previous interface if exists
                if current_interface and current_interface not in interfaces_map:
                    iface_config = '\n'.join(current_config_lines)
                    interfaces_map[current_interface] = self._parse_interface_config(
                        current_interface, iface_config
                    )
                
                # Start new interface
                current_interface = interface_match.group(1)
                current_config_lines = []
                
                # Skip NULL0 and similar
                if "NULL" in current_interface.upper():
                    current_interface = None
                    current_config_lines = []
                    continue
            elif line_stripped == '#' and current_interface:
                # End of interface block (Huawei uses # as separator)
                if current_interface not in interfaces_map:
                    iface_config = '\n'.join(current_config_lines)
                    interfaces_map[current_interface] = self._parse_interface_config(
                        current_interface, iface_config
                    )
                current_interface = None
                current_config_lines = []
            elif current_interface:
                # Accumulate config lines for current interface
                current_config_lines.append(line)
        
        # Handle last interface if file doesn't end with #
        if current_interface and current_interface not in interfaces_map:
            iface_config = '\n'.join(current_config_lines)
            interfaces_map[current_interface] = self._parse_interface_config(
                current_interface, iface_config
            )
        
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
            for iface in interfaces_map.values():
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
        
        # Convert dictionary values to list
        return list(interfaces_map.values())
    
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
        """Determine interface type from name"""
        iface_upper = iface_name.upper()
        if "GIGABITETHERNET" in iface_upper or "GE" in iface_upper:
            return "GigabitEthernet"
        elif "ETHERNET" in iface_upper or "ETH" in iface_upper:
            return "Ethernet"
        elif "ETH-TRUNK" in iface_upper:
            return "Eth-Trunk"
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
        """2.3.2.3 VLAN & L2 Switching - Dictionary-based to prevent duplicates"""
        # Use set to prevent duplicates during collection
        vlan_set = set()
        
        # Parse vlan batch command
        batch_match = re.search(r'vlan\s+batch\s+(.+)', content, re.IGNORECASE)
        if batch_match:
            batch_str = batch_match.group(1).strip()
            # Parse ranges like "10 20 30-40 50"
            for part in batch_str.split():
                if '-' in part:
                    # Range like "30-40"
                    try:
                        start, end = map(int, part.split('-'))
                        vlan_set.update(range(start, end + 1))
                    except ValueError:
                        pass
                else:
                    # Single VLAN
                    try:
                        vlan_set.add(int(part))
                    except ValueError:
                        pass
        
        # Parse individual vlan blocks - use set to prevent duplicates
        vlan_pattern = r'vlan\s+(\d+)'
        for match in re.finditer(vlan_pattern, content, re.IGNORECASE):
            try:
                vlan_id = int(match.group(1))
                vlan_set.add(vlan_id)
            except ValueError:
                pass
        
        # Convert set to sorted list
        vlan_list = sorted(list(vlan_set))
        
        return {
            "vlan_list": vlan_list,
            "total_vlan_count": len(vlan_list),
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
        
        # Extract STP interfaces from "display stp brief"
        stp_brief_section = re.search(r'display\s+stp\s+brief(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if stp_brief_section:
            brief_output = stp_brief_section.group(1)
            # Parse table format: "MSTID  Port                        Role  STP State     Protection"
            # Example: "   0    GigabitEthernet0/0/1        DESI  FORWARDING      NONE"
            lines = brief_output.split('\n')
            header_found = False
            for line in lines:
                line_stripped = line.strip()
                # Skip empty lines
                if not line_stripped:
                    continue
                
                # Skip header lines
                if 'MSTID' in line_stripped or ('Port' in line_stripped and 'Role' in line_stripped and 'STP' in line_stripped):
                    header_found = True
                    continue
                
                # Skip separator lines
                if line_stripped.startswith('---') or line_stripped.startswith('===') or line_stripped.startswith('<'):
                    continue
                
                # Parse data lines - split by whitespace but handle multiple spaces
                parts = [p for p in line_stripped.split() if p]  # Remove empty strings
                if len(parts) >= 4:
                    mstid = parts[0]  # First column is MSTID
                    port = parts[1]  # Second column is port name
                    role = parts[2]  # Third column is role (DESI, ROOT, ALTE, etc.)
                    state = parts[3]  # Fourth column is state (FORWARDING, BLOCKING, etc.)
                    
                    # Validate port is an interface name
                    if is_valid_interface_name(port):
                        stp["interfaces"].append({
                            "port": port,
                            "role": role,
                            "state": state,
                        })
        
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
            })
        
        # Parse OSPF
        ospf_match = re.search(r'ospf\s+(\d+)', content, re.IGNORECASE)
        if ospf_match:
            try:
                process_id = int(ospf_match.group(1))
                ospf_info = {
                    "process_id": process_id,
                    "router_id": None,
                    "areas": [],
                    "networks": [],
                }
                
                # Extract router-id
                router_id_match = re.search(r'ospf\s+\d+.*?router-id\s+(\S+)', content, re.IGNORECASE | re.DOTALL)
                if router_id_match:
                    router_id_candidate = router_id_match.group(1)
                    # Validate router-id is a valid IP address
                    if is_valid_ipv4(router_id_candidate):
                        ospf_info["router_id"] = router_id_candidate
                
                # Extract areas and networks
                ospf_section = re.search(r'ospf\s+\d+(.*?)(?=\n\w+\s+\d+|#|$)', content, re.IGNORECASE | re.DOTALL)
                if ospf_section:
                    area_matches = re.finditer(r'area\s+(\S+)', ospf_section.group(1), re.IGNORECASE)
                    for area_match in area_matches:
                        area = area_match.group(1)
                        if area not in ospf_info["areas"]:
                            ospf_info["areas"].append(area)
                    
                    network_matches = re.finditer(r'network\s+(\S+)', ospf_section.group(1), re.IGNORECASE)
                    for net_match in network_matches:
                        network = net_match.group(1)
                        if network not in ospf_info["networks"]:
                            ospf_info["networks"].append(network)
                
                routing["ospf"] = ospf_info
            except (ValueError, AttributeError):
                pass
        
        # Parse RIP
        rip_match = re.search(r'rip\s+(\d+)', content, re.IGNORECASE)
        if rip_match:
            try:
                process_id = int(rip_match.group(1))
                rip_info = {
                    "process_id": process_id,
                    "version": None,
                    "networks": [],
                }
                
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
                                    })
                        except ValueError:
                            pass
                
                routing["bgp"] = bgp_info
            except (ValueError, AttributeError):
                pass
        
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
                    
                    # Extract system name
                    system_name_match = re.search(r'System\s+name\s*:\s*(\S+)', neighbor_details, re.IGNORECASE)
                    if system_name_match:
                        device_name = system_name_match.group(1)
                        
                        # Extract remote port
                        port_id_match = re.search(r'Port\s+ID\s*:\s*(\S+)', neighbor_details, re.IGNORECASE)
                        remote_port = port_id_match.group(1) if port_id_match else None
                        
                        # Extract IP address
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
        
        # Check for display mac-address
        mac_section = re.search(r'display\s+mac-address(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if mac_section and "No MAC" not in mac_section.group(1):
            mac_table = []
            mac_lines = mac_section.group(1).strip().split('\n')
            for line in mac_lines:
                line = line.strip()
                
                # Guard clauses: Filter garbage lines
                if not line:
                    continue
                if line.startswith('---') or '---' in line:
                    continue
                if any(keyword in line for keyword in ['MAC Address', 'Total:', 'Dynamic:', 'Static:', 'Slot', 'Type']):
                    continue
                
                parts = line.split()
                if len(parts) >= 3:
                    mac_addr = parts[0]
                    
                    # CRITICAL: Validate MAC address format - reject garbage
                    if not is_valid_mac_address(mac_addr):
                        continue
                    
                    vlan = parts[1] if len(parts) > 1 and parts[1].isdigit() else None
                    
                    # Find interface/port dynamically - usually after VLAN column
                    # MAC format: MAC VLAN [-] [-] INTERFACE [TYPE] [AGE]
                    port = None
                    
                    # Try columns after VLAN (usually column 2-4)
                    for i in range(2, min(len(parts), 6)):  # Check up to column 5
                        candidate = parts[i]
                        # Skip dashes and numbers
                        if candidate == '-' or candidate.isdigit():
                            continue
                        # Check if it looks like an interface
                        if is_valid_interface_name(candidate):
                            port = candidate
                            break
                    
                    # If not found, try last column as fallback
                    if not port and len(parts) > 2:
                        last_col = parts[-1]
                        if is_valid_interface_name(last_col):
                            port = last_col
                    
                    mac_table.append({
                        "mac_address": mac_addr,
                        "vlan": int(vlan) if vlan else None,
                        "port": port,  # Can be None if not found
                    })
            
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
                if any(keyword in line for keyword in ['IP ADDRESS', 'Total:', 'Dynamic:', 'Static:', 'Interface:', 'Slot', 'Type']):
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
            
            # Check if this line starts a new ACL block
            # Patterns: "acl number 3000", "acl name MY_ACL", "acl 3000"
            acl_start_match = re.match(r'acl\s+(?:number\s+)?(?:name\s+)?(\S+)', line_stripped, re.IGNORECASE)
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
                    
                    ether_trunk_map[current_trunk_id] = {
                        "id": current_trunk_id,
                        "name": f"Eth-Trunk{current_trunk_id}",
                        "mode": mode,
                        "members": set(),  # Use SET to prevent duplicate members
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
                    
                    ether_trunk_map[current_trunk_id] = {
                        "id": current_trunk_id,
                        "name": f"Eth-Trunk{current_trunk_id}",
                        "mode": mode,
                        "members": set(),  # Use SET to prevent duplicate members
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
            
            ether_trunk_map[current_trunk_id] = {
                "id": current_trunk_id,
                "name": f"Eth-Trunk{current_trunk_id}",
                "mode": mode,
                "members": set(),  # Use SET to prevent duplicate members
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
        
        # Convert dictionary values to list - return empty list if none found
        ha["vrrp"] = list(vrrp_map.values()) if vrrp_map else []
        
        return ha
