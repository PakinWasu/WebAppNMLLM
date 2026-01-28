"""Topology Service for Auto-Generating Network Topology using LLM Analysis
Based on POC logic from network-llm-poc/main.py"""

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

3. OUTPUT FORMAT: You MUST return a valid JSON object with this exact structure (NO markdown, NO code blocks, ONLY pure JSON):
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

EXAMPLE OUTPUT:
{{
  "nodes": [
    {{"id": "CORE1", "label": "CORE1", "type": "Core"}},
    {{"id": "DIST1", "label": "DIST1", "type": "Distribution"}},
    {{"id": "ACC1", "label": "ACC1", "type": "Access"}}
  ],
  "edges": [
    {{"from": "CORE1", "to": "DIST1", "label": "GE0/0/1-GE0/0/1", "evidence": "LLDP neighbor match"}},
    {{"from": "DIST1", "to": "ACC1", "label": "GE0/0/2-GE0/0/1", "evidence": "LLDP neighbor match"}}
  ],
  "analysis_summary": "3-tier hierarchy: Core-Distribution-Access"
}}

4. DEVICE TYPE CLASSIFICATION:
   - Core: Typically has multiple routing protocols, high-speed interfaces, connects to distribution/access
   - Distribution: Connects core to access, may have routing and switching
   - Access: End-user facing, typically access ports, connects to distribution/core
   - Router: Primarily routing, minimal switching
   - Switch: Primarily switching, minimal routing

5. ACCURACY: Be precise. Only create edges you can verify from the provided data.

6. UNKNOWN LINKS: If neighbor data is incomplete, ambiguous, or you cannot determine the connection with certainty, you MUST:
   - Still create the edge if there's partial evidence
   - Set evidence to "Unknown Link - incomplete neighbor data" or similar
   - DO NOT guess or invent connection details

Project ID: {project_id}
Number of devices to analyze: {device_count}
"""
    
    def _prepare_topology_data_for_llm(self, devices_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Prepare topology data for LLM analysis following POC approach.
        Focuses on LLDP neighbors and IP routing information.
        """
        topology_data = {
            "total_devices": len(devices_data),
            "devices": []
        }
        
        # Limit number of devices if too many (for efficiency)
        max_devices = 15
        devices_to_process = devices_data[:max_devices]
        
        for device in devices_to_process:
            device_name = device.get("device_name")
            if not device_name:
                continue
            
            overview = device.get("device_overview", {})
            interfaces = device.get("interfaces", [])
            neighbors = device.get("neighbors", [])
            routing = device.get("routing", {})
            
            # Prepare device info following POC structure
            device_info = {
                "device_id": device_name,
                "hostname": overview.get("hostname", device_name),
                "role": overview.get("role", "Unknown"),
                "model": overview.get("model", overview.get("model_platform", "Unknown")),
                "management_ip": overview.get("management_ip"),
                # Only include UP interfaces with IPs (most relevant for topology)
                "interfaces": [
                    {
                        "name": intf.get("name"),
                        "ipv4_address": intf.get("ipv4_address"),
                        "admin_status": intf.get("admin_status", "up"),
                        "oper_status": intf.get("oper_status", "up"),
                        "type": intf.get("type")
                    }
                    for intf in interfaces[:10]  # Limit to 10 interfaces per device
                    if intf.get("ipv4_address") or intf.get("admin_status") == "up"
                ],
                # LLDP/CDP neighbors - most important for topology
                "neighbors": neighbors[:15],  # Limit to 15 neighbors per device
                # Routing information for L3 topology
                "routing": {
                    "ospf": {
                        "neighbors": routing.get("ospf", {}).get("neighbors", []) if routing.get("ospf") else []
                    },
                    "bgp": {
                        "peers": routing.get("bgp", {}).get("peers", []) if routing.get("bgp") else []
                    },
                    "eigrp": {
                        "neighbors": routing.get("eigrp", {}).get("neighbors", []) if routing.get("eigrp") else []
                    }
                }
            }
            topology_data["devices"].append(device_info)
        
        return topology_data
    
    def _build_topology_prompt(self, topology_data: Dict[str, Any]) -> str:
        """Build user prompt following POC approach"""
        user_message = f"""Analyze the following network device data and generate a complete topology structure.

Network Device Data:
{json.dumps(topology_data, ensure_ascii=False, indent=2)}

Based on these LLDP/CDP neighbors and subnet masks, list all Point-to-Point connections.

CRITICAL INSTRUCTIONS:
- Create links ONLY based on explicit evidence from LLDP/CDP neighbors or subnet matching
- If neighbor data is incomplete or ambiguous, state "Unknown Link" in the evidence field
- DO NOT hallucinate links. If there's no evidence, do NOT create an edge.
- Return ONLY the JSON object with nodes and edges as specified in the system prompt."""
        
        return user_message
    
    def _generate_rule_based_topology(self, devices_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate topology using rule-based approach (fallback when LLM fails).
        Uses LLDP/CDP neighbors and subnet matching to create edges.
        """
        nodes = []
        edges = []
        device_map = {}
        
        # Create nodes from all devices
        for device in devices_data:
            device_name = device.get("device_name")
            if not device_name:
                continue
            
            overview = device.get("device_overview", {})
            device_type = overview.get("role", "Switch")
            
            # Classify device type based on routing info
            routing = device.get("routing", {})
            if routing.get("ospf") or routing.get("bgp"):
                if device_type.lower() not in ["core", "distribution", "access"]:
                    device_type = "Router"
            
            nodes.append({
                "id": device_name,
                "label": device_name,
                "type": device_type
            })
            device_map[device_name] = device
        
        # Create edges based on LLDP/CDP neighbors
        edge_set = set()  # To avoid duplicates
        
        for device in devices_data:
            device_name = device.get("device_name")
            if not device_name:
                continue
            
            neighbors = device.get("neighbors", [])
            for neighbor in neighbors:
                neighbor_name = neighbor.get("device_name")
                if not neighbor_name or neighbor_name not in device_map:
                    continue
                
                # Check if this device exists in our device list
                if neighbor_name in device_map:
                    local_port = neighbor.get("local_port", "")
                    remote_port = neighbor.get("remote_port", "")
                    
                    # Create edge key to avoid duplicates
                    edge_key = tuple(sorted([device_name, neighbor_name]))
                    if edge_key not in edge_set:
                        edge_set.add(edge_key)
                        edges.append({
                            "from": device_name,
                            "to": neighbor_name,
                            "label": f"{local_port}-{remote_port}" if local_port and remote_port else "",
                            "evidence": f"LLDP/CDP neighbor: {device_name} sees {neighbor_name}"
                        })
        
        # Create edges based on subnet matching
        interface_subnets = {}  # subnet -> [(device_name, interface_name, ip)]
        
        for device in devices_data:
            device_name = device.get("device_name")
            if not device_name:
                continue
            
            interfaces = device.get("interfaces", [])
            for iface in interfaces:
                ipv4 = iface.get("ipv4_address")
                if not ipv4:
                    continue
                
                # Extract subnet (simple approach: remove last octet)
                try:
                    parts = ipv4.split(".")
                    if len(parts) == 4:
                        subnet = ".".join(parts[:3]) + ".0/24"  # Assume /24
                        if subnet not in interface_subnets:
                            interface_subnets[subnet] = []
                        interface_subnets[subnet].append((device_name, iface.get("name", ""), ipv4))
                except:
                    continue
        
        # Create edges for devices on same subnet
        for subnet, devices_on_subnet in interface_subnets.items():
            if len(devices_on_subnet) < 2:
                continue
            
            # Create edges between all devices on the same subnet
            for i, (dev1, iface1, ip1) in enumerate(devices_on_subnet):
                for j, (dev2, iface2, ip2) in enumerate(devices_on_subnet[i+1:], i+1):
                    if dev1 not in device_map or dev2 not in device_map:
                        continue
                    
                    edge_key = tuple(sorted([dev1, dev2]))
                    if edge_key not in edge_set:
                        edge_set.add(edge_key)
                        edges.append({
                            "from": dev1,
                            "to": dev2,
                            "label": f"{iface1}-{iface2}",
                            "evidence": f"Subnet match: {dev1} ({ip1}) and {dev2} ({ip2}) on {subnet}"
                        })
        
        return {
            "nodes": nodes,
            "edges": edges
        }
    
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
        
        # Prepare topology data following POC approach
        topology_data_for_llm = self._prepare_topology_data_for_llm(devices_data)
        
        # Log data being sent to LLM
        total_interfaces = sum(len(d.get("interfaces", [])) for d in devices_data)
        total_neighbors = sum(len(d.get("neighbors", [])) for d in devices_data)
        print(f"[Topology] Generating topology for project {project_id}: {len(devices_data)} devices, {total_interfaces} interfaces, {total_neighbors} neighbors")
        
        # Build prompts
        system_prompt = self._get_topology_system_prompt(project_id, len(devices_data))
        user_prompt = self._build_topology_prompt(topology_data_for_llm)
        
        # Estimate prompt length (rough token count)
        prompt_length = len(system_prompt) + len(user_prompt)
        estimated_tokens = prompt_length // 4  # Rough estimate: 4 chars per token
        print(f"[Topology] Prompt length: {prompt_length} chars (~{estimated_tokens} tokens)")
        
        # Prepare Ollama API request
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "format": "json",  # Request JSON format output (qwen2.5-coder supports this)
            "options": {
                "temperature": 0.1,  # Very low temperature for faster, more focused responses
                "top_p": 0.8,  # Lower for faster inference
                "num_predict": 3072,  # Increased to allow sufficient tokens for response
            }
        }
        
        llm_success = False
        topology_data = None
        analysis_summary = ""
        token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        
        try:
            # Use detailed timeout configuration like POC (connect, read, write, pool)
            timeout = httpx.Timeout(
                connect=30.0,  # Connection timeout
                read=600.0,   # Read timeout (10 minutes for complex topology analysis)
                write=120.0,  # Write timeout
                pool=120.0    # Pool timeout
            )
            async with httpx.AsyncClient(timeout=timeout) as client:
                llm_start_time = time.time()
                print(f"[Topology] Calling Ollama API at {self.base_url} with model {self.model_name}...")
                response = await client.post(url, json=payload)
                llm_response_time = time.time() - llm_start_time
                print(f"[Topology] Ollama API response received in {llm_response_time:.2f}s")
                
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
                print(f"[Topology] Token usage: {token_usage}")
                
                # Parse JSON from response
                # With "format": "json", Ollama should return pure JSON, but we still clean it
                try:
                    content_cleaned = ai_response.strip()
                    
                    # Remove markdown code blocks if present (some models still add them)
                    if content_cleaned.startswith("```"):
                        lines = content_cleaned.split("\n")
                        if lines[0].startswith("```"):
                            lines = lines[1:]  # Remove opening ```
                        if lines and lines[-1].strip() == "```":
                            lines = lines[:-1]  # Remove closing ```
                        content_cleaned = "\n".join(lines).strip()
                    
                    # Try parsing JSON
                    topology_data = json.loads(content_cleaned)
                    
                    # Validate structure
                    if not isinstance(topology_data, dict):
                        raise ValueError("Topology must be a JSON object")
                    if "nodes" not in topology_data or "edges" not in topology_data:
                        raise ValueError("Topology must contain 'nodes' and 'edges' arrays")
                    if not isinstance(topology_data["nodes"], list) or not isinstance(topology_data["edges"], list):
                        raise ValueError("'nodes' and 'edges' must be arrays")
                    
                    llm_success = True
                    print(f"[Topology] Successfully parsed LLM response: {len(topology_data.get('nodes', []))} nodes, {len(topology_data.get('edges', []))} edges")
                    
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"[Topology] Failed to parse LLM JSON response: {e}")
                    print(f"[Topology] Response preview: {ai_response[:500]}")
                    llm_success = False
                    
        except httpx.ReadTimeout:
            print(f"[Topology] Ollama read timeout (600s) - falling back to rule-based topology")
            llm_success = False
        except httpx.ConnectTimeout:
            print(f"[Topology] Connection to Ollama timed out - falling back to rule-based topology")
            llm_success = False
        except httpx.HTTPStatusError as e:
            error_text = e.response.text[:200] if e.response else str(e)
            print(f"[Topology] Ollama API error ({e.response.status_code}): {error_text}")
            if e.response.status_code == 404:
                print(f"[Topology] Model {self.model_name} may not be available. Check if model is pulled.")
            llm_success = False
        except httpx.ConnectError as e:
            print(f"[Topology] Cannot connect to Ollama at {self.base_url}: {e}")
            print(f"[Topology] Please ensure Ollama is running and accessible")
            llm_success = False
        except Exception as e:
            print(f"[Topology] Unexpected error during LLM call: {type(e).__name__}: {e}")
            import traceback
            print(f"[Topology] Traceback: {traceback.format_exc()}")
            llm_success = False
        
        # Calculate inference time
        inference_time_ms = (time.time() - start_time) * 1000
        
        # If LLM failed, use rule-based fallback
        if not llm_success or not topology_data:
            print(f"[Topology] Using rule-based fallback topology generation")
            rule_based_result = self._generate_rule_based_topology(devices_data)
            topology_data = rule_based_result
            analysis_summary = "Topology generated using rule-based method (LLDP/CDP neighbors and subnet matching)"
            if not llm_success:
                analysis_summary += " - LLM timeout or error occurred"
        else:
            # Extract analysis_summary if present
            analysis_summary = topology_data.get("analysis_summary", "")
            if not analysis_summary:
                analysis_summary = f"Topology generated successfully using LLM ({len(topology_data.get('nodes', []))} nodes, {len(topology_data.get('edges', []))} edges)"
        
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
        
        print(f"[Topology] Final topology: {len(validated_nodes)} nodes, {len(validated_edges)} edges, time: {inference_time_ms:.0f}ms")
        
        # Log performance metrics
        await self._log_performance_metrics(
            project_id=project_id,
            inference_time_ms=inference_time_ms,
            devices_processed=len(devices_data),
            token_usage=token_usage
        )
        
        return {
            "topology": topology_data,
            "analysis_summary": analysis_summary,
            "metrics": {
                "inference_time_ms": inference_time_ms,
                "devices_processed": len(devices_data),
                "token_usage": token_usage,
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
