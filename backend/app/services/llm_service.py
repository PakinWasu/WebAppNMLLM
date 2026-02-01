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
SYSTEM_PROMPT_PROJECT_OVERVIEW = """You are a Network Solution Architect. Review the configuration summaries of these devices collectively.

**Task: Network Overview (Scope 2.3.5.1)**
- Provide a concise, executive summary of the entire network architecture.
- Mention the topology style (e.g., Star, Ring, Core-Dist-Access).
- List key protocols detected globally (e.g., 'OSPF Area 0 is used for core routing', 'HSRP is active on Core switches').
- **Constraint:** Keep it between 3-5 sentences. Professional and descriptive.

**Output Format:** Return ONLY valid JSON:
{
  "overview_text": "string (3-5 sentences)"
}

**CRITICAL:** Output ONLY JSON, no markdown, no code blocks. Parseable directly as JSON object."""

# Project-Level Analysis System Prompt - Full Project Analysis (Scope 2.3.5.1 & 2.3.5.2)
SYSTEM_PROMPT_FULL_PROJECT_ANALYSIS = """You are a Network Solution Architect. Analyze these network devices as a whole system.

**Task 1: Network Overview (Scope 2.3.5.1)**
- Provide a concise executive summary of the entire network architecture.
- Mention the topology style (e.g., Star, Ring, Core-Dist-Access).
- List key protocols detected globally (e.g., 'OSPF Area 0 is used for core routing', 'HSRP is active on Core switches').
- **Constraint:** Keep it between 3-5 sentences. Professional and descriptive. Output in English.

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
  "network_overview": "string (3-5 sentences, executive summary in English)",
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
SYSTEM_PROMPT_PROJECT_RECOMMENDATIONS = """You are a Network Solution Architect. Review the configuration summaries of these devices collectively.

**Task: Gap & Integrity Analysis (Scope 2.3.5.2)**
- Identify MISSING configurations, security issues, and configuration inconsistencies that prevent a complete/safe topology.
- Detect patterns of error and potential problems (e.g., 'Switch A defines VLAN 10, but the Core Switch does not have VLAN 10 created', 'STP is disabled globally - risk of Loops', 'Missing NTP configuration on device X', 'Weak password policy detected').
- Provide SPECIFIC, ACTIONABLE recommendations with clear explanation of:
  1. What the issue is (problem description)
  2. Why it matters (impact/risk)
  3. How to fix it (specific configuration steps or actions)
- **Constraint:** Each recommendation must be detailed and actionable. Be specific (mention device names). Format each message as: "Issue: [description]. Impact: [why it matters]. Fix: [specific steps]"

**Output Format:** Return ONLY valid JSON:
{
  "recommendations": [
    {
      "severity": "high|medium|low",
      "message": "string (detailed recommendation with issue description, impact, and fix steps)",
      "device": "string (device name or 'all' if global)"
    }
  ]
}

**CRITICAL:** 
- Each message must be comprehensive and include problem description, impact, and fix steps.
- Output ONLY JSON, no markdown, no code blocks. Parseable directly as JSON object."""


class LLMService:
    """Service for communicating with remote Ollama API (async, non-blocking)."""

    def __init__(self):
        # Environment configuration — remote Ollama on Windows
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://10.4.15.152:11434").rstrip("/")
        self.model_name = os.getenv("OLLAMA_MODEL", "deepseek-coder-v2:16b")
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
                "num_predict": 2048,
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
    
    def _prepare_aggregated_data(self, devices_data: List[Dict[str, Any]], project_id: str) -> Dict[str, Any]:
        """Helper method to prepare aggregated device data."""
        aggregated_data = {
            "project_id": project_id,
            "total_devices": len(devices_data),
            "devices": []
        }
        
        for device in devices_data:
            try:
                device_name = device.get("device_name")
                if not device_name:
                    continue
                
                # Extract key configuration data for each device
                device_summary = {
                    "device_name": device_name,
                    "device_overview": device.get("device_overview", {}),
                    "interfaces": device.get("interfaces", [])[:20] if isinstance(device.get("interfaces"), list) else [],
                    "vlans": device.get("vlans", {}),
                    "stp": device.get("stp", {}),
                    "routing": device.get("routing", {}),
                    "neighbors": device.get("neighbors", [])[:10] if isinstance(device.get("neighbors"), list) else [],
                }
                aggregated_data["devices"].append(device_summary)
            except Exception as e:
                logger.warning(f"Error preparing device data for {device.get('device_name', 'unknown')}: {e}")
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
Provide a Network Overview: executive summary of architecture, topology style, and key protocols.

Return ONLY valid JSON with 'overview_text' key as specified in system prompt."""

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
            
            # Check if JSON parsing failed (returns fallback format)
            if isinstance(parsed_response, dict) and parsed_response.get("format") == "text":
                # JSON parsing failed, treat as error
                logger.warning(f"Failed to parse JSON response for project overview. Raw response: {ai_response[:500]}")
                return self._error_result(
                    f"[ERROR] LLM returned non-JSON response. Expected JSON with 'overview_text' key. Response: {ai_response[:200]}",
                    "json_parse_failed",
                    inference_time_ms,
                    details=ai_response[:500],
                )
            
            # Ensure required fields exist
            if not isinstance(parsed_response, dict):
                parsed_response = {}
            
            if "overview_text" not in parsed_response:
                logger.warning(f"LLM response missing 'overview_text' key. Response: {parsed_response}")
                parsed_response["overview_text"] = "Analysis completed. Overview text not provided."

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
Perform Gap & Integrity Analysis: Identify missing configurations, errors, and suggest specific actionable fixes.

Return ONLY valid JSON with 'recommendations' key as specified in system prompt."""

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
                "num_predict": 2048,
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
