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


def _normalize_acls(audit_acls: Any, mgmt_acls: Any) -> List[Dict[str, Any]]:
    """Produce unified acls list: [{ name, type, rules }]. Prefer audit_acls when present and structured."""
    if isinstance(audit_acls, list) and audit_acls and isinstance(audit_acls[0], dict):
        return [
            {"name": a.get("name"), "type": a.get("type") or "Extended", "rules": a.get("rules") or []}
            for a in audit_acls if a.get("name") is not None
        ]
    if isinstance(mgmt_acls, list):
        return [{"name": a, "type": "Extended", "rules": []} for a in mgmt_acls if isinstance(a, (str, int))]
    return []


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
        subnet_mask = i.get("subnet_mask")
        if isinstance(ip_addr, str) and "/" in ip_addr:
            parts = ip_addr.split("/", 1)
            ip_addr = parts[0]
            if not subnet_mask and len(parts) > 1 and parts[1].strip():
                subnet_mask = parts[1].strip()
        interfaces.append({
            "name": i.get("name"),
            "type": i.get("type"),
            "admin_status": i.get("status") or "up",
            "oper_status": i.get("status") or "up",
            "line_protocol": i.get("protocol") or "up",
            "description": i.get("description"),
            "ipv4_address": ip_addr,
            "subnet_mask": subnet_mask,
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

    # vlans: vlan_list, details (name/status per VLAN), access_ports, trunk_ports; no redundant vlan_names/vlan_status
    _vlans_raw = parsed.get("vlans")
    if isinstance(_vlans_raw, dict):
        vlan_list_spec = _vlans_raw.get("vlan_list") or []
        details_spec = _vlans_raw.get("details") or []
        if vlan_list_spec and isinstance(vlan_list_spec[0], dict):
            vlan_list = [str(v.get("id")) for v in vlan_list_spec if v.get("id") is not None]
        else:
            vlan_list = [str(v) for v in vlan_list_spec if v is not None]
        vlans = {
            "vlan_list": vlan_list,
            "total_vlan_count": _vlans_raw.get("total_vlan_count") or _vlans_raw.get("total_count") or len(vlan_list),
            "details": details_spec,
            "access_ports": _vlans_raw.get("access_ports", []),
            "trunk_ports": _vlans_raw.get("trunk_ports", []),
        }
        vlans["total_vlan_count"] = vlans["total_vlan_count"] or len(vlans["vlan_list"])
    else:
        vlan_list_spec = _vlans_raw if isinstance(_vlans_raw, list) else []
        vlan_list = [str(v.get("id")) for v in vlan_list_spec if v.get("id") is not None]
        vlans = {
            "vlan_list": vlan_list,
            "total_vlan_count": len(vlan_list),
            "details": [],
            "access_ports": [],
            "trunk_ports": [],
        }

    # routing: Scope 2.3.2.5 - routes (distance, metric), ospf (interfaces, learned_prefix_count), eigrp, bgp, rip
    routing_raw = parsed.get("routing") or {}
    routes = routing_raw.get("routes") or []
    static_routes = [{"network": r["network"], "next_hop": r.get("next_hop") or "", "interface": r.get("interface") or "", "distance": r.get("distance"), "metric": r.get("metric")} for r in routes if r.get("protocol") == "S"]
    route_table = [{"protocol": r.get("protocol"), "network": r.get("network"), "next_hop": r.get("next_hop") or "", "interface": r.get("interface") or "", "distance": r.get("distance"), "metric": r.get("metric")} for r in routes]
    _ospf = routing_raw.get("ospf")
    _ospf_default = {"router_id": None, "process_id": None, "areas": [], "interfaces": [], "neighbors": [], "dr_bdr": {}, "learned_prefix_count": None}
    ospf = (_ospf if isinstance(_ospf, dict) and (_ospf.get("router_id") or _ospf.get("process_id") or _ospf.get("areas")) else None) or _ospf_default.copy()
    if isinstance(_ospf, dict):
        if "learned_prefix_count" in _ospf:
            ospf["learned_prefix_count"] = _ospf["learned_prefix_count"]
        if _ospf.get("interfaces"):
            ospf["interfaces"] = _ospf["interfaces"]
    _eigrp = routing_raw.get("eigrp")
    eigrp = (_eigrp if isinstance(_eigrp, dict) and (_eigrp.get("as_number") or _eigrp.get("router_id")) else None) or {"as_number": None, "router_id": None, "neighbors": [], "hold_time": None, "learned_routes": []}
    _bgp = routing_raw.get("bgp")
    bgp = (_bgp if isinstance(_bgp, dict) and (_bgp.get("local_as") or _bgp.get("peers")) else None) or {"local_as": None, "peers": [], "router_id": None}
    if isinstance(_bgp, dict) and _bgp.get("peers"):
        for p in bgp.get("peers") or []:
            if "neighbor_ip" not in p and p.get("peer"):
                p["neighbor_ip"] = p["peer"]
    _rip = routing_raw.get("rip")
    rip_default = {"version": None, "timers": {"update": None, "invalid": None, "hold": None, "flush": None}, "interfaces": [], "passive_interfaces": []}
    rip = (_rip if isinstance(_rip, dict) else None) or rip_default.copy()
    if isinstance(_rip, dict):
        rip["version"] = _rip.get("version")
        rip["timers"] = _rip.get("timers") or rip_default["timers"]
        rip["interfaces"] = _rip.get("interfaces") or []
        rip["passive_interfaces"] = _rip.get("passive_interfaces") or []
    routing = {
        "static": static_routes,
        "routes": route_table,
        "ospf": ospf,
        "eigrp": eigrp,
        "bgp": bgp,
        "rip": rip,
    }

    # neighbors: map to legacy keys and 2.3.2.6 fields (neighbor_device_name, neighbor_ip, platform, local_port, remote_port, capabilities, discovery_protocol)
    neighbors = []
    for n in parsed.get("neighbors") or []:
        neighbors.append({
            "device_name": n.get("neighbor_id") or n.get("neighbor_device_name"),
            "neighbor_device_name": n.get("neighbor_device_name") or n.get("neighbor_id"),
            "neighbor_ip": n.get("neighbor_ip") or n.get("ip_address"),
            "local_port": n.get("local_port") or n.get("local_interface"),
            "remote_port": n.get("remote_port") or n.get("remote_interface"),
            "platform": n.get("platform"),
            "ip_address": n.get("ip_address") or n.get("neighbor_ip"),
            "capabilities": n.get("capabilities"),
            "discovery_protocol": n.get("discovery_protocol"),
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
        _logging_enabled = logging_obj.get("syslog_enabled") if logging_obj.get("syslog_enabled") is not None else bool(_log_host)
        security = {
            "users": sec_mgmt.get("users") or [],
            "aaa": {"protocols": sec_audit.get("aaa") and sec_audit["aaa"].get("protocols") or []},
            "ssh": {"version": ssh.get("version"), "enabled": ssh.get("status") == "Enabled"},
            "snmp": {"enabled": snmp.get("status") == "Enabled", "communities": snmp.get("communities") or []},
            "ntp": {"enabled": bool(ntp.get("servers")), "servers": ntp.get("servers") or [], "sync_status": ntp.get("sync_status") or "unknown"},
            "logging": {"enabled": _logging_enabled, "console_level": logging_obj.get("console_level"), "log_hosts": [_log_host] if _log_host else []},
            "acls": _normalize_acls(sec_audit.get("acls"), sec_mgmt.get("acls")),
        }
    else:
        _log_host = sec_mgmt.get("logging_host")
        security = {
            "users": sec_mgmt.get("users") or [],
            "aaa": {},
            "ssh": {"version": sec_mgmt.get("ssh_version"), "enabled": sec_mgmt.get("ssh_enabled") or False},
            "snmp": {"enabled": sec_mgmt.get("snmp_enabled") or False, "communities": []},
            "ntp": {"enabled": bool(sec_mgmt.get("ntp_servers")), "servers": sec_mgmt.get("ntp_servers") or [], "sync_status": "unknown"},
            "logging": {"enabled": bool(_log_host), "console_level": None, "log_hosts": [_log_host] if _log_host else []},
            "acls": sec_mgmt.get("acls") or [],
        }

    # stp: mode, root_bridges, root_bridge_id, interfaces (port/role/state/cost/portfast/bpduguard), portfast_enabled
    stp_spec = parsed.get("stp") or {}
    root_bridges = stp_spec.get("root_bridges") or []
    stp = {
        "stp_mode": stp_spec.get("mode"),
        "root_bridges": root_bridges,
        "root_bridge_id": stp_spec.get("root_bridge_id") or (root_bridges[0] if root_bridges else None),
        "mode": stp_spec.get("mode"),
        "interfaces": stp_spec.get("interfaces") or [],
        "portfast_enabled": stp_spec.get("portfast_enabled"),
        "bpduguard_enabled": stp_spec.get("bpduguard_enabled"),
    }
    if stp_spec.get("stp_info") is not None:
        stp["stp_info"] = stp_spec["stp_info"]

    # high_availability (new) or ha -> single etherchannels list; hsrp/vrrp with priority and preempt (Scope 2.3.2.9)
    high_avail = parsed.get("high_availability") or {}
    ha_spec = parsed.get("ha") or {}
    etherchannels = []
    # Scope 2.3.2.9.1: etherchannels with group, name, protocol, status, members[{ interface, status }]
    if ha_spec.get("etherchannels"):
        for e in ha_spec["etherchannels"]:
            if isinstance(e, dict):
                group = e.get("group", e.get("id"))
                name = e.get("name") or f"Po{e.get('group', e.get('id', 0))}"
                protocol = e.get("protocol") or e.get("mode") or "LACP"
                members = e.get("members") or []
                members_norm = [m if isinstance(m, dict) and ("interface" in m or "port" in m) else {"interface": m, "status": "Bundled"} for m in members]
                for m in members_norm:
                    if isinstance(m, dict) and "interface" not in m and "port" in m:
                        m["interface"] = m.pop("port", m.get("port"))
                etherchannels.append({"group": group, "name": name, "protocol": protocol, "status": e.get("status") or "up", "members": members_norm})
    if not etherchannels:
        ether_channels = high_avail.get("ether_channels") or []
        for e in ether_channels:
            if isinstance(e, dict):
                name = e.get("interface") or f"Po{e.get('id', 0)}"
                members = e.get("members") or []
                members_norm = [m if isinstance(m, dict) else {"interface": m, "status": "Bundled"} for m in members]
                for m in members_norm:
                    if isinstance(m, dict) and "interface" not in m and "port" in m:
                        m["interface"] = m.pop("port", m.get("port"))
                etherchannels.append({"group": None, "name": name, "protocol": e.get("protocol") or "LACP", "status": e.get("status") or "up", "members": members_norm})
    # Backward compat: port_channels and etherchannel derived from etherchannels
    port_channels = []
    for e in etherchannels:
        po_name = (e.get("name") or "").strip()
        po_id = e.get("group") if e.get("group") is not None else (int(po_name.replace("Po", "")) if po_name.upper().startswith("PO") and len(po_name) > 2 and po_name[2:].isdigit() else None)
        members_list = [m.get("interface", m.get("port", m)) if isinstance(m, dict) else m for m in (e.get("members") or [])]
        port_channels.append({"id": po_id, "mode": e.get("protocol") or e.get("mode"), "members": members_list, "status": (e.get("status") or "up").lower()})
    hsrp = []
    for h in ha_spec.get("hsrp") or []:
        hsrp.append({"group": h.get("group"), "virtual_ip": h.get("virtual_ip"), "interface": h.get("interface"), "state": h.get("state"), "priority": h.get("priority"), "preempt": h.get("preempt")})
    vrrp = list(ha_spec.get("vrrp") or [])
    etherchannel = [{"name": e.get("name") or "Po", "mode": e.get("protocol") or e.get("mode"), "members": e.get("members") or [], "status": e.get("status") or "up"} for e in etherchannels]
    ha = {"etherchannels": etherchannels, "port_channels": port_channels, "etherchannel": etherchannel, "hsrp": hsrp, "vrrp": vrrp}

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
        "memory_utilization": overview_raw.get("memory_utilization") or overview_raw.get("memory_usage"),
        "memory_usage": overview_raw.get("memory_utilization") or overview_raw.get("memory_usage"),
    }

    # interfaces: same keys as legacy (Huawei already uses admin_status, oper_status, line_protocol, ipv4_address, etc.)
    interfaces: List[Dict[str, Any]] = []
    for i in parsed.get("interfaces") or []:
        ip_addr = i.get("ipv4_address") or i.get("ip_address")
        subnet_mask = i.get("subnet_mask")
        if isinstance(ip_addr, str) and "/" in ip_addr:
            parts = ip_addr.split("/", 1)
            ip_addr = parts[0]
            if not subnet_mask and len(parts) > 1 and parts[1].strip():
                subnet_mask = parts[1].strip()
        interfaces.append({
            "name": i.get("name"),
            "type": i.get("type"),
            "admin_status": i.get("admin_status") or "up",
            "oper_status": i.get("oper_status") or i.get("status") or "up",
            "line_protocol": i.get("line_protocol") or i.get("protocol") or "up",
            "description": i.get("description"),
            "ipv4_address": ip_addr,
            "subnet_mask": subnet_mask,
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

    # vlans: vlan_list, details (name/status per VLAN), access_ports, trunk_ports; no redundant vlan_names/vlan_status
    vlan_list_spec = parsed.get("vlans") or {}
    raw_list = vlan_list_spec.get("vlan_list") or []
    if raw_list and isinstance(raw_list[0], dict):
        vlan_list = [str(v.get("id")) for v in raw_list if v.get("id") is not None]
    else:
        vlan_list = [str(v) for v in raw_list]
    vlans = {
        "vlan_list": vlan_list,
        "total_vlan_count": vlan_list_spec.get("total_vlan_count", len(vlan_list)) if isinstance(vlan_list_spec, dict) else len(vlan_list),
        "details": vlan_list_spec.get("details", []) if isinstance(vlan_list_spec, dict) else [],
        "access_ports": vlan_list_spec.get("access_ports", []) if isinstance(vlan_list_spec, dict) else [],
        "trunk_ports": vlan_list_spec.get("trunk_ports", []) if isinstance(vlan_list_spec, dict) else [],
    }

    # routing: 2.3.2.5 structure (static_routes, ospf, eigrp, bgp, rip) + legacy static/routes
    routing_raw = parsed.get("routing") or {}
    # 2.3.2.5 exact structure (pass through from parser)
    static_routes_obj = routing_raw.get("static_routes")
    if not isinstance(static_routes_obj, dict):
        static_routes_obj = {"routes": []}
    ospf_obj = routing_raw.get("ospf")
    if not isinstance(ospf_obj, dict):
        ospf_obj = {"router_id": None, "process_id": None, "areas": [], "interfaces": [], "neighbors": [], "dr_bdr_info": {}, "learned_prefixes": []}
    eigrp_obj = routing_raw.get("eigrp")
    if not isinstance(eigrp_obj, dict):
        eigrp_obj = {"as_number": None, "router_id": None, "neighbors": [], "hold_time": None, "learned_routes": []}
    bgp_obj = routing_raw.get("bgp")
    if not isinstance(bgp_obj, dict):
        bgp_obj = {"local_as": None, "peers": []}
    rip_obj = routing_raw.get("rip")
    if not isinstance(rip_obj, dict):
        rip_obj = {"version": None, "networks": [], "hop_count": None, "interfaces": [], "auto_summary": False, "passive_interfaces": [], "timers": {"update": 30, "invalid": 180, "garbage": 120}, "admin_distance": 100}
    # Legacy: static list and route table for backward compat
    static_raw = routing_raw.get("static") or []
    routes_from_table = routing_raw.get("routes") or []
    static_legacy = []
    for r in static_raw:
        net = r.get("network")
        if not net:
            continue
        nh = r.get("next_hop") or r.get("nexthop") or ""
        iface = r.get("interface") or ""
        static_legacy.append({"network": net, "next_hop": nh, "interface": iface})
    route_table = [{"protocol": r.get("protocol"), "network": r.get("network"), "next_hop": r.get("next_hop") or "", "interface": r.get("interface") or ""} for r in routes_from_table] if routes_from_table else []
    if not route_table and static_legacy:
        for s in static_legacy:
            route_table.append({"protocol": "S", "network": s.get("network"), "next_hop": s.get("next_hop"), "interface": s.get("interface")})
    routing = {
        "static_routes": static_routes_obj,
        "ospf": ospf_obj,
        "eigrp": eigrp_obj,
        "bgp": bgp_obj,
        "rip": rip_obj,
        "static": static_legacy,
        "routes": route_table,
    }

    # neighbors: 2.3.2.6 device_name, ip_address, platform, local_port, remote_port, capabilities, discovery_protocol
    neighbors = []
    for n in parsed.get("neighbors") or []:
        neighbors.append({
            "device_name": n.get("device_name"),
            "local_port": n.get("local_port"),
            "remote_port": n.get("remote_port"),
            "platform": n.get("platform"),
            "ip_address": n.get("ip_address"),
            "capabilities": n.get("capabilities"),
            "discovery_protocol": n.get("discovery_protocol"),
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
    audit_ntp = (sec_audit.get("ntp") or {}).get("servers")
    if isinstance(audit_ntp, list):
        for s in audit_ntp:
            if s and s not in ntp_servers:
                ntp_servers.append(s)
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

    # stp: Cisco-aligned; stp_info MUST NOT be null; root_bridges = VLAN IDs (integers) only; no stp_interfaces
    stp_raw = parsed.get("stp") or {}
    rb = stp_raw.get("root_bridge_id")
    root_bridges = [x for x in (stp_raw.get("root_bridges") or []) if isinstance(x, int)]
    raw_interfaces = stp_raw.get("interfaces") or []
    # Normalize each interface to exactly 6 fields (Cisco schema)
    def _norm_stp_iface(o: Any) -> Dict[str, Any]:
        if not isinstance(o, dict):
            return {"port": "", "role": "Designated", "state": "Forwarding", "cost": 20000, "portfast_enabled": False, "bpduguard_enabled": False}
        return {
            "port": o.get("port") if o.get("port") is not None else "",
            "role": o.get("role") if o.get("role") is not None else "Designated",
            "state": o.get("state") if o.get("state") is not None else "Forwarding",
            "cost": int(o["cost"]) if o.get("cost") is not None else 20000,
            "portfast_enabled": bool(o.get("portfast_enabled")) if o.get("portfast_enabled") is not None else False,
            "bpduguard_enabled": bool(o.get("bpduguard_enabled")) if o.get("bpduguard_enabled") is not None else False,
        }
    interfaces_list = [_norm_stp_iface(i) for i in raw_interfaces]
    stp_info_raw = stp_raw.get("stp_info")
    if stp_info_raw and isinstance(stp_info_raw, dict) and "mode" in stp_info_raw and "root_bridge" in stp_info_raw:
        stp_info = dict(stp_info_raw)
        stp_info["interfaces"] = [_norm_stp_iface(i) for i in (stp_info_raw.get("interfaces") or [])]
    else:
        root_bridge_nested = (stp_info_raw or {}).get("root_bridge") if isinstance(stp_info_raw, dict) else {}
        stp_info = {
            "mode": stp_raw.get("stp_mode") or stp_raw.get("mode") or "MSTP",
            "root_bridge": {
                "root_bridge_id": rb,
                "priority": (root_bridge_nested.get("priority") if isinstance(root_bridge_nested, dict) else None) or 32768,
                "is_local_device_root": root_bridge_nested.get("is_local_device_root", False) if isinstance(root_bridge_nested, dict) else False,
            },
            "interfaces": list(interfaces_list),
        }
    stp = {
        "stp_mode": stp_raw.get("stp_mode") or stp_raw.get("mode"),
        "root_bridges": root_bridges,
        "root_bridge_id": rb,
        "mode": stp_raw.get("stp_mode") or stp_raw.get("mode"),
        "priority": stp_info.get("root_bridge", {}).get("priority"),
        "is_root": stp_info.get("root_bridge", {}).get("is_local_device_root"),
        "bpdu_protection_global": stp_raw.get("bpduguard_enabled"),
        "portfast_enabled": stp_raw.get("portfast_enabled"),
        "bpduguard_enabled": stp_raw.get("bpduguard_enabled"),
        "interfaces": interfaces_list,
        "stp_info": stp_info,
    }

    # ha: port_channels, etherchannel, etherchannels (Cisco-aligned), hsrp, vrrp
    ha_raw = parsed.get("ha") or {}
    high_avail = parsed.get("high_availability") or {}
    ether_list = high_avail.get("ether_channels") or ha_raw.get("etherchannels") or ha_raw.get("etherchannel") or []
    port_channels = []
    etherchannels_out = []
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
            members_raw = e.get("members") or []
            members_flat = [m.get("interface", m.get("port", m)) if isinstance(m, dict) else m for m in members_raw]
            port_channels.append({
                "id": po_id or e.get("id"),
                "mode": e.get("protocol") or e.get("mode"),
                "members": members_flat,
                "status": (e.get("status") or "up").lower(),
            })
            etherchannels_out.append({
                "name": name or (f"Po{po_id}" if po_id is not None else "Po"),
                "mode": e.get("protocol") or e.get("mode"),
                "status": e.get("status") or "up",
                "members": members_raw if members_raw and isinstance(members_raw[0], dict) else [{"interface": m, "status": "Bundled"} for m in members_flat],
            })
    etherchannel = [{"name": x["name"], "mode": x["mode"], "members": x["members"], "status": x["status"]} for x in etherchannels_out]
    vrrp_list = ha_raw.get("vrrp") or []
    vrrp = []
    for v in vrrp_list if isinstance(vrrp_list, list) else []:
        if isinstance(v, dict):
            vrrp.append({"group": v.get("vrid") or v.get("group"), "virtual_ip": v.get("virtual_ip"), "interface": v.get("interface"), "state": v.get("state")})
    ha = {"port_channels": port_channels, "etherchannel": etherchannel, "etherchannels": etherchannels_out, "hsrp": ha_raw.get("hsrp") or [], "vrrp": vrrp}

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
                            "vlans": {"vlan_list": [], "total_vlan_count": 0, "details": [], "access_ports": [], "trunk_ports": []},
                            "stp": {"stp_mode": None, "root_bridges": [], "root_bridge_id": None, "mode": None, "priority": None, "is_root": None, "bpdu_protection_global": None, "portfast_enabled": None, "bpduguard_enabled": None, "interfaces": [], "stp_info": {"mode": "MSTP", "root_bridge": {"root_bridge_id": None, "priority": 32768, "is_local_device_root": False}, "interfaces": []}},
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

