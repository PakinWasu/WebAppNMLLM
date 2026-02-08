"""Topology Service for Auto-Generating Network Topology using LLM Analysis
Based on POC logic from network-llm-poc/main.py"""

import os
import httpx
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..db.mongo import db


def _ollama_base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", "http://10.4.15.52:11434").rstrip("/")


def _ollama_model() -> str:
    return os.getenv("OLLAMA_MODEL", "qwen2.5:7b")


def _ollama_timeout_seconds() -> float:
    return float(os.getenv("OLLAMA_TIMEOUT", "300"))


def _topology_use_llm() -> bool:
    """Whether topology generation should call LLM (default True). Set TOPOLOGY_USE_LLM=false to use rule-based only."""
    v = os.getenv("TOPOLOGY_USE_LLM", "true").strip().lower()
    return v in ("true", "1", "yes")


class TopologyService:
    """Service for generating network topology using LLM analysis"""

    def __init__(self):
        self.base_url = _ollama_base_url()
        self.model_name = _ollama_model()
    
    def _get_topology_system_prompt(self, project_id: str, device_count: int) -> str:
        """Generate system prompt for topology analysis - ONLY CDP/LLDP neighbors, NO VLAN/interface data"""
        
        return f"""You are an Expert Network Topology Engineer. Analyze CDP/LLDP neighbor data ONLY from network devices and generate a complete network topology.

**CRITICAL OUTPUT REQUIREMENTS:**
- Output ONLY valid JSON format (no markdown, no code blocks)
- Parseable directly as JSON object
- Use ONLY CDP/LLDP neighbor relationships - DO NOT use VLAN or interface information

**Output Format:**
{{
  "nodes": [
    {{
      "id": "device_id_or_hostname",
      "label": "display_name",
      "type": "router|switch|access_switch|firewall|other"
    }}
  ],
  "edges": [
    {{
      "from": "source_device_id",
      "to": "target_device_id",
      "label": "local_port-remote_port",
      "evidence": "CDP/LLDP neighbor"
    }}
  ],
  "analysis_summary": "brief explanation"
}}

**Analysis Guidelines:**
1. **Nodes**: Create one node per unique device from neighbor data. Use device_id or hostname as "id".
2. **Edges**: Create edges ONLY from CDP/LLDP neighbor information. Each neighbor entry indicates a direct physical connection.
3. **Data Source**: Use ONLY the neighbors array provided - DO NOT use VLAN or interface data.

**CRITICAL RULES:**
- Use ONLY CDP/LLDP neighbor relationships to create edges
- DO NOT create edges based on VLAN membership or interface IP addresses
- DO NOT infer connections from routing protocols or other data
- If device A has neighbor B in CDP/LLDP, create edge from A to B
- If device B also has neighbor A, that's bidirectional (one edge is enough)
- Use exact device IDs/hostnames from input data
- Preserve port names from neighbor data (local_port-remote_port)

**DO NOT:**
- Use VLAN information to create connections
- Use interface IP addresses to infer connections
- Use routing protocol neighbors to create topology edges
- Create edges that are not explicitly shown in CDP/LLDP neighbor data

Project: {project_id} ({device_count} devices)"""
    
    def _prepare_topology_data_for_llm(self, devices_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Prepare topology data for LLM analysis - ONLY CDP/LLDP neighbors data.
        Sends minimal data: device_id, hostname, and CDP/LLDP neighbors array only.
        NO VLAN, NO interface data, NO routing data.
        """
        topology_data = {
            "total_devices": len(devices_data),
            "devices": []
        }
        
        # Limit number of devices if too many (for efficiency)
        max_devices = 20  # Increased since we're sending less data per device
        devices_to_process = devices_data[:max_devices]
        
        for device in devices_to_process:
            device_name = device.get("device_name")
            if not device_name:
                continue
            
            overview = device.get("device_overview", {})
            neighbors = device.get("neighbors", [])
            
            # Filter only CDP/LLDP neighbors (exclude routing protocol neighbors)
            cdp_lldp_neighbors = []
            for neighbor in neighbors:
                # Only include neighbors that have local_port/remote_port (CDP/LLDP indicators)
                # Exclude routing protocol neighbors (OSPF/BGP/EIGRP)
                if neighbor.get("local_port") or neighbor.get("remote_port") or \
                   neighbor.get("local_interface") or neighbor.get("remote_interface"):
                    cdp_lldp_neighbors.append(neighbor)
            
            # Skip devices with no CDP/LLDP neighbors (they won't contribute to topology)
            if not cdp_lldp_neighbors:
                continue
            
            # Prepare minimal device info - ONLY CDP/LLDP neighbors for topology
            device_info = {
                "device_id": device_name,
                "hostname": overview.get("hostname", device_name),
                # Send ONLY CDP/LLDP neighbors - NO VLAN, NO interface, NO routing data
                "neighbors": cdp_lldp_neighbors
            }
            topology_data["devices"].append(device_info)
        
        return topology_data
    
    def _build_topology_prompt(self, topology_data: Dict[str, Any]) -> str:
        """Build user prompt - ONLY CDP/LLDP neighbors data for topology generation"""
        devices = topology_data.get("devices", [])
        
        # Build detailed prompt with CDP/LLDP neighbor information ONLY
        prompt_parts = [
            f"Analyze the following CDP/LLDP neighbor data and generate a complete network topology structure.",
            f"\nTotal devices: {topology_data.get('total_devices', 0)}",
            f"\n\nCDP/LLDP Neighbor Data (ONLY - no VLAN, no interface IPs, no routing data):"
        ]
        
        # Include device info with CDP/LLDP neighbors only (up to reasonable size)
        devices_json = json.dumps(devices, separators=(',', ':'), ensure_ascii=False)
        # Limit to ~4000 chars to keep prompt manageable but informative
        if len(devices_json) > 4000:
            prompt_parts.append(f"\n{devices_json[:4000]}... (truncated)")
        else:
            prompt_parts.append(f"\n{devices_json}")
        
        prompt_parts.append(
            "\n\nIMPORTANT: Use ONLY CDP/LLDP neighbor relationships to create topology edges."
            "\nDO NOT use VLAN information, interface IP addresses, or routing protocol data."
            "\nCreate edges based solely on the neighbor relationships shown above."
            "\nReturn ONLY the JSON object with nodes and edges as specified in the system prompt."
        )
        
        return "".join(prompt_parts)
    
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
            # Filter only CDP/LLDP neighbors (exclude routing protocol neighbors)
            for neighbor in neighbors:
                neighbor_name = neighbor.get("device_name")
                if not neighbor_name or neighbor_name not in device_map:
                    continue
                
                # Only process neighbors with local_port/remote_port (CDP/LLDP indicators)
                local_port = neighbor.get("local_port") or neighbor.get("local_interface")
                remote_port = neighbor.get("remote_port") or neighbor.get("remote_interface")
                
                # Skip routing protocol neighbors (no port info) - use ONLY CDP/LLDP
                if not local_port and not remote_port:
                    continue
                
                # Create edge key to avoid duplicates
                edge_key = tuple(sorted([device_name, neighbor_name]))
                if edge_key not in edge_set:
                    edge_set.add(edge_key)
                    edges.append({
                        "from": device_name,
                        "to": neighbor_name,
                        "label": f"{local_port}-{remote_port}" if local_port and remote_port else "",
                        "evidence": f"CDP/LLDP neighbor: {device_name} sees {neighbor_name}"
                        })
        
        # NO subnet matching - use ONLY CDP/LLDP neighbors
        # This ensures topology matches actual physical connections
        
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
                "num_predict": 256,  # Minimal output for fastest response within Ollama's ~60s server timeout
            }
        }
        
        # Use LLM for topology by default (TOPOLOGY_USE_LLM=true). Fallback to rule-based on error or if disabled.
        llm_success = False
        topology_data = None
        analysis_summary = ""
        token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        use_llm = _topology_use_llm()
        timeout_sec = _ollama_timeout_seconds()

        start_time = time.time()

        if use_llm:
            try:
                timeout = httpx.Timeout(
                    connect=30.0,
                    read=timeout_sec,
                    write=120.0,
                    pool=60.0,
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
                        print(f"[Topology] LLM Response Preview: {json.dumps(topology_data, indent=2, ensure_ascii=False)[:1000]}")
                        
                    except (json.JSONDecodeError, ValueError) as e:
                        print(f"[Topology] Failed to parse LLM JSON response: {e}")
                        print(f"[Topology] Response preview: {ai_response[:500]}")
                        llm_success = False
                        
            except httpx.ReadTimeout:
                print(f"[Topology] Ollama read timeout ({int(timeout_sec)}s) - falling back to rule-based topology")
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
        
        # Calculate inference time (even if LLM was skipped)
        inference_time_ms = (time.time() - start_time) * 1000
        
        # Use rule-based topology (default - fast, reliable, no timeout)
        # Skip LLM entirely if use_llm is False
        if not use_llm or not llm_success or not topology_data:
            print(f"[Topology] Using rule-based topology generation (LLM disabled: use_llm={use_llm})")
            rule_based_result = self._generate_rule_based_topology(devices_data)
            topology_data = rule_based_result
            analysis_summary = f"Topology generated using rule-based method from {len(devices_data)} devices (LLDP/CDP neighbors and subnet matching). Fast and reliable."
        elif llm_success and topology_data:
            # LLM succeeded - use its result
            analysis_summary = topology_data.get("analysis_summary", "") or f"Topology generated successfully using LLM ({len(topology_data.get('nodes', []))} nodes, {len(topology_data.get('edges', []))} edges)"
            
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
            
            # CRITICAL: Validate edges against neighbor data to prevent hallucination
            validated_edges = self._validate_edges_against_neighbors(
                topology_data.get("edges", []),
                devices_data
            )
            
            topology_data = {
                "nodes": validated_nodes,
                "edges": validated_edges
            }
        
        print(f"[Topology] Final topology: {len(topology_data.get('nodes', []))} nodes, {len(topology_data.get('edges', []))} edges, time: {inference_time_ms:.0f}ms")
        
        # Prepare metrics
        metrics = {
            "inference_time_ms": inference_time_ms,
            "devices_processed": len(devices_data),
            "token_usage": token_usage,
            "model_name": self.model_name,
            "timestamp": datetime.utcnow()
        }
        
        # Save LLM result to database (persistent storage) - metrics included in result
        await self._save_llm_result(
            project_id=project_id,
            result_type="topology",
            result_data=topology_data,
            analysis_summary=analysis_summary,
            metrics=metrics,
            llm_used=use_llm and llm_success
        )
        
        return {
            "topology": topology_data,
            "analysis_summary": analysis_summary,
            "metrics": metrics
        }
    
    def _validate_edges_against_neighbors(
        self,
        llm_edges: List[Dict[str, Any]],
        devices_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Validate LLM-generated edges against actual neighbor data.
        Remove edges that don't exist in neighbor data (hallucination).
        
        Returns only edges that are confirmed by neighbor relationships.
        """
        # Build neighbor relationship map: device -> set of neighbor device names
        # Normalize device names (lowercase, strip) for consistent matching
        device_name_map = {}  # normalized -> original
        neighbor_map = {}
        
        for device in devices_data:
            device_name = device.get("device_name")
            if not device_name:
                continue
            device_name_normalized = str(device_name).strip().lower()
            device_name_map[device_name_normalized] = device_name
            
            neighbors = device.get("neighbors", [])
            neighbor_set = set()
            for neighbor in neighbors:
                # Only process CDP/LLDP neighbors (have local_port/remote_port)
                local_port = neighbor.get("local_port") or neighbor.get("local_interface")
                remote_port = neighbor.get("remote_port") or neighbor.get("remote_interface")
                
                # Skip routing protocol neighbors (no port info) - use ONLY CDP/LLDP
                if not local_port and not remote_port:
                    continue
                
                # Try multiple field names for neighbor device name
                neighbor_name = (
                    neighbor.get("device_name") or 
                    neighbor.get("neighbor_device") or 
                    neighbor.get("remote_device") or
                    neighbor.get("system_name")
                )
                if neighbor_name:
                    neighbor_set.add(str(neighbor_name).strip().lower())
            if neighbor_set:
                neighbor_map[device_name_normalized] = neighbor_set
        
        # Validate each edge
        validated_edges = []
        removed_count = 0
        removed_edges = []
        
        for edge in llm_edges:
            if not isinstance(edge, dict) or "from" not in edge or "to" not in edge:
                continue
            
            from_dev = str(edge["from"]).strip()
            to_dev = str(edge["to"]).strip()
            
            if not from_dev or not to_dev or from_dev == to_dev:
                continue
            
            # Normalize device names for matching
            from_dev_norm = from_dev.lower()
            to_dev_norm = to_dev.lower()
            
            # Check if this edge exists in neighbor data
            # Edge A->B is valid if: A has neighbor B OR B has neighbor A (bidirectional)
            is_valid = (
                (from_dev_norm in neighbor_map and to_dev_norm in neighbor_map[from_dev_norm]) or
                (to_dev_norm in neighbor_map and from_dev_norm in neighbor_map[to_dev_norm])
            )
            
            if is_valid:
                # Use original device names (not normalized) in output
                validated_edges.append({
                    "from": device_name_map.get(from_dev_norm, from_dev),
                    "to": device_name_map.get(to_dev_norm, to_dev),
                    "label": edge.get("label", ""),
                    "evidence": edge.get("evidence", "neighbor")
                })
            else:
                removed_count += 1
                removed_edges.append(f"{from_dev}->{to_dev}")
        
        if removed_count > 0:
            print(f"[Topology] Removed {removed_count} hallucinated edge(s) not in neighbor data: {', '.join(removed_edges[:5])}")
        
        return validated_edges
    
    async def get_network_topology_fast(self, project_id: str) -> Dict[str, Any]:
        """
        Fetch network topology from DB only (rule-based, no LLM).
        Returns immediately with nodes/edges from parsed_configs.
        Use this for instant graph display; call generate_topology (LLM) separately for AI analysis.
        """
        project = await db()["projects"].find_one({"project_id": project_id})
        if not project:
            return {
                "topology": {"nodes": [], "edges": []},
                "layout": {"positions": {}, "links": [], "node_labels": {}, "node_roles": {}},
                "generated_at": None,
                "llm_used": False,
            }
        devices_cursor = db()["parsed_configs"].find(
            {"project_id": project_id},
            sort=[("device_name", 1)]
        )
        devices_data = []
        device_names = set()
        async for device_doc in devices_cursor:
            device_doc.pop("_id", None)
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
                "layout": {
                    "positions": project.get("topoPositions", {}),
                    "links": project.get("topoLinks", []),
                    "node_labels": project.get("topoNodeLabels", {}),
                    "node_roles": project.get("topoNodeRoles", {}),
                },
                "generated_at": None,
                "llm_used": False,
            }
        topology_data = self._generate_rule_based_topology(devices_data)
        return {
            "topology": topology_data,
            "layout": {
                "positions": project.get("topoPositions", {}),
                "links": project.get("topoLinks", []),
                "node_labels": project.get("topoNodeLabels", {}),
                "node_roles": project.get("topoNodeRoles", {}),
            },
            "generated_at": None,
            "llm_used": False,
        }
    
    async def _save_llm_result(
        self,
        project_id: str,
        result_type: str,
        result_data: Dict[str, Any],
        analysis_summary: str,
        metrics: Dict[str, Any],
        llm_used: bool
    ):
        """
        Save LLM result to database - unified storage for all LLM analysis results.
        Metrics are included in the result, no separate performance_logs collection.
        
        Args:
            project_id: Project ID
            result_type: Type of LLM analysis (e.g., "topology", "config_analysis", etc.)
            result_data: The actual result data (e.g., topology nodes/edges, analysis content)
            analysis_summary: Summary text from LLM
            metrics: LLM performance metrics (inference_time_ms, token_usage, model_name, etc.)
            llm_used: Whether LLM was actually used
        """
        try:
            llm_result = {
                "project_id": project_id,
                "result_type": result_type,
                "result_data": result_data,
                "analysis_summary": analysis_summary,
                "metrics": metrics,  # All LLM metrics stored here (no separate performance_logs)
                "llm_used": llm_used,
                "generated_at": datetime.utcnow(),
                "version": 1  # For future versioning
            }
            
            # Save to llm_results collection (latest result per project per result_type)
            await db()["llm_results"].update_one(
                {"project_id": project_id, "result_type": result_type},
                {"$set": llm_result},
                upsert=True
            )
            
            if result_type == "topology":
                nodes_count = len(result_data.get('nodes', []))
                edges_count = len(result_data.get('edges', []))
                print(f"[Topology] Saved LLM result to database: {nodes_count} nodes, {edges_count} edges")
            else:
                print(f"[LLM] Saved {result_type} result to database")
        except Exception as e:
            print(f"Warning: Failed to save LLM result: {e}")


# Singleton instance
topology_service = TopologyService()
