"""LLM Service for Ollama Integration — Remote server, Scope 2.3.5 analysis, async httpx."""

import os
import json
import time
import logging
from typing import Dict, Any, Optional
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
        except httpx.ConnectError as e:
            inference_time_ms = (time.perf_counter() - start_time) * 1000
            logger.exception("ollama_request connect_error base_url=%s error=%s", self.base_url, e)
            return self._error_result(
                f"[ERROR] Cannot connect to Ollama at {self.base_url}. Check network and OLLAMA_BASE_URL. Error: {e!s}",
                "connection_failed",
                inference_time_ms,
                details=str(e),
            )
        except httpx.HTTPStatusError as e:
            inference_time_ms = (time.perf_counter() - start_time) * 1000
            logger.warning(
                "ollama_request http_error model_used=%s status=%s device=%s",
                self.model_name,
                e.response.status_code if e.response else None,
                device_name,
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
            logger.exception("ollama_request failed model_used=%s device=%s error=%s", self.model_name, device_name, e)
            return self._error_result(
                f"[ERROR] Ollama call failed: {e!s}",
                type(e).__name__,
                inference_time_ms,
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
