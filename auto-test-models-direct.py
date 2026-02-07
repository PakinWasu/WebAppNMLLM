#!/usr/bin/env python3
"""
Automatically test all Ollama models and select the best one.
Tests models directly using LLM service without requiring projects.
"""

import os
import sys
import asyncio
import httpx
import json
import time
from datetime import datetime

# Add app to path
sys.path.insert(0, '/app')

from app.services.llm_service import LLMService

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://10.4.15.52:11434")
BACKEND_ENV = "/app/.env"

# Sample test data (simplified network config)
SAMPLE_DEVICES_DATA = [
    {
        "device_id": "test-switch-01",
        "hostname": "SW-CORE-01",
        "parsed_config": {
            "device_overview": {
                "hostname": "SW-CORE-01",
                "vendor": "Cisco",
                "model": "Catalyst 9300",
                "role": "core"
            },
            "interfaces": [
                {"name": "GigabitEthernet0/1", "status": "up", "description": "Link to DIST-01"},
                {"name": "GigabitEthernet0/2", "status": "up", "description": "Link to DIST-02"}
            ],
            "vlans": [{"id": 10, "name": "VLAN10"}, {"id": 20, "name": "VLAN20"}],
            "routing": {"protocol": "OSPF", "area": 0}
        }
    },
    {
        "device_id": "test-switch-02",
        "hostname": "SW-DIST-01",
        "parsed_config": {
            "device_overview": {
                "hostname": "SW-DIST-01",
                "vendor": "Cisco",
                "model": "Catalyst 2960",
                "role": "distribution"
            },
            "interfaces": [
                {"name": "GigabitEthernet0/1", "status": "up", "description": "Link to CORE-01"},
                {"name": "GigabitEthernet0/2", "status": "down", "description": "Unused"}
            ],
            "vlans": [{"id": 10, "name": "VLAN10"}]
        }
    }
]

TEST_PROJECT_ID = "test-comparison-project"


async def get_available_models():
    """Get list of available models from Ollama server."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = [model["name"] for model in data.get("models", [])]
                return models
            return []
    except Exception as e:
        print(f"Error fetching models: {e}")
        return []


async def test_model_overview(model_name, devices_data):
    """Test model on overview analysis."""
    llm_service = LLMService()
    llm_service.model_name = model_name
    
    start_time = time.time()
    try:
        result = await llm_service.analyze_project_overview(
            devices_data=devices_data,
            project_id=TEST_PROJECT_ID
        )
        elapsed_time = time.time() - start_time
        
        overview_text = result.get("overview_text", "")
        metrics = result.get("metrics", {})
        
        return {
            "success": True,
            "elapsed_time": elapsed_time,
            "overview_length": len(overview_text),
            "overview_text": overview_text[:200] + "..." if len(overview_text) > 200 else overview_text,
            "metrics": metrics,
            "error": None
        }
    except Exception as e:
        elapsed_time = time.time() - start_time
        return {
            "success": False,
            "elapsed_time": elapsed_time,
            "overview_length": 0,
            "overview_text": "",
            "metrics": {},
            "error": str(e)
        }


async def test_model_recommendations(model_name, devices_data):
    """Test model on recommendations analysis."""
    llm_service = LLMService()
    llm_service.model_name = model_name
    
    start_time = time.time()
    try:
        result = await llm_service.analyze_project_recommendations(
            devices_data=devices_data,
            project_id=TEST_PROJECT_ID
        )
        elapsed_time = time.time() - start_time
        
        recommendations = result.get("recommendations", [])
        metrics = result.get("metrics", {})
        
        return {
            "success": True,
            "elapsed_time": elapsed_time,
            "recommendations_count": len(recommendations),
            "recommendations": recommendations[:3] if recommendations else [],  # First 3 for preview
            "metrics": metrics,
            "error": None
        }
    except Exception as e:
        elapsed_time = time.time() - start_time
        return {
            "success": False,
            "elapsed_time": elapsed_time,
            "recommendations_count": 0,
            "recommendations": [],
            "metrics": {},
            "error": str(e)
        }


def calculate_score(result):
    """Calculate quality score for a model."""
    score = 0
    
    # Overview success (3 points)
    if result["overview"]["success"]:
        score += 3
        # Overview quality based on length (2 points)
        if result["overview"]["overview_length"] > 200:
            score += 2
        elif result["overview"]["overview_length"] > 100:
            score += 1
    
    # Recommendations success (3 points)
    if result["recommendations"]["success"]:
        score += 3
        # Recommendations quality based on count (2 points)
        if result["recommendations"]["recommendations_count"] > 3:
            score += 2
        elif result["recommendations"]["recommendations_count"] > 0:
            score += 1
    
    # Speed bonus (if both succeed and fast)
    if result["overview"]["success"] and result["recommendations"]["success"]:
        avg_time = (result["overview"]["elapsed_time"] + result["recommendations"]["elapsed_time"]) / 2
        if avg_time < 30:
            score += 2
        elif avg_time < 60:
            score += 1
    
    return min(score, 10)  # Cap at 10


async def main():
    print("=" * 80)
    print("Automatic Ollama Model Testing")
    print("=" * 80)
    print(f"Ollama Server: {OLLAMA_URL}")
    print(f"Test Time: {datetime.now().isoformat()}")
    print()
    
    # Get available models
    print("[1/4] Fetching available models...")
    models = await get_available_models()
    
    if not models:
        print("Error: No models found or cannot connect to Ollama server")
        return
    
    print(f"Found {len(models)} models:")
    for model in models:
        print(f"  - {model}")
    print()
    
    # Test each model
    print("[2/4] Testing models...")
    print("This will take 5-10 minutes per model...")
    print()
    
    results = []
    
    for i, model_name in enumerate(models, 1):
        print("-" * 80)
        print(f"[{i}/{len(models)}] Testing: {model_name}")
        print("-" * 80)
        
        # Test Overview
        print("  Testing Overview analysis...")
        overview_result = await test_model_overview(model_name, SAMPLE_DEVICES_DATA)
        
        if overview_result["success"]:
            print(f"    ✓ Success: {overview_result['elapsed_time']:.2f}s")
            print(f"    ✓ Length: {overview_result['overview_length']} chars")
            if overview_result.get("metrics"):
                tokens = overview_result["metrics"].get("total_tokens", "N/A")
                print(f"    ✓ Tokens: {tokens}")
        else:
            print(f"    ✗ Failed: {overview_result['error']}")
        
        # Wait a bit
        await asyncio.sleep(2)
        
        # Test Recommendations
        print("  Testing Recommendations analysis...")
        rec_result = await test_model_recommendations(model_name, SAMPLE_DEVICES_DATA)
        
        if rec_result["success"]:
            print(f"    ✓ Success: {rec_result['elapsed_time']:.2f}s")
            print(f"    ✓ Recommendations: {rec_result['recommendations_count']}")
            if rec_result.get("metrics"):
                tokens = rec_result["metrics"].get("total_tokens", "N/A")
                print(f"    ✓ Tokens: {tokens}")
        else:
            print(f"    ✗ Failed: {rec_result['error']}")
        
        # Calculate score
        model_result = {
            "model": model_name,
            "overview": overview_result,
            "recommendations": rec_result
        }
        model_result["score"] = calculate_score(model_result)
        
        avg_time = "N/A"
        if overview_result["success"] and rec_result["success"]:
            avg_time = (overview_result["elapsed_time"] + rec_result["elapsed_time"]) / 2
        
        print(f"  Score: {model_result['score']}/10")
        if avg_time != "N/A":
            print(f"  Average Time: {avg_time:.2f}s")
        print()
        
        results.append(model_result)
        
        # Wait before next model
        await asyncio.sleep(3)
    
    # Find best model
    print("[3/4] Analyzing results...")
    print()
    
    best_model = None
    best_score = 0
    best_time = float('inf')
    
    for result in results:
        score = result["score"]
        avg_time = float('inf')
        if result["overview"]["success"] and result["recommendations"]["success"]:
            avg_time = (result["overview"]["elapsed_time"] + result["recommendations"]["elapsed_time"]) / 2
        
        if score > best_score or (score == best_score and avg_time < best_time):
            best_model = result
            best_score = score
            best_time = avg_time
    
    # Print summary
    print("[4/4] Summary")
    print("=" * 80)
    print()
    print(f"{'Model':<25} {'Overview':<15} {'Rec':<15} {'Avg Time':<12} {'Score':<10}")
    print("-" * 80)
    
    for result in results:
        ov_status = "✗"
        if result["overview"]["success"]:
            ov_status = f"✓ {result['overview']['elapsed_time']:.1f}s"
        
        rec_status = "✗"
        if result["recommendations"]["success"]:
            rec_status = f"✓ {result['recommendations']['elapsed_time']:.1f}s"
        
        avg_time = "N/A"
        if result["overview"]["success"] and result["recommendations"]["success"]:
            avg_time = f"{(result['overview']['elapsed_time'] + result['recommendations']['elapsed_time']) / 2:.1f}s"
        
        print(f"{result['model']:<25} {ov_status:<15} {rec_status:<15} {avg_time:<12} {result['score']}/10")
    
    print()
    print("=" * 80)
    if best_model:
        print(f"🏆 BEST MODEL: {best_model['model']}")
        print(f"   Score: {best_model['score']}/10")
        if best_time != float('inf'):
            print(f"   Average Time: {best_time:.2f}s")
        print()
        print("Overview sample:")
        if best_model["overview"]["overview_text"]:
            print(f"  {best_model['overview']['overview_text'][:300]}...")
        print()
        print("Recommendations sample:")
        for rec in best_model["recommendations"]["recommendations"][:2]:
            print(f"  - {rec.get('message', rec.get('recommendation', 'N/A'))[:100]}...")
    else:
        print("⚠️  Could not determine best model")
    print("=" * 80)
    print()
    
    # Save results
    output_file = f"/app/model_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w") as f:
        json.dump({
            "test_time": datetime.now().isoformat(),
            "ollama_url": OLLAMA_URL,
            "models_tested": [r["model"] for r in results],
            "results": results,
            "best_model": best_model["model"] if best_model else None,
            "best_score": best_score
        }, f, indent=2)
    
    print(f"Detailed results saved to: {output_file}")
    print()
    
    # Update .env file
    if best_model:
        print(f"Updating backend/.env to use: {best_model['model']}")
        try:
            with open(BACKEND_ENV, "r") as f:
                content = f.read()
            
            import re
            new_content = re.sub(
                r'^OLLAMA_MODEL=.*',
                f'OLLAMA_MODEL={best_model["model"]}',
                content,
                flags=re.MULTILINE
            )
            
            with open(BACKEND_ENV, "w") as f:
                f.write(new_content)
            
            print("✅ Backend/.env updated successfully")
            print()
            print("Please restart backend to apply changes:")
            print("  docker compose -f docker-compose.prod.yml restart backend")
        except Exception as e:
            print(f"⚠️  Could not update .env file: {e}")
            print(f"   Please manually update OLLAMA_MODEL={best_model['model']} in backend/.env")


if __name__ == "__main__":
    asyncio.run(main())
