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


class VlanL2Switching(BaseModel):
    """2.3.2.3 VLAN & L2 Switching"""
    vlan_list: List[int] = Field(default_factory=list)
    total_vlan_count: int = 0


class STPInfo(BaseModel):
    """2.3.2.4 Spanning Tree Protocol"""
    stp_mode: Optional[str] = None
    root_bridge_status: Optional[bool] = None
    portfast_enabled: Optional[bool] = None
    bpdu_guard: Optional[bool] = None


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


class SecurityManagement(BaseModel):
    """2.3.2.8 Security & Management"""
    user_accounts: List[str] = Field(default_factory=list)
    ssh_enabled: Optional[bool] = None
    snmp_settings: Optional[Dict[str, Any]] = None
    ntp_server: Optional[str] = None
    syslog: Optional[str] = None
    acls: Optional[List[Dict[str, Any]]] = None


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
            device_overview = {}
            interfaces = []
            vlans = {"vlan_list": [], "total_vlan_count": 0}
            stp = {}
            routing = {"static": [], "ospf": None, "rip": None, "bgp": None}
            neighbors = []
            mac_arp = {"mac_table": None, "arp_table": None}
            security = {}
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
                "stp": {},
                "routing": {"static": [], "ospf": None, "rip": None, "bgp": None},
                "neighbors": [],
                "mac_arp": {"mac_table": None, "arp_table": None},
                "security": {},
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
        esn_match = re.search(r'display\s+esn.*?(\S+)', content, re.IGNORECASE | re.DOTALL)
        if esn_match and "Error" not in esn_match.group(0):
            # Try to extract ESN value
            esn_value = re.search(r'ESN[:\s]+(\S+)', esn_match.group(0), re.IGNORECASE)
            if esn_value:
                overview["serial_number"] = esn_value.group(1)
        
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
        cpu_match = re.search(r'CPU\s+Usage\s*:\s*(\d+)%', content, re.IGNORECASE)
        if cpu_match:
            try:
                overview["cpu_utilization"] = float(cpu_match.group(1))
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
        }
        
        # Extract description
        desc_match = re.search(r'description\s+(.+?)(?:\n|#|$)', iface_config, re.IGNORECASE)
        if desc_match:
            iface["description"] = desc_match.group(1).strip()
        
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
            "root_bridge_status": None,
            "portfast_enabled": None,
            "bpdu_guard": None,
        }
        
        # Extract STP mode
        stp_mode_match = re.search(r'stp\s+mode\s+(stp|rstp|mstp)', content, re.IGNORECASE)
        if stp_mode_match:
            stp["stp_mode"] = stp_mode_match.group(1).upper()
        
        # Check for portfast (edged-port)
        if re.search(r'stp\s+edged-port\s+default', content, re.IGNORECASE):
            stp["portfast_enabled"] = True
        elif re.search(r'stp\s+edged-port\s+enable', content, re.IGNORECASE):
            stp["portfast_enabled"] = True
        else:
            # Check per-interface
            if re.search(r'stp\s+edged-port\s+enable', content, re.IGNORECASE):
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
        
        # Parse static routes
        static_pattern = r'ip\s+route-static\s+(\S+)\s+(\S+)(?:\s+(\S+))?'
        for match in re.finditer(static_pattern, content, re.IGNORECASE):
            network = match.group(1)
            mask_or_nexthop = match.group(2)
            third_param = match.group(3) if match.group(3) else None
            
            # Determine if second param is mask or nexthop
            if '.' in mask_or_nexthop:
                # It's a nexthop IP
                nexthop = mask_or_nexthop
                mask = "255.255.255.255"  # Default /32
                interface = third_param
            else:
                # It's a mask length or nexthop name
                if mask_or_nexthop.isdigit():
                    mask = mask_or_nexthop
                    nexthop = third_param if third_param else None
                    interface = None
                else:
                    nexthop = mask_or_nexthop
                    mask = "255.255.255.255"
                    interface = third_param
            
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
        
        # Parse BGP
        bgp_match = re.search(r'bgp\s+(\d+)', content, re.IGNORECASE)
        if bgp_match:
            try:
                as_number = int(bgp_match.group(1))
                bgp_info = {
                    "as_number": as_number,
                    "router_id": None,
                    "peers": [],
                }
                
                # Extract router-id
                router_id_match = re.search(r'bgp\s+\d+.*?router-id\s+(\S+)', content, re.IGNORECASE | re.DOTALL)
                if router_id_match:
                    router_id_candidate = router_id_match.group(1)
                    # Validate router-id is a valid IP address
                    if is_valid_ipv4(router_id_candidate):
                        bgp_info["router_id"] = router_id_candidate
                
                # Extract peers
                peer_pattern = r'peer\s+(\S+)\s+as-number\s+(\d+)'
                for peer_match in re.finditer(peer_pattern, content, re.IGNORECASE):
                    try:
                        bgp_info["peers"].append({
                            "peer": peer_match.group(1),
                            "remote_as": int(peer_match.group(2)),
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
        
        # Check for display lldp neighbor output
        lldp_section = re.search(r'display\s+lldp\s+neighbor(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if lldp_section and "No LLDP" not in lldp_section.group(1):
            lldp_output = lldp_section.group(1)
            
            # Parse detailed neighbor output
            neighbor_pattern = r'(\S+)\s+has\s+\d+\s+neighbors:(.*?)(?=\n\S+\s+has\s+\d+\s+neighbors:|display|#|$)'
            for match in re.finditer(neighbor_pattern, lldp_output, re.IGNORECASE | re.DOTALL):
                local_port = match.group(1)
                neighbor_details = match.group(2)
                
                # Extract system name
                system_name_match = re.search(r'System\s+name\s*:\s*(\S+)', neighbor_details, re.IGNORECASE)
                if system_name_match:
                    device_name = system_name_match.group(1)
                    
                    # Extract remote port
                    port_id_match = re.search(r'Port\s+ID\s*:\s*(\S+)', neighbor_details, re.IGNORECASE)
                    remote_port = port_id_match.group(1) if port_id_match else None
                    
                    # Extract IP address
                    ip_match = re.search(r'Management\s+address\s*:\s*(\d+\.\d+\.\d+\.\d+)', neighbor_details, re.IGNORECASE)
                    ip_address = ip_match.group(1) if ip_match else None
                    
                    neighbors.append({
                        "device_name": device_name,
                        "local_port": local_port,
                        "remote_port": remote_port,
                        "ip_address": ip_address,
                    })
            
            # Also try brief format
            brief_match = re.search(r'Local\s+Intf.*?Neighbor\s+Dev.*?Neighbor\s+Intf.*?\n(.*?)(?=display|#|$)', lldp_output, re.IGNORECASE | re.DOTALL)
            if brief_match:
                brief_lines = brief_match.group(1).strip().split('\n')
                for line in brief_lines:
                    line = line.strip()
                    if not line or '---' in line or any(kw in line.lower() for kw in ['local', 'neighbor', 'intf', 'dev']):
                        continue
                    
                    parts = [p for p in line.split() if p]
                    if len(parts) >= 3:
                        local_port = parts[0]
                        device_name = parts[1]
                        remote_port = parts[2]
                        
                        # Validate
                        if not re.search(r'(Eth|GE|Gi|Fa|Te|Se|Lo|Vl|Po|Tu)', local_port, re.IGNORECASE):
                            continue
                        
                        # Check if already added
                        if not any(n.get("device_name") == device_name and n.get("local_port") == local_port for n in neighbors):
                            neighbors.append({
                                "device_name": device_name,
                                "local_port": local_port,
                                "remote_port": remote_port,
                                "ip_address": None,
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
        
        # Extract user accounts - Filter separator usernames
        user_pattern = r'local-user\s+(\S+)'
        for match in re.finditer(user_pattern, content, re.IGNORECASE):
            username = match.group(1)
            # Validate username - filter out separators and garbage
            if is_valid_username(username) and username not in security["user_accounts"]:
                security["user_accounts"].append(username)
        
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
        
        # Extract ACLs - Use dictionary to prevent duplicates and filter garbage
        acl_map = {}
        # Improved regex: acl (number|name)? <ID> - capture ID, ignore keywords like "advance", "basic", "match-order"
        acl_pattern = r'acl\s+(?:number\s+)?(?:name\s+)?(\S+)(?:\s+(?:advance|basic|match-order))?'
        for match in re.finditer(acl_pattern, content, re.IGNORECASE):
            acl_identifier = match.group(1)
            # Filter out garbage keywords
            if acl_identifier.lower() in ['is', 'name', 'number', 'advance', 'basic', 'match-order']:
                continue
            # Use identifier as key to prevent duplicates
            if acl_identifier not in acl_map:
                acl_map[acl_identifier] = {"name": acl_identifier}
        
        if acl_map:
            security["acls"] = list(acl_map.values())
        
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
                "members": [],  # Will be populated in second pass
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
                            # Use set to prevent duplicate members
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
                    if current_interface not in ether_trunk_map[trunk_id]["members"]:
                        ether_trunk_map[trunk_id]["members"].append(current_interface)
        
        # Convert dictionary values to list and convert sets to lists
        etherchannel_list = []
        for trunk in ether_trunk_map.values():
            trunk_copy = trunk.copy()
            trunk_copy["members"] = sorted(list(trunk["members"]))  # Convert set to sorted list
            etherchannel_list.append(trunk_copy)
        ha["etherchannel"] = etherchannel_list
        
        # Extract VRRP - Use dictionary to prevent duplicates
        vrrp_map = {}
        vrrp_pattern = r'vrrp\s+vrid\s+(\d+)\s+virtual-ip\s+(\d+\.\d+\.\d+\.\d+)'
        for match in re.finditer(vrrp_pattern, content, re.IGNORECASE):
            vrid = match.group(1)
            virtual_ip = match.group(2)
            
            # Use vrid as key to prevent duplicates
            if vrid not in vrrp_map:
                # Find interface context
                vrrp_context = content[max(0, match.start()-500):match.end()+500]
                interface_match = re.search(r'interface\s+(Vlanif\d+)', vrrp_context, re.IGNORECASE)
                interface = interface_match.group(1) if interface_match else None
                
                # Extract priority
                priority = None
                priority_match = re.search(r'vrrp\s+vrid\s+' + vrid + r'.*?priority\s+(\d+)', vrrp_context, re.IGNORECASE | re.DOTALL)
                if priority_match:
                    try:
                        priority = int(priority_match.group(1))
                    except ValueError:
                        pass
                
                vrrp_map[vrid] = {
                    "vrid": vrid,
                    "interface": interface,
                    "virtual_ip": virtual_ip,
                    "priority": priority,
                }
        
        # Convert dictionary values to list
        ha["vrrp"] = list(vrrp_map.values())
        
        return ha
