from backend.app.services.parsers.huawei import HuaweiParser
import json

# Test the current backend parser
with open('topo-cisco/huawei1/acl/2026-01-27_topo_realDIST1.log', 'r', encoding='utf-8') as f:
    content = f.read()

parser = HuaweiParser()
result = parser.parse(content, 'test.log')

print('=== BACKEND PARSER TEST ===')
print(f'DHCP Pools: {len(result.get("dhcp_pools", []))}')
print(f'ACLs: {len(result.get("acls", {}).get("basic", [])) + len(result.get("acls", {}).get("advanced", []))}')
print(f'NAT Policies: {len(result.get("nat_policies", []))}')

# Check if dhcp_pools has the new structure
if result.get('dhcp_pools'):
    pool = result['dhcp_pools'][0]
    print(f'First DHCP pool has network: {"network" in pool}')
    print(f'First DHCP pool has mask: {"mask" in pool}')
    print(f'First DHCP pool has lease_time: {"lease_time" in pool}')
    print(f'Network: {pool.get("network")}')
    print(f'Mask: {pool.get("mask")}')
    print(f'Lease: {pool.get("lease_time")}')
else:
    print('❌ No DHCP pools found')
