#!/usr/bin/env python3
"""
Test script to debug LLM topology generation step by step.
Tests each component individually to identify issues.
"""

import asyncio
import httpx
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.settings import settings
from app.db.mongo import connect, close, db


async def test_ollama_connection():
    """Test 1: Check if Ollama is accessible"""
    print("\n" + "="*60)
    print("TEST 1: Testing Ollama Connection")
    print("="*60)
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test basic connection
            response = await client.get(f"{settings.AI_MODEL_ENDPOINT}/api/tags")
            response.raise_for_status()
            print(f"✅ Ollama is accessible at {settings.AI_MODEL_ENDPOINT}")
            
            # Check if model is available
            models_data = response.json()
            models = [m.get("name", "") for m in models_data.get("models", [])]
            print(f"📦 Available models: {models}")
            
            if settings.AI_MODEL_NAME in models:
                print(f"✅ Model '{settings.AI_MODEL_NAME}' is available")
                return True
            else:
                print(f"❌ Model '{settings.AI_MODEL_NAME}' NOT found!")
                print(f"   Available models: {models}")
                return False
                
    except httpx.ConnectError as e:
        print(f"❌ Cannot connect to Ollama: {e}")
        print(f"   Endpoint: {settings.AI_MODEL_ENDPOINT}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_simple_llm_call():
    """Test 2: Test simple LLM call"""
    print("\n" + "="*60)
    print("TEST 2: Testing Simple LLM Call")
    print("="*60)
    
    url = f"{settings.AI_MODEL_ENDPOINT}/api/chat"
    payload = {
        "model": settings.AI_MODEL_NAME,
        "messages": [
            {"role": "user", "content": "Say hello and return JSON: {\"status\": \"ok\"}"}
        ],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.1,
            "num_predict": 100,
        }
    }
    
    try:
        timeout = httpx.Timeout(connect=30.0, read=60.0, write=30.0, pool=30.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            print(f"📤 Sending request to {url}")
            print(f"   Model: {settings.AI_MODEL_NAME}")
            
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            print(f"✅ LLM responded successfully")
            print(f"   Response: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
            
            content = data.get("message", {}).get("content", "")
            print(f"\n📝 Content preview: {content[:200]}")
            
            return True
            
    except httpx.ReadTimeout:
        print(f"❌ LLM read timeout (60s)")
        return False
    except httpx.ConnectTimeout:
        print(f"❌ Connection timeout")
        return False
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP error: {e.response.status_code}")
        print(f"   Response: {e.response.text[:200]}")
        return False
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_topology_llm_with_sample_data():
    """Test 3: Test topology LLM with sample neighbor data"""
    print("\n" + "="*60)
    print("TEST 3: Testing Topology LLM with Sample Data")
    print("="*60)
    
    # Sample neighbor data (minimal)
    sample_data = {
        "total_devices": 2,
        "devices": [
            {
                "device_id": "SWITCH1",
                "hostname": "SWITCH1",
                "neighbors": [
                    {
                        "device_name": "SWITCH2",
                        "local_port": "GE0/0/1",
                        "remote_port": "GE0/0/2"
                    }
                ]
            },
            {
                "device_id": "SWITCH2",
                "hostname": "SWITCH2",
                "neighbors": [
                    {
                        "device_name": "SWITCH1",
                        "local_port": "GE0/0/2",
                        "remote_port": "GE0/0/1"
                    }
                ]
            }
        ]
    }
    
    system_prompt = """You are a Network Topology Engineer. Analyze LLDP/CDP neighbor data and create network topology.

CRITICAL RULES:
1. CREATE EDGES FROM NEIGHBORS:
   - For each neighbor entry, create an edge from device to neighbor device
   - Use format: "local_port-remote_port" for label (e.g., "GE0/0/1-GE0/0/4")
   - Evidence: "LLDP/CDP neighbor: device_name sees neighbor_name on local_port"

2. OUTPUT FORMAT (ONLY JSON, no markdown):
{
  "nodes": [
    {"id": "device_name", "label": "device_name", "type": "Core|Distribution|Access|Router|Switch"},
    ...
  ],
  "edges": [
    {"from": "device_a", "to": "device_b", "label": "local_port-remote_port", "evidence": "LLDP neighbor match"},
    ...
  ],
  "analysis_summary": "Brief summary"
}

3. DEVICE TYPE: Use "Core", "Distribution", "Access", "Router", or "Switch" based on device name patterns.

4. ACCURACY: Only create edges from neighbor data. Do NOT invent links."""
    
    user_prompt = f"""Analyze the neighbor data below and create topology edges.

Neighbor Data:
{json.dumps(sample_data, indent=2)}

Create nodes for all devices mentioned in neighbors.
Create edges based on neighbor relationships.
Return ONLY valid JSON, no markdown, no code blocks."""
    
    url = f"{settings.AI_MODEL_ENDPOINT}/api/chat"
    payload = {
        "model": settings.AI_MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.1,
            "top_p": 0.8,
            "num_predict": 1536,
        }
    }
    
    try:
        timeout = httpx.Timeout(connect=30.0, read=600.0, write=120.0, pool=120.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            print(f"📤 Sending topology request to LLM...")
            print(f"   Sample data: {len(sample_data['devices'])} devices")
            
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            print(f"✅ LLM responded")
            print(f"   Response time: {data.get('total_duration', 0) / 1e9:.2f}s")
            
            ai_response = data.get("message", {}).get("content", "")
            print(f"\n📝 Raw response preview: {ai_response[:500]}")
            
            # Try to parse JSON
            try:
                content_cleaned = ai_response.strip()
                if content_cleaned.startswith("```"):
                    lines = content_cleaned.split("\n")
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    content_cleaned = "\n".join(lines).strip()
                
                topology_data = json.loads(content_cleaned)
                print(f"\n✅ Successfully parsed JSON!")
                print(f"   Nodes: {len(topology_data.get('nodes', []))}")
                print(f"   Edges: {len(topology_data.get('edges', []))}")
                print(f"\n📊 Topology data:")
                print(json.dumps(topology_data, indent=2, ensure_ascii=False))
                return True
                
            except json.JSONDecodeError as e:
                print(f"\n❌ Failed to parse JSON: {e}")
                print(f"   Full response: {ai_response}")
                return False
                
    except httpx.ReadTimeout:
        print(f"❌ LLM read timeout (600s)")
        return False
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_project_data(project_id: str):
    """Test 4: Check project data in MongoDB"""
    print("\n" + "="*60)
    print(f"TEST 4: Checking Project Data (project_id: {project_id})")
    print("="*60)
    
    try:
        await connect()
        
        # Check project exists
        project = await db()["projects"].find_one({"project_id": project_id})
        if not project:
            print(f"❌ Project '{project_id}' not found!")
            return False
        
        print(f"✅ Project found: {project.get('name', 'N/A')}")
        
        # Check parsed_configs
        devices_cursor = db()["parsed_configs"].find(
            {"project_id": project_id},
            sort=[("device_name", 1)]
        )
        
        devices_data = []
        async for device_doc in devices_cursor:
            device_doc.pop("_id", None)
            devices_data.append(device_doc)
        
        print(f"📦 Found {len(devices_data)} devices")
        
        if not devices_data:
            print(f"❌ No devices found in project!")
            return False
        
        # Show device summary
        for i, device in enumerate(devices_data[:5]):  # Show first 5
            device_name = device.get("device_name", "N/A")
            neighbors = device.get("neighbors", [])
            print(f"   {i+1}. {device_name}: {len(neighbors)} neighbors")
        
        if len(devices_data) > 5:
            print(f"   ... and {len(devices_data) - 5} more devices")
        
        # Count total neighbors
        total_neighbors = sum(len(d.get("neighbors", [])) for d in devices_data)
        print(f"\n📊 Total neighbors: {total_neighbors}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_topology_api_endpoint(project_id: str, token: str):
    """Test 5: Test actual API endpoint"""
    print("\n" + "="*60)
    print(f"TEST 5: Testing Topology API Endpoint")
    print("="*60)
    
    url = f"http://localhost:8000/projects/{project_id}/topology/generate"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        timeout = httpx.Timeout(connect=30.0, read=600.0, write=120.0, pool=120.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            print(f"📤 Calling API: POST {url}")
            
            response = await client.post(url, headers=headers)
            
            print(f"📥 Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Success!")
                print(f"   Topology nodes: {len(data.get('topology', {}).get('nodes', []))}")
                print(f"   Topology edges: {len(data.get('topology', {}).get('edges', []))}")
                print(f"   Analysis summary: {data.get('analysis_summary', 'N/A')[:100]}")
                print(f"\n📊 Full response:")
                print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])
                return True
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"   Response: {response.text[:500]}")
                return False
                
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("TOPOLOGY LLM DEBUG TEST SUITE")
    print("="*60)
    
    # Get project_id from command line or use default
    project_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    if not project_id:
        print("\n❌ Usage: python test_topology_llm.py <project_id> [token]")
        print("   Example: python test_topology_llm.py 14d2baf4-5e75-4e5f-9fed-c42a8c1f70a2")
        return
    
    token = sys.argv[2] if len(sys.argv) > 2 else None
    
    results = []
    
    # Test 1: Ollama connection
    results.append(("Ollama Connection", await test_ollama_connection()))
    
    # Test 2: Simple LLM call
    if results[-1][1]:  # Only if Ollama is accessible
        results.append(("Simple LLM Call", await test_simple_llm_call()))
    
    # Test 3: Topology LLM with sample data
    if results[-1][1]:  # Only if simple call works
        results.append(("Topology LLM (Sample)", await test_topology_llm_with_sample_data()))
    
    # Test 4: Project data
    results.append(("Project Data", await test_project_data(project_id)))
    
    # Test 5: API endpoint (if token provided)
    if token:
        results.append(("API Endpoint", await test_topology_api_endpoint(project_id, token)))
    else:
        print("\n⚠️  Skipping API endpoint test (no token provided)")
        print("   To test API endpoint, provide token as second argument")
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    await close()


if __name__ == "__main__":
    asyncio.run(main())
