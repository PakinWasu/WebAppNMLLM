#!/usr/bin/env python3
"""Test script to verify parser is working correctly"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.config_parser import ConfigParser

def test_parser():
    """Test parser with a sample log file"""
    parser = ConfigParser()
    
    # Test with ACC1 log file
    test_file = Path(__file__).parent.parent.parent / "test_config" / "2026-01-11_topo_realACC1.log"
    
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return False
    
    print(f"📄 Reading test file: {test_file.name}")
    with open(test_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    print(f"📊 File size: {len(content)} characters")
    
    # Test vendor detection
    print("\n🔍 Testing vendor detection...")
    huawei_parser = parser.parsers[0]  # HuaweiParser
    is_huawei = huawei_parser.detect_vendor(content)
    print(f"   Is Huawei: {is_huawei}")
    
    if not is_huawei:
        print("❌ Vendor detection failed!")
        return False
    
    # Test parsing
    print("\n🔧 Testing parser...")
    try:
        parsed_data = parser.parse_config(content, test_file.name)
        
        if not parsed_data:
            print("❌ Parser returned None!")
            return False
        
        print(f"✅ Parser returned data")
        print(f"   Vendor: {parsed_data.get('vendor', 'N/A')}")
        
        # Extract device name
        device_name = parser.extract_device_name(content, test_file.name)
        print(f"   Device name: {device_name}")
        
        # Check structure
        overview = parsed_data.get("device_overview", {})
        interfaces = parsed_data.get("interfaces", [])
        vlans = parsed_data.get("vlans", {})
        stp = parsed_data.get("stp", {})
        routing = parsed_data.get("routing", {})
        
        print(f"\n📋 Parsed Data Summary:")
        print(f"   Hostname: {overview.get('hostname', 'N/A')}")
        print(f"   Role: {overview.get('role', 'N/A')}")
        print(f"   Model: {overview.get('model', 'N/A')}")
        print(f"   OS Version: {overview.get('os_version', 'N/A')}")
        print(f"   Management IP: {overview.get('management_ip', 'N/A')}")
        print(f"   CPU Utilization: {overview.get('cpu_utilization', 'N/A')}")
        print(f"   Interfaces: {len(interfaces)}")
        print(f"   VLANs: {vlans.get('total_vlan_count', 0)}")
        print(f"   STP Mode: {stp.get('stp_mode', 'N/A')}")
        print(f"   Static Routes: {len(routing.get('static', []))}")
        print(f"   OSPF: {routing.get('ospf') is not None}")
        print(f"   BGP: {routing.get('bgp') is not None}")
        
        # Check for None values (should be None, not defaults)
        print(f"\n🔍 Checking for None values (strict mode):")
        none_fields = []
        for key, value in overview.items():
            if value is None:
                none_fields.append(key)
        
        if none_fields:
            print(f"   Fields with None: {', '.join(none_fields)}")
        else:
            print(f"   All fields have values")
        
        return True
        
    except Exception as e:
        print(f"❌ Parser error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Parser Test Script")
    print("=" * 60)
    
    success = test_parser()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Test PASSED")
    else:
        print("❌ Test FAILED")
    print("=" * 60)
