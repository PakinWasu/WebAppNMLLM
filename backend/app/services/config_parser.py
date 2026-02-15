"""
Main config parser service that routes to vendor-specific parsers.

Unified output schema (same for all vendors):
  device_name, device_overview, interfaces, vlans, stp, routing, neighbors,
  mac_arp, security, ha
Each key has the same structure regardless of Cisco/Huawei; only the way we
extract from raw config differs. Frontend and API consume this single shape.
"""

from typing import Dict, Any, Optional, List
from .parsers.cisco import CiscoIOSParser
from .parsers.huawei import HuaweiParser


def normalize_cisco_to_legacy(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map Cisco IOS parser spec output to legacy stored format so that
    documents, summary, and analysis continue to work without changes.
    Prefer device_info / security_audit / high_availability when present (new schema).
    """
    # device_overview: prefer device_info (new schema), else device_overview
    device_info = parsed.get("device_info") or {}
    overview = parsed.get("device_overview") or {}
    if device_info:
        overview = {
            "hostname": device_info.get("hostname") or overview.get("hostname"),
            "role": overview.get("role"),
            "model": device_info.get("model") or overview.get("model"),
            "os_version": device_info.get("os_version") or overview.get("os_version"),
            "serial_number": device_info.get("serial_number") or overview.get("serial_number"),
            "management_ip": device_info.get("management_ip") or overview.get("management_ip"),
            "uptime": device_info.get("uptime") or overview.get("uptime"),
            "cpu_utilization": device_info.get("cpu_load") if device_info.get("cpu_load") is not None else overview.get("cpu_utilization"),
            "memory_utilization": device_info.get("memory_usage") if device_info.get("memory_usage") is not None else overview.get("memory_utilization"),
        }
    if overview.get("memory_utilization") is not None and "memory_usage" not in overview:
        overview = {**overview, "memory_usage": overview["memory_utilization"]}

    # interfaces: status -> oper_status, protocol -> line_protocol, mode -> port_mode, ip_address -> ipv4_address; pass mtu/vlans from parser when present
    interfaces: List[Dict[str, Any]] = []
    for i in parsed.get("interfaces") or []:
        ip_addr = i.get("ip_address")
        if isinstance(ip_addr, str) and "/" in ip_addr:
            ip_addr = ip_addr.split("/")[0]
        interfaces.append({
            "name": i.get("name"),
            "type": i.get("type"),
            "admin_status": i.get("status") or "up",
            "oper_status": i.get("status") or "up",
            "line_protocol": i.get("protocol") or "up",
            "description": i.get("description"),
            "ipv4_address": ip_addr,
            "ipv6_address": i.get("ipv6_address"),
            "mac_address": i.get("mac_address"),
            "speed": i.get("speed"),
            "duplex": i.get("duplex"),
            "mtu": i.get("mtu"),
            "port_mode": i.get("mode"),
            "access_vlan": i.get("access_vlan"),
            "native_vlan": i.get("native_vlan"),
            "allowed_vlans": i.get("allowed_vlans"),
        })

    # vlans: dict with vlan_list/details/access_ports/trunk_ports or list [{id,name,status}]
    _vlans_raw = parsed.get("vlans")
    if isinstance(_vlans_raw, dict):
        vlan_list_spec = _vlans_raw.get("vlan_list") or []
        vlans = {
            "vlan_list": [str(v.get("id")) for v in vlan_list_spec if v.get("id") is not None],
            "vlan_names": {str(v["id"]): v.get("name") or str(v["id"]) for v in vlan_list_spec if v.get("id") is not None},
            "vlan_status": {str(v["id"]): v.get("status") or "active" for v in vlan_list_spec if v.get("id") is not None},
            "total_vlan_count": _vlans_raw.get("total_count", len(vlan_list_spec)),
            "details": _vlans_raw.get("details", []),
            "access_ports": _vlans_raw.get("access_ports", []),
            "trunk_ports": _vlans_raw.get("trunk_ports", []),
        }
        vlans["total_vlan_count"] = vlans["total_vlan_count"] or len(vlans["vlan_list"])
    else:
        vlan_list_spec = _vlans_raw if isinstance(_vlans_raw, list) else []
        vlan_list = [str(v.get("id")) for v in vlan_list_spec if v.get("id") is not None]
        vlans = {
            "vlan_list": vlan_list,
            "vlan_names": {str(v["id"]): v.get("name") or str(v["id"]) for v in vlan_list_spec if v.get("id") is not None},
            "vlan_status": {str(v["id"]): v.get("status") or "active" for v in vlan_list_spec if v.get("id") is not None},
            "total_vlan_count": len(vlan_list),
            "details": [],
            "access_ports": [],
            "trunk_ports": [],
        }

    # routing: routes[] -> static (list) + full route table for UI; ospf, eigrp, bgp from parser when present
    routing_raw = parsed.get("routing") or {}
    routes = routing_raw.get("routes") or []
    static_routes = [{"network": r["network"], "next_hop": r.get("next_hop") or "", "interface": r.get("interface") or ""} for r in routes if r.get("protocol") == "S"]
    route_table = [{"protocol": r.get("protocol"), "network": r.get("network"), "next_hop": r.get("next_hop") or "", "interface": r.get("interface") or ""} for r in routes]
    _ospf = routing_raw.get("ospf")
    ospf = (_ospf if isinstance(_ospf, dict) and (_ospf.get("router_id") or _ospf.get("process_id") or _ospf.get("areas")) else None) or {"router_id": None, "process_id": None, "areas": [], "interfaces": [], "neighbors": [], "dr_bdr": {}}
    _eigrp = routing_raw.get("eigrp")
    eigrp = (_eigrp if isinstance(_eigrp, dict) and (_eigrp.get("as_number") or _eigrp.get("router_id")) else None) or {"as_number": None, "router_id": None, "neighbors": [], "hold_time": None, "learned_routes": []}
    _bgp = routing_raw.get("bgp")
    bgp = (_bgp if isinstance(_bgp, dict) and (_bgp.get("local_as") or _bgp.get("peers")) else None) or {"local_as": None, "peers": []}
    routing = {
        "static": static_routes,
        "routes": route_table,
        "ospf": ospf,
        "eigrp": eigrp,
        "bgp": bgp,
        "rip": {"version": None, "networks": [], "interfaces": [], "hop_count": {}, "auto_summary": None, "passive_interfaces": [], "timers": {"update": None, "invalid": None, "holddown": None, "flush": None}, "admin_distance": None},
    }

    # neighbors: neighbor_id -> device_name, local_interface -> local_port, remote_interface -> remote_port
    neighbors = []
    for n in parsed.get("neighbors") or []:
        neighbors.append({
            "device_name": n.get("neighbor_id"),
            "local_port": n.get("local_interface"),
            "remote_port": n.get("remote_interface"),
            "platform": n.get("platform"),
            "ip_address": n.get("ip_address"),
        })

    # arp_mac_table -> mac_arp
    arp_mac = parsed.get("arp_mac_table") or {}
    mac_arp = {"mac_table": arp_mac.get("mac_entries") or [], "arp_table": arp_mac.get("arp_entries") or []}

    # security_audit (new) or security_mgmt -> security
    sec_audit = parsed.get("security_audit") or {}
    sec_mgmt = parsed.get("security_mgmt") or {}
    _log_host = None
    if sec_audit:
        ssh = sec_audit.get("ssh") or {}
        snmp = sec_audit.get("snmp") or {}
        ntp = sec_audit.get("ntp") or {}
        logging_obj = sec_audit.get("logging") or {}
        _log_host = (logging_obj.get("syslog_servers") or [None])[0] if logging_obj.get("syslog_servers") else sec_mgmt.get("logging_host")
        security = {
            "users": sec_mgmt.get("users") or [],
            "aaa": {"protocols": sec_audit.get("aaa") and sec_audit["aaa"].get("protocols") or []},
            "ssh": {"version": ssh.get("version"), "enabled": ssh.get("status") == "Enabled"},
            "snmp": {"enabled": snmp.get("status") == "Enabled", "communities": snmp.get("communities") or []},
            "ntp": {"enabled": bool(ntp.get("servers")), "servers": ntp.get("servers") or []},
            "logging": {"enabled": bool(_log_host), "log_hosts": [_log_host] if _log_host else []},
            "acls": [a.get("name") for a in (sec_audit.get("acls") or []) if a.get("name")] or sec_mgmt.get("acls") or [],
        }
    else:
        _log_host = sec_mgmt.get("logging_host")
        security = {
            "users": sec_mgmt.get("users") or [],
            "aaa": {},
            "ssh": {"version": sec_mgmt.get("ssh_version"), "enabled": sec_mgmt.get("ssh_enabled") or False},
            "snmp": {"enabled": sec_mgmt.get("snmp_enabled") or False, "communities": []},
            "ntp": {"enabled": bool(sec_mgmt.get("ntp_servers")), "servers": sec_mgmt.get("ntp_servers") or []},
            "logging": {"enabled": bool(_log_host), "log_hosts": [_log_host] if _log_host else []},
            "acls": sec_mgmt.get("acls") or [],
        }

    # stp: mode, root_bridges, root_bridge_id, interfaces (port/role/state), portfast_enabled
    stp_spec = parsed.get("stp") or {}
    root_bridges = stp_spec.get("root_bridges") or []
    stp = {
        "stp_mode": stp_spec.get("mode"),
        "root_bridges": root_bridges,
        "root_bridge_id": stp_spec.get("root_bridge_id") or (root_bridges[0] if root_bridges else None),
        "mode": stp_spec.get("mode"),
        "interfaces": stp_spec.get("interfaces") or [],
        "portfast_enabled": stp_spec.get("portfast_enabled"),
    }

    # high_availability (new) or ha -> port_channels, hsrp_vrrp -> hsrp / vrrp
    high_avail = parsed.get("high_availability") or {}
    ha_spec = parsed.get("ha") or {}
    ether_channels = high_avail.get("ether_channels") or []
    if not ether_channels and ha_spec.get("etherchannels"):
        ether_channels = [{"interface": f"Po{e.get('id')}", "protocol": e.get("protocol"), "members": e.get("members") or [], "status": "up" if e.get("members") else "down"} for e in ha_spec["etherchannels"]]
    port_channels = []
    for e in ether_channels:
        if isinstance(e, dict):
            po_name = e.get("interface") or ""
            po_id = int(po_name.replace("Po", "")) if po_name and po_name.upper().startswith("PO") else None
            port_channels.append({"id": po_id, "mode": e.get("protocol"), "members": e.get("members") or [], "status": (e.get("status") or "up").lower()})
    if not port_channels:
        port_channels = [{"id": e.get("id"), "mode": e.get("protocol"), "members": e.get("members") or [], "status": "up" if e.get("members") else "down"} for e in ha_spec.get("etherchannels") or []]
    hsrp_vrrp_list = ha_spec.get("hsrp_vrrp") or []
    hsrp = [{"group": h.get("group"), "virtual_ip": h.get("virtual_ip"), "interface": h.get("interface"), "state": h.get("state")} for h in hsrp_vrrp_list]
    vrrp = []
    # etherchannel: frontend expects list of {name, mode, members, status}; derive from port_channels
    etherchannel = [{"name": f"Po{p.get('id')}" if p.get("id") is not None else "Po", "mode": p.get("mode"), "members": p.get("members") or [], "status": p.get("status") or "up"} for p in port_channels]
    ha = {"port_channels": port_channels, "etherchannel": etherchannel, "hsrp": hsrp, "vrrp": vrrp}

    # Ensure device_name is set (Cisco stores hostname in device_overview only; topology/summary expect top-level device_name)
    device_name = (overview.get("hostname") or "").strip() if isinstance(overview.get("hostname"), str) else None
    return {
        "device_name": device_name,
        "device_overview": overview,
        "interfaces": interfaces,
        "vlans": vlans,
        "stp": stp,
        "routing": routing,
        "neighbors": neighbors,
        "mac_arp": mac_arp,
        "security": security,
        "ha": ha,
    }


def normalize_huawei_to_legacy(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map Huawei parser output to the same unified JSON structure as Cisco (legacy).
    Result must have identical top-level keys and shapes so frontend/API behave the same for any vendor.
    """
    device_info = parsed.get("device_info") or {}
    overview_raw = parsed.get("device_overview") or {}
    overview = {
        "hostname": device_info.get("hostname") or overview_raw.get("hostname"),
        "role": overview_raw.get("role"),
        "model": device_info.get("model") or overview_raw.get("model"),
        "os_version": device_info.get("os_version") or overview_raw.get("os_version"),
        "serial_number": device_info.get("serial_number") or overview_raw.get("serial_number"),
        "management_ip": device_info.get("management_ip") or overview_raw.get("management_ip"),
        "uptime": device_info.get("uptime") or overview_raw.get("uptime"),
        "cpu_utilization": device_info.get("cpu_utilization") or overview_raw.get("cpu_utilization"),
        "memory_utilization": overview_raw.get("memory_usage"),
        "memory_usage": overview_raw.get("memory_usage"),
    }
    if overview.get("memory_utilization") is not None and "memory_usage" not in overview:
        overview["memory_usage"] = overview["memory_utilization"]

    # interfaces: same keys as legacy (Huawei already uses admin_status, oper_status, line_protocol, ipv4_address, etc.)
    interfaces: List[Dict[str, Any]] = []
    for i in parsed.get("interfaces") or []:
        ip_addr = i.get("ipv4_address") or i.get("ip_address")
        if isinstance(ip_addr, str) and "/" in ip_addr:
            ip_addr = ip_addr.split("/")[0]
        interfaces.append({
            "name": i.get("name"),
            "type": i.get("type"),
            "admin_status": i.get("admin_status") or "up",
            "oper_status": i.get("oper_status") or i.get("status") or "up",
            "line_protocol": i.get("line_protocol") or i.get("protocol") or "up",
            "description": i.get("description"),
            "ipv4_address": ip_addr,
            "ipv6_address": i.get("ipv6_address"),
            "mac_address": i.get("mac_address"),
            "speed": i.get("speed"),
            "duplex": i.get("duplex"),
            "mtu": i.get("mtu"),
            "port_mode": i.get("port_mode"),
            "access_vlan": i.get("access_vlan"),
            "native_vlan": i.get("native_vlan"),
            "allowed_vlans": i.get("allowed_vlans"),
        })

    # vlans: dict with vlan_list (list of {id,name,status} or list of ids), details, access_ports, trunk_ports
    vlan_list_spec = parsed.get("vlans") or {}
    raw_list = vlan_list_spec.get("vlan_list") or []
    if raw_list and isinstance(raw_list[0], dict):
        vlan_list = [str(v.get("id")) for v in raw_list if v.get("id") is not None]
        vlan_names = {str(v["id"]): v.get("name") or str(v["id"]) for v in raw_list if v.get("id") is not None}
        vlan_status = {str(v["id"]): v.get("status") or "active" for v in raw_list if v.get("id") is not None}
    else:
        vlan_list = [str(v) for v in raw_list]
        vlan_names = (vlan_list_spec.get("vlan_names") or {}) if isinstance(vlan_list_spec, dict) else {vid: vid for vid in vlan_list}
        vlan_status = (vlan_list_spec.get("vlan_status") or {}) if isinstance(vlan_list_spec, dict) else {vid: "active" for vid in vlan_list}
    vlans = {
        "vlan_list": vlan_list,
        "vlan_names": vlan_names,
        "vlan_status": vlan_status,
        "total_vlan_count": vlan_list_spec.get("total_vlan_count", len(vlan_list)) if isinstance(vlan_list_spec, dict) else len(vlan_list),
        "details": vlan_list_spec.get("details", []) if isinstance(vlan_list_spec, dict) else [],
        "access_ports": vlan_list_spec.get("access_ports", []) if isinstance(vlan_list_spec, dict) else [],
        "trunk_ports": vlan_list_spec.get("trunk_ports", []) if isinstance(vlan_list_spec, dict) else [],
    }

    # routing: static + routes[] (from display ip routing-table when present) + ospf/eigrp/bgp/rip
    routing_raw = parsed.get("routing") or {}
    static_raw = routing_raw.get("static") or []
    static_routes = []
    # Prefer full route table from "display ip routing-table" when present (Huawei); else build from static only
    routes_from_table = routing_raw.get("routes") or []
    if routes_from_table:
        route_table = [{"protocol": r.get("protocol"), "network": r.get("network"), "next_hop": r.get("next_hop") or "", "interface": r.get("interface") or ""} for r in routes_from_table]
    else:
        route_table = []
    for r in static_raw:
        net = r.get("network")
        if not net:
            continue
        nh = r.get("next_hop") or r.get("nexthop") or ""
        iface = r.get("interface") or ""
        static_routes.append({"network": net, "next_hop": nh, "interface": iface})
        if not routes_from_table:
            route_table.append({"protocol": "S", "network": net, "next_hop": nh, "interface": iface})
    ospf_raw = routing_raw.get("ospf")
    ospf = {"router_id": None, "process_id": None, "areas": [], "interfaces": [], "neighbors": [], "dr_bdr": {}}
    if isinstance(ospf_raw, dict):
        ospf["router_id"] = ospf_raw.get("router_id")
        ospf["process_id"] = ospf_raw.get("process_id")
        ospf["areas"] = ospf_raw.get("areas") or []
    bgp_raw = routing_raw.get("bgp")
    bgp = {"local_as": None, "peers": []}
    if isinstance(bgp_raw, dict):
        bgp["local_as"] = bgp_raw.get("as_number") or bgp_raw.get("local_as")
        bgp["peers"] = bgp_raw.get("peers") or []
    rip_raw = routing_raw.get("rip")
    rip = {"version": None, "networks": [], "interfaces": [], "hop_count": {}, "auto_summary": None, "passive_interfaces": [], "timers": {"update": None, "invalid": None, "holddown": None, "flush": None}, "admin_distance": None}
    if isinstance(rip_raw, dict):
        rip["version"] = rip_raw.get("version")
        rip["networks"] = rip_raw.get("networks") or []
    routing = {
        "static": static_routes,
        "routes": route_table,
        "ospf": ospf,
        "eigrp": {"as_number": None, "router_id": None, "neighbors": [], "hold_time": None, "learned_routes": []},
        "bgp": bgp,
        "rip": rip,
    }

    # neighbors: same keys device_name, local_port, remote_port, platform, ip_address
    neighbors = []
    for n in parsed.get("neighbors") or []:
        neighbors.append({
            "device_name": n.get("device_name"),
            "local_port": n.get("local_port"),
            "remote_port": n.get("remote_port"),
            "platform": n.get("platform"),
            "ip_address": n.get("ip_address"),
        })

    # mac_arp: ensure lists
    mac_arp_raw = parsed.get("mac_arp") or {}
    mac_arp = {
        "mac_table": mac_arp_raw.get("mac_table") if isinstance(mac_arp_raw.get("mac_table"), list) else [],
        "arp_table": mac_arp_raw.get("arp_table") if isinstance(mac_arp_raw.get("arp_table"), list) else [],
    }

    # security: same shape as legacy (users, aaa, ssh, snmp, ntp, logging, acls)
    sec_raw = parsed.get("security") or {}
    sec_audit = parsed.get("security_audit") or {}
    users = sec_raw.get("user_accounts") or sec_raw.get("users") or []
    ntp_servers = []
    if sec_raw.get("ntp_server"):
        ntp_servers.append(sec_raw["ntp_server"])
    log_host = sec_raw.get("syslog") or (sec_audit.get("logging") or {}).get("log_host") if isinstance(sec_audit.get("logging"), dict) else None
    if not log_host and isinstance(sec_audit.get("logging"), str):
        log_host = sec_audit.get("logging")
    ssh_enabled = sec_raw.get("ssh_enabled") if sec_raw.get("ssh_enabled") is not None else (sec_audit.get("ssh") or {}).get("status") == "Enabled"
    snmp_enabled = bool(sec_raw.get("snmp_settings") or (sec_audit.get("snmp") or {}).get("status") == "Enabled")
    snmp_communities = []
    if isinstance(sec_raw.get("snmp_settings"), dict) and sec_raw["snmp_settings"].get("community"):
        snmp_communities.append(sec_raw["snmp_settings"]["community"])
    acls_raw = sec_raw.get("acls")
    if isinstance(acls_raw, list):
        acls = [a.get("name") or a.get("acl_number") or str(a) for a in acls_raw if isinstance(a, dict)] or [str(x) for x in acls_raw if isinstance(x, str)]
    elif isinstance(acls_raw, dict):
        acls = list(acls_raw.keys())
    else:
        acls = []
    security = {
        "users": users,
        "aaa": {},
        "ssh": {"version": (sec_audit.get("ssh") or {}).get("version"), "enabled": bool(ssh_enabled)},
        "snmp": {"enabled": bool(snmp_enabled), "communities": snmp_communities or (sec_audit.get("snmp") or {}).get("communities") or []},
        "ntp": {"enabled": bool(ntp_servers), "servers": ntp_servers},
        "logging": {"enabled": bool(log_host), "log_hosts": [log_host] if log_host else []},
        "acls": acls or (sec_audit.get("acls") if isinstance(sec_audit.get("acls"), list) else []),
    }

    # stp: same keys stp_mode, root_bridges, root_bridge_id, mode
    stp_raw = parsed.get("stp") or {}
    rb = stp_raw.get("root_bridge_id")
    root_bridges = stp_raw.get("root_bridges") or ([rb] if rb else [])
    stp = {
        "stp_mode": stp_raw.get("stp_mode") or stp_raw.get("mode"),
        "root_bridges": root_bridges,
        "root_bridge_id": rb,
        "mode": stp_raw.get("stp_mode") or stp_raw.get("mode"),
    }

    # ha: port_channels, etherchannel, hsrp, vrrp (same as legacy)
    ha_raw = parsed.get("ha") or {}
    high_avail = parsed.get("high_availability") or {}
    ether_list = high_avail.get("ether_channels") or ha_raw.get("etherchannel") or []
    port_channels = []
    for e in ether_list:
        if isinstance(e, dict):
            name = e.get("interface") or e.get("name") or ""
            po_id = None
            if name:
                import re as _re
                num = _re.search(r"\d+", name)
                if num:
                    try:
                        po_id = int(num.group(0))
                    except ValueError:
                        pass
            port_channels.append({
                "id": po_id or e.get("id"),
                "mode": e.get("protocol") or e.get("mode"),
                "members": e.get("members") or [],
                "status": (e.get("status") or "up").lower(),
            })
    etherchannel = [{"name": f"Po{p['id']}" if p.get("id") is not None else "Po", "mode": p.get("mode"), "members": p.get("members") or [], "status": p.get("status") or "up"} for p in port_channels]
    hsrp = []
    vrrp_list = ha_raw.get("vrrp") or []
    vrrp = []
    for v in vrrp_list if isinstance(vrrp_list, list) else []:
        if isinstance(v, dict):
            vrrp.append({"group": v.get("vrid") or v.get("group"), "virtual_ip": v.get("virtual_ip"), "interface": v.get("interface"), "state": v.get("state")})
    ha = {"port_channels": port_channels, "etherchannel": etherchannel, "hsrp": hsrp, "vrrp": vrrp}

    device_name = (overview.get("hostname") or "").strip() if isinstance(overview.get("hostname"), str) else None
    return {
        "device_name": device_name,
        "device_overview": overview,
        "interfaces": interfaces,
        "vlans": vlans,
        "stp": stp,
        "routing": routing,
        "neighbors": neighbors,
        "mac_arp": mac_arp,
        "security": security,
        "ha": ha,
    }


class ConfigParser:
    """Main parser service that detects vendor and routes to appropriate parser"""
    
    def __init__(self):
        # Put HuaweiParser first because it has more specific patterns
        # and Cisco might match Huawei configs incorrectly
        self.parsers = [
            HuaweiParser(),   # Check Huawei first (more specific)
            CiscoIOSParser(), # Then check Cisco (returns spec; normalized to legacy below)
        ]

    def parse_config(self, content: str, filename: str) -> Optional[Dict[str, Any]]:
        """
        Parse configuration content and return structured data in legacy format.
        Passes full content (original_content) to each vendor parser so that
        Multi-Source Inference can extract from anywhere in the file.
        """
        for parser in self.parsers:
            if parser.detect_vendor(content):
                try:
                    parsed_data = parser.parse(content, filename)
                    vendor = self._get_vendor_name(parser)
                    parsed_data["vendor"] = vendor
                    # Normalize to unified JSON structure so frontend sees same shape for all vendors
                    if isinstance(parser, CiscoIOSParser):
                        parsed_data = normalize_cisco_to_legacy(parsed_data)
                    elif isinstance(parser, HuaweiParser):
                        parsed_data = normalize_huawei_to_legacy(parsed_data)
                    parsed_data["vendor"] = vendor
                    return parsed_data
                except Exception as e:
                    print(f"Error parsing config with {type(parser).__name__}: {e}")
                    # Return minimal legacy shape so we can still store device_name (e.g. for topology)
                    try:
                        device_name = self.extract_device_name(content, filename)
                        overview = {"hostname": device_name} if device_name else {}
                        return {
                            "device_name": device_name or None,
                            "device_overview": overview,
                            "interfaces": [],
                            "vlans": {"vlan_list": [], "vlan_names": {}, "vlan_status": {}, "total_vlan_count": 0},
                            "stp": {"stp_mode": None, "root_bridges": [], "root_bridge_id": None, "mode": None},
                            "routing": {"static": [], "routes": [], "ospf": {}, "eigrp": {}, "bgp": {}, "rip": {}},
                            "neighbors": [],
                            "mac_arp": {"mac_table": [], "arp_table": []},
                            "security": {"users": [], "aaa": {}, "ssh": {"version": None, "enabled": False}, "snmp": {"enabled": False, "communities": []}, "ntp": {"enabled": False, "servers": []}, "logging": {"enabled": False, "log_hosts": []}, "acls": []},
                            "ha": {"port_channels": [], "etherchannel": [], "hsrp": [], "vrrp": []},
                            "vendor": self._get_vendor_name(parser),
                        }
                    except Exception:
                        return None
        return None
    
    def extract_device_name(self, content: str, filename: str) -> str:
        """
        Extract device name from config content or filename
        
        Args:
            content: Configuration file content
            filename: Original filename
        
        Returns:
            Device name string
        """
        import re
        import os
        
        # Try to extract from prompt in log files (e.g., <ACC1>display...)
        prompt_match = re.search(r'<(\S+)>', content)
        if prompt_match:
            device_name = prompt_match.group(1)
            # Remove common suffixes that might be in prompt
            device_name = device_name.split()[0] if ' ' in device_name else device_name
            return device_name
        
        # Try to extract from config content
        # Cisco hostname
        hostname_match = re.search(r'hostname\s+(\S+)', content, re.IGNORECASE)
        if hostname_match:
            return hostname_match.group(1)
        
        # Huawei sysname
        sysname_match = re.search(r'sysname\s+(\S+)', content, re.IGNORECASE)
        if sysname_match:
            return sysname_match.group(1)
        
        # Try from comment
        device_match = re.search(r'!.*DEVICE:\s*(\S+)', content, re.IGNORECASE)
        if device_match:
            return device_match.group(1)
        
        # Fallback to filename (remove extension and common prefixes)
        base_name = os.path.splitext(filename)[0]
        # Remove common prefixes like "2026-01-11_topo_real"
        base_name = re.sub(r'^\d{4}-\d{2}-\d{2}_[^_]+_real', '', base_name)
        return base_name if base_name else os.path.splitext(filename)[0]
    
    def _get_vendor_name(self, parser) -> str:
        """Get vendor name string from parser instance"""
        parser_name = type(parser).__name__.lower()
        if "cisco" in parser_name:
            return "cisco"
        elif "huawei" in parser_name:
            return "huawei"
        else:
            return "unknown"

