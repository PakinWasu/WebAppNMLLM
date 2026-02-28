/**
 * Enhanced Routing Display Component
 * Supports both legacy and standardized routing data structures
 * Handles Cisco and Huawei parser outputs
 */

import React from 'react';
import { Card, Badge, Table } from './ui';

export function RoutingSection({ routingData }) {
  if (!routingData) return null;

  return (
    <div className="space-y-6">
      {/* Full route table (Cisco show ip route / Huawei display ip routing-table) */}
      {routingData.routes && Array.isArray(routingData.routes) && routingData.routes.length > 0 && (
        <div className="border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900/30 rounded-2xl overflow-hidden">
          <div className="flex items-center justify-between gap-2 px-4 py-2.5 border-b border-slate-200 dark:border-slate-700 bg-slate-50/70 dark:bg-slate-800/30">
            <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">Routing Table</h3>
          </div>
          <div className="h-[400px] overflow-auto">
            <Table
              searchable
              searchPlaceholder="Search network, next hop, interface..."
              columns={[
                { 
                  header: "Protocol", 
                  key: "protocol", 
                  cell: (r) => (
                    <Badge className={
                      r.protocol === "S" ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200" :
                      r.protocol === "C" ? "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200" :
                      r.protocol === "L" ? "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200" :
                      r.protocol === "O" ? "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200" :
                      r.protocol === "B" ? "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200" :
                      r.protocol === "R" ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200" :
                      r.protocol === "D" ? "bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200" :
                      "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200"
                    }>
                      {r.protocol || "—"}
                    </Badge>
                  )
                },
                { header: "Network", key: "network", cell: (r) => <span className="font-mono text-slate-800 dark:text-slate-200">{r.network || "—"}</span> },
                { header: "Next Hop", key: "next_hop", cell: (r) => r.next_hop || "—" },
                { header: "Interface", key: "interface", cell: (r) => r.interface || "—" }
              ]}
              data={routingData.routes}
              empty="No routes"
              minWidthClass="min-w-[800px]"
              containerClassName="h-full"
            />
          </div>
        </div>
      )}

      {/* Static Routes - Support both legacy and new structure */}
      <StaticRoutesSection data={routingData} />
      
      {/* Dynamic Routing Protocols */}
      <OSPFSection data={routingData.ospf} />
      <BGPSection data={routingData.bgp} />
      <EIGRPSection data={routingData.eigrp} />
      <RIPSection data={routingData.rip} />
    </div>
  );
}

function StaticRoutesSection({ data }) {
  // Support both legacy and new standardized structure
  const staticRoutes = data.static_routes?.routes || data.static || [];
  
  if (!staticRoutes || staticRoutes.length === 0) return null;

  // Check if routes are in CIDR format (contain /) or legacy format (separate mask field)
  const isCIDRFormat = staticRoutes.some(route => route.network && route.network.includes('/'));

  return (
    <div className="border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900/30 rounded-2xl overflow-hidden">
      <div className="flex items-center justify-between gap-2 px-4 py-2.5 border-b border-slate-200 dark:border-slate-700 bg-slate-50/70 dark:bg-slate-800/30">
        <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">Static Routes</h3>
      </div>
      <div className="h-[400px] overflow-auto">
        <Table
          searchable
          searchPlaceholder="Search network, next hop, interface..."
          columns={[
            { 
              header: "Network", 
              key: "network", 
              cell: (r) => {
                // Check if default route (CIDR: 0.0.0.0/0, Legacy: network 0.0.0.0 with mask 0.0.0.0)
                const isDefaultRoute = r.is_default_route || 
                  (r.network === "0.0.0.0/0") || 
                  (r.network === "0.0.0.0" && r.mask === "0.0.0.0");
                
                return (
                  <div>
                    <span className="font-mono text-slate-800 dark:text-slate-200">{r.network || '—'}</span>
                    {isDefaultRoute && (
                      <Badge className="ml-2 bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                        Default
                      </Badge>
                    )}
                  </div>
                );
              }
            },
            // Only show mask column for legacy format (non-CIDR)
            ...(isCIDRFormat ? [] : [{ header: "Mask", key: "mask", cell: (r) => r.mask || '—' }]),
            { header: "Next Hop", key: "next_hop", cell: (r) => r.next_hop || r.nexthop || '—' },
            { header: "Interface", key: "interface", cell: (r) => r.interface || r.exit_interface || '—' },
            { header: "AD", key: "admin_distance", cell: (r) => r.admin_distance || r.distance || '—' },
            { 
              header: "Type", 
              key: "type", 
              cell: (r) => r.interface && !r.next_hop ? (
                <Badge className="bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200">
                  Connected
                </Badge>
              ) : (
                <Badge className="bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                  Next Hop
                </Badge>
              )
            }
          ]}
          data={staticRoutes}
          empty="No static routes"
          minWidthClass={isCIDRFormat ? "min-w-[800px]" : "min-w-[900px]"}
          containerClassName="h-full"
        />
      </div>
    </div>
  );
}

function OSPFSection({ data }) {
  if (!data || (!data.router_id && !data.process_id && (!data.interfaces || data.interfaces.length === 0))) return null;

  // Convert Huawei string interfaces to object format for consistency with Cisco
  const normalizeInterfaces = (interfaces) => {
    return interfaces.map(iface => {
      if (typeof iface === 'string') {
        // Huawei format: "10.0.0.20 0.0.0.3" 
        // Convert to Cisco format: {interface: "10.0.0.20", area: "0.0.0.3"}
        const parts = iface.split(' ');
        if (parts.length >= 2) {
          return {
            interface: parts[0],
            area: parts[1]
          };
        } else {
          // Fallback for single part strings
          return {
            interface: iface,
            area: '—'
          };
        }
      }
      // Cisco format: already object like {interface: "Ethernet0/0", area: "0"}
      return iface;
    });
  };

  // Add missing fields to Huawei neighbors to match Cisco format
  const normalizeNeighbors = (neighbors) => {
    return neighbors.map(neighbor => {
      // Check if this is a Huawei neighbor (missing priority, address, dr_bdr)
      if (neighbor.priority === undefined && neighbor.address === undefined && neighbor.dr_bdr === undefined) {
        // This is likely a Huawei neighbor, add missing fields
        return {
          ...neighbor,
          priority: '—',  // Add missing priority field
          address: '—',   // Add missing address field  
          dr_bdr: '—'    // Add missing dr_bdr field
        };
      }
      // This is already a Cisco neighbor, return as-is
      return neighbor;
    });
  };

  const normalizedInterfaces = normalizeInterfaces(data.interfaces || []);
  const normalizedNeighbors = normalizeNeighbors(data.neighbors || []);
  const learnedPrefixCount = data.learned_prefix_count ?? (Array.isArray(data.learned_prefixes) ? data.learned_prefixes.length : null);

  return (
    <div className="border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900/30 rounded-2xl overflow-hidden">
      <div className="flex items-center justify-between gap-2 px-4 py-2.5 border-b border-slate-200 dark:border-slate-700 bg-slate-50/70 dark:bg-slate-800/30">
        <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">OSPF</h3>
      </div>
      <div className="p-4 space-y-4">
        {/* 2.3.2.5.2.1 Router ID & 2.3.2.5.2.2 Process ID & 2.3.2.5.2.3 Areas */}
        <div className="grid gap-4 md:grid-cols-3 text-sm">
          <div>
            <span className="font-medium text-slate-700 dark:text-slate-300">Router ID: </span>
            <span className="font-mono text-slate-800 dark:text-slate-200">{data.router_id || '—'}</span>
          </div>
          <div>
            <span className="font-medium text-slate-700 dark:text-slate-300">Process ID: </span>
            <span className="font-mono text-slate-800 dark:text-slate-200">{data.process_id || '—'}</span>
          </div>
          <div>
            <span className="font-medium text-slate-700 dark:text-slate-300">Areas: </span>
            <span className="font-mono text-slate-800 dark:text-slate-200">
              {Array.isArray(data.areas) ? data.areas.join(', ') : '—'}
            </span>
          </div>
        </div>

        {/* 2.3.2.5.2.4 OSPF Interfaces */}
        {(normalizedInterfaces && normalizedInterfaces.length > 0) && (
          <div>
            <h3 className="text-sm font-semibold mb-2 text-slate-800 dark:text-slate-200">OSPF Interfaces</h3>
            <div className="h-[200px] overflow-auto border border-slate-200 dark:border-slate-700 rounded-lg">
              <Table
                columns={[
                  { 
                    header: "Interface", 
                    key: "interface", 
                    cell: (r) => (
                      <span className="font-medium text-slate-800 dark:text-slate-200">
                        {r.interface || r.name || r.iface || '—'}
                      </span>
                    )
                  },
                  { 
                    header: "Area", 
                    key: "area", 
                    cell: (r) => r.area || r.area_id || '—'
                  }
                ]}
                data={normalizedInterfaces}
                empty="No OSPF interfaces"
                minWidthClass="min-w-[400px]"
                containerClassName="h-full"
              />
            </div>
          </div>
        )}

        {/* 2.3.2.5.2.5 Neighbor List and State */}
        {(normalizedNeighbors && normalizedNeighbors.length > 0) && (
          <div>
            <h3 className="text-sm font-semibold mb-2 text-slate-800 dark:text-slate-200">OSPF Neighbors</h3>
            <div className="h-[200px] overflow-auto border border-slate-200 dark:border-slate-700 rounded-lg">
              <Table
                columns={[
                  { 
                    header: "Neighbor ID", 
                    key: "neighbor_id", 
                    cell: (r) => {
                      const neighborId = r.neighbor_id || r.id || r.router_id || '—';
                      return <span className="font-medium text-slate-800 dark:text-slate-200">{neighborId}</span>;
                    }
                  },
                  { 
                    header: "Interface", 
                    key: "interface", 
                    cell: (r) => {
                      const interfaceName = r.interface || r.iface || r.intf || '—';
                      return interfaceName;
                    }
                  },
                  { 
                    header: "State", 
                    key: "state", 
                    cell: (r) => (
                      <Badge className={
                        r.state === "Full" || r.state === "FULL" ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200" :
                        r.state === "Init" || r.state === "INIT" ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200" :
                        r.state === "2-Way" || r.state === "2WAY" ? "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200" :
                        "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200"
                      }>
                        {r.state || "—"}
                      </Badge>
                    )
                  },
                  { header: "Priority", key: "priority", cell: (r) => r.priority ?? "—" },
                  { header: "Address", key: "address", cell: (r) => r.address || "—" },
                  { 
                    header: "DR/BDR", 
                    key: "dr_bdr", 
                    cell: (r) => (
                      <Badge className={
                        r.dr_bdr === "DR" ? "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200" :
                        r.dr_bdr === "BDR" ? "bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200" :
                        "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200"
                      }>
                        {r.dr_bdr || "—"}
                      </Badge>
                    )
                  }
                ]}
                data={normalizedNeighbors}
                empty="No OSPF neighbors"
                minWidthClass="min-w-[700px]"
                containerClassName="h-full"
              />
            </div>
          </div>
        )}

        {/* 2.3.2.5.2.7 Learned Prefix Summary */}
        {learnedPrefixCount ? (
          <div>
            <h3 className="text-sm font-semibold mb-2 text-slate-800 dark:text-slate-200">Learned Prefix Summary</h3>
            <div className="text-sm text-slate-600 dark:text-slate-400">
              Total learned prefixes: <span className="font-mono text-slate-800 dark:text-slate-200">{learnedPrefixCount}</span>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function BGPSection({ data }) {
  if (!data || (!data.local_as && !data.as_number && (!data.peers || data.peers.length === 0))) return null;

  return (
    <div className="border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900/30 rounded-2xl overflow-hidden">
      <div className="flex items-center justify-between gap-2 px-4 py-2.5 border-b border-slate-200 dark:border-slate-700 bg-slate-50/70 dark:bg-slate-800/30">
        <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">BGP</h3>
      </div>
      <div className="p-4 space-y-4">
        <div className="grid gap-4 md:grid-cols-2 text-sm">
          <div>
            <span className="font-medium text-slate-700 dark:text-slate-300">Local AS: </span>
            <span className="font-mono text-slate-800 dark:text-slate-200">
              {data.local_as || data.as_number || '—'}
            </span>
          </div>
          <div>
            <span className="font-medium text-slate-700 dark:text-slate-300">Router ID: </span>
            <span className="font-mono text-slate-800 dark:text-slate-200">{data.router_id || '—'}</span>
          </div>
        </div>

        {data.peers && data.peers.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold mb-2 text-slate-800 dark:text-slate-200">BGP Peers</h3>
            <div className="h-[300px] overflow-auto border border-slate-200 dark:border-slate-700 rounded-lg">
              <Table
                columns={[
                  { header: "Peer IP", key: "peer_ip", cell: (r) => <span className="font-medium text-slate-800 dark:text-slate-200">{r.peer_ip || r.ip || r.address || "—"}</span> },
                  { header: "Remote AS", key: "remote_as", cell: (r) => r.remote_as || r.as || "—" },
                  { 
                    header: "State", 
                    key: "state", 
                    cell: (r) => (
                      <Badge className={
                        r.state === "Established" ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200" :
                        r.state === "Active" ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200" :
                        "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200"
                      }>
                        {r.state || "—"}
                      </Badge>
                    )
                  },
                  { header: "Prefixes", key: "prefixes", cell: (r) => r.prefixes_received || r.prefixes || "—" }
                ]}
                data={data.peers}
                empty="No BGP peers"
                minWidthClass="min-w-[700px]"
                containerClassName="h-full"
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function EIGRPSection({ data }) {
  if (!data || (!data.as_number && (!data.neighbors || data.neighbors.length === 0))) return null;

  return (
    <div className="border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900/30 rounded-2xl overflow-hidden">
      <div className="flex items-center justify-between gap-2 px-4 py-2.5 border-b border-slate-200 dark:border-slate-700 bg-slate-50/70 dark:bg-slate-800/30">
        <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">EIGRP</h3>
      </div>
      <div className="p-4 space-y-4">
        <div className="grid gap-4 md:grid-cols-3 text-sm">
          <div>
            <span className="font-medium text-slate-700 dark:text-slate-300">AS Number: </span>
            <span className="font-mono text-slate-800 dark:text-slate-200">{data.as_number ?? '—'}</span>
          </div>
          <div>
            <span className="font-medium text-slate-700 dark:text-slate-300">Router ID: </span>
            <span className="font-mono text-slate-800 dark:text-slate-200">{data.router_id ?? '—'}</span>
          </div>
          <div>
            <span className="font-medium text-slate-700 dark:text-slate-300">Hold Timer: </span>
            <span className="font-mono text-slate-800 dark:text-slate-200">{data.hold_time ?? '—'}</span>
          </div>
        </div>

        {data.neighbors && data.neighbors.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold mb-2 text-slate-800 dark:text-slate-200">EIGRP Neighbors</h3>
            <div className="h-[260px] overflow-auto border border-slate-200 dark:border-slate-700 rounded-lg">
              <Table
                searchable
                searchPlaceholder="Search neighbor or interface..."
                columns={[
                  { header: "Address", key: "address", cell: (r) => <span className="font-medium text-slate-800 dark:text-slate-200">{r.address || r.neighbor_ip || r.ip || "—"}</span> },
                  { header: "Interface", key: "interface", cell: (r) => r.interface || "—" },
                  { header: "Hold (sec)", key: "hold_time", cell: (r) => (r.hold_time ?? r.holdtime) ?? "—" },
                  { header: "Uptime", key: "uptime", cell: (r) => r.uptime || "—" },
                ]}
                data={data.neighbors}
                empty="No EIGRP neighbors"
                minWidthClass="min-w-[700px]"
                containerClassName="h-full"
              />
            </div>
          </div>
        )}

        {data.learned_routes && data.learned_routes.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold mb-2 text-slate-800 dark:text-slate-200">Learned Routes</h3>
            <div className="h-[300px] overflow-auto border border-slate-200 dark:border-slate-700 rounded-lg">
              <Table
                searchable
                searchPlaceholder="Search network, next hop, interface..."
                columns={[
                  { header: "Protocol", key: "protocol", cell: (r) => <Badge className={
                    (r.protocol || '').toUpperCase().startsWith('EX') ? "bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200" :
                    "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200"
                  }>{r.protocol || '—'}</Badge> },
                  { header: "Network", key: "network", cell: (r) => <span className="font-mono text-slate-800 dark:text-slate-200">{r.network || '—'}</span> },
                  { header: "Next Hop", key: "next_hop", cell: (r) => r.next_hop || '—' },
                  { header: "Interface", key: "interface", cell: (r) => r.interface || '—' },
                  { header: "AD", key: "distance", cell: (r) => r.distance ?? r.admin_distance ?? '—' },
                  { header: "Metric", key: "metric", cell: (r) => r.metric ?? '—' },
                ]}
                data={data.learned_routes}
                empty="No EIGRP learned routes"
                minWidthClass="min-w-[900px]"
                containerClassName="h-full"
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function RIPSection({ data }) {
  if (!data || (!data.version && (!data.networks || data.networks.length === 0))) return null;

  const version = data.version ?? data.details?.version;
  const adminDistance = data.admin_distance ?? data.details?.admin_distance;
  const advertisedNetworks = data.advertised_networks || data.networks || data.details?.advertised_networks || [];
  const learnedRoutes = data.learned_routes || data.details?.learned_routes || [];
  const learnedNetworks = (data.learned_networks && Array.isArray(data.learned_networks) && data.learned_networks.length > 0)
    ? data.learned_networks
    : (Array.isArray(learnedRoutes)
      ? Array.from(new Set(learnedRoutes.map(r => r?.network).filter(Boolean)))
      : []);
  const participatingInterfaces = data.participating_interfaces || data.details?.participating_interfaces || [];
  const passiveInterfaces = data.passive_interfaces || data.details?.passive_interfaces || [];
  const autoSummary = data.auto_summary ?? data.details?.auto_summary;
  const timers = data.timers || data.details?.timers;

  return (
    <div className="border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900/30 rounded-2xl overflow-hidden">
      <div className="flex items-center justify-between gap-2 px-4 py-2.5 border-b border-slate-200 dark:border-slate-700 bg-slate-50/70 dark:bg-slate-800/30">
        <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">RIP</h3>
      </div>
      <div className="p-4 space-y-4">
        <div className="grid gap-4 md:grid-cols-3 text-sm">
          <div>
            <span className="font-medium text-slate-700 dark:text-slate-300">Version: </span>
            <span className="font-mono text-slate-800 dark:text-slate-200">{version ?? '—'}</span>
          </div>
          <div>
            <span className="font-medium text-slate-700 dark:text-slate-300">Admin Distance: </span>
            <span className="font-mono text-slate-800 dark:text-slate-200">{adminDistance ?? '—'}</span>
          </div>
          <div>
            <span className="font-medium text-slate-700 dark:text-slate-300">Auto-Summary: </span>
            <span className="font-mono text-slate-800 dark:text-slate-200">{typeof autoSummary === 'boolean' ? (autoSummary ? 'Enabled' : 'Disabled') : '—'}</span>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <h3 className="text-sm font-semibold mb-2 text-slate-800 dark:text-slate-200">Advertised Networks</h3>
            <div className="h-[160px] overflow-auto border border-slate-200 dark:border-slate-700 rounded-lg">
              <Table
                searchable
                searchPlaceholder="Search network..."
                columns={[{ header: "Network", key: "network", cell: (r) => <span className="font-mono text-slate-800 dark:text-slate-200">{r.network || "—"}</span> }]}
                data={(Array.isArray(advertisedNetworks) ? advertisedNetworks : []).map(n => ({ network: n }))}
                empty="No advertised networks"
                minWidthClass="min-w-[320px]"
                containerClassName="h-full"
              />
            </div>
          </div>
          <div>
            <h3 className="text-sm font-semibold mb-2 text-slate-800 dark:text-slate-200">Learned Networks</h3>
            <div className="h-[160px] overflow-auto border border-slate-200 dark:border-slate-700 rounded-lg">
              <Table
                searchable
                searchPlaceholder="Search network..."
                columns={[{ header: "Network", key: "network", cell: (r) => <span className="font-mono text-slate-800 dark:text-slate-200">{r.network || "—"}</span> }]}
                data={(Array.isArray(learnedNetworks) ? learnedNetworks : []).map(n => ({ network: n }))}
                empty="No learned networks"
                minWidthClass="min-w-[320px]"
                containerClassName="h-full"
              />
            </div>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2 text-sm">
          <div>
            <span className="font-medium text-slate-700 dark:text-slate-300">Passive Interfaces: </span>
            <span className="font-mono text-slate-800 dark:text-slate-200">
              {Array.isArray(passiveInterfaces) && passiveInterfaces.length > 0 ? passiveInterfaces.join(', ') : '—'}
            </span>
          </div>
          <div>
            <span className="font-medium text-slate-700 dark:text-slate-300">Timers: </span>
            <span className="font-mono text-slate-800 dark:text-slate-200">
              {timers && typeof timers === 'object'
                ? `U:${timers.update ?? '—'} I:${timers.invalid ?? '—'} H:${(timers.hold_down ?? timers.hold) ?? '—'} F:${timers.flush ?? '—'}`
                : '—'}
            </span>
          </div>
        </div>

        {timers && typeof timers === 'object' && (
          <div>
            <h3 className="text-sm font-semibold mb-2 text-slate-800 dark:text-slate-200">Timers</h3>
            <div className="grid gap-2 md:grid-cols-5 text-sm">
              <div>
                <span className="font-medium text-slate-700 dark:text-slate-300">Update: </span>
                <span className="font-mono text-slate-800 dark:text-slate-200">{timers.update ?? '—'}</span>
              </div>
              <div>
                <span className="font-medium text-slate-700 dark:text-slate-300">Invalid: </span>
                <span className="font-mono text-slate-800 dark:text-slate-200">{timers.invalid ?? '—'}</span>
              </div>
              <div>
                <span className="font-medium text-slate-700 dark:text-slate-300">Holddown: </span>
                <span className="font-mono text-slate-800 dark:text-slate-200">{timers.hold_down ?? timers.hold ?? '—'}</span>
              </div>
              <div>
                <span className="font-medium text-slate-700 dark:text-slate-300">Flush: </span>
                <span className="font-mono text-slate-800 dark:text-slate-200">{timers.flush ?? '—'}</span>
              </div>
              <div>
                <span className="font-medium text-slate-700 dark:text-slate-300">Garbage: </span>
                <span className="font-mono text-slate-800 dark:text-slate-200">{timers.garbage_collect ?? timers.garbage ?? '—'}</span>
              </div>
            </div>
          </div>
        )}

        {Array.isArray(participatingInterfaces) && participatingInterfaces.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold mb-2 text-slate-800 dark:text-slate-200">Participating Interfaces</h3>
            <div className="h-[200px] overflow-auto border border-slate-200 dark:border-slate-700 rounded-lg">
              <Table
                columns={[
                  { header: "Interface", key: "name", cell: (r) => <span className="font-medium text-slate-800 dark:text-slate-200">{r.name || r.interface || "—"}</span> },
                  { header: "Send", key: "send", cell: (r) => r.send ?? "—" },
                  { header: "Recv", key: "recv", cell: (r) => r.recv ?? "—" },
                  { header: "Passive", key: "passive", cell: (r) => (typeof r.passive === 'boolean' ? (r.passive ? 'Yes' : 'No') : '—') }
                ]}
                data={participatingInterfaces}
                empty="No participating interfaces"
                minWidthClass="min-w-[500px]"
                containerClassName="h-full"
              />
            </div>
          </div>
        )}

        {Array.isArray(learnedRoutes) && learnedRoutes.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold mb-2 text-slate-800 dark:text-slate-200">Learned Routes</h3>
            <div className="h-[300px] overflow-auto border border-slate-200 dark:border-slate-700 rounded-lg">
              <Table
                columns={[
                  { header: "Network", key: "network", cell: (r) => <span className="font-medium text-slate-800 dark:text-slate-200">{r.network || "—"}</span> },
                  { header: "Next Hop", key: "next_hop", cell: (r) => r.next_hop || "—" },
                  { header: "Hop", key: "hop_count", cell: (r) => r.hop_count ?? "—" },
                  { header: "Metric", key: "metric", cell: (r) => (r.metric ?? r.hop_count) ?? "—" },
                  { header: "Interface", key: "interface", cell: (r) => r.interface || "—" },
                  { header: "Uptime", key: "uptime", cell: (r) => r.uptime || "—" }
                ]}
                data={learnedRoutes}
                empty="No RIP learned routes"
                minWidthClass="min-w-[900px]"
                containerClassName="h-full"
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
