import json

# Read the updated JSON file
with open('DIST1_parsed huawei.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print('=== DHCP VERIFICATION ===')
dhcp_pools = data.get('dhcp_pools', [])
print(f'Number of DHCP pools: {len(dhcp_pools)}')

if dhcp_pools:
    for i, pool in enumerate(dhcp_pools, 1):
        print(f'\nPool {i}:')
        print(f'  Name: {pool.get("name", "N/A")}')
        print(f'  Network: {pool.get("network", "N/A")}')
        print(f'  Mask: {pool.get("mask", "N/A")}')
        print(f'  Gateway: {pool.get("gateway", "N/A")}')
        print(f'  DNS Servers: {pool.get("dns_servers", [])}')
        print(f'  Excluded Addresses: {pool.get("excluded_addresses", [])}')
        print(f'  Lease Time: {pool.get("lease_time", "N/A")}')
else:
    print('❌ No DHCP pools found')
