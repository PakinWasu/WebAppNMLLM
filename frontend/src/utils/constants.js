/**
 * Sample command set and config text for templates / upload helpers.
 */

export const CMDSET = `# === COMMAND SET USED TO COLLECT DATA ===
terminal length 0
! Inventory/Chassis
show switch
show inventory
show environment all
show platform hardware power
show interfaces transceiver detail
! Interfaces deep
show interfaces
show interfaces status
show interfaces description
show controllers counters errors
show storm-control
show etherchannel summary
! L2/L2-Security
show vlan brief
show interfaces switchport
show spanning-tree summary
show spanning-tree detail
show spanning-tree interface detail
show port-security
show dhcp snooping
show ip arp inspection
show udld interface
! L3/VRF/HSRP/BGP/OSPF
show ip interface brief
show vrf
show ip route summary vrf all
show ip ospf neighbor vrf all
show ip bgp summary vrf all
show standby brief
show vrrp brief
! Multicast/QoS/NAT/DHCP
show ip igmp snooping
show ip pim neighbor
show policy-map interface
show nat statistics
show ip dhcp relay
! Mgmt/NTP/SNMP/Logging
show running-config | i aaa|tacacs|radius|snmp|logging host|ip http|ssh
show snmp user
show logging
show flow exporter
show ntp associations detail
show clock detail
! Health/Drift
show processes cpu | include one minute
show processes memory
show archive
show running-config | include Last configuration change
`;

export const SAMPLE_CORE_SW1 = `${CMDSET}

=== SHOW VERSION ===
Cisco C9500-24Y4C (X86) IOS-XE Software, Version 17.9.4
System Serial Number : FTX12345AAA
Uptime: 2 weeks, 4 days

=== SHOW IP INTERFACE BRIEF ===
Vlan10           10.0.0.11     YES manual up up
Vlan20           10.0.20.1     YES manual up up
Vlan30           10.0.30.1     YES manual up up
Vlan99           10.0.99.1     YES manual up up
Gi1/0/1          unassigned     YES unset  up up
Gi1/0/2          unassigned     YES unset  up up

=== SHOW VLAN BRIEF ===
VLAN Name      Status  Ports
1    default   active
10   USERS     active  Gi1/0/4-5,Gi1/0/10-12
20   CCTV      active  Gi1/0/3,Gi1/0/6-7
30   IOT       active  Gi1/0/8-9
99   NATIVE    active  trunk(native)
(total 38 VLANs)

=== SHOW INTERFACES SWITCHPORT (excerpt) ===
Name: Gi1/0/1
  Administrative Mode: trunk
  Trunking Native Mode VLAN: 99
  Trunking VLANs Enabled: 1,10,20,30,99,100-120

=== SHOW STANDBY BRIEF (HSRP) ===
Vlan10 - Group 10  Active prio120 preempt VIP 10.0.10.1
Vlan20 - Group 20  Standby prio110 preempt VIP 10.0.20.1

=== SHOW IP OSPF NEIGHBOR ===
(total 6 neighbors) on Vlan10

=== SHOW IP BGP SUMMARY ===
Local AS 65001, Neighbors: 4

=== SHOW CDP/LLDP ===
CDP: 8 neighbors, LLDP: 3 neighbors

=== SHOW NTP STATUS ===
Clock synchronized (stratum 3)

=== SHOW CPU/MEM ===
CPU 21% / MEM 58%

=== SYSLOG ===
logging host 10.10.1.10
`;

export const SAMPLE_DIST_SW2 = `${CMDSET}

=== SHOW VERSION ===
Cisco C9300-48P IOS-XE 17.6.5  SN:FTX12345BBB

=== SHOW IP INTERFACE BRIEF ===
Vlan10 10.0.1.21 up up
Vlan20 10.0.21.1 up up
Vlan30 10.0.31.1 up up

=== SHOW VLAN BRIEF ===
1 default, 10 USERS, 20 CCTV, 30 IOT  (total 24)

=== STP ===
rapid-pvst, not root

=== OSPF ===
3 neighbors

=== CDP/LLDP ===
5 / 2

=== NTP ===
synchronized

=== CPU/MEM ===
18% / 62%
`;

export function createUploadRecord(type, files, user, project, details) {
  return {
    id: `upload_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    type,
    files: files.map((f) => ({ name: f.name, size: f.size, type: f.type })),
    user,
    project,
    timestamp: new Date().toISOString(),
    details: {
      who: details.who || user,
      what: details.what || "",
      where: details.where || "",
      when: details.when || "",
      why: details.why || "",
      description: details.description || "",
    },
  };
}
