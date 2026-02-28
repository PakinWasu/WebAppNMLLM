"""LLM Service for Ollama Integration — Remote server, Scope 2.3.5 analysis, async httpx."""

import os
import json
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import difflib

import httpx

logger = logging.getLogger(__name__)

# Scope 2.3.5 — Strict system prompt for configuration analysis output format
SYSTEM_PROMPT_SCOPE_235 = """You are a Senior Network Security Engineer. Analyze the provided network configuration file.
Output must be in JSON format with the following keys:
- `summary`: A concise English summary of the device role and status (Scope 2.3.5.1).
- `security_risks`: A list of potential security issues (e.g., Telnet enabled, weak passwords, old firmware) (Scope 2.3.5.2).
- `device_details`: Specifics like Hostname, Management IP, and Vendor (Scope 2.3.5.3).
- `config_quality`: A score (1-10) based on best practices.

Strictly avoid hallucination. If data is missing, state 'Not found'."""

# Project-Level Analysis System Prompt - Network Overview (Scope 2.3.5.1)
SYSTEM_PROMPT_PROJECT_OVERVIEW = """You are a Senior Network Architect. Analyze the provided network device data and return a comprehensive overview.

For EACH section below, write 2-4 detailed sentences using ACTUAL values from the data (device names, IPs, VLAN IDs, protocol parameters, interface counts). Do NOT write generic statements.

Return ONLY valid JSON with these keys:
{
  "health_status": "Healthy|Warning|Critical",
  "overview": "Network architecture summary: how many devices, their roles (Core/Distribution/Access), topology design (redundant/single-path), overall health. Mention specific device names and models.",
  "interfaces": "Total interface count, how many are up vs down. Trunk vs access port distribution. Notable speed/duplex configurations. Mention specific port utilization rates.",
  "vlans": "Total VLAN count with actual VLAN IDs and names. Which VLANs are most widely deployed. Native VLAN configuration. Any VLAN inconsistencies across devices.",
  "stp": "STP mode in use (PVST/RSTP/MST). Root bridge device name and priority. Any non-default STP configurations. Potential loop risks.",
  "routing": "Which routing protocols are active (OSPF/BGP/EIGRP/RIP/Static). OSPF areas and router IDs. BGP AS numbers and peering. Route redistribution if any.",
  "security": "SSH vs Telnet status. AAA/TACACS configuration. ACL presence. Port security, DHCP snooping, 802.1X status. Password encryption. Any security concerns.",
  "ha": "High availability setup: HSRP/VRRP groups and VIPs. EtherChannel/LACP bundles. Redundant uplinks. Failover readiness.",
  "highlights": ["Key finding 1 with specific values", "Key finding 2", "Key finding 3", "Key finding 4", "Key finding 5"]
}

CRITICAL: Output ONLY valid JSON. No markdown, no code blocks. Be specific with actual values from the data."""

# Per-Device Overview (More Detail page - Device Summary tab)
SYSTEM_PROMPT_DEVICE_OVERVIEW = """You are a Network Engineer analyzing a single device configuration. Provide detailed analysis.

Return JSON with these sections (write 2-4 sentences per section):

{
  "health_status": "Healthy|Warning|Critical",
  "overview": "Device role, model, purpose in network. What layer? Core/Distribution/Access? Primary functions.",
  "interfaces": "List interface types and counts. Which are up/down? Any trunk ports? Speed/duplex settings. Notable interface configs.",
  "vlans": "List all VLANs with names/IDs. Native VLAN? Voice VLAN? How VLANs are distributed across interfaces.",
  "routing": "Which routing protocols active (OSPF/BGP/EIGRP/Static)? Router ID? Areas? Neighbors? Default route?",
  "security": "AAA config? ACLs? Port security? DHCP snooping? 802.1X? SSH/Telnet settings? Any security concerns?",
  "highlights": ["Important finding 1", "Important finding 2", "Important finding 3"]
}

Be specific with actual values from config (IPs, VLAN IDs, interface names, protocol details)."""

# Project-Level Analysis System Prompt - Full Project Analysis (Scope 2.3.5.1 & 2.3.5.2)
SYSTEM_PROMPT_FULL_PROJECT_ANALYSIS = """You are a Network Solution Architect. Analyze these network devices as a whole system.

**Task 1: Network Overview (Scope 2.3.5.1)**
- Summarize the network status concisely using **bullet points** and **bold keys** (e.g., **Architecture:**, **Topology:**).
- Do NOT use long paragraphs. One bullet per line, under 10 words per line. Example format:
  * **Architecture:** 3-Layer (Core, Dist, Access)
  * **Topology:** Dual-core redundant design
  * **Protocols:** OSPF (Active), LACP (Load Balancing)
- Output in English. The network_overview value must be a single string with newlines between each bullet line.

**Task 2: Gap & Integrity Analysis (Scope 2.3.5.2)**
- Identify MISSING configurations, security issues, and configuration inconsistencies that prevent a complete/safe topology.
- Detect patterns of error and potential problems (e.g., 'Switch A defines VLAN 10, but the Core Switch does not have VLAN 10 created', 'STP is disabled globally - risk of Loops', 'Missing NTP configuration on device X', 'Weak password policy detected').
- Provide SPECIFIC, ACTIONABLE recommendations with clear explanation:
  1. What the issue is (problem description)
  2. Why it matters (impact/risk)
  3. How to fix it (specific configuration steps or actions)
- **Constraint:** Each recommendation must be detailed and actionable. Be specific (mention device names). Format each message as: "Issue: [description]. Impact: [why it matters]. Fix: [specific steps]". Output in English.

**Output Format:** Return ONLY valid JSON:
{
  "network_overview": "string (bullet-point lines with **Bold Keys**, newline-separated)",
  "gap_analysis": [
    {
      "severity": "High|Medium|Low",
      "device": "string (device name or 'all' if global)",
      "issue": "string (specific problem description)",
      "recommendation": "string (detailed recommendation with issue, impact, and fix steps)"
    }
  ]
}

**CRITICAL:** 
- Output ONLY JSON, no markdown, no code blocks. Parseable directly as JSON object.
- All text must be in English.
- Each gap_analysis item must include severity, device, issue, and recommendation fields."""

# Project-Level Analysis System Prompt - Recommendations (Scope 2.3.5.2)
# Network-wide: gaps, missing configs, what to add; MUST specify affected devices.
SYSTEM_PROMPT_PROJECT_RECOMMENDATIONS = """You are a Network Solution Architect. Review the configuration summaries of ALL devices in this project as ONE network.

**Task: Network-wide gap and improvement analysis (Scope 2.3.5.2)**
- Think at NETWORK level: what is missing across the project? What should be added or fixed?
- Identify: missing or inconsistent configurations (e.g. VLAN not defined on core but used on access), security gaps (e.g. no NTP, weak auth), redundancy or best-practice gaps (e.g. no HSRP, STP disabled).
- **IMPORTANT:** For each recommendation, you MUST specify which device(s) are affected. List the actual device names from the config.
- For each item give: (1) clear issue description, (2) concrete recommendation (what to add or change), (3) which devices are affected.

**Output Format:** Return ONLY valid JSON:
{
  "recommendations": [
    {
      "severity": "high|medium|low",
      "issue": "Short description of the gap or problem.",
      "recommendation": "What to add or do (specific, actionable).",
      "affected_devices": ["device1", "device2"] or ["all"] if truly network-wide
    }
  ]
}

**CRITICAL:**
- You MUST fill "issue", "recommendation", AND "affected_devices" for every item. Never leave them empty.
- "affected_devices" MUST be an array of actual device names from the configuration. Use ["all"] only if the issue genuinely affects ALL devices.
- Output ONLY JSON, no markdown, no code blocks. Parseable directly as JSON object."""

# Per-Device Recommendations (More Detail page - AI Recommendations tab)
SYSTEM_PROMPT_DEVICE_RECOMMENDATIONS = """You are a Network Solution Architect. Analyze this single device's configuration.

**Task: Per-Device flaw and improvement analysis**
- Find flaws, missing configurations, security issues, and best-practice gaps for THIS device only.
- Recommend what to add or change so the device works as it should (e.g. enable NTP, harden security, fix VLAN/STP/routing).
- For each item give: (1) clear issue description, (2) concrete recommendation (what to add or change). Be concise but actionable.

**Output Format:** Return ONLY valid JSON:
{
  "recommendations": [
    {
      "severity": "high|medium|low",
      "issue": "Short description of the problem or gap for this device.",
      "recommendation": "What to add or do (specific, actionable)."
    }
  ]
}

**CRITICAL:**
- You MUST fill both "issue" and "recommendation" for every item.
- Output ONLY JSON, no markdown, no code blocks. Parseable directly as JSON object."""

# Config Drift summary (More Detail page - Config Drift tab)
SYSTEM_PROMPT_CONFIG_DRIFT = """You are a Network Engineer comparing two device configurations.
You will be given a unified diff between the OLD and NEW running configuration.

Your job is to analyze ONLY the lines shown in the diff and describe all configuration changes in detail.

**Task: Detailed configuration drift analysis**
For each change found, provide:
1. The exact section/feature affected (e.g., "interface GigabitEthernet0/0", "OSPF", "VLAN 10")
2. What specifically changed with actual values (old vs new lines)
3. Potential impact of the change
4. Overall how different the new config is from the old one as a percentage of the configuration (0–100%), based on logical changes (not just line count).

You MUST NOT invent changes that are not visible in the diff.

**Output Format:** Return ONLY valid JSON:
{
  "difference_percent": 0-100 number,
  "changes": [
    {
      "type": "add|remove|modify",
      "section": "Feature or config section name",
      "description": "Detailed description with actual config values",
      "old_value": "Previous value (for modify only, null for add)",
      "new_value": "New value (for modify/add, null for remove)"
    }
  ]
}

**Examples:**
- {"difference_percent": 12.5, "changes":[{"type":"add","section":"Interface GigabitEthernet0/1","description":"Added new interface with IP 10.0.0.1/24","old_value":null,"new_value":"ip address 10.0.0.1 255.255.255.0"}]}
- {"difference_percent": 3, "changes":[{"type":"modify","section":"NTP Configuration","description":"Changed NTP server address","old_value":"ntp server 10.10.1.10","new_value":"ntp server 10.10.1.11"}]}
- {"difference_percent": 0, "changes":[]}

**CRITICAL:**
- Always include a numeric difference_percent between 0 and 100.
- Output ONLY valid JSON, no markdown, no code blocks."""


class LLMService:
    """Service for communicating with remote Ollama API (async, non-blocking)."""

    def __init__(self):
        # Environment configuration — remote Ollama on Windows
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://10.4.15.52:11434").rstrip("/")
        self.model_name = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
        self.timeout_seconds = int(os.getenv("OLLAMA_TIMEOUT", "300"))  # 5 minutes for 16B model

    def _filter_relevant_data(self, parsed_data: Dict[str, Any], analysis_type: str) -> Dict[str, Any]:
        """Filter parsed data to include only relevant fields for the analysis type."""
        filtered = {}

        if "device_overview" in parsed_data:
            filtered["device_overview"] = parsed_data["device_overview"]

        if analysis_type == "security_audit":
            for key in ("users", "acl", "snmp", "ssh"):
                if key in parsed_data:
                    filtered[key] = parsed_data[key]
        elif analysis_type == "performance_review":
            if "interfaces" in parsed_data:
                filtered["interfaces"] = parsed_data["interfaces"][:30]
            if "stp" in parsed_data:
                filtered["stp"] = parsed_data["stp"]
            if "routing" in parsed_data:
                filtered["routing"] = parsed_data["routing"]
        elif analysis_type == "network_topology":
            if "interfaces" in parsed_data:
                filtered["interfaces"] = [
                    iface for iface in parsed_data["interfaces"][:50]
                    if iface.get("ipv4_address") or iface.get("description")
                ]
            for key in ("neighbors", "routing"):
                if key in parsed_data:
                    filtered[key] = parsed_data[key]
        else:
            for key, value in parsed_data.items():
                if isinstance(value, list) and len(value) > 50:
                    filtered[key] = value[:50]
                else:
                    filtered[key] = value

        return filtered

    def _build_user_prompt(
        self,
        parsed_data: Dict[str, Any],
        original_content: Optional[str],
        analysis_type: str,
        custom_prompt: Optional[str] = None,
    ) -> str:
        """Build user prompt with filtered data."""
        filtered = self._filter_relevant_data(parsed_data, analysis_type)
        parts = [
            "=== PARSED CONFIGURATION DATA ===",
            json.dumps(filtered, separators=(",", ":"), ensure_ascii=False),
        ]
        if original_content:
            parts.append("\n=== ORIGINAL CONFIGURATION CONTENT (REFERENCE) ===")
            parts.append(original_content[:3000])
            if len(original_content) > 3000:
                parts.append("\n[Content truncated - showing first 3000 characters]")
        parts.append("\n=== ANALYSIS REQUEST ===")
        if custom_prompt:
            parts.append(custom_prompt)
        else:
            parts.append(f"Perform {analysis_type} analysis. Return valid JSON only with keys: summary, security_risks, device_details, config_quality.")
        parts.append("Use only data from configuration above. If missing, use 'Not found'.")
        return "\n".join(parts)

    async def analyze_configuration(
        self,
        parsed_data: Dict[str, Any],
        original_content: Optional[str],
        analysis_type: str,
        device_name: str,
        custom_prompt: Optional[str] = None,
        include_original: bool = False,
    ) -> Dict[str, Any]:
        """
        Analyze network configuration (Scope 2.3.5).
        Uses strict system prompt for JSON: summary, security_risks, device_details, config_quality.
        """
        start_time = time.perf_counter()
        user_prompt = self._build_user_prompt(
            parsed_data,
            original_content if include_original else None,
            analysis_type,
            custom_prompt,
        )

        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT_SCOPE_235},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {
                "temperature": 0.3,
                "top_p": 0.85,
                "num_predict": 1024,  # Reduced from 2048 to prevent timeout
            },
        }

        try:
            async with httpx.AsyncClient(timeout=float(self.timeout_seconds)) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()

            inference_time_sec = time.perf_counter() - start_time
            inference_time_ms = inference_time_sec * 1000

            # Log every request for performance tracking
            logger.info(
                "ollama_request model_used=%s inference_time_sec=%.2f inference_time_ms=%.0f device=%s analysis_type=%s",
                self.model_name,
                inference_time_sec,
                inference_time_ms,
                device_name,
                analysis_type,
            )

            ai_response = data.get("message", {}).get("content", "")
            token_usage = {
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            }

            parsed_response = self._parse_json_response(ai_response)

            return {
                "content": ai_response,
                "parsed_response": parsed_response,
                "metrics": {
                    "inference_time_ms": inference_time_ms,
                    "token_usage": token_usage,
                    "model_name": self.model_name,
                    "timestamp": datetime.utcnow(),
                },
            }

        except httpx.ReadTimeout:
            inference_time_ms = (time.perf_counter() - start_time) * 1000
            logger.warning(
                "ollama_request timeout model_used=%s inference_time_sec=%.2f device=%s",
                self.model_name,
                (time.perf_counter() - start_time),
                device_name,
            )
            return self._error_result(
                f"[ERROR] Ollama read timeout ({self.timeout_seconds}s). Model may be slow or unresponsive.",
                "timeout",
                inference_time_ms,
            )
    
    # Limits to keep prompt size and inference time manageable
    MAX_DEVICES_AGGREGATED = 20
    MAX_INTERFACES_PER_DEVICE = 5
    MAX_NEIGHBORS_PER_DEVICE = 3
    MAX_AGGREGATED_JSON_CHARS = 8000  # very small for 7B model to avoid timeout

    def _prepare_aggregated_data(self, devices_data: List[Dict[str, Any]], project_id: str) -> Dict[str, Any]:
        """Prepare aggregated device data with size limits for stable LLM inference."""
        devices_data = devices_data[: self.MAX_DEVICES_AGGREGATED]
        aggregated_data = {
            "project_id": project_id,
            "total_devices": len(devices_data),
            "devices": [],
        }

        for device in devices_data:
            try:
                device_name = device.get("device_name")
                if not device_name:
                    continue
                interfaces = device.get("interfaces")
                if isinstance(interfaces, list):
                    interfaces = interfaces[: self.MAX_INTERFACES_PER_DEVICE]
                else:
                    interfaces = []
                neighbors = device.get("neighbors")
                if isinstance(neighbors, list):
                    neighbors = neighbors[: self.MAX_NEIGHBORS_PER_DEVICE]
                else:
                    neighbors = []
                vlans = device.get("vlans", {})
                stp = device.get("stp", {})
                routing = device.get("routing", {})
                # Keep vlans/stp/routing compact: top-level keys only or first N entries if dict/list
                if isinstance(vlans, dict) and len(vlans) > 15:
                    vlans = dict(list(vlans.items())[:15])
                if isinstance(stp, dict) and len(stp) > 10:
                    stp = dict(list(stp.items())[:10])
                if isinstance(routing, dict) and len(routing) > 10:
                    routing = dict(list(routing.items())[:10])

                device_summary = {
                    "device_name": device_name,
                    "device_overview": device.get("device_overview", {}),
                    "interfaces": interfaces,
                    "vlans": vlans,
                    "stp": stp,
                    "routing": routing,
                    "neighbors": neighbors,
                }
                aggregated_data["devices"].append(device_summary)
            except Exception as e:
                logger.warning("Error preparing device data for %s: %s", device.get("device_name", "unknown"), e)
                continue

        return aggregated_data

    async def analyze_project_overview(
        self,
        devices_data: List[Dict[str, Any]],
        project_id: str,
    ) -> Dict[str, Any]:
        """
        Analyze entire project - Network Overview only (Scope 2.3.5.1).
        Returns overview_text.
        """
        start_time = time.perf_counter()
        
        # Prepare aggregated data for all devices
        try:
            aggregated_data = self._prepare_aggregated_data(devices_data, project_id)
        except Exception as e:
            logger.exception(f"Error preparing aggregated data for project {project_id}: {e}")
            return self._error_result(
                f"[ERROR] Failed to prepare device data: {str(e)}",
                "data_preparation_failed",
                0,
                details=str(e),
            )
        
        # Build enriched summary for LLM (detailed per-device stats)
        try:
            device_summaries = []
            total_interfaces = 0
            total_up = 0
            total_down = 0
            total_trunk = 0
            total_access = 0
            all_vlans = {}  # vlan_id -> {name, devices[]}
            routing_protocols = set()
            stp_info = {}  # device -> {mode, root}
            ha_info = []  # HSRP/VRRP/EtherChannel entries
            neighbor_map = {}  # device -> [neighbor names]
            
            for device in aggregated_data.get("devices", []):
                dname = device.get("device_name", "unknown")
                overview = device.get("device_overview", {})
                ifaces = device.get("interfaces", [])
                vlans = device.get("vlans", {})
                routing = device.get("routing", {})
                stp = device.get("stp", {})
                neighbors = device.get("neighbors", [])
                
                # Interface stats
                iface_count = len(ifaces) if isinstance(ifaces, list) else 0
                up_count = sum(1 for i in ifaces if isinstance(i, dict) and i.get("oper_status") == "up") if isinstance(ifaces, list) else 0
                down_count = sum(1 for i in ifaces if isinstance(i, dict) and i.get("oper_status") == "down") if isinstance(ifaces, list) else 0
                trunk_count = sum(1 for i in ifaces if isinstance(i, dict) and i.get("port_mode") == "trunk") if isinstance(ifaces, list) else 0
                access_count = sum(1 for i in ifaces if isinstance(i, dict) and i.get("port_mode") == "access") if isinstance(ifaces, list) else 0
                total_interfaces += iface_count
                total_up += up_count
                total_down += down_count
                total_trunk += trunk_count
                total_access += access_count
                
                # VLAN details
                if isinstance(vlans, dict):
                    vlan_list = vlans.get("vlan_list", [])
                    details = vlans.get("details", [])
                    if isinstance(vlan_list, list):
                        for v in vlan_list[:30]:
                            vid = str(v.get("vlan_id", v) if isinstance(v, dict) else v)
                            vname = v.get("name", "") if isinstance(v, dict) else ""
                            if vid not in all_vlans:
                                all_vlans[vid] = {"name": vname, "devices": []}
                            all_vlans[vid]["devices"].append(dname)
                
                # Routing details
                if isinstance(routing, dict):
                    ospf = routing.get("ospf", {})
                    if ospf and isinstance(ospf, dict):
                        rid = ospf.get("router_id", "")
                        areas = list(ospf.get("areas", {}).keys()) if isinstance(ospf.get("areas"), dict) else []
                        routing_protocols.add(f"OSPF(rid={rid},areas={areas})" if rid else "OSPF")
                    bgp = routing.get("bgp", {})
                    if bgp and isinstance(bgp, dict):
                        asn = bgp.get("as_number", "")
                        routing_protocols.add(f"BGP(AS{asn})" if asn else "BGP")
                    if routing.get("eigrp"):
                        eigrp = routing["eigrp"]
                        eas = eigrp.get("as_number", "") if isinstance(eigrp, dict) else ""
                        routing_protocols.add(f"EIGRP(AS{eas})" if eas else "EIGRP")
                    if routing.get("rip"):
                        routing_protocols.add("RIP")
                    if routing.get("static_routes"):
                        sr = routing["static_routes"]
                        routing_protocols.add(f"Static({len(sr)} routes)" if isinstance(sr, list) else "Static")
                
                # STP details
                if isinstance(stp, dict) and (stp.get("mode") or stp.get("stp_mode")):
                    stp_info[dname] = {
                        "mode": stp.get("mode") or stp.get("stp_mode", "Unknown"),
                        "root": bool(stp.get("root_bridge") or stp.get("is_root")),
                    }
                
                # Neighbor info
                if isinstance(neighbors, list) and neighbors:
                    neighbor_map[dname] = [
                        n.get("device_id", n.get("neighbor", "")) for n in neighbors[:8] if isinstance(n, dict)
                    ]
                
                # Per-device summary
                dev_summary = {
                    "name": dname,
                    "model": overview.get("model", ""),
                    "vendor": device.get("vendor", ""),
                    "interfaces": f"{iface_count} total ({up_count} up, {down_count} down, {trunk_count} trunk, {access_count} access)",
                }
                device_summaries.append(dev_summary)
            
            # Build enriched summary
            compact_summary = {
                "device_count": len(device_summaries),
                "devices": device_summaries,
                "total_interfaces": total_interfaces,
                "interface_stats": {"up": total_up, "down": total_down, "trunk": total_trunk, "access": total_access},
                "vlan_count": len(all_vlans),
                "vlans": {vid: {"name": info["name"], "on_devices": info["devices"]} for vid, info in list(all_vlans.items())[:20]},
                "routing_protocols": list(routing_protocols),
                "stp": stp_info if stp_info else {"mode": "Unknown"},
                "neighbors": neighbor_map if neighbor_map else {},
                "ha": ha_info if ha_info else "No HA data",
            }
            
            aggregated_json = json.dumps(compact_summary, separators=(",", ":"), ensure_ascii=False, default=str)
            # Limit to prevent token overflow
            if len(aggregated_json) > 10000:
                aggregated_json = aggregated_json[:10000] + "...[truncated]"
            print(f"[LLM_OVERVIEW] Enriched summary size: {len(aggregated_json)} chars", flush=True)
        except (TypeError, ValueError) as e:
            logger.exception("Error creating compact summary for project %s: %s", project_id, e)
            return self._error_result(
                f"[ERROR] Failed to create summary: {str(e)}",
                "summary_creation_failed",
                0,
                details=str(e),
            )

        user_prompt = f"""Analyze this network data and provide a detailed overview for each section.

{aggregated_json}

Return ONLY valid JSON with keys: health_status, overview, interfaces, vlans, stp, routing, security, ha, highlights.
Be specific: use actual device names, VLAN IDs, IP addresses, protocol parameters from the data above."""

        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT_PROJECT_OVERVIEW},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {
                "temperature": 0.3,
                "top_p": 0.9,
                "num_predict": 3072,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=float(self.timeout_seconds)) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()

            inference_time_sec = time.perf_counter() - start_time
            inference_time_ms = inference_time_sec * 1000

            logger.info(
                "project_overview_analysis model_used=%s inference_time_sec=%.2f inference_time_ms=%.0f project_id=%s devices_count=%d",
                self.model_name,
                inference_time_sec,
                inference_time_ms,
                project_id,
                len(devices_data),
            )

            ai_response = data.get("message", {}).get("content", "")
            token_usage = {
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            }
            
            # Log raw LLM response for debugging
            print(f"[LLM_OVERVIEW_RAW] project_id={project_id} response_length={len(ai_response)}", flush=True)
            print(f"[LLM_OVERVIEW_RAW] first_2000_chars: {ai_response[:2000]}", flush=True)

            # Parse JSON response
            parsed_response = self._parse_json_response(ai_response)
            print(f"[LLM_OVERVIEW_PARSED] parsed_keys={list(parsed_response.keys()) if isinstance(parsed_response, dict) else 'not_dict'}", flush=True)
            if isinstance(parsed_response, dict) and parsed_response.get("sections"):
                print(f"[LLM_OVERVIEW_PARSED] sections_keys={list(parsed_response['sections'].keys())}", flush=True)
                for k, v in parsed_response['sections'].items():
                    print(f"[LLM_OVERVIEW_PARSED] section[{k}] summary={str(v.get('summary', ''))[:100] if isinstance(v, dict) else 'N/A'}", flush=True)
            
            if isinstance(parsed_response, dict) and parsed_response.get("format") == "text":
                logger.warning(f"Failed to parse JSON response for project overview. Raw response: {ai_response[:500]}") 
                return self._error_result(
                    f"[ERROR] LLM returned non-JSON response. Expected JSON object. Response: {ai_response[:200]}",
                    "json_parse_failed",
                    inference_time_ms,
                    details=ai_response[:500],
                )
            
            if not isinstance(parsed_response, dict):
                parsed_response = {}
            
            # Normalize to required structure (fill defaults if keys missing)
            parsed_response = self._normalize_network_overview_response(parsed_response)

            return {
                "content": ai_response,
                "parsed_response": parsed_response,
                "metrics": {
                    "inference_time_ms": inference_time_ms,
                    "token_usage": token_usage,
                    "model_name": self.model_name,
                    "timestamp": datetime.utcnow(),
                },
            }

        except httpx.ReadTimeout:
            inference_time_ms = (time.perf_counter() - start_time) * 1000
            logger.warning(
                "project_overview_analysis timeout model_used=%s inference_time_sec=%.2f project_id=%s",
                self.model_name,
                (time.perf_counter() - start_time),
                project_id,
            )
            return self._error_result(
                f"[ERROR] Ollama read timeout ({self.timeout_seconds}s). Model may be slow or unresponsive.",
                "timeout",
                inference_time_ms,
            )
        except httpx.ConnectError as e:
            inference_time_ms = (time.perf_counter() - start_time) * 1000
            logger.exception("project_overview_analysis connect_error base_url=%s error=%s", self.base_url, e)
            return self._error_result(
                f"[ERROR] Cannot connect to Ollama at {self.base_url}. Check network and OLLAMA_BASE_URL. Error: {e!s}",
                "connection_failed",
                inference_time_ms,
                details=str(e),
            )
        except httpx.HTTPStatusError as e:
            inference_time_ms = (time.perf_counter() - start_time) * 1000
            logger.warning(
                "project_overview_analysis http_error model_used=%s status=%s project_id=%s",
                self.model_name,
                e.response.status_code if e.response else None,
                project_id,
            )
            msg = f"[ERROR] Ollama API error ({e.response.status_code if e.response else 'unknown'})"
            if e.response and e.response.status_code == 404:
                msg += f"\nModel '{self.model_name}' not found. Pull it on the Ollama server: ollama pull {self.model_name}"
            return self._error_result(
                msg + (f"\nResponse: {e.response.text[:200]}" if e.response else ""),
                "http_error",
                inference_time_ms,
                status_code=e.response.status_code if e.response else None,
            )
        except Exception as e:
            inference_time_ms = (time.perf_counter() - start_time) * 1000
            logger.exception("project_overview_analysis error project_id=%s", project_id)
            return self._error_result(
                f"[ERROR] Analysis failed: {str(e)}",
                "analysis_failed",
                inference_time_ms,
                details=str(e),
            )

    async def analyze_device_overview(
        self,
        devices_data: List[Dict[str, Any]],
        project_id: str,
        device_name: str,
    ) -> Dict[str, Any]:
        """
        Analyze a single device - overview/summary only (for More Detail page).
        Returns overview_text for that device.
        """
        start_time = time.perf_counter()
        if not devices_data or not device_name:
            return self._error_result(
                "[ERROR] No device data or device_name provided.",
                "invalid_input",
                0,
            )
        # Find the specific device data
        device_data = None
        for d in devices_data:
            if d.get("device_name") == device_name:
                device_data = d
                break
        
        if not device_data:
            return self._error_result(
                f"[ERROR] Device {device_name} not found in project data.",
                "device_not_found",
                0,
            )
        
        try:
            # Build detailed device config for LLM analysis
            ifaces = device_data.get("interfaces", [])
            vlans = device_data.get("vlans", {})
            routing = device_data.get("routing", {})
            stp = device_data.get("stp", {})
            neighbors = device_data.get("neighbors", [])
            overview = device_data.get("device_overview", {})
            
            # Build device config with actual details (limit to reasonable size)
            device_config = {
                "device_name": device_name,
                "hostname": overview.get("hostname", device_name),
                "model": overview.get("model", "Unknown"),
                "os_version": overview.get("os_version", "Unknown"),
                "serial": overview.get("serial_number", "Unknown"),
            }
            
            # Include interface details (limit to 15 interfaces)
            if isinstance(ifaces, list):
                device_config["interfaces"] = []
                for iface in ifaces[:15]:
                    if isinstance(iface, dict):
                        device_config["interfaces"].append({
                            "name": iface.get("name", "Unknown"),
                            "ip": iface.get("ip_address") or iface.get("ipv4_address", ""),
                            "status": iface.get("status", ""),
                            "description": iface.get("description", ""),
                            "vlan": iface.get("access_vlan") or iface.get("native_vlan", ""),
                            "mode": iface.get("switchport_mode", ""),
                            "speed": iface.get("speed", ""),
                        })
            
            # Include VLAN details
            if isinstance(vlans, dict):
                device_config["vlans"] = {}
                for vid, vinfo in list(vlans.items())[:20]:
                    if isinstance(vinfo, dict):
                        device_config["vlans"][vid] = {
                            "name": vinfo.get("name", ""),
                            "status": vinfo.get("status", "active"),
                        }
                    else:
                        device_config["vlans"][vid] = {"name": str(vinfo)}
            elif isinstance(vlans, list):
                device_config["vlans"] = vlans[:20]
            
            # Include routing details
            if isinstance(routing, dict):
                device_config["routing"] = {}
                if routing.get("ospf"):
                    ospf = routing["ospf"]
                    device_config["routing"]["ospf"] = {
                        "router_id": ospf.get("router_id", ""),
                        "areas": list(ospf.get("areas", {}).keys()) if isinstance(ospf.get("areas"), dict) else [],
                        "networks": ospf.get("networks", [])[:5],
                    }
                if routing.get("bgp"):
                    bgp = routing["bgp"]
                    device_config["routing"]["bgp"] = {
                        "as_number": bgp.get("as_number", ""),
                        "router_id": bgp.get("router_id", ""),
                        "neighbors": [n.get("ip", n) if isinstance(n, dict) else n for n in bgp.get("neighbors", [])[:5]],
                    }
                if routing.get("eigrp"):
                    device_config["routing"]["eigrp"] = routing["eigrp"]
                if routing.get("static_routes"):
                    device_config["routing"]["static_routes"] = routing["static_routes"][:10]
            
            # Include STP details
            if isinstance(stp, dict) and stp:
                device_config["stp"] = {
                    "mode": stp.get("mode", "Unknown"),
                    "root_bridge": stp.get("root_bridge", False),
                }
            
            # Include neighbors
            if isinstance(neighbors, list) and neighbors:
                device_config["neighbors"] = [
                    {"name": n.get("device_id", n.get("neighbor", "")), "port": n.get("local_interface", "")}
                    for n in neighbors[:10] if isinstance(n, dict)
                ]
            
            aggregated_json = json.dumps(device_config, indent=2, ensure_ascii=False, default=str)
            # Limit size but keep enough detail
            if len(aggregated_json) > 12000:
                aggregated_json = aggregated_json[:12000] + "\n...[truncated]"
            print(f"[LLM_DEVICE_OVERVIEW] Device {device_name} config size: {len(aggregated_json)} chars", flush=True)
        except (TypeError, ValueError) as e:
            logger.exception("Error creating device config: %s", e)
            return self._error_result(
                f"[ERROR] Failed to create device config: {str(e)}",
                "config_creation_failed",
                0,
                details=str(e),
            )
        
        user_prompt = f"""Analyze this device configuration in detail:

{aggregated_json}

Provide detailed analysis for each section. Be specific with actual values from the config."""

        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT_DEVICE_OVERVIEW},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {"temperature": 0.4, "top_p": 0.9, "num_predict": 2048},
        }
        try:
            async with httpx.AsyncClient(timeout=float(self.timeout_seconds)) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
            inference_time_sec = time.perf_counter() - start_time
            inference_time_ms = inference_time_sec * 1000
            token_usage = {
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            }
            ai_response = data.get("message", {}).get("content", "")
            parsed_response = self._parse_json_response(ai_response)
            if isinstance(parsed_response, dict) and parsed_response.get("format") == "text":
                parsed_response = {}
            if not isinstance(parsed_response, dict):
                parsed_response = {}
            parsed_response = self._normalize_device_overview_response(parsed_response)
            logger.info(
                "device_overview_analysis model_used=%s inference_time_ms=%.0f project_id=%s device_name=%s",
                self.model_name, inference_time_ms, project_id, device_name,
            )
            return {
                "content": ai_response,
                "parsed_response": parsed_response,
                "metrics": {
                    "inference_time_ms": inference_time_ms,
                    "token_usage": token_usage,
                    "model_name": self.model_name,
                    "timestamp": datetime.utcnow(),
                },
            }
        except Exception as e:
            inference_time_ms = (time.perf_counter() - start_time) * 1000
            logger.exception("device_overview_analysis error project_id=%s device_name=%s", project_id, device_name)
            return self._error_result(
                f"[ERROR] Device analysis failed: {str(e)}",
                "analysis_failed",
                inference_time_ms,
                details=str(e),
            )

    async def analyze_project_recommendations(
        self,
        devices_data: List[Dict[str, Any]],
        project_id: str,
    ) -> Dict[str, Any]:
        """
        Analyze entire project - Recommendations only (Scope 2.3.5.2).
        Returns recommendations list.
        """
        start_time = time.perf_counter()
        
        # Prepare aggregated data for all devices
        try:
            aggregated_data = self._prepare_aggregated_data(devices_data, project_id)
        except Exception as e:
            logger.exception(f"Error preparing aggregated data for project {project_id}: {e}")
            return self._error_result(
                f"[ERROR] Failed to prepare device data: {str(e)}",
                "data_preparation_failed",
                0,
                details=str(e),
            )
        
        # Build user prompt (truncate if too large)
        try:
            aggregated_json = json.dumps(aggregated_data, separators=(",", ":"), ensure_ascii=False, indent=2, default=str)
            if len(aggregated_json) > self.MAX_AGGREGATED_JSON_CHARS:
                aggregated_json = aggregated_json[: self.MAX_AGGREGATED_JSON_CHARS] + "\n\n[Truncated for length.]"
                logger.info("project_recommendations aggregated JSON truncated to %d chars", self.MAX_AGGREGATED_JSON_CHARS)
        except (TypeError, ValueError) as e:
            logger.exception("Error serializing aggregated data to JSON for project %s: %s", project_id, e)
            return self._error_result(
                f"[ERROR] Failed to serialize device data to JSON: {str(e)}",
                "json_serialization_failed",
                0,
                details=str(e),
            )

        user_prompt = f"""Analyze the following network project with {len(devices_data)} devices as ONE network.

=== AGGREGATED DEVICE CONFIGURATIONS ===
{aggregated_json}

=== ANALYSIS REQUEST ===
Give a NETWORK-WIDE gap and improvement list: what is missing or should be added across the project (e.g. missing VLANs on core, no NTP, weak security). You may mention specific devices when relevant but do NOT list one item per device. For each item provide "issue" (what is wrong or missing) and "recommendation" (what to do). Return ONLY valid JSON with "recommendations" array; each item must have "severity", "issue", "recommendation", and "device" (or "all")."""

        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT_PROJECT_RECOMMENDATIONS},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {
                "temperature": 0.3,
                "top_p": 0.85,
                "num_predict": 1024,  # Reduced from 2048 to prevent timeout
            },
        }

        try:
            async with httpx.AsyncClient(timeout=float(self.timeout_seconds)) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()

            inference_time_sec = time.perf_counter() - start_time
            inference_time_ms = inference_time_sec * 1000

            logger.info(
                "project_recommendations_analysis model_used=%s inference_time_sec=%.2f inference_time_ms=%.0f project_id=%s devices_count=%d",
                self.model_name,
                inference_time_sec,
                inference_time_ms,
                project_id,
                len(devices_data),
            )

            ai_response = data.get("message", {}).get("content", "")
            token_usage = {
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            }

            # Parse JSON response
            parsed_response = self._parse_json_response(ai_response)
            
            # Check if JSON parsing failed (returns fallback format)
            if isinstance(parsed_response, dict) and parsed_response.get("format") == "text":
                # JSON parsing failed, treat as error
                logger.warning(f"Failed to parse JSON response for project recommendations. Raw response: {ai_response[:500]}")
                return self._error_result(
                    f"[ERROR] LLM returned non-JSON response. Expected JSON with 'recommendations' key. Response: {ai_response[:200]}",
                    "json_parse_failed",
                    inference_time_ms,
                    details=ai_response[:500],
                )
            
            # Ensure required fields exist
            if not isinstance(parsed_response, dict):
                parsed_response = {}
            
            if "recommendations" not in parsed_response:
                logger.warning(f"LLM response missing 'recommendations' key. Response: {parsed_response}")
                parsed_response["recommendations"] = []

            return {
                "content": ai_response,
                "parsed_response": parsed_response,
                "metrics": {
                    "inference_time_ms": inference_time_ms,
                    "token_usage": token_usage,
                    "model_name": self.model_name,
                    "timestamp": datetime.utcnow(),
                },
            }

        except httpx.ReadTimeout:
            inference_time_ms = (time.perf_counter() - start_time) * 1000
            logger.warning(
                "project_recommendations_analysis timeout model_used=%s inference_time_sec=%.2f project_id=%s",
                self.model_name,
                (time.perf_counter() - start_time),
                project_id,
            )
            return self._error_result(
                f"[ERROR] Ollama read timeout ({self.timeout_seconds}s). Model may be slow or unresponsive.",
                "timeout",
                inference_time_ms,
            )
        except httpx.ConnectError as e:
            inference_time_ms = (time.perf_counter() - start_time) * 1000
            logger.exception("project_recommendations_analysis connect_error base_url=%s error=%s", self.base_url, e)
            return self._error_result(
                f"[ERROR] Cannot connect to Ollama at {self.base_url}. Check network and OLLAMA_BASE_URL. Error: {e!s}",
                "connection_failed",
                inference_time_ms,
                details=str(e),
            )
        except httpx.HTTPStatusError as e:
            inference_time_ms = (time.perf_counter() - start_time) * 1000
            logger.warning(
                "project_recommendations_analysis http_error model_used=%s status=%s project_id=%s",
                self.model_name,
                e.response.status_code if e.response else None,
                project_id,
            )
            msg = f"[ERROR] Ollama API error ({e.response.status_code if e.response else 'unknown'})"
            if e.response and e.response.status_code == 404:
                msg += f"\nModel '{self.model_name}' not found. Pull it on the Ollama server: ollama pull {self.model_name}"
            return self._error_result(
                msg + (f"\nResponse: {e.response.text[:200]}" if e.response else ""),
                "http_error",
                inference_time_ms,
                status_code=e.response.status_code if e.response else None,
            )
        except Exception as e:
            inference_time_ms = (time.perf_counter() - start_time) * 1000
            logger.exception("project_recommendations_analysis error project_id=%s", project_id)
            return self._error_result(
                f"[ERROR] Analysis failed: {str(e)}",
                "analysis_failed",
                inference_time_ms,
                details=str(e),
            )

    async def analyze_device_recommendations(
        self,
        devices_data: List[Dict[str, Any]],
        project_id: str,
        device_name: str,
    ) -> Dict[str, Any]:
        """
        Analyze a single device for flaws and recommendations (More Detail - AI Recommendations tab).
        Returns recommendations list for this device only.
        """
        start_time = time.perf_counter()
        if not devices_data or not device_name:
            return self._error_result(
                "[ERROR] No device data or device_name provided.",
                "invalid_input",
                0,
            )
        try:
            aggregated_data = self._prepare_aggregated_data(devices_data, project_id)
        except Exception as e:
            logger.exception("Error preparing device data for device_recommendations: %s", e)
            return self._error_result(
                f"[ERROR] Failed to prepare device data: {str(e)}",
                "data_preparation_failed",
                0,
                details=str(e),
            )
        try:
            aggregated_json = json.dumps(aggregated_data, separators=(",", ":"), ensure_ascii=False, indent=2, default=str)
            if len(aggregated_json) > self.MAX_AGGREGATED_JSON_CHARS:
                aggregated_json = aggregated_json[: self.MAX_AGGREGATED_JSON_CHARS] + "\n\n[Truncated.]"
        except (TypeError, ValueError) as e:
            logger.exception("Error serializing device data to JSON: %s", e)
            return self._error_result(
                f"[ERROR] Failed to serialize device data to JSON: {str(e)}",
                "json_serialization_failed",
                0,
                details=str(e),
            )
        user_prompt = f"""Analyze this single device: {device_name}. Find flaws and recommend improvements so the config works as it should.

=== DEVICE CONFIGURATION ===
{aggregated_json}

=== REQUEST ===
List issues and actionable recommendations for this device only. Return ONLY valid JSON with "recommendations" array; each item must have "severity", "issue", and "recommendation"."""

        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT_DEVICE_RECOMMENDATIONS},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {"temperature": 0.3, "top_p": 0.85, "num_predict": 1024},
        }
        try:
            async with httpx.AsyncClient(timeout=float(self.timeout_seconds)) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
            inference_time_ms = (time.perf_counter() - start_time) * 1000
            ai_response = data.get("message", {}).get("content", "")
            token_usage = {
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            }
            parsed_response = self._parse_json_response(ai_response)
            if isinstance(parsed_response, dict) and parsed_response.get("format") == "text":
                logger.warning("Failed to parse JSON for device recommendations. Raw: %s", ai_response[:500])
                return self._error_result(
                    "[ERROR] LLM returned non-JSON. Expected JSON with 'recommendations' key.",
                    "json_parse_failed",
                    inference_time_ms,
                    details=ai_response[:500],
                )
            if not isinstance(parsed_response, dict):
                parsed_response = {}
            if "recommendations" not in parsed_response:
                parsed_response["recommendations"] = []
            return {
                "content": ai_response,
                "parsed_response": parsed_response,
                "metrics": {
                    "inference_time_ms": inference_time_ms,
                    "token_usage": token_usage,
                    "model_name": self.model_name,
                    "timestamp": datetime.utcnow(),
                },
            }
        except httpx.ReadTimeout:
            inference_time_ms = (time.perf_counter() - start_time) * 1000
            return self._error_result("[ERROR] Ollama read timeout.", "timeout", inference_time_ms)
        except httpx.ConnectError as e:
            inference_time_ms = (time.perf_counter() - start_time) * 1000
            return self._error_result(f"[ERROR] Cannot connect to Ollama: {e!s}", "connection_failed", inference_time_ms)
        except Exception as e:
            inference_time_ms = (time.perf_counter() - start_time) * 1000
            logger.exception("device_recommendations_analysis error project_id=%s device_name=%s", project_id, device_name)
            return self._error_result(f"[ERROR] Analysis failed: {str(e)}", "analysis_failed", inference_time_ms, details=str(e))

    @staticmethod
    def _extract_running_config(content: str) -> str:
        """
        Extract only the running-config / current-configuration section from device output.
        Supports Cisco (show running-config) and Huawei (display current-configuration) formats.
        """
        if not content:
            return ""
        
        lines = content.split('\n')
        config_lines = []
        in_config = False
        config_start_patterns = [
            'show running-config',
            'show startup-config',
            'display current-configuration',
            'display saved-configuration',
            'Building configuration...',
            'Current configuration :',
            '[V200R',  # Huawei config start
        ]
        config_end_patterns = [
            '#show ',
            '#display ',
            '<',  # Huawei prompt like <EDGE1>
            'end',
        ]
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Check for config start
            if not in_config:
                for pattern in config_start_patterns:
                    if pattern in line:
                        in_config = True
                        # For Huawei [V200R...], include this line
                        if line_stripped.startswith('[V'):
                            config_lines.append(line)
                        break
                continue
            
            # Check for config end
            if in_config:
                # Cisco "end" command
                if line_stripped == 'end':
                    config_lines.append(line)
                    break
                # Huawei "return" command
                if line_stripped == 'return':
                    config_lines.append(line)
                    break
                # New command prompt (end of config output)
                if line_stripped.startswith('<') and line_stripped.endswith('>'):
                    break
                if line_stripped.endswith('#show ') or line_stripped.endswith('#display '):
                    break
                # New show/display command
                if '#show ' in line_stripped or '#display ' in line_stripped:
                    break
                
                config_lines.append(line)
        
        extracted = '\n'.join(config_lines).strip()
        # If extraction failed, return original (truncated)
        if len(extracted) < 100:
            return content
        return extracted

    async def analyze_config_drift(
        self,
        old_content: str,
        new_content: str,
        device_name: str,
        from_filename: Optional[str] = None,
        to_filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Summarize configuration drift between two configs (More Detail - Config Drift tab).
        Returns changes list: [{ type: "add"|"remove"|"modify", section, description, old_value, new_value }].
        """
        start_time = time.perf_counter()
        if not old_content or not new_content:
            return self._error_result(
                "[ERROR] Both old and new config content required.",
                "invalid_input",
                0,
            )

        # Extract only running-config section from each file
        old_config = self._extract_running_config(old_content)
        new_config = self._extract_running_config(new_content)

        print(f"[CONFIG_DRIFT] Original sizes: old={len(old_content)}, new={len(new_content)}", flush=True)
        print(f"[CONFIG_DRIFT] Extracted config sizes: old={len(old_config)}, new={len(new_config)}", flush=True)

        # Truncate to avoid token overflow
        max_chars = 15000
        old_config = old_config[:max_chars]
        new_config = new_config[:max_chars]

        from_label = from_filename or "old"
        to_label = to_filename or "new"

        # Build unified diff so the LLM sees the exact line-level changes
        old_lines = old_config.splitlines()
        new_lines = new_config.splitlines()
        diff_lines = list(
            difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile=from_label,
                tofile=to_label,
                lineterm="",
            )
        )
        diff_text = "\n".join(diff_lines)

        # If there is no diff after extraction, short‑circuit without calling the LLM
        if not diff_text.strip():
            inference_time_ms = (time.perf_counter() - start_time) * 1000
            return {
                "content": "",
                "parsed_response": {"changes": [], "difference_percent": 0.0},
                "metrics": {
                    "inference_time_ms": inference_time_ms,
                    "token_usage": {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                    },
                    "model_name": self.model_name,
                    "timestamp": datetime.utcnow(),
                },
            }

        user_prompt = f"""Device: {device_name}
Compare: {from_label} → {to_label}

The following is a unified diff between the OLD and NEW running configuration.
Lines starting with '-' exist only in the OLD config.
Lines starting with '+' exist only in the NEW config.

=== UNIFIED DIFF ===
{diff_text}

=== TASK ===
Using ONLY the diff above, list all configuration changes (additions, removals, modifications).
Treat each related group of +/- lines inside the same logical section (for example, a specific interface, routing process, or ACL) as one change item.

For each change, provide: section name (e.g., "interface GigabitEthernet0/0", "OSPF"), 
a detailed description with actual old and new CLI lines, old_value, and new_value.
Return ONLY valid JSON."""

        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT_CONFIG_DRIFT},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {"temperature": 0.3, "top_p": 0.9, "num_predict": 2048},
        }
        try:
            async with httpx.AsyncClient(timeout=float(self.timeout_seconds)) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
            inference_time_ms = (time.perf_counter() - start_time) * 1000
            ai_response = data.get("message", {}).get("content", "")
            token_usage = {
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            }
            parsed_response = self._parse_json_response(ai_response)
            if isinstance(parsed_response, dict) and parsed_response.get("format") == "text":
                logger.warning("Failed to parse JSON for config drift. Raw: %s", ai_response[:500])
                return self._error_result(
                    "[ERROR] LLM returned non-JSON. Expected JSON with 'changes' key.",
                    "json_parse_failed",
                    inference_time_ms,
                    details=ai_response[:500],
                )
            if not isinstance(parsed_response, dict):
                parsed_response = {}
            changes = parsed_response.get("changes") or []
            if not isinstance(changes, list):
                changes = []

            # Validate changes list
            validated = []
            for c in changes:
                if isinstance(c, dict) and c.get("type"):
                    t = str(c.get("type", "")).lower()
                    if t in ("add", "remove", "modify"):
                        validated.append({
                            "type": t,
                            "section": str(c.get("section", "Configuration")),
                            "description": str(c.get("description", "")),
                            "old_value": c.get("old_value"),
                            "new_value": c.get("new_value"),
                        })

            # Extract and normalize difference_percent (0–100)
            diff_raw = parsed_response.get("difference_percent")
            difference_percent: Optional[float] = None
            try:
                if isinstance(diff_raw, (int, float)):
                    val = float(diff_raw)
                elif isinstance(diff_raw, str) and diff_raw.strip():
                    # Strip potential % sign
                    val = float(diff_raw.strip().replace("%", ""))
                else:
                    val = None
                if val is not None and 0.0 <= val <= 100.0:
                    difference_percent = round(val, 2)
            except (ValueError, TypeError):
                difference_percent = None

            return {
                "content": ai_response,
                "parsed_response": {"changes": validated, "difference_percent": difference_percent},
                "metrics": {
                    "inference_time_ms": inference_time_ms,
                    "token_usage": token_usage,
                    "model_name": self.model_name,
                    "timestamp": datetime.utcnow(),
                },
            }
        except httpx.ReadTimeout:
            inference_time_ms = (time.perf_counter() - start_time) * 1000
            return self._error_result("[ERROR] Ollama read timeout.", "timeout", inference_time_ms)
        except httpx.ConnectError as e:
            inference_time_ms = (time.perf_counter() - start_time) * 1000
            return self._error_result(f"[ERROR] Cannot connect to Ollama: {e!s}", "connection_failed", inference_time_ms)
        except Exception as e:
            inference_time_ms = (time.perf_counter() - start_time) * 1000
            logger.exception("config_drift_analysis error device_name=%s", device_name)
            return self._error_result(f"[ERROR] Analysis failed: {str(e)}", "analysis_failed", inference_time_ms, details=str(e))

    async def analyze_full_project(
        self,
        devices_data: List[Dict[str, Any]],
        project_id: str,
    ) -> Dict[str, Any]:
        """
        Full Project Analysis - Network Overview + Gap Analysis (Scope 2.3.5.1 & 2.3.5.2).
        Returns network_overview and gap_analysis.
        """
        start_time = time.perf_counter()
        
        # Prepare aggregated data for all devices
        try:
            aggregated_data = self._prepare_aggregated_data(devices_data, project_id)
        except Exception as e:
            logger.exception(f"Error preparing aggregated data for project {project_id}: {e}")
            return self._error_result(
                f"[ERROR] Failed to prepare device data: {str(e)}",
                "data_preparation_failed",
                0,
                details=str(e),
            )
        
        # Build user prompt
        try:
            aggregated_json = json.dumps(aggregated_data, separators=(",", ":"), ensure_ascii=False, indent=2, default=str)
        except (TypeError, ValueError) as e:
            logger.exception(f"Error serializing aggregated data to JSON for project {project_id}: {e}")
            return self._error_result(
                f"[ERROR] Failed to serialize device data to JSON: {str(e)}",
                "json_serialization_failed",
                0,
                details=str(e),
            )
        
        user_prompt = f"""Analyze the following network project with {len(devices_data)} devices.

=== AGGREGATED DEVICE CONFIGURATIONS ===
{aggregated_json}

=== ANALYSIS REQUEST ===
Perform comprehensive project-level analysis:
1. Network Overview: Provide executive summary of architecture, topology style, and key protocols.
2. Gap & Integrity Analysis: Identify missing configurations, errors, and suggest specific actionable fixes.

Return ONLY valid JSON with 'network_overview' and 'gap_analysis' keys as specified in system prompt."""

        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT_FULL_PROJECT_ANALYSIS},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {
                "temperature": 0.3,
                "top_p": 0.85,
                "num_predict": 1536,  # Reduced from 3072 to prevent timeout
            },
        }

        try:
            async with httpx.AsyncClient(timeout=float(self.timeout_seconds)) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()

            inference_time_sec = time.perf_counter() - start_time
            inference_time_ms = inference_time_sec * 1000

            logger.info(
                "full_project_analysis model_used=%s inference_time_sec=%.2f inference_time_ms=%.0f project_id=%s devices_count=%d",
                self.model_name,
                inference_time_sec,
                inference_time_ms,
                project_id,
                len(devices_data),
            )

            ai_response = data.get("message", {}).get("content", "")
            token_usage = {
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            }

            # Parse JSON response
            parsed_response = self._parse_json_response(ai_response)
            
            # Check if JSON parsing failed (returns fallback format)
            if isinstance(parsed_response, dict) and parsed_response.get("format") == "text":
                # JSON parsing failed, treat as error
                logger.warning(f"Failed to parse JSON response for full project analysis. Raw response: {ai_response[:500]}")
                return self._error_result(
                    f"[ERROR] LLM returned non-JSON response. Expected JSON with 'network_overview' and 'gap_analysis' keys. Response: {ai_response[:200]}",
                    "json_parse_failed",
                    inference_time_ms,
                    details=ai_response[:500],
                )
            
            # Ensure required fields exist
            if not isinstance(parsed_response, dict):
                parsed_response = {}
            
            if "network_overview" not in parsed_response:
                logger.warning(f"LLM response missing 'network_overview' key. Response: {parsed_response}")
                parsed_response["network_overview"] = "Analysis completed. Network overview not provided."
            
            if "gap_analysis" not in parsed_response:
                logger.warning(f"LLM response missing 'gap_analysis' key. Response: {parsed_response}")
                parsed_response["gap_analysis"] = []

            return {
                "content": ai_response,
                "parsed_response": parsed_response,
                "metrics": {
                    "inference_time_ms": inference_time_ms,
                    "token_usage": token_usage,
                    "model_name": self.model_name,
                    "timestamp": datetime.utcnow(),
                },
            }

        except httpx.ReadTimeout:
            inference_time_ms = (time.perf_counter() - start_time) * 1000
            logger.warning(
                "full_project_analysis timeout model_used=%s inference_time_sec=%.2f project_id=%s",
                self.model_name,
                (time.perf_counter() - start_time),
                project_id,
            )
            return self._error_result(
                f"[ERROR] Ollama read timeout ({self.timeout_seconds}s). Model may be slow or unresponsive.",
                "timeout",
                inference_time_ms,
            )
        except httpx.ConnectError as e:
            inference_time_ms = (time.perf_counter() - start_time) * 1000
            logger.exception("full_project_analysis connect_error base_url=%s error=%s", self.base_url, e)
            return self._error_result(
                f"[ERROR] Cannot connect to Ollama at {self.base_url}. Check network and OLLAMA_BASE_URL. Error: {e!s}",
                "connection_failed",
                inference_time_ms,
                details=str(e),
            )
        except httpx.HTTPStatusError as e:
            inference_time_ms = (time.perf_counter() - start_time) * 1000
            logger.warning(
                "full_project_analysis http_error model_used=%s status=%s project_id=%s",
                self.model_name,
                e.response.status_code if e.response else None,
                project_id,
            )
            msg = f"[ERROR] Ollama API error ({e.response.status_code if e.response else 'unknown'})"
            if e.response and e.response.status_code == 404:
                msg += f"\nModel '{self.model_name}' not found. Pull it on the Ollama server: ollama pull {self.model_name}"
            return self._error_result(
                msg + (f"\nResponse: {e.response.text[:200]}" if e.response else ""),
                "http_error",
                inference_time_ms,
                status_code=e.response.status_code if e.response else None,
            )
        except Exception as e:
            inference_time_ms = (time.perf_counter() - start_time) * 1000
            logger.exception("full_project_analysis error project_id=%s", project_id)
            return self._error_result(
                f"[ERROR] Analysis failed: {str(e)}",
                "analysis_failed",
                inference_time_ms,
                details=str(e),
            )

    def _parse_json_response(self, ai_response: str) -> Optional[Dict[str, Any]]:
        """Extract and parse JSON from LLM response (handles markdown code blocks and text before JSON)."""
        try:
            # Try markdown code blocks first
            if "```json" in ai_response:
                start = ai_response.find("```json") + 7
                end = ai_response.find("```", start)
                return json.loads(ai_response[start:end].strip())
            if "```" in ai_response:
                start = ai_response.find("```") + 3
                end = ai_response.find("```", start)
                return json.loads(ai_response[start:end].strip())
            
            # Try to find JSON object in response (handles text before/after JSON)
            # Find first { and last }
            first_brace = ai_response.find("{")
            last_brace = ai_response.rfind("}")
            if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                json_str = ai_response[first_brace:last_brace + 1]
                return json.loads(json_str)
            
            # Try direct parse
            return json.loads(ai_response)
        except json.JSONDecodeError:
            return {"analysis": ai_response, "format": "text"}

    @staticmethod
    def _normalize_network_overview_response(data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize LLM response to simple section format for frontend display."""
        if not isinstance(data, dict):
            data = {}
        
        health_status = data.get("health_status", "Unknown")
        if not isinstance(health_status, str):
            health_status = "Unknown"
        
        # Simple format: convert flat fields to sections for display
        section_keys = ["overview", "interfaces", "vlans", "stp", "routing", "security", "ha"]
        section_titles = {
            "overview": "Network Overview",
            "interfaces": "Interfaces", 
            "vlans": "VLANs",
            "stp": "Spanning Tree (STP)",
            "routing": "Routing",
            "security": "Security",
            "ha": "High Availability"
        }
        
        sections = {}
        for key in section_keys:
            value = data.get(key, "")
            if isinstance(value, str) and value.strip():
                sections[key] = {
                    "title": section_titles.get(key, key.title()),
                    "summary": value,
                    "highlights": []
                }
            elif isinstance(value, dict):
                sections[key] = {
                    "title": value.get("title") or section_titles.get(key, key.title()),
                    "summary": value.get("summary", ""),
                    "highlights": value.get("highlights", []) if isinstance(value.get("highlights"), list) else []
                }
        
        # Add highlights to overview if present at top level
        highlights = data.get("highlights", [])
        if isinstance(highlights, list) and highlights:
            if "overview" in sections:
                sections["overview"]["highlights"] = highlights
            else:
                sections["overview"] = {
                    "title": "Network Overview",
                    "summary": data.get("overview", "Network analysis complete"),
                    "highlights": highlights
                }
        
        # Fallback: if still no sections, try legacy format
        if not sections:
            topology = data.get("topology", {})
            key_insights = data.get("key_insights", [])
            if isinstance(topology, dict) or isinstance(key_insights, list):
                return {
                    "topology": topology if isinstance(topology, dict) else {"type": "Unknown"},
                    "stats": data.get("stats", {}),
                    "protocols": data.get("protocols", []),
                    "health_status": health_status,
                    "key_insights": key_insights if isinstance(key_insights, list) else [],
                    "recommendations": data.get("recommendations", []),
                    "format": "legacy"
                }
        
        return {
            "health_status": health_status,
            "sections": sections,
            "format": "sections"
        }

    @staticmethod
    def _normalize_device_overview_response(data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize LLM response to section format for device overview display (same as project overview)."""
        if not isinstance(data, dict):
            data = {}
        
        health_status = data.get("health_status", "Unknown")
        if not isinstance(health_status, str):
            health_status = "Unknown"
        
        # Convert flat fields to sections for display (same format as project overview)
        section_keys = ["overview", "interfaces", "vlans", "routing", "security"]
        section_titles = {
            "overview": "Device Overview",
            "interfaces": "Interfaces",
            "vlans": "VLANs",
            "routing": "Routing",
            "security": "Security"
        }
        
        sections = {}
        for key in section_keys:
            value = data.get(key, "")
            if isinstance(value, str) and value.strip():
                sections[key] = {
                    "title": section_titles.get(key, key.title()),
                    "summary": value,
                    "highlights": []
                }
            elif isinstance(value, dict):
                sections[key] = {
                    "title": value.get("title") or section_titles.get(key, key.title()),
                    "summary": value.get("summary", ""),
                    "highlights": value.get("highlights", []) if isinstance(value.get("highlights"), list) else []
                }
        
        # Add highlights to overview if present at top level
        highlights = data.get("highlights", [])
        if isinstance(highlights, list) and highlights:
            if "overview" in sections:
                sections["overview"]["highlights"] = highlights
            else:
                sections["overview"] = {
                    "title": "Device Overview",
                    "summary": data.get("overview", "Device analysis complete"),
                    "highlights": highlights
                }
        
        # Fallback: legacy format support
        if not sections:
            role = data.get("role", "Other")
            config_highlights = data.get("config_highlights", [])
            security_issues = data.get("security_issues", [])
            if role or config_highlights or security_issues:
                return {
                    "role": role,
                    "uptime_human": data.get("uptime_human", "N/A"),
                    "critical_metrics": data.get("critical_metrics", {}),
                    "config_highlights": config_highlights if isinstance(config_highlights, list) else [],
                    "security_issues": security_issues if isinstance(security_issues, list) else [],
                    "format": "legacy"
                }
        
        return {
            "health_status": health_status,
            "sections": sections,
            "format": "sections"
        }

    def _error_result(
        self,
        content: str,
        error_kind: str,
        inference_time_ms: float,
        details: Optional[str] = None,
        status_code: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Build error result with metrics."""
        parsed = {"error": error_kind}
        if details:
            parsed["details"] = details
        if status_code is not None:
            parsed["status_code"] = status_code
        return {
            "content": content,
            "parsed_response": parsed,
            "metrics": {
                "inference_time_ms": inference_time_ms,
                "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "model_name": self.model_name,
                "timestamp": datetime.utcnow(),
            },
        }


# Singleton instance
llm_service = LLMService()
