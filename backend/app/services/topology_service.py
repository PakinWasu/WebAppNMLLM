"""Topology Service for Auto-Generating Network Topology using LLM Analysis"""

import httpx
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..core.settings import settings
from ..db.mongo import db


class TopologyService:
    """Service for generating network topology using LLM analysis"""
    
    def __init__(self):
        self.base_url = settings.AI_MODEL_ENDPOINT
        self.model_name = settings.AI_MODEL_NAME
    
    def _get_topology_system_prompt(self, project_id: str, device_count: int) -> str:
        """Generate system prompt for topology analysis"""
        
        return f"""You are a Senior Network Engineer AI Assistant specializing in network topology analysis.

CRITICAL RULES:
1. CONTEXT ISOLATION: You are analyzing ONLY devices within project_id "{project_id}". Do NOT reference or mix data from other projects.

2. EVIDENCE-BASED TOPOLOGY:
   - Create links ONLY based on explicit evidence:
     a) LLDP/CDP neighbor matches (device A's neighbor list shows device B)
     b) Subnet matching (two interfaces on different devices share the same subnet)
     c) Interface descriptions explicitly mentioning other device names
   - DO NOT hallucinate links. If there's no evidence, do NOT create an edge.
   - Each link must have supporting evidence cited.

3. OUTPUT FORMAT: You MUST return a valid JSON object with this exact structure:
{{
  "nodes": [
    {{"id": "device_name", "label": "display_name", "type": "Core|Distribution|Access|Router|Switch"}},
    ...
  ],
  "edges": [
    {{"from": "device_a", "to": "device_b", "label": "interface_info", "evidence": "why_this_link_exists"}},
    ...
  ],
  "analysis_summary": "Brief explanation of topology structure"
}}

4. DEVICE TYPE CLASSIFICATION:
   - Core: Typically has multiple routing protocols, high-speed interfaces, connects to distribution/access
   - Distribution: Connects core to access, may have routing and switching
   - Access: End-user facing, typically access ports, connects to distribution/core
   - Router: Primarily routing, minimal switching
   - Switch: Primarily switching, minimal routing

5. ACCURACY: Be precise. Only create edges you can verify from the provided data.

Project ID: {project_id}
Number of devices to analyze: {device_count}
"""
    
    def _build_topology_prompt(self, devices_data: List[Dict[str, Any]]) -> str:
        """Build user prompt with all device data for topology analysis"""
        
        prompt_parts = []
        prompt_parts.append("=== NETWORK TOPOLOGY ANALYSIS REQUEST ===")
        prompt_parts.append("\nAnalyze the following network devices and their relationships to generate a topology map.")
        prompt_parts.append("\nFor each device, I will provide:")
        prompt_parts.append("- Device name and overview")
        prompt_parts.append("- Interfaces with IP addresses and descriptions")
        prompt_parts.append("- LLDP/CDP neighbors")
        prompt_parts.append("- Routing information")
        prompt_parts.append("\n=== DEVICE DATA ===")
        
        for idx, device in enumerate(devices_data, 1):
            device_name = device.get("device_name", f"device_{idx}")
            overview = device.get("device_overview", {})
            interfaces = device.get("interfaces", [])
            neighbors = device.get("neighbors", [])
            routing = device.get("routing", {})
            
            prompt_parts.append(f"\n--- Device {idx}: {device_name} ---")
            prompt_parts.append(f"Role: {overview.get('role', 'Unknown')}")
            prompt_parts.append(f"Model: {overview.get('model', 'Unknown')}")
            prompt_parts.append(f"Management IP: {overview.get('management_ip', 'N/A')}")
            
            # Interfaces with IPs and descriptions
            if interfaces:
                prompt_parts.append("\nInterfaces:")
                for iface in interfaces[:20]:  # Limit to prevent token overflow
                    iface_info = f"  - {iface.get('name', 'N/A')}"
                    if iface.get('ipv4_address'):
                        iface_info += f" IP: {iface.get('ipv4_address')}"
                    if iface.get('description'):
                        iface_info += f" Desc: {iface.get('description')}"
                    if iface.get('port_mode'):
                        iface_info += f" Mode: {iface.get('port_mode')}"
                    prompt_parts.append(iface_info)
            
            # Neighbors (LLDP/CDP)
            if neighbors:
                prompt_parts.append("\nNeighbors (LLDP/CDP):")
                for neighbor in neighbors[:20]:  # Limit neighbors
                    neighbor_info = f"  - Device: {neighbor.get('device_name', 'Unknown')}"
                    neighbor_info += f" | Local Port: {neighbor.get('local_port', 'N/A')}"
                    neighbor_info += f" | Remote Port: {neighbor.get('remote_port', 'N/A')}"
                    if neighbor.get('ip_address'):
                        neighbor_info += f" | IP: {neighbor.get('ip_address')}"
                    prompt_parts.append(neighbor_info)
            
            # Routing info (for L3 relationships)
            if routing:
                routing_info = []
                if routing.get('ospf'):
                    ospf = routing['ospf']
                    routing_info.append(f"OSPF: Router ID {ospf.get('router_id', 'N/A')}, Process {ospf.get('process_id', 'N/A')}")
                if routing.get('bgp'):
                    bgp = routing['bgp']
                    routing_info.append(f"BGP: AS {bgp.get('as_number', bgp.get('local_as', 'N/A'))}, Peers: {len(bgp.get('peers', []))}")
                if routing.get('static'):
                    static_routes = routing['static']
                    if isinstance(static_routes, list):
                        routing_info.append(f"Static Routes: {len(static_routes)}")
                    elif isinstance(static_routes, dict) and static_routes.get('routes'):
                        routing_info.append(f"Static Routes: {len(static_routes['routes'])}")
                if routing_info:
                    prompt_parts.append("\nRouting:")
                    prompt_parts.append("  " + " | ".join(routing_info))
        
        prompt_parts.append("\n=== ANALYSIS INSTRUCTIONS ===")
        prompt_parts.append("1. Identify all devices and classify their types (Core/Distribution/Access/Router/Switch)")
        prompt_parts.append("2. Create edges ONLY when you have evidence:")
        prompt_parts.append("   - LLDP/CDP shows device A connected to device B")
        prompt_parts.append("   - Two interfaces on different devices share the same subnet")
        prompt_parts.append("   - Interface description explicitly mentions another device")
        prompt_parts.append("3. For each edge, include:")
        prompt_parts.append("   - 'from': source device name")
        prompt_parts.append("   - 'to': destination device name")
        prompt_parts.append("   - 'label': interface or link description")
        prompt_parts.append("   - 'evidence': why this link exists (e.g., 'LLDP neighbor match', 'Subnet match: 10.0.1.0/24')")
        prompt_parts.append("4. Return ONLY valid JSON matching the required format.")
        
        return "\n".join(prompt_parts)
    
    async def generate_topology(
        self,
        project_id: str
    ) -> Dict[str, Any]:
        """
        Generate network topology for a project using LLM analysis.
        
        Args:
            project_id: Project ID to analyze
        
        Returns:
            Dict with 'topology' (nodes/edges), 'metrics', and 'analysis_summary'
        """
        
        start_time = time.time()
        
        # Fetch all devices for this project (strict project isolation)
        devices_cursor = db()["parsed_configs"].find(
            {"project_id": project_id},
            sort=[("device_name", 1)]
        )
        
        devices_data = []
        device_names = set()
        
        async for device_doc in devices_cursor:
            # Remove MongoDB _id
            device_doc.pop("_id", None)
            
            # Extract key fields for topology analysis
            device_data = {
                "device_name": device_doc.get("device_name"),
                "device_overview": device_doc.get("device_overview", {}),
                "interfaces": device_doc.get("interfaces", []),
                "neighbors": device_doc.get("neighbors", []),
                "routing": device_doc.get("routing", {}),
            }
            
            if device_data["device_name"] and device_data["device_name"] not in device_names:
                devices_data.append(device_data)
                device_names.add(device_data["device_name"])
        
        if not devices_data:
            return {
                "topology": {"nodes": [], "edges": []},
                "analysis_summary": "No devices found in project",
                "metrics": {
                    "inference_time_ms": 0,
                    "devices_processed": 0,
                    "model_name": self.model_name,
                    "timestamp": datetime.utcnow()
                }
            }
        
        # Build prompts
        system_prompt = self._get_topology_system_prompt(project_id, len(devices_data))
        user_prompt = self._build_topology_prompt(devices_data)
        
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
                "temperature": 0.2,  # Very low temperature for factual topology
                "top_p": 0.9,
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                
                # Extract response
                ai_response = data.get("message", {}).get("content", "")
                
                # Extract token usage
                token_usage = {
                    "prompt_tokens": data.get("prompt_eval_count", 0),
                    "completion_tokens": data.get("eval_count", 0),
                    "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
                }
                
                # Calculate inference time
                inference_time_ms = (time.time() - start_time) * 1000
                
                # Parse JSON from response
                topology_data = None
                analysis_summary = ""
                
                try:
                    # Try to extract JSON from markdown code blocks
                    if "```json" in ai_response:
                        json_start = ai_response.find("```json") + 7
                        json_end = ai_response.find("```", json_start)
                        json_str = ai_response[json_start:json_end].strip()
                        topology_data = json.loads(json_str)
                    elif "```" in ai_response:
                        json_start = ai_response.find("```") + 3
                        json_end = ai_response.find("```", json_start)
                        json_str = ai_response[json_start:json_end].strip()
                        topology_data = json.loads(json_str)
                    else:
                        # Try parsing the whole response as JSON
                        topology_data = json.loads(ai_response)
                    
                    # Extract analysis_summary if present
                    analysis_summary = topology_data.get("analysis_summary", "")
                    
                    # Validate structure
                    if "nodes" not in topology_data:
                        topology_data["nodes"] = []
                    if "edges" not in topology_data:
                        topology_data["edges"] = []
                    
                    # Validate and clean nodes
                    validated_nodes = []
                    for node in topology_data.get("nodes", []):
                        if isinstance(node, dict) and "id" in node:
                            validated_nodes.append({
                                "id": str(node["id"]),
                                "label": node.get("label", node["id"]),
                                "type": node.get("type", "Switch")
                            })
                    
                    # Validate and clean edges
                    validated_edges = []
                    for edge in topology_data.get("edges", []):
                        if isinstance(edge, dict) and "from" in edge and "to" in edge:
                            validated_edges.append({
                                "from": str(edge["from"]),
                                "to": str(edge["to"]),
                                "label": edge.get("label", ""),
                                "evidence": edge.get("evidence", "")
                            })
                    
                    topology_data = {
                        "nodes": validated_nodes,
                        "edges": validated_edges
                    }
                    
                except json.JSONDecodeError as e:
                    # If JSON parsing fails, return error
                    return {
                        "topology": {"nodes": [], "edges": []},
                        "analysis_summary": f"Failed to parse LLM response as JSON: {str(e)}",
                        "raw_response": ai_response[:500],  # First 500 chars for debugging
                        "metrics": {
                            "inference_time_ms": inference_time_ms,
                            "devices_processed": len(devices_data),
                            "token_usage": token_usage,
                            "model_name": self.model_name,
                            "timestamp": datetime.utcnow()
                        }
                    }
                
                # Log performance metrics
                await self._log_performance_metrics(
                    project_id=project_id,
                    inference_time_ms=inference_time_ms,
                    devices_processed=len(devices_data),
                    token_usage=token_usage
                )
                
                return {
                    "topology": topology_data,
                    "analysis_summary": analysis_summary or "Topology generated successfully",
                    "metrics": {
                        "inference_time_ms": inference_time_ms,
                        "devices_processed": len(devices_data),
                        "token_usage": token_usage,
                        "model_name": self.model_name,
                        "timestamp": datetime.utcnow()
                    }
                }
                
        except httpx.ReadTimeout:
            return {
                "topology": {"nodes": [], "edges": []},
                "analysis_summary": "[ERROR] Ollama read timeout (300s) - Topology generation failed. Please check if Ollama is running and responsive.",
                "metrics": {
                    "inference_time_ms": 300000,
                    "devices_processed": len(devices_data),
                    "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                    "model_name": self.model_name,
                    "timestamp": datetime.utcnow()
                }
            }
        except httpx.HTTPStatusError as e:
            error_msg = f"[ERROR] Ollama API error ({e.response.status_code}): {e.response.text[:200] if e.response else str(e)}"
            if e.response.status_code == 404:
                error_msg += "\n\nPossible causes:\n- Ollama is not running on your host machine\n- Ollama is not accessible from Docker container\n- Check Ollama endpoint: " + self.base_url
            return {
                "topology": {"nodes": [], "edges": []},
                "analysis_summary": error_msg,
                "metrics": {
                    "inference_time_ms": (time.time() - start_time) * 1000,
                    "devices_processed": len(devices_data),
                    "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                    "model_name": self.model_name,
                    "timestamp": datetime.utcnow()
                }
            }
        except httpx.ConnectError as e:
            return {
                "topology": {"nodes": [], "edges": []},
                "analysis_summary": f"[ERROR] Cannot connect to Ollama at {self.base_url}\n\nPlease ensure:\n1. Ollama is running on your host machine\n2. Ollama is accessible from Docker (check host.docker.internal)\n3. Ollama is listening on port 11434\n\nError details: {str(e)}",
                "metrics": {
                    "inference_time_ms": (time.time() - start_time) * 1000,
                    "devices_processed": len(devices_data),
                    "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                    "model_name": self.model_name,
                    "timestamp": datetime.utcnow()
                }
            }
        except Exception as e:
            return {
                "topology": {"nodes": [], "edges": []},
                "analysis_summary": f"[ERROR] Topology generation failed: {str(e)}\n\nPlease check:\n1. Ollama service is running\n2. Network connectivity from Docker to host\n3. Backend logs for more details",
                "metrics": {
                    "inference_time_ms": (time.time() - start_time) * 1000,
                    "devices_processed": len(devices_data),
                    "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                    "model_name": self.model_name,
                    "timestamp": datetime.utcnow()
                }
            }
    
    async def _log_performance_metrics(
        self,
        project_id: str,
        inference_time_ms: float,
        devices_processed: int,
        token_usage: Dict[str, int]
    ):
        """Log topology generation performance metrics"""
        
        try:
            performance_log = {
                "project_id": project_id,
                "task_type": "topology_generation",
                "inference_time_ms": inference_time_ms,
                "devices_processed": devices_processed,
                "token_usage": token_usage,
                "model_name": self.model_name,
                "timestamp": datetime.utcnow()
            }
            
            from ..db.mongo import db
            await db()["performance_logs"].insert_one(performance_log)
        except Exception as e:
            # Log error but don't fail the request
            print(f"Warning: Failed to log topology performance metrics: {e}")


# Singleton instance
topology_service = TopologyService()
