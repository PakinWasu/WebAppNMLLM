"""Cisco IOS/IOS-XE/IOS-XR/NX-OS configuration parser"""

import re
from typing import Dict, List, Any, Optional
from .base import BaseParser


class CiscoParser(BaseParser):
    """Parser for Cisco device configurations"""
    
    def detect_vendor(self, content: str) -> bool:
        """Detect if this is a Cisco configuration"""
        cisco_indicators = [
            r'hostname\s+\S+',
            r'version\s+\d+',
            r'!.*Cisco',
            r'switchport\s+mode',
            r'spanning-tree',
            r'router\s+ospf',
            r'router\s+bgp',
            r'show\s+running-config',
            r'interface\s+(GigabitEthernet|FastEthernet|Ethernet|TenGigabitEthernet)',
        ]
        content_lower = content.lower()
        matches = sum(1 for pattern in cisco_indicators if re.search(pattern, content, re.IGNORECASE))
        return matches >= 2
    
    def parse(self, content: str, filename: str) -> Dict[str, Any]:
        """Parse complete Cisco configuration"""
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
        }
        
        # Extract hostname
        hostname_match = re.search(r'hostname\s+(\S+)', content, re.IGNORECASE)
        if hostname_match:
            overview["hostname"] = hostname_match.group(1)
        
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
        
        # Extract version
        version_match = re.search(r'version\s+([\d.]+)', content, re.IGNORECASE)
        if version_match:
            overview["os_version"] = version_match.group(1)
        
        # Extract from show version output
        show_version_match = re.search(r'show\s+version.*?(?=show|!|$)', content, re.IGNORECASE | re.DOTALL)
        if show_version_match:
            version_output = show_version_match.group(0)
            
            # Model/Platform
            model_match = re.search(r'(?:Model|cisco)\s+(\S+)', version_output, re.IGNORECASE)
            if model_match:
                overview["model"] = model_match.group(1)
            
            # Serial number
            serial_match = re.search(r'[Ss]erial\s+[Nn]umber[:\s]+(\S+)', version_output)
            if serial_match:
                overview["serial_number"] = serial_match.group(1)
            
            # Uptime
            uptime_match = re.search(r'uptime\s+is\s+(.+?)(?:\n|$)', version_output, re.IGNORECASE)
            if uptime_match:
                overview["uptime"] = uptime_match.group(1).strip()
        
        # Extract management IP (look for IP on management interface or loopback)
        mgmt_ip_match = re.search(r'interface\s+(?:[Vv]lan|Loopback|Management)\s*\d+.*?ip\s+address\s+(\d+\.\d+\.\d+\.\d+)', content, re.IGNORECASE | re.DOTALL)
        if mgmt_ip_match:
            overview["mgmt_ip"] = mgmt_ip_match.group(1)
        
        # CPU and Memory from show processes or show memory
        cpu_match = re.search(r'CPU\s+utilization.*?(\d+(?:\.\d+)?)\s*%', content, re.IGNORECASE)
        if cpu_match:
            try:
                overview["cpu_util"] = float(cpu_match.group(1))
            except:
                pass
        
        mem_match = re.search(r'[Mm]emory\s+utilization.*?(\d+(?:\.\d+)?)\s*%', content, re.IGNORECASE)
        if mem_match:
            try:
                overview["mem_util"] = float(mem_match.group(1))
            except:
                pass
        
        return overview
    
    def extract_interfaces(self, content: str) -> List[Dict[str, Any]]:
        """Extract interface information"""
        interface_dict = {}  # Use dict to merge config and show output, prevent duplicates
        
        # Parse interface blocks
        interface_pattern = r'interface\s+(\S+)\s*\n(.*?)(?=\ninterface\s+|$)'
        for match in re.finditer(interface_pattern, content, re.IGNORECASE | re.DOTALL):
            iface_name = match.group(1)
            iface_config = match.group(2)
            
            iface = {
                "name": iface_name,
                "type": self._get_interface_type(iface_name),
                "admin_status": "up" if "shutdown" not in iface_config.lower() else "down",
                "oper_status": "up",  # Default, will be updated from show output
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
            }
            
            # Extract description
            desc_match = re.search(r'description\s+(.+?)(?:\n|$)', iface_config, re.IGNORECASE)
            if desc_match:
                iface["description"] = desc_match.group(1).strip()
            
            # Extract IPv4 address
            ip_match = re.search(r'ip\s+address\s+(\d+\.\d+\.\d+\.\d+)', iface_config, re.IGNORECASE)
            if ip_match:
                iface["ipv4_address"] = ip_match.group(1)
            
            # Extract IPv6 address
            ipv6_match = re.search(r'ipv6\s+address\s+([\da-fA-F:]+/\d+)', iface_config, re.IGNORECASE)
            if ipv6_match:
                iface["ipv6_address"] = ipv6_match.group(1)
            
            # Extract port mode
            if "switchport mode access" in iface_config.lower():
                iface["port_mode"] = "access"
                vlan_match = re.search(r'switchport\s+access\s+vlan\s+(\d+)', iface_config, re.IGNORECASE)
                if vlan_match:
                    iface["access_vlan"] = vlan_match.group(1)
            elif "switchport mode trunk" in iface_config.lower():
                iface["port_mode"] = "trunk"
                native_match = re.search(r'switchport\s+trunk\s+native\s+vlan\s+(\d+)', iface_config, re.IGNORECASE)
                if native_match:
                    iface["native_vlan"] = native_match.group(1)
                allowed_match = re.search(r'switchport\s+trunk\s+allowed\s+vlan\s+(.+)', iface_config, re.IGNORECASE)
                if allowed_match:
                    iface["allowed_vlans"] = allowed_match.group(1).strip()
            elif "no switchport" in iface_config.lower() or iface["ipv4_address"]:
                iface["port_mode"] = "routed"
            
            interface_dict[iface_name] = iface
        
        # Update from show ip interface brief
        brief_match = re.search(r'show\s+ip\s+interface\s+brief.*?\n(.*?)(?=!|show|$)', content, re.IGNORECASE | re.DOTALL)
        if brief_match:
            brief_lines = brief_match.group(1).strip().split('\n')
            for line in brief_lines[1:]:  # Skip header
                parts = line.split()
                if len(parts) >= 4:
                    iface_name = parts[0]
                    ip_addr = parts[1] if parts[1] != "unassigned" else None
                    status = parts[3] if len(parts) > 3 else None
                    protocol = parts[4] if len(parts) > 4 else None
                    
                    if iface_name not in interface_dict:
                        interface_dict[iface_name] = {
                            "name": iface_name,
                            "type": self._get_interface_type(iface_name),
                            "admin_status": "up",
                            "oper_status": status.lower() if status else "up",
                            "line_protocol": protocol.lower() if protocol else "up",
                        }
                    
                    iface = interface_dict[iface_name]
                    if ip_addr:
                        iface["ipv4_address"] = ip_addr
                    if status:
                        iface["oper_status"] = status.lower()
                    if protocol:
                        iface["line_protocol"] = protocol.lower()
        
        # Parse show interface for speed, duplex, MTU, MAC
        # Try multiple patterns for show interface
        show_patterns = [
            r'(\S+)\s+is\s+(?:up|down|administratively down).*?Hardware\s+is\s+(.+?)(?=\n\S+\s+is\s+(?:up|down)|!|show|$)',
            r'interface\s+(\S+).*?Hardware\s+is\s+(.+?)(?=\ninterface\s+|!|show|$)',
        ]
        
        for pattern in show_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE | re.DOTALL):
                iface_name = match.group(1)
                iface_details = match.group(2) if len(match.groups()) > 1 else ""
                
                if iface_name not in interface_dict:
                    interface_dict[iface_name] = {
                        "name": iface_name,
                        "type": self._get_interface_type(iface_name),
                    }
                
                iface = interface_dict[iface_name]
                
                # Extract MAC address
                mac_match = re.search(r'address\s+is\s+([\da-fA-F.]+)', iface_details, re.IGNORECASE)
                if mac_match:
                    iface["mac_address"] = mac_match.group(1)
                
                # Extract Speed
                speed_match = re.search(r'BW\s+(\d+)\s*(?:Kbit|Mbit|Gbit)', iface_details, re.IGNORECASE)
                if speed_match:
                    speed_val = speed_match.group(1)
                    speed_unit = speed_match.group(0).upper()
                    if 'GBIT' in speed_unit:
                        iface["speed"] = f"{speed_val}Gbps"
                    elif 'MBIT' in speed_unit:
                        iface["speed"] = f"{speed_val}Mbps"
                    else:
                        iface["speed"] = f"{speed_val}Kbps"
                else:
                    # Try alternative pattern
                    speed_match = re.search(r'(\d+)\s*(?:Mbps|Gbps|Kbps)', iface_details, re.IGNORECASE)
                    if speed_match:
                        iface["speed"] = speed_match.group(0)
                
                # Extract Duplex
                duplex_match = re.search(r'(?:full|half)[-\s]*duplex', iface_details, re.IGNORECASE)
                if duplex_match:
                    iface["duplex"] = duplex_match.group(0).split()[0].lower()
                
                # Extract MTU
                mtu_match = re.search(r'MTU\s+(\d+)', iface_details, re.IGNORECASE)
                if mtu_match:
                    iface["mtu"] = int(mtu_match.group(1))
        
        # Convert dict to list
        interfaces = list(interface_dict.values())
        
        return interfaces
    
    def _get_interface_type(self, iface_name: str) -> str:
        """Determine interface type from name"""
        if "GigabitEthernet" in iface_name or "Gi" in iface_name:
            return "GigabitEthernet"
        elif "FastEthernet" in iface_name or "Fa" in iface_name:
            return "FastEthernet"
        elif "TenGigabitEthernet" in iface_name or "Te" in iface_name:
            return "TenGigabitEthernet"
        elif "Ethernet" in iface_name or "Eth" in iface_name:
            return "Ethernet"
        elif "Vlan" in iface_name or "VLAN" in iface_name:
            return "VLAN"
        elif "Loopback" in iface_name:
            return "Loopback"
        else:
            return "Unknown"
    
    def extract_vlans(self, content: str) -> Dict[str, Any]:
        """Extract VLAN information"""
        vlans = {
            "vlan_list": [],
            "vlan_names": {},
            "vlan_status": {},
            "access_ports": {},
            "trunk_ports": {},
            "native_vlan": None,
            "total_vlan_count": 0,
        }
        
        # Parse vlan blocks
        vlan_pattern = r'vlan\s+(\d+)\s*\n(.*?)(?=\nvlan\s+|$)'
        for match in re.finditer(vlan_pattern, content, re.IGNORECASE | re.DOTALL):
            vlan_id = match.group(1)
            vlan_config = match.group(2)
            
            if vlan_id not in vlans["vlan_list"]:
                vlans["vlan_list"].append(vlan_id)
            
            # Extract VLAN name
            name_match = re.search(r'name\s+(\S+)', vlan_config, re.IGNORECASE)
            if name_match:
                vlans["vlan_names"][vlan_id] = name_match.group(1)
            
            # Status (default active)
            vlans["vlan_status"][vlan_id] = "active"
        
        # Parse from show vlan brief
        vlan_brief_match = re.search(r'show\s+vlan\s+brief.*?\n(.*?)(?=!|show|$)', content, re.IGNORECASE | re.DOTALL)
        if vlan_brief_match:
            brief_lines = vlan_brief_match.group(1).strip().split('\n')
            for line in brief_lines[1:]:  # Skip header
                parts = line.split()
                if len(parts) >= 2:
                    vlan_id = parts[0]
                    vlan_name = parts[1] if len(parts) > 1 else None
                    status = parts[2] if len(parts) > 2 else "active"
                    ports = parts[3:] if len(parts) > 3 else []
                    
                    if vlan_id not in vlans["vlan_list"]:
                        vlans["vlan_list"].append(vlan_id)
                    if vlan_name:
                        vlans["vlan_names"][vlan_id] = vlan_name
                    vlans["vlan_status"][vlan_id] = status.lower()
                    
                    # Track ports
                    for port in ports:
                        if port not in vlans["access_ports"]:
                            vlans["access_ports"][port] = []
                        if vlan_id not in vlans["access_ports"][port]:
                            vlans["access_ports"][port].append(vlan_id)
        
        vlans["total_vlan_count"] = len(vlans["vlan_list"])
        
        return vlans
    
    def extract_stp(self, content: str) -> Dict[str, Any]:
        """Extract Spanning Tree Protocol information"""
        stp = {
            "mode": None,
            "root_bridge_id": None,
            "root_priority": None,
            "is_root_bridge": False,
            "port_roles": {},
            "port_states": {},
            "port_costs": {},
            "portfast_enabled": {},
            "bpdu_guard_enabled": {},
        }
        
        # Extract STP mode
        mode_match = re.search(r'spanning-tree\s+mode\s+(\S+)', content, re.IGNORECASE)
        if mode_match:
            stp["mode"] = mode_match.group(1).upper()
        
        # Parse from show spanning-tree
        stp_match = re.search(r'show\s+spanning-tree.*?\n(.*?)(?=!|show|$)', content, re.IGNORECASE | re.DOTALL)
        if stp_match:
            stp_output = stp_match.group(1)
            
            # Root bridge info
            root_match = re.search(r'Root\s+ID\s+.*?(\d+\.\d+\.\d+\.\d+)', stp_output, re.IGNORECASE)
            if root_match:
                stp["root_bridge_id"] = root_match.group(1)
            
            # Port information
            port_pattern = r'(\S+)\s+(\w+)\s+(\w+)\s+(\d+)\s+(\d+\.\d+)\s+(\w+)'
            for match in re.finditer(port_pattern, stp_output):
                iface = match.group(1)
                role = match.group(2)
                state = match.group(3)
                cost = match.group(4)
                
                stp["port_roles"][iface] = role
                stp["port_states"][iface] = state
                stp["port_costs"][iface] = cost
        
        # Extract portfast and bpduguard from config
        for iface_match in re.finditer(r'interface\s+(\S+)\s*\n(.*?)(?=\ninterface\s+|$)', content, re.IGNORECASE | re.DOTALL):
            iface = iface_match.group(1)
            iface_config = iface_match.group(2)
            
            if "spanning-tree portfast" in iface_config.lower():
                stp["portfast_enabled"][iface] = True
            if "spanning-tree bpduguard enable" in iface_config.lower():
                stp["bpdu_guard_enabled"][iface] = True
        
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
                "peers": [],
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
        }
        
        # Static routes
        static_pattern = r'ip\s+route\s+(\S+)\s+(\S+)(?:\s+(\S+))?'
        for match in re.finditer(static_pattern, content, re.IGNORECASE):
            network = match.group(1)
            next_hop = match.group(2)
            if network == "0.0.0.0" and next_hop:
                routing["static"]["default_route"] = next_hop
            routing["static"]["routes"].append({
                "network": network,
                "next_hop": next_hop,
                "interface": match.group(3) if match.group(3) else None,
            })
        
        # OSPF
        ospf_match = re.search(r'router\s+ospf\s+(\d+)', content, re.IGNORECASE)
        if ospf_match:
            routing["ospf"]["process_id"] = ospf_match.group(1)
            
            router_id_match = re.search(r'router-id\s+(\d+\.\d+\.\d+\.\d+)', content, re.IGNORECASE)
            if router_id_match:
                routing["ospf"]["router_id"] = router_id_match.group(1)
        
        # BGP
        bgp_match = re.search(r'router\s+bgp\s+(\d+)', content, re.IGNORECASE)
        if bgp_match:
            routing["bgp"]["local_as"] = bgp_match.group(1)
        
        # EIGRP
        eigrp_match = re.search(r'router\s+eigrp\s+(\d+)', content, re.IGNORECASE)
        if eigrp_match:
            routing["eigrp"]["as_number"] = eigrp_match.group(1)
            
            # Parse router-id
            router_id_match = re.search(r'eigrp\s+\d+.*?router-id\s+(\d+\.\d+\.\d+\.\d+)', content, re.IGNORECASE | re.DOTALL)
            if router_id_match:
                routing["eigrp"]["router_id"] = router_id_match.group(1)
            
            # Parse EIGRP neighbors from show commands
            eigrp_neighbor_match = re.search(r'show\s+eigrp\s+neighbors.*?\n(.*?)(?=!|show|$)', content, re.IGNORECASE | re.DOTALL)
            if eigrp_neighbor_match:
                neighbor_lines = eigrp_neighbor_match.group(1).strip().split('\n')
                for line in neighbor_lines[1:]:  # Skip header
                    parts = line.split()
                    if len(parts) >= 4:
                        routing["eigrp"]["neighbors"].append({
                            "neighbor": parts[0],
                            "interface": parts[1],
                            "hold_time": int(parts[2]) if parts[2].isdigit() else None,
                            "uptime": parts[3] if len(parts) > 3 else None,
                        })
                        if parts[2].isdigit() and not routing["eigrp"]["hold_time"]:
                            routing["eigrp"]["hold_time"] = int(parts[2])
        
        # RIP
        rip_match = re.search(r'router\s+rip', content, re.IGNORECASE)
        if rip_match:
            # Parse version
            version_match = re.search(r'version\s+(\d+)', content, re.IGNORECASE)
            if version_match:
                routing["rip"]["version"] = version_match.group(1)
            
            # Parse networks
            network_pattern = r'network\s+(\S+)'
            for match in re.finditer(network_pattern, content, re.IGNORECASE):
                if match.group(1) not in routing["rip"]["networks"]:
                    routing["rip"]["networks"].append(match.group(1))
            
            # Parse auto-summary
            auto_summary_match = re.search(r'auto-summary', content, re.IGNORECASE)
            if auto_summary_match:
                routing["rip"]["auto_summary"] = True
            
            # Parse passive interfaces
            passive_match = re.search(r'passive-interface\s+(\S+)', content, re.IGNORECASE)
            if passive_match:
                routing["rip"]["passive_interfaces"].append(passive_match.group(1))
            
            # Parse timers
            timer_match = re.search(r'timers\s+basic\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)', content, re.IGNORECASE)
            if timer_match:
                routing["rip"]["timers"]["update"] = int(timer_match.group(1))
                routing["rip"]["timers"]["invalid"] = int(timer_match.group(2))
                routing["rip"]["timers"]["holddown"] = int(timer_match.group(3))
                routing["rip"]["timers"]["flush"] = int(timer_match.group(4))
            
            # Parse admin distance
            admin_dist_match = re.search(r'distance\s+(\d+)', content, re.IGNORECASE)
            if admin_dist_match:
                routing["rip"]["admin_distance"] = int(admin_dist_match.group(1))
        
        # Parse RIP database for hop counts
        rip_db_match = re.search(r'show\s+ip\s+rip\s+database.*?\n(.*?)(?=!|show|$)', content, re.IGNORECASE | re.DOTALL)
        if rip_db_match:
            db_lines = rip_db_match.group(1).strip().split('\n')
            for line in db_lines:
                line = line.strip()
                if not line or '---' in line:
                    continue
                # Look for route entries with hop count
                hop_match = re.search(r'(\d+\.\d+\.\d+\.\d+/\d+).*?\[(\d+)\]', line, re.IGNORECASE)
                if hop_match:
                    network = hop_match.group(1)
                    hop_count = int(hop_match.group(2))
                    routing["rip"]["hop_count"][network] = hop_count
        
        return routing
    
    def extract_neighbors(self, content: str) -> List[Dict[str, Any]]:
        """Extract neighbor discovery information"""
        neighbors = []
        
        # CDP neighbors
        cdp_match = re.search(r'show\s+cdp\s+neighbors.*?\n(.*?)(?=!|show|$)', content, re.IGNORECASE | re.DOTALL)
        if cdp_match:
            cdp_lines = cdp_match.group(1).strip().split('\n')
            # Skip header lines - look for common header patterns
            header_keywords = ['device id', 'local intf', 'holdtme', 'capability', 'platform', 'port id', '---', 'device', 'router', 'switch', 'wlan', 'other']
            for line in cdp_lines:
                line = line.strip()
                if not line:
                    continue
                # Skip header lines
                if any(keyword in line.lower() for keyword in header_keywords):
                    continue
                # Skip separator lines
                if line.startswith('---') or line.startswith('==='):
                    continue
                parts = line.split()
                if len(parts) >= 4:
                    device_name = parts[0]
                    local_port = parts[1]
                    # Validate that device_name and local_port look like real values
                    # Device names shouldn't be single characters or common header words
                    invalid_names = ['device', 'router', 'switch', 'wlan', 'other', 'id', 'port', 'local', 'remote', 'neighbor', 'intf', 'dev']
                    if device_name.lower() in invalid_names or len(device_name) <= 1:
                        continue
                    # Local port should contain interface type (Gi, Fa, Eth, etc.)
                    if not re.search(r'(Gi|Fa|Eth|Te|Se|Lo|Vl|Po|Tu)', local_port, re.IGNORECASE):
                        continue
                    neighbors.append({
                        "device_name": device_name,
                        "local_port": local_port,
                        "remote_port": parts[-1],
                        "platform": parts[-2] if len(parts) > 4 else None,
                        "ip_address": None,  # CDP may not have IP in brief output
                        "protocol": "CDP",
                    })
        
        # Parse detailed CDP output for IP addresses
        cdp_detail_match = re.search(r'show\s+cdp\s+neighbors\s+detail.*?(.*?)(?=!|show|$)', content, re.IGNORECASE | re.DOTALL)
        if cdp_detail_match:
            detail_output = cdp_detail_match.group(1)
            # Look for IP addresses in CDP detail
            device_sections = detail_output.split('Device ID:')
            for section in device_sections[1:]:  # Skip first empty section
                ip_match = re.search(r'IP\s+address:\s+(\d+\.\d+\.\d+\.\d+)', section, re.IGNORECASE)
                device_match = re.search(r'Device\s+ID:\s+(\S+)', section, re.IGNORECASE)
                interface_match = re.search(r'Interface:\s+(\S+)', section, re.IGNORECASE)
                
                if ip_match and device_match and interface_match:
                    device_name = device_match.group(1)
                    local_port = interface_match.group(1)
                    ip_address = ip_match.group(1)
                    
                    # Update existing neighbor or create new
                    existing = next((n for n in neighbors if n.get("device_name") == device_name and n.get("local_port") == local_port), None)
                    if existing:
                        existing["ip_address"] = ip_address
                    else:
                        neighbors.append({
                            "device_name": device_name,
                            "local_port": local_port,
                            "remote_port": "N/A",
                            "platform": None,
                            "ip_address": ip_address,
                            "protocol": "CDP",
                        })
        
        # LLDP neighbors
        lldp_match = re.search(r'show\s+lldp\s+neighbors.*?\n(.*?)(?=!|show|$)', content, re.IGNORECASE | re.DOTALL)
        if lldp_match:
            lldp_lines = lldp_match.group(1).strip().split('\n')
            for line in lldp_lines[1:]:  # Skip header
                parts = line.split()
                if len(parts) >= 4:
                    neighbors.append({
                        "device_name": parts[0],
                        "local_port": parts[1],
                        "remote_port": parts[-1],
                        "platform": parts[-2] if len(parts) > 4 else None,
                        "ip_address": None,  # LLDP may not have IP in brief output
                        "protocol": "LLDP",
                    })
        
        # Parse detailed LLDP output for IP addresses
        lldp_detail_match = re.search(r'show\s+lldp\s+neighbors\s+detail.*?(.*?)(?=!|show|$)', content, re.IGNORECASE | re.DOTALL)
        if lldp_detail_match:
            detail_output = lldp_detail_match.group(1)
            # Look for IP addresses in LLDP detail
            device_sections = detail_output.split('Chassis id:')
            for section in device_sections[1:]:  # Skip first empty section
                ip_match = re.search(r'Management\s+address:\s+(\d+\.\d+\.\d+\.\d+)', section, re.IGNORECASE)
                device_match = re.search(r'System\s+name:\s+(\S+)', section, re.IGNORECASE)
                interface_match = re.search(r'Local\s+intf:\s+(\S+)', section, re.IGNORECASE)
                
                if ip_match and device_match and interface_match:
                    device_name = device_match.group(1)
                    local_port = interface_match.group(1)
                    ip_address = ip_match.group(1)
                    
                    # Update existing neighbor or create new
                    existing = next((n for n in neighbors if n.get("device_name") == device_name and n.get("local_port") == local_port), None)
                    if existing:
                        existing["ip_address"] = ip_address
                    else:
                        neighbors.append({
                            "device_name": device_name,
                            "local_port": local_port,
                            "remote_port": "N/A",
                            "platform": None,
                            "ip_address": ip_address,
                            "protocol": "LLDP",
                        })
        
        return neighbors
    
    def extract_mac_arp(self, content: str) -> Dict[str, Any]:
        """Extract MAC address table and ARP table"""
        mac_arp = {
            "mac_table": [],
            "arp_table": [],
        }
        
        # MAC address table
        mac_match = re.search(r'show\s+mac\s+address-table.*?\n(.*?)(?=!|show|$)', content, re.IGNORECASE | re.DOTALL)
        if mac_match:
            mac_lines = mac_match.group(1).strip().split('\n')
            for line in mac_lines[1:]:  # Skip header
                parts = line.split()
                if len(parts) >= 3:
                    mac_arp["mac_table"].append({
                        "vlan": parts[0],
                        "mac_address": parts[1],
                        "type": parts[2] if len(parts) > 2 else "DYNAMIC",
                        "port": parts[3] if len(parts) > 3 else None,
                    })
        
        # ARP table
        arp_match = re.search(r'show\s+arp.*?\n(.*?)(?=!|show|$)', content, re.IGNORECASE | re.DOTALL)
        if arp_match:
            arp_lines = arp_match.group(1).strip().split('\n')
            for line in arp_lines[1:]:  # Skip header
                parts = line.split()
                if len(parts) >= 4:
                    mac_arp["arp_table"].append({
                        "ip_address": parts[1],
                        "mac_address": parts[3],
                        "interface": parts[-1],
                        "age": parts[2] if len(parts) > 4 else None,
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
            },
            "snmp": {
                "enabled": False,
                "communities": [],
            },
            "ntp": {
                "enabled": False,
                "servers": [],
            },
            "logging": {},
            "acls": [],
        }
        
        # Users
        user_pattern = r'username\s+(\S+)\s+(?:privilege\s+(\d+))?\s*(?:secret|password)'
        for match in re.finditer(user_pattern, content, re.IGNORECASE):
            security["users"].append({
                "username": match.group(1),
                "privilege": int(match.group(2)) if match.group(2) else 1,
            })
        
        # SSH
        if "ip ssh version" in content.lower():
            ssh_version_match = re.search(r'ip\s+ssh\s+version\s+(\d+)', content, re.IGNORECASE)
            if ssh_version_match:
                security["ssh"]["version"] = ssh_version_match.group(1)
            security["ssh"]["enabled"] = True
        
        # SNMP
        if "snmp-server" in content.lower():
            security["snmp"]["enabled"] = True
            community_pattern = r'snmp-server\s+community\s+(\S+)'
            for match in re.finditer(community_pattern, content, re.IGNORECASE):
                security["snmp"]["communities"].append(match.group(1))
        
        # NTP
        if "ntp" in content.lower():
            security["ntp"]["enabled"] = True
            ntp_server_pattern = r'ntp\s+server\s+(\S+)'
            for match in re.finditer(ntp_server_pattern, content, re.IGNORECASE):
                security["ntp"]["servers"].append(match.group(1))
        
        return security
    
    def extract_ha(self, content: str) -> Dict[str, Any]:
        """Extract High Availability information"""
        ha = {
            "port_channels": [],
            "hsrp": [],
            "vrrp": [],
        }
        
        # Port channels
        portchan_pattern = r'interface\s+(Port-channel|port-channel)\s*(\d+)\s*\n(.*?)(?=\ninterface\s+|$)'
        for match in re.finditer(portchan_pattern, content, re.IGNORECASE | re.DOTALL):
            channel_id = match.group(2)
            channel_config = match.group(3)
            
            members = []
            mode = None
            
            # Find member interfaces
            for iface_match in re.finditer(r'interface\s+(\S+)\s*\n(.*?)(?=\ninterface\s+|$)', content, re.IGNORECASE | re.DOTALL):
                iface_config = iface_match.group(2)
                if f"channel-group {channel_id}" in iface_config.lower():
                    members.append(iface_match.group(1))
                    if "channel-group" in iface_config.lower():
                        mode_match = re.search(r'channel-group\s+\d+\s+mode\s+(\S+)', iface_config, re.IGNORECASE)
                        if mode_match:
                            mode = mode_match.group(1).upper()
            
            ha["port_channels"].append({
                "id": channel_id,
                "mode": mode,
                "members": members,
                "status": "up" if members else "down",
            })
        
        # HSRP
        hsrp_pattern = r'standby\s+(\d+)\s+ip\s+(\d+\.\d+\.\d+\.\d+)'
        for match in re.finditer(hsrp_pattern, content, re.IGNORECASE):
            ha["hsrp"].append({
                "group": match.group(1),
                "virtual_ip": match.group(2),
            })
        
        # VRRP
        vrrp_pattern = r'vrrp\s+(\d+)\s+ip\s+(\d+\.\d+\.\d+\.\d+)'
        for match in re.finditer(vrrp_pattern, content, re.IGNORECASE):
            ha["vrrp"].append({
                "group": match.group(1),
                "virtual_ip": match.group(2),
            })
        
        return ha

