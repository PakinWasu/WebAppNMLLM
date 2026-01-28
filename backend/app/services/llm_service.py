"""LLM Service for Ollama Integration with Context Isolation and Evidence-Based Responses"""

import httpx
import json
import time
from typing import Dict, Any, Optional
from datetime import datetime

from ..core.settings import settings


class LLMService:
    """Service for communicating with Ollama API (async)"""
    
    def __init__(self):
        self.base_url = settings.AI_MODEL_ENDPOINT
        self.model_name = settings.AI_MODEL_NAME
    
    def _get_system_prompt(self, analysis_type: str, device_name: str) -> str:
        """Generate specialized system prompt optimized for technical/code analysis models"""
        
        base_prompt = f"""You are a Senior Network Engineer AI Assistant specialized in analyzing network device configurations. You have deep expertise in network protocols, configuration syntax, and technical documentation.

CRITICAL RULES:
1. CONTEXT ISOLATION: You are analyzing ONLY the device "{device_name}" from the provided configuration data. Do NOT reference or mix data from other devices or projects.

2. EVIDENCE-BASED ANALYSIS: 
   - Base your analysis ONLY on the data provided in the configuration.
   - If information is NOT in the configuration, you MUST respond with "Data not available" or "Not found in configuration".
   - DO NOT hallucinate or make assumptions about missing data.
   - Cite specific configuration values when making claims (e.g., "Interface GE0/0/1 has IP address 10.0.0.1").
   - Analyze configuration syntax and command structures with technical precision.

3. STRUCTURED OUTPUT: Provide your analysis in a well-structured JSON format with clear sections. Ensure JSON is valid and properly formatted.

4. TECHNICAL ACCURACY: 
   - Be precise and factual in your technical analysis.
   - Explain configuration commands and their purposes clearly.
   - Identify potential issues, misconfigurations, or security concerns.
   - If you're uncertain, state it clearly rather than guessing.

5. CODE/CONFIGURATION UNDERSTANDING:
   - Parse and understand configuration syntax accurately.
   - Recognize command hierarchies and relationships.
   - Identify dependencies between configuration sections.

Device being analyzed: {device_name}
Analysis type: {analysis_type}
"""
        
        # Add type-specific instructions
        type_prompts = {
            "security_audit": """
Focus on:
- User accounts and privilege levels
- SSH/SNMP configuration
- ACL rules and security policies
- VRRP/HA security implications
- Potential security vulnerabilities
""",
            "performance_review": """
Focus on:
- Interface utilization and status
- STP configuration and potential loops
- Routing protocol efficiency
- Resource usage (CPU, memory)
- Bottlenecks and optimization opportunities
""",
            "configuration_compliance": """
Focus on:
- Compliance with network standards
- Best practices adherence
- Configuration consistency
- Missing or incorrect settings
- Policy violations
""",
            "network_topology": """
Focus on:
- Interface connections and descriptions
- VLAN assignments
- Routing relationships
- Neighbor devices (LLDP)
- Network segmentation
""",
            "best_practices": """
Focus on:
- Configuration best practices
- Recommendations for improvement
- Industry standards compliance
- Optimization suggestions
- Documentation quality
"""
        }
        
        return base_prompt + type_prompts.get(analysis_type, "")
    
    def _filter_relevant_data(self, parsed_data: Dict[str, Any], analysis_type: str) -> Dict[str, Any]:
        """Filter parsed data to include only relevant fields for the analysis type"""
        filtered = {}
        
        # Always include basic device info
        if "device_overview" in parsed_data:
            filtered["device_overview"] = parsed_data["device_overview"]
        
        # Type-specific filtering to reduce token usage
        if analysis_type == "security_audit":
            if "users" in parsed_data:
                filtered["users"] = parsed_data["users"]
            if "acl" in parsed_data:
                filtered["acl"] = parsed_data["acl"]
            if "snmp" in parsed_data:
                filtered["snmp"] = parsed_data["snmp"]
            if "ssh" in parsed_data:
                filtered["ssh"] = parsed_data["ssh"]
        elif analysis_type == "performance_review":
            if "interfaces" in parsed_data:
                # Limit to first 30 interfaces to reduce tokens
                filtered["interfaces"] = parsed_data["interfaces"][:30]
            if "stp" in parsed_data:
                filtered["stp"] = parsed_data["stp"]
            if "routing" in parsed_data:
                filtered["routing"] = parsed_data["routing"]
        elif analysis_type == "network_topology":
            if "interfaces" in parsed_data:
                # Only include interfaces with IPs or descriptions for topology
                filtered["interfaces"] = [
                    iface for iface in parsed_data["interfaces"][:50]
                    if iface.get("ipv4_address") or iface.get("description")
                ]
            if "neighbors" in parsed_data:
                filtered["neighbors"] = parsed_data["neighbors"]
            if "routing" in parsed_data:
                filtered["routing"] = parsed_data["routing"]
        else:
            # For other types, include most data but limit large arrays
            for key, value in parsed_data.items():
                if isinstance(value, list) and len(value) > 50:
                    filtered[key] = value[:50]  # Limit large arrays
                else:
                    filtered[key] = value
        
        return filtered
    
    def _build_user_prompt(
        self, 
        parsed_data: Dict[str, Any], 
        original_content: Optional[str],
        analysis_type: str,
        custom_prompt: Optional[str] = None
    ) -> str:
        """Build optimized user prompt with filtered data to reduce token usage"""
        
        prompt_parts = []
        
        # Filter data to include only relevant fields
        filtered_data = self._filter_relevant_data(parsed_data, analysis_type)
        
        # Add parsed data (filtered and compressed)
        prompt_parts.append("=== PARSED CONFIGURATION DATA ===")
        # Use compact JSON format to reduce tokens
        prompt_parts.append(json.dumps(filtered_data, separators=(',', ':'), ensure_ascii=False))
        
        # Optionally include original content (reduced limit for 14b model)
        if original_content:
            prompt_parts.append("\n=== ORIGINAL CONFIGURATION CONTENT (REFERENCE) ===")
            prompt_parts.append(original_content[:3000])  # Reduced from 5000 to 3000 for 14b model
            if len(original_content) > 3000:
                prompt_parts.append("\n[Content truncated - showing first 3000 characters]")
        
        # Add analysis request (optimized)
        if custom_prompt:
            prompt_parts.append(f"\n=== ANALYSIS REQUEST ===")
            prompt_parts.append(custom_prompt)
        else:
            prompt_parts.append(f"\n=== ANALYSIS REQUEST ===")
            prompt_parts.append(f"Perform {analysis_type} analysis. Return valid JSON only.")
            prompt_parts.append("Use only data from configuration above.")
        
        return "\n".join(prompt_parts)
    
    async def analyze_configuration(
        self,
        parsed_data: Dict[str, Any],
        original_content: Optional[str],
        analysis_type: str,
        device_name: str,
        custom_prompt: Optional[str] = None,
        include_original: bool = False
    ) -> Dict[str, Any]:
        """
        Analyze network configuration with strict context isolation.
        
        Args:
            parsed_data: Parsed configuration data (from parser)
            original_content: Original configuration text (optional)
            analysis_type: Type of analysis to perform
            device_name: Name of device being analyzed
            custom_prompt: Custom prompt for CUSTOM analysis type
            include_original: Whether to include original_content in context
        
        Returns:
            Dict with 'content', 'metrics', and 'parsed_response'
        """
        
        start_time = time.time()
        
        # Build prompts with context isolation
        system_prompt = self._get_system_prompt(analysis_type, device_name)
        
        # Only include original_content if explicitly requested
        content_to_include = original_content if include_original else None
        user_prompt = self._build_user_prompt(
            parsed_data, 
            content_to_include, 
            analysis_type, 
            custom_prompt
        )
        
        # Prepare Ollama API request
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "options": {
                # Optimized for 14b coder model: balanced temperature for efficiency and accuracy
                "temperature": 0.3,  # Lower temperature for faster, more focused responses
                "top_p": 0.85,  # Slightly lower for faster inference
                "num_predict": 2048,  # Limit max tokens for faster responses
            }
        }
        
        try:
            # Reduced timeout for 14b model (faster than 32b)
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                
                # Extract response
                ai_response = data.get("message", {}).get("content", "")
                
                # Extract token usage if available
                token_usage = {
                    "prompt_tokens": data.get("prompt_eval_count", 0),
                    "completion_tokens": data.get("eval_count", 0),
                    "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
                }
                
                # Calculate inference time
                inference_time_ms = (time.time() - start_time) * 1000
                
                # Try to parse JSON from response
                parsed_response = None
                try:
                    # Try to extract JSON from markdown code blocks if present
                    if "```json" in ai_response:
                        json_start = ai_response.find("```json") + 7
                        json_end = ai_response.find("```", json_start)
                        json_str = ai_response[json_start:json_end].strip()
                        parsed_response = json.loads(json_str)
                    elif "```" in ai_response:
                        json_start = ai_response.find("```") + 3
                        json_end = ai_response.find("```", json_start)
                        json_str = ai_response[json_start:json_end].strip()
                        parsed_response = json.loads(json_str)
                    else:
                        # Try parsing the whole response as JSON
                        parsed_response = json.loads(ai_response)
                except json.JSONDecodeError:
                    # If JSON parsing fails, return as structured text
                    parsed_response = {
                        "analysis": ai_response,
                        "format": "text"
                    }
                
                return {
                    "content": ai_response,
                    "parsed_response": parsed_response,
                    "metrics": {
                        "inference_time_ms": inference_time_ms,
                        "token_usage": token_usage,
                        "model_name": self.model_name,
                        "timestamp": datetime.utcnow()
                    }
                }
                
        except httpx.ReadTimeout:
            return {
                "content": "[ERROR] Ollama read timeout (300s) - Model may be too slow or unresponsive. Consider reducing input data size.",
                "parsed_response": {"error": "timeout"},
                "metrics": {
                    "inference_time_ms": 300000,  # Max timeout
                    "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                    "model_name": self.model_name,
                    "timestamp": datetime.utcnow()
                }
            }
        except httpx.ConnectError as e:
            return {
                "content": f"[ERROR] Cannot connect to Ollama at {self.base_url}\n\nPlease ensure:\n1. Ollama container is running\n2. Ollama is accessible from backend container\n3. Check network connectivity: docker network inspect mnp-network\n4. Verify endpoint in .env: AI_MODEL_ENDPOINT={self.base_url}\n\nError: {str(e)}",
                "parsed_response": {"error": "connection_failed", "details": str(e)},
                "metrics": {
                    "inference_time_ms": (time.time() - start_time) * 1000,
                    "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                    "model_name": self.model_name,
                    "timestamp": datetime.utcnow()
                }
            }
        except httpx.HTTPStatusError as e:
            error_msg = f"[ERROR] Ollama API error ({e.response.status_code})"
            if e.response.status_code == 404:
                error_msg += f"\n\nModel '{self.model_name}' not found. Please pull the model:\n  docker exec mnp-ollama-prod ollama pull {self.model_name}\n  Or run: ./pull-llm-model.sh"
            elif e.response.status_code == 500:
                error_msg += "\n\nOllama internal error. Check Ollama logs:\n  docker logs mnp-ollama-prod"
            return {
                "content": error_msg + f"\n\nResponse: {e.response.text[:200] if e.response else str(e)}",
                "parsed_response": {"error": "http_error", "status_code": e.response.status_code},
                "metrics": {
                    "inference_time_ms": (time.time() - start_time) * 1000,
                    "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                    "model_name": self.model_name,
                    "timestamp": datetime.utcnow()
                }
            }
        except Exception as e:
            return {
                "content": f"[ERROR] Ollama call failed: {str(e)}\n\nTroubleshooting:\n1. Check Ollama is running: docker ps | grep ollama\n2. Check Ollama logs: docker logs mnp-ollama-prod\n3. Verify model exists: docker exec mnp-ollama-prod ollama list\n4. Test connection: curl http://localhost:11434/api/tags",
                "parsed_response": {"error": str(e), "type": type(e).__name__},
                "metrics": {
                    "inference_time_ms": (time.time() - start_time) * 1000,
                    "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                    "model_name": self.model_name,
                    "timestamp": datetime.utcnow()
                }
            }


# Singleton instance
llm_service = LLMService()
