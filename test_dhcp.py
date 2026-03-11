from backend.app.services.parsers.huawei import HuaweiParser
import json

# Read the original config file
with open('topo-cisco/huawei1/acl/2026-01-27_topo_realDIST1.log', 'r', encoding='utf-8') as f:
    content = f.read()

# Parse with updated parser
parser = HuaweiParser()
result = parser.parse(content, 'test.log')

print('=== UPDATED DHCP PARSING ===')
dhcp_pools = result.get('dhcp_pools', [])
print(f'DHCP Pools count: {len(dhcp_pools)}')

for i, pool in enumerate(dhcp_pools, 1):
    print(f'\nPool {i}: {pool.get("name")}')
    print(f'  Network: {pool.get("network", "—")}')
    print(f'  Mask: {pool.get("mask", "—")}')
    print(f'  Gateway: {pool.get("gateway", "—")}')
    print(f'  DNS: {pool.get("dns_servers", [])}')
    print(f'  Excluded: {pool.get("excluded_addresses", [])}')
    print(f'  Lease: {pool.get("lease_time", "—")}')
