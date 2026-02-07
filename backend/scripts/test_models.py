#!/usr/bin/env python3
"""
Test script to compare different Ollama models for network analysis tasks.
Tests models on real endpoints and compares performance metrics.
"""

import os
import sys
import asyncio
import httpx
import json
import time
from typing import Dict, List, Any
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.mongo import db
from app.services.llm_service import LLMService

# Ollama server URL
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://10.4.15.52:11434")

# Test models - add your models here
# These will be tested if they exist on the Ollama server
TEST_MODELS = [
    "deepseek-r1:7b",
    "qwen2.5:7b",
    "llama3.1:latest",
    # Add more models as needed
]

# Test project ID - use a real project ID from your database
TEST_PROJECT_ID = None  # Will be set from database


async def get_available_models() -> List[str]:
    """Get list of available models from Ollama server."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = [model["name"] for model in data.get("models", [])]
                return models
            else:
                print(f"Error fetching models: {response.status_code}")
                return []
    except Exception as e:
        print(f"Error connecting to Ollama server: {e}")
        return []


async def test_model_overview(model_name: str, project_id: str, devices_data: List[Dict]) -> Dict[str, Any]:
    """Test model on overview analysis task."""
    llm_service = LLMService()
    llm_service.model_name = model_name
    
    start_time = time.time()
    try:
        result = await llm_service.analyze_project_overview(
            devices_data=devices_data,
            project_id=project_id
        )
        elapsed_time = time.time() - start_time
        
        return {
            "success": True,
            "model": model_name,
            "task": "overview",
            "elapsed_time": elapsed_time,
            "metrics": result.get("metrics", {}),
            "overview_length": len(result.get("overview_text", "")),
            "error": None
        }
    except Exception as e:
        elapsed_time = time.time() - start_time
        return {
            "success": False,
            "model": model_name,
            "task": "overview",
            "elapsed_time": elapsed_time,
            "metrics": {},
            "overview_length": 0,
            "error": str(e)
        }


async def test_model_recommendations(model_name: str, project_id: str, devices_data: List[Dict]) -> Dict[str, Any]:
    """Test model on recommendations analysis task."""
    llm_service = LLMService()
    llm_service.model_name = model_name
    
    start_time = time.time()
    try:
        result = await llm_service.analyze_project_recommendations(
            devices_data=devices_data,
            project_id=project_id
        )
        elapsed_time = time.time() - start_time
        
        recommendations = result.get("recommendations", [])
        return {
            "success": True,
            "model": model_name,
            "task": "recommendations",
            "elapsed_time": elapsed_time,
            "metrics": result.get("metrics", {}),
            "recommendations_count": len(recommendations),
            "error": None
        }
    except Exception as e:
        elapsed_time = time.time() - start_time
        return {
            "success": False,
            "model": model_name,
            "task": "recommendations",
            "elapsed_time": elapsed_time,
            "metrics": {},
            "recommendations_count": 0,
            "error": str(e)
        }


async def get_test_project_data() -> tuple[str, List[Dict]]:
    """Get a test project ID and its device data."""
    try:
        # Get first project with devices
        project = await db()["projects"].find_one(
            {"summaryRows": {"$exists": True, "$ne": []}},
            sort=[("updated_at", -1)]
        )
        
        if not project:
            print("No projects found with devices. Please upload some configs first.")
            return None, []
        
        project_id = project.get("project_id") or project.get("_id")
        
        # Get device data
        devices = await db()["devices"].find(
            {"project_id": project_id}
        ).to_list(length=10)  # Limit to 10 devices for testing
        
        devices_data = []
        for device in devices:
            parsed_config = device.get("parsed_config", {})
            devices_data.append({
                "device_id": device.get("device_id"),
                "hostname": device.get("hostname", "Unknown"),
                "parsed_config": parsed_config
            })
        
        return str(project_id), devices_data
    except Exception as e:
        print(f"Error getting test project: {e}")
        return None, []


async def run_model_tests():
    """Run tests on all available models."""
    print("=" * 80)
    print("Ollama Model Comparison Test")
    print("=" * 80)
    print(f"Ollama Server: {OLLAMA_BASE_URL}")
    print(f"Test Time: {datetime.now().isoformat()}")
    print()
    
    # Get available models
    print("Fetching available models from Ollama server...")
    available_models = await get_available_models()
    
    if not available_models:
        print("No models found or cannot connect to Ollama server.")
        print("Available models will be tested from TEST_MODELS list.")
        models_to_test = TEST_MODELS
    else:
        print(f"Found {len(available_models)} models:")
        for model in available_models:
            print(f"  - {model}")
        print()
        
        # Filter to only test models that exist
        models_to_test = [m for m in TEST_MODELS if m in available_models]
        if not models_to_test:
            print("No matching models found. Testing all available models...")
            models_to_test = available_models[:5]  # Limit to first 5 for testing
    
    # Get test project data
    print("Getting test project data...")
    project_id, devices_data = await get_test_project_data()
    
    if not project_id or not devices_data:
        print("ERROR: Cannot get test project data. Exiting.")
        return
    
    print(f"Using project: {project_id}")
    print(f"Testing with {len(devices_data)} devices")
    print()
    
    # Run tests
    results = []
    
    for model_name in models_to_test:
        print(f"\n{'=' * 80}")
        print(f"Testing Model: {model_name}")
        print(f"{'=' * 80}")
        
        # Test Overview
        print(f"  [1/2] Testing Overview analysis...")
        overview_result = await test_model_overview(model_name, project_id, devices_data)
        results.append(overview_result)
        
        if overview_result["success"]:
            print(f"    ✓ Success: {overview_result['elapsed_time']:.2f}s")
            print(f"    ✓ Overview length: {overview_result['overview_length']} chars")
            if overview_result.get("metrics"):
                metrics = overview_result["metrics"]
                print(f"    ✓ Tokens: {metrics.get('total_tokens', 'N/A')}")
        else:
            print(f"    ✗ Failed: {overview_result['error']}")
        
        # Wait a bit between tests
        await asyncio.sleep(2)
        
        # Test Recommendations
        print(f"  [2/2] Testing Recommendations analysis...")
        rec_result = await test_model_recommendations(model_name, project_id, devices_data)
        results.append(rec_result)
        
        if rec_result["success"]:
            print(f"    ✓ Success: {rec_result['elapsed_time']:.2f}s")
            print(f"    ✓ Recommendations: {rec_result['recommendations_count']}")
            if rec_result.get("metrics"):
                metrics = rec_result["metrics"]
                print(f"    ✓ Tokens: {metrics.get('total_tokens', 'N/A')}")
        else:
            print(f"    ✗ Failed: {rec_result['error']}")
        
        # Wait before next model
        await asyncio.sleep(3)
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    # Group results by model
    model_summaries = {}
    for result in results:
        model = result["model"]
        if model not in model_summaries:
            model_summaries[model] = {"overview": None, "recommendations": None}
        
        if result["task"] == "overview":
            model_summaries[model]["overview"] = result
        elif result["task"] == "recommendations":
            model_summaries[model]["recommendations"] = result
    
    # Print comparison table
    print(f"\n{'Model':<30} {'Overview':<15} {'Rec':<15} {'Avg Time':<12} {'Status'}")
    print("-" * 80)
    
    for model, tasks in sorted(model_summaries.items()):
        overview = tasks["overview"]
        recommendations = tasks["recommendations"]
        
        overview_status = "✓" if overview and overview["success"] else "✗"
        rec_status = "✓" if recommendations and recommendations["success"] else "✗"
        
        overview_time = f"{overview['elapsed_time']:.1f}s" if overview and overview["success"] else "FAIL"
        rec_time = f"{recommendations['elapsed_time']:.1f}s" if recommendations and recommendations["success"] else "FAIL"
        
        avg_time = "N/A"
        if overview and overview["success"] and recommendations and recommendations["success"]:
            avg_time = f"{(overview['elapsed_time'] + recommendations['elapsed_time']) / 2:.1f}s"
        
        status = "✓" if overview_status == "✓" and rec_status == "✓" else "✗"
        
        print(f"{model:<30} {overview_status} {overview_time:<12} {rec_status} {rec_time:<12} {avg_time:<12} {status}")
    
    # Find best model
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    
    successful_models = []
    for model, tasks in model_summaries.items():
        if tasks["overview"] and tasks["overview"]["success"] and \
           tasks["recommendations"] and tasks["recommendations"]["success"]:
            avg_time = (tasks["overview"]["elapsed_time"] + tasks["recommendations"]["elapsed_time"]) / 2
            successful_models.append({
                "model": model,
                "avg_time": avg_time,
                "overview_time": tasks["overview"]["elapsed_time"],
                "rec_time": tasks["recommendations"]["elapsed_time"]
            })
    
    if successful_models:
        # Sort by average time
        successful_models.sort(key=lambda x: x["avg_time"])
        
        print("\nBest performing models (sorted by average time):")
        for i, model_info in enumerate(successful_models[:5], 1):
            print(f"{i}. {model_info['model']}")
            print(f"   Average time: {model_info['avg_time']:.2f}s")
            print(f"   Overview: {model_info['overview_time']:.2f}s")
            print(f"   Recommendations: {model_info['rec_time']:.2f}s")
            print()
        
        best_model = successful_models[0]["model"]
        print(f"🏆 RECOMMENDED MODEL: {best_model}")
        print(f"\nTo use this model, update your .env file:")
        print(f"OLLAMA_MODEL={best_model}")
    else:
        print("\n⚠️  No models completed both tests successfully.")
    
    # Save results to file
    output_file = f"model_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w") as f:
        json.dump({
            "test_time": datetime.now().isoformat(),
            "ollama_url": OLLAMA_BASE_URL,
            "project_id": project_id,
            "devices_count": len(devices_data),
            "results": results,
            "summary": model_summaries
        }, f, indent=2)
    
    print(f"\nDetailed results saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(run_model_tests())
