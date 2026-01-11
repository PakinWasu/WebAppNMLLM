"""Huawei VRP configuration parser"""

import re
from typing import Dict, List, Any
from .base import BaseParser


class HuaweiParser(BaseParser):
    """Parser for Huawei device configurations"""
    
    def detect_vendor(self, content: str) -> bool:
        """Detect if this is a Huawei configuration"""
        # Strong indicators that this is definitely Huawei (check these first)
        strong_indicators = [
            r'display\s+version',
            r'display\s+current-configuration',
            r'display\s+lldp',
            r'display\s+arp',
            r'display\s+mac-address',
            r'display\s+stp',
            r'display\s+ospf',
            r'display\s+bgp',
            r'VRP\s+\(R\)',
            r'Huawei\s+Versatile',
            r'sysname\s+\S+',  # Huawei uses sysname, Cisco uses hostname
            r'port\s+link-type',
            r'port\s+default\s+vlan',
            r'vrrp\s+vrid',
            r'local-user\s+\S+',
            r'info-center',
        ]
        
        # Check for strong Huawei-specific patterns first
        strong_matches = sum(1 for pattern in strong_indicators if re.search(pattern, content, re.IGNORECASE))
        if strong_matches >= 2:
            return True
        
        # Also check for absence of Cisco-specific patterns
        cisco_indicators = [
            r'hostname\s+\S+',  # Cisco uses hostname
            r'show\s+running-config',
            r'show\s+version',
            r'switchport\s+mode',
            r'router\s+ospf',
            r'router\s+bgp',
        ]
        cisco_matches = sum(1 for pattern in cisco_indicators if re.search(pattern, content, re.IGNORECASE))
        
        # If we have Huawei indicators but no Cisco indicators, it's likely Huawei
        if strong_matches >= 1 and cisco_matches == 0:
            return True
        
        return False
    
    def parse(self, content: str, filename: str) -> Dict[str, Any]:
        """Parse complete Huawei configuration"""
        return {
            "device_overview": self.extract_device_overview(content),
            "interfaces": self.extract_interfaces(content),
            "vlans": self.extract_vlans(content),
            "stp": self.extract_stp(content),
            "routing": self.extract_routing(content),
            "neighbors": self.extract_neighbors(content),
            "mac_arp": self.extract_mac_arp(content),
            "security": self.extract_security(content),
            "ha": self.extract_ha(content),
        }
    
    def extract_device_overview(self, content: str) -> Dict[str, Any]:
        """Extract device overview information"""
        overview = {
            "hostname": None,
            "role": None,
            "model": None,
            "platform": None,
            "os_version": None,
            "serial_number": None,
            "mgmt_ip": None,
            "uptime": None,
            "cpu_util": None,
            "mem_util": None,
            "device_status": {},
        }
        
        # Extract sysname (hostname)
        sysname_match = re.search(r'sysname\s+(\S+)', content, re.IGNORECASE)
        if sysname_match:
            overview["hostname"] = sysname_match.group(1)
        
        # If no sysname found, try to extract from prompt in log files (e.g., <ACC1>)
        if not overview["hostname"]:
            prompt_match = re.search(r'<(\S+)>', content)
            if prompt_match:
                overview["hostname"] = prompt_match.group(1)
        
        # Extract role from comments
        role_match = re.search(r'!.*ROLE:\s*(\S+)', content, re.IGNORECASE)
        if role_match:
            overview["role"] = role_match.group(1)
        
        # If role not found in comments, try to infer from hostname/device name
        if not overview.get("role"):
            hostname = overview.get("hostname", "").lower()
            if hostname:
                if "core" in hostname:
                    overview["role"] = "Core"
                elif "dist" in hostname or "distribution" in hostname:
                    overview["role"] = "Distribution"
                elif "access" in hostname:
                    overview["role"] = "Access"
                elif "router" in hostname or "rt" in hostname:
                    overview["role"] = "Router"
                elif "switch" in hostname or "sw" in hostname:
                    overview["role"] = "Switch"
        
        # Extract CPU usage from display cpu-usage
        cpu_match = re.search(r'display\s+cpu-usage.*?CPU\s+Usage\s*:\s*(\d+)%', content, re.IGNORECASE | re.DOTALL)
        if cpu_match:
            try:
                overview["cpu_util"] = int(cpu_match.group(1))
            except (ValueError, AttributeError):
                pass
        
        # Extract Memory usage from display memory-usage
        mem_match = re.search(r'display\s+memory-usage.*?Memory\s+Using\s+Percentage\s+Is:\s*(\d+)%', content, re.IGNORECASE | re.DOTALL)
        if not mem_match:
            # Try alternative pattern (sometimes command has typo like "isplay memory-usage")
            mem_match = re.search(r'Memory\s+utilization\s+statistics.*?Memory\s+Using\s+Percentage\s+Is:\s*(\d+)%', content, re.IGNORECASE | re.DOTALL)
        if mem_match:
            try:
                overview["mem_util"] = int(mem_match.group(1))
            except (ValueError, AttributeError):
                pass
        
        # Extract Device status from display device
        device_match = re.search(r'display\s+device.*?Slot\s+Sub\s+Type.*?Online.*?Power.*?Register.*?Status.*?Role\s*\n.*?\n\s*(\d+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)', content, re.IGNORECASE | re.DOTALL)
        if device_match:
            overview["device_status"] = {
                "slot": device_match.group(1),
                "sub": device_match.group(2),
                "type": device_match.group(3),
                "online": device_match.group(4),
                "power": device_match.group(5),
                "register": device_match.group(6),
                "status": device_match.group(7),
                "role": device_match.group(8) if len(device_match.groups()) >= 8 else None,
            }
        
        # Extract from display version
        version_match = re.search(r'display\s+version.*?(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if version_match:
            version_output = version_match.group(0)
            
            # VRP version - try multiple patterns
            vrp_patterns = [
                r'VRP\s+\(R\)\s+software.*?Version\s+([\d.]+)',
                r'Version\s+([\d.]+)',
                r'VRP.*?Version\s+([\d.]+)',
            ]
            for pattern in vrp_patterns:
                vrp_match = re.search(pattern, version_output, re.IGNORECASE | re.DOTALL)
                if vrp_match:
                    overview["os_version"] = vrp_match.group(1)
                    break
            
            # Model - try multiple patterns (order matters - most specific first)
            # Try to extract from device status first (e.g., "S3700-26C-HI's Device status")
            model_from_device = re.search(r"(\S+-\d+\S*)\'s\s+Device\s+status", version_output, re.IGNORECASE)
            if model_from_device:
                overview["model"] = model_from_device.group(1)
            else:
                model_patterns = [
                    r'!.*Model:\s*(\S+)',  # From comments first
                    r'Quidway\s+(\S+)\s+uptime',  # "Quidway S3700-26C-HI uptime"
                    r'HUAWEI\s+(\S+)\s+uptime',  # "HUAWEI AR6120 uptime" - most specific
                    r'HUAWEI\s+(\S+)',  # "HUAWEI AR6120"
                    r'Model:\s*(\S+)',  # "Model: AR6120"
                    r'\[SLOT\s+\d+\].*?(\S+)\s+Main Board',  # From slot info
                ]
                for pattern in model_patterns:
                    model_match = re.search(pattern, version_output, re.IGNORECASE)
                    if model_match:
                        model_name = model_match.group(1)
                        # Skip common words
                        if model_name.lower() not in ['uptime', 'software', 'version', 'hardware', 'versatile', 'routing', 'platform']:
                            overview["model"] = model_name
                            break
            
            # Serial number
            serial_match = re.search(r'Serial[:\s]+(\S+)', version_output, re.IGNORECASE)
            if serial_match:
                overview["serial_number"] = serial_match.group(1)
            
            # Uptime - improved pattern
            uptime_match = re.search(r'uptime\s+is\s+(.+?)(?:\n|<|$)', version_output, re.IGNORECASE)
            if uptime_match:
                overview["uptime"] = uptime_match.group(1).strip()
        
        # Extract from comments if not found (check before version output patterns)
        if not overview.get("model"):
            # Try comment patterns first (most reliable)
            comment_patterns = [
                r'!.*Model:\s*(\S+)',
                r'!.*MODEL:\s*(\S+)',
            ]
            for pattern in comment_patterns:
                model_match = re.search(pattern, content, re.IGNORECASE)
                if model_match:
                    overview["model"] = model_match.group(1)
                    break
        
        if not overview.get("serial_number"):
            serial_match = re.search(r'!.*Serial:\s*(\S+)', content, re.IGNORECASE)
            if serial_match:
                overview["serial_number"] = serial_match.group(1)
        
        # Extract management IP
        mgmt_ip_match = re.search(r'interface\s+Vlanif\s*\d+.*?ip\s+address\s+(\d+\.\d+\.\d+\.\d+)', content, re.IGNORECASE | re.DOTALL)
        if mgmt_ip_match:
            overview["mgmt_ip"] = mgmt_ip_match.group(1)
        
        return overview
    
    def extract_interfaces(self, content: str) -> List[Dict[str, Any]]:
        """Extract interface information"""
        interfaces = []
        interface_dict = {}  # Use dict to merge config and display data
        
        # First, parse interface blocks from current-configuration
        interface_pattern = r'interface\s+(\S+)\s*\n(.*?)(?=\ninterface\s+|#|$)'
        for match in re.finditer(interface_pattern, content, re.IGNORECASE | re.DOTALL):
            iface_name = match.group(1)
            iface_config = match.group(2)
            
            iface = {
                "name": iface_name,
                "type": self._get_interface_type(iface_name),
                "admin_status": "up" if "shutdown" not in iface_config.lower() else "down",
                "oper_status": "up",
                "line_protocol": "up",
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
                "statistics": {},
                "bandwidth_util": {},
            }
            
            # Extract description
            desc_match = re.search(r'description\s+(.+?)(?:\n|$)', iface_config, re.IGNORECASE)
            if desc_match:
                iface["description"] = desc_match.group(1).strip()
            
            # Extract IPv4 address
            ip_match = re.search(r'ip\s+address\s+(\d+\.\d+\.\d+\.\d+)', iface_config, re.IGNORECASE)
            if ip_match:
                iface["ipv4_address"] = ip_match.group(1)
                iface["port_mode"] = "routed"
            
            # Extract IPv6 address
            ipv6_match = re.search(r'ipv6\s+address\s+([\da-fA-F:]+/\d+)', iface_config, re.IGNORECASE)
            if ipv6_match:
                iface["ipv6_address"] = ipv6_match.group(1)
            
            # Extract port mode
            if "port link-type access" in iface_config.lower():
                iface["port_mode"] = "access"
                vlan_match = re.search(r'port\s+default\s+vlan\s+(\d+)', iface_config, re.IGNORECASE)
                if vlan_match:
                    iface["access_vlan"] = vlan_match.group(1)
            elif "port link-type trunk" in iface_config.lower():
                iface["port_mode"] = "trunk"
                native_match = re.search(r'port\s+trunk\s+pvid\s+vlan\s+(\d+)', iface_config, re.IGNORECASE)
                if native_match:
                    iface["native_vlan"] = native_match.group(1)
                allowed_match = re.search(r'port\s+trunk\s+allow-pass\s+vlan\s+(.+)', iface_config, re.IGNORECASE)
                if allowed_match:
                    iface["allowed_vlans"] = allowed_match.group(1).strip()
            
            interface_dict[iface_name] = iface
        
        # Parse display interface output to get runtime state and statistics
        display_interface_pattern = r'(\S+)\s+current\s+state\s*:\s*(\S+)\s*\n.*?Line\s+protocol\s+current\s+state\s*:\s*(\S+)(.*?)(?=\n\S+\s+current\s+state\s*:|display|#|$)'
        for match in re.finditer(display_interface_pattern, content, re.IGNORECASE | re.DOTALL):
            iface_name = match.group(1)
            oper_status = match.group(2).upper()
            line_protocol = match.group(3).upper()
            iface_details = match.group(4)
            
            # Get or create interface entry
            if iface_name not in interface_dict:
                interface_dict[iface_name] = {
                    "name": iface_name,
                    "type": self._get_interface_type(iface_name),
                    "admin_status": "up",
                    "oper_status": oper_status.lower(),
                    "line_protocol": line_protocol.lower(),
                    "description": None,
                    "ipv4_address": None,
                    "mac_address": None,
                    "port_mode": None,
                    "statistics": {},
                    "bandwidth_util": {},
                }
            
            iface = interface_dict[iface_name]
            iface["oper_status"] = oper_status.lower()
            iface["line_protocol"] = line_protocol.lower()
            
            # Extract description from display output
            desc_match = re.search(r'Description[:\s]+(.+?)(?:\n|Switch|Route|IP)', iface_details, re.IGNORECASE)
            if desc_match and not iface.get("description"):
                iface["description"] = desc_match.group(1).strip()
            
            # Extract MAC address
            mac_match = re.search(r'Hardware\s+address\s+is\s+([\da-fA-F-]+)', iface_details, re.IGNORECASE)
            if mac_match:
                iface["mac_address"] = mac_match.group(1)
            
            # Extract Speed
            speed_match = re.search(r'Speed\s*:\s*(\d+)\s*(?:Mbps|Gbps|Kbps)?', iface_details, re.IGNORECASE)
            if speed_match:
                speed_val = speed_match.group(1)
                # Try to determine unit from context
                speed_unit = speed_match.group(0).upper()
                if 'GBPS' in speed_unit or 'G' in speed_unit:
                    iface["speed"] = f"{speed_val}Gbps"
                elif 'MBPS' in speed_unit or 'M' in speed_unit:
                    iface["speed"] = f"{speed_val}Mbps"
                else:
                    iface["speed"] = f"{speed_val}Mbps"  # Default to Mbps
            else:
                # Try alternative pattern
                speed_match = re.search(r'(\d+)\s*(?:Mbps|Gbps)', iface_details, re.IGNORECASE)
                if speed_match:
                    iface["speed"] = speed_match.group(0)
            
            # Extract Duplex Mode
            duplex_match = re.search(r'Duplex\s*:\s*(\w+)', iface_details, re.IGNORECASE)
            if duplex_match:
                iface["duplex"] = duplex_match.group(1).lower()
            else:
                # Try alternative pattern
                duplex_match = re.search(r'(?:full|half)\s*duplex', iface_details, re.IGNORECASE)
                if duplex_match:
                    iface["duplex"] = duplex_match.group(0).split()[0].lower()
            
            # Extract MTU
            mtu_match = re.search(r'MTU\s*:\s*(\d+)', iface_details, re.IGNORECASE)
            if mtu_match:
                iface["mtu"] = int(mtu_match.group(1))
            
            # Extract PVID
            pvid_match = re.search(r'PVID\s*:\s*(\d+)', iface_details, re.IGNORECASE)
            if pvid_match:
                if not iface.get("native_vlan"):
                    iface["native_vlan"] = pvid_match.group(1)
            
            # Extract statistics
            input_match = re.search(r'Input:\s+(\d+)\s+bytes,\s+(\d+)\s+packets', iface_details, re.IGNORECASE)
            if input_match:
                iface["statistics"]["input_bytes"] = int(input_match.group(1))
                iface["statistics"]["input_packets"] = int(input_match.group(2))
            
            output_match = re.search(r'Output:\s+(\d+)\s+bytes,\s+(\d+)\s+packets', iface_details, re.IGNORECASE)
            if output_match:
                iface["statistics"]["output_bytes"] = int(output_match.group(1))
                iface["statistics"]["output_packets"] = int(output_match.group(2))
            
            # Extract bandwidth utilization
            input_util_match = re.search(r'Input\s+bandwidth\s+utilization\s*:\s*(\d+)%', iface_details, re.IGNORECASE)
            if input_util_match:
                iface["bandwidth_util"]["input"] = int(input_util_match.group(1))
            
            output_util_match = re.search(r'Output\s+bandwidth\s+utilization\s*:\s*(\d+)%', iface_details, re.IGNORECASE)
            if output_util_match:
                iface["bandwidth_util"]["output"] = int(output_util_match.group(1))
        
        # Parse display interface brief
        brief_match = re.search(r'display\s+interface\s+brief.*?Interface\s+PHY\s+Protocol.*?\n(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if brief_match:
            brief_lines = brief_match.group(1).strip().split('\n')
            for line in brief_lines:
                parts = line.split()
                if len(parts) >= 4:
                    iface_name = parts[0]
                    phy_status = parts[1].lower()
                    protocol_status = parts[2].lower()
                    
                    if iface_name not in interface_dict:
                        interface_dict[iface_name] = {
                            "name": iface_name,
                            "type": self._get_interface_type(iface_name),
                            "admin_status": phy_status,
                            "oper_status": phy_status,
                            "line_protocol": protocol_status,
                        }
                    
                    iface = interface_dict[iface_name]
                    iface["admin_status"] = phy_status
                    iface["oper_status"] = phy_status
                    iface["line_protocol"] = protocol_status
                    
                    # Extract utilization if available
                    if len(parts) >= 5:
                        try:
                            in_util = parts[3].rstrip('%')
                            out_util = parts[4].rstrip('%')
                            if in_util != '--':
                                iface.setdefault("bandwidth_util", {})["input"] = int(in_util)
                            if out_util != '--':
                                iface.setdefault("bandwidth_util", {})["output"] = int(out_util)
                        except (ValueError, IndexError):
                            pass
        
        # Parse display ip interface for IP interface details
        ip_interface_pattern = r'(\S+)\s+current\s+state\s*:\s*(\S+).*?The\s+Maximum\s+Transmit\s+Unit\s*:\s*(\d+)\s+bytes(.*?)(?=\n\S+\s+current\s+state\s*:|display|#|$)'
        for match in re.finditer(ip_interface_pattern, content, re.IGNORECASE | re.DOTALL):
            iface_name = match.group(1)
            ip_details = match.group(4)
            
            if iface_name in interface_dict:
                iface = interface_dict[iface_name]
                # Extract MTU
                mtu_val = match.group(3)
                if mtu_val:
                    iface["mtu"] = int(mtu_val)
                
                # Extract IPv4 address if not already set
                ipv4_match = re.search(r'Internet\s+Address\s+is\s+(\d+\.\d+\.\d+\.\d+/\d+)', ip_details, re.IGNORECASE)
                if ipv4_match and not iface.get("ipv4_address"):
                    iface["ipv4_address"] = ipv4_match.group(1).split('/')[0]
                
                # Extract IP statistics if available
                ip_input_match = re.search(r'input\s+packets\s*:\s*(\d+)', ip_details, re.IGNORECASE)
                if ip_input_match:
                    iface.setdefault("statistics", {})["ip_input_packets"] = int(ip_input_match.group(1))
        
        # Parse display ipv6 interface for IPv6 addresses
        ipv6_interface_pattern = r'display\s+ipv6\s+interface.*?(\S+)\s+current\s+state\s*:\s*(\S+).*?IPv6\s+address\s+is\s+([\da-fA-F:]+/\d+)(.*?)(?=\n\S+\s+current\s+state\s*:|display|#|$)'
        for match in re.finditer(ipv6_interface_pattern, content, re.IGNORECASE | re.DOTALL):
            iface_name = match.group(1)
            ipv6_addr = match.group(3)
            
            if iface_name in interface_dict:
                iface = interface_dict[iface_name]
                iface["ipv6_address"] = ipv6_addr
        
        # Convert dict to list
        interfaces = list(interface_dict.values())
        
        return interfaces
    
    def _get_interface_type(self, iface_name: str) -> str:
        """Determine interface type from name"""
        if "GigabitEthernet" in iface_name or "GigE" in iface_name:
            return "GigabitEthernet"
        elif "Ethernet" in iface_name or "Eth" in iface_name:
            return "Ethernet"
        elif "Eth-Trunk" in iface_name:
            return "Eth-Trunk"
        elif "Vlanif" in iface_name:
            return "VLAN"
        elif "LoopBack" in iface_name:
            return "Loopback"
        else:
            return "Unknown"
    
    def extract_vlans(self, content: str) -> Dict[str, Any]:
        """Extract VLAN information"""
        vlans = {
            "vlan_list": [],
            "vlan_names": {},
            "vlan_status": {},
            "vlan_type": {},
            "vlan_property": {},
            "vlan_ports": {},
            "access_ports": {},
            "trunk_ports": {},
            "port_vlan_mapping": {},
            "native_vlan": None,
            "total_vlan_count": 0,
        }
        
        # Parse vlan blocks from config
        vlan_pattern = r'vlan\s+(\d+)'
        for match in re.finditer(vlan_pattern, content, re.IGNORECASE):
            vlan_id = match.group(1)
            if vlan_id not in vlans["vlan_list"]:
                vlans["vlan_list"].append(vlan_id)
        
        # Extract VLAN names
        name_pattern = r'vlan\s+(\d+).*?name\s+(\S+)'
        for match in re.finditer(name_pattern, content, re.IGNORECASE | re.DOTALL):
            vlan_id = match.group(1)
            vlan_name = match.group(2)
            vlans["vlan_names"][vlan_id] = vlan_name
        
        # Parse display vlan output
        vlan_display_match = re.search(r'display\s+vlan.*?The\s+total\s+number\s+of\s+vlans\s+is\s*:\s*(\d+).*?VID\s+Type\s+Ports(.*?)VID\s+Status\s+Property(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if vlan_display_match:
            total_count = vlan_display_match.group(1)
            ports_section = vlan_display_match.group(2)
            status_section = vlan_display_match.group(3)
            
            # Parse VLAN ports section
            vlan_port_lines = ports_section.strip().split('\n')
            current_vid = None
            current_ports = []
            for line in vlan_port_lines:
                line = line.strip()
                if not line or '---' in line:
                    continue
                
                # Check if line starts with VID
                vid_match = re.match(r'^(\d+)\s+(\S+)\s+(.*)$', line)
                if vid_match:
                    # Save previous VLAN if exists
                    if current_vid:
                        vlans["vlan_ports"][current_vid] = current_ports
                    
                    current_vid = vid_match.group(1)
                    vlans["vlan_type"][current_vid] = vid_match.group(2)
                    port_info = vid_match.group(3)
                    current_ports = [port_info] if port_info.strip() else []
                    
                    if current_vid not in vlans["vlan_list"]:
                        vlans["vlan_list"].append(current_vid)
                elif current_vid and line:
                    # Continuation line for ports
                    current_ports.append(line)
            
            # Save last VLAN
            if current_vid:
                vlans["vlan_ports"][current_vid] = current_ports
            
            # Parse VLAN status section
            status_lines = status_section.strip().split('\n')
            for line in status_lines:
                line = line.strip()
                if not line or '---' in line:
                    continue
                
                parts = line.split()
                if len(parts) >= 3:
                    vlan_id = parts[0]
                    vlans["vlan_status"][vlan_id] = parts[1]
                    vlans["vlan_property"][vlan_id] = parts[2]
                    
                    # Extract description if available
                    if len(parts) > 6:
                        desc = ' '.join(parts[6:])
                        if desc and desc not in vlans.get("vlan_names", {}).get(vlan_id, ""):
                            if vlan_id not in vlans["vlan_names"]:
                                vlans["vlan_names"][vlan_id] = desc
        
        # Parse display port vlan output
        port_vlan_match = re.search(r'display\s+port\s+vlan.*?Port\s+Link\s+Type\s+PVID\s+Trunk\s+VLAN\s+List.*?\n(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if port_vlan_match:
            port_vlan_lines = port_vlan_match.group(1).strip().split('\n')
            for line in port_vlan_lines:
                line = line.strip()
                if not line or '---' in line:
                    continue
                
                parts = line.split()
                if len(parts) >= 3:
                    port_name = parts[0]
                    link_type = parts[1].lower()
                    pvid = parts[2]
                    trunk_vlans = parts[3] if len(parts) > 3 and parts[3] != '-' else None
                    
                    vlans["port_vlan_mapping"][port_name] = {
                        "link_type": link_type,
                        "pvid": pvid,
                        "trunk_vlans": trunk_vlans.split() if trunk_vlans else [],
                    }
                    
                    # Categorize ports
                    if link_type == "access":
                        if pvid not in vlans["access_ports"]:
                            vlans["access_ports"][pvid] = []
                        vlans["access_ports"][pvid].append(port_name)
                    elif link_type == "trunk":
                        if trunk_vlans:
                            for vlan in trunk_vlans.split():
                                if vlan not in vlans["trunk_ports"]:
                                    vlans["trunk_ports"][vlan] = []
                                vlans["trunk_ports"][vlan].append(port_name)
        
        vlans["total_vlan_count"] = len(vlans["vlan_list"])
        
        return vlans
    
    def extract_stp(self, content: str) -> Dict[str, Any]:
        """Extract Spanning Tree Protocol information"""
        stp = {
            "mode": None,
            "root_bridge_id": None,
            "root_priority": None,
            "is_root_bridge": False,
            "bridge_id": None,
            "root_port": None,
            "bpdu_protection": False,
            "port_roles": {},
            "port_states": {},
            "port_costs": {},
            "port_priorities": {},
            "port_instances": {},
            "portfast_enabled": {},
            "bpdu_guard_enabled": {},
            "instances": {},
        }
        
        # Extract STP mode from config
        if "stp enable" in content.lower():
            mode_match = re.search(r'stp\s+mode\s+(\S+)', content, re.IGNORECASE)
            if mode_match:
                stp["mode"] = mode_match.group(1).upper()
            else:
                stp["mode"] = "MSTP"  # Default for Huawei
        
        # Parse display stp output
        stp_display_match = re.search(r'display\s+stp.*?\[Mode\s+(\S+)\].*?CIST\s+Bridge\s*:\s*([\d.]+)\.([\da-fA-F-]+).*?CIST\s+Root/ERPC\s*:\s*([\d.]+)\.([\da-fA-F-]+)\s*/\s*(\d+)(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if stp_display_match:
            stp["mode"] = stp_display_match.group(1).upper()
            stp["bridge_id"] = f"{stp_display_match.group(2)}.{stp_display_match.group(3)}"
            stp["root_bridge_id"] = f"{stp_display_match.group(4)}.{stp_display_match.group(5)}"
            stp["root_priority"] = stp_display_match.group(4)
            stp["is_root_bridge"] = (stp["bridge_id"] == stp["root_bridge_id"])
            
            stp_details = stp_display_match.group(7)
            
            # Extract BPDU Protection
            if "BPDU-Protection" in stp_details:
                bpdu_match = re.search(r'BPDU-Protection\s*:\s*(\S+)', stp_details, re.IGNORECASE)
                if bpdu_match:
                    stp["bpdu_protection"] = bpdu_match.group(1).upper() == "ENABLED"
            
            # Extract Root Port
            root_port_match = re.search(r'CIST\s+RootPortId\s*:\s*(\S+)', stp_details, re.IGNORECASE)
            if root_port_match:
                stp["root_port"] = root_port_match.group(1)
            
            # Parse port details
            port_pattern = r'----\[Port\d+\((\S+)\)\]\[(\S+)\].*?Port\s+Role\s*:\s*(\S+).*?Port\s+Priority\s*:\s*(\d+).*?Port\s+Cost.*?Active=(\d+)'
            for port_match in re.finditer(port_pattern, stp_details, re.IGNORECASE | re.DOTALL):
                port_name = port_match.group(1)
                port_state = port_match.group(2).upper()
                port_role = port_match.group(3).upper()
                port_priority = port_match.group(4)
                port_cost = port_match.group(5)
                
                stp["port_roles"][port_name] = port_role
                stp["port_states"][port_name] = port_state
                stp["port_priorities"][port_name] = int(port_priority)
                stp["port_costs"][port_name] = int(port_cost)
                
                # Extract BPDU guard/portfast from port details
                if "Port Edged" in port_match.group(0):
                    edged_match = re.search(r'Port\s+Edged\s*:\s*.*?Active=(\S+)', port_match.group(0), re.IGNORECASE)
                    if edged_match:
                        stp["portfast_enabled"][port_name] = edged_match.group(1).lower() == "enabled"
                
                protection_match = re.search(r'Protection\s+Type\s*:\s*(\S+)', port_match.group(0), re.IGNORECASE)
                if protection_match:
                    protection = protection_match.group(1).upper()
                    stp["bpdu_guard_enabled"][port_name] = protection == "BPDU" or "BPDU" in protection
        
        # Parse display stp brief output
        stp_brief_match = re.search(r'display\s+stp\s+brief.*?MSTID\s+Port\s+Role\s+STP\s+State\s+Protection.*?\n(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if stp_brief_match:
            brief_lines = stp_brief_match.group(1).strip().split('\n')
            for line in brief_lines:
                line = line.strip()
                if not line or '---' in line:
                    continue
                
                parts = line.split()
                if len(parts) >= 4:
                    mstid = parts[0]
                    port_name = parts[1]
                    role = parts[2].upper()
                    state = parts[3].upper()
                    protection = parts[4] if len(parts) > 4 else "NONE"
                    
                    # Store instance info
                    if mstid not in stp["instances"]:
                        stp["instances"][mstid] = {}
                    
                    stp["instances"][mstid][port_name] = {
                        "role": role,
                        "state": state,
                        "protection": protection.upper(),
                    }
                    
                    # Store port instance mapping
                    if port_name not in stp["port_instances"]:
                        stp["port_instances"][port_name] = []
                    if mstid not in stp["port_instances"][port_name]:
                        stp["port_instances"][port_name].append(mstid)
                    
                    # Update port roles/states if not already set
                    if port_name not in stp["port_roles"]:
                        stp["port_roles"][port_name] = role
                    if port_name not in stp["port_states"]:
                        stp["port_states"][port_name] = state
                    
                    # Update BPDU guard status
                    if protection.upper() == "BPDU" or "BPDU" in protection.upper():
                        stp["bpdu_guard_enabled"][port_name] = True
        
        return stp
    
    def extract_routing(self, content: str) -> Dict[str, Any]:
        """Extract routing protocol information"""
        routing = {
            "static": {
                "routes": [],
                "default_route": None,
            },
            "ospf": {
                "router_id": None,
                "process_id": None,
                "areas": [],
                "interfaces": [],
                "neighbors": [],
                "routes": [],
                "dr_bdr": {},
            },
            "eigrp": {
                "as_number": None,
                "router_id": None,
                "neighbors": [],
                "hold_time": None,
                "learned_routes": [],
            },
            "bgp": {
                "local_as": None,
                "router_id": None,
                "peers": [],
                "routes": [],
            },
            "rip": {
                "version": None,
                "networks": [],
                "interfaces": [],
                "hop_count": {},
                "auto_summary": None,
                "passive_interfaces": [],
                "timers": {
                    "update": None,
                    "invalid": None,
                    "holddown": None,
                    "flush": None,
                },
                "admin_distance": None,
            },
            "routing_table": [],
        }
        
        # Parse display ip routing-table
        routing_table_match = re.search(r'display\s+ip\s+routing-table.*?Destination/Mask\s+Proto\s+Pre\s+Cost.*?\n(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if routing_table_match:
            table_lines = routing_table_match.group(1).strip().split('\n')
            for line in table_lines:
                line = line.strip()
                if not line or '---' in line or 'Destinations' in line:
                    continue
                
                parts = line.split()
                if len(parts) >= 6:
                    destination = parts[0]
                    proto = parts[1]
                    pre = parts[2]
                    cost = parts[3]
                    flags = parts[4]
                    next_hop = parts[5]
                    interface = parts[6] if len(parts) > 6 else None
                    
                    route_entry = {
                        "destination": destination,
                        "protocol": proto,
                        "preference": pre,
                        "cost": cost,
                        "flags": flags,
                        "next_hop": next_hop,
                        "interface": interface,
                    }
                    routing["routing_table"].append(route_entry)
                    
                    # Categorize by protocol
                    if proto.upper() == "DIRECT":
                        routing["static"]["routes"].append(route_entry)
                    elif proto.upper() == "STATIC":
                        routing["static"]["routes"].append(route_entry)
                        if destination == "0.0.0.0/0" or destination.startswith("0.0.0.0/"):
                            routing["static"]["default_route"] = next_hop
        
        # Static routes from config
        static_pattern = r'ip\s+route-static\s+(\S+)\s+(\S+)(?:\s+(\S+))?'
        for match in re.finditer(static_pattern, content, re.IGNORECASE):
            network = match.group(1)
            next_hop = match.group(2)
            if network == "0.0.0.0" and next_hop:
                routing["static"]["default_route"] = next_hop
            route_entry = {
                "network": network,
                "next_hop": next_hop,
                "interface": match.group(3) if match.group(3) else None,
                "protocol": "STATIC",
            }
            # Only add if not already in routing_table
            if not any(r.get("destination") == network and r.get("next_hop") == next_hop for r in routing["static"]["routes"]):
                routing["static"]["routes"].append(route_entry)
        
        # Parse OSPF from config
        ospf_match = re.search(r'ospf\s+(\d+)\s+router-id\s+(\S+)', content, re.IGNORECASE)
        if ospf_match:
            routing["ospf"]["process_id"] = ospf_match.group(1)
            routing["ospf"]["router_id"] = ospf_match.group(2)
        else:
            ospf_match = re.search(r'ospf\s+(\d+)', content, re.IGNORECASE)
            if ospf_match:
                routing["ospf"]["process_id"] = ospf_match.group(1)
        
        # Parse OSPF from display commands
        ospf_peer_match = re.search(r'display\s+ospf\s+peer.*?OSPF\s+Process\s+(\d+)\s+with\s+Router\s+ID\s+(\S+)(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if ospf_peer_match:
            routing["ospf"]["process_id"] = ospf_peer_match.group(1)
            routing["ospf"]["router_id"] = ospf_peer_match.group(2)
            peer_details = ospf_peer_match.group(3)
            
            # Parse OSPF neighbors
            neighbor_pattern = r'Area\s+(\S+)\s+interface\s+(\S+)\((\S+)\)\'s\s+neighbors.*?Router\s+ID:\s+(\S+).*?Address:\s+(\S+).*?State:\s+(\S+).*?DR:\s+(\S+)\s+BDR:\s+(\S+)'
            for neighbor_match in re.finditer(neighbor_pattern, peer_details, re.IGNORECASE | re.DOTALL):
                routing["ospf"]["neighbors"].append({
                    "area": neighbor_match.group(1),
                    "interface": neighbor_match.group(3),
                    "router_id": neighbor_match.group(4),
                    "address": neighbor_match.group(5),
                    "state": neighbor_match.group(6).upper(),
                    "dr": neighbor_match.group(7),
                    "bdr": neighbor_match.group(8),
                })
                if neighbor_match.group(1) not in routing["ospf"]["areas"]:
                    routing["ospf"]["areas"].append(neighbor_match.group(1))
        
        # Parse OSPF interfaces
        ospf_interface_match = re.search(r'display\s+ospf\s+interface.*?Area:\s+(\S+).*?IP\s+Address\s+Type.*?\n(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if ospf_interface_match:
            area = ospf_interface_match.group(1)
            interface_lines = ospf_interface_match.group(2).strip().split('\n')
            for line in interface_lines:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) >= 6:
                    routing["ospf"]["interfaces"].append({
                        "area": area,
                        "ip_address": parts[0],
                        "type": parts[1],
                        "state": parts[2],
                        "cost": parts[3],
                        "priority": parts[4],
                        "dr": parts[5],
                        "bdr": parts[6] if len(parts) > 6 else None,
                    })
        
        # Parse OSPF routing
        ospf_routing_match = re.search(r'display\s+ospf\s+routing.*?Routing\s+for\s+Network.*?Destination.*?\n(.*?)(?=Routing\s+for\s+ASEs|display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if ospf_routing_match:
            routing_lines = ospf_routing_match.group(1).strip().split('\n')
            for line in routing_lines:
                line = line.strip()
                if not line or 'Destination' in line:
                    continue
                parts = line.split()
                if len(parts) >= 5:
                    routing["ospf"]["routes"].append({
                        "destination": parts[0],
                        "cost": parts[1],
                        "type": parts[2],
                        "next_hop": parts[3],
                        "adv_router": parts[4],
                        "area": parts[5] if len(parts) > 5 else None,
                    })
        
        # Parse BGP from config
        bgp_match = re.search(r'bgp\s+(\d+).*?router-id\s+(\S+)', content, re.IGNORECASE | re.DOTALL)
        if bgp_match:
            routing["bgp"]["local_as"] = bgp_match.group(1)
            routing["bgp"]["router_id"] = bgp_match.group(2)
        else:
            bgp_match = re.search(r'bgp\s+(\d+)', content, re.IGNORECASE)
            if bgp_match:
                routing["bgp"]["local_as"] = bgp_match.group(1)
        
        # Parse BGP peers from config
        bgp_peer_pattern = r'peer\s+(\S+)\s+as-number\s+(\d+)'
        for match in re.finditer(bgp_peer_pattern, content, re.IGNORECASE):
            routing["bgp"]["peers"].append({
                "peer": match.group(1),
                "remote_as": match.group(2),
            })
        
        # Parse EIGRP from config (if present)
        eigrp_match = re.search(r'eigrp\s+(\d+)', content, re.IGNORECASE)
        if eigrp_match:
            routing["eigrp"]["as_number"] = eigrp_match.group(1)
            
            # Parse router-id
            router_id_match = re.search(r'eigrp\s+\d+.*?router-id\s+(\S+)', content, re.IGNORECASE | re.DOTALL)
            if router_id_match:
                routing["eigrp"]["router_id"] = router_id_match.group(1)
            
            # Parse EIGRP neighbors from display commands
            eigrp_neighbor_match = re.search(r'display\s+eigrp\s+neighbor.*?(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
            if eigrp_neighbor_match:
                neighbor_details = eigrp_neighbor_match.group(1)
                # Parse neighbor entries
                neighbor_pattern = r'(\d+\.\d+\.\d+\.\d+)\s+(\S+)\s+(\d+)\s+(\d+)'
                for neighbor_match in re.finditer(neighbor_pattern, neighbor_details, re.IGNORECASE):
                    routing["eigrp"]["neighbors"].append({
                        "neighbor": neighbor_match.group(1),
                        "interface": neighbor_match.group(2),
                        "hold_time": int(neighbor_match.group(3)),
                        "uptime": int(neighbor_match.group(4)),
                    })
                    if not routing["eigrp"]["hold_time"]:
                        routing["eigrp"]["hold_time"] = int(neighbor_match.group(3))
        
        # Parse RIP from config
        rip_match = re.search(r'rip\s+(\d+)', content, re.IGNORECASE)
        if rip_match:
            routing["rip"]["version"] = None  # Will be extracted from config
            version_match = re.search(r'rip\s+\d+.*?version\s+(\d+)', content, re.IGNORECASE | re.DOTALL)
            if version_match:
                routing["rip"]["version"] = version_match.group(1)
            
            # Parse RIP networks
            network_pattern = r'network\s+(\S+)'
            for match in re.finditer(network_pattern, content, re.IGNORECASE):
                # Only add if it's within RIP context (simplified)
                if match.group(1) not in routing["rip"]["networks"]:
                    routing["rip"]["networks"].append(match.group(1))
            
            # Parse auto-summary
            auto_summary_match = re.search(r'rip\s+\d+.*?auto-summary', content, re.IGNORECASE | re.DOTALL)
            if auto_summary_match:
                routing["rip"]["auto_summary"] = True
            
            # Parse passive interfaces
            passive_match = re.search(r'rip\s+\d+.*?silent-interface\s+(\S+)', content, re.IGNORECASE | re.DOTALL)
            if passive_match:
                routing["rip"]["passive_interfaces"].append(passive_match.group(1))
            
            # Parse timers
            timer_match = re.search(r'rip\s+\d+.*?timers\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)', content, re.IGNORECASE | re.DOTALL)
            if timer_match:
                routing["rip"]["timers"]["update"] = int(timer_match.group(1))
                routing["rip"]["timers"]["invalid"] = int(timer_match.group(2))
                routing["rip"]["timers"]["holddown"] = int(timer_match.group(3))
                routing["rip"]["timers"]["flush"] = int(timer_match.group(4))
            
            # Parse admin distance
            admin_dist_match = re.search(r'rip\s+\d+.*?preference\s+(\d+)', content, re.IGNORECASE | re.DOTALL)
            if admin_dist_match:
                routing["rip"]["admin_distance"] = int(admin_dist_match.group(1))
        
        # Parse RIP database for hop counts
        rip_db_match = re.search(r'display\s+rip\s+database.*?(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if rip_db_match:
            db_lines = rip_db_match.group(1).strip().split('\n')
            for line in db_lines:
                line = line.strip()
                if not line or '---' in line:
                    continue
                parts = line.split()
                if len(parts) >= 3:
                    network = parts[0]
                    hop_count = parts[1] if parts[1].isdigit() else None
                    if hop_count:
                        routing["rip"]["hop_count"][network] = int(hop_count)
        
        return routing
    
    def extract_neighbors(self, content: str) -> List[Dict[str, Any]]:
        """Extract neighbor discovery information"""
        neighbors = []
        neighbor_dict = {}  # Use dict to merge brief and detailed info, prevent duplicates
        
        # Parse display lldp neighbor brief first (simpler format)
        # Pattern: "display lldp neighbor brief" followed by header line, then data lines
        # Format example:
        # display lldp neighbor brief
        # Local Intf   Neighbor Dev             Neighbor Intf             Exptime
        # Eth0/0/1     DIST1                    GE0/0/6                   94
        # Match pattern: "display lldp neighbor brief" followed by header line, then data line(s)
        # Example:
        # <ACC1>display lldp neighbor brief
        # Local Intf   Neighbor Dev             Neighbor Intf             Exptime
        # Eth0/0/1     DIST1                    GE0/0/6                   94
        # Note: May have prompt like <ACC1> before command
        lldp_brief_match = re.search(r'(?:<[^>]+>)?\s*display\s+lldp\s+neighbor\s+brief.*?\n.*?Local\s+Intf.*?Neighbor\s+Dev.*?Neighbor\s+Intf.*?Exptime.*?\n([^\n<]*?)(?=\n<|display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if lldp_brief_match:
            brief_lines = lldp_brief_match.group(1).strip().split('\n')
            # Header keywords to skip
            header_keywords = ['local intf', 'neighbor dev', 'neighbor intf', 'exptime', 'device', 'router', 'switch', 'wlan', 'other', 'id', 'port']
            for line in brief_lines:
                line = line.strip()
                if not line:
                    continue
                # Skip header lines
                if any(keyword in line.lower() for keyword in header_keywords):
                    continue
                # Skip separator lines
                if '---' in line or '===' in line:
                    continue
                
                # Format: "Eth0/0/1     DIST1                    GE0/0/6                   94"
                # Split by whitespace, but handle multiple spaces
                parts = [p for p in line.split() if p]
                if len(parts) >= 3:
                    local_port = parts[0]
                    device_name = parts[1]
                    remote_port = parts[2]
                    expire_time = parts[3] if len(parts) > 3 else None
                    
                    # Validate data - skip if looks like header
                    invalid_names = ['device', 'router', 'switch', 'wlan', 'other', 'id', 'port', 'local', 'remote', 'neighbor', 'intf', 'dev', 'exptime']
                    if device_name.lower() in invalid_names or len(device_name) <= 1:
                        continue
                    # Local port should contain interface type (Eth, GE, Gi, etc.)
                    if not re.search(r'(Eth|GE|Gi|Fa|Te|Se|Lo|Vl|Po|Tu)', local_port, re.IGNORECASE):
                        continue
                    
                    neighbor_key = f"{local_port}_{device_name}"
                    neighbor_dict[neighbor_key] = {
                        "device_name": device_name,
                        "local_port": local_port,
                        "remote_port": remote_port,
                        "expire_time": expire_time,
                        "platform": None,
                        "ip_address": None,
                        "capabilities": None,
                        "protocol": "LLDP",
                    }
        
        # Parse detailed display lldp neighbor output
        # Pattern: "Ethernet0/0/1 has 1 neighbors:" or "GigabitEthernet0/0/1 has 1 neighbors:" followed by details
        lldp_detailed_pattern = r'(\S+)\s+has\s+(\d+)\s+neighbors:(.*?)(?=\n\S+\s+has\s+\d+\s+neighbors:|<|display|#|$)'
        for lldp_match in re.finditer(lldp_detailed_pattern, content, re.IGNORECASE | re.DOTALL):
            local_port = lldp_match.group(1)
            neighbor_count = int(lldp_match.group(2)) if lldp_match.group(2).isdigit() else 0
            neighbor_details = lldp_match.group(3)
            
            if neighbor_count == 0:
                continue
            
            # Extract System name
            system_name_match = re.search(r'System\s+name\s*:\s*(\S+)', neighbor_details, re.IGNORECASE)
            device_name = system_name_match.group(1) if system_name_match else None
            
            if not device_name:
                continue
            
            # Extract Port ID (remote port)
            port_id_match = re.search(r'Port\s+ID\s*:\s*(\S+)', neighbor_details, re.IGNORECASE)
            remote_port = port_id_match.group(1) if port_id_match else None
            
            # Extract Chassis ID
            chassis_id_match = re.search(r'Chassis\s+ID\s*:\s*([\da-fA-F-]+)', neighbor_details, re.IGNORECASE)
            chassis_id = chassis_id_match.group(1) if chassis_id_match else None
            
            # Extract platform/description
            platform = None
            desc_match = re.search(r'System\s+description\s*:\s*(.+?)(?:\n(?:Huawei|VRP|Copyright)|$)', neighbor_details, re.IGNORECASE | re.DOTALL)
            if desc_match:
                platform = desc_match.group(1).strip()
                # Clean up platform string
                if platform:
                    platform = ' '.join(platform.split()[:2])  # Take first 2 words (e.g., "S5700-28C-HI")
            
            # Extract IP address (Management address)
            ip_address = None
            # Try IPv4 address first
            ip_match = re.search(r'Management\s+address\s*:\s*(\d+\.\d+\.\d+\.\d+)', neighbor_details, re.IGNORECASE)
            if ip_match:
                ip_address = ip_match.group(1)
            else:
                # Try alternative patterns
                ip_match = re.search(r'IP\s+address\s*:\s*(\d+\.\d+\.\d+\.\d+)', neighbor_details, re.IGNORECASE)
                if ip_match:
                    ip_address = ip_match.group(1)
            
            # Extract capabilities
            capabilities = []
            caps_supported_match = re.search(r'System\s+capabilities\s+supported\s*:\s*(.+?)(?:\n|$)', neighbor_details, re.IGNORECASE)
            if caps_supported_match:
                caps_str = caps_supported_match.group(1).strip()
                capabilities = [c.strip() for c in caps_str.split() if c.strip()]
            
            # Extract expire time
            expire_time_match = re.search(r'Expired\s+time\s*:\s*(\d+)s', neighbor_details, re.IGNORECASE)
            expire_time = expire_time_match.group(1) if expire_time_match else None
            
            # Merge with brief data or create new entry
            neighbor_key = f"{local_port}_{device_name}"
            if neighbor_key in neighbor_dict:
                # Update existing entry with detailed info
                neighbor_dict[neighbor_key].update({
                    "remote_port": remote_port or neighbor_dict[neighbor_key].get("remote_port"),
                    "platform": platform or neighbor_dict[neighbor_key].get("platform"),
                    "ip_address": ip_address or neighbor_dict[neighbor_key].get("ip_address"),
                    "capabilities": capabilities if capabilities else neighbor_dict[neighbor_key].get("capabilities"),
                    "expire_time": expire_time or neighbor_dict[neighbor_key].get("expire_time"),
                    "chassis_id": chassis_id,
                })
            else:
                # Create new entry from detailed output
                neighbor_dict[neighbor_key] = {
                    "device_name": device_name,
                    "local_port": local_port,
                    "remote_port": remote_port,
                    "expire_time": expire_time,
                    "platform": platform,
                    "ip_address": ip_address,
                    "capabilities": capabilities,
                    "chassis_id": chassis_id,
                    "protocol": "LLDP",
                }
        
        # Convert dict to list and filter out invalid entries
        neighbors = []
        invalid_names = ['device', 'router', 'switch', 'wlan', 'other', 'id', 'port', 'local', 'remote', 'neighbor', 'intf', 'dev', 'exptime', '(r)', '(w)', '(o)']
        for neighbor in neighbor_dict.values():
            device_name = neighbor.get("device_name", "")
            local_port = neighbor.get("local_port", "")
            
            # Skip if device_name is invalid
            if device_name.lower() in invalid_names or len(device_name) <= 1:
                continue
            
            # Skip if local_port doesn't look like an interface
            if not re.search(r'(Eth|GE|Gi|Fa|Te|Se|Lo|Vl|Po|Tu|Ethernet|Gigabit)', local_port, re.IGNORECASE):
                continue
            
            neighbors.append(neighbor)
        
        # Fallback: Parse line-by-line if no neighbors found yet
        if len(neighbors) == 0:
            # Try to parse from display lldp neighbor (detailed) line by line
            lldp_sections = re.finditer(r'(\S+)\s+has\s+(\d+)\s+neighbors:(.*?)(?=\n\S+\s+has\s+\d+\s+neighbors:|<|display|#|$)', content, re.IGNORECASE | re.DOTALL)
            for section_match in lldp_sections:
                local_port = section_match.group(1)
                neighbor_count = int(section_match.group(2)) if section_match.group(2).isdigit() else 0
                section_content = section_match.group(3)
                
                if neighbor_count == 0:
                    continue
                
                # Extract from section content
                system_name_match = re.search(r'System\s+name\s*:\s*(\S+)', section_content, re.IGNORECASE)
                port_id_match = re.search(r'Port\s+ID\s*:\s*(\S+)', section_content, re.IGNORECASE)
                desc_match = re.search(r'System\s+description\s*:\s*(.+?)(?:\n(?:Huawei|VRP|Copyright)|$)', section_content, re.IGNORECASE | re.DOTALL)
                
                if system_name_match:
                    device_name = system_name_match.group(1)
                    remote_port = port_id_match.group(1) if port_id_match else None
                    platform = desc_match.group(1).strip() if desc_match else None
                    if platform:
                        platform = ' '.join(platform.split()[:2])  # Take first 2 words
                    
                    # Validate data before adding
                    invalid_names = ['device', 'router', 'switch', 'wlan', 'other', 'id', 'port', 'local', 'remote', 'neighbor', 'intf', 'dev']
                    if device_name.lower() not in invalid_names and len(device_name) > 1:
                        if re.search(r'(Eth|GE|Gi|Fa|Te|Se|Lo|Vl|Po|Tu|Ethernet|Gigabit)', local_port, re.IGNORECASE):
                            neighbor_key = f"{local_port}_{device_name}"
                            if neighbor_key not in neighbor_dict:
                                neighbor_dict[neighbor_key] = {
                                    "device_name": device_name,
                                    "local_port": local_port,
                                    "remote_port": remote_port,
                                    "platform": platform,
                                    "ip_address": None,
                                    "capabilities": None,
                                    "protocol": "LLDP",
                                }
            
            # Filter neighbors again before returning
            filtered_neighbors = []
            invalid_names = ['device', 'router', 'switch', 'wlan', 'other', 'id', 'port', 'local', 'remote', 'neighbor', 'intf', 'dev', 'exptime', '(r)', '(w)', '(o)']
            for neighbor in neighbor_dict.values():
                device_name = neighbor.get("device_name", "")
                local_port = neighbor.get("local_port", "")
                if device_name.lower() not in invalid_names and len(device_name) > 1:
                    if re.search(r'(Eth|GE|Gi|Fa|Te|Se|Lo|Vl|Po|Tu|Ethernet|Gigabit)', local_port, re.IGNORECASE):
                        filtered_neighbors.append(neighbor)
            neighbors = filtered_neighbors
        
        return neighbors
    
    def extract_mac_arp(self, content: str) -> Dict[str, Any]:
        """Extract MAC address table and ARP table"""
        mac_arp = {
            "mac_table": [],
            "arp_table": [],
        }
        
        # MAC address table - parse display mac-address output
        mac_match = re.search(r'display\s+mac-address.*?MAC\s+Address\s+VLAN.*?\n.*?---.*?\n(.*?)(?=Total|display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if mac_match:
            mac_lines = mac_match.group(1).strip().split('\n')
            for line in mac_lines:
                line = line.strip()
                if not line or '---' in line or 'MAC Address' in line:
                    continue
                
                parts = line.split()
                if len(parts) >= 4:
                    mac_arp["mac_table"].append({
                        "mac_address": parts[0],
                        "vlan": parts[1],
                        "pevlan": parts[2] if parts[2] != '-' else None,
                        "cevlan": parts[3] if len(parts) > 3 and parts[3] != '-' else None,
                        "port": parts[4] if len(parts) > 4 else None,
                        "type": parts[5].upper() if len(parts) > 5 else "DYNAMIC",
                    })
        
        # ARP table - parse display arp output
        arp_match = re.search(r'display\s+arp.*?IP\s+ADDRESS\s+MAC\s+ADDRESS.*?\n.*?---.*?\n(.*?)(?=Total|display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if arp_match:
            arp_lines = arp_match.group(1).strip().split('\n')
            for line in arp_lines:
                line = line.strip()
                if not line or '---' in line or 'IP ADDRESS' in line:
                    continue
                
                parts = line.split()
                if len(parts) >= 2:
                    # Format: IP_ADDRESS MAC_ADDRESS EXPIRE(M) TYPE INTERFACE VLAN
                    mac_arp["arp_table"].append({
                        "ip_address": parts[0],
                        "mac_address": parts[1],
                        "expire": parts[2] if len(parts) > 2 else None,
                        "type": parts[3] if len(parts) > 3 else None,
                        "interface": parts[4] if len(parts) > 4 else None,
                        "vlan": parts[5] if len(parts) > 5 else None,
                    })
        
        return mac_arp
    
    def extract_security(self, content: str) -> Dict[str, Any]:
        """Extract security and management information"""
        security = {
            "users": [],
            "aaa": {},
            "ssh": {
                "version": None,
                "enabled": False,
                "connection_timeout": None,
                "auth_retries": None,
                "stelnet_enabled": False,
                "sftp_enabled": False,
                "scp_enabled": False,
            },
            "snmp": {
                "enabled": False,
                "communities": [],
                "version": None,
            },
            "ntp": {
                "enabled": False,
                "servers": [],
                "status": None,
                "stratum": None,
                "synchronized": False,
            },
            "logging": {
                "enabled": False,
                "log_hosts": [],
                "console": {},
                "monitor": {},
                "log_buffer": {},
                "trap_buffer": {},
            },
            "acls": {
                "total_count": 0,
            },
        }
        
        # Parse display local-user
        local_user_match = re.search(r'display\s+local-user.*?User-name\s+State\s+AuthMask\s+AdminLevel.*?\n.*?---.*?\n(.*?)(?=Total|display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if local_user_match:
            user_lines = local_user_match.group(1).strip().split('\n')
            for line in user_lines:
                line = line.strip()
                if not line or '---' in line:
                    continue
                parts = line.split()
                if len(parts) >= 4:
                    security["users"].append({
                        "username": parts[0],
                        "state": parts[1],
                        "auth_mask": parts[2],
                        "admin_level": int(parts[3]) if parts[3].isdigit() else None,
                    })
        
        # Parse users from config if not found in display
        if not security["users"]:
            user_pattern = r'local-user\s+(\S+)\s+.*?privilege\s+level\s+(\d+)'
            for match in re.finditer(user_pattern, content, re.IGNORECASE | re.DOTALL):
                security["users"].append({
                    "username": match.group(1),
                    "privilege": int(match.group(2)) if match.group(2) else 1,
                    "state": "A",
                    "auth_mask": "S",
                })
        
        # Parse display ssh server status
        ssh_status_match = re.search(r'display\s+ssh\s+server\s+status.*?SSH\s+version\s*:\s*(\S+).*?SSH\s+connection\s+timeout\s*:\s*(\d+).*?SSH\s+authentication\s+retries\s*:\s*(\d+).*?Stelnet\s+server\s*:\s*(\S+).*?SFTP\s+server\s*:\s*(\S+).*?Scp\s+server\s*:\s*(\S+)', content, re.IGNORECASE | re.DOTALL)
        if ssh_status_match:
            security["ssh"]["version"] = ssh_status_match.group(1)
            security["ssh"]["connection_timeout"] = int(ssh_status_match.group(2))
            security["ssh"]["auth_retries"] = int(ssh_status_match.group(3))
            security["ssh"]["stelnet_enabled"] = ssh_status_match.group(4).upper() == "ENABLE"
            security["ssh"]["sftp_enabled"] = ssh_status_match.group(5).upper() == "ENABLE"
            security["ssh"]["scp_enabled"] = ssh_status_match.group(6).upper() == "ENABLE"
            security["ssh"]["enabled"] = security["ssh"]["stelnet_enabled"] or security["ssh"]["sftp_enabled"] or security["ssh"]["scp_enabled"]
        else:
            # Fallback to config
            if "stelnet server enable" in content.lower() or "ssh server enable" in content.lower():
                security["ssh"]["enabled"] = True
                security["ssh"]["stelnet_enabled"] = True
        
        # Parse display snmp-agent community
        snmp_community_match = re.search(r'display\s+snmp-agent\s+community.*?Community\s+name:(\S+).*?Group\s+name:(\S+).*?Storage-type:\s*(\S+)', content, re.IGNORECASE | re.DOTALL)
        if snmp_community_match:
            security["snmp"]["enabled"] = True
            security["snmp"]["communities"].append({
                "name": snmp_community_match.group(1).strip(),
                "group": snmp_community_match.group(2).strip(),
                "storage_type": snmp_community_match.group(3).strip(),
            })
        else:
            # Parse from config
            if "snmp-agent" in content.lower():
                security["snmp"]["enabled"] = True
                snmp_community_pattern = r'snmp-agent\s+community\s+(read|write)\s+(\S+)'
                for match in re.finditer(snmp_community_pattern, content, re.IGNORECASE):
                    security["snmp"]["communities"].append({
                        "name": match.group(2),
                        "access": match.group(1).upper(),
                    })
            
            # Extract SNMP version
            snmp_version_match = re.search(r'snmp-agent\s+sys-info\s+version\s+(\S+)', content, re.IGNORECASE)
            if snmp_version_match:
                security["snmp"]["version"] = snmp_version_match.group(1)
        
        # Parse display ntp-service status
        ntp_status_match = re.search(r'display\s+ntp-service\s+status.*?clock\s+status:\s*(\S+).*?clock\s+stratum:\s*(\d+)', content, re.IGNORECASE | re.DOTALL)
        if ntp_status_match:
            security["ntp"]["enabled"] = True
            security["ntp"]["status"] = ntp_status_match.group(1)
            security["ntp"]["stratum"] = int(ntp_status_match.group(2))
            security["ntp"]["synchronized"] = ntp_status_match.group(1).lower() == "synchronized"
        else:
            # Fallback to config
            if "ntp-service" in content.lower():
                security["ntp"]["enabled"] = True
                ntp_server_pattern = r'ntp-service\s+unicast-server\s+(\S+)'
                for match in re.finditer(ntp_server_pattern, content, re.IGNORECASE):
                    security["ntp"]["servers"].append(match.group(1))
        
        # Parse display info-center
        info_center_match = re.search(r'display\s+info-center.*?Information\s+Center:(\S+).*?Log\s+host:.*?(\d+\.\d+\.\d+\.\d+)', content, re.IGNORECASE | re.DOTALL)
        if info_center_match:
            security["logging"]["enabled"] = info_center_match.group(1).lower() == "enabled"
            security["logging"]["log_hosts"].append(info_center_match.group(2))
            
            # Parse log buffer
            log_buffer_match = re.search(r'Log\s+buffer:.*?enabled.*?max\s+buffer\s+size\s+(\d+).*?current\s+buffer\s+size\s+(\d+)', content, re.IGNORECASE | re.DOTALL)
            if log_buffer_match:
                security["logging"]["log_buffer"] = {
                    "enabled": True,
                    "max_size": int(log_buffer_match.group(1)),
                    "current_size": int(log_buffer_match.group(2)),
                }
            
            # Parse trap buffer
            trap_buffer_match = re.search(r'Trap\s+buffer:.*?enabled.*?max\s+buffer\s+size\s+(\d+).*?current\s+buffer\s+size\s+(\d+)', content, re.IGNORECASE | re.DOTALL)
            if trap_buffer_match:
                security["logging"]["trap_buffer"] = {
                    "enabled": True,
                    "max_size": int(trap_buffer_match.group(1)),
                    "current_size": int(trap_buffer_match.group(2)),
                }
        else:
            # Fallback to config
            if "info-center loghost" in content.lower():
                security["logging"]["enabled"] = True
                loghost_pattern = r'info-center\s+loghost\s+(\d+\.\d+\.\d+\.\d+)'
                for match in re.finditer(loghost_pattern, content, re.IGNORECASE):
                    security["logging"]["log_hosts"].append(match.group(1))
        
        # Parse display acl all
        acl_match = re.search(r'display\s+acl\s+all.*?Total\s+nonempty\s+ACL\s+number\s+is\s+(\d+)', content, re.IGNORECASE | re.DOTALL)
        if acl_match:
            security["acls"]["total_count"] = int(acl_match.group(1))
        
        return security
    
    def extract_ha(self, content: str) -> Dict[str, Any]:
        """Extract High Availability information"""
        ha = {
            "port_channels": [],
            "etherchannel": [],
            "hsrp": {
                "groups": [],
            },
            "vrrp": {
                "groups": [],
            },
        }
        
        # Parse display eth-trunk or Eth-Trunk from display interface
        # First try display eth-trunk
        eth_trunk_match = re.search(r'display\s+eth-trunk.*?Eth-Trunk(\d+).*?Working\s+Mode.*?(\S+).*?Number\s+of\s+Ports\s+in\s+Trunk\s*:\s*(\d+)', content, re.IGNORECASE | re.DOTALL)
        if not eth_trunk_match:
            # Try parsing from display interface output
            eth_trunk_pattern = r'(Eth-Trunk\d+)\s+current\s+state\s*:\s*(\S+).*?The\s+Number\s+of\s+Ports\s+in\s+Trunk\s*:\s*(\d+).*?The\s+Number\s+of\s+UP\s+Ports\s+in\s+Trunk\s*:\s*(\d+).*?PortName\s+Status.*?\n(.*?)(?=\n\S+\s+current\s+state|display|#|$)'
            for match in re.finditer(eth_trunk_pattern, content, re.IGNORECASE | re.DOTALL):
                trunk_name = match.group(1)
                trunk_id = re.search(r'Eth-Trunk(\d+)', trunk_name).group(1) if re.search(r'Eth-Trunk(\d+)', trunk_name) else None
                trunk_status = match.group(2).upper()
                total_ports = int(match.group(3))
                up_ports = int(match.group(4))
                member_section = match.group(5)
                
                members = []
                member_lines = member_section.strip().split('\n')
                for line in member_lines:
                    line = line.strip()
                    if not line or '---' in line or 'PortName' in line:
                        continue
                    parts = line.split()
                    if len(parts) >= 2:
                        members.append({
                            "port": parts[0],
                            "status": parts[1].upper(),
                            "weight": int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None,
                        })
                
                # Get mode from config
                mode = None
                trunk_config_match = re.search(r'interface\s+Eth-Trunk\s*' + trunk_id + r'.*?mode\s+(\S+)', content, re.IGNORECASE | re.DOTALL)
                if trunk_config_match:
                    mode_str = trunk_config_match.group(1).lower()
                    if "lacp" in mode_str:
                        mode = "LACP"
                    elif "manual" in mode_str:
                        mode = "STATIC"
                
                ha["port_channels"].append({
                    "id": trunk_id,
                    "name": trunk_name,
                    "mode": mode,
                    "members": [m["port"] for m in members],
                    "member_details": members,
                    "status": trunk_status.lower(),
                    "total_ports": total_ports,
                    "up_ports": up_ports,
                })
                ha["etherchannel"].append({
                    "id": trunk_id,
                    "name": trunk_name,
                    "mode": mode,
                    "members": [m["port"] for m in members],
                    "status": trunk_status.lower(),
                })
        
        # Parse Eth-Trunk from config if not found in display
        if not ha["port_channels"]:
            trunk_pattern = r'interface\s+Eth-Trunk\s*(\d+)\s*\n(.*?)(?=\ninterface\s+|#|$)'
            for match in re.finditer(trunk_pattern, content, re.IGNORECASE | re.DOTALL):
                trunk_id = match.group(1)
                trunk_config = match.group(2)
                
                members = []
                mode = None
                
                # Find member interfaces
                if "mode lacp" in trunk_config.lower():
                    mode = "LACP"
                elif "mode manual" in trunk_config.lower():
                    mode = "STATIC"
                
                # Find members
                for iface_match in re.finditer(r'interface\s+(\S+)\s*\n(.*?)(?=\ninterface\s+|#|$)', content, re.IGNORECASE | re.DOTALL):
                    iface_config = iface_match.group(2)
                    if f"eth-trunk {trunk_id}" in iface_config.lower():
                        members.append(iface_match.group(1))
                
                ha["port_channels"].append({
                    "id": trunk_id,
                    "mode": mode,
                    "members": members,
                    "status": "up" if members else "down",
                })
                ha["etherchannel"].append({
                    "id": trunk_id,
                    "mode": mode,
                    "members": members,
                    "status": "up" if members else "down",
                })
        
        # Parse display vrrp - parse all VRRP groups
        vrrp_display_match = re.search(r'display\s+vrrp(.*?)(?=display|#|$)', content, re.IGNORECASE | re.DOTALL)
        if vrrp_display_match and "No VRRP" not in vrrp_display_match.group(1):
            vrrp_output = vrrp_display_match.group(1)
            
            # Parse each VRRP group
            vrrp_group_pattern = r'(Vlanif\d+)\s+\|\s+Virtual\s+Router\s+(\d+).*?State\s*:\s*(\S+).*?Virtual\s+IP\s*:\s*(\d+\.\d+\.\d+\.\d+).*?Master\s+IP\s*:\s*(\d+\.\d+\.\d+\.\d+).*?PriorityRun\s*:\s*(\d+).*?PriorityConfig\s*:\s*(\d+).*?Preempt\s*:\s*(\S+)'
            for match in re.finditer(vrrp_group_pattern, vrrp_output, re.IGNORECASE | re.DOTALL):
                interface = match.group(1)
                vrid = match.group(2)
                state = match.group(3).upper()
                virtual_ip = match.group(4)
                master_ip = match.group(5)
                priority_run = int(match.group(6))
                priority_config = int(match.group(7))
                preempt = match.group(8).upper() == "YES"
                
                ha["vrrp"]["groups"].append({
                    "vrid": vrid,
                    "interface": interface,
                    "virtual_ip": virtual_ip,
                    "state": state,
                    "master_ip": master_ip,
                    "priority": priority_config,
                    "priority_run": priority_run,
                    "preempt": preempt,
                })
        else:
            # Parse VRRP from config
            vrrp_pattern = r'vrrp\s+vrid\s+(\d+)\s+virtual-ip\s+(\d+\.\d+\.\d+\.\d+)'
            for match in re.finditer(vrrp_pattern, content, re.IGNORECASE):
                vrid = match.group(1)
                virtual_ip = match.group(2)
                
                # Try to find interface and priority
                vrrp_context = content[max(0, match.start()-500):match.end()+500]
                interface_match = re.search(r'interface\s+(Vlanif\d+)', vrrp_context, re.IGNORECASE)
                interface = interface_match.group(1) if interface_match else None
                
                priority_match = re.search(r'vrrp\s+vrid\s+' + vrid + r'.*?priority\s+(\d+)', vrrp_context, re.IGNORECASE | re.DOTALL)
                priority = int(priority_match.group(1)) if priority_match else None
                
                ha["vrrp"]["groups"].append({
                    "vrid": vrid,
                    "interface": interface,
                    "virtual_ip": virtual_ip,
                    "priority": priority,
                })
        
        return ha

