"""LLM Service for Ollama Integration — Remote server, Scope 2.3.5 analysis, async httpx."""

import os
import json
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

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
# Response must be a strictly valid JSON object (no markdown, no code fences).
SYSTEM_PROMPT_PROJECT_OVERVIEW = """You are a Network Solution Architect. Review the configuration summaries of these devices collectively.

**Task:** Return a strictly valid JSON object describing the network overview. No prose, no markdown—only JSON.

**Required JSON structure (use exactly these keys):**
{
  "topology": { "type": "Star" | "Mesh" | "Tree" | "Ring" | "Hybrid", "redundancy": "High" | "Low" | "None" },
  "stats": { "core_devices": number, "distribution": number, "access": number },
  "protocols": ["OSPF", "LACP", "MSTP", ...],
  "health_status": "Healthy" | "Warning" | "Critical",
  "key_insights": ["Short bullet 1", "Short bullet 2", "Short bullet 3 or 4"],
  "recommendations": ["Actionable advice 1", "Actionable advice 2", ...]
}

- topology.type: overall topology style. redundancy: level of redundancy (High/Low/None).
- stats: counts of devices by layer (use 0 if a layer is not present).
- protocols: list of key protocols detected (routing, link aggregation, STP, etc.).
- health_status: overall network health.
- key_insights: 3–4 short bullet-point strings.
- recommendations: list of actionable recommendations (can be empty).

**CRITICAL:** Output ONLY valid JSON. No markdown, no code blocks, no text before or after the JSON object."""

# Per-Device Overview (More Detail page - Device Summary tab)
# Response must be a strictly valid JSON object (no markdown, no code fences).
SYSTEM_PROMPT_DEVICE_OVERVIEW = """You are a Network Solution Architect. Analyze this single device's configuration.

**Task:** Return a strictly valid JSON object describing the device summary. No prose, no markdown—only JSON.

**Required JSON structure (use exactly these keys):**
{
  "role": "Core" | "Access" | "Distribution" | "Edge" | "Other",
  "uptime_human": "X days, Y hours" or "N/A",
  "critical_metrics": { "cpu_load": "Low" | "Normal" | "High" | "N/A", "memory": "Low" | "Normal" | "High" | "N/A" },
  "config_highlights": ["Key config feature 1", "Key config feature 2", "3–4 short items"],
  "security_issues": ["Risk 1", "Risk 2", ...] or ["None"]
}

- role: device role in the network.
- uptime_human: human-readable uptime if available, else "N/A".
- critical_metrics: infer from config if possible; use "N/A" if unknown.
- config_highlights: 3–4 short strings of key configuration aspects (interfaces, VLANs, routing, etc.).
- security_issues: list of potential risks, or ["None"] if none found.

**CRITICAL:** Output ONLY valid JSON. No markdown, no code blocks, no text before or after the JSON object."""

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
# Network-wide: gaps, missing configs, what to add; may mention devices but NOT per-device list.
SYSTEM_PROMPT_PROJECT_RECOMMENDATIONS = """You are a Network Solution Architect. Review the configuration summaries of ALL devices in this project as ONE network.

**Task: Network-wide gap and improvement analysis (Scope 2.3.5.2)**
- Think at NETWORK level: what is missing across the project? What should be added or fixed for the whole network?
- Identify: missing or inconsistent configurations (e.g. VLAN not defined on core but used on access), security gaps (e.g. no NTP, weak auth), redundancy or best-practice gaps (e.g. no HSRP, STP disabled).
- You MAY mention specific device names when relevant (e.g. "Core-SW has no VLAN 10") but do NOT produce one recommendation per device. Output a short list of network-wide issues and what to do.
- For each item give: (1) clear issue description, (2) concrete recommendation (what to add or change). Be concise but actionable.

**Output Format:** Return ONLY valid JSON:
{
  "recommendations": [
    {
      "severity": "high|medium|low",
      "issue": "Short description of the gap or problem (network-wide or which device).",
      "recommendation": "What to add or do (specific, actionable).",
      "device": "device name if relevant, or \"all\" for network-wide"
    }
  ]
}

**CRITICAL:**
- You MUST fill both "issue" and "recommendation" for every item. Never leave them empty.
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
SYSTEM_PROMPT_CONFIG_DRIFT = """You are a Network Engineer. You compare two device output files and summarize only CONFIGURATION changes.

**Scope: Configuration only**
- Analyze ONLY the configuration section of each file. This is the part that corresponds to commands such as: show running-config, display current-configuration, show startup-config, display saved-configuration (and equivalent vendor commands).
- IGNORE and do NOT report: show version output, interface status (e.g. "current state UP/DOWN"), display device, display cpu-usage, or any other non-configuration output. Report only changes to actual configuration lines (e.g. interface settings, VLANs, ACLs, NTP, SNMP, routing config).

**Task: Config drift summary**
- Output a short list of changes: additions, removals, and modifications to the configuration only.
- For additions: what config was added (e.g. "Enabled port-security on Gi1/0/5").
- For removals: what config was removed (e.g. "Removed VLAN 40").
- For modifications: describe the config change with old → new (e.g. "NTP server 10.10.1.10 → 10.10.1.11").

**Output Format:** Return ONLY valid JSON:
{
  "changes": [
    { "type": "add", "description": "Short description of what was added" },
    { "type": "remove", "description": "Short description of what was removed" },
    { "type": "modify", "description": "What changed, use 'old_value → new_value' format" }
  ]
}

**CRITICAL:**
- "type" must be exactly "add", "remove", or "modify".
- Output ONLY JSON, no markdown, no code blocks. Parseable directly as JSON object."""


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
    MAX_INTERFACES_PER_DEVICE = 12
    MAX_NEIGHBORS_PER_DEVICE = 6
    MAX_AGGREGATED_JSON_CHARS = 45000  # truncate if larger to avoid token overflow

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
        
        # Build user prompt (truncate if too large to avoid token overflow)
        try:
            aggregated_json = json.dumps(aggregated_data, separators=(",", ":"), ensure_ascii=False, indent=2, default=str)
            if len(aggregated_json) > self.MAX_AGGREGATED_JSON_CHARS:
                aggregated_json = aggregated_json[: self.MAX_AGGREGATED_JSON_CHARS] + "\n\n[Truncated for length.]"
                logger.info("project_overview aggregated JSON truncated to %d chars", self.MAX_AGGREGATED_JSON_CHARS)
        except (TypeError, ValueError) as e:
            logger.exception("Error serializing aggregated data to JSON for project %s: %s", project_id, e)
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
Return a strictly valid JSON object with keys: topology, stats, protocols, health_status, key_insights, recommendations (as in the system prompt). No other text."""

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
                "top_p": 0.85,
                "num_predict": 1024,
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

            # Parse JSON response
            parsed_response = self._parse_json_response(ai_response)
            
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
        try:
            aggregated_data = self._prepare_aggregated_data(devices_data, project_id)
        except Exception as e:
            logger.exception("Error preparing device data for device_overview: %s", e)
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
                f"[ERROR] Failed to serialize device data: {str(e)}",
                "json_serialization_failed",
                0,
                details=str(e),
            )
        user_prompt = f"""Analyze this single device: {device_name}.

=== DEVICE CONFIGURATION ===
{aggregated_json}

=== REQUEST ===
Return a strictly valid JSON object with keys: role, uptime_human, critical_metrics, config_highlights, security_issues (as in the system prompt). No other text."""

        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT_DEVICE_OVERVIEW},
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
        Returns changes list: [{ type: "add"|"remove"|"modify", description: "..." }].
        """
        start_time = time.perf_counter()
        if not old_content or not new_content:
            return self._error_result(
                "[ERROR] Both old and new config content required.",
                "invalid_input",
                0,
            )
        # Truncate to avoid token overflow (e.g. 20k chars each)
        max_chars = 18000
        old_content = (old_content or "")[:max_chars]
        new_content = (new_content or "")[:max_chars]
        from_label = from_filename or "old"
        to_label = to_filename or "new"
        user_prompt = f"""Device: {device_name}. Compare: {from_label} → {to_label}.

Consider ONLY the configuration section in each file (e.g. output of show running-config / display current-configuration / show startup-config / display saved-configuration). Ignore version output, interface status lines, and other non-configuration output. Report only changes to actual configuration.

=== OLD FILE (previous) ===
{old_content}

=== NEW FILE (latest) ===
{new_content}

=== REQUEST ===
Summarize configuration changes only: additions, removals, modifications. For modifications use "old_value → new_value". Return ONLY valid JSON with "changes" array; each item must have "type" ("add"|"remove"|"modify") and "description"."""

        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT_CONFIG_DRIFT},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {"temperature": 0.2, "top_p": 0.85, "num_predict": 1024},
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
            validated = []
            for c in changes:
                if isinstance(c, dict) and c.get("type") and c.get("description"):
                    t = str(c.get("type", "")).lower()
                    if t in ("add", "remove", "modify"):
                        validated.append({"type": t, "description": str(c.get("description", ""))})
            return {
                "content": ai_response,
                "parsed_response": {"changes": validated},
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
        """Extract and parse JSON from LLM response (handles markdown code blocks)."""
        try:
            if "```json" in ai_response:
                start = ai_response.find("```json") + 7
                end = ai_response.find("```", start)
                return json.loads(ai_response[start:end].strip())
            if "```" in ai_response:
                start = ai_response.find("```") + 3
                end = ai_response.find("```", start)
                return json.loads(ai_response[start:end].strip())
            return json.loads(ai_response)
        except json.JSONDecodeError:
            return {"analysis": ai_response, "format": "text"}

    @staticmethod
    def _normalize_network_overview_response(data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure parsed project overview has the required JSON structure. Fill defaults for missing keys."""
        if not isinstance(data, dict):
            data = {}
        topology = data.get("topology")
        if not isinstance(topology, dict):
            topology = {"type": "Unknown", "redundancy": "Unknown"}
        stats = data.get("stats")
        if not isinstance(stats, dict):
            stats = {"core_devices": 0, "distribution": 0, "access": 0}
        protocols = data.get("protocols")
        if not isinstance(protocols, list):
            protocols = []
        health_status = data.get("health_status")
        if not isinstance(health_status, str):
            health_status = "Unknown"
        key_insights = data.get("key_insights")
        if not isinstance(key_insights, list):
            key_insights = []
        recommendations = data.get("recommendations")
        if not isinstance(recommendations, list):
            recommendations = []
        return {
            "topology": topology,
            "stats": stats,
            "protocols": protocols,
            "health_status": health_status,
            "key_insights": key_insights,
            "recommendations": recommendations,
        }

    @staticmethod
    def _normalize_device_overview_response(data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure parsed device overview has the required JSON structure. Fill defaults for missing keys."""
        if not isinstance(data, dict):
            data = {}
        role = data.get("role")
        if not isinstance(role, str):
            role = "Other"
        uptime_human = data.get("uptime_human")
        if not isinstance(uptime_human, str):
            uptime_human = "N/A"
        critical_metrics = data.get("critical_metrics")
        if not isinstance(critical_metrics, dict):
            critical_metrics = {"cpu_load": "N/A", "memory": "N/A"}
        config_highlights = data.get("config_highlights")
        if not isinstance(config_highlights, list):
            config_highlights = []
        security_issues = data.get("security_issues")
        if not isinstance(security_issues, list):
            security_issues = []
        return {
            "role": role,
            "uptime_human": uptime_human,
            "critical_metrics": critical_metrics,
            "config_highlights": config_highlights,
            "security_issues": security_issues,
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
