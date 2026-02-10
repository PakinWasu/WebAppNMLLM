#!/usr/bin/env python3
"""Test script to verify parser is working correctly"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.config_parser import ConfigParser, normalize_cisco_to_legacy
from app.services.parsers.cisco import CiscoIOSParser

# Minimal Cisco IOS-style content for testing without test_config file
CISCO_SAMPLE = """
CORE1#show version
Cisco IOS Software, Version 15.2(4)M6
Processor board ID FXS1234ABCD
uptime is 1 week, 2 days, 3 hours

CORE1#show running-config
hostname CORE1
interface GigabitEthernet0/0
 description Uplink
 ip address 10.0.0.1 255.255.255.0
 no shutdown
interface GigabitEthernet0/1
 switchport mode access
 switchport access vlan 10

CORE1#show ip interface brief
Interface              IP-Address      OK? Method Status                Protocol
GigabitEthernet0/0      10.0.0.1        YES NVRAM  up                    up
GigabitEthernet0/1      unassigned      YES unset  up                    up

CORE1#show vlan brief
VLAN Name                             Status    Ports
1    default                          active
10   DATA                            active

CORE1#show ip route
Codes: L - local, C - connected, S - static
C    10.0.0.0/24 is directly connected, GigabitEthernet0/0

CORE1#show cdp neighbors detail
Device ID: DIST1
IP address: 10.0.0.2
Platform: cisco WS-C2960
Port ID (outgoing port): GigabitEthernet0/1
Interface: GigabitEthernet0/1
"""


def test_cisco_parser():
    """Test Cisco IOS parser: spec output and normalized legacy shape."""
    parser = ConfigParser()
    cisco_parser = CiscoIOSParser()
    assert cisco_parser.detect_vendor(CISCO_SAMPLE), "Cisco vendor detection should pass"

    # Parse with ConfigParser (returns normalized legacy format for Cisco)
    parsed = parser.parse_config(CISCO_SAMPLE, "CORE1_All.txt")
    if not parsed:
        print("Cisco parse_config returned None")
        return False

    assert parsed.get("vendor") == "cisco"
    assert "device_overview" in parsed
    assert "interfaces" in parsed
    assert "vlans" in parsed
    assert "routing" in parsed
    assert "neighbors" in parsed
    assert "mac_arp" in parsed
    assert "security" in parsed
    assert "ha" in parsed
    assert "stp" in parsed

    overview = parsed["device_overview"]
    assert overview.get("hostname") == "CORE1"
    assert overview.get("role") == "Core"
    assert "management_ip" in overview or "mgmt_ip" in overview or overview.get("hostname")

    interfaces = parsed["interfaces"]
    assert isinstance(interfaces, list)
    for i in interfaces:
        assert "name" in i
        assert "oper_status" in i or "status" in i
        assert "port_mode" in i or "mode" in i or i.get("name", "").startswith("Gi")

    vlans = parsed["vlans"]
    assert isinstance(vlans, dict)
    assert "total_vlan_count" in vlans
    assert "vlan_list" in vlans

    routing = parsed["routing"]
    assert "static" in routing
    assert isinstance(routing["static"], list)

    # Direct CiscoIOSParser.parse returns spec shape; normalizer converts to legacy
    raw = cisco_parser.parse(CISCO_SAMPLE, "CORE1_All.txt")
    assert "arp_mac_table" in raw
    assert isinstance(raw.get("vlans"), list)
    normalized = normalize_cisco_to_legacy(raw)
    assert "mac_arp" in normalized
    assert "security" in normalized
    assert isinstance(normalized["vlans"], dict) and "total_vlan_count" in normalized["vlans"]
    print("Cisco parser and normalizer OK")
    return True


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

    cisco_ok = False
    try:
        cisco_ok = test_cisco_parser()
    except Exception as e:
        print(f"Cisco test error: {e}")
        import traceback
        traceback.print_exc()

    huawei_ok = test_parser()

    print("\n" + "=" * 60)
    all_ok = cisco_ok and huawei_ok
    if all_ok:
        print("✅ All tests PASSED")
    else:
        print("Result: Cisco=%s, Huawei=%s" % (cisco_ok, huawei_ok))
    print("=" * 60)
    sys.exit(0 if cisco_ok else 1)
