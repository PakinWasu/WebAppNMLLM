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
        """Generate specialized system prompt that forces evidence-based answers"""
        
        base_prompt = f"""You are a Senior Network Engineer AI Assistant analyzing network device configurations.

CRITICAL RULES:
1. CONTEXT ISOLATION: You are analyzing ONLY the device "{device_name}" from the provided configuration data. Do NOT reference or mix data from other devices or projects.

2. EVIDENCE-BASED ANALYSIS: 
   - Base your analysis ONLY on the data provided in the configuration.
   - If information is NOT in the configuration, you MUST respond with "Data not available" or "Not found in configuration".
   - DO NOT hallucinate or make assumptions about missing data.
   - Cite specific configuration values when making claims (e.g., "Interface GE0/0/1 has IP address 10.0.0.1").

3. STRUCTURED OUTPUT: Provide your analysis in a structured JSON format with clear sections.

4. ACCURACY: Be precise and factual. If you're uncertain, state it clearly.

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
    
    def _build_user_prompt(
        self, 
        parsed_data: Dict[str, Any], 
        original_content: Optional[str],
        analysis_type: str,
        custom_prompt: Optional[str] = None
    ) -> str:
        """Build user prompt with strict context isolation"""
        
        prompt_parts = []
        
        # Add parsed data (always included)
        prompt_parts.append("=== PARSED CONFIGURATION DATA ===")
        prompt_parts.append(json.dumps(parsed_data, indent=2, ensure_ascii=False))
        
        # Optionally include original content
        if original_content:
            prompt_parts.append("\n=== ORIGINAL CONFIGURATION CONTENT ===")
            prompt_parts.append(original_content[:5000])  # Limit to prevent token overflow
            if len(original_content) > 5000:
                prompt_parts.append("\n[Content truncated - showing first 5000 characters]")
        
        # Add analysis request
        if custom_prompt:
            prompt_parts.append(f"\n=== ANALYSIS REQUEST ===")
            prompt_parts.append(custom_prompt)
        else:
            prompt_parts.append(f"\n=== ANALYSIS REQUEST ===")
            prompt_parts.append(f"Please perform a {analysis_type} analysis on this device configuration.")
            prompt_parts.append("Provide your analysis in structured JSON format with clear sections.")
            prompt_parts.append("Remember: Only use information present in the configuration data above.")
        
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
                "temperature": 0.3,  # Lower temperature for more factual responses
                "top_p": 0.9,
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=600.0) as client:
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
                "content": "[ERROR] Ollama read timeout (600s) - Model may be too slow or unresponsive",
                "parsed_response": {"error": "timeout"},
                "metrics": {
                    "inference_time_ms": 600000,  # Max timeout
                    "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                    "model_name": self.model_name,
                    "timestamp": datetime.utcnow()
                }
            }
        except Exception as e:
            return {
                "content": f"[ERROR] Ollama call failed: {str(e)}",
                "parsed_response": {"error": str(e)},
                "metrics": {
                    "inference_time_ms": (time.time() - start_time) * 1000,
                    "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                    "model_name": self.model_name,
                    "timestamp": datetime.utcnow()
                }
            }


# Singleton instance
llm_service = LLMService()
