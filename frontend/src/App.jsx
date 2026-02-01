// src/App.jsx
import React, { useMemo, useState, useEffect, useRef } from "react";
import * as api from "./api";
import MainLayout from "./components/layout/MainLayout";

// Utility function to format date/time in local timezone (English)
const formatDateTime = (dateString) => {
  if (!dateString) return "—";
  try {
    const date = new Date(dateString);
    // Format to local timezone in English
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });
  } catch (e) {
    return dateString;
  }
};

const formatDate = (dateString) => {
  if (!dateString) return "—";
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    });
  } catch (e) {
    return dateString;
  }
};

/* ========== UI PRIMITIVES ========= */
const Badge = ({ children }) => (
  <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100">
    {children}
  </span>
);
const Button = ({
  children,
  onClick,
  variant = "primary",
  disabled,
  className = "",
}) => {
  const base =
    "inline-flex items-center justify-center rounded-2xl px-4 py-2 text-sm font-semibold shadow-sm transition focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed";
  const styles = {
    primary:
      "bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500 dark:bg-blue-500 dark:hover:bg-blue-400",
    secondary:
      "bg-white text-gray-900 ring-1 ring-gray-300 hover:bg-gray-50 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100 dark:ring-gray-600 dark:hover:bg-gray-700",
    ghost:
      "bg-transparent text-gray-700 hover:bg-gray-100 focus:ring-blue-500 dark:text-gray-200 dark:hover:bg-gray-800",
    danger: "bg-rose-600 text-white hover:bg-rose-700 focus:ring-rose-500",
  }[variant];
  return (
    <button
      className={`${base} ${styles} ${className}`}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  );
};
const Card = ({ title, actions, children, className = "", compact = false }) => (
  <div
    className={`rounded-2xl border border-gray-200 dark:border-[#1F2937] bg-white dark:bg-[#111827] shadow-sm ${className}`}
  >
    {(title || actions) && (
      <div className={`flex items-center justify-between border-b border-gray-100 dark:border-[#1F2937] ${compact ? 'px-2 py-1' : 'px-5 py-3'}`}>
        <h3 className={`${compact ? 'text-[10px]' : 'text-sm'} font-semibold text-gray-700 dark:text-gray-200`}>
          {title}
        </h3>
        <div className="flex gap-2">{actions}</div>
      </div>
    )}
    <div className={compact ? "p-1" : "p-5"}>{children}</div>
  </div>
);
const Field = ({ label, children }) => (
  <label className="grid gap-1.5">
    <span className="text-xs font-medium text-gray-600 dark:text-gray-300">
      {label}
    </span>
    {children}
  </label>
);
const Input = (props) => (
  <input
    {...props}
    className={`w-full rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 ${
      props.className || ""
    }`}
  />
);

// Password Input with Eye Icon Toggle
const PasswordInput = ({ value, onChange, placeholder, disabled, className = "" }) => {
  const [showPassword, setShowPassword] = useState(false);
  
  const togglePasswordVisibility = () => {
    setShowPassword(!showPassword);
  };
  
  return (
    <div className="relative w-full">
      <input
        type={showPassword ? "text" : "password"}
        value={value || ""}
        onChange={onChange}
        placeholder={placeholder}
        disabled={disabled}
        autoComplete="current-password"
        className={`w-full rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 pr-10 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
          className || ""
        }`}
      />
      <button
        type="button"
        onClick={togglePasswordVisibility}
        disabled={disabled}
        className="absolute right-0 top-0 h-full px-3 flex items-center justify-center border-l border-gray-300 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        aria-label={showPassword ? "Hide password" : "Show password"}
      >
        {showPassword ? (
          // Eye with slash (hide password)
          <svg
            className="w-5 h-5 text-gray-600 dark:text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"
            />
          </svg>
        ) : (
          // Eye without slash (show password)
          <svg
            className="w-5 h-5 text-gray-600 dark:text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
            />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
            />
          </svg>
        )}
      </button>
    </div>
  );
};
const Select = ({ options = [], value, onChange, className = "" }) => (
  <select
    value={value}
    onChange={(e) => onChange(e.target.value)}
    className={`rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 ${className}`}
  >
    {options.map((o) => (
      <option key={o.value} value={o.value}>
        {o.label}
      </option>
    ))}
  </select>
);

const SelectWithOther = ({ options = [], value, onChange, className = "", placeholder = "Select or type..." }) => {
  const [inputValue, setInputValue] = useState(value || "");
  const [showDropdown, setShowDropdown] = useState(false);
  const [filteredOptions, setFilteredOptions] = useState(options);
  const inputRef = useRef(null);

  useEffect(() => {
    setInputValue(value || "");
  }, [value]);

  useEffect(() => {
    // Filter options based on input
    if (inputValue.trim() === "") {
      setFilteredOptions(options);
    } else {
      const filtered = options.filter(o => 
        o.label.toLowerCase().includes(inputValue.toLowerCase()) ||
        o.value.toLowerCase().includes(inputValue.toLowerCase())
      );
      setFilteredOptions(filtered);
    }
  }, [inputValue, options]);

  const handleInputChange = (e) => {
    const newValue = e.target.value;
    setInputValue(newValue);
    setShowDropdown(true);
    // Don't call onChange here - only update local state
    // onChange will be called on blur or option selection
  };

  const handleInputFocus = () => {
    setShowDropdown(true);
  };

  const handleInputBlur = (e) => {
    // Call onChange when blur (user finished typing)
    if (inputValue !== value) {
      onChange(inputValue);
    }
    // Delay hiding dropdown to allow option click
    setTimeout(() => {
      setShowDropdown(false);
    }, 200);
  };

  const handleOptionClick = (optionValue) => {
    setInputValue(optionValue);
    setShowDropdown(false);
    onChange(optionValue);
    if (inputRef.current) {
      inputRef.current.blur();
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Escape") {
      setShowDropdown(false);
      if (inputRef.current) {
        inputRef.current.blur();
      }
    }
  };

  return (
    <div className="relative">
      <Input
        ref={inputRef}
        value={inputValue}
        onChange={handleInputChange}
        onFocus={handleInputFocus}
        onBlur={handleInputBlur}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        className={className}
        autoComplete="off"
      />
      {showDropdown && filteredOptions.length > 0 && (
        <div className="absolute z-50 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-xl shadow-lg max-h-60 overflow-auto">
          {filteredOptions.map((o) => (
            <div
              key={o.value}
              onClick={() => handleOptionClick(o.value)}
              className="px-3 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer text-sm"
            >
              {o.label}
            </div>
          ))}
          {inputValue.trim() !== "" && !options.find(o => o.value === inputValue) && (
            <div
              onClick={() => handleOptionClick(inputValue)}
              className="px-3 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer text-sm border-t border-gray-300 dark:border-gray-700 text-blue-600 dark:text-blue-400"
            >
              Use "{inputValue}" (custom)
            </div>
          )}
        </div>
      )}
    </div>
  );
};
const Table = ({
  columns,
  data,
  empty = "No data",
  containerClassName = "",
  minWidthClass = "min-w-full",
}) => {
  // Check if containerClassName includes text size override
  const textSizeClass = containerClassName.includes('text-[') 
    ? containerClassName.match(/text-\[[^\]]+\]/)?.[0] 
    : null;
  const tableTextSize = textSizeClass || "text-[11px]";
  const headerTextSize = textSizeClass ? textSizeClass.replace('text-', 'text-').replace('px]', 'px]') : "text-[10px]";
  
  return (
    <div
      className={`overflow-auto rounded-2xl border border-gray-200 dark:border-[#1F2937] ${containerClassName}`}
    >
      <table
        className={`${minWidthClass} divide-y divide-gray-200 dark:divide-[#1F2937]`}
      >
        <thead className="bg-gray-50 dark:bg-[#111827] sticky top-0 z-10">
          <tr>
            {columns.map((c) => (
              <th
                key={c.key || c.header}
                className={`px-2 py-1.5 text-left ${headerTextSize} font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-300`}
                style={{ width: c.width }}
              >
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 dark:divide-[#1F2937] bg-white dark:bg-[#0F172A]">
          {data.length === 0 && (
            <tr>
              <td
                className={`px-2 py-4 ${tableTextSize} text-gray-500 dark:text-gray-400`}
                colSpan={columns.length}
              >
                {empty}
              </td>
            </tr>
          )}
          {data.map((row, i) => (
            <tr
              key={i}
              className="odd:bg-white even:bg-gray-50 dark:odd:bg-[#0F172A] dark:even:bg-[#0D1422] hover:bg-gray-50 dark:hover:bg-[#1A2231]"
            >
              {columns.map((c) => (
                <td
                  key={c.key || c.header}
                  className={`px-2 py-1 ${tableTextSize} text-gray-800 dark:text-gray-100 align-top ${c.key === 'more' ? 'text-center' : ''}`}
                >
                  {typeof c.cell === "function" ? c.cell(row) : row[c.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

/* ========= TXT SAMPLES (commands + show outputs) ========= */
const CMDSET = `# === COMMAND SET USED TO COLLECT DATA ===
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

const SAMPLE_CORE_SW1 = `${CMDSET}

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

const SAMPLE_DIST_SW2 = `${CMDSET}

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

/* ========= MOCK DATA ========= */
const seedUsers = [
  {
    id: "u1",
    username: "admin",
    email: "admin@net.app",
    role: "admin",
    lastLogin: "2025-10-04",
  },
  {
    id: "u2",
    username: "managerA",
    email: "mA@net.app",
    role: "manager",
    lastLogin: "2025-10-05",
  },
  {
    id: "u3",
    username: "operatorB",
    email: "opB@net.app",
    role: "operator",
    lastLogin: "2025-10-05",
  },
  {
    id: "u4",
    username: "viewerC",
    email: "vC@net.app",
    role: "viewer",
    lastLogin: "2025-10-02",
  },
];

// Upload history tracking
const createUploadRecord = (type, files, user, project, details) => ({
  id: `upload_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
  type, // 'config' or 'document'
  files: files.map(f => ({
    name: f.name,
    size: f.size,
    type: f.type
  })),
  user,
  project,
  timestamp: new Date().toISOString(),
  details: {
    who: details.who || user,
    what: details.what || '',
    where: details.where || '',
    when: details.when || '',
    why: details.why || '',
    description: details.description || ''
  }
});

const seedProjects = [
  {
    id: "p1",
    name: "Network ABC",
    desc: "Core Campus Network",
    manager: "managerA",
    updated: "2025-10-05 14:23",
    status: "Active",
    members: [
      { username: "admin", role: "admin" },
      { username: "managerA", role: "manager" },
      { username: "operatorB", role: "operator" },
      { username: "viewerC", role: "viewer" },
    ],
    devices: 12,
    lastBackup: "2025-10-05 10:00",
    services: 8,
    visibility: "Private",
    topoUrl: new URL("./assets/topo1.png", import.meta.url).href,

    logs: [
      {
        time: "2025-10-05 14:23",
        user: "operatorB",
        action: "Upload Config",
        target: "core-sw1.txt",
        result: "Success",
      },
      {
        time: "2025-10-04 17:05",
        user: "managerA",
        action: "Edit Project",
        target: "Network ABC",
        result: "Updated",
      },
      {
        time: "2025-10-04 11:40",
        user: "operatorB",
        action: "Upload Config",
        target: "access-sw2.txt",
        result: "Error",
      },
    ],
    uploadHistory: [
      {
        id: "upload_1",
        type: "config",
        files: [{ name: "HQ_CORE-SW1_20251006.txt", size: 28672, type: "text/plain" }],
        user: "operatorB",
        project: "p1",
        timestamp: "2025-10-05T14:23:00.000Z",
        details: {
          who: "operatorB",
          what: "Backup Configuration",
          where: "Data Center A",
          when: "Monthly Backup",
          why: "Regular Backup Schedule",
          description: "Regular monthly configuration backup for core switch"
        }
      },
      {
        id: "upload_2",
        type: "config",
        files: [{ name: "HQ_DIST-SW2_20251006.txt", size: 20480, type: "text/plain" }],
        user: "operatorB",
        project: "p1",
        timestamp: "2025-10-05T14:20:00.000Z",
        details: {
          who: "operatorB",
          what: "Backup Configuration",
          where: "Data Center A",
          when: "Monthly Backup",
          why: "Regular Backup Schedule",
          description: "Regular monthly configuration backup for distribution switch"
        }
      },
      {
        id: "upload_3",
        type: "document",
        files: [{ name: "PhysicalDiagram.pdf", size: 327680, type: "application/pdf" }],
        user: "managerA",
        project: "p1",
        timestamp: "2025-10-01T10:15:00.000Z",
        details: {
          who: "managerA",
          what: "Update Network Documentation",
          where: "Office",
          when: "Project Update",
          why: "Project Documentation",
          description: "Updated physical network diagram after equipment changes"
        }
      },
      {
        id: "upload_4",
        type: "document",
        files: [{ name: "LogicalDiagram.pdf", size: 280000, type: "application/pdf" }],
        user: "managerA",
        project: "p1",
        timestamp: "2025-10-01T10:10:00.000Z",
        details: {
          who: "managerA",
          what: "Update Network Documentation",
          where: "Office",
          when: "Project Update",
          why: "Project Documentation",
          description: "Updated logical network diagram"
        }
      },
      {
        id: "upload_5",
        type: "config",
        files: [{ name: "core-sw1_running-config.txt", size: 35000, type: "text/plain" }],
        user: "admin",
        project: "p1",
        timestamp: "2025-09-28T16:30:00.000Z",
        details: {
          who: "admin",
          what: "Update Running Config",
          where: "Data Center A",
          when: "Before Change",
          why: "Before System Changes",
          description: "Backup before implementing new VLAN configuration"
        }
      }
    ],
    /* Summary enriched */
    summaryRows: [
      {
        device: "core-sw1",
        model: "C9500-24Y4C",
        osVersion: "IOS-XE 17.9.4",
        serial: "FTX12345AAA",
        mgmtIp: "10.0.0.11",
        ifaces: { total: 96, up: 92, down: 2, adminDown: 2 },
        accessCount: 40,
        trunkCount: 6,
        vlanCount: 38,
        stpMode: "RPVST",
        stpRoot: "No",
        routing: "OSPF,BGP",
        ospfNeighbors: 6,
        bgpAsn: 65001,
        bgpNeighbors: 4,
        cdpNeighbors: 8,
        lldpNeighbors: 3,
        cpu: 21,
        mem: 58,
        ntpStatus: "Sync",
        snmp: "Yes",
        syslog: "10.10.1.10",
        allowedVlansShort: "1,10,20,30,99,100-120…(42)",
      },
      {
        device: "dist-sw2",
        model: "C9300-48P",
        osVersion: "IOS-XE 17.6.5",
        serial: "FTX12345BBB",
        mgmtIp: "10.0.1.21",
        ifaces: { total: 56, up: 54, down: 2, adminDown: 0 },
        accessCount: 44,
        trunkCount: 4,
        vlanCount: 24,
        stpMode: "RPVST",
        stpRoot: "No",
        routing: "OSPF",
        ospfNeighbors: 3,
        bgpAsn: null,
        bgpNeighbors: 0,
        cdpNeighbors: 5,
        lldpNeighbors: 2,
        cpu: 18,
        mem: 62,
        ntpStatus: "Sync",
        snmp: "Yes",
        syslog: "10.10.1.10",
        allowedVlansShort: "1,10,20,30…(24)",
      },
      {
        device: "access-sw3",
        serial: "FTX12345CCC",
        vlan: "10,20",
        services: "-",
        status: "Drift",
      },
    ],
    documents: {
      config: [
        {
          name: "HQ_CORE-SW1_20251006.txt",
          size: "28 KB",
          modified: "2025-10-06",
          content: SAMPLE_CORE_SW1,
        },
        {
          name: "HQ_DIST-SW2_20251006.txt",
          size: "20 KB",
          modified: "2025-10-06",
          content: SAMPLE_DIST_SW2,
        },
      ],
      others: [
        { name: "PhysicalDiagram.pdf", size: "320 KB", modified: "2025-10-01" },
        { name: "LogicalDiagram.pdf", size: "280 KB", modified: "2025-10-01" },
      ],
    },
    vlanDetails: {
      "core-sw1": [
        {
          vlanId: 1,
          name: "default",
          status: "active",
          ports: "-",
          sviIp: null,
          hsrpVip: null,
        },
        {
          vlanId: 10,
          name: "USERS",
          status: "active",
          ports: "Gi1/0/4-5,10-12",
          sviIp: "10.0.0.11/24",
          hsrpVip: "10.0.10.1",
        },
        {
          vlanId: 20,
          name: "CCTV",
          status: "active",
          ports: "Gi1/0/3,6-7",
          sviIp: "10.0.20.1/24",
          hsrpVip: "10.0.20.1",
        },
        {
          vlanId: 30,
          name: "IOT",
          status: "active",
          ports: "Gi1/0/8-9",
          sviIp: "10.0.30.1/24",
          hsrpVip: null,
        },
        {
          vlanId: 99,
          name: "NATIVE",
          status: "active",
          ports: "trunk(native)",
          sviIp: "10.0.99.1/24",
          hsrpVip: null,
        },
      ],
      "dist-sw2": [
        {
          vlanId: 1,
          name: "default",
          status: "active",
          ports: "-",
          sviIp: null,
          hsrpVip: null,
        },
        {
          vlanId: 10,
          name: "USERS",
          status: "active",
          ports: "Gi1/0/1-3",
          sviIp: "10.0.1.21/24",
          hsrpVip: null,
        },
        {
          vlanId: 20,
          name: "CCTV",
          status: "active",
          ports: "Gi1/0/4-5",
          sviIp: "10.0.21.1/24",
          hsrpVip: null,
        },
        {
          vlanId: 30,
          name: "IOT",
          status: "active",
          ports: "Gi1/0/6",
          sviIp: "10.0.31.1/24",
          hsrpVip: null,
        },
      ],
    },
  },
  {
    id: "p2",
    name: "Branch B",
    desc: "Edge / WAN Link",
    manager: "managerA",
    updated: "2025-10-03 09:10",
    status: "Pending",
    members: [
      { username: "managerA", role: "manager" },
      { username: "operatorB", role: "operator" },
    ],
    devices: 5,
    lastBackup: "2025-10-03 02:00",
    services: 3,
    visibility: "Shared",
    topoUrl: new URL("./assets/topo2.png", import.meta.url).href,

    logs: [],
    summaryRows: [],
    documents: { config: [], others: [] },
    vlanDetails: {},
    uploadHistory: [
      {
        id: "upload_branch_1",
        type: "config",
        files: [{ name: "branch-router_config.txt", size: 15000, type: "text/plain" }],
        user: "operatorB",
        project: "p2",
        timestamp: "2025-10-03T09:00:00.000Z",
        details: {
          who: "operatorB",
          what: "Backup Configuration",
          where: "Branch Office",
          when: "Weekly Backup",
          why: "Regular Backup Schedule",
          description: "Weekly configuration backup for branch router"
        }
      },
      {
        id: "upload_branch_2",
        type: "document",
        files: [{ name: "BranchNetworkDiagram.pdf", size: 250000, type: "application/pdf" }],
        user: "managerA",
        project: "p2",
        timestamp: "2025-10-02T14:30:00.000Z",
        details: {
          who: "managerA",
          what: "Create Network Diagram",
          where: "Branch Office",
          when: "New Implementation",
          why: "Project Documentation",
          description: "Initial network diagram for branch office setup"
        }
      }
    ],
  },
];

/* ========= ROOT APP ========= */
export default function App() {
  // Load dark mode preference from localStorage, default to true
  const [dark, setDark] = useState(() => {
    const saved = localStorage.getItem("darkMode");
    return saved !== null ? saved === "true" : true;
  });
  const [users, setUsers] = useState([]);
  const [projects, setProjects] = useState([]);
  const [authedUser, setAuthedUser] = useState(null); // {username, role}
  const [route, setRoute] = useState({ name: "login" });
  const [uploadHistory, setUploadHistory] = useState([]);
  const [loading, setLoading] = useState(false);

  // Apply dark mode class on mount and when dark changes
  useEffect(() => {
    const root = document.documentElement;
    if (dark) {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
    // Save preference to localStorage
    localStorage.setItem("darkMode", dark.toString());
  }, [dark]);

  // Load user info on mount if token exists
  useEffect(() => {
    const loadUser = async () => {
      try {
        const user = await api.getMe();
        setAuthedUser({ username: user.username, role: user.role || "admin" });
        setRoute({ name: "index" });
        await loadProjects();
        if (user.role === "admin") {
          await loadUsers();
        }
      } catch (e) {
        // Not logged in
        api.clearToken();
      }
    };
    if (api.getToken()) {
      loadUser();
    }
  }, []);

  const loadUsers = async () => {
    try {
      const data = await api.getUsers();
      setUsers(data);
    } catch (e) {
      console.error("Failed to load users:", e);
    }
  };

  const loadProjects = async () => {
    try {
      setLoading(true);
      const data = await api.getProjects();
      // Transform backend format to frontend format
      const transformed = await Promise.all(data.map(async (p) => {
        const members = await api.getProjectMembers(p.project_id).catch(() => []);
        // Find manager (first manager or admin, or created_by)
        const manager = members.find(m => m.role === "manager")?.username || 
                       members.find(m => m.role === "admin")?.username || 
                       p.created_by;
        return {
          id: p.project_id,
          project_id: p.project_id,
          name: p.name,
          desc: p.description || "",
          description: p.description || "",
          manager: manager,
          updated: formatDateTime(p.updated_at || p.created_at),
          status: p.visibility === "Shared" ? "Shared" : "Active",
          members: members.map(m => ({ username: m.username, role: m.role })),
          devices: 0,
          lastBackup: "—",
          services: 0,
          visibility: p.visibility || "Private",
          backupInterval: p.backup_interval || "Daily",
          topoUrl: p.topo_url || "",
          topo_url: p.topo_url || "",
          logs: [],
          summaryRows: [],
          documents: { config: [], others: [] },
          vlanDetails: {},
          uploadHistory: [],
          device_images: p.device_images || {}, // Include device_images from database
          created_at: p.created_at,
          created_by: p.created_by,
          updated_at: p.updated_at || p.created_at,
        };
      }));
      setProjects(transformed);
    } catch (e) {
      console.error("Failed to load projects:", e);
    } finally {
      setLoading(false);
    }
  };

  const can = (perm, project = null) => {
    const userRole = authedUser?.role; // System role (admin only)
    if (!userRole) return false;
    
    // Get project role if project is provided
    let projectRole = null;
    if (project && project.members && authedUser?.username) {
      const member = project.members.find(m => m.username === authedUser.username);
      projectRole = member?.role; // manager, engineer, viewer
    }
    
    // System-level permissions (admin only)
    if (perm === "see-all-projects") return userRole === "admin";
    if (perm === "create-project") return userRole === "admin";
    if (perm === "user-management") return userRole === "admin";
    
    // Project-level permissions
    if (perm === "project-setting") {
      // Admin or project manager can access project settings
      return userRole === "admin" || projectRole === "manager";
    }
    if (perm === "upload-config") {
      return userRole === "admin" || ["manager", "engineer"].includes(projectRole);
    }
    if (perm === "upload-document") {
      return userRole === "admin" || ["manager", "engineer"].includes(projectRole);
    }
    if (perm === "view-documents") {
      return true; // All authenticated users can view documents
    }
    return false;
  };

  const handleLogin = async (username, password) => {
    try {
      await api.login(username, password);
      const user = await api.getMe();
      setAuthedUser({ username: user.username, role: user.role || "admin" });
      setRoute({ name: "index" });
      await loadProjects();
      if (user.role === "admin") {
        await loadUsers();
      }
    } catch (e) {
      alert("Login failed: " + e.message);
    }
  };

  const handleLogout = () => {
    api.clearToken();
    setAuthedUser(null);
    setUsers([]);
    setProjects([]);
    setRoute({ name: "login" });
  };

  const memberUsernames = (p) => (p.members || []).map((m) => m.username);
  const isMember = (p, username) => memberUsernames(p).includes(username);

  // #region agent log
  useEffect(() => {
    const logData = {location:'App.jsx:1017',message:'ROUTE_STATE_CHANGE',data:{routeName:route.name,routeDevice:route.device,routeProjectId:route.projectId,hasAuthedUser:!!authedUser},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'};
    console.log('[DEBUG] ROUTE_STATE_CHANGE:', logData);
    fetch('http://127.0.0.1:7242/ingest/b2e1e3ce-f337-4937-85a6-3e6049434e8e',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(logData)}).catch((err) => console.error('[DEBUG] Log fetch failed:', err));
  }, [route.name, route.device, route.projectId, authedUser]);
  // #endregion

  /* Single-pane layout for Index, Project, and Device (above-the-fold, no outer scroll) */
  if (authedUser && (route.name === "index" || route.name === "project" || route.name === "device")) {
    const project = (route.name === "project" || route.name === "device") 
      ? projects.find((p) => (p.project_id || p.id) === route.projectId) 
      : null;
    
    // Build tabs for project view
    const projectTabs = [];
    if (project && route.name === "project") {
      if (can("project-setting", project)) {
        projectTabs.push({ id: "setting", label: "Setting", icon: "⚙️" });
      }
      if (can("view-documents", project)) {
        projectTabs.push({ id: "summary", label: "Summary", icon: "📊" });
        projectTabs.push({ id: "documents", label: "Documents", icon: "📄" });
        projectTabs.push({ id: "analysis", label: "AI Analysis", icon: "🤖" });
      }
    }
    
    return (
      <MainLayout
        topBar={
          <div className="h-full flex items-center justify-between px-4 border-b border-slate-800">
            {/* Left: Logo + Platform Name + Breadcrumb */}
            <div className="flex items-center gap-4 flex-1 min-w-0">
              <button
                onClick={() => setRoute({ name: "index" })}
                className="flex items-center gap-3 hover:opacity-80 transition-opacity cursor-pointer flex-shrink-0"
              >
                <div className="h-7 w-7 rounded-lg bg-blue-600 flex-shrink-0" />
                <span className="text-sm font-semibold text-slate-200 whitespace-nowrap">Network Project Platform</span>
              </button>
              
              {/* Breadcrumb and Tabs (show when in project or device) */}
              {project && (
                <>
                  <span className="text-slate-600 dark:text-slate-400">/</span>
                  <div className="flex items-center gap-4 flex-1 min-w-0">
                    {route.name === "device" ? (
                      <>
                        <button
                          onClick={() => setRoute({ name: "project", projectId: route.projectId, tab: "summary" })}
                          className="text-sm font-medium text-slate-300 hover:text-blue-400 truncate"
                        >
                          {project.name}
                        </button>
                        <span className="text-slate-600 dark:text-slate-400">/</span>
                        <span className="text-sm font-medium text-slate-300 truncate">{route.device}</span>
                      </>
                    ) : (
                      <>
                        <span className="text-sm font-medium text-slate-300 truncate">{project.name}</span>
                        {/* Tabs integrated in header */}
                        {projectTabs.length > 0 && (
                          <nav className="flex items-center gap-1 ml-4">
                            {projectTabs.map((t) => (
                              <button
                                key={t.id}
                                onClick={() => setRoute({ ...route, tab: t.id })}
                                className={`flex items-center gap-2 px-3 py-1.5 text-xs font-medium transition rounded-lg whitespace-nowrap ${
                                  (route.tab || "setting") === t.id
                                    ? "bg-blue-600 text-white"
                                    : "hover:bg-slate-700 hover:text-blue-400 text-slate-400"
                                }`}
                              >
                                <span>{t.icon}</span>
                                <span>{t.label}</span>
                              </button>
                            ))}
                          </nav>
                        )}
                      </>
                    )}
                  </div>
                </>
              )}
            </div>
            
            {/* Right: Dark mode + User + Sign out */}
            <div className="flex items-center gap-2 flex-shrink-0">
              <Button variant="ghost" className="text-slate-400 hover:text-slate-200" onClick={() => setDark(!dark)}>
                {dark ? "🌙" : "☀️"}
              </Button>
              <span className="text-xs text-slate-400">{authedUser?.username}</span>
              <Button variant="secondary" className="text-xs py-1.5 px-3" onClick={handleLogout}>
                Sign out
              </Button>
            </div>
          </div>
        }
        mainClassName="bg-slate-950 overflow-auto"
      >
        {route.name === "index" && (
          <ProjectIndex
            authedUser={authedUser}
            can={can}
            projects={projects}
            openProject={(p) => setRoute({ name: "project", projectId: p.project_id || p.id, tab: "setting" })}
            newProject={() => setRoute({ name: "newProject" })}
            openUserAdmin={() => setRoute({ name: "userAdmin" })}
            openChangePassword={() => setRoute({ name: "changePassword", username: authedUser.username, fromIndex: true })}
            isMember={isMember}
          />
        )}
        {route.name === "project" && project && (
          <ProjectView
            project={project}
            tab={route.tab || "setting"}
            onChangeTab={(tab) => setRoute({ ...route, tab })}
            openDevice={(device) => setRoute({ name: "device", projectId: route.projectId, device })}
            goIndex={() => setRoute({ name: "index" })}
            setProjects={setProjects}
            uploadHistory={uploadHistory}
            setUploadHistory={setUploadHistory}
            can={can}
            authedUser={authedUser}
          />
        )}
        {route.name === "project" && !project && (
          <div className="p-6 text-sm text-rose-400">Project not found.</div>
        )}
        {route.name === "device" && project && route.device && (
          <DeviceDetailsPage
            project={project}
            deviceId={route.device}
            goBack={() => setRoute({ name: "project", projectId: route.projectId, tab: "summary" })}
            goIndex={() => setRoute({ name: "index" })}
            uploadHistory={uploadHistory}
            authedUser={authedUser}
            setProjects={setProjects}
          />
        )}
      </MainLayout>
    );
  }

  return (
    <div
      className={`min-h-screen bg-slate-50 text-slate-900 dark:bg-[#0B0F19] dark:text-gray-100`}
    >
      <div className="mx-auto max-w-[1440px] px-6 py-6">
        <Header
          dark={dark}
          setDark={setDark}
          authedUser={authedUser}
          setRoute={setRoute}
          can={can}
          onLogout={handleLogout}
        />
      </div>
      <div className="mx-auto max-w-[1440px] px-6 py-6">
          <div className="mt-6">
            {route.name === "login" && (
              <Login
                onLogin={handleLogin}
                goChange={(username) =>
                  setRoute({ name: "changePassword", username })
                }
              />
            )}
            {route.name === "changePassword" && (
              <ChangePassword
                initialUsername={route.username || authedUser?.username || ""}
                isLoggedIn={!!authedUser}
                authedUser={authedUser}
                goBack={() => {
                  if (route.fromIndex && authedUser) {
                    // Go back to index if changing password from logged in state
                    setRoute({ name: "index" });
                  } else {
                    // Clear token if changing password from login page
                    if (!authedUser) {
                      api.clearToken();
                    }
                    setRoute({ name: "login" });
                  }
                }}
              />
            )}

            {authedUser && route.name === "index" && (
              <ProjectIndex
                authedUser={authedUser}
                can={can}
                projects={projects}
                openProject={(p) =>
                  setRoute({ name: "project", projectId: p.project_id || p.id, tab: "setting" })
                }
                newProject={() => setRoute({ name: "newProject" })}
                openUserAdmin={() => setRoute({ name: "userAdmin" })}
                openChangePassword={() => setRoute({ name: "changePassword", username: authedUser.username, fromIndex: true })}
                isMember={isMember}
              />
            )}
            {authedUser &&
              route.name === "newProject" &&
              can("create-project") && (
                <NewProjectPage
                  onCancel={() => setRoute({ name: "index" })}
                  onCreate={async (proj) => {
                    await loadProjects();
                    setRoute({ name: "index" });
                  }}
                />
              )}
            {authedUser &&
              route.name === "userAdmin" &&
              can("user-management") && (
                <UserAdminPage
                  users={users}
                  setUsers={setUsers}
                  onClose={async () => {
                    await loadUsers();
                    setRoute({ name: "index" });
                  }}
                />
              )}
            {authedUser && route.name === "project" && (
              <ProjectView
                can={can}
                authedUser={authedUser}
                project={projects.find((p) => (p.project_id || p.id) === route.projectId)}
                tab={route.tab || "setting"}
                onChangeTab={(tab) => setRoute({ ...route, tab })}
                openDevice={(device) => {
                  // #region agent log
                  const logData1 = {location:'App.jsx:1153',message:'openDevice CALLED',data:{device,currentRouteName:route.name,projectId:route.projectId},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'};
                  console.log('[DEBUG] openDevice CALLED:', logData1);
                  fetch('http://127.0.0.1:7242/ingest/b2e1e3ce-f337-4937-85a6-3e6049434e8e',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(logData1)}).catch((err) => console.error('[DEBUG] Log fetch failed:', err));
                  // #endregion
                  console.log('[ProjectView] openDevice called with device:', device);
                  console.log('[ProjectView] Current route:', route);
                  const newRoute = { name: "device", projectId: route.projectId, device };
                  console.log('[ProjectView] Setting new route:', newRoute);
                  // #region agent log
                  const logData2 = {location:'App.jsx:1158',message:'setRoute BEFORE',data:{newRoute},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'};
                  console.log('[DEBUG] setRoute BEFORE:', logData2);
                  fetch('http://127.0.0.1:7242/ingest/b2e1e3ce-f337-4937-85a6-3e6049434e8e',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(logData2)}).catch((err) => console.error('[DEBUG] Log fetch failed:', err));
                  // #endregion
                  setRoute(newRoute);
                  // #region agent log
                  const logData3 = {location:'App.jsx:1159',message:'setRoute AFTER',data:{newRoute},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'};
                  console.log('[DEBUG] setRoute AFTER:', logData3);
                  fetch('http://127.0.0.1:7242/ingest/b2e1e3ce-f337-4937-85a6-3e6049434e8e',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(logData3)}).catch((err) => console.error('[DEBUG] Log fetch failed:', err));
                  // #endregion
                }}
                goIndex={() => setRoute({ name: "index" })}
                setProjects={setProjects}
                uploadHistory={uploadHistory}
                setUploadHistory={setUploadHistory}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* ========= HEADER ========= */
const Header = ({ dark, setDark, authedUser, setRoute, can, onLogout }) => (
  <div className="flex items-center justify-between">
    <button
      onClick={() => {
        if (authedUser) {
          setRoute({ name: "index" });
        } else {
          setRoute({ name: "login" });
        }
      }}
      className="flex items-center gap-3 hover:opacity-80 transition-opacity cursor-pointer"
    >
      <div className="h-8 w-8 rounded-xl bg-blue-600"></div>
      <div className="text-lg font-semibold">Network Project Platform</div>
    </button>
    <div className="flex items-center gap-2">
      <Button variant="ghost" onClick={() => setDark(!dark)}>
        {dark ? "🌙 Dark" : "☀️ Light"}
      </Button>
      {authedUser ? (
        <>
          <div className="text-sm text-gray-300">{authedUser.username}</div>
          <Button
            variant="secondary"
            onClick={onLogout}
          >
            Sign out
          </Button>
        </>
      ) : (
        <Button variant="secondary" onClick={() => setRoute({ name: "login" })}>
          Sign in
        </Button>
      )}
    </div>
  </div>
);

/* ========= LOGIN & CHANGE PASSWORD ========= */
const Login = ({ onLogin, goChange }) => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e?.preventDefault();
    if (!username.trim() || !password.trim()) {
      setError("Please enter username and password");
      return;
    }
    setError("");
    setLoading(true);
    try {
      await onLogin(username.trim(), password);
    } catch (e) {
      // Better error messages
      let errorMsg = e.message || "Login failed";
      if (errorMsg.includes("Cannot connect")) {
        errorMsg = "Cannot connect to server. Please check if the backend is running.";
      } else if (errorMsg.includes("401") || errorMsg.includes("Invalid")) {
        errorMsg = "Invalid username or password. Please try again.";
      } else if (errorMsg.includes("Request failed")) {
        errorMsg = "Login failed. Please check your credentials and try again.";
      }
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid place-items-center py-16">
      <Card className="w-full max-w-md" title="Sign in">
        <form onSubmit={handleSubmit} className="grid gap-3">
          <Field label="Username">
            <Input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter username"
              disabled={loading}
              autoComplete="username"
            />
          </Field>
          <Field label="Password">
            <PasswordInput
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              disabled={loading}
            />
          </Field>
          {error && (
            <div className="text-sm text-rose-500 dark:text-rose-400 bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 rounded-lg px-3 py-2 flex items-start gap-2">
              <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{error}</span>
            </div>
          )}
          <div className="flex items-center justify-between">
            <a
              className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
              href="#"
              onClick={(e) => {
                e.preventDefault();
                goChange(username);
              }}
            >
              Change password
            </a>
            <Button type="submit" disabled={loading}>
              {loading ? "Signing in..." : "Sign in"}
            </Button>
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            Default: admin / admin123
          </div>
        </form>
      </Card>
    </div>
  );
};
const ChangePassword = ({ initialUsername = "", isLoggedIn = false, goBack, authedUser = null }) => {
  const [username, setUsername] = useState(initialUsername);
  const [oldPw, setOldPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [cf, setCf] = useState("");
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(false);
  
  const submit = async () => {
    if (!oldPw || !newPw || !cf) {
      setMsg("❌ Please fill in all fields");
      return;
    }
    if (newPw.length < 6) {
      setMsg("❌ New password must be at least 6 characters");
      return;
    }
    if (newPw !== cf) {
      setMsg("❌ Password confirmation does not match");
      return;
    }
    setMsg("");
    setLoading(true);
    try {
      // If logged in, token should already be set
      // If not logged in, check if token exists
      const token = api.getToken();
      if (!token && !isLoggedIn) {
        setMsg("❌ Please login first to change password");
        setLoading(false);
        return;
      }
      
      await api.changePassword(oldPw, newPw);
      
      setMsg("✅ Password changed successfully." + (isLoggedIn ? "" : " You can sign in now."));
      setTimeout(() => {
        goBack();
      }, 2000);
    } catch (e) {
      let errorMsg = e.message || "Failed to change password. Please check your current password.";
      if (errorMsg.includes("401") || errorMsg.includes("Unauthorized")) {
        errorMsg = "Session expired. Please login again.";
      } else if (errorMsg.includes("400") || errorMsg.includes("Wrong")) {
        errorMsg = "Current password is incorrect. Please try again.";
      }
      setMsg("❌ " + errorMsg);
    } finally {
      setLoading(false);
    }
  };
  return (
    <div className="grid place-items-center py-12">
      <Card className="w-full max-w-md" title="Change Password">
        <div className="grid gap-3">
          <Field label="Username">
            <Input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter username"
              disabled={loading || isLoggedIn}
            />
          </Field>
          <Field label="Current password">
            <PasswordInput
              value={oldPw}
              onChange={(e) => setOldPw(e.target.value)}
              placeholder="Enter current password"
              disabled={loading}
            />
          </Field>
          <Field label="New password">
            <PasswordInput
              value={newPw}
              onChange={(e) => setNewPw(e.target.value)}
              placeholder="Enter new password (min 6 characters)"
              disabled={loading}
            />
          </Field>
          <Field label="Confirm new password">
            <PasswordInput
              value={cf}
              onChange={(e) => setCf(e.target.value)}
              placeholder="Confirm new password"
              disabled={loading}
            />
          </Field>
          {msg && (
            <div className={`text-sm ${msg.startsWith("✅") ? "text-green-600 dark:text-green-400" : "text-rose-400"}`}>
              {msg}
            </div>
          )}
          <div className="flex gap-2">
            <Button onClick={submit} disabled={loading}>
              {loading ? "Updating..." : "Update"}
            </Button>
            <Button variant="secondary" onClick={goBack} disabled={loading}>
              Back
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
};

/* ========= INDEX ========= */
const ProjectIndex = ({
  authedUser,
  can,
  projects,
  openProject,
  newProject,
  openUserAdmin,
  openChangePassword,
  isMember,
}) => {
  const [q, setQ] = useState("");
  const visible = useMemo(() => {
    if (!authedUser) return [];
    const mine = projects.filter(
      (p) => can("see-all-projects") || isMember(p, authedUser.username)
    );
    return mine.filter((p) => p.name.toLowerCase().includes(q.toLowerCase()));
  }, [projects, authedUser, q, can, isMember]);
  return (
    <div className="grid gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">My Projects</h1>
        <div className="flex items-center gap-2">
          <Input
            placeholder="Search projects..."
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          {can("create-project") && (
            <Button onClick={newProject}>New Project</Button>
          )}
          {can("user-management") && (
            <Button variant="secondary" onClick={openUserAdmin}>
              User Admin
            </Button>
          )}
          <Button variant="ghost" onClick={openChangePassword}>
            Change Password
          </Button>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {visible.map((p) => (
          <Card
            key={p.id || p.project_id}
            className="hover:shadow-lg transition-all duration-200 hover:scale-[1.02]"
            title={p.name}
            actions={
              <Badge className={
                (p.visibility === "Shared" 
                  ? "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100"
                  : "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100")
              }>
                {p.visibility === "Shared" ? "Shared" : "Active"}
              </Badge>
            }
          >
            {(p.topoUrl || p.topo_url) ? (
              <img
                src={p.topoUrl || p.topo_url}
                alt="topology"
                className="h-48 w-full object-contain rounded-xl mb-4 border border-gray-200 dark:border-[#1F2937] shadow-sm bg-gray-50 dark:bg-gray-900"
              />
            ) : (
              <div className="h-48 w-full bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-900 rounded-xl mb-4 border border-gray-200 dark:border-[#1F2937] flex items-center justify-center">
                <div className="text-center text-gray-400 dark:text-gray-500">
                  <svg className="w-12 h-12 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                  <p className="text-xs">No topology image</p>
                </div>
              </div>
            )}
            <div className="grid gap-3">
              {p.desc && (
                <div className="text-sm text-gray-600 dark:text-gray-300 line-clamp-2 min-h-[2.5rem]">
                  {p.desc}
                </div>
              )}
              <div className="flex flex-wrap gap-x-4 gap-y-2 text-xs text-gray-500 dark:text-gray-400 pt-1 border-t border-gray-200 dark:border-[#1F2937]">
                <span className="flex items-center gap-1.5">
                  <svg className="w-4 h-4 text-gray-400 dark:text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                  <span className="font-medium text-gray-700 dark:text-gray-300">{p.manager || "—"}</span>
                </span>
                <span className="flex items-center gap-1.5">
                  <svg className="w-4 h-4 text-gray-400 dark:text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>{p.updated}</span>
                </span>
                <span className="flex items-center gap-1.5">
                  <svg className="w-4 h-4 text-gray-400 dark:text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                  <span><b className="text-gray-700 dark:text-gray-300">{p.devices || 0}</b> devices</span>
                </span>
              </div>
              <div className="pt-2">
                <Button 
                  onClick={() => {
                    if (p.project_id || p.id) {
                      openProject(p);
                    } else {
                      console.error("Project missing project_id:", p);
                    }
                  }}
                  className="w-full"
                >
                  Open Project
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};

/* ========= NEW PROJECT ========= */
const NewProjectPage = ({ onCancel, onCreate }) => {
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [members, setMembers] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [availableUsers, setAvailableUsers] = useState([]);
  const [backupInterval, setBackupInterval] = useState("Daily");
  const [visibility, setVisibility] = useState("Private");
  const [topoUrl, setTopoUrl] = useState("");

  useEffect(() => {
    const loadUsers = async () => {
      try {
        const data = await api.getUsers();
        setAvailableUsers(data);
      } catch (e) {
        console.error("Failed to load users:", e);
      }
    };
    loadUsers();
  }, []);

  const addMember = (username, role) => {
    if (!username) return;
    if (members.find((m) => m.username === username)) return;
    setMembers([...members, { username, role }]);
  };
  const remove = (u) => setMembers(members.filter((m) => m.username !== u));
  
  const save = async () => {
    if (!name.trim()) {
      setError("Project name is required");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const project = await api.createProject(name, desc || "", topoUrl, visibility, backupInterval);
      // Add members to project
      for (const member of members) {
        try {
          await api.addProjectMember(project.project_id, member.username, member.role);
        } catch (e) {
          console.error(`Failed to add member ${member.username}:`, e);
        }
      }
      onCreate(project);
    } catch (e) {
      setError(e.message || "Failed to create project");
    } finally {
      setLoading(false);
    }
  };
  
  const handleFile = async (file) => {
    setError("");
    if (!file) {
      setTopoUrl("");
      return;
    }
    // No size limit - just recommend optimal size
    const data = await fileToDataURL(file);
    const img = new Image();
    img.onload = () => {
      let { width, height } = img;
      // Recommend optimal size but don't restrict
      if (width > 1600 || height > 900) {
        // Just set the URL, no error
      }
      setTopoUrl(data);
      setError("");
    };
    img.src = data;
  };
  
  return (
    <div className="grid gap-6">
      <h2 className="text-xl font-semibold">Create New Project</h2>
      <Card title="Project Info">
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="Project Name">
            <Input 
              value={name} 
              onChange={(e) => setName(e.target.value)} 
              placeholder="Enter project name"
              disabled={loading}
            />
          </Field>
          <Field label="Visibility">
            <Select
              value={visibility}
              onChange={setVisibility}
              options={[
                { value: "Private", label: "Private" },
                { value: "Shared", label: "Shared" },
              ]}
              disabled={loading}
            />
          </Field>
          <Field label="Description">
            <Input 
              value={desc} 
              onChange={(e) => setDesc(e.target.value)} 
              placeholder="Enter project description"
              disabled={loading}
            />
          </Field>
          <Field label="Backup Interval">
            <Select
              value={backupInterval}
              onChange={setBackupInterval}
              options={[
                { value: "Hourly", label: "Hourly" },
                { value: "Daily", label: "Daily" },
                { value: "Weekly", label: "Weekly" },
              ]}
              disabled={loading}
            />
          </Field>
          <div className="md:col-span-2 grid gap-2">
            <Field label="Topology Image (Recommended: ≤1.5MB, 1600×900 for best display)">
              <input
                type="file"
                accept="image/*"
                onChange={(e) => handleFile(e.target.files?.[0])}
                disabled={loading}
                className="block w-full text-sm text-gray-500 dark:text-gray-400
                  file:mr-4 file:py-2 file:px-4
                  file:rounded-lg file:border-0
                  file:text-sm file:font-semibold
                  file:bg-blue-50 file:text-blue-700
                  hover:file:bg-blue-100
                  dark:file:bg-blue-900 dark:file:text-blue-300
                  dark:hover:file:bg-blue-800
                  cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </Field>
            {error && <div className="text-sm text-rose-500 dark:text-rose-400">{error}</div>}
            {topoUrl && (
              <img
                src={topoUrl}
                alt="topology preview"
                className="w-full max-w-md h-48 object-contain rounded-xl border border-gray-200 dark:border-[#1F2937]"
              />
            )}
          </div>
        </div>
      </Card>
      <Card title="Members">
        <AddMemberInline 
          members={members} 
          onAdd={addMember}
          availableUsers={availableUsers}
        />
        <div className="mt-3">
          <Table
            columns={[
              { header: "Username", key: "username" },
              { header: "Role", key: "role" },
              {
                header: "",
                key: "x",
                cell: (r) => (
                  <Button variant="danger" onClick={() => remove(r.username)}>
                    Remove
                  </Button>
                ),
              },
            ]}
            data={members}
            empty="No members yet"
          />
        </div>
      </Card>
      <div className="flex gap-2">
        <Button onClick={save} disabled={!name || loading}>
          {loading ? "Creating..." : "Create"}
        </Button>
        <Button variant="secondary" onClick={onCancel} disabled={loading}>
          Cancel
        </Button>
      </div>
    </div>
  );
};

// Password Display Cell Component for User Table
const PasswordDisplayCell = ({ tempPassword }) => {
  const [showPassword, setShowPassword] = useState(false);
  
  if (!tempPassword) {
    return (
      <span className="text-xs text-gray-400 dark:text-gray-500 italic">
        Not available
      </span>
    );
  }
  
  return (
    <div className="flex items-center gap-0.5">
      <span className="font-mono text-sm text-gray-700 dark:text-gray-300">
        {showPassword ? tempPassword : "••••••••"}
      </span>
      <button
        type="button"
        onClick={() => setShowPassword(!showPassword)}
        className="p-0.5 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded transition-colors"
        aria-label={showPassword ? "Hide password" : "Show password"}
      >
        {showPassword ? (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
          </svg>
        ) : (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
        )}
      </button>
    </div>
  );
};

// Delete User Button with confirmation dialog
const DeleteUserButton = ({ username, onDelete }) => {
  const [showConfirm, setShowConfirm] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [deleting, setDeleting] = useState(false);
  
  const handleDelete = async () => {
    if (confirmText.toLowerCase() !== "delete") {
      alert('Please type "delete" to confirm');
      return;
    }
    
    setDeleting(true);
    try {
      await onDelete();
      setShowConfirm(false);
      setConfirmText("");
    } catch (e) {
      // Error handled in onDelete
    } finally {
      setDeleting(false);
    }
  };
  
  if (!showConfirm) {
    return (
      <Button 
        variant="danger" 
        onClick={() => setShowConfirm(true)}
        className="text-sm"
      >
        Delete
      </Button>
    );
  }
  
  return (
    <div className="flex items-center gap-2">
      <Input
        value={confirmText}
        onChange={(e) => setConfirmText(e.target.value)}
        placeholder='Type "delete"'
        className="w-32 text-sm"
        disabled={deleting}
        onKeyDown={(e) => {
          if (e.key === "Enter" && confirmText.toLowerCase() === "delete") {
            handleDelete();
          } else if (e.key === "Escape") {
            setShowConfirm(false);
            setConfirmText("");
          }
        }}
      />
      <Button
        variant="danger"
        onClick={handleDelete}
        disabled={confirmText.toLowerCase() !== "delete" || deleting}
        className="text-sm"
      >
        {deleting ? "Deleting..." : "Confirm"}
      </Button>
      <Button
        variant="secondary"
        onClick={() => {
          setShowConfirm(false);
          setConfirmText("");
        }}
        disabled={deleting}
        className="text-sm"
      >
        Cancel
      </Button>
    </div>
  );
};

/* ========= USER ADMIN (admin only) ========= */
const UserAdminPage = ({ users, setUsers, onClose }) => {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [tempPwd, setTempPwd] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Reload users from database when component mounts
  useEffect(() => {
    const loadUsers = async () => {
      try {
        const updated = await api.getUsers();
        setUsers(updated);
      } catch (e) {
        console.error("Failed to load users:", e);
      }
    };
    loadUsers();
  }, [setUsers]);

  const create = async () => {
    if (!username || !email) {
      setError("Username and email are required");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const result = await api.createUser(username, email, phoneNumber || undefined, tempPwd || undefined);
      const tempPassword = result.temp_password || tempPwd || "123456";
      
      alert(`User created! Temporary password: ${tempPassword}`);
      // Reload users to get temp_password from API
      const updated = await api.getUsers();
      setUsers(updated);
      setUsername("");
      setEmail("");
      setPhoneNumber("");
      setTempPwd("");
    } catch (e) {
      setError(e.message || "Failed to create user");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid gap-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">User Administration</h2>
        <Button variant="secondary" onClick={onClose}>
          ← Back to Index
        </Button>
      </div>
      <Card title="Create Account">
        <div className="grid gap-4">
          <div className="grid gap-3 md:grid-cols-2">
            <Field label="Username">
              <Input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                disabled={loading}
                placeholder="Enter username"
              />
            </Field>
            <Field label="Email">
              <Input 
                value={email} 
                onChange={(e) => setEmail(e.target.value)} 
                type="email"
                disabled={loading}
                placeholder="Enter email"
              />
            </Field>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <Field label="Password">
              <PasswordInput
                value={tempPwd}
                onChange={(e) => setTempPwd(e.target.value)}
                placeholder="Enter temporary password"
                disabled={loading}
              />
            </Field>
            <Field label="Phone Number">
              <Input
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                type="tel"
                disabled={loading}
                placeholder="Enter phone number"
              />
            </Field>
          </div>
        </div>
        {error && (
          <div className="mt-3 text-sm text-rose-500 dark:text-rose-400 bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 rounded-lg px-3 py-2">
            {error}
          </div>
        )}
        <div className="mt-4 flex gap-2">
          <Button onClick={create} disabled={loading}>
            {loading ? "Creating..." : "Create"}
          </Button>
          <Button variant="secondary" onClick={onClose} disabled={loading}>
            Close
          </Button>
        </div>
      </Card>
      <Card title="Existing Users">
        <Table
          columns={[
            { 
              header: "Username", 
              key: "username",
              cell: (row) => (
                <div className="font-medium text-gray-900 dark:text-gray-100">
                  {row.username}
                </div>
              )
            },
            { 
              header: "Email", 
              key: "email",
              cell: (row) => (
                <div className="text-gray-700 dark:text-gray-300">
                  {row.email || "-"}
                </div>
              )
            },
            { 
              header: "Password", 
              key: "temp_password",
              cell: (row) => <PasswordDisplayCell tempPassword={row.temp_password} />
            },
            { 
              header: "Phone Number", 
              key: "phone_number",
              cell: (row) => (
                <div className="text-gray-700 dark:text-gray-300">
                  {row.phone_number || "-"}
                </div>
              )
            },
            { 
              header: "Last login", 
              key: "last_login_at",
              cell: (row) => (
                <div className="text-sm text-gray-600 dark:text-gray-400">
                  {row.last_login_at ? formatDateTime(row.last_login_at) : "-"}
                </div>
              )
            },
            {
              header: "Actions",
              key: "actions",
              cell: (row) => (
                row.username !== "admin" ? (
                  <DeleteUserButton 
                    username={row.username}
                    onDelete={async () => {
                      try {
                        await api.deleteUser(row.username);
                        const updated = await api.getUsers();
                        setUsers(updated);
                        alert(`User "${row.username}" deleted successfully`);
                      } catch (e) {
                        alert("Failed to delete user: " + e.message);
                      }
                    }}
                  />
                ) : (
                  <span className="text-xs text-gray-400 dark:text-gray-500 px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded">Protected</span>
                )
              ),
            },
          ]}
          data={users}
          empty="No users yet"
        />
      </Card>
    </div>
  );
};

/* ========= PROJECT VIEW (Sidebar + pages) ========= */
const ProjectView = ({
  can,
  authedUser,
  project,
  tab,
  onChangeTab,
  openDevice,
  goIndex,
  setProjects,
  uploadHistory,
  setUploadHistory,
}) => {
  if (!project)
    return <div className="text-sm text-rose-400">Project not found</div>;
  
  // Show tabs based on permissions
  const tabs = [];
  if (can("project-setting", project)) {
    tabs.push({ id: "setting", label: "Setting", icon: "⚙️" });
  }
  if (can("view-documents", project)) {
    tabs.push({ id: "summary", label: "Summary", icon: "📊" });
    tabs.push({ id: "documents", label: "Documents", icon: "📄" });
    tabs.push({ id: "analysis", label: "AI Analysis", icon: "🤖" });
  }

  return (
    <div className="h-full flex flex-col min-h-0">
      {/* Main content - full width (header is now in MainLayout topBar) */}
      <main className="flex-1 min-h-0 overflow-hidden flex flex-col gap-3 px-4 py-3">
        {tab === "setting" && can("project-setting", project) && (
          <SettingPage
            project={project}
            setProjects={setProjects}
            authedUser={authedUser}
            goIndex={goIndex}
          />
        )}
        {tab === "summary" && can("view-documents", project) && (
          <div className="flex-1 min-h-0 overflow-hidden flex flex-col">
            <SummaryPage
              project={project}
              can={can}
              authedUser={authedUser}
              setProjects={setProjects}
              openDevice={openDevice}
            />
          </div>
        )}
        {tab === "analysis" && can("view-documents", project) && (
          <AnalysisPage
            project={project}
            authedUser={authedUser}
            onChangeTab={onChangeTab}
          />
        )}
        {tab === "documents" && can("view-documents", project) && (
          <DocumentsPage
            project={project}
            can={can}
            authedUser={authedUser}
            uploadHistory={uploadHistory}
            setUploadHistory={setUploadHistory}
            setProjects={setProjects}
          />
        )}
      </main>
    </div>
  );
};

/* ========= OVERVIEW ========= */
/* ========= OVERVIEW ========= */
const OverviewPage = ({ project, uploadHistory }) => {
  const [searchActivity, setSearchActivity] = useState("");
  const [filterActivityWho, setFilterActivityWho] = useState("all");
  const [filterActivityWhat, setFilterActivityWhat] = useState("all");
  
  // Combine project logs with upload history
  const allHistory = [
    ...(project.logs || []).map(log => ({
      time: log.time,
      files: log.target,
      who: log.user,
      what: log.action,
      where: '—',
      when: '—',
      why: '—',
      description: '—',
      type: 'log',
      details: null,
      uploadRecord: null
    })),
    ...(uploadHistory || []).filter(upload => upload.project === project.id).map(upload => ({
      time: formatDateTime(upload.timestamp),
      files: upload.files.map(f => f.name).join(', '),
      who: upload.details?.who || upload.user,
      what: upload.details?.what || '',
      where: upload.details?.where || '',
      when: upload.details?.when || '',
      why: upload.details?.why || '',
      description: upload.details?.description || '',
      type: 'upload',
      details: upload.details,
      uploadRecord: upload
    }))
  ].sort((a, b) => new Date(b.time) - new Date(a.time));
  
  const uniqueActivityWhos = [...new Set(allHistory.map(h => h.who))];
  const uniqueActivityWhats = [...new Set(allHistory.map(h => h.what))];
  
  const combinedHistory = useMemo(() => {
    return allHistory.filter(activity => {
      const matchSearch = !searchActivity.trim() || 
        [activity.files, activity.who, activity.what, activity.where, activity.description].some(v => 
          (v || "").toLowerCase().includes(searchActivity.toLowerCase())
        );
      const matchWho = filterActivityWho === "all" || activity.who === filterActivityWho;
      const matchWhat = filterActivityWhat === "all" || activity.what === filterActivityWhat;
      return matchSearch && matchWho && matchWhat;
    }).slice(0, 10); // Show only latest 10
  }, [allHistory, searchActivity, filterActivityWho, filterActivityWhat]);

  return (
  <div className="grid gap-6">
    <div className="flex items-center justify-between">
      <div>
        <h2 className="text-xl font-semibold">Overview</h2>
        <div className="text-sm text-gray-500 dark:text-gray-400">
          Last updated: {project.updated} · Manager: {project.manager}
        </div>
      </div>
    </div>

    {/* KPIs */}
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      <Card title="Total Devices"><div className="text-3xl font-semibold">{project.devices}</div></Card>
      <Card title="Last Backup"><div className="text-3xl font-semibold">{project.lastBackup}</div></Card>
      <Card title="Team Members"><div className="text-3xl font-semibold">{project.members.length}</div></Card>
      <Card title="Active Services"><div className="text-3xl font-semibold">{project.services}</div></Card>
    </div>

    {/* Topology (ถ้ามี) */}
    {project.topoUrl && (
      <Card title="Topology Diagram">
        <img src={project.topoUrl} alt="Topology" className="w-full h-72 object-cover rounded-xl" />
      </Card>
    )}

    {/* NEW: Drift & Changes (30 days) — ทุกอุปกรณ์ในโปรเจ็กต์ */}
    <Card title="Drift & Changes (30 days)">
      <div className="grid gap-4">
        {(project.summaryRows || []).map((r) => {
          const [oldF, newF] = getComparePair(project, r.device);
          const lines = getDriftLines(r.device);
          return (
            <div
              key={r.device}
              className="rounded-xl border border-gray-200 dark:border-[#1F2937] bg-white dark:bg-[#0F172A] p-4"
            >
              <div className="flex items-center justify-between gap-4">
                <div className="text-sm">
                  <div className="font-semibold text-gray-800 dark:text-gray-100">Device: {r.device}</div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    Compare file: <span className="font-mono">{oldF}</span> <span className="opacity-70">→</span>{" "}
                    <span className="font-mono">{newF}</span>
                  </div>
                </div>
              </div>

              <ul className="mt-3 space-y-1 text-sm leading-relaxed">
                {lines.map((line, i) => {
                  const first = line.trim().charAt(0);
                  const color =
                    first === "+" ? "text-emerald-400" :
                    first === "−" ? "text-rose-400" :
                    first === "~" ? "text-amber-300" : "text-gray-300";
                  return (
                    <li key={i} className="font-mono">
                      <span className={`${color} font-semibold mr-2`}>{first}</span>
                      <span className="text-gray-200">{line.slice(1).trim()}</span>
                    </li>
                  );
                })}
              </ul>
            </div>
          );
        })}
      </div>
    </Card>

    {/* Combined Logs and Upload History */}
    <Card title="Activity Log (Recent)">
      <div className="mb-4 grid grid-cols-1 md:grid-cols-3 gap-2">
        <Input 
          placeholder="ค้นหา (ชื่อไฟล์, ผู้ใช้, คำอธิบาย...)" 
          value={searchActivity} 
          onChange={(e) => setSearchActivity(e.target.value)} 
        />
        <Select 
          value={filterActivityWho} 
          onChange={setFilterActivityWho} 
                  options={[{value: "all", label: "ทั้งหมด (Responsible User)"}, ...uniqueActivityWhos.map(w => ({value: w, label: w}))]} 
                />
                <Select 
                  value={filterActivityWhat} 
                  onChange={setFilterActivityWhat} 
                  options={[{value: "all", label: "ทั้งหมด (Activity Type)"}, ...uniqueActivityWhats.map(w => ({value: w, label: w}))]}
        />
      </div>
      <Table
        columns={[
          { header: "Time", key: "time" },
          { header: "Name", key: "files" },
          { header: "Responsible User", key: "who" },
          { header: "Activity Type", key: "what" },
          { header: "Site", key: "where" },
          { header: "Operational Timing", key: "when" },
          { header: "Purpose", key: "why" },
          { header: "Description", key: "description" },
          {
            header: "Action",
            key: "act",
            cell: (r) => (
              r.type === 'upload' && r.uploadRecord?.files?.[0] ? (
                <div className="flex gap-2">
                  <Button 
                    variant="secondary" 
                    onClick={() => {
                      const file = r.uploadRecord.files[0];
                      if (!file) return;
                      const blob = new Blob(
                        [file.content || `# ${r.uploadRecord.type === 'config' ? 'Configuration' : 'Document'} Backup\n# File: ${file.name}\n# Uploaded: ${r.time}\n# User: ${r.who}\n\n(mock file content - actual file would be here)`],
                        { type: file.type || (r.uploadRecord.type === 'config' ? "text/plain;charset=utf-8" : "application/octet-stream") }
                      );
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement("a");
                      a.href = url;
                      a.download = file.name || "file";
                      document.body.appendChild(a);
                      a.click();
                      a.remove();
                      URL.revokeObjectURL(url);
                    }}
                  >
                    ⬇ Download
                  </Button>
                </div>
              ) : "—"
            ),
          },
        ]}
        data={combinedHistory}
        empty="No recent activity"
      />
    </Card>
  </div>
  );
};

/* ========= Topology helpers (role + links) ========= */

/* ========= SUMMARY (network-focused) + CSV ========= */
const SummaryPage = ({ project, can, authedUser, setProjects, openDevice }) => {
  // LLM metrics state for topology generation (shared with TopologyGraph)
  const [topologyLLMMetrics, setTopologyLLMMetrics] = React.useState(null);
  const [q, setQ] = useState("");
  const [showUploadConfig, setShowUploadConfig] = useState(false);
  const [summaryRows, setSummaryRows] = useState([]);
  const [dashboardMetrics, setDashboardMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [folderStructure, setFolderStructure] = useState(null);
  // Removed: searchConfig, filterConfigWho, filterConfigWhat, configUploadHistory (History table removed)

  // Load summary + dashboard metrics from API (NOC backend)
  useEffect(() => {
    const loadSummary = async () => {
      const projectId = project?.project_id || project?.id;
      if (!projectId) {
        setLoading(false);
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const [summary, metrics] = await Promise.all([
          api.getConfigSummary(projectId),
          api.getSummaryMetrics(projectId).catch(() => null),
        ]);
        setSummaryRows(summary.summaryRows || []);
        setDashboardMetrics(metrics || null);

        setProjects(prev => {
          const updated = prev.map(p => {
            const pId = p.project_id || p.id;
            if (pId === projectId) {
              const currentRows = p.summaryRows || [];
              const newRows = summary.summaryRows || [];
              if (JSON.stringify(currentRows) !== JSON.stringify(newRows)) {
                return { ...p, summaryRows: newRows };
              }
            }
            return p;
          });
          return updated;
        });
      } catch (err) {
        console.error('Failed to load config summary:', err);
        setError(err.message || 'Failed to load summary data');
        setSummaryRows([]);
        setDashboardMetrics(null);
      } finally {
        setLoading(false);
      }
    };
    loadSummary();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project?.project_id || project?.id]);

  // Load folder structure for upload form
  useEffect(() => {
    const loadFolderStructure = async () => {
      if (!project?.project_id && !project?.id) return;
      try {
        const projectId = project.project_id || project.id;
        const docs = await api.getDocuments(projectId);
        // Build simple folder structure for upload form
        const structure = {
          id: "root",
          name: "/",
          folders: [
            { id: "Config", name: "Config", folders: [], files: [] }
          ],
          files: []
        };
        setFolderStructure(structure);
      } catch (error) {
        console.error('Failed to load folder structure:', error);
      }
    };
    loadFolderStructure();
  }, [project]);

  // Load config upload history from documents
  // Config upload history removed - no longer displayed on Summary page

  const handleUpload = async (uploadRecord, folderId) => {
    console.log('Upload completed:', uploadRecord);
    setShowUploadConfig(false);
    // Reload summary + metrics after upload (wait a bit for backend to parse)
    const projectId = project?.project_id || project?.id;
    if (!projectId) return;
    
    setLoading(true);
    setTimeout(async () => {
      try {
        const [summary, metrics] = await Promise.all([
          api.getConfigSummary(projectId),
          api.getSummaryMetrics(projectId).catch(() => null),
        ]);
        setSummaryRows(summary.summaryRows || []);
        setDashboardMetrics(metrics || null);
        setProjects(prev => {
          const updated = prev.map(p => {
            const pId = p.project_id || p.id;
            if (pId === projectId) {
              return { ...p, summaryRows: summary.summaryRows || [] };
            }
            return p;
          });
          return updated;
        });
      } catch (error) {
        console.error('Failed to reload summary:', error);
      } finally {
        setLoading(false);
      }
    }, 2000); // Wait 2 seconds for parsing to complete
  };

  const handleDeviceClick = (deviceName, e) => {
    // #region agent log
    const logData = {location:'App.jsx:2464',message:'handleDeviceClick ENTRY',data:{deviceName,hasEvent:!!e,hasOpenDevice:!!openDevice},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'};
    console.log('[DEBUG] handleDeviceClick ENTRY:', logData);
    fetch('http://127.0.0.1:7242/ingest/b2e1e3ce-f337-4937-85a6-3e6049434e8e',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(logData)}).catch((err) => console.error('[DEBUG] Log fetch failed:', err));
    // #endregion
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    console.log('handleDeviceClick called with deviceName:', deviceName);
    console.log('openDevice prop:', openDevice);
    if (!deviceName) {
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/b2e1e3ce-f337-4937-85a6-3e6049434e8e',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'App.jsx:2472',message:'handleDeviceClick MISSING_DEVICE',data:{deviceName},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
      // #endregion
      console.error('Device name is missing');
      return;
    }
    if (openDevice) {
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/b2e1e3ce-f337-4937-85a6-3e6049434e8e',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'App.jsx:2477',message:'handleDeviceClick CALLING_OPENDEVICE',data:{deviceName},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
      // #endregion
      console.log('Calling openDevice with:', deviceName);
      openDevice(deviceName);
    } else {
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/b2e1e3ce-f337-4937-85a6-3e6049434e8e',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'App.jsx:2480',message:'handleDeviceClick NO_OPENDEVICE',data:{deviceName},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
      // #endregion
      // Fallback: try to navigate using route if openDevice is not available
      console.error('openDevice prop not provided, cannot navigate to device details');
    }
  };

  const filtered = useMemo(() => {
    if (!q.trim()) return summaryRows;
    return summaryRows.filter((r) =>
      [r.device, r.model, r.mgmt_ip, r.serial].some((v) =>
        (v || "").toLowerCase().includes(q.toLowerCase())
      )
    );
  }, [summaryRows, q]);

  const columns = [
    { header: "DEVICE", key: "device" },
    { header: "MODEL", key: "model" },
    { header: "SERIAL", key: "serial" },
    { header: "OS/VER", key: "os_ver" },
    { header: "MGMT IP", key: "mgmt_ip" },
    { header: "IFACES (T/U/D/A)", key: "ifaces" },
    { header: "ACCESS", key: "access" },
    { header: "TRUNK", key: "trunk" },
    { header: "UNUSED", key: "unused" },
    { header: "VLANS", key: "vlans" },
    { header: "NATIVE VLAN", key: "native_vlan" },
    { header: "TRUNK ALLOWED", key: "trunk_allowed" },
    { header: "STP", key: "stp" },
    { header: "STP ROLE", key: "stp_role" },
    { header: "OSPF NEIGH", key: "ospf_neigh" },
    { header: "BGP ASN/NEIGH", key: "bgp_asn_neigh" },
    { header: "RT-PROTO", key: "rt_proto" },
    { header: "CPU%", key: "cpu" },
    { header: "MEM%", key: "mem" },
    { header: "STATUS", key: "status", cell: (r) => {
        const status = r.status || "OK";
        if (status === "OK") {
          return <span className="text-emerald-400">✅ OK</span>;
        } else if (status === "Drift") {
          return <span className="text-amber-400">⚠ Drift</span>;
        } else {
          return <span className="text-red-400">⚠ {status}</span>;
        }
      }},
    { header: "MORE", key: "more", width: "40px", cell: (r) => (
      <button
        className="w-6 h-6 flex items-center justify-center rounded border border-slate-600 hover:bg-slate-700 text-slate-300 text-[10px] transition-colors mx-auto"
        onClick={(e) => {
          // #region agent log
          const logData = {location:'App.jsx:2556',message:'BUTTON_CLICK',data:{device:r.device,hasEvent:!!e},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'};
          console.log('[DEBUG] BUTTON_CLICK:', logData);
          fetch('http://127.0.0.1:7242/ingest/b2e1e3ce-f337-4937-85a6-3e6049434e8e',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(logData)}).catch((err) => console.error('[DEBUG] Log fetch failed:', err));
          // #endregion
          handleDeviceClick(r.device, e);
        }}
        title="Open Details"
      >
        →
      </button>
    )},
  ];

  const exportCSV = () => {
    const headers = columns.map(c => c.header);
    const rows = (filtered || []).map(r =>
      columns.map(c => {
        const value = c.cell ? c.cell(r) : (r[c.key] ?? "");
        return `"${value.toString().replaceAll('"','""')}"`;
      }).join(","));
    downloadCSV([headers.join(","), ...rows].join("\n"), `summary_${project.name}.csv`);
  };

  /* Above-the-fold metrics: from backend dashboard API or fallback to summaryRows */
  const totalDevices = dashboardMetrics?.total_devices ?? summaryRows.length;
  const okCount = dashboardMetrics?.healthy ?? summaryRows.filter((r) => (r.status || "").toLowerCase() === "ok").length;
  const criticalCount = dashboardMetrics?.critical ?? summaryRows.filter((r) => (r.status || "").toLowerCase() !== "ok").length;
  const coreCount = dashboardMetrics?.core ?? summaryRows.filter((r) => /core/i.test(r.device || "")).length;
  const distCount = dashboardMetrics?.dist ?? summaryRows.filter((r) => /dist|distribution/i.test(r.device || "")).length;
  const accessCount = dashboardMetrics?.access ?? summaryRows.filter((r) => /access/i.test(r.device || "")).length;

  // ====== UI: Single-pane, above-the-fold (1920x1080) ======
  return (
    <div className="h-full flex flex-col gap-0 overflow-hidden min-h-0">
      {/* Content section header - integrated design */}
      <div className="flex-shrink-0 flex items-center justify-between gap-2 py-0.5 px-2">
        <h2 className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
          <span className="w-0.5 h-3 bg-blue-500/70 rounded-full"></span>
          Summary Config
        </h2>
        <div className="flex gap-1.5 items-center">
          <div className="relative">
            <Input 
              placeholder="Search..." 
              value={q} 
              onChange={(e)=>setQ(e.target.value)} 
              className="w-28 text-[9px] py-1 px-2.5 h-6 bg-slate-900/80 border-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500/50 rounded-md" 
            />
            <span className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[9px] text-slate-500 pointer-events-none">🔍</span>
          </div>
          <button
            className="px-2.5 py-0.5 h-6 flex items-center justify-center rounded-md border border-slate-700 bg-slate-900/80 hover:bg-slate-800 hover:border-slate-600 text-slate-300 text-[9px] font-medium transition-all duration-150 whitespace-nowrap"
            onClick={exportCSV}
            title="Export CSV"
          >
            CSV
          </button>
          {can("upload-config", project) && (
            <button
              className="px-2.5 py-0.5 h-6 flex items-center justify-center rounded-md border border-slate-700 bg-slate-900/80 hover:bg-slate-800 hover:border-slate-600 text-slate-300 text-[9px] font-medium transition-all duration-150 whitespace-nowrap"
              onClick={() => setShowUploadConfig(true)}
              title="Upload Config"
            >
              Upload
            </button>
          )}
        </div>
      </div>

      {showUploadConfig && folderStructure && (
        <UploadDocumentForm
          project={project}
          authedUser={authedUser}
          onClose={() => setShowUploadConfig(false)}
          onUpload={handleUpload}
          folderStructure={folderStructure}
          defaultFolderId="Config"
        />
      )}

      {/* Topology (2/3) + Narrative (1/3) */}
      <div className="flex-1 min-h-0 grid grid-cols-12 gap-3">
        <div className="col-span-6 min-h-0 overflow-hidden rounded-xl border border-slate-800 bg-slate-900/50">
          <TopologyGraph project={project} onOpenDevice={(id)=>openDevice(id)} can={can} authedUser={authedUser} setProjects={setProjects} setTopologyLLMMetrics={setTopologyLLMMetrics} topologyLLMMetrics={topologyLLMMetrics} />
        </div>
        <div className="col-span-6 min-h-0 overflow-auto rounded-xl border border-slate-800 bg-slate-900/50 p-2 text-[10px] text-slate-400 space-y-1.5 break-words">
          <div className="font-semibold text-slate-300 text-xs">Auto Summary</div>
          <div className="break-words">อุปกรณ์รวม: {project.summaryRows.length} เครื่อง (Core: {coreCount}, Dist: {distCount}, Access: {accessCount})</div>
          <div className="break-words">โครงแบบ: Core ↔ Distribution ↔ Access • HSRP/STP • OSPF/BGP</div>
          <div className="text-slate-500">ล่าสุด: {project.lastBackup || "—"}</div>
          
          {/* LLM Metrics (แสดงเมื่อมีการ generate topology ด้วย LLM) */}
          {topologyLLMMetrics && (
            <>
              <div className="font-semibold text-slate-300 pt-1.5 border-t border-slate-700 mt-1.5 text-xs">LLM Processing Info</div>
              <div className="space-y-0.5 break-words">
                <div className="break-words">โมเดล: <span className="text-slate-200">{topologyLLMMetrics.model_name || "—"}</span></div>
                <div>เวลา: <span className="text-slate-200">{topologyLLMMetrics.inference_time_ms ? `${(topologyLLMMetrics.inference_time_ms / 1000).toFixed(2)}s` : "—"}</span></div>
                {topologyLLMMetrics.token_usage && (
                  <>
                    <div>Tokens: <span className="text-slate-200">{topologyLLMMetrics.token_usage.total_tokens || topologyLLMMetrics.token_usage.prompt_tokens + topologyLLMMetrics.token_usage.completion_tokens || "—"}</span></div>
                    <div className="text-slate-500 text-[9px] pl-1.5 break-words">
                      (Prompt: {topologyLLMMetrics.token_usage.prompt_tokens || 0}, 
                      Completion: {topologyLLMMetrics.token_usage.completion_tokens || 0})
                    </div>
                  </>
                )}
                {topologyLLMMetrics.devices_processed && (
                  <div className="break-words">อุปกรณ์ที่วิเคราะห์: <span className="text-slate-200">{topologyLLMMetrics.devices_processed}</span></div>
                )}
              </div>
            </>
          )}
          
          <div className="font-semibold text-slate-300 pt-1 text-xs">Recommendations</div>
          <ul className="list-disc pl-3 space-y-0.5 break-words">
            <li className="break-words">ตั้งค่า NTP ให้ Sync</li>
            <li className="break-words">กำหนด HSRP/STP priority</li>
            <li className="break-words">portfast/bpduguard ด้าน access</li>
          </ul>
        </div>
      </div>

      {/* Table: fills remaining height, scrolls inside */}
      {loading ? (
        <div className="flex-1 min-h-0 flex items-center justify-center rounded-xl border border-slate-800 bg-slate-900/50">
          <div className="text-sm text-slate-400">Loading summary data...</div>
        </div>
      ) : error ? (
        <div className="flex-1 min-h-0 flex flex-col items-center justify-center rounded-xl border border-slate-800 bg-slate-900/50 p-4">
          <div className="text-sm text-rose-400 font-semibold mb-2">Error loading summary</div>
          <div className="text-xs text-slate-400 mb-3">{error}</div>
          <Button variant="secondary" className="text-xs" onClick={() => {
            setError(null);
            const projectId = project?.project_id || project?.id;
            if (projectId) {
              setLoading(true);
              Promise.all([
                api.getConfigSummary(projectId),
                api.getSummaryMetrics(projectId).catch(() => null),
              ])
                .then(([summary, metrics]) => {
                  setSummaryRows(summary.summaryRows || []);
                  setDashboardMetrics(metrics || null);
                  setLoading(false);
                })
                .catch(err => { setError(err.message || 'Failed to load summary data'); setLoading(false); });
            }
          }}>Retry</Button>
        </div>
      ) : (
        <div className="flex-1 min-h-0 overflow-auto rounded-xl border border-slate-800 bg-slate-900/50 p-1" style={{ maxHeight: 'calc(100vh - 575px)' }}>
          <Table columns={columns} data={filtered} empty="No devices yet. Upload config files to see summary." minWidthClass="min-w-full" containerClassName="text-[12px]" />
        </div>
      )}


      {/* Upload Config Modal */}
      {showUploadConfig && (
        <UploadConfigForm
          project={project}
          authedUser={authedUser}
          onClose={() => setShowUploadConfig(false)}
          onUpload={handleUpload}
        />
      )}
    </div>
  );
};


/* ========= DEVICE DETAILS PAGE (with header navigation) ========= */
const DeviceDetailsPage = ({ project, deviceId, goBack, goIndex, uploadHistory, authedUser, setProjects }) => {
  if (!project) {
    return <div className="text-sm text-rose-400">Project not found</div>;
  }

  return (
    <div className="h-full flex flex-col min-h-0 px-6 py-4">
      <DeviceDetailsView
        project={project}
        deviceId={deviceId}
        goBack={goBack}
        uploadHistory={uploadHistory}
        authedUser={authedUser}
        setProjects={setProjects}
      />
    </div>
  );
};

/* ========= DEVICE DETAILS (Overview / Interfaces / VLANs / Raw) ========= */
/* ========= DEVICE DETAILS (Overview / Interfaces / VLANs / Raw) ========= */
const DeviceDetailsView = ({ project, deviceId, goBack, uploadHistory, authedUser, setProjects }) => {
  console.log('[DeviceDetailsView] Rendering with props:', { project, deviceId, hasGoBack: !!goBack });
  
  // Early return if project or deviceId is missing
  if (!project) {
    console.error('[DeviceDetailsView] Project not found');
    return (
      <div className="grid gap-4">
        <div className="text-sm text-rose-400">Project not found</div>
        {goBack && <Button variant="secondary" onClick={goBack}>← Back to Summary</Button>}
      </div>
    );
  }

  if (!deviceId) {
    console.error('[DeviceDetailsView] Device ID not provided');
    return (
      <div className="grid gap-4">
        <div className="text-sm text-rose-400">Device ID not provided</div>
        {goBack && <Button variant="secondary" onClick={goBack}>← Back to Summary</Button>}
      </div>
    );
  }

  // State for API data
  const [deviceData, setDeviceData] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(null);

  // Fetch device details from API
  React.useEffect(() => {
    const fetchDeviceDetails = async () => {
      if (!project?.project_id && !project?.id) return;
      if (!deviceId) return;
      
      setLoading(true);
      setError(null);
      try {
        const projectId = project.project_id || project.id;
        const details = await api.getDeviceDetails(projectId, deviceId);
        console.log('📥 Received device details from API:', {
          device_name: details?.device_name,
          neighbors_count: details?.neighbors?.length || 0,
          has_original_content: !!details?.original_content,
          neighbors_sample: details?.neighbors?.slice(0, 2),
          all_keys: Object.keys(details || {})
        });
        setDeviceData(details);
      } catch (err) {
        console.error('Failed to load device details:', err);
        setError(err.message || 'Failed to load device details');
      } finally {
        setLoading(false);
      }
    };

    fetchDeviceDetails();
  }, [project?.project_id || project?.id, deviceId]);

  // เลือก row ของอุปกรณ์นี้จาก summaryRows (ข้อมูลจริงจาก API)
  const row =
    project?.summaryRows?.find((r) => r.device === deviceId) ||
    project?.summaryRows?.[0] ||
    null;

  // State for device backups and config history from API
  const [deviceBackups, setDeviceBackups] = React.useState([]);
  const [deviceConfigHistory, setDeviceConfigHistory] = React.useState([]);
  const [loadingBackups, setLoadingBackups] = React.useState(true);

  // Fetch device backups and config history from API
  React.useEffect(() => {
    const fetchDeviceBackups = async () => {
      if (!project?.project_id && !project?.id) return;
      if (!deviceId) return;
      
      setLoadingBackups(true);
      try {
        const projectId = project.project_id || project.id;
        
        // Get all config documents for this project
        const docs = await api.getDocuments(projectId, { folder_id: "Config" });
        
        // Filter documents that match this device
        const devBase = deviceId.toLowerCase();
        const keyVariants = [
          devBase,
          devBase.replace(/-/g, "_"),
          devBase.replace(/_/g, "-"),
          devBase.replace(/[-_]/g, ""),
        ];
        
        const matchingDocs = docs.filter((doc) => {
          const name = (doc.filename || "").toLowerCase();
          return keyVariants.some((k) => name.includes(k));
        });
        
        // Sort by created_at descending (newest first)
        const sorted = matchingDocs.sort((a, b) => {
          const dateA = new Date(a.created_at || 0);
          const dateB = new Date(b.created_at || 0);
          return dateB - dateA;
        });
        
        setDeviceBackups(sorted);
        
        // Transform to config history format
        const history = sorted.map(doc => ({
          timestamp: doc.created_at,
          files: [{ 
            name: doc.filename,
            document_id: doc.document_id,
            version: doc.version
          }],
          user: doc.uploader || "Unknown",
          details: {
            who: doc.metadata?.who || doc.uploader || "Unknown",
            what: doc.metadata?.what || "—",
            where: doc.metadata?.where || "—",
            when: doc.metadata?.when || "—",
            why: doc.metadata?.why || "—",
            description: doc.metadata?.description || "—",
          },
          type: "config",
          project: projectId,
        }));
        
        setDeviceConfigHistory(history);
      } catch (err) {
        console.error('Failed to load device backups:', err);
        setDeviceBackups([]);
        setDeviceConfigHistory([]);
      } finally {
        setLoadingBackups(false);
      }
    };

    fetchDeviceBackups();
  }, [project?.project_id || project?.id, deviceId]);

  // default: 2 ไฟล์ล่าสุด
  const [compareOpen, setCompareOpen] = React.useState(false);
  const [leftFileName, setLeftFileName] = React.useState("");
  const [rightFileName, setRightFileName] = React.useState("");
  
  // Update default file names when deviceBackups change
  React.useEffect(() => {
    if (deviceBackups.length >= 2) {
      setLeftFileName(deviceBackups[1]?.filename || deviceBackups[0]?.filename || "");
      setRightFileName(deviceBackups[0]?.filename || deviceBackups[1]?.filename || "");
    } else if (deviceBackups.length === 1) {
      setLeftFileName(deviceBackups[0]?.filename || "");
      setRightFileName("");
    }
  }, [deviceBackups]);
  
  const leftFile = deviceBackups.find((f) => f.filename === leftFileName);
  const rightFile = deviceBackups.find((f) => f.filename === rightFileName);

  // modal preview สำหรับกดจากตาราง Backup
  const [bkPreview, setBkPreview] = React.useState(null);
  const [searchBackup, setSearchBackup] = React.useState("");
  const [filterBackupWho, setFilterBackupWho] = React.useState("all");
  const [filterBackupWhat, setFilterBackupWhat] = React.useState("all");

  // diff แบบง่าย (บรรทัดต่อบรรทัด)
  const simpleDiff = React.useCallback((aText = "", bText = "") => {
    const a = (aText || "").split(/\r?\n/);
    const b = (bText || "").split(/\r?\n/);
    const max = Math.max(a.length, b.length);
    const out = [];
    for (let i = 0; i < max; i++) {
      const L = a[i] ?? "";
      const R = b[i] ?? "";
      if (L === R) out.push({ t: "=", l: L });
      else {
        if (L) out.push({ t: "-", l: L });
        if (R) out.push({ t: "+", l: R });
      }
    }
    return out;
  }, []);


  // Extract facts from API data or fallback to row data
  const overview = deviceData?.device_overview || {};
  const interfaces = deviceData?.interfaces || [];
  const vlansData = deviceData?.vlans || {};
  const stpData = deviceData?.stp || {};
  const routingData = deviceData?.routing || {};
  const neighborsData = deviceData?.neighbors || [];
  
  // Debug logging
  React.useEffect(() => {
    if (deviceData) {
      console.log('🔍 DeviceDetailsView - neighborsData:', {
        count: neighborsData.length,
        data: neighborsData,
        deviceData_keys: Object.keys(deviceData),
        has_neighbors_field: 'neighbors' in deviceData
      });
    }
  }, [deviceData, neighborsData]);
  const macArpData = deviceData?.mac_arp || {};
  const securityData = deviceData?.security || {};
  const haData = deviceData?.ha || {};

  // Calculate stats from real data
  const totalIfaces = interfaces.length;
  const upIfaces = interfaces.filter(i => i.oper_status === "up").length;
  const downIfaces = interfaces.filter(i => i.oper_status === "down").length;
  const adminDown = interfaces.filter(i => i.admin_status === "down").length;
  const accessPorts = interfaces.filter(i => i.port_mode === "access").length;
  const trunkPorts = interfaces.filter(i => i.port_mode === "trunk").length;
  const vlanList = vlansData.vlan_list || [];
  const vlanCount = vlanList.length;

  // facts - use API data ONLY (no fallback to row/mock data)
  // Note: All device info is now stored in device_overview, not top-level fields
  const facts = {
    device: deviceData?.device_name || deviceId,
    model: overview.model || "—",
    osVersion: overview.os_version || "—",
    serial: overview.serial_number || "—",
    mgmtIp: overview.mgmt_ip || "—",
    role: overview.role || "—",
    vlanCount: vlanCount || 0,
    stpMode: stpData.mode || "—",
    stpRoot: stpData.root_bridge_id || "—",
    trunkCount: trunkPorts || 0,
    accessCount: accessPorts || 0,
    sviCount: interfaces.filter(i => i.type === "Vlan" || i.name?.startsWith("Vlan")).length || 0,
    hsrpGroups: haData.hsrp?.groups?.length || 0,
    vrrpGroups: haData.vrrp?.groups?.length || 0,
    routing: Object.keys(routingData).filter(k => routingData[k] && Object.keys(routingData[k]).length > 0 && k !== "routing_table").join(", ") || "—",
    ospfNeighbors: routingData.ospf?.neighbors?.length || 0,
    bgpAsn: routingData.bgp?.as_number ?? routingData.bgp?.local_as ?? "—",
    bgpNeighbors: routingData.bgp?.peers?.length || 0,
    cdpNeighbors: neighborsData.filter(n => n.protocol === "CDP").length || 0,
    lldpNeighbors: neighborsData.filter(n => n.protocol === "LLDP").length || 0,
    ntpStatus: securityData.ntp?.status || securityData.ntp?.synchronized ? "Synchronized" : "—",
    snmp: securityData.snmp?.enabled ? "Enabled" : "—",
    syslog: securityData.logging?.enabled || securityData.syslog?.enabled ? "Enabled" : "—",
    cpu: overview.cpu_utilization ?? overview.cpu_util ?? "—",
    mem: overview.memory_usage ?? overview.mem_util ?? "—",
    uptime: overview.uptime || "—",
    ifaces: {
      total: totalIfaces,
      up: upIfaces,
      down: downIfaces,
      adminDown: adminDown
    },
    allowedVlansShort: "—", // Not available from parsed data
  };
  
  // Device narrative - use facts from API data only
  const deviceNarrative = React.useMemo(() => {
    if (!deviceData && loading) return "Device information is being loaded...";
    if (!deviceData) return "No device data available.";
    
    const parts = [];
    parts.push(`สรุปอัตโนมัติของอุปกรณ์: ${facts.device}`);
    parts.push([
      `• รุ่น/แพลตฟอร์ม: ${facts.model} • OS/Version: ${facts.osVersion}`,
      `• Serial: ${facts.serial} • Mgmt IP: ${facts.mgmtIp}`
    ].join("  |  "));
    
    if (facts.ifaces) {
      parts.push(`• พอร์ตทั้งหมด ${facts.ifaces.total} (Up ${facts.ifaces.up}, Down ${facts.ifaces.down}, AdminDown ${facts.ifaces.adminDown})`);
      parts.push(`• Access ≈ ${facts.accessCount}  |  Trunk ≈ ${facts.trunkCount}`);
    }
    parts.push(`• VLAN ทั้งหมด: ${facts.vlanCount}  |  STP: ${facts.stpMode}${facts.stpRoot && facts.stpRoot !== "—" ? ` (Root: ${facts.stpRoot})` : ""}`);
    
    // L3
    const l3 = [];
    if (facts.routing && facts.routing !== "—") l3.push(facts.routing);
    if (facts.ospfNeighbors > 0) l3.push(`OSPF ${facts.ospfNeighbors} neigh`);
    if (facts.bgpAsn && facts.bgpAsn !== "—") l3.push(`BGP ${facts.bgpAsn}/${facts.bgpNeighbors}`);
    if (l3.length) parts.push(`• Routing: ${l3.join(" | ")}`);
    
    // Neighbors
    if (facts.cdpNeighbors > 0 || facts.lldpNeighbors > 0) {
      parts.push(`• Neighbors: CDP ${facts.cdpNeighbors} / LLDP ${facts.lldpNeighbors}`);
    }
    
    // Mgmt/Health
    parts.push(`• NTP: ${facts.ntpStatus}  |  SNMP: ${facts.snmp}  |  Syslog: ${facts.syslog}  |  CPU ${facts.cpu}% / MEM ${facts.mem}%`);
    
    // HA
    if (facts.hsrpGroups > 0 || facts.vrrpGroups > 0) {
      parts.push(`• HA: HSRP ${facts.hsrpGroups} groups / VRRP ${facts.vrrpGroups} groups`);
    }
    
    return parts.join("\n");
  }, [deviceData, facts, loading]);

  // Recommendations - use facts from API data only
  const deviceRecs = React.useMemo(() => {
    if (!deviceData) return [];
    
    const recs = [];
    
    // NTP
    if (!facts.ntpStatus || facts.ntpStatus === "—" || !/sync/i.test(facts.ntpStatus)) {
      recs.push("ตั้งค่า NTP ให้ Sync เพื่อความถูกต้องของ Time (ตรวจสอบ server, key, timezone)");
    }
    
    // Syslog
    if (!facts.syslog || facts.syslog === "—") {
      recs.push("กำหนด logging host/syslog server เพื่อบันทึกเหตุการณ์ส่วนกลาง");
    }
    
    // STP
    if (facts.stpMode && facts.stpMode !== "—" && /pvst|rpvst|mstp/i.test(facts.stpMode)) {
      const role = classifyRoleByName(facts.device);
      if (role === "core") {
        recs.push("กำหนด STP priority (เช่น 4096) ให้ Core เป็น Root Primary สำหรับ VLAN หลัก");
      } else if (role === "distribution") {
        recs.push("กำหนด STP priority (เช่น 8192/12288) เป็น Root Secondary ตาม Policy และเปิด UplinkFast (ถ้ารองรับ)");
      } else if (role === "access") {
        recs.push("เปิด portfast และ bpduguard บนพอร์ต access เพื่อลด Time convergence และป้องกัน loop");
      }
    }
    
    // Interfaces health
    if (facts.ifaces && facts.ifaces.down > 10) {
      recs.push(`ตรวจสอบพอร์ตที่ Down จำนวน ${facts.ifaces.down} พอร์ต อาจมีปัญหาทางกายภาพหรือการตั้งค่า`);
    }
    
    // Security
    if (!facts.snmp || facts.snmp === "—") {
      recs.push("พิจารณาตั้งค่า SNMP สำหรับการตรวจสอบและจัดการอุปกรณ์");
    }
    
    return recs;
  }, [deviceData, facts]);

  // VLANs - transform from API data
  const vlans = React.useMemo(() => {
    if (!vlansData || !vlanList.length) return [];
    return vlanList.map(vlanId => {
      const vlanName = vlansData.vlan_names?.[vlanId] || "";
      const vlanStatus = vlansData.vlan_status?.[vlanId] || "active";
      // Find ports in this VLAN
      const accessPorts = interfaces.filter(i => i.port_mode === "access" && i.access_vlan === vlanId).map(i => i.name);
      const trunkPorts = interfaces.filter(i => i.port_mode === "trunk" && i.allowed_vlans?.includes(vlanId)).map(i => i.name);
      const ports = [...accessPorts, ...trunkPorts];
      // Find SVI IP
      const sviInterface = interfaces.find(i => (i.type === "Vlan" || i.name?.startsWith("Vlan")) && i.name?.includes(vlanId));
      const sviIp = sviInterface?.ipv4_address || null;
      // Find HSRP VIP (if any)
      const hsrpGroup = haData.hsrp?.groups?.find(g => g.vlan_id === vlanId);
      const hsrpVip = hsrpGroup?.virtual_ip || null;
      
      return {
        vlanId,
        name: vlanName,
        status: vlanStatus,
        ports: ports.join(", ") || "—",
        sviIp: sviIp || "—",
        hsrpVip: hsrpVip || "—"
      };
    });
  }, [vlansData, interfaces, haData]);

  // Interfaces - transform from API data (include STP fields from parser)
  const ifaces = React.useMemo(() => {
    return interfaces.map(iface => ({
      port: iface.name || "—",
      admin: iface.admin_status || "—",
      oper: iface.oper_status || "—",
      mode: iface.port_mode || "—",
      accessVlan: iface.access_vlan || null,
      nativeVlan: iface.native_vlan || null,
      allowedShort: (Array.isArray(iface.allowed_vlans) ? iface.allowed_vlans.join(",") : (typeof iface.allowed_vlans === 'string' ? iface.allowed_vlans : null)) || "—",
      poeW: iface.poe_power || null,
      speed: iface.speed || "—",
      duplex: iface.duplex || "—",
      errors: iface.errors ? `${iface.errors.input || 0}/${iface.errors.output || 0}` : "0/0",
      stp: stpData.port_states?.[iface.name] || "—",
      stpRole: iface.stp_role || "—",  // From parser
      stpState: iface.stp_state || "—",  // From parser
      stpEdgedPort: iface.stp_edged_port !== undefined ? (iface.stp_edged_port ? "Yes" : "No") : "—",  // From parser
      ipv4: iface.ipv4_address || "—",
      desc: iface.description || ""
    }));
  }, [interfaces, stpData]);
  const ifaceColumns = [
    { header: "Port", key: "port" }, 
    { header: "Admin", key: "admin" }, 
    { header: "Oper", key: "oper" }, 
    { header: "Mode", key: "mode" },
    { header: "IPv4", key: "ipv4", cell: (r) => r.ipv4 || "—" },
    { header: "Access VLAN", key: "accessVlan", cell: (r) => r.accessVlan ?? "—" },
    { header: "Native", key: "nativeVlan", cell: (r) => r.nativeVlan ?? "—" },
    { header: "Allowed VLANs", key: "allowedShort" },
    { header: "STP Role", key: "stpRole", cell: (r) => r.stpRole || "—" },
    { header: "STP State", key: "stpState", cell: (r) => r.stpState || "—" },
    { header: "STP Edged", key: "stpEdgedPort", cell: (r) => r.stpEdgedPort || "—" },
    { header: "Speed", key: "speed" }, 
    { header: "Duplex", key: "duplex" },
    { header: "PoE (W)", key: "poeW", cell: (r) => r.poeW ?? "—" },
    { header: "Description", key: "desc" },
  ];
  const [qMode, setQMode] = React.useState("all");
  const [qState, setQState] = React.useState("all");
  const [qVlan, setQVlan] = React.useState("");
  const [qSpeed, setQSpeed] = React.useState("all");
  const filteredIfaces = React.useMemo(() => {
    return ifaces.filter((r) => {
      if (qMode !== "all" && r.mode !== qMode) return false;
      if (qState !== "all") {
        const isUp = r.admin === "up" && r.oper === "up";
        if (qState === "up" && !isUp) return false;
        if (qState === "down" && isUp) return false;
      }
      if (qVlan && String(r.accessVlan || "") !== String(qVlan)) return false;
      if (qSpeed !== "all" && r.speed !== qSpeed) return false;
      return true;
    });
  }, [ifaces, qMode, qState, qVlan, qSpeed]);

  const onExportIfaces = () => {
    const headers = ifaceColumns.map((c) => c.key);
    const rows = filteredIfaces.map((r) =>
      headers.map((h) => (r[h] != null ? `"${String(r[h]).replaceAll('"', '""')}"` : "")).join(",")
    );
    downloadCSV([headers.join(","), ...rows].join("\n"), `${facts.device}_interfaces.csv`);
  };

  const vlanColumns = [
    { header: "VLAN ID", key: "vlanId" }, { header: "Name", key: "name" }, { header: "Status", key: "status" },
    { header: "Ports", key: "ports" }, { header: "SVI IP", key: "sviIp", cell: (r) => r.sviIp || "—" },
    { header: "HSRP VIP", key: "hsrpVip", cell: (r) => r.hsrpVip || "—" },
  ];
  const exportVlans = () => {
    const headers = ["vlanId","name","status","ports","sviIp","hsrpVip"];
    const rows = vlans.map((v) => headers.map((h) => `"${String(v[h] ?? "").replaceAll('"','""')}"`).join(","));
    downloadCSV([headers.join(","), ...rows].join("\n"), `${facts.device}_vlans.csv`);
  };

  // Tabs
  const [tab, setTab] = React.useState("overview"); // overview | interfaces | vlans | stp | routing | neighbors | macarp | security | ha | raw
  const [rawSubTab, setRawSubTab] = React.useState("parsed"); // parsed | original

  // คำนวณ drift summary จาก 2 ไฟล์ล่าสุดถ้ามี (ใช้ข้อมูลจาก API)
  const lastTwo = deviceBackups.slice(0, 2);
  const driftSummary = React.useMemo(() => {
    if (lastTwo.length < 2) return null;
    const [newF, oldF] = [lastTwo[0], lastTwo[1]]; // ใหม่ ← เก่า
    // Note: We don't have file content here, so we can't calculate diff
    // This would require fetching file content from API
    return {
      device: facts.device,
      from: oldF.filename || oldF.name,
      to: newF.filename || newF.name,
      lines: [], // Would need to fetch file content to calculate diff
    };
  }, [facts.device, lastTwo]);

  // ตาราง Backup Config History (ใช้ deviceConfigHistory จาก API)
  const uniqueBackupWhos = React.useMemo(() => 
    [...new Set(deviceConfigHistory.map(d => d.details?.who || d.user))],
    [deviceConfigHistory]
  );
  const uniqueBackupWhats = React.useMemo(() => 
    [...new Set(deviceConfigHistory.map(d => d.details?.what || "—"))],
    [deviceConfigHistory]
  );
  
  const filteredBackupHistory = React.useMemo(() => {
    return deviceConfigHistory.filter(backup => {
      const matchSearch = !searchBackup.trim() || 
        [backup.files.map(f => f.name).join(', '), 
         backup.details?.who || backup.user,
         backup.details?.what || "—",
         backup.details?.where || "—",
         backup.details?.description || "—"].some(v => 
          v.toLowerCase().includes(searchBackup.toLowerCase())
        );
      const matchWho = filterBackupWho === "all" || (backup.details?.who || backup.user) === filterBackupWho;
      const matchWhat = filterBackupWhat === "all" || (backup.details?.what || "—") === filterBackupWhat;
      return matchSearch && matchWho && matchWhat;
    });
  }, [deviceConfigHistory, searchBackup, filterBackupWho, filterBackupWhat]);
  
  const backupCols = [
    { header: "Time", key: "timestamp", cell: (r) => formatDateTime(r.timestamp) },
    { header: "Name", key: "files", cell: (r) => r.files.map(f => f.name).join(', ') },
    { header: "Responsible User", key: "who", cell: (r) => r.details?.who || r.user },
    { header: "Activity Type", key: "what", cell: (r) => r.details?.what || "—" },
    { header: "Site", key: "where", cell: (r) => r.details?.where || "—" },
    { header: "Operational Timing", key: "when", cell: (r) => r.details?.when || "—" },
    { header: "Purpose", key: "why", cell: (r) => r.details?.why || "—" },
    { header: "Description", key: "description", cell: (r) => r.details?.description || "—" },
    {
      header: "Action",
      key: "act",
      cell: (r) => {
        const file = r.files[0];
        const documentId = file?.document_id;
        const projectId = project?.project_id || project?.id;
        
        return (
          <div className="flex gap-2">
            {documentId && projectId ? (
              <>
                <Button 
                  variant="secondary" 
                  onClick={async () => {
                    try {
                      const preview = await api.getDocumentPreview(projectId, documentId);
                      setBkPreview({ 
                        name: file.name || "config.txt", 
                        content: preview.preview_data || "(Preview not available)" 
                      });
                    } catch (err) {
                      console.error('Failed to load preview:', err);
                      alert('Failed to load preview');
                    }
                  }}
                >
                  Preview
                </Button>
                <Button 
                  variant="secondary" 
                  onClick={async () => {
                    try {
                      await api.downloadDocument(projectId, documentId);
                    } catch (err) {
                      console.error('Failed to download:', err);
                      alert('Failed to download file');
                    }
                  }}
                >
                  ⬇ Download
                </Button>
              </>
            ) : (
              <span className="text-sm text-gray-400">No file available</span>
            )}
          </div>
        );
      },
    },
  ];

  return (
    <div className="grid gap-6">
      {/* Header + Tabs */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">More Details — {facts.device}</h2>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            From config/show parsing • Mgmt IP: {facts.mgmtIp || "—"}
          </div>
        </div>
        <Button variant="secondary" onClick={goBack}>← Back to Summary</Button>
      </div>

      {loading && (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          Loading device details...
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-rose-300 dark:border-rose-700 bg-rose-50 dark:bg-rose-900/20 p-4 text-sm text-rose-700 dark:text-rose-400">
          Error: {error}
        </div>
      )}

      {!loading && !error && (
        <>
          <div className="flex gap-2 flex-wrap">
            {[
              { id: "overview", label: "Overview" },
              { id: "interfaces", label: "Interfaces" },
              { id: "vlans", label: "VLANs" },
              { id: "stp", label: "STP" },
              { id: "routing", label: "Routing" },
              { id: "neighbors", label: "Neighbors" },
              { id: "macarp", label: "MAC/ARP" },
              { id: "security", label: "Security" },
              { id: "ha", label: "HA" },
              { id: "raw", label: "Raw" }
            ].map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`px-4 py-2 rounded-xl text-sm font-semibold ${
                  tab === t.id
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </>
      )}

      {/* OVERVIEW */}
      {!loading && !error && tab === "overview" && (
        <div className="grid gap-6">
          {/* Device Image Upload */}
          <Card title="Device Image">
            <DeviceImageUpload 
              project={project}
              deviceName={deviceId}
              authedUser={authedUser}
              setProjects={setProjects}
            />
          </Card>
          
          <Card title="Device Facts">
            <div className="grid gap-4 md:grid-cols-3 text-sm">
              <Metric k="Model" v={facts.model || "—"} />
              <Metric k="OS / Version" v={facts.osVersion || "—"} />
              <Metric k="Serial" v={facts.serial || "—"} />
              <Metric k="Mgmt IP" v={facts.mgmtIp || "—"} />
              <Metric k="Role" v={facts.role || "—"} />
              <Metric k="Uptime" v={facts.uptime || "—"} />
              <Metric k="VLAN Count" v={facts.vlanCount ?? "—"} />
              <Metric k="Allowed VLANs (short)" v={facts.allowedVlansShort || "—"} />
              <Metric k="STP Mode" v={facts.stpMode || "—"} />
              <Metric k="STP Root" v={facts.stpRoot || "—"} />
              <Metric k="SVIs" v={facts.sviCount ?? "—"} />
              <Metric k="HSRP Groups" v={facts.hsrpGroups ?? "—"} />
              <Metric k="Routing" v={facts.routing || "—"} />
              <Metric k="OSPF Neighbors" v={facts.ospfNeighbors ?? "—"} />
              <Metric k="BGP ASN" v={facts.bgpAsn ?? "—"} />
              <Metric k="BGP Neighbors" v={facts.bgpNeighbors ?? "—"} />
              <Metric k="CDP / LLDP" v={`${facts.cdpNeighbors ?? "—"} / ${facts.lldpNeighbors ?? "—"}`} />
              <Metric k="NTP" v={facts.ntpStatus || "—"} />
              <Metric k="SNMP" v={facts.snmp || "—"} />
              <Metric k="Syslog" v={facts.syslog || "—"} />
              <Metric k="CPU %" v={facts.cpu != null && facts.cpu !== "—" ? `${facts.cpu}%` : "—"} />
              <Metric k="Memory %" v={facts.mem != null && facts.mem !== "—" ? `${facts.mem}%` : "—"} />
              <Metric k="Hostname" v={overview.hostname || "—"} />
              <Metric k="Management IP" v={overview.management_ip || overview.mgmt_ip || "—"} />
              {overview.device_status && Object.keys(overview.device_status).length > 0 && (
                <>
                  <Metric k="Device Slot" v={overview.device_status.slot || "—"} />
                  <Metric k="Device Type" v={overview.device_status.type || "—"} />
                  <Metric k="Device Status" v={overview.device_status.status || "—"} />
                  <Metric k="Device Role" v={overview.device_status.role || "—"} />
                </>
              )}
              <Metric
                k="Ifaces (T/U/D/A)"
                v={
                  facts.ifaces
                    ? `${facts.ifaces.total} / ${facts.ifaces.up} / ${facts.ifaces.down} / ${facts.ifaces.adminDown}`
                    : "—"
                }
              />
              <Metric k="Ports (Access/Trunk)" v={`${facts.accessCount ?? "—"}/${facts.trunkCount ?? "—"}`} />
            </div>
          </Card>

                {/* AI Summary — per device */}
                {/* AI Summary — per device (ความสัมพันธ์+STP) */}
      <Card
        title="AI Summary (per-device)"
      >
        <div className="rounded-xl border border-gray-200 dark:border-[#1F2937] p-4 bg-gray-50 dark:bg-[#0F172A]">
          <pre className="whitespace-pre-wrap text-[13px] leading-relaxed">{deviceNarrative}</pre>
        </div>
      </Card>

      {/* Recommendations — per device */}
      <Card
        title="Recommendations (per-device)"
      >
        {deviceRecs.length ? (
          <ul className="list-disc pl-5 text-sm space-y-1">
            {deviceRecs.map((r)=>(<li key={r}>{r}</li>))}
          </ul>
        ) : (
          <div className="text-sm text-gray-500 dark:text-gray-400">No recommendations.</div>
        )}
      </Card>


          {/* Drift & Changes (30 days) */}
          <Card title="Drift & Changes (30 days)">
            {loadingBackups ? (
              <div className="text-sm text-gray-400">Loading backup history...</div>
            ) : deviceBackups.length < 2 ? (
              <div className="text-sm text-gray-400">Not enough backups to compare. Upload at least 2 config files for this device.</div>
            ) : (
              <div className="grid gap-3">
                <div className="text-sm">
                  <b>Device:</b> {facts.device} <br />
                  <b>Available backups:</b> {deviceBackups.length} file(s) <br />
                  <b>Latest files:</b>{" "}
                  <span className="text-blue-300">{driftSummary?.from}</span>{" "}
                  <span className="mx-1">→</span>
                  <span className="text-blue-300">{driftSummary?.to}</span>
                </div>
                <div className="text-sm text-gray-400">
                  To view detailed diff, use the "Compare Backups" button below or download files to compare locally.
                </div>
                <div>
                  <Button variant="secondary" onClick={() => setCompareOpen(true)}>Compare Backups</Button>
                </div>
              </div>
            )}
          </Card>

          {/* Backup history */}
          <Card
            title="Backup Config History"
            actions={
              deviceConfigHistory.length >= 2 ? (
                <Button variant="secondary" onClick={() => setCompareOpen(true)}>Compare Backups</Button>
              ) : null
            }
          >
            {loadingBackups ? (
              <div className="text-sm text-gray-400">Loading backup history...</div>
            ) : (
              <>
                <div className="mb-4 grid grid-cols-1 md:grid-cols-3 gap-2">
                  <Input 
                    placeholder="ค้นหา (ชื่อไฟล์, ผู้ใช้, คำอธิบาย...)" 
                    value={searchBackup} 
                    onChange={(e) => setSearchBackup(e.target.value)} 
                  />
                  <Select 
                    value={filterBackupWho} 
                    onChange={setFilterBackupWho} 
                    options={[{value: "all", label: "ทั้งหมด (Responsible User)"}, ...uniqueBackupWhos.map(w => ({value: w, label: w}))]} 
                  />
                  <Select 
                    value={filterBackupWhat} 
                    onChange={setFilterBackupWhat} 
                    options={[{value: "all", label: "ทั้งหมด (Activity Type)"}, ...uniqueBackupWhats.map(w => ({value: w, label: w}))]} 
                  />
                </div>
                <div className="rounded-2xl border border-gray-200 dark:border-[#1F2937]">
                  <Table
                    columns={backupCols}
                    data={filteredBackupHistory}
                    empty="No config uploads for this device"
                    minWidthClass="min-w-[1200px]"
                  />
                </div>
              </>
            )}
          </Card>
        </div>
      )}

      {/* INTERFACES */}
      {!loading && !error && tab === "interfaces" && (
        <Card
          title="Interfaces Explorer"
          actions={<div className="flex items-center gap-2"><Button variant="secondary" onClick={onExportIfaces}>Export CSV</Button></div>}
        >
          <div className="mb-3 grid grid-cols-2 md:grid-cols-5 gap-2">
            <Field label="Mode">
              <Select value={qMode} onChange={setQMode} options={[
                {value:"all",label:"All"},{value:"access",label:"Access"},{value:"trunk",label:"Trunk"}
              ]}/>
            </Field>
            <Field label="State">
              <Select value={qState} onChange={setQState} options={[
                {value:"all",label:"All"},{value:"up",label:"Up"},{value:"down",label:"Down"}
              ]}/>
            </Field>
            <Field label="Access VLAN">
              <Input placeholder="e.g. 20" value={qVlan} onChange={(e)=>setQVlan(e.target.value)} />
            </Field>
            <Field label="Speed">
              <Select value={qSpeed} onChange={setQSpeed} options={[
                {value:"all",label:"All"},{value:"10G",label:"10G"},{value:"1G",label:"1G"},{value:"auto",label:"auto"}
              ]}/>
            </Field>
            <div className="flex items-end">
              <Button variant="secondary" onClick={()=>{setQMode("all");setQState("all");setQVlan("");setQSpeed("all");}}>Clear Filters</Button>
            </div>
          </div>
          <div className="h-[70vh] overflow-auto rounded-2xl border border-gray-200 dark:border-[#1F2937]">
            <Table columns={ifaceColumns} data={filteredIfaces} empty="No interfaces" minWidthClass="min-w-[1400px]" />
          </div>
        </Card>
      )}

      {/* VLANS */}
      {!loading && !error && tab === "vlans" && (
        <Card title={`VLANs (${vlans.length}) — All VLANs from config`} actions={<Button variant="secondary" onClick={exportVlans}>Export CSV</Button>}>
          <div className="h-[70vh] overflow-auto rounded-2xl border border-gray-200 dark:border-[#1F2937]">
            <Table columns={vlanColumns} data={vlans} empty="No VLANs parsed" minWidthClass="min-w-[900px]" />
          </div>
        </Card>
      )}

      {/* STP */}
      {!loading && !error && tab === "stp" && (
        <div className="grid gap-6">
          <Card title="STP Information">
            <div className="grid gap-4 md:grid-cols-3 text-sm mb-6">
              <Metric k="STP Mode" v={stpData.stp_mode || stpData.mode || "—"} />
              <Metric k="Bridge Priority" v={stpData.bridge_priority ?? "—"} />
              <Metric k="Bridge ID" v={stpData.bridge_id || "—"} />
              <Metric k="Root Bridge ID" v={stpData.root_bridge_id || "—"} />
              <Metric k="Root Bridge Status" v={stpData.root_bridge_status !== undefined ? (stpData.root_bridge_status ? "Yes" : "No") : "—"} />
              <Metric k="BPDU Guard" v={stpData.bpdu_guard !== undefined ? (stpData.bpdu_guard ? "Enabled" : "Disabled") : "—"} />
              <Metric k="PortFast Enabled" v={stpData.portfast_enabled !== undefined ? (stpData.portfast_enabled ? "Yes" : "No") : "—"} />
            </div>
            
            {/* STP Interfaces from parser */}
            {stpData.interfaces && Array.isArray(stpData.interfaces) && stpData.interfaces.length > 0 && (
              <div className="mt-4">
                <h3 className="text-sm font-semibold mb-3">STP Port Roles & States (from parser)</h3>
                <div className="h-[60vh] overflow-auto rounded-2xl border border-gray-200 dark:border-[#1F2937]">
                  <Table
                    columns={[
                      { header: "Port", key: "port" },
                      { header: "Role", key: "role", cell: (r) => r.role || "—" },
                      { header: "State", key: "state", cell: (r) => r.state || "—" }
                    ]}
                    data={stpData.interfaces}
                    empty="No STP port information available"
                    minWidthClass="min-w-[600px]"
                  />
                </div>
              </div>
            )}
            
            {/* Fallback: Legacy port_roles format */}
            {(!stpData.interfaces || !Array.isArray(stpData.interfaces) || stpData.interfaces.length === 0) && stpData.port_roles && Object.keys(stpData.port_roles).length > 0 && (
              <div className="mt-4">
                <h3 className="text-sm font-semibold mb-3">Port Roles & States (legacy format)</h3>
                <div className="h-[60vh] overflow-auto rounded-2xl border border-gray-200 dark:border-[#1F2937]">
                  <Table
                    columns={[
                      { header: "Port", key: "port" },
                      { header: "Role", key: "role" },
                      { header: "State", key: "state" },
                      { header: "Cost", key: "cost", cell: (r) => r.cost || "—" },
                      { header: "PortFast", key: "portfast", cell: (r) => r.portfast ? "Enabled" : "Disabled" },
                      { header: "BPDU Guard", key: "bpduguard", cell: (r) => r.bpduguard ? "Enabled" : "Disabled" }
                    ]}
                    data={Object.entries(stpData.port_roles || {}).map(([port, role]) => ({
                      port,
                      role: role || "—",
                      state: stpData.port_states?.[port] || "—",
                      cost: stpData.port_costs?.[port] || null,
                      portfast: stpData.portfast_enabled?.[port] || false,
                      bpduguard: stpData.bpdu_guard_enabled?.[port] || false
                    }))}
                    empty="No STP port information available"
                    minWidthClass="min-w-[800px]"
                  />
                </div>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* ROUTING */}
      {!loading && !error && tab === "routing" && (
        <div className="grid gap-6">
          {/* Static Routes */}
          {routingData.static && ((Array.isArray(routingData.static) && routingData.static.length > 0) || (routingData.static.routes && routingData.static.routes.length > 0)) && (
            <Card title="Static Routes">
              <div className="h-[50vh] overflow-auto rounded-2xl border border-gray-200 dark:border-[#1F2937]">
                <Table
                  columns={[
                    { header: "Network", key: "network" },
                    { header: "Mask", key: "mask", cell: (r) => r.mask || "—" },
                    { header: "Next Hop", key: "nexthop", cell: (r) => r.nexthop || r.next_hop || "—" },
                    { header: "Interface", key: "interface", cell: (r) => r.interface || r.exit_interface || "—" },
                    { header: "AD", key: "admin_distance", cell: (r) => r.admin_distance || "—" }
                  ]}
                  data={Array.isArray(routingData.static) ? routingData.static : (routingData.static.routes || [])}
                  empty="No static routes"
                  minWidthClass="min-w-[900px]"
                />
              </div>
            </Card>
          )}

          {/* OSPF */}
          {routingData.ospf && (
            <Card title="OSPF">
              <div className="grid gap-4 md:grid-cols-3 text-sm mb-4">
                <Metric k="Router ID" v={routingData.ospf.router_id || "—"} />
                <Metric k="Process ID" v={routingData.ospf.process_id || "—"} />
                <Metric k="Areas" v={(Array.isArray(routingData.ospf.areas) ? routingData.ospf.areas.join(", ") : null) || "—"} />
              </div>
              {routingData.ospf.interfaces && routingData.ospf.interfaces.length > 0 && (
                <div className="mb-4">
                  <h3 className="text-sm font-semibold mb-2">OSPF Interfaces</h3>
                  <div className="h-[30vh] overflow-auto rounded-xl border border-gray-200 dark:border-[#1F2937]">
                    <Table
                      columns={[
                        { header: "Interface", key: "interface" },
                        { header: "Area", key: "area" },
                        { header: "Cost", key: "cost", cell: (r) => r.cost || "—" }
                      ]}
                      data={routingData.ospf.interfaces}
                      empty="No OSPF interfaces"
                      minWidthClass="min-w-[600px]"
                    />
                  </div>
                </div>
              )}
              {routingData.ospf.neighbors && routingData.ospf.neighbors.length > 0 && (
                <div className="mb-4">
                  <h3 className="text-sm font-semibold mb-2">OSPF Neighbors</h3>
                  <div className="h-[30vh] overflow-auto rounded-xl border border-gray-200 dark:border-[#1F2937]">
                    <Table
                      columns={[
                        { header: "Neighbor ID", key: "neighbor_id" },
                        { header: "Interface", key: "interface" },
                        { header: "State", key: "state" },
                        { header: "DR", key: "dr", cell: (r) => r.dr || "—" },
                        { header: "BDR", key: "bdr", cell: (r) => r.bdr || "—" }
                      ]}
                      data={routingData.ospf.neighbors}
                      empty="No OSPF neighbors"
                      minWidthClass="min-w-[800px]"
                    />
                  </div>
                </div>
              )}
            </Card>
          )}

          {/* EIGRP */}
          {routingData.eigrp && (
            <Card title="EIGRP">
              <div className="grid gap-4 md:grid-cols-3 text-sm mb-4">
                <Metric k="AS Number" v={routingData.eigrp.as_number || "—"} />
                <Metric k="Router ID" v={routingData.eigrp.router_id || "—"} />
                <Metric k="Neighbors" v={routingData.eigrp.neighbors?.length || 0} />
              </div>
              {routingData.eigrp.neighbors && routingData.eigrp.neighbors.length > 0 && (
                <div className="mb-4">
                  <h3 className="text-sm font-semibold mb-2">EIGRP Neighbors</h3>
                  <div className="h-[30vh] overflow-auto rounded-xl border border-gray-200 dark:border-[#1F2937]">
                    <Table
                      columns={[
                        { header: "Neighbor", key: "neighbor" },
                        { header: "Interface", key: "interface" },
                        { header: "Hold Time", key: "hold_time", cell: (r) => r.hold_time || "—" }
                      ]}
                      data={routingData.eigrp.neighbors}
                      empty="No EIGRP neighbors"
                      minWidthClass="min-w-[600px]"
                    />
                  </div>
                </div>
              )}
            </Card>
          )}

          {/* BGP */}
          {routingData.bgp && (
            <Card title="BGP">
              <div className="grid gap-4 md:grid-cols-3 text-sm mb-4">
                <Metric k="AS Number" v={routingData.bgp.as_number ?? routingData.bgp.local_as ?? "—"} />
                <Metric k="Router ID" v={routingData.bgp.router_id || "—"} />
                <Metric k="Peers" v={routingData.bgp.peers?.length || 0} />
                <Metric k="Received Prefixes" v={routingData.bgp.received_prefixes || 0} />
                <Metric k="Advertised Prefixes" v={routingData.bgp.advertised_prefixes || 0} />
              </div>
              {routingData.bgp.peers && routingData.bgp.peers.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold mb-2">BGP Peers</h3>
                  <div className="h-[40vh] overflow-auto rounded-xl border border-gray-200 dark:border-[#1F2937]">
                    <Table
                      columns={[
                        { header: "Peer IP", key: "peer", cell: (r) => r.peer || r.peer_ip || "—" },
                        { header: "Remote AS", key: "remote_as" },
                        { header: "State", key: "state", cell: (r) => r.state || "—" },
                        { header: "Received", key: "received_prefixes", cell: (r) => r.received_prefixes || 0 },
                        { header: "Advertised", key: "advertised_prefixes", cell: (r) => r.advertised_prefixes || 0 }
                      ]}
                      data={routingData.bgp.peers}
                      empty="No BGP peers"
                      minWidthClass="min-w-[900px]"
                    />
                  </div>
                </div>
              )}
            </Card>
          )}

          {/* RIP */}
          {routingData.rip && (
            <Card title="RIP">
              <div className="grid gap-4 md:grid-cols-3 text-sm">
                <Metric k="Version" v={routingData.rip.version || "—"} />
                <Metric k="Networks" v={(Array.isArray(routingData.rip.networks) ? routingData.rip.networks.join(", ") : null) || "—"} />
                <Metric k="Interfaces" v={(Array.isArray(routingData.rip.interfaces) ? routingData.rip.interfaces.join(", ") : null) || "—"} />
              </div>
            </Card>
          )}

          {(!routingData.static || ((!Array.isArray(routingData.static) || routingData.static.length === 0) && (!routingData.static.routes || routingData.static.routes.length === 0))) && !routingData.ospf && !routingData.eigrp && !routingData.bgp && !routingData.rip && (
            <Card title="Routing">
              <div className="text-sm text-gray-500 dark:text-gray-400">No routing protocol information available</div>
            </Card>
          )}
        </div>
      )}

      {/* NEIGHBORS */}
      {!loading && !error && tab === "neighbors" && (
        <div className="grid gap-6">
          <Card title={`Neighbors (${neighborsData.length})`}>
            {neighborsData.length > 0 ? (
              <div className="h-[70vh] overflow-auto rounded-2xl border border-gray-200 dark:border-[#1F2937]">
                <Table
                  columns={[
                    { header: "Device Name", key: "device_name" },
                    { header: "IP Address", key: "ip_address", cell: (r) => r.ip_address || "—" },
                    { header: "Platform/Model", key: "platform", cell: (r) => r.platform || r.model || "—" },
                    { header: "Local Port", key: "local_port" },
                    { header: "Remote Port", key: "remote_port", cell: (r) => r.remote_port || "—" },
                    { header: "Capabilities", key: "capabilities", cell: (r) => (Array.isArray(r.capabilities) ? r.capabilities.join(", ") : (r.capabilities || "—")) },
                    { header: "Protocol", key: "protocol" }
                  ]}
                  data={neighborsData.filter(n => {
                    // Additional client-side filtering to remove invalid entries
                    const deviceName = (n.device_name || "").toLowerCase();
                    const invalidNames = ['device', 'router', 'switch', 'wlan', 'other', 'id', 'port', 'local', 'remote', 'neighbor', 'intf', 'dev', 'exptime', '(r)', '(w)', '(o)'];
                    return deviceName && deviceName.length > 1 && !invalidNames.includes(deviceName);
                  })}
                  empty="No neighbor information available"
                  minWidthClass="min-w-[1200px]"
                />
              </div>
            ) : (
              <div className="text-sm text-gray-500 dark:text-gray-400">
                No neighbor information available. This may be because:
                <ul className="list-disc list-inside mt-2 ml-4">
                  <li>The configuration file does not contain LLDP/CDP neighbor information</li>
                  <li>The neighbor discovery protocol is not enabled on the device</li>
                  <li>Please ensure the uploaded file includes "display lldp neighbor" or "show cdp neighbors" output</li>
                </ul>
                {deviceData && (
                  <div className="mt-4 p-3 bg-gray-100 dark:bg-gray-800 rounded-lg">
                    <div className="text-xs font-mono text-gray-600 dark:text-gray-400">
                      Debug: neighborsData = {JSON.stringify(neighborsData, null, 2)}
                    </div>
                  </div>
                )}
              </div>
            )}
          </Card>
        </div>
      )}

      {/* MAC/ARP */}
      {!loading && !error && tab === "macarp" && (
        <div className="grid gap-6">
          {/* MAC Address Table */}
          <Card title="MAC Address Table">
            {macArpData.mac_table && macArpData.mac_table.length > 0 ? (
              <div className="h-[50vh] overflow-auto rounded-2xl border border-gray-200 dark:border-[#1F2937]">
                <Table
                  columns={[
                    { header: "MAC Address", key: "mac_address" },
                    { header: "Port", key: "port" },
                    { header: "Type", key: "type", cell: (r) => r.type || "Dynamic" },
                    { header: "VLAN", key: "vlan", cell: (r) => r.vlan || "—" }
                  ]}
                  data={macArpData.mac_table}
                  empty="No MAC address table entries"
                  minWidthClass="min-w-[800px]"
                />
              </div>
            ) : (
              <div className="text-sm text-gray-500 dark:text-gray-400">No MAC address table available</div>
            )}
          </Card>

          {/* ARP Table */}
          <Card title="ARP Table">
            {macArpData.arp_table && macArpData.arp_table.length > 0 ? (
              <div className="h-[50vh] overflow-auto rounded-2xl border border-gray-200 dark:border-[#1F2937]">
                <Table
                  columns={[
                    { header: "IP Address", key: "ip_address" },
                    { header: "MAC Address", key: "mac_address" },
                    { header: "Interface", key: "interface" },
                    { header: "Age", key: "age", cell: (r) => r.age || "—" }
                  ]}
                  data={macArpData.arp_table}
                  empty="No ARP table entries"
                  minWidthClass="min-w-[800px]"
                />
              </div>
            ) : (
              <div className="text-sm text-gray-500 dark:text-gray-400">No ARP table available</div>
            )}
          </Card>
        </div>
      )}

      {/* SECURITY */}
      {!loading && !error && tab === "security" && (
        <div className="grid gap-6">
          {/* User Accounts */}
          {(securityData.user_accounts && securityData.user_accounts.length > 0) || (securityData.users && securityData.users.length > 0) && (
            <Card title="User Accounts & Privilege Levels">
              <div className="h-[40vh] overflow-auto rounded-xl border border-gray-200 dark:border-[#1F2937]">
                <Table
                  columns={[
                    { header: "Username", key: "username" },
                    { header: "Privilege Level", key: "privilege_level", cell: (r) => r.privilege_level ?? "—" },
                    { header: "Role", key: "role", cell: (r) => r.role || "—" }
                  ]}
                  data={securityData.user_accounts || securityData.users || []}
                  empty="No user accounts"
                  minWidthClass="min-w-[600px]"
                />
              </div>
            </Card>
          )}

          {/* AAA */}
          {securityData.aaa && (
            <Card title="AAA Configuration">
              <div className="grid gap-4 md:grid-cols-2 text-sm">
                <Metric k="Authentication" v={securityData.aaa.authentication || "—"} />
                <Metric k="Authorization" v={securityData.aaa.authorization || "—"} />
                <Metric k="Accounting" v={securityData.aaa.accounting || "—"} />
              </div>
            </Card>
          )}

          {/* SSH */}
          {securityData.ssh && (
            <Card title="SSH">
              <div className="grid gap-4 md:grid-cols-2 text-sm">
                <Metric k="Version" v={securityData.ssh.version || "—"} />
                <Metric k="Status" v={securityData.ssh.enabled ? "Enabled" : "Disabled"} />
                <Metric k="Connection Timeout" v={securityData.ssh.connection_timeout ? `${securityData.ssh.connection_timeout}s` : "—"} />
                <Metric k="Auth Retries" v={securityData.ssh.auth_retries || "—"} />
                <Metric k="Stelnet" v={securityData.ssh.stelnet_enabled ? "Enabled" : "Disabled"} />
                <Metric k="SFTP" v={securityData.ssh.sftp_enabled ? "Enabled" : "Disabled"} />
                <Metric k="SCP" v={securityData.ssh.scp_enabled ? "Enabled" : "Disabled"} />
              </div>
            </Card>
          )}

          {/* SNMP */}
          {securityData.snmp && (
            <Card title="SNMP">
              <div className="grid gap-4 md:grid-cols-2 text-sm">
                <Metric k="Status" v={securityData.snmp.enabled ? "Enabled" : "Disabled"} />
                <Metric k="Version" v={securityData.snmp.version || "—"} />
                {securityData.snmp.communities && securityData.snmp.communities.length > 0 && (
                  <div className="col-span-2">
                    <h4 className="text-sm font-semibold mb-2">Communities</h4>
                    <div className="h-[20vh] overflow-auto rounded-xl border border-gray-200 dark:border-[#1F2937]">
                      <Table
                        columns={[
                          { header: "Name", key: "name" },
                          { header: "Group", key: "group", cell: (r) => r.group || "—" },
                          { header: "Access", key: "access", cell: (r) => r.access || "—" },
                          { header: "Storage Type", key: "storage_type", cell: (r) => r.storage_type || "—" },
                        ]}
                        data={securityData.snmp.communities}
                        empty="No SNMP communities"
                        minWidthClass="min-w-[600px]"
                      />
                    </div>
                  </div>
                )}
              </div>
            </Card>
          )}

          {/* NTP */}
          {securityData.ntp && (
            <Card title="NTP">
              <div className="grid gap-4 md:grid-cols-2 text-sm">
                <Metric k="Status" v={securityData.ntp.status || "—"} />
                <Metric k="Enabled" v={securityData.ntp.enabled ? "Yes" : "No"} />
                <Metric k="Synchronized" v={securityData.ntp.synchronized ? "Yes" : "No"} />
                <Metric k="Stratum" v={securityData.ntp.stratum || "—"} />
                <Metric k="Servers" v={securityData.ntp.servers?.join(", ") || "—"} />
              </div>
            </Card>
          )}

          {/* Syslog / Info Center */}
          {(securityData.logging || securityData.syslog) && (
            <Card title="Syslog / Info Center / Logging">
              <div className="grid gap-4 md:grid-cols-2 text-sm">
                <Metric k="Enabled" v={(securityData.logging?.enabled || securityData.syslog?.enabled) ? "Yes" : "No"} />
                <Metric k="Log Hosts" v={securityData.logging?.log_hosts?.join(", ") || securityData.syslog?.servers?.join(", ") || "—"} />
                {securityData.logging?.log_buffer && (
                  <>
                    <Metric k="Log Buffer Max" v={securityData.logging.log_buffer.max_size ? `${securityData.logging.log_buffer.max_size} bytes` : "—"} />
                    <Metric k="Log Buffer Current" v={securityData.logging.log_buffer.current_size ? `${securityData.logging.log_buffer.current_size} bytes` : "—"} />
                  </>
                )}
                {securityData.logging?.trap_buffer && (
                  <>
                    <Metric k="Trap Buffer Max" v={securityData.logging.trap_buffer.max_size ? `${securityData.logging.trap_buffer.max_size} bytes` : "—"} />
                    <Metric k="Trap Buffer Current" v={securityData.logging.trap_buffer.current_size ? `${securityData.logging.trap_buffer.current_size} bytes` : "—"} />
                  </>
                )}
              </div>
            </Card>
          )}

          {/* ACLs */}
          {(securityData.acls && Array.isArray(securityData.acls) && securityData.acls.length > 0) && (
            <Card title="Access Control Lists (ACLs)">
              <div className="grid gap-4">
                {securityData.acls.map((acl, idx) => (
                  <Card key={idx} title={`ACL ${acl.acl_number || acl.name || `#${idx + 1}`}`} className="border border-gray-200 dark:border-gray-700">
                    {acl.rules && Array.isArray(acl.rules) && acl.rules.length > 0 ? (
                      <div className="h-[40vh] overflow-auto rounded-xl border border-gray-200 dark:border-[#1F2937]">
                        <Table
                          columns={[
                            { header: "Rule ID", key: "id" },
                            { header: "Action", key: "action", cell: (r) => r.action?.toUpperCase() || "—" },
                            { header: "Protocol", key: "protocol", cell: (r) => r.protocol || "—" },
                            { header: "Source", key: "source", cell: (r) => r.source || r.source_ip || "—" },
                            { header: "Source Mask", key: "source_mask", cell: (r) => r.source_mask || "—" },
                            { header: "Destination", key: "destination", cell: (r) => r.destination || r.destination_ip || "—" },
                            { header: "Destination Mask", key: "destination_mask", cell: (r) => r.destination_mask || "—" }
                          ]}
                          data={acl.rules}
                          empty="No rules in this ACL"
                          minWidthClass="min-w-[1200px]"
                        />
                      </div>
                    ) : (
                      <div className="text-sm text-gray-500 dark:text-gray-400">No rules defined for this ACL</div>
                    )}
                  </Card>
                ))}
              </div>
            </Card>
          )}

          {(!securityData.user_accounts || securityData.user_accounts.length === 0) && (!securityData.users || securityData.users.length === 0) && !securityData.aaa && !securityData.ssh && !securityData.snmp && !securityData.ntp && !securityData.syslog && (!securityData.acls || securityData.acls.length === 0) && (
            <Card title="Security">
              <div className="text-sm text-gray-500 dark:text-gray-400">No security information available</div>
            </Card>
          )}
        </div>
      )}

      {/* HA */}
      {!loading && !error && tab === "ha" && (
        <div className="grid gap-6">
          {/* EtherChannel / Port-Channel */}
          {haData.etherchannel && haData.etherchannel.length > 0 && (
            <Card title="EtherChannel / Port-Channel">
              <div className="h-[50vh] overflow-auto rounded-2xl border border-gray-200 dark:border-[#1F2937]">
                <Table
                  columns={[
                    { header: "Port-Channel", key: "name" },
                    { header: "Mode", key: "mode" },
                    { header: "Member Interfaces", key: "members", cell: (r) => r.members?.join(", ") || "—" },
                    { header: "Status", key: "status" }
                  ]}
                  data={haData.etherchannel}
                  empty="No Port-Channel information"
                  minWidthClass="min-w-[900px]"
                />
              </div>
            </Card>
          )}

          {/* HSRP */}
          {haData.hsrp && haData.hsrp.groups && haData.hsrp.groups.length > 0 && (
            <Card title="HSRP (Hot Standby Router Protocol)">
              <div className="h-[50vh] overflow-auto rounded-2xl border border-gray-200 dark:border-[#1F2937]">
                <Table
                  columns={[
                    { header: "Group", key: "group_id" },
                    { header: "Virtual IP", key: "virtual_ip" },
                    { header: "Status", key: "status" },
                    { header: "Priority", key: "priority", cell: (r) => r.priority || "—" },
                    { header: "Preempt", key: "preempt", cell: (r) => r.preempt ? "Yes" : "No" },
                    { header: "VLAN", key: "vlan_id", cell: (r) => r.vlan_id || "—" }
                  ]}
                  data={haData.hsrp.groups}
                  empty="No HSRP groups"
                  minWidthClass="min-w-[900px]"
                />
              </div>
            </Card>
          )}

          {/* VRRP */}
          {haData.vrrp && ((Array.isArray(haData.vrrp) && haData.vrrp.length > 0) || (haData.vrrp.groups && haData.vrrp.groups.length > 0)) && (
            <Card title="VRRP (Virtual Router Redundancy Protocol)">
              <div className="h-[50vh] overflow-auto rounded-2xl border border-gray-200 dark:border-[#1F2937]">
                <Table
                  columns={[
                    { header: "VRID", key: "vrid" },
                    { header: "Interface", key: "interface", cell: (r) => r.interface || "—" },
                    { header: "Virtual IP", key: "virtual_ip" },
                    { header: "State", key: "state", cell: (r) => r.state || r.status || "—" },
                    { header: "Master IP", key: "master_ip", cell: (r) => r.master_ip || "—" },
                    { header: "Priority", key: "priority", cell: (r) => r.priority ?? r.priority_run ?? "—" },
                    { header: "Preempt", key: "preempt", cell: (r) => r.preempt !== undefined ? (r.preempt ? "Yes" : "No") : "—" }
                  ]}
                  data={Array.isArray(haData.vrrp) ? haData.vrrp : (haData.vrrp.groups || [])}
                  empty="No VRRP groups"
                  minWidthClass="min-w-[1000px]"
                />
              </div>
            </Card>
          )}

          {(!haData.etherchannel || haData.etherchannel.length === 0) && (!haData.hsrp || !haData.hsrp.groups || haData.hsrp.groups.length === 0) && (!haData.vrrp || ((!Array.isArray(haData.vrrp) || haData.vrrp.length === 0) && (!haData.vrrp.groups || haData.vrrp.groups.length === 0))) && (
            <Card title="High Availability">
              <div className="text-sm text-gray-500 dark:text-gray-400">No HA information available</div>
            </Card>
          )}
        </div>
      )}

      {/* RAW */}
      {!loading && !error && tab === "raw" && (
        <div className="grid gap-6">
          {/* Tabs for Raw view */}
          <div className="flex gap-2 flex-wrap">
            {[
              { id: "parsed", label: "Parsed Data (JSON)" },
              { id: "original", label: "Original File Content" }
            ].map((t) => (
              <button
                key={t.id}
                onClick={() => setRawSubTab(t.id)}
                className={`px-4 py-2 rounded-xl text-sm font-semibold ${
                  rawSubTab === t.id
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* Parsed Data (JSON) */}
          {rawSubTab === "parsed" && (
            <Card 
              title="Parsed Data from Database (JSON Structure)"
              actions={
                <button
                  onClick={() => {
                    // Create download link for JSON
                    if (!deviceData) {
                      alert('No data available to download');
                      return;
                    }
                    const jsonContent = JSON.stringify(deviceData, null, 2);
                    const blob = new Blob([jsonContent], { type: 'application/json' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    const deviceName = deviceData.device_name || deviceId || 'config';
                    a.download = `${deviceName}_parsed.json`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                  }}
                  disabled={!deviceData}
                  className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-xl bg-blue-600 text-white hover:bg-blue-700 transition focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Download as JSON file"
                >
                  <span>⬇</span>
                  <span>Download JSON</span>
                </button>
              }
            >
              <div className="rounded-xl border border-gray-200 dark:border-[#1F2937] p-3 bg-gray-50 dark:bg-[#0F172A] text-sm overflow-auto max-h-[70vh]">
                {deviceData ? (
                  <pre className="whitespace-pre-wrap">{JSON.stringify(deviceData, null, 2)}</pre>
                ) : (
                  <div className="text-sm text-gray-500 dark:text-gray-400">No parsed data available</div>
                )}
              </div>
            </Card>
          )}

          {/* Original File Content */}
          {rawSubTab === "original" && (
            <Card 
              title="Original File Content"
              actions={
                <button
                  onClick={() => {
                    // Create download link
                    const content = deviceData?.original_content || '';
                    if (!content) {
                      alert('No content available to download');
                      return;
                    }
                    const blob = new Blob([content], { type: 'text/plain' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    const deviceName = deviceData?.device_name || deviceId || 'config';
                    a.download = `${deviceName}_original.txt`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                  }}
                  disabled={!deviceData?.original_content}
                  className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-xl bg-blue-600 text-white hover:bg-blue-700 transition focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Download as TXT file"
                >
                  <span>⬇</span>
                  <span>Download TXT</span>
                </button>
              }
            >
              <div className="rounded-xl border border-gray-200 dark:border-[#1F2937] p-3 bg-gray-50 dark:bg-[#0F172A] text-sm overflow-auto max-h-[70vh]">
                {deviceData?.original_content ? (
                  <pre className="whitespace-pre-wrap">{deviceData.original_content}</pre>
                ) : (
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    Original file content not available. This may be because:
                    <ul className="list-disc list-inside mt-2 ml-4">
                      <li>The file was not uploaded with the configuration</li>
                      <li>The original content was not stored in the database</li>
                      <li>Please re-upload the configuration file</li>
                    </ul>
                  </div>
                )}
              </div>
            </Card>
          )}
        </div>
      )}

      {/* Modal: Compare Backups */}
      {compareOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/50" onClick={()=>setCompareOpen(false)} />
          <div className="relative z-10 w-full max-w-5xl">
            <Card
              title={`Compare Backups — ${facts.device}`}
              actions={<Button variant="secondary" onClick={()=>setCompareOpen(false)}>Close</Button>}
            >
              <div className="grid gap-3">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <Field label="Left (older)">
                    <Select
                      value={leftFileName}
                      onChange={setLeftFileName}
                      options={deviceBackups.map(f=>({value:f.name,label:f.name}))}
                    />
                  </Field>
                  <Field label="Right (newer)">
                    <Select
                      value={rightFileName}
                      onChange={setRightFileName}
                      options={deviceBackups.map(f=>({value:f.name,label:f.name}))}
                    />
                  </Field>
                </div>

                <div className="rounded-xl border border-gray-200 dark:border-[#1F2937] overflow-hidden">
                  <div className="grid grid-cols-1 md:grid-cols-2">
                    <div className="border-b md:border-b-0 md:border-r border-[#1F2937] p-3">
                      <div className="text-xs text-gray-400 mb-2 truncate">{leftFile?.name || "—"}</div>
                      <div className="text-xs text-gray-400 mb-2">vs</div>
                      <div className="text-xs text-gray-400 mb-2 truncate">{rightFile?.name || "—"}</div>
                    </div>
                    <div className="p-3">
                      <div className="text-xs text-gray-400 mb-2">Diff (line by line)</div>
                      <div className="bg-[#0D1422] rounded-lg p-3 h-[60vh] overflow-auto text-sm">
                        {leftFile && rightFile ? (
                          simpleDiff(leftFile.content || "", rightFile.content || "").map((d,i)=>(
                            <div key={i} className={
                              d.t === "+" ? "text-emerald-400" :
                              d.t === "-" ? "text-rose-400" : "text-gray-300"
                            }>
                              {d.t} {d.l}
                            </div>
                          ))
                        ) : (
                          <div className="text-gray-400">Select both files to compare.</div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                {rightFile && (
                  <div className="flex gap-2">
                    {/* Download buttons removed - only available in Documents page */}
                  </div>
                )}
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* Modal preview (จากตาราง) */}
      {bkPreview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/50" onClick={() => setBkPreview(null)} />
          <div className="relative z-10 w-full max-w-3xl">
            <Card
              title={`Preview — ${bkPreview.name}`}
              actions={
                <div className="flex gap-2">
                  <Button variant="secondary" onClick={() => setBkPreview(null)}>Close</Button>
                </div>
              }
            >
              <div className="rounded-xl border border-gray-200 dark:border-[#1F2937] p-3 bg-gray-50 dark:bg-[#0F172A] text-sm overflow-auto max-h-[70vh]">
                <pre className="whitespace-pre-wrap text-[13px] leading-relaxed">{bkPreview.content}</pre>
              </div>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
};






const Metric = ({ k, v }) => (
  <div className="rounded-xl border border-gray-200 dark:border-[#1F2937] bg-white dark:bg-[#0F172A] p-3">
    <div className="text-xs text-gray-500 dark:text-gray-400">{k}</div>
    <div className="mt-1 font-semibold">{v}</div>
  </div>
);

/* ========= UPLOAD FORMS ========= */
const UploadConfigForm = ({ project, authedUser, onClose, onUpload }) => {
  const [files, setFiles] = useState([]);
  const [details, setDetails] = useState({
    who: authedUser?.username || '',
    what: '',
    where: '',
    when: '',
    why: '',
    description: ''
  });
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [projectOptions, setProjectOptions] = useState({ what: [], where: [], when: [], why: [] });
  
  // Load project-specific options
  useEffect(() => {
    const loadProjectOptions = async () => {
      if (!project?.project_id && !project?.id) return;
      try {
        const projectId = project.project_id || project.id;
        const options = await api.getProjectOptions(projectId);
        setProjectOptions(options || { what: [], where: [], when: [], why: [] });
      } catch (error) {
        console.error('Failed to load project options:', error);
      }
    };
    loadProjectOptions();
  }, [project]);

  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files || []);
    setFiles(prev => [...prev, ...selectedFiles]);
    setError(null);
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFiles = Array.from(e.dataTransfer.files);
      setFiles(prev => [...prev, ...droppedFiles]);
      setError(null);
    }
  };

  const removeFile = (index) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (files.length === 0) return;
    
    setIsUploading(true);
    setError(null);
    
    try {
      // Upload config files - always to Config folder
      const metadata = {
        who: details.who,
        what: details.what,
        where: details.where || null,
        when: details.when || null,
        why: details.why || null,
        description: details.description || null
      };
      
      const projectId = project.project_id || project.id;
      const result = await api.uploadDocuments(projectId, files, metadata, "Config"); // Force Config folder
      
      // Upload successful - close modal and refresh
      // Create upload record for UI consistency
      const uploadRecord = createUploadRecord('config', files, authedUser.username, projectId, {
        ...details,
        folderId: "Config"
      });
      
      onUpload(uploadRecord, "Config");
      onClose(); // Close modal after successful upload
    } catch (error) {
      console.error('Upload failed:', error);
      // Handle error message properly
      let errorMessage = 'Upload failed. Please try again.';
      if (error instanceof Error) {
        errorMessage = error.message;
      } else if (typeof error === 'string') {
        errorMessage = error;
      } else if (error && error.message) {
        errorMessage = error.message;
      } else if (error && error.detail) {
        errorMessage = error.detail;
      }
      setError(errorMessage);
      // Don't close modal on error - let user see the error and retry
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 overflow-y-auto">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative z-10 w-full max-w-5xl max-h-[90vh] my-4">
        <Card title="Upload Configuration Files" actions={<Button variant="secondary" onClick={onClose}>Close</Button>}>
          <div className="max-h-[calc(90vh-120px)] overflow-y-auto pr-2">
            <form onSubmit={handleSubmit} className="grid gap-3">
            {error && (
              <div className="rounded-xl border border-rose-300 dark:border-rose-700 bg-rose-50 dark:bg-rose-900/20 p-3 text-sm text-rose-700 dark:text-rose-400">
                {error}
                </div>
              )}

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              <Field label="Responsible User">
                <Input
                  value={details.who}
                  disabled
                  className="bg-gray-100 dark:bg-gray-700"
                />
              </Field>
              <Field label="Activity Type">
                <SelectWithOther
                  value={details.what}
                  onChange={async (value) => {
                    setDetails({...details, what: value});
                    // Save custom option to project
                    if (value && !projectOptions.what.includes(value)) {
                      try {
                        const projectId = project.project_id || project.id;
                        await api.saveProjectOption(projectId, 'what', value);
                        setProjectOptions(prev => ({ ...prev, what: [...prev.what, value] }));
                      } catch (error) {
                        console.error('Failed to save option:', error);
                      }
                    }
                  }}
                  options={projectOptions.what.map(v => ({ value: v, label: v }))}
                  placeholder="Type custom value..."
                />
              </Field>
              <Field label="Site">
                <SelectWithOther
                  value={details.where}
                  onChange={async (value) => {
                    setDetails({...details, where: value});
                    // Save custom option to project
                    if (value && !projectOptions.where.includes(value)) {
                      try {
                        const projectId = project.project_id || project.id;
                        await api.saveProjectOption(projectId, 'where', value);
                        setProjectOptions(prev => ({ ...prev, where: [...prev.where, value] }));
                      } catch (error) {
                        console.error('Failed to save option:', error);
                      }
                    }
                  }}
                  options={projectOptions.where.map(v => ({ value: v, label: v }))}
                  placeholder="Type custom value..."
                />
              </Field>
              <Field label="Operational Timing">
                <SelectWithOther
                  value={details.when}
                  onChange={async (value) => {
                    setDetails({...details, when: value});
                    // Save custom option to project
                    if (value && !projectOptions.when.includes(value)) {
                      try {
                        const projectId = project.project_id || project.id;
                        await api.saveProjectOption(projectId, 'when', value);
                        setProjectOptions(prev => ({ ...prev, when: [...prev.when, value] }));
                      } catch (error) {
                        console.error('Failed to save option:', error);
                      }
                    }
                  }}
                  options={projectOptions.when.map(v => ({ value: v, label: v }))}
                  placeholder="Type custom value..."
                />
              </Field>
            <Field label="Purpose">
              <SelectWithOther
                value={details.why}
                  onChange={async (value) => {
                    setDetails({...details, why: value});
                    // Save custom option to project
                    if (value && !projectOptions.why.includes(value)) {
                      try {
                        const projectId = project.project_id || project.id;
                        await api.saveProjectOption(projectId, 'why', value);
                        setProjectOptions(prev => ({ ...prev, why: [...prev.why, value] }));
                      } catch (error) {
                        console.error('Failed to save option:', error);
                      }
                    }
                  }}
                  options={projectOptions.why.map(v => ({ value: v, label: v }))}
                  placeholder="Type custom value..."
              />
            </Field>
            </div>

            <Field label="Description">
              <textarea
                value={details.description}
                onChange={(e) => setDetails({...details, description: e.target.value})}
                placeholder="Describe the purpose of this upload..."
                className="w-full rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm min-h-[60px]"
              />
            </Field>

            {/* File Upload Section - Moved to bottom */}
            <Field label="Select Configuration Files">
              <div
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-xl p-6 text-center transition-colors ${
                  dragActive
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                    : 'border-gray-300 dark:border-gray-700 hover:border-gray-400 dark:hover:border-gray-600'
                }`}
              >
                <input
                  type="file"
                  multiple
                  accept=".txt,.cfg,.conf,.log"
                  onChange={handleFileChange}
                  className="hidden"
                  id="file-upload-input-config"
                />
                <label
                  htmlFor="file-upload-input-config"
                  className="cursor-pointer block"
                >
                  <div className="text-4xl mb-2">📁</div>
                  <div className="text-sm font-medium mb-1">
                    Drag & drop files here, or click to select
                  </div>
                  <div className="text-xs text-gray-500">
                    You can select multiple files (.txt, .cfg, .conf)
                  </div>
                </label>
              </div>
              
              {files.length > 0 && (
                <div className="mt-4">
                  <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Selected {files.length} file(s):
                  </div>
                  <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-2 max-h-48 overflow-y-auto">
                    <div className="space-y-2">
                      {files.map((file, idx) => (
                        <div key={idx} className="flex items-center justify-between rounded-lg border border-gray-200 dark:border-gray-700 p-2 text-sm bg-gray-50 dark:bg-gray-800/50">
                          <div className="flex-1 min-w-0">
                            <div className="font-medium truncate">{file.name}</div>
                            <div className="text-xs text-gray-500">{(file.size / 1024).toFixed(1)} KB</div>
                          </div>
                          <button
                            type="button"
                            onClick={() => removeFile(idx)}
                            className="ml-2 text-rose-500 hover:text-rose-700 text-sm flex-shrink-0"
                          >
                            ✕
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </Field>

            <div className="flex gap-2 justify-end sticky bottom-0 bg-white dark:bg-gray-900 pt-3 pb-1 border-t border-gray-200 dark:border-gray-700 mt-2">
              <Button variant="secondary" onClick={onClose}>Cancel</Button>
              <Button type="submit" disabled={files.length === 0 || isUploading}>
                {isUploading ? 'Uploading...' : 'Upload Files'}
              </Button>
            </div>
          </form>
          </div>
        </Card>
      </div>
    </div>
  );
};

const UploadDocumentForm = ({ project, authedUser, onClose, onUpload, folderStructure, defaultFolderId = null }) => {
  const [files, setFiles] = useState([]);
  const [selectedFolderId, setSelectedFolderId] = useState(defaultFolderId || '');
  const [details, setDetails] = useState({
    who: authedUser?.username || '',
    what: '',
    where: '',
    when: '',
    why: '',
    description: ''
  });
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [projectOptions, setProjectOptions] = useState({ what: [], where: [], when: [], why: [] });
  
  // Load project-specific options
  useEffect(() => {
    const loadProjectOptions = async () => {
      if (!project?.project_id && !project?.id) return;
      try {
        const projectId = project.project_id || project.id;
        const options = await api.getProjectOptions(projectId);
        setProjectOptions(options || { what: [], where: [], when: [], why: [] });
      } catch (error) {
        console.error('Failed to load project options:', error);
      }
    };
    loadProjectOptions();
  }, [project]);
  
  // Get all folders for selection (exclude Config folder and root, but include Other)
  const getAllFolders = (node, path = []) => {
    let folders = [];
    
    // Skip root and Config folders
    if (node.id === "root" || node.id === "Config") {
      // Process children with empty path for root, or skip Config entirely
      if (node.id === "root" && node.folders) {
        node.folders.forEach(folder => {
          if (folder.id !== "Config") {
            // Include Other folder and custom folders
            folders = folders.concat(getAllFolders(folder, []));
          }
        });
      }
      return folders;
    }
    
    // Build path for current folder
    const currentPath = path.length > 0 ? [...path, node.name] : [node.name];
    
    // Add current folder (including Other folder)
    folders.push({ id: node.id, name: node.name, path: currentPath });
    
    // Process child folders (exclude Config, but include Other and custom folders)
    if (node.folders) {
      node.folders.forEach(folder => {
        if (folder.id !== "Config") {
          folders = folders.concat(getAllFolders(folder, currentPath));
        }
      });
    }
    
    return folders;
  };
  
  const folderOptions = folderStructure ? [
    ...getAllFolders(folderStructure).map(f => ({
      value: f.id,
      label: f.path.join(' / ')
    }))
  ] : [];

  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files || []);
    setFiles(prev => [...prev, ...selectedFiles]);
    setError(null);
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFiles = Array.from(e.dataTransfer.files);
      setFiles(prev => [...prev, ...droppedFiles]);
      setError(null);
    }
  };

  const removeFile = (index) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (files.length === 0) return;
    
    setIsUploading(true);
    setError(null);
    
    try {
      // Upload using real API
      const metadata = {
        who: details.who,
        what: details.what,
        where: details.where || null,
        when: details.when || null,
        why: details.why || null,
        description: details.description || null
      };
      
      const projectId = project.project_id || project.id;
      const result = await api.uploadDocuments(projectId, files, metadata, selectedFolderId || null);
      
      // Upload successful - close modal and refresh
      // Create upload record for UI consistency
      const uploadRecord = createUploadRecord('document', files, authedUser.username, projectId, {
        ...details,
        folderId: selectedFolderId || null
      });
      
      onUpload(uploadRecord, selectedFolderId);
      onClose(); // Close modal after successful upload
    } catch (error) {
      console.error('Upload failed:', error);
      // Handle error message properly
      let errorMessage = 'Upload failed. Please try again.';
      if (error instanceof Error) {
        errorMessage = error.message;
      } else if (typeof error === 'string') {
        errorMessage = error;
      } else if (error && error.message) {
        errorMessage = error.message;
      } else if (error && error.detail) {
        errorMessage = error.detail;
      }
      setError(errorMessage);
      // Don't close modal on error - let user see the error and retry
    } finally {
      setIsUploading(false);
    }
  };

  // No preset options - only project-specific saved options

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 overflow-y-auto">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative z-10 w-full max-w-5xl max-h-[90vh] my-4">
        <Card title="Upload Documents" actions={<Button variant="secondary" onClick={onClose}>Close</Button>}>
          <div className="max-h-[calc(90vh-120px)] overflow-y-auto pr-2">
            <form onSubmit={handleSubmit} className="grid gap-3">
            {error && (
              <div className="rounded-xl border border-rose-300 dark:border-rose-700 bg-rose-50 dark:bg-rose-900/20 p-3 text-sm text-rose-700 dark:text-rose-400">
                {error}
                </div>
              )}

            <Field label="Upload to Folder (Optional)">
              <Select
                value={selectedFolderId}
                onChange={setSelectedFolderId}
                options={[
                  { value: "", label: "Root (No folder)" },
                  ...folderOptions
                ]}
                placeholder="Select folder (leave empty for root)..."
              />
            </Field>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Field label="Responsible User">
                <Input
                  value={details.who}
                  disabled
                  className="bg-gray-100 dark:bg-gray-700"
                />
              </Field>
              <Field label="Activity Type">
                <SelectWithOther
                  value={details.what}
                  onChange={async (value) => {
                    setDetails({...details, what: value});
                    // Save custom option to project
                    if (value && !projectOptions.what.includes(value)) {
                      try {
                        const projectId = project.project_id || project.id;
                        await api.saveProjectOption(projectId, 'what', value);
                        setProjectOptions(prev => ({ ...prev, what: [...prev.what, value] }));
                      } catch (error) {
                        console.error('Failed to save option:', error);
                      }
                    }
                  }}
                  options={projectOptions.what.map(v => ({ value: v, label: v }))}
                  placeholder="Type custom value..."
                />
              </Field>
              <Field label="Site">
                <SelectWithOther
                  value={details.where}
                  onChange={async (value) => {
                    setDetails({...details, where: value});
                    // Save custom option to project
                    if (value && !projectOptions.where.includes(value)) {
                      try {
                        const projectId = project.project_id || project.id;
                        await api.saveProjectOption(projectId, 'where', value);
                        setProjectOptions(prev => ({ ...prev, where: [...prev.where, value] }));
                      } catch (error) {
                        console.error('Failed to save option:', error);
                      }
                    }
                  }}
                  options={projectOptions.where.map(v => ({ value: v, label: v }))}
                  placeholder="Type custom value..."
                />
              </Field>
              <Field label="Operational Timing">
                <SelectWithOther
                  value={details.when}
                  onChange={async (value) => {
                    setDetails({...details, when: value});
                    // Save custom option to project
                    if (value && !projectOptions.when.includes(value)) {
                      try {
                        const projectId = project.project_id || project.id;
                        await api.saveProjectOption(projectId, 'when', value);
                        setProjectOptions(prev => ({ ...prev, when: [...prev.when, value] }));
                      } catch (error) {
                        console.error('Failed to save option:', error);
                      }
                    }
                  }}
                  options={projectOptions.when.map(v => ({ value: v, label: v }))}
                  placeholder="Type custom value..."
                />
              </Field>
            </div>

            <Field label="Purpose">
              <SelectWithOther
                value={details.why}
                onChange={async (value) => {
                  setDetails({...details, why: value});
                  // Save custom option to project
                  if (value && !projectOptions.why.includes(value)) {
                    try {
                      const projectId = project.project_id || project.id;
                      await api.saveProjectOption(projectId, 'why', value);
                      setProjectOptions(prev => ({ ...prev, why: [...prev.why, value] }));
                    } catch (error) {
                      console.error('Failed to save option:', error);
                    }
                  }
                }}
                options={projectOptions.why.map(v => ({ value: v, label: v }))}
                placeholder="Type custom value..."
              />
            </Field>

            <Field label="Description">
              <textarea
                value={details.description}
                onChange={(e) => setDetails({...details, description: e.target.value})}
                placeholder="Describe the purpose of this upload..."
                className="w-full rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm min-h-[80px]"
              />
            </Field>

            {/* File Upload Section - Moved to bottom */}
            <Field label="Select Document Files">
              <div
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-xl p-6 text-center transition-colors ${
                  dragActive
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                    : 'border-gray-300 dark:border-gray-700 hover:border-gray-400 dark:hover:border-gray-600'
                }`}
              >
                <input
                  type="file"
                  multiple
                  accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg"
                  onChange={handleFileChange}
                  className="hidden"
                  id="file-upload-input-doc"
                />
                <label
                  htmlFor="file-upload-input-doc"
                  className="cursor-pointer block"
                >
                  <div className="text-4xl mb-2">📁</div>
                  <div className="text-sm font-medium mb-1">
                    Drag & drop files here, or click to select
                  </div>
                  <div className="text-xs text-gray-500">
                    You can select multiple files
                  </div>
                </label>
              </div>
              
              {files.length > 0 && (
                <div className="mt-4">
                  <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Selected {files.length} file(s):
                  </div>
                  <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-2 max-h-48 overflow-y-auto">
                    <div className="space-y-2">
                      {files.map((file, idx) => (
                        <div key={idx} className="flex items-center justify-between rounded-lg border border-gray-200 dark:border-gray-700 p-2 text-sm bg-gray-50 dark:bg-gray-800/50">
                          <div className="flex-1 min-w-0">
                            <div className="font-medium truncate">{file.name}</div>
                            <div className="text-xs text-gray-500">{(file.size / 1024).toFixed(1)} KB</div>
                          </div>
                          <button
                            type="button"
                            onClick={() => removeFile(idx)}
                            className="ml-2 text-rose-500 hover:text-rose-700 text-sm flex-shrink-0"
                          >
                            ✕
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </Field>

            <div className="flex gap-2 justify-end sticky bottom-0 bg-white dark:bg-gray-900 pt-3 pb-1 border-t border-gray-200 dark:border-gray-700 mt-2">
              <Button variant="secondary" onClick={onClose}>Cancel</Button>
              <Button type="submit" disabled={files.length === 0 || isUploading}>
                {isUploading ? 'Uploading...' : 'Upload Files'}
              </Button>
            </div>
          </form>
          </div>
        </Card>
      </div>
    </div>
  );
};

/* ========= DOCUMENTS (file tree + preview) ========= */
/* ========= ANALYSIS PAGE ========= */
const AnalysisPage = ({ project, authedUser, onChangeTab }) => {
  const [analyses, setAnalyses] = useState([]);
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedAnalysis, setSelectedAnalysis] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const [filters, setFilters] = useState({
    device_name: null,
    status: null,
    analysis_type: null
  });
  const [performanceMetrics, setPerformanceMetrics] = useState([]);
  const [showMetrics, setShowMetrics] = useState(false);

  useEffect(() => {
    loadAnalyses();
    loadDevices();
    loadPerformanceMetrics();
  }, [project?.project_id, filters]);

  const loadDevices = async () => {
    try {
      const summary = await api.getConfigSummary(project.project_id);
      const deviceNames = summary.map(d => d.device).filter(Boolean);
      setDevices([...new Set(deviceNames)]);
    } catch (e) {
      console.error("Failed to load devices:", e);
    }
  };

  const loadAnalyses = async () => {
    setLoading(true);
    try {
      const data = await api.getAnalyses(project.project_id, filters);
      setAnalyses(data);
    } catch (e) {
      console.error("Failed to load analyses:", e);
      alert("Failed to load analyses: " + e.message);
    } finally {
      setLoading(false);
    }
  };

  const loadPerformanceMetrics = async () => {
    try {
      const metrics = await api.getPerformanceMetrics(project.project_id, filters.device_name, 50);
      setPerformanceMetrics(metrics);
    } catch (e) {
      console.error("Failed to load performance metrics:", e);
    }
  };

  const handleCreateAnalysis = async (deviceName, analysisType, customPrompt, includeOriginal) => {
    setLoading(true);
    try {
      const newAnalysis = await api.createAnalysis(
        project.project_id,
        deviceName,
        analysisType,
        customPrompt,
        includeOriginal
      );
      await loadAnalyses();
      setSelectedAnalysis(newAnalysis);
      setShowCreate(false);
    } catch (e) {
      alert("Failed to create analysis: " + e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyAnalysis = async (analysisId, verifiedContent, comments, status) => {
    setLoading(true);
    try {
      const updated = await api.verifyAnalysis(
        project.project_id,
        analysisId,
        verifiedContent,
        comments,
        status
      );
      await loadAnalyses();
      setSelectedAnalysis(updated);
    } catch (e) {
      alert("Failed to verify analysis: " + e.message);
    } finally {
      setLoading(false);
    }
  };

  const analysisTypes = [
    { value: "security_audit", label: "Security Audit" },
    { value: "performance_review", label: "Performance Review" },
    { value: "configuration_compliance", label: "Configuration Compliance" },
    { value: "network_topology", label: "Network Topology" },
    { value: "best_practices", label: "Best Practices" },
    { value: "custom", label: "Custom Analysis" }
  ];

  const statusColors = {
    pending_review: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100",
    verified: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100",
    rejected: "bg-rose-100 text-rose-800 dark:bg-rose-900 dark:text-rose-100"
  };


  return (
    <div className="grid gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">AI Analysis</h2>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            LLM-powered network configuration analysis with Human-in-the-Loop workflow
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => setShowMetrics(!showMetrics)}>
            {showMetrics ? "Hide" : "Show"} Metrics
          </Button>
          <Button onClick={() => setShowCreate(true)} disabled={loading || devices.length === 0}>
            + New Analysis
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <div className="grid gap-3 md:grid-cols-3">
          <Field label="Device">
            <Select
              options={[{ value: null, label: "All Devices" }, ...devices.map(d => ({ value: d, label: d }))]}
              value={filters.device_name || null}
              onChange={(val) => setFilters({ ...filters, device_name: val || null })}
            />
          </Field>
          <Field label="Status">
            <Select
              options={[
                { value: null, label: "All Status" },
                { value: "pending_review", label: "Pending Review" },
                { value: "verified", label: "Verified" },
                { value: "rejected", label: "Rejected" }
              ]}
              value={filters.status || null}
              onChange={(val) => setFilters({ ...filters, status: val || null })}
            />
          </Field>
          <Field label="Analysis Type">
            <Select
              options={[{ value: null, label: "All Types" }, ...analysisTypes]}
              value={filters.analysis_type || null}
              onChange={(val) => setFilters({ ...filters, analysis_type: val || null })}
            />
          </Field>
        </div>
      </Card>

      {/* Performance Metrics Dashboard */}
      {showMetrics && (
        <Card title="Performance Metrics">
          <PerformanceMetricsView metrics={performanceMetrics} />
        </Card>
      )}

      {/* Create Analysis Modal */}
      {showCreate && (
        <CreateAnalysisModal
          devices={devices}
          analysisTypes={analysisTypes}
          onCreate={handleCreateAnalysis}
          onClose={() => setShowCreate(false)}
          loading={loading}
        />
      )}

      {/* Analysis List */}
      {loading && analyses.length === 0 ? (
        <div className="text-center py-12 text-gray-500">Loading analyses...</div>
      ) : analyses.length === 0 ? (
        <Card>
          <div className="text-center py-12 text-gray-500">
            <p className="mb-4">No analyses found</p>
            <Button onClick={() => setShowCreate(true)}>Create First Analysis</Button>
          </div>
        </Card>
      ) : (
        <div className="grid gap-4">
          {analyses.map((analysis) => (
            <Card
              key={analysis.analysis_id}
              className="hover:shadow-lg transition-all cursor-pointer"
              onClick={() => setSelectedAnalysis(analysis)}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="font-semibold">{analysis.device_name}</h3>
                    <Badge className={statusColors[analysis.status]}>
                      {analysis.status.replace("_", " ")}
                    </Badge>
                    <Badge>{analysis.analysis_type.replace("_", " ")}</Badge>
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                    {analysis.ai_draft_text?.substring(0, 200)}...
                  </div>
                  <div className="flex items-center gap-4 text-xs text-gray-500">
                    <span>Created: {formatDateTime(analysis.created_at)}</span>
                    <span>By: {analysis.created_by}</span>
                    {analysis.llm_metrics && (
                      <span>
                        {analysis.llm_metrics.inference_time_ms?.toFixed(0)}ms · {analysis.llm_metrics.model_name}
                      </span>
                    )}
                    {analysis.accuracy_metrics && (
                      <span className="font-semibold">
                        Accuracy: {analysis.accuracy_metrics.accuracy_score}%
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Analysis Detail Modal */}
      {selectedAnalysis && (
        <AnalysisDetailModal
          analysis={selectedAnalysis}
          authedUser={authedUser}
          onVerify={handleVerifyAnalysis}
          onClose={() => setSelectedAnalysis(null)}
          loading={loading}
        />
      )}
    </div>
  );
};

/* ========= ANALYSIS COMPONENTS ========= */
const CreateAnalysisModal = ({ devices, analysisTypes, onCreate, onClose, loading }) => {
  const [deviceName, setDeviceName] = useState("");
  const [analysisType, setAnalysisType] = useState("security_audit");
  const [customPrompt, setCustomPrompt] = useState("");
  const [includeOriginal, setIncludeOriginal] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!deviceName) {
      alert("Please select a device");
      return;
    }
    onCreate(
      deviceName,
      analysisType,
      analysisType === "custom" ? customPrompt : null,
      includeOriginal
    );
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Create New Analysis</h3>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">✕</button>
        </div>
        <form onSubmit={handleSubmit} className="grid gap-4">
          <Field label="Device">
            <Select
              options={devices.map(d => ({ value: d, label: d }))}
              value={deviceName}
              onChange={setDeviceName}
            />
          </Field>
          <Field label="Analysis Type">
            <Select
              options={analysisTypes}
              value={analysisType}
              onChange={setAnalysisType}
            />
          </Field>
          {analysisType === "custom" && (
            <Field label="Custom Prompt">
              <textarea
                className="w-full rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={4}
                value={customPrompt}
                onChange={(e) => setCustomPrompt(e.target.value)}
                placeholder="Enter your custom analysis prompt..."
              />
            </Field>
          )}
          <Field>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={includeOriginal}
                onChange={(e) => setIncludeOriginal(e.target.checked)}
                className="rounded border-gray-300"
              />
              <span className="text-sm">Include original configuration content (may increase processing time)</span>
            </label>
          </Field>
          <div className="flex gap-2 justify-end">
            <Button variant="secondary" onClick={onClose} disabled={loading}>Cancel</Button>
            <Button type="submit" disabled={loading || !deviceName}>
              {loading ? "Creating..." : "Create Analysis"}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
};

const AnalysisDetailModal = ({ analysis, authedUser, onVerify, onClose, loading }) => {
  const [viewMode, setViewMode] = useState("draft"); // "draft" or "verified"
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent, setEditedContent] = useState(null);
  const [comments, setComments] = useState("");
  const [showDiff, setShowDiff] = useState(false);
  
  const statusColors = {
    pending_review: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100",
    verified: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100",
    rejected: "bg-rose-100 text-rose-800 dark:bg-rose-900 dark:text-rose-100"
  };

  useEffect(() => {
    if (analysis.verified_version) {
      setEditedContent(analysis.verified_version);
    } else {
      setEditedContent(analysis.ai_draft);
    }
  }, [analysis]);

  const handleSave = async () => {
    if (!editedContent) return;
    await onVerify(
      analysis.analysis_id,
      editedContent,
      comments,
      "verified"
    );
    setIsEditing(false);
  };

  const handleReject = async () => {
    if (!confirm("Are you sure you want to reject this analysis?")) return;
    await onVerify(
      analysis.analysis_id,
      analysis.ai_draft,
      comments || "Rejected by reviewer",
      "rejected"
    );
  };

  const currentContent = viewMode === "verified" && analysis.verified_version
    ? analysis.verified_version
    : analysis.ai_draft;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between mb-4 border-b pb-4">
          <div>
            <h3 className="text-lg font-semibold">{analysis.device_name} - {analysis.analysis_type.replace("_", " ")}</h3>
            <div className="flex items-center gap-2 mt-2">
              <Badge className={statusColors[analysis.status]}>
                {analysis.status.replace("_", " ")}
              </Badge>
              {analysis.accuracy_metrics && (
                <Badge className="bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100">
                  Accuracy: {analysis.accuracy_metrics.accuracy_score}%
                </Badge>
              )}
            </div>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">✕</button>
        </div>

        <div className="flex-1 overflow-y-auto">
          {/* View Mode Toggle */}
          {analysis.verified_version && (
            <div className="flex gap-2 mb-4">
              <Button
                variant={viewMode === "draft" ? "primary" : "secondary"}
                onClick={() => setViewMode("draft")}
              >
                AI Draft
              </Button>
              <Button
                variant={viewMode === "verified" ? "primary" : "secondary"}
                onClick={() => setViewMode("verified")}
              >
                Verified Version
              </Button>
              {analysis.verified_version && (
                <Button
                  variant={showDiff ? "primary" : "secondary"}
                  onClick={() => setShowDiff(!showDiff)}
                >
                  {showDiff ? "Hide" : "Show"} Diff
                </Button>
              )}
            </div>
          )}

          {/* Diff View */}
          {showDiff && analysis.diff_summary && (
            <Card className="mb-4" title="Changes Summary">
              <DiffView diff={analysis.diff_summary} />
            </Card>
          )}

          {/* Content Display/Edit */}
          {isEditing ? (
            <div className="grid gap-4">
              <Field label="Analysis Content (JSON)">
                <textarea
                  className="w-full rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm font-mono text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  rows={20}
                  value={JSON.stringify(editedContent, null, 2)}
                  onChange={(e) => {
                    try {
                      setEditedContent(JSON.parse(e.target.value));
                    } catch {
                      // Invalid JSON, keep as is
                    }
                  }}
                />
              </Field>
              <Field label="Comments">
                <textarea
                  className="w-full rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  rows={3}
                  value={comments}
                  onChange={(e) => setComments(e.target.value)}
                  placeholder="Add comments about your changes..."
                />
              </Field>
            </div>
          ) : (
            <div className="prose dark:prose-invert max-w-none">
              <pre className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg overflow-x-auto text-sm">
                {JSON.stringify(currentContent, null, 2)}
              </pre>
              {analysis.ai_draft_text && viewMode === "draft" && (
                <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                  <h4 className="font-semibold mb-2">Full AI Response:</h4>
                  <p className="whitespace-pre-wrap text-sm">{analysis.ai_draft_text}</p>
                </div>
              )}
            </div>
          )}

          {/* Metrics */}
          {analysis.llm_metrics && (
            <Card className="mt-4" title="Performance Metrics">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <div className="text-gray-500">Inference Time</div>
                  <div className="font-semibold">{analysis.llm_metrics.inference_time_ms?.toFixed(0)}ms</div>
                </div>
                <div>
                  <div className="text-gray-500">Model</div>
                  <div className="font-semibold">{analysis.llm_metrics.model_name}</div>
                </div>
                <div>
                  <div className="text-gray-500">Prompt Tokens</div>
                  <div className="font-semibold">{analysis.llm_metrics.token_usage?.prompt_tokens || 0}</div>
                </div>
                <div>
                  <div className="text-gray-500">Completion Tokens</div>
                  <div className="font-semibold">{analysis.llm_metrics.token_usage?.completion_tokens || 0}</div>
                </div>
              </div>
            </Card>
          )}
        </div>

        {/* Actions */}
        {analysis.status === "pending_review" && (
          <div className="flex gap-2 justify-end mt-4 border-t pt-4">
            <Button variant="secondary" onClick={onClose}>Close</Button>
            <Button variant="danger" onClick={handleReject} disabled={loading}>
              Reject
            </Button>
            {isEditing ? (
              <>
                <Button variant="secondary" onClick={() => setIsEditing(false)}>Cancel Edit</Button>
                <Button onClick={handleSave} disabled={loading}>
                  {loading ? "Saving..." : "Save & Verify"}
                </Button>
              </>
            ) : (
              <Button onClick={() => setIsEditing(true)}>
                Edit & Verify
              </Button>
            )}
          </div>
        )}
      </Card>
    </div>
  );
};

const DiffView = ({ diff }) => {
  if (!diff) return null;

  return (
    <div className="grid gap-4">
      <div className="flex items-center gap-4">
        <div>
          <span className="text-sm text-gray-500">Total Changes:</span>
          <span className="ml-2 font-semibold">{diff.total_changes || 0}</span>
        </div>
        <div>
          <span className="text-sm text-gray-500">Accuracy Score:</span>
          <span className="ml-2 font-semibold">{diff.accuracy_score || 0}%</span>
        </div>
      </div>

      {diff.changes_by_type && Object.keys(diff.changes_by_type).length > 0 && (
        <div>
          <h4 className="font-semibold mb-2">Changes by Type:</h4>
          <div className="grid gap-2">
            {Object.entries(diff.changes_by_type).map(([type, changes]) => (
              <div key={type} className="p-2 bg-gray-50 dark:bg-gray-800 rounded">
                <div className="font-medium capitalize">{type}: {changes.length}</div>
                <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  {changes.slice(0, 5).map((change, idx) => (
                    <div key={idx} className="truncate">
                      {change.field}: {JSON.stringify(change.ai_value)} → {JSON.stringify(change.verified_value)}
                    </div>
                  ))}
                  {changes.length > 5 && <div>... and {changes.length - 5} more</div>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {diff.key_changes && diff.key_changes.length > 0 && (
        <div>
          <h4 className="font-semibold mb-2">Key Changes:</h4>
          <div className="space-y-2">
            {diff.key_changes.map((change, idx) => (
              <div key={idx} className="p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded border border-yellow-200 dark:border-yellow-800">
                <div className="font-medium text-sm">{change.field}</div>
                <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                  <div>AI: {JSON.stringify(change.ai_value)}</div>
                  <div>Human: {JSON.stringify(change.verified_value)}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const PerformanceMetricsView = ({ metrics }) => {
  if (!metrics || metrics.length === 0) {
    return <div className="text-center py-8 text-gray-500">No performance metrics available</div>;
  }

  const avgInferenceTime = metrics.reduce((sum, m) => sum + (m.inference_time_ms || 0), 0) / metrics.length;
  const avgAccuracy = metrics
    .filter(m => m.accuracy_score !== null)
    .reduce((sum, m) => sum + (m.accuracy_score || 0), 0) / metrics.filter(m => m.accuracy_score !== null).length || 0;
  const totalTokens = metrics.reduce((sum, m) => sum + ((m.token_usage?.total_tokens || 0)), 0);

  return (
    <div className="grid gap-4">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <div className="text-sm text-gray-500">Avg Inference Time</div>
          <div className="text-2xl font-semibold">{avgInferenceTime.toFixed(0)}ms</div>
        </Card>
        <Card>
          <div className="text-sm text-gray-500">Avg Accuracy</div>
          <div className="text-2xl font-semibold">{avgAccuracy.toFixed(1)}%</div>
        </Card>
        <Card>
          <div className="text-sm text-gray-500">Total Requests</div>
          <div className="text-2xl font-semibold">{metrics.length}</div>
        </Card>
        <Card>
          <div className="text-sm text-gray-500">Total Tokens</div>
          <div className="text-2xl font-semibold">{totalTokens.toLocaleString()}</div>
        </Card>
      </div>

      <div className="max-h-96 overflow-y-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-800 sticky top-0">
            <tr>
              <th className="px-4 py-2 text-left">Device</th>
              <th className="px-4 py-2 text-left">Time (ms)</th>
              <th className="px-4 py-2 text-left">Tokens</th>
              <th className="px-4 py-2 text-left">Accuracy</th>
              <th className="px-4 py-2 text-left">Timestamp</th>
            </tr>
          </thead>
          <tbody>
            {metrics.map((m) => (
              <tr key={m.log_id} className="border-b border-gray-200 dark:border-gray-700">
                <td className="px-4 py-2">{m.device_name}</td>
                <td className="px-4 py-2">{m.inference_time_ms?.toFixed(0)}</td>
                <td className="px-4 py-2">{m.token_usage?.total_tokens || 0}</td>
                <td className="px-4 py-2">
                  {m.accuracy_score !== null ? `${m.accuracy_score.toFixed(1)}%` : "—"}
                </td>
                <td className="px-4 py-2">{formatDateTime(m.timestamp)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const DocumentsPage = ({ project, can, authedUser, uploadHistory, setUploadHistory, setProjects }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [selectedDocument, setSelectedDocument] = useState(null); // Document from API
  const [selectedFolder, setSelectedFolder] = useState(null);
  const [expanded, setExpanded] = useState(
    new Set(["root", "Config"])
  );
  const [layout, setLayout] = useState("side");
  const [showUploadConfig, setShowUploadConfig] = useState(false);
  const [showUploadDocument, setShowUploadDocument] = useState(false);
  const [showFolderDialog, setShowFolderDialog] = useState(false);
  const [folderAction, setFolderAction] = useState("add"); // "add", "edit", "delete"
  const [folderName, setFolderName] = useState("");
  const [folderParent, setFolderParent] = useState(null);
  const [showFileRenameDialog, setShowFileRenameDialog] = useState(false);
  const [fileRenameName, setFileRenameName] = useState("");
  const [fileToRename, setFileToRename] = useState(null);
  const [searchDoc, setSearchDoc] = useState("");
  const [filterWho, setFilterWho] = useState("all");
  const [filterWhat, setFilterWhat] = useState("all");
  const [documents, setDocuments] = useState([]); // Documents from API
  const [loading, setLoading] = useState(true);
  const [previewContent, setPreviewContent] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [pdfBlobUrl, setPdfBlobUrl] = useState(null);
  const [filesPanelCollapsed, setFilesPanelCollapsed] = useState(false);
  const [versions, setVersions] = useState([]);
  const [showVersions, setShowVersions] = useState(false);
  const [versionDocument, setVersionDocument] = useState(null); // Store document info for version modal
  const isOpeningVersions = useRef(false); // Flag to prevent accidental modal close during opening
  const [showMoveFolder, setShowMoveFolder] = useState(false);
  const [moveFolderTarget, setMoveFolderTarget] = useState(null);
  const [moveFolderId, setMoveFolderId] = useState('');
  // Load custom folders from API
  const [customFolders, setCustomFolders] = useState([]);
  
  // Load folders from API on mount and when project changes
  useEffect(() => {
    const loadFolders = async () => {
      if (!project?.project_id && !project?.id) {
        setCustomFolders([]);
        return;
      }
      try {
        const projectId = project.project_id || project.id;
        const folders = await api.getFolders(projectId);
        // Transform API response to match expected format
        const transformedFolders = folders.map(f => ({
          id: f.id,
          name: f.name,
          parentId: f.parent_id || null,
          deleted: f.deleted || false
        }));
        setCustomFolders(transformedFolders);
      } catch (error) {
        console.error('Failed to load folders:', error);
        setCustomFolders([]);
      }
    };
    loadFolders();
  }, [project]);

  // Load documents from API
  useEffect(() => {
    const loadDocuments = async () => {
      if (!project?.project_id && !project?.id) {
        setLoading(false);
        return;
      }
      setLoading(true);
      try {
        const projectId = project.project_id || project.id;
        const docs = await api.getDocuments(projectId);
        // Ensure docs is an array
        setDocuments(Array.isArray(docs) ? docs : []);
      } catch (error) {
        console.error('Failed to load documents:', error);
        setDocuments([]);
      } finally {
        setLoading(false);
      }
    };
    loadDocuments();
  }, [project]);

  const handleUpload = async (uploadRecord, folderId) => {
    // Add to upload history
    setUploadHistory(prev => [uploadRecord, ...prev]);
    
    // Always reload documents from API after upload
    // Add a small delay to ensure backend has finished processing
    try {
      const projectId = project.project_id || project.id;
      
      // Wait a bit for backend to finish processing (especially for config parsing)
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Reload all documents (frontend will filter by folder in UI)
      const docs = await api.getDocuments(projectId);
      // Ensure docs is an array
      setDocuments(Array.isArray(docs) ? docs : []);
      
      console.log('Documents reloaded after upload:', docs.length, 'documents');
    } catch (error) {
      console.error('Failed to reload documents:', error);
      // Still update documents to empty array on error to clear stale data
      setDocuments([]);
    }
    
    console.log('Upload completed:', uploadRecord);
  };

  // Load preview for selected document
  useEffect(() => {
    const loadPreview = async () => {
      if (!selectedDocument) {
        setPreviewContent(null);
        // Clean up previous PDF blob URL
        if (pdfBlobUrl) {
          URL.revokeObjectURL(pdfBlobUrl);
          setPdfBlobUrl(null);
        }
        return;
      }
      
      setPreviewLoading(true);
      try {
        const projectId = project.project_id || project.id;
        
        // For PDF files, load the file directly as blob for iframe viewing
        if (selectedDocument.content_type === "application/pdf") {
          const token = api.getToken();
          const response = await fetch(`/projects/${projectId}/documents/${selectedDocument.document_id}/download`, {
            headers: {
              'Authorization': token ? `Bearer ${token}` : '',
            },
          });
          
          if (!response.ok) {
            throw new Error('Failed to load PDF');
          }
          
          const blob = await response.blob();
          // Clean up previous blob URL
          if (pdfBlobUrl) {
            URL.revokeObjectURL(pdfBlobUrl);
          }
          const blobUrl = URL.createObjectURL(blob);
          setPdfBlobUrl(blobUrl);
          setPreviewContent({ preview_type: "pdf", blob_url: blobUrl });
        } else {
          // For other file types, use preview endpoint
          const preview = await api.getDocumentPreview(projectId, selectedDocument.document_id);
          setPreviewContent(preview);
        }
      } catch (error) {
        console.error('Failed to load preview:', error);
        setPreviewContent({ error: error.message });
      } finally {
        setPreviewLoading(false);
      }
    };
    
    loadPreview();
    
    // Cleanup function to revoke blob URL when component unmounts or document changes
    return () => {
      if (pdfBlobUrl) {
        URL.revokeObjectURL(pdfBlobUrl);
        setPdfBlobUrl(null);
      }
    };
  }, [selectedDocument, project]); // Don't include pdfBlobUrl in dependencies to avoid infinite loop

  // Load versions for selected document
  const loadVersions = async (documentId, documentInfo = null) => {
    try {
      // Set flag to prevent accidental close during opening
      isOpeningVersions.current = true;
      
      setVersions([]); // Clear previous versions
      // Store document info for the modal (use provided info or selectedDocument)
      const docInfo = documentInfo || selectedDocument;
      if (!docInfo) {
        console.error('No document info provided for loadVersions');
        isOpeningVersions.current = false;
        return;
      }
      // Set document info and show modal first (with loading state)
      setVersionDocument(docInfo);
      setShowVersions(true);
      
      // Small delay to ensure modal is rendered before API call
      await new Promise(resolve => setTimeout(resolve, 50));
      
      const projectId = project.project_id || project.id;
      const versionData = await api.getDocumentVersions(projectId, documentId);
      console.log('Version data received:', versionData);
      
      if (versionData && versionData.versions && Array.isArray(versionData.versions)) {
        setVersions(versionData.versions);
        // Update versionDocument with filename from API if available
        if (versionData.filename) {
          setVersionDocument(prev => ({
            ...(prev || docInfo),
            filename: versionData.filename
          }));
        }
        if (versionData.versions.length === 0) {
          console.warn('Versions array is empty');
        }
      } else {
        setVersions([]);
        console.warn('No versions found or invalid response:', versionData);
      }
      
      // Clear flag after modal is fully loaded
      setTimeout(() => {
        isOpeningVersions.current = false;
      }, 200);
    } catch (error) {
      console.error('Failed to load versions:', error);
      setVersions([]);
      isOpeningVersions.current = false;
      // Don't close modal on error, show error message instead
      alert('Failed to load version history: ' + (error.message || 'Unknown error'));
    }
  };

  // Build folder structure from API documents (only latest versions)
  const buildFolderStructure = () => {
    const baseStructure = {
      id: "root",
      name: "/",
      files: [],
      folders: [
        {
          id: "Config",
          name: "Config",
          folders: [],
          files: [],
        },
      ],
      files: [],
    };

    // Merge custom folders into base structure
    // Find folder by ID in a specific location (not recursively - to avoid duplicates)
    const findFolderInLocation = (folders, id) => {
      return folders.find(f => f.id === id) || null;
    };
    
    // Find folder recursively in entire structure (for file placement)
    const findFolderInStructure = (folders, id) => {
      for (const folder of folders) {
        if (folder.id === id) return folder;
        if (folder.folders && folder.folders.length > 0) {
          const found = findFolderInStructure(folder.folders, id);
          if (found) return found;
        }
      }
      return null;
    };
    
    // Check if folder already exists anywhere in the structure
    const folderExists = (targetFolders, folderId) => {
      return findFolderInStructure(targetFolders, folderId) !== null;
    };

    // Helper function to ensure a folder exists in the structure at the correct location
    const ensureFolderExists = (targetFolders, folderId, folderName, parentId, customFolders, visited = new Set(), rootFolders = baseStructure.folders) => {
      // Prevent infinite loops
      if (visited.has(folderId)) {
        return false;
      }
      visited.add(folderId);
      
      // Check if folder already exists anywhere in the entire structure
      const existingFolder = findFolderInStructure(rootFolders, folderId);
      
      if (parentId) {
        // Find parent folder - search in entire structure, not just targetFolders
        const parentFolder = findFolderInStructure(rootFolders, parentId);
        if (parentFolder) {
          if (!parentFolder.folders) {
            parentFolder.folders = [];
          }
          
          // Check if folder already exists in this parent
          const existingInParent = findFolderInLocation(parentFolder.folders, folderId);
          if (existingInParent) {
            return true; // Already exists in correct location
          }
          
          // If folder exists elsewhere, remove it first (it's in wrong location)
          if (existingFolder && existingFolder !== existingInParent) {
            // Remove from wrong location - search in entire structure
            const removeFromStructure = (folders, id) => {
              const index = folders.findIndex(f => f.id === id);
              if (index !== -1) {
                folders.splice(index, 1);
                return true;
              }
              for (const folder of folders) {
                if (folder.folders && removeFromStructure(folder.folders, id)) {
                  return true;
                }
              }
              return false;
            };
            removeFromStructure(rootFolders, folderId);
          }
          
          // Create folder in correct location
          parentFolder.folders.push({
            id: folderId,
            name: folderName,
            folders: [],
            files: [],
          });
          return true;
        } else {
          // Parent not found - try to create parent first if it's a custom folder
          const parentCustomFolder = customFolders.find(f => f.id === parentId);
          if (parentCustomFolder) {
            // Find where parent should be created
            let parentTargetFolders = targetFolders;
            if (parentCustomFolder.parentId) {
              const parentParent = findFolderInStructure(targetFolders, parentCustomFolder.parentId);
              if (parentParent) {
                if (!parentParent.folders) {
                  parentParent.folders = [];
                }
                parentTargetFolders = parentParent.folders;
              } else {
                // Parent's parent doesn't exist - can't create parent yet
                return false;
              }
            }
            
            // Recursively ensure parent exists in the correct location
            if (ensureFolderExists(parentTargetFolders, parentId, parentCustomFolder.name, parentCustomFolder.parentId, customFolders, visited, rootFolders)) {
              // Parent created, now create this folder
              const parentFolderAfter = findFolderInStructure(targetFolders, parentId);
              if (parentFolderAfter) {
                if (!parentFolderAfter.folders) {
                  parentFolderAfter.folders = [];
                }
                // Check if folder already exists in this parent
                if (!findFolderInLocation(parentFolderAfter.folders, folderId)) {
                  // Remove from wrong location if exists
                  if (existingFolder) {
                    const removeFromStructure = (folders, id) => {
                      const index = folders.findIndex(f => f.id === id);
                      if (index !== -1) {
                        folders.splice(index, 1);
                        return true;
                      }
                      for (const folder of folders) {
                        if (folder.folders && removeFromStructure(folder.folders, id)) {
                          return true;
                        }
                      }
                      return false;
                    };
                    removeFromStructure(rootFolders, folderId);
                  }
                  
                  parentFolderAfter.folders.push({
                    id: folderId,
                    name: folderName,
                    folders: [],
                    files: [],
                  });
                  return true;
                } else {
                  return true; // Already exists in correct location
                }
              }
            }
          }
          return false;
        }
      } else {
        // Add to root
        // Check if folder already exists in root
        const existingInRoot = findFolderInLocation(targetFolders, folderId);
        if (existingInRoot) {
          return true; // Already exists in root
        }
        
        // If folder exists elsewhere, remove it first (it's in wrong location)
        if (existingFolder) {
          const removeFromStructure = (folders, id) => {
            const index = folders.findIndex(f => f.id === id);
            if (index !== -1) {
              folders.splice(index, 1);
              return true;
            }
            for (const folder of folders) {
              if (folder.folders && removeFromStructure(folder.folders, id)) {
                return true;
              }
            }
            return false;
          };
          removeFromStructure(rootFolders, folderId);
        }
        
        // Create folder in root
        targetFolders.push({
          id: folderId,
          name: folderName,
          folders: [],
          files: [],
        });
        return true;
      }
    };

    // Filter out deleted folders
    const activeCustomFolders = customFolders.filter(f => !f.deleted);

    const mergeCustomFolders = (targetFolders, customFolders, parentId = null, processed = new Set()) => {
      // Find all folders that belong to the current parent level
      const foldersForThisLevel = customFolders.filter(customFolder => {
        if (customFolder.id === "Config") return false;
        if (processed.has(customFolder.id)) return false;
        return customFolder.parentId === parentId;
      });
      
      // First pass: create all folders at this level
      foldersForThisLevel.forEach(customFolder => {
        if (!processed.has(customFolder.id)) {
          const created = ensureFolderExists(targetFolders, customFolder.id, customFolder.name, customFolder.parentId, customFolders, processed, baseStructure.folders);
          if (created) {
            processed.add(customFolder.id);
          }
        }
      });
      
      // Second pass: recursively merge nested folders for each folder at this level
      foldersForThisLevel.forEach(customFolder => {
        const targetFolder = findFolderInStructure(targetFolders, customFolder.id);
        if (targetFolder) {
          if (!targetFolder.folders) {
            targetFolder.folders = [];
          }
          mergeCustomFolders(targetFolder.folders, customFolders, customFolder.id, processed);
        }
      });
    };

    // Merge custom folders - use multiple passes to ensure parent folders are created first
    if (activeCustomFolders && activeCustomFolders.length > 0) {
      // Calculate depth for each folder (how many levels deep it is)
      const calculateDepth = (folderId, visited = new Set()) => {
        if (visited.has(folderId)) return 0; // Prevent circular references
        visited.add(folderId);
        const folder = activeCustomFolders.find(f => f.id === folderId);
        if (!folder || !folder.parentId) return 0;
        return 1 + calculateDepth(folder.parentId, visited);
      };
      
      // Sort by depth: folders with no parent first, then nested ones by depth
      const sortedFolders = [...activeCustomFolders].sort((a, b) => {
        const depthA = calculateDepth(a.id);
        const depthB = calculateDepth(b.id);
        return depthA - depthB;
      });
      
      // Single pass merge with proper processing tracking
      const processed = new Set();
      mergeCustomFolders(baseStructure.folders, sortedFolders, null, processed);
    }

    // Only show latest versions in file tree
    if (!Array.isArray(documents)) {
      return baseStructure;
    }

    const latestDocs = documents.filter(doc => doc && doc.is_latest);

    // Group documents by folder_id or type
    latestDocs.forEach(doc => {
      if (!doc || !doc.filename) return;
      
      const fileInfo = {
        name: doc.filename,
        size: doc.size,
        sizeFormatted: `${(doc.size / 1024).toFixed(1)} KB`,
        modified: doc.created_at,
        modifiedFormatted: formatDateTime(doc.created_at),
        document_id: doc.document_id,
        version: doc.version,
        is_latest: doc.is_latest,
        uploader: doc.uploader,
        content_type: doc.content_type,
        extension: doc.filename.split('.').pop() || '',
      };

      if (doc.folder_id) {
        // Find folder by ID recursively (supports nested folders)
        const folder = findFolderInStructure(baseStructure.folders, doc.folder_id);
        if (folder) {
          folder.files.push(fileInfo);
        } else {
          // Folder not found - add to root "Other" folder or create one
          let otherFolder = findFolderInStructure(baseStructure.folders, "Other");
          if (!otherFolder) {
            // Create "Other" folder in root
            baseStructure.folders.push({
              id: "Other",
              name: "Other",
              folders: [],
              files: []
            });
            otherFolder = findFolderInStructure(baseStructure.folders, "Other");
          }
          if (otherFolder) {
            otherFolder.files.push(fileInfo);
          }
        }
      } else {
        // No folder_id - add files directly to root (not to Other folder)
        // Files without folder_id should be in root, not automatically in Other
        if (!baseStructure.files) {
          baseStructure.files = [];
        }
        baseStructure.files.push(fileInfo);
      }
    });

    return baseStructure;
  };

  // Build folder structure with custom folders
  const folderStructure = useMemo(() => buildFolderStructure(), [documents, customFolders]);
  const tree = folderStructure;

  const onToggle = (id) => {
    const n = new Set(expanded);
    n.has(id) ? n.delete(id) : n.add(id);
    setExpanded(n);
  };

  // Find folder by ID in tree structure
  const findFolder = (node, id, parent = null) => {
    if (node.id === id) return { node, parent };
    if (node.folders) {
      for (const folder of node.folders) {
        const result = findFolder(folder, id, node);
        if (result) return result;
      }
    }
    return null;
  };

  // Handle folder actions
  const handleNewFolder = () => {
    setFolderAction("add");
    setFolderName("");
    setFolderParent(null);
    setShowFolderDialog(true);
  };

  const handleEditFolder = (folderId) => {
    // Only prevent editing Config folder
    if (folderId === "Config") {
      alert("ไม่สามารถแก้ไขโฟลเดอร์ Config ได้");
      return;
    }
    const found = findFolder(tree, folderId);
    if (found) {
      setFolderAction("edit");
      setSelectedFolder(folderId);
      setFolderName(found.node.name);
      setFolderParent(found.parent ? found.parent.id : null);
      setShowFolderDialog(true);
    } else {
      alert("ไม่พบโฟลเดอร์");
    }
  };

  const handleDeleteFolder = async (folderId) => {
    // Only prevent deleting Config folder and Other folder
    if (folderId === "Config" || folderId === "Other") {
      alert("ไม่สามารถลบโฟลเดอร์นี้ได้");
      return;
    }
    const found = findFolder(tree, folderId);
    if (found) {
      if (confirm(`ต้องการลบโฟลเดอร์ "${found.node.name}" และไฟล์ทั้งหมดภายในหรือไม่?`)) {
        try {
          const projectId = project.project_id || project.id;
          await api.deleteFolder(projectId, folderId);
          // Reload folders from API
          const folders = await api.getFolders(projectId);
          const transformedFolders = folders.map(f => ({
            id: f.id,
            name: f.name,
            parentId: f.parent_id || null,
            deleted: f.deleted || false
          }));
          setCustomFolders(transformedFolders);
          alert("ลบโฟลเดอร์สำเร็จ");
        } catch (error) {
          console.error('Failed to delete folder:', error);
          alert(`ลบโฟลเดอร์ไม่สำเร็จ: ${error.message || error}`);
        }
      }
    }
  };

  const handleSaveFolder = async () => {
    if (!folderName.trim()) {
      alert("กรุณากรอกชื่อโฟลเดอร์");
      return;
    }

    // Prevent editing Config folder and Other folder
    if (folderAction === "edit" && selectedFolder) {
      if (selectedFolder === "Config" || selectedFolder === "Other") {
        alert("ไม่สามารถแก้ไขโฟลเดอร์นี้ได้");
        return;
      }
    }

    try {
      const projectId = project.project_id || project.id;
      
      if (folderAction === "add") {
        // Prevent adding to Config folder
        if (folderParent === "Config" || folderParent === "Other") {
          alert("ไม่สามารถสร้างโฟลเดอร์ในโฟลเดอร์นี้ได้");
          return;
        }
        
        await api.createFolder(projectId, folderName.trim(), folderParent || null);
        alert("สร้างโฟลเดอร์สำเร็จ");
      } else if (folderAction === "edit" && selectedFolder) {
        await api.updateFolder(projectId, selectedFolder, folderName.trim(), folderParent || null);
        alert("แก้ไขโฟลเดอร์สำเร็จ");
      }
      
      // Reload folders from API
      const folders = await api.getFolders(projectId);
      const transformedFolders = folders.map(f => ({
        id: f.id,
        name: f.name,
        parentId: f.parent_id || null,
        deleted: f.deleted || false
      }));
      setCustomFolders(transformedFolders);
      
      setShowFolderDialog(false);
      setFolderName("");
      setSelectedFolder(null);
    } catch (error) {
      console.error('Failed to save folder:', error);
      alert(`ไม่สำเร็จ: ${error.message || error}`);
    }
  };

  const handleEditFile = (file) => {
    // Check if file has document_id
    if (!file || !file.document_id) {
      console.error("File missing document_id:", file);
      alert("Cannot rename: File information is incomplete");
      return;
    }
    
    // Prevent renaming files in Config folder
    const doc = documents.find(d => d.document_id === file.document_id);
    if (doc && doc.folder_id === "Config") {
      alert("Cannot rename files in Config folder");
      return;
    }
    
    setFileToRename(file);
    setFileRenameName(file.name);
    setShowFileRenameDialog(true);
  };

  const handleSaveFileRename = async () => {
    if (!fileRenameName.trim()) {
      alert("Please enter a filename");
      return;
    }

    if (!fileToRename) {
      return;
    }

    try {
      const projectId = project.project_id || project.id;
      await api.renameDocument(projectId, fileToRename.document_id, fileRenameName.trim());
      alert("File renamed successfully");
      
      // Reload documents
      const docsResponse = await api.getDocuments(projectId);
      const docs = Array.isArray(docsResponse) ? docsResponse : (docsResponse?.documents || []);
      setDocuments(docs);
      
      // Update selected file if it was the renamed one
      if (selectedFile && selectedFile.document_id === fileToRename.document_id) {
        const updatedDoc = docs.find(d => d.document_id === fileToRename.document_id);
        if (updatedDoc) {
          setSelectedFile({ ...selectedFile, name: fileRenameName.trim() });
          setSelectedDocument(updatedDoc);
        }
      }
      
      setShowFileRenameDialog(false);
      setFileRenameName("");
      setFileToRename(null);
    } catch (error) {
      console.error('Failed to rename file:', error);
      alert(`Failed: ${error.message || error}`);
    }
  };

  // Get all folders for parent selection
  const getAllFolders = (node, excludeId = null, path = []) => {
    let folders = [];
    
    // Skip root node - just process its children
    if (node.id === "root") {
      if (node.folders) {
        node.folders.forEach(folder => {
          folders = folders.concat(getAllFolders(folder, excludeId, []));
        });
      }
      return folders;
    }
    
    // Build current path - only add node.name if it's not already in path
    const currentPath = path.length > 0 ? [...path, node.name] : [node.name];
    
    // Add current folder if not excluded
    if (node.id !== excludeId) {
      folders.push({ id: node.id, name: node.name, path: currentPath });
    }
    
    // Recursively process child folders with updated path
    if (node.folders) {
      node.folders.forEach(folder => {
        folders = folders.concat(getAllFolders(folder, excludeId, currentPath));
      });
    }
    
    return folders;
  };

  const PreviewPane = (
    <Card
      title={
        <div className="text-xs font-medium text-gray-600 dark:text-gray-400">
          {selectedFile ? selectedFile.name : "Preview"}
        </div>
      }
      actions={
        selectedFile && selectedDocument ? (
          <div className="flex gap-2">
          <Button
            variant="secondary"
              onClick={async () => {
                try {
                  const projectId = project.project_id || project.id;
                  await api.downloadDocument(projectId, selectedDocument.document_id);
                } catch (error) {
                  alert('Download failed: ' + error.message);
                }
            }}
          >
            ⬇ Download
          </Button>
            <Button
              variant="secondary"
              onClick={(e) => {
                e.stopPropagation();
                loadVersions(selectedDocument.document_id, selectedDocument);
              }}
            >
              📜 Versions
            </Button>
            {/* Only show Rename button if document is not in Config folder */}
            {selectedDocument.folder_id !== "Config" && (
              <Button
                variant="secondary"
                onClick={(e) => {
                  e.stopPropagation();
                  handleEditFile(selectedFile);
                }}
              >
                ✏️ Rename
              </Button>
            )}
            {/* Only show Move button if document is not in Config folder */}
            {selectedDocument.folder_id !== "Config" && (
              <Button
                variant="secondary"
                onClick={(e) => {
                  e.stopPropagation();
                  setMoveFolderTarget(selectedDocument);
                  setMoveFolderId(selectedDocument.folder_id || '');
                  setShowMoveFolder(true);
                }}
              >
                📁 Move
              </Button>
            )}
            {/* Only show Delete button if document is not in Config folder and user has permission */}
            {selectedDocument.folder_id !== "Config" && can("project-setting", project) && (
              <Button
                variant="danger"
                onClick={async (e) => {
                  e.stopPropagation();
                  if (confirm(`Are you sure you want to delete "${selectedDocument.filename}"?`)) {
                    try {
                      const projectId = project.project_id || project.id;
                      await api.deleteDocument(projectId, selectedDocument.document_id);
                      alert("Document deleted successfully");
                      // Reload documents
                      const docs = await api.getDocuments(projectId);
                      setDocuments(Array.isArray(docs) ? docs : []);
                      // Clear selection
                      setSelectedFile(null);
                      setSelectedDocument(null);
                      setPreviewContent(null);
                    } catch (error) {
                      alert("Failed to delete document: " + (error.message || error));
                    }
                  }
                }}
              >
                🗑️ Delete
              </Button>
            )}
          </div>
        ) : null
      }
    >
      <div className={layout === "side" ? "h-[85vh]" : "h-[80vh]"}>

        {!selectedFile && (
          <div
            className={`${
              layout === "side"
                ? "h-[calc(85vh-1.5rem)]"
                : "h-[calc(80vh-1.5rem)]"
            } grid place-items-center text-sm text-gray-500 dark:text-gray-400`}
          >
            Select a file to preview. Supported: <b>.txt, .pdf, .png, .jpg</b>
          </div>
        )}

        {previewLoading && (
          <div
            className={`${
              layout === "side"
                ? "h-[calc(85vh-2rem)]"
                : "h-[calc(80vh-2rem)]"
            } grid place-items-center text-sm text-gray-500 dark:text-gray-400`}
          >
            Loading preview...
          </div>
        )}

        {!previewLoading && previewContent && (
          <>
            {previewContent.error ? (
              <div className="text-sm text-rose-500 dark:text-rose-400 p-4">
                Error loading preview: {previewContent.error}
              </div>
            ) : previewContent.preview_type === "text" ? (
          <div
            className={`${
              layout === "side"
                    ? "h-[calc(85vh-2rem)]"
                    : "h-[calc(80vh-2rem)]"
                } rounded-xl border border-gray-200 dark:border-[#1F2937] p-4 bg-gray-50 dark:bg-[#0F172A] text-sm overflow-auto`}
          >
                <pre className="whitespace-pre-wrap text-[13px] leading-relaxed">
                  {previewContent.preview_data || "(empty file)"}
                </pre>
          </div>
            ) : previewContent.preview_type === "image" ? (
              // Regular image preview with size constraints - images are already resized by backend
              <div className="flex items-center justify-center p-4 min-h-[200px]">
                <img
                  src={previewContent.preview_data}
                  alt={selectedFile?.name || "Preview"}
                  className={`${
                    layout === "side"
                      ? "max-h-[calc(85vh-2rem)] max-w-[calc(50vw-4rem)]"
                      : "max-h-[calc(80vh-2rem)] max-w-[calc(90vw-4rem)]"
                  } w-auto h-auto object-contain rounded-xl shadow-lg`}
                  style={{ 
                    maxWidth: '100%', 
                    maxHeight: '100%',
                    imageRendering: 'auto'
                  }}
                  loading="lazy"
                />
              </div>
            ) : previewContent.preview_type === "pdf" || previewContent.blob_url ? (
              // PDF preview using blob URL
              previewContent.blob_url ? (
                <div className={`${
                  layout === "side"
                    ? "h-[calc(85vh-1.5rem)]"
                    : "h-[calc(80vh-1.5rem)]"
                } rounded-xl border border-gray-200 dark:border-[#1F2937] overflow-hidden bg-gray-50 dark:bg-gray-900`}>
                  <iframe
                    src={`${previewContent.blob_url}#toolbar=1&navpanes=1&scrollbar=1`}
                    className="w-full h-full"
                    title="PDF Preview"
                    type="application/pdf"
                  />
                </div>
              ) : (
                <div
                  className={`${
                    layout === "side"
                      ? "h-[calc(85vh-1.5rem)]"
                      : "h-[calc(80vh-1.5rem)]"
                  } grid place-items-center text-gray-500 dark:text-gray-300 border border-gray-200 dark:border-[#1F2937] rounded-xl`}
                >
                  <div className="text-center">
                    <div className="text-4xl mb-2">📄</div>
                    <div>{previewContent.preview_data || "PDF Preview"}</div>
                    <div className="text-sm mt-2">Click Download to view PDF</div>
                  </div>
                </div>
              )
            ) : (
              <div className="text-sm text-gray-500 dark:text-gray-400 p-4">
                {previewContent.preview_data || "Preview not available"}
              </div>
            )}
          </>
        )}
      </div>
    </Card>
  );


  // Early return if no project
  if (!project) {
    return (
      <div className="grid gap-4">
        <div className="text-sm text-rose-400">Project not found</div>
      </div>
    );
  }

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Documents</h2>
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            onClick={() => setLayout(layout === "side" ? "bottom" : "side")}
          >
            {layout === "side" ? "Preview Bottom" : "Preview Side"}
          </Button>
          {can("upload-config", project) && (
            <Button variant="secondary" onClick={() => setShowUploadConfig(true)}>
              Upload Config
            </Button>
          )}
          {can("upload-document", project) && (
            <Button variant="secondary" onClick={() => setShowUploadDocument(true)}>
              Upload Document
            </Button>
          )}
          {can("project-setting", project) && (
            <>
              <Button variant="secondary" onClick={handleNewFolder}>New Folder</Button>
              {selectedFolder && (
                <>
                  <Button variant="secondary" onClick={() => handleEditFolder(selectedFolder)}>Rename</Button>
                  <Button variant="danger" onClick={() => handleDeleteFolder(selectedFolder)}>Delete</Button>
                </>
              )}
            </>
          )}
        </div>
      </div>

      {layout === "side" ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          <Card 
            className={filesPanelCollapsed ? "lg:col-span-1" : "lg:col-span-4"} 
            title={
              <div className="flex items-center justify-between w-full">
                <span>Files</span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setFilesPanelCollapsed(!filesPanelCollapsed);
                  }}
                  className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
                  title={filesPanelCollapsed ? "Expand" : "Collapse"}
                >
                  {filesPanelCollapsed ? "▶" : "◀"}
                </button>
              </div>
            }
          >
            {!filesPanelCollapsed && (
              <div className="h-[85vh] overflow-auto pr-1">
                <FileTree2
                  node={tree}
                  expanded={expanded}
                  onToggle={onToggle}
                  onSelectFile={(f) => {
                    setSelectedFile(f);
                    setSelectedFolder(null);
                    // Find document from API
                    const doc = documents.find(d => d.document_id === f.document_id);
                    if (doc) {
                      setSelectedDocument(doc);
                    } else {
                      setSelectedDocument(null);
                    }
                  }}
                  onSelectFolder={(id, action) => {
                    if (action === "edit") {
                      handleEditFolder(id);
                    } else {
                      setSelectedFolder(id);
                      setSelectedFile(null);
                      setSelectedDocument(null);
                      setPreviewContent(null);
                    }
                  }}
                  selectedFile={selectedFile}
                  selectedFolder={selectedFolder}
                />
              </div>
            )}
          </Card>
          <div className={filesPanelCollapsed ? "lg:col-span-11" : "lg:col-span-8"}>{PreviewPane}</div>
        </div>
      ) : (
        <div className="grid gap-4">
          <Card title="Files">
            <div className="h-[45vh] overflow-auto pr-1">
              <FileTree2
                node={tree}
                expanded={expanded}
                onToggle={onToggle}
                onSelectFile={(f) => {
                  setSelectedFile(f);
                  setSelectedFolder(null);
                  // Find document from API
                  const doc = documents.find(d => d.document_id === f.document_id);
                  if (doc) {
                    setSelectedDocument(doc);
                  } else {
                    setSelectedDocument(null);
                  }
                }}
                onSelectFolder={(id, action) => {
                  if (action === "edit") {
                    handleEditFolder(id);
                  } else {
                    setSelectedFolder(id);
                    setSelectedFile(null);
                    setSelectedDocument(null);
                    setPreviewContent(null);
                  }
                }}
                onEditFile={handleEditFile}
                selectedFile={selectedFile}
                selectedFolder={selectedFolder}
              />
            </div>
          </Card>
          {PreviewPane}
        </div>
      )}

      {/* Version History Modal */}
      {showVersions && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div 
            className="absolute inset-0 bg-black/50" 
            onClick={(e) => {
              e.stopPropagation();
              // Prevent closing during opening
              if (isOpeningVersions.current) {
                return;
              }
              setShowVersions(false);
              setVersionDocument(null);
            }} 
          />
          <div 
            className="relative z-10 w-full max-w-4xl"
            onClick={(e) => e.stopPropagation()}
          >
            <Card
              title={`Version History — ${versionDocument?.filename || selectedDocument?.filename || 'Unknown'}`}
              actions={<Button variant="secondary" onClick={() => {
                setShowVersions(false);
                setVersionDocument(null);
              }}>Close</Button>}
            >
              <div className="max-h-[70vh] overflow-auto">
                {versions.length === 0 ? (
                  <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                    No versions found for this document.
                  </div>
                ) : (
                  <Table
                    columns={[
                      { header: "Version", key: "version", cell: (v) => `v${v.version} ${v.is_latest ? '(Latest)' : ''}` },
                      { header: "Uploaded By", key: "uploader", cell: (v) => v.uploader },
                      { header: "Uploaded At", key: "created_at", cell: (v) => formatDateTime(v.created_at) },
                      { header: "Size", key: "size", cell: (v) => `${(v.size / 1024).toFixed(1)} KB` },
                      { header: "Hash", key: "file_hash", cell: (v) => <span className="font-mono text-xs">{v.file_hash ? v.file_hash.substring(0, 16) + '...' : 'N/A'}</span> },
                      { 
                        header: "Actions", 
                        key: "actions", 
                        cell: (v) => (
                          <div className="flex gap-2">
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={async () => {
                                try {
                                  const projectId = project.project_id || project.id;
                                  const docId = versionDocument?.document_id || selectedDocument?.document_id;
                                  await api.downloadDocument(projectId, docId, v.version);
                                } catch (error) {
                                  alert('Download failed: ' + error.message);
                                }
                              }}
                            >
                              Download
                            </Button>
                          </div>
                        )
                      },
                    ]}
                    data={versions}
                  />
                )}
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* Document Upload History */}
      <Card title="Document Upload History">
        {loading ? (
          <div className="text-center py-8 text-gray-500">Loading documents...</div>
        ) : (
          (() => {
            if (!Array.isArray(documents)) {
              return <div className="text-center py-8 text-gray-500">No documents found</div>;
            }
            
            const uniqueWhos = [...new Set(documents.map(d => d.metadata?.who || d.uploader))];
            const uniqueWhats = [...new Set(documents.map(d => d.metadata?.what || "—"))];
          
            const filteredDocs = documents.filter(doc => {
            const matchSearch = !searchDoc.trim() || 
                [doc.filename, 
                 doc.metadata?.who || doc.uploader,
                 doc.metadata?.what || "—",
                 doc.metadata?.where || "—",
                 doc.metadata?.description || "—"].some(v => 
                v.toLowerCase().includes(searchDoc.toLowerCase())
              );
              const matchWho = filterWho === "all" || (doc.metadata?.who || doc.uploader) === filterWho;
              const matchWhat = filterWhat === "all" || (doc.metadata?.what || "—") === filterWhat;
            return matchSearch && matchWho && matchWhat;
          });
          
          return (
            <>
              <div className="mb-4 grid grid-cols-1 md:grid-cols-3 gap-2">
                <Input 
                  placeholder="ค้นหา (ชื่อไฟล์, ผู้ใช้, คำอธิบาย...)" 
                  value={searchDoc} 
                  onChange={(e) => setSearchDoc(e.target.value)} 
                />
                <Select 
                  value={filterWho} 
                  onChange={setFilterWho} 
                  options={[{value: "all", label: "ทั้งหมด (Responsible User)"}, ...uniqueWhos.map(w => ({value: w, label: w}))]} 
                />
                <Select 
                  value={filterWhat} 
                  onChange={setFilterWhat} 
                  options={[{value: "all", label: "ทั้งหมด (Activity Type)"}, ...uniqueWhats.map(w => ({value: w, label: w}))]} 
                />
              </div>
              <Table
                columns={[
                    { header: "Time", key: "created_at", cell: (r) => formatDateTime(r.created_at) },
                    { header: "Name", key: "filename", cell: (r) => r.filename },
                    { header: "Responsible User", key: "who", cell: (r) => r.metadata?.who || r.uploader },
                    { header: "Activity Type", key: "what", cell: (r) => r.metadata?.what || "—" },
                  { header: "Site", key: "where", cell: (r) => r.metadata?.where || "—" },
                  { header: "Operational Timing", key: "when", cell: (r) => r.metadata?.when || "—" },
                  { header: "Purpose", key: "why", cell: (r) => r.metadata?.why || "—" },
                  { header: "Version", key: "version", cell: (r) => `v${r.version} ${r.is_latest ? '(Latest)' : ''}` },
                  {
                    header: "Actions",
                    key: "actions",
                    cell: (r) => (
                      <div className="flex gap-2">
                        <Button 
                          variant="secondary" 
                          size="sm"
                          onClick={async () => {
                            try {
                              const projectId = project.project_id || project.id;
                              await api.downloadDocument(projectId, r.document_id);
                            } catch (error) {
                              alert('Download failed: ' + error.message);
                            }
                          }}
                        >
                          ⬇ Download
                        </Button>
                        <Button 
                          variant="secondary"
                          size="sm"
                          onClick={async (e) => {
                            e.stopPropagation();
                            // Don't setSelectedDocument here to avoid re-render issues
                            // Pass document info directly to loadVersions
                            await loadVersions(r.document_id, r);
                          }}
                        >
                          📜 Versions
                        </Button>
                      </div>
                    ),
                  },
                ]}
                data={filteredDocs}
                empty="No document uploads yet"
              />
            </>
          );
        })()
        )}
      </Card>

      {/* Move Folder Dialog */}
      {showMoveFolder && moveFolderTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/50" onClick={() => setShowMoveFolder(false)} />
          <div className="relative z-10 w-full max-w-md">
            <Card
              title={`Move Document — ${moveFolderTarget.filename || ''}`}
              actions={<Button variant="secondary" onClick={() => setShowMoveFolder(false)}>Cancel</Button>}
            >
              <div className="space-y-4">
                <Field label="Move to Folder">
                  <Select
                    value={moveFolderId}
                    onChange={setMoveFolderId}
                    options={[
                      { value: "", label: "Root (No folder)" },
                      ...getAllFolders(folderStructure).map(f => ({
                        value: f.id,
                        label: f.path.join(' / ')
                      })).filter(f => f.value !== "Config" && f.value !== "Other") // Exclude Config and Other folders
                    ]}
                    placeholder="Select folder..."
                  />
                </Field>
                {moveFolderTarget?.folder_id === "Config" && (
                  <div className="text-sm text-red-500 dark:text-red-400">
                    ⚠️ ไม่สามารถย้ายไฟล์ออกจากโฟลเดอร์ Config ได้
                  </div>
                )}
                {moveFolderId === "Config" && (
                  <div className="text-sm text-red-500 dark:text-red-400">
                    ⚠️ ไม่สามารถย้ายไฟล์เข้าโฟลเดอร์ Config ได้ กรุณาใช้ Upload Config แทน
                  </div>
                )}
                {moveFolderId === "Other" && (
                  <div className="text-sm text-red-500 dark:text-red-400">
                    ⚠️ ไม่สามารถย้ายไฟล์เข้าโฟลเดอร์ Other ได้ โฟลเดอร์ Other เป็นโฟลเดอร์เสมือนสำหรับไฟล์ที่มี folder_id ไม่ถูกต้อง
                  </div>
                )}
                {moveFolderTarget?.folder_id === "Other" && (
                  <div className="text-sm text-blue-500 dark:text-blue-400">
                    ℹ️ ไฟล์นี้อยู่ในโฟลเดอร์ Other (โฟลเดอร์เสมือน) คุณสามารถย้ายไปโฟลเดอร์อื่นหรือ Root ได้
                  </div>
                )}
                <div className="flex gap-2 justify-end">
                  <Button
                    variant="secondary"
                    onClick={() => setShowMoveFolder(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={async () => {
                      try {
                        // Prevent moving to/from Config folder
                        if (moveFolderTarget?.folder_id === "Config") {
                          alert('ไม่สามารถย้ายไฟล์ออกจากโฟลเดอร์ Config ได้');
                          return;
                        }
                        if (moveFolderId === "Config") {
                          alert('ไม่สามารถย้ายไฟล์เข้าโฟลเดอร์ Config ได้ กรุณาใช้ Upload Config แทน');
                          return;
                        }
                        // Prevent moving to Other folder (it's a virtual folder)
                        if (moveFolderId === "Other") {
                          alert('ไม่สามารถย้ายไฟล์เข้าโฟลเดอร์ Other ได้ โฟลเดอร์ Other เป็นโฟลเดอร์เสมือนสำหรับไฟล์ที่มี folder_id ไม่ถูกต้อง');
                          return;
                        }
                        
                        const projectId = project.project_id || project.id;
                        await api.moveDocumentFolder(projectId, moveFolderTarget.document_id, moveFolderId || null);
                        setShowMoveFolder(false);
                        
                        // Reload documents to reflect the change
                        // Add a small delay to ensure backend has finished processing
                        setTimeout(async () => {
                          try {
                            const projectId2 = project.project_id || project.id;
                            const docs = await api.getDocuments(projectId2);
                            // api.getDocuments returns array directly, not {documents: [...]}
                            setDocuments(Array.isArray(docs) ? docs : []);
                            // Clear selected document since it may have moved
                            setSelectedDocument(null);
                            setSelectedFile(null);
                          } catch (error) {
                            console.error('Failed to reload documents after move:', error);
                            // Still reload to clear stale data
                            const projectId2 = project.project_id || project.id;
                            const docs = await api.getDocuments(projectId2);
                            setDocuments(Array.isArray(docs) ? docs : []);
                          }
                        }, 300);
                        
                        alert('Document moved successfully');
                      } catch (error) {
                        alert('Failed to move document: ' + (error.message || 'Unknown error'));
                      }
                    }}
                  >
                    Move
                  </Button>
                </div>
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* Upload Forms */}
      {showUploadConfig && (
        <UploadConfigForm
          project={project}
          authedUser={authedUser}
          onClose={() => setShowUploadConfig(false)}
          onUpload={handleUpload}
        />
      )}
      {showUploadDocument && (
        <UploadDocumentForm
          project={project}
          authedUser={authedUser}
          onClose={() => setShowUploadDocument(false)}
          onUpload={handleUpload}
          folderStructure={folderStructure}
        />
      )}

      {/* Folder Management Dialog */}
      {showFolderDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 max-w-md w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">
              {folderAction === "add" ? "สร้างโฟลเดอร์ใหม่" : "แก้ไขชื่อโฟลเดอร์"}
            </h3>
            <div className="space-y-4">
              {folderAction === "add" && (
                <Field label="โฟลเดอร์แม่ (ไม่บังคับ)">
                  <Select
                    value={folderParent || ""}
                    onChange={(value) => setFolderParent(value || null)}
                    options={[
                      { value: "", label: "Root (ระดับบนสุด)" },
                      ...getAllFolders(tree).map(f => ({
                        value: f.id,
                        label: f.path.join(" / ")
                      }))
                    ]}
                  />
                </Field>
              )}
              <Field label="ชื่อโฟลเดอร์">
                <Input
                  value={folderName}
                  onChange={(e) => setFolderName(e.target.value)}
                  placeholder="กรอกชื่อโฟลเดอร์"
                  autoFocus
                />
              </Field>
            </div>
            <div className="flex gap-2 mt-6 justify-end">
              <Button variant="secondary" onClick={() => {
                setShowFolderDialog(false);
                setFolderName("");
                setSelectedFolder(null);
              }}>
                ยกเลิก
              </Button>
              <Button variant="primary" onClick={handleSaveFolder}>
                {folderAction === "add" ? "สร้าง" : "บันทึก"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* File Rename Dialog */}
      {showFileRenameDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 max-w-md w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">
              Rename File
            </h3>
            <div className="space-y-4">
              <Field label="Filename">
                <Input
                  value={fileRenameName}
                  onChange={(e) => setFileRenameName(e.target.value)}
                  placeholder="Enter filename"
                  autoFocus
                />
              </Field>
            </div>
            <div className="flex gap-2 mt-6 justify-end">
              <Button variant="secondary" onClick={() => {
                setShowFileRenameDialog(false);
                setFileRenameName("");
                setFileToRename(null);
              }}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handleSaveFileRename}>
                Save
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
const FileTree2 = ({
  node,
  depth = 0,
  expanded,
  onToggle,
  onSelectFile,
  onSelectFolder,
  onEditFile,
  selectedFile,
  selectedFolder,
  parentPath = [],
  isRoot = false,
  indentSize = 20,
}) => {
  const isRootNode = node.id === "root";
  
  const FolderRow = ({ folder, open, onSelectFolder }) => {
    const isSelected = selectedFolder === folder.id;
    const paddingLeft = isRootNode ? 8 : 8 + depth * indentSize;
    
    return (
      <div
        className={`flex items-center gap-2 py-1.5 cursor-pointer hover:bg-gray-100 dark:hover:bg-[#1A2231] ${
          isSelected ? "bg-blue-50 dark:bg-blue-900/20" : ""
        }`}
        style={{ paddingLeft: `${paddingLeft}px` }}
        onClick={(e) => {
          e.stopPropagation();
          if (e.detail === 2 && onSelectFolder) {
            // Double click to edit
            onSelectFolder(folder.id, "edit");
          } else {
            onToggle(folder.id);
            if (onSelectFolder) {
              onSelectFolder(folder.id, "select");
            }
          }
        }}
      >
        {/* Expand/collapse indicator */}
        <div className="flex items-center justify-center flex-shrink-0" style={{ width: '16px' }}>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {open ? "▼" : "▶"}
          </span>
        </div>
        <span className="text-sm flex-shrink-0">{open ? "📂" : "📁"}</span>
        <span className={`text-sm flex-1 min-w-0 truncate ${isSelected ? 'font-semibold text-blue-600 dark:text-blue-400' : 'font-medium'}`}>
          {folder.name}
        </span>
      </div>
    );
  };
  
  const FileRow = ({ f, onEditFile, onSelectFile }) => {
    const selected =
      selectedFile?.name === f.name &&
      JSON.stringify(selectedFile?.path) === JSON.stringify(f.path);
    const paddingLeft = isRootNode ? 8 : 8 + (depth + 1) * indentSize;
    
    // Build tooltip content
    const tooltipContent = [
      `Uploaded by: ${f.uploader || "Unknown"}`,
      `Uploaded at: ${f.modifiedFormatted || f.modified || "Unknown"}`,
      `Size: ${f.sizeFormatted || (f.size ? `${(f.size / 1024).toFixed(1)} KB` : "Unknown")}`,
      `Type: ${f.extension ? `.${f.extension}` : "Unknown"}`
    ].join('\n');
    
    return (
      <div
        className={`flex items-center py-1.5 cursor-pointer hover:bg-gray-100 dark:hover:bg-[#1A2231] relative group ${
          selected ? "bg-blue-50 dark:bg-blue-900/20" : ""
        }`}
        style={{ paddingLeft: `${paddingLeft}px` }}
        onClick={() => {
          onSelectFile(f);
        }}
        onDoubleClick={(e) => {
          if (onEditFile) {
            e.stopPropagation();
            onEditFile(f);
          }
        }}
        title={tooltipContent}
      >
        {/* Spacer for alignment with folders */}
        <div className="flex items-center justify-center flex-shrink-0" style={{ width: '16px' }}>
          <span className="text-xs text-gray-400">•</span>
        </div>
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <span className="text-sm flex-shrink-0">📄</span>
          <span className={`text-sm truncate ${selected ? 'font-semibold text-blue-600 dark:text-blue-400' : ''}`}>
            {f.name}
          </span>
        </div>
        {/* Tooltip on hover */}
        <div className="absolute left-0 top-full mt-1 z-50 hidden group-hover:block bg-gray-900 dark:bg-gray-800 text-white text-xs rounded-lg px-3 py-2 shadow-lg whitespace-pre-line pointer-events-none" style={{ minWidth: '200px' }}>
          {tooltipContent}
        </div>
      </div>
    );
  };
  
  return (
    <div>
      {isRootNode && node.files?.length > 0 && (
        <div>
          {node.files.map((f) => (
            <FileRow
              key={f.name}
              f={{ ...f, path: [...parentPath, f.name] }}
              onEditFile={onEditFile}
              onSelectFile={onSelectFile}
            />
          ))}
        </div>
      )}
      {node.folders?.map((folder) => {
        const open = expanded.has(folder.id);
        const current = [...parentPath, folder.name];
        
        return (
          <div key={folder.id}>
            <FolderRow 
              folder={folder} 
              open={open} 
              onSelectFolder={onSelectFolder}
            />
            {open && (
              <div>
                {folder.files?.map((f) => (
                  <FileRow
                    key={f.name}
                    f={{ ...f, path: current, content: f.content }}
                    onEditFile={onEditFile}
                    onSelectFile={onSelectFile}
                  />
                ))}
                {folder.folders && folder.folders.length > 0 && (
                  <FileTree2
                    node={folder}
                    depth={depth + 1}
                    expanded={expanded}
                    onToggle={onToggle}
                    onSelectFile={onSelectFile}
                    onSelectFolder={onSelectFolder}
                    onEditFile={onEditFile}
                    selectedFile={selectedFile}
                    selectedFolder={selectedFolder}
                    parentPath={current}
                  />
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

/* ========= SETTING (with Members management + Topo uploader) ========= */
const SettingPage = ({ project, setProjects, authedUser, goIndex }) => {
  const [name, setName] = useState(project.name);
  const [desc, setDesc] = useState(project.desc || project.description || "");
  const [backupInterval, setBackupInterval] = useState(
    project.backupInterval || project.backup_interval || "Daily"
  );
  const [visibility, setVisibility] = useState(project.visibility || "Private");
  const [topoUrl, setTopoUrl] = useState(project.topoUrl || project.topo_url || "");
  const [error, setError] = useState("");
  const [members, setMembers] = useState(project.members || []);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState("");
  const [availableUsers, setAvailableUsers] = useState([]);

  // Load members, project details, and available users from backend on mount
  useEffect(() => {
    const loadData = async () => {
      try {
        const projectId = project.project_id || project.id;
        if (projectId) {
          const [membersData, projectData, usersData] = await Promise.all([
            api.getProjectMembers(projectId).catch(() => []),
            api.getProject(projectId).catch(() => null),
            api.getUsers().catch(() => [])
          ]);
          setMembers(membersData.map(m => ({ username: m.username, role: m.role })));
          setAvailableUsers(usersData);
          
          // Update project data if available
          if (projectData) {
            if (projectData.topo_url) setTopoUrl(projectData.topo_url);
            if (projectData.visibility) setVisibility(projectData.visibility);
            if (projectData.backup_interval) setBackupInterval(projectData.backup_interval);
          }
        }
      } catch (e) {
        console.error("Failed to load data:", e);
      }
    };
    loadData();
  }, [project.project_id, project.id]);

  const MAX_SIZE = 1.5 * 1024 * 1024,
    MAX_W = 1600,
    MAX_H = 900;

  const handleFile = async (file) => {
    setError("");
    if (!file) return;

    // ✅ ตรวจขนาดก่อนโหลด (เร็วกว่า base64)
    const MB = file.size / (1024 * 1024);
    if (MB > 1.5) {
      setError(`❌ ขนาดไฟล์ ${MB.toFixed(2)} MB — เกิน 1.5MB`);
      return;
    }

    const data = await fileToDataURL(file);
    const img = new Image();
    img.onload = () => {
      let { width, height } = img;
      if (width > 1600 || height > 900) {
        setError(`⚠ ขนาดรูป ${width}×${height}px เกินขอบเขต (≤1600×900)`);
      }
      setTopoUrl(data);
    };
    img.src = data;
  };

  const save = async () => {
    setError("");
    try {
      // Update project info including topoUrl, visibility, backupInterval
      await api.updateProject(project.project_id || project.id, name, desc, topoUrl, visibility, backupInterval);
      
      // Update members - sync with backend
      const currentMembers = await api.getProjectMembers(project.project_id || project.id);
      const currentUsernames = currentMembers.map(m => m.username);
      const newUsernames = members.map(m => m.username);
      
      // Remove members that are no longer in the list
      for (const currentMember of currentMembers) {
        if (!newUsernames.includes(currentMember.username)) {
          await api.removeProjectMember(project.project_id || project.id, currentMember.username);
        }
      }
      
      // Add or update members
      for (const member of members) {
        if (!currentUsernames.includes(member.username)) {
          // Add new member
          await api.addProjectMember(project.project_id || project.id, member.username, member.role);
        } else {
          // Update role if changed
          const currentMember = currentMembers.find(m => m.username === member.username);
          if (currentMember && currentMember.role !== member.role) {
            await api.updateProjectMemberRole(project.project_id || project.id, member.username, member.role);
          }
        }
      }
      
      // Reload project data
      const updatedProject = await api.getProject(project.project_id || project.id);
      const updatedMembers = await api.getProjectMembers(project.project_id || project.id);
      
      setProjects((prev) =>
        prev.map((p) => {
          if ((p.project_id || p.id) === (project.project_id || project.id)) {
            return {
              ...p,
              name: updatedProject.name,
              desc: updatedProject.description || "",
              description: updatedProject.description || "",
              members: updatedMembers.map(m => ({ username: m.username, role: m.role })),
              visibility: updatedProject.visibility || visibility,
              backupInterval: updatedProject.backup_interval || backupInterval,
              topoUrl: updatedProject.topo_url || topoUrl,
              topo_url: updatedProject.topo_url || topoUrl,
              updated_at: updatedProject.updated_at || updatedProject.created_at,
            };
          }
          return p;
        })
      );
      
      alert("✅ Project saved successfully");
    } catch (e) {
      setError("Failed to save: " + e.message);
    }
  };

  const changeRole = async (username, role) => {
    // Prevent changing admin role
    const member = members.find(m => m.username === username);
    if (member && member.role === "admin") {
      setError("Cannot change admin role in project");
      return;
    }
    try {
      await api.updateProjectMemberRole(project.project_id || project.id, username, role);
      // Update local state immediately
      const updatedMembers = members.map((m) => (m.username === username ? { ...m, role } : m));
      setMembers(updatedMembers);
      setError("");
    } catch (e) {
      // Better error handling
      let errorMessage = "Failed to update role";
      if (e && typeof e === 'object') {
        if (e.message) {
          errorMessage = e.message;
        } else if (e.detail) {
          errorMessage = e.detail;
        } else {
          try {
            errorMessage = JSON.stringify(e);
          } catch {
            errorMessage = String(e);
          }
        }
      } else if (typeof e === 'string') {
        errorMessage = e;
      }
      setError("Failed to update role: " + errorMessage);
    }
  };
  
  const remove = async (username) => {
    // Prevent removing admin
    const member = members.find(m => m.username === username);
    if (member && member.role === "admin") {
      setError("Cannot remove admin from project");
      return;
    }
    try {
      await api.removeProjectMember(project.project_id || project.id, username);
      setMembers(members.filter((m) => m.username !== username));
      setError("");
    } catch (e) {
      setError("Failed to remove member: " + e.message);
    }
  };

  const handleDeleteProject = async () => {
    if (deleteConfirm !== "Confirm Delete") {
      alert("Please type 'Confirm Delete' to proceed");
      return;
    }
    
    try {
      await api.deleteProject(project.project_id || project.id);
      setProjects(prev => prev.filter(p => (p.project_id || p.id) !== (project.project_id || project.id)));
      alert("✅ Project deleted successfully");
      goIndex();
    } catch (e) {
      setError("Failed to delete project: " + e.message);
    }
  };

  return (
    <div className="grid gap-6">
      <h2 className="text-xl font-semibold">Setting</h2>
      <Card title="Project Info">
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="Project Name">
            <Input value={name} onChange={(e) => setName(e.target.value)} />
          </Field>
          <Field label="Visibility">
            <Select
              value={visibility}
              onChange={setVisibility}
              options={[
                { value: "Private", label: "Private" },
                { value: "Shared", label: "Shared" },
              ]}
            />
          </Field>
          <Field label="Description">
            <Input value={desc} onChange={(e) => setDesc(e.target.value)} />
          </Field>
          <Field label="Backup Interval">
            <Select
              value={backupInterval}
              onChange={setBackupInterval}
              options={[
                { value: "Hourly", label: "Hourly" },
                { value: "Daily", label: "Daily" },
                { value: "Weekly", label: "Weekly" },
              ]}
            />
          </Field>
          <div className="md:col-span-2 grid gap-2">
            <Field label="Topology Image (Recommended: ≤1.5MB, 1600×900 for best display)">
              <input
                type="file"
                accept="image/*"
                onChange={(e) => handleFile(e.target.files?.[0])}
                className="block w-full text-sm text-gray-500 dark:text-gray-400
                  file:mr-4 file:py-2 file:px-4
                  file:rounded-lg file:border-0
                  file:text-sm file:font-semibold
                  file:bg-blue-50 file:text-blue-700
                  hover:file:bg-blue-100
                  dark:file:bg-blue-900 dark:file:text-blue-300
                  dark:hover:file:bg-blue-800
                  cursor-pointer"
              />
            </Field>
            {error && <div className="text-sm text-red-400">{error}</div>}
            {topoUrl && (
              <img
                src={topoUrl}
                alt="topology preview"
                className="w-full max-w-md h-48 object-contain rounded-xl border border-gray-200 dark:border-[#1F2937]"
              />
            )}
          </div>
        </div>
      </Card>

      <Card title="Members" className="overflow-hidden">
        <div className="mb-4 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
          <AddMemberInline
            members={members}
            availableUsers={availableUsers}
            onAdd={async (u, role) => {
              try {
                await api.addProjectMember(project.project_id || project.id, u, role);
                setMembers([...members, { username: u, role }]);
                setError("");
              } catch (e) {
                setError("Failed to add member: " + e.message);
              }
            }}
          />
          {error && (
            <div className="mt-3 text-sm text-rose-500 dark:text-rose-400 bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 rounded-lg px-3 py-2">
              {error}
            </div>
          )}
        </div>
        <div className="mt-4">
          <Table
            columns={[
              { 
                header: "Username", 
                key: "username",
                cell: (r) => (
                  <div className="font-medium text-gray-900 dark:text-gray-100">
                    {r.username}
                  </div>
                )
              },
              {
                header: "Role",
                key: "role",
                cell: (r) => {
                  // Prevent changing admin role - show as text instead of dropdown
                  const isAdmin = r.role === "admin";
                  if (isAdmin) {
                    return (
                      <span className="text-sm text-gray-600 dark:text-gray-400 font-medium">
                        {r.role}
                      </span>
                    );
                  }
                  return (
                    <Select
                      value={r.role}
                      onChange={(val) => {
                        changeRole(r.username, val);
                      }}
                      options={[
                        { value: "manager", label: "manager" },
                        { value: "engineer", label: "engineer" },
                        { value: "viewer", label: "viewer" },
                      ]}
                      className="min-w-[120px]"
                    />
                  );
                },
              },
              {
                header: "Actions",
                key: "x",
                cell: (r) => (
                  r.role === "admin" ? (
                    <span className="text-xs text-gray-400 dark:text-gray-500 px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded">Protected</span>
                  ) : (
                    <Button 
                      variant="danger" 
                      onClick={() => remove(r.username)}
                      className="text-sm"
                    >
                      Remove
                    </Button>
                  )
                ),
              },
            ]}
            data={members}
            empty="No members added yet"
          />
        </div>
      </Card>

      <div className="flex gap-2">
        <Button onClick={save}>Save Changes</Button>
        {authedUser?.role === "admin" && (
          <Button variant="danger" onClick={() => setShowDeleteModal(true)}>
            Delete Project
          </Button>
        )}
      </div>

      {/* Delete Project Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/50" onClick={() => setShowDeleteModal(false)} />
          <div className="relative z-10 w-full max-w-md">
            <Card title="Delete Project" actions={<Button variant="secondary" onClick={() => setShowDeleteModal(false)}>Close</Button>}>
              <div className="grid gap-4">
                <div className="text-sm text-red-600 dark:text-red-400">
                  ⚠️ This action cannot be undone. All project data will be permanently deleted.
                </div>
                
                <Field label="Type 'Confirm Delete' to proceed">
                  <Input
                    value={deleteConfirm}
                    onChange={(e) => setDeleteConfirm(e.target.value)}
                    placeholder="Confirm Delete"
                  />
                </Field>
                
                <div className="flex gap-2 justify-end">
                  <Button variant="secondary" onClick={() => setShowDeleteModal(false)}>
                    Cancel
                  </Button>
                  <Button variant="danger" onClick={handleDeleteProject}>
                    Delete Project
                  </Button>
                </div>
              </div>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
};

/* helper: inline add member row */
const AddMemberInline = ({ members, onAdd, availableUsers = [] }) => {
  const [username, setUsername] = useState("");
  const [role, setRole] = useState("viewer");
  const available = (availableUsers || []).filter(
    (u) => !members.find((m) => m.username === u.username)
  );
  
  useEffect(() => {
    if (available.length && !username) setUsername(available[0].username);
  }, [available, username]); // pick first
  return (
    <div className="flex flex-wrap items-end gap-2">
      <Field label="User">
        <Select
          value={username}
          onChange={setUsername}
          options={[
            { value: "", label: "-- Select User --" },
            ...available.map((u) => ({
              value: u.username,
              label: u.username,
            }))
          ]}
        />
      </Field>
      <Field label="Role">
        <Select
          value={role}
            onChange={setRole}
            options={[
              { value: "admin", label: "admin" },
              { value: "manager", label: "manager" },
              { value: "engineer", label: "engineer" },
              { value: "viewer", label: "viewer" },
            ]}
        />
      </Field>
      <Button onClick={() => onAdd(username, role)} disabled={!username}>
        Add
      </Button>
    </div>
  );
};

/* ========= COMMAND TEMPLATES ========= */
const CommandTemplatesPage = () => {
  const [selectedOS, setSelectedOS] = useState("cisco-ios");

  const commandTemplates = {
    "cisco-ios": {
      name: "Cisco IOS / IOS-XE / IOS-XR / NX-OS",
      commands: [
        { category: "System Information", commands: [
          "show version",
          "show inventory",
          "show running-config",
          "show startup-config",
          "show clock",
          "show uptime"
        ]},
        { category: "Interfaces", commands: [
          "show interfaces",
          "show interfaces status",
          "show interfaces description",
          "show ip interface brief",
          "show interfaces counters",
          "show interfaces transceiver",
          "show interfaces switchport"
        ]},
        { category: "VLAN", commands: [
          "show vlan",
          "show vlan brief",
          "show vlan id <vlan-id>",
          "show interfaces trunk"
        ]},
        { category: "Spanning Tree", commands: [
          "show spanning-tree",
          "show spanning-tree summary",
          "show spanning-tree detail",
          "show spanning-tree root"
        ]},
        { category: "Routing", commands: [
          "show ip route",
          "show ip route summary",
          "show ip ospf neighbor",
          "show ip ospf database",
          "show ip bgp summary",
          "show ip bgp neighbors",
          "show ip protocols"
        ]},
        { category: "HSRP/VRRP", commands: [
          "show standby",
          "show standby brief",
          "show vrrp",
          "show vrrp brief"
        ]},
        { category: "Security", commands: [
          "show port-security",
          "show ip arp inspection",
          "show dhcp snooping",
          "show access-lists"
        ]},
        { category: "Management", commands: [
          "show snmp",
          "show ntp status",
          "show logging",
          "show users"
        ]}
      ]
    },
    "huawei-vrp": {
      name: "Huawei VRP",
      commands: [
        { category: "System Information", commands: [
          "display version",
          "display device",
          "display current-configuration",
          "display saved-configuration",
          "display clock",
          "display cpu-usage"
        ]},
        { category: "Interfaces", commands: [
          "display interface",
          "display interface brief",
          "display ip interface",
          "display interface description",
          "display interface counters"
        ]},
        { category: "VLAN", commands: [
          "display vlan",
          "display vlan all",
          "display port vlan",
          "display port trunk"
        ]},
        { category: "Spanning Tree", commands: [
          "display stp",
          "display stp brief",
          "display stp root",
          "display stp region-configuration"
        ]},
        { category: "Routing", commands: [
          "display ip routing-table",
          "display ospf peer",
          "display ospf lsdb",
          "display bgp peer",
          "display ip routing-table protocol ospf"
        ]},
        { category: "VRRP", commands: [
          "display vrrp",
          "display vrrp brief",
          "display vrrp statistics"
        ]},
        { category: "Security", commands: [
          "display port-security",
          "display dhcp snooping",
          "display acl all"
        ]},
        { category: "Management", commands: [
          "display snmp-agent sys-info",
          "display ntp-service status",
          "display logbuffer",
          "display users"
        ]}
      ]
    },
    "h3c-comware": {
      name: "H3C Comware",
      commands: [
        { category: "System Information", commands: [
          "display version",
          "display device",
          "display current-configuration",
          "display saved-configuration",
          "display clock",
          "display cpu-usage"
        ]},
        { category: "Interfaces", commands: [
          "display interface",
          "display interface brief",
          "display ip interface",
          "display interface description",
          "display interface counters"
        ]},
        { category: "VLAN", commands: [
          "display vlan",
          "display vlan all",
          "display port vlan",
          "display port trunk"
        ]},
        { category: "Spanning Tree", commands: [
          "display stp",
          "display stp brief",
          "display stp root",
          "display stp region-configuration"
        ]},
        { category: "Routing", commands: [
          "display ip routing-table",
          "display ospf peer",
          "display ospf lsdb",
          "display bgp peer",
          "display ip routing-table protocol ospf"
        ]},
        { category: "VRRP", commands: [
          "display vrrp",
          "display vrrp brief",
          "display vrrp statistics"
        ]},
        { category: "Security", commands: [
          "display port-security",
          "display dhcp snooping",
          "display acl all"
        ]},
        { category: "Management", commands: [
          "display snmp-agent sys-info",
          "display ntp-service status",
          "display logbuffer",
          "display users"
        ]}
      ]
    },
    "juniper-junos": {
      name: "Juniper JunOS",
      commands: [
        { category: "System Information", commands: [
          "show version",
          "show chassis hardware",
          "show configuration",
          "show system uptime",
          "show system information"
        ]},
        { category: "Interfaces", commands: [
          "show interfaces",
          "show interfaces terse",
          "show interfaces detail",
          "show interfaces descriptions",
          "show interfaces statistics"
        ]},
        { category: "VLAN", commands: [
          "show vlans",
          "show vlans extensive",
          "show ethernet-switching table"
        ]},
        { category: "Spanning Tree", commands: [
          "show spanning-tree bridge",
          "show spanning-tree interface",
          "show spanning-tree statistics"
        ]},
        { category: "Routing", commands: [
          "show route",
          "show route summary",
          "show ospf neighbor",
          "show ospf database",
          "show bgp summary",
          "show bgp neighbor",
          "show route protocol ospf"
        ]},
        { category: "VRRP", commands: [
          "show vrrp",
          "show vrrp extensive",
          "show vrrp statistics"
        ]},
        { category: "Security", commands: [
          "show security",
          "show firewall",
          "show access-lists"
        ]},
        { category: "Management", commands: [
          "show snmp",
          "show ntp",
          "show log",
          "show system users"
        ]}
      ]
    },
    "arista-eos": {
      name: "Arista EOS",
      commands: [
        { category: "System Information", commands: [
          "show version",
          "show inventory",
          "show running-config",
          "show startup-config",
          "show clock",
          "show uptime"
        ]},
        { category: "Interfaces", commands: [
          "show interfaces",
          "show interfaces status",
          "show interfaces description",
          "show ip interface brief",
          "show interfaces counters",
          "show interfaces transceiver"
        ]},
        { category: "VLAN", commands: [
          "show vlan",
          "show vlan brief",
          "show vlan id <vlan-id>",
          "show interfaces trunk"
        ]},
        { category: "Spanning Tree", commands: [
          "show spanning-tree",
          "show spanning-tree summary",
          "show spanning-tree detail",
          "show spanning-tree root"
        ]},
        { category: "Routing", commands: [
          "show ip route",
          "show ip route summary",
          "show ip ospf neighbor",
          "show ip ospf database",
          "show ip bgp summary",
          "show ip bgp neighbors",
          "show ip protocols"
        ]},
        { category: "VRRP", commands: [
          "show vrrp",
          "show vrrp brief",
          "show vrrp statistics"
        ]},
        { category: "Security", commands: [
          "show port-security",
          "show ip arp inspection",
          "show dhcp snooping",
          "show access-lists"
        ]},
        { category: "Management", commands: [
          "show snmp",
          "show ntp status",
          "show logging",
          "show users"
        ]}
      ]
    }
  };

  const osOptions = [
    { value: "cisco-ios", label: "Cisco IOS / IOS-XE / IOS-XR / NX-OS" },
    { value: "huawei-vrp", label: "Huawei VRP" },
    { value: "h3c-comware", label: "H3C Comware" },
    { value: "juniper-junos", label: "Juniper JunOS" },
    { value: "arista-eos", label: "Arista EOS" }
  ];

  const currentTemplates = commandTemplates[selectedOS];

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text).then(() => {
      alert("Copied to clipboard!");
    });
  };

  return (
    <div className="grid gap-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Command Templates</h2>
      </div>

      <Card>
        <div className="grid gap-4">
          <Field label="Select Network OS">
            <Select
              value={selectedOS}
              onChange={setSelectedOS}
              options={osOptions}
            />
          </Field>
        </div>
      </Card>

      <Card title={currentTemplates.name}>
        <div className="grid gap-6">
          {currentTemplates.commands.map((category, idx) => (
            <div key={idx} className="border-b border-gray-200 dark:border-[#1F2937] pb-4 last:border-0">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                {category.category}
              </h3>
              <div className="grid gap-2">
                {category.commands.map((cmd, cmdIdx) => (
                  <div
                    key={cmdIdx}
                    className="flex items-center justify-between p-3 bg-gray-50 dark:bg-[#0F172A] rounded-lg border border-gray-200 dark:border-[#1F2937] hover:bg-gray-100 dark:hover:bg-[#1A2231] transition"
                  >
                    <code className="text-sm text-gray-800 dark:text-gray-200 font-mono">
                      {cmd}
                    </code>
                    <Button
                      variant="ghost"
                      className="text-xs px-3 py-1"
                      onClick={() => copyToClipboard(cmd)}
                    >
                      📋 Copy
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
};

/* ========= LOGS ========= */
const LogsPage = ({ project, uploadHistory }) => {
  const [searchLog, setSearchLog] = useState("");
  const [filterLogWho, setFilterLogWho] = useState("all");
  const [filterLogWhat, setFilterLogWhat] = useState("all");
  
  // Combine project logs with upload history
  const allHistory = [
    ...(project.logs || []).map(log => ({
      time: log.time,
      files: log.target,
      who: log.user,
      what: log.action,
      where: '—',
      when: '—',
      why: '—',
      description: '—',
      type: 'log',
      details: null,
      uploadRecord: null
    })),
    ...(uploadHistory || []).filter(upload => upload.project === project.id).map(upload => ({
      time: formatDateTime(upload.timestamp),
      files: upload.files.map(f => f.name).join(', '),
      who: upload.details?.who || upload.user,
      what: upload.details?.what || '',
      where: upload.details?.where || '',
      when: upload.details?.when || '',
      why: upload.details?.why || '',
      description: upload.details?.description || '',
      type: 'upload',
      details: upload.details,
      uploadRecord: upload
    }))
  ].sort((a, b) => new Date(b.time) - new Date(a.time));
  
  const uniqueLogWhos = [...new Set(allHistory.map(h => h.who))];
  const uniqueLogWhats = [...new Set(allHistory.map(h => h.what))];
  
  const combinedHistory = useMemo(() => {
    return allHistory.filter(log => {
      const matchSearch = !searchLog.trim() || 
        [log.files, log.who, log.what, log.where, log.description].some(v => 
          (v || "").toLowerCase().includes(searchLog.toLowerCase())
        );
      const matchWho = filterLogWho === "all" || log.who === filterLogWho;
      const matchWhat = filterLogWhat === "all" || log.what === filterLogWhat;
      return matchSearch && matchWho && matchWhat;
    });
  }, [allHistory, searchLog, filterLogWho, filterLogWhat]);

  const exportCSV = () => {
    const headers = ["Time", "Name", "Who", "What", "Where", "When", "Why", "Description"];
    const rows = combinedHistory.map(r =>
      [r.time, r.files, r.who, r.what, r.where, r.when, r.why, r.description]
        .map(v => `"${(v || "").toString().replaceAll('"','""')}"`).join(",")
    );
    downloadCSV([headers.join(","), ...rows].join("\n"), `logs_${project.name}.csv`);
  };

  return (
  <div className="grid gap-4">
    <div className="flex items-center justify-between">
      <h2 className="text-xl font-semibold">Log Updates</h2>
      <div className="flex gap-2">
        <Button variant="secondary" onClick={exportCSV}>Export CSV</Button>
      </div>
    </div>
    <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
      <Input 
        placeholder="ค้นหา (ชื่อไฟล์, ผู้ใช้, คำอธิบาย...)" 
        value={searchLog} 
        onChange={(e) => setSearchLog(e.target.value)} 
      />
      <Select 
        value={filterLogWho} 
        onChange={setFilterLogWho} 
        options={[{value: "all", label: "ทั้งหมด (Responsible User)"}, ...uniqueLogWhos.map(w => ({value: w, label: w}))]} 
      />
      <Select 
        value={filterLogWhat} 
        onChange={setFilterLogWhat} 
        options={[{value: "all", label: "ทั้งหมด (Activity Type)"}, ...uniqueLogWhats.map(w => ({value: w, label: w}))]} 
      />
    </div>
    <Table
      columns={[
        { header: "Time", key: "time" },
        { header: "Name", key: "files" },
        { header: "Responsible User", key: "who" },
        { header: "Activity Type", key: "what" },
        { header: "Site", key: "where" },
        { header: "Operational Timing", key: "when" },
        { header: "Purpose", key: "why" },
        { header: "Description", key: "description" },
        {
          header: "Action",
          key: "act",
          cell: (r) => (
            r.type === 'upload' && r.uploadRecord?.files?.[0] ? (
              <div className="flex gap-2">
                <Button 
                  variant="secondary" 
                  onClick={() => {
                    const file = r.uploadRecord.files[0];
                    if (!file) return;
                    const blob = new Blob(
                      [file.content || `# ${r.uploadRecord.type === 'config' ? 'Configuration' : 'Document'} Backup\n# File: ${file.name}\n# Uploaded: ${r.time}\n# User: ${r.who}\n\n(mock file content - actual file would be here)`],
                      { type: file.type || (r.uploadRecord.type === 'config' ? "text/plain;charset=utf-8" : "application/octet-stream") }
                    );
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = file.name || "file";
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                    URL.revokeObjectURL(url);
                  }}
                >
                  ⬇ Download
                </Button>
              </div>
            ) : "—"
          ),
        },
      ]}
      data={combinedHistory}
      empty="No logs yet"
    />
  </div>
  );
};

/* ========= HELPERS ========= */
const fileToDataURL = (file) =>
  new Promise((res, rej) => {
    const fr = new FileReader();
    fr.onload = () => res(fr.result);
    fr.onerror = rej;
    fr.readAsDataURL(file);
  });
function downloadCSV(csv, filename) {
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
/* ===== MOCK helpers for Overview Drift (UI only) ===== */
function getComparePair(project, device) {
  // UI-only: เลือก 2 ไฟล์ล่าสุด (ถ้าไม่มี ใช้ชื่อ mock)
  const hits = (project.documents?.config || [])
    .filter(f => f.name.toLowerCase().includes(device.replace(/-/g, "_")))
    .sort((a,b)=> (b.modified||"").localeCompare(a.modified||""));

  if (hits.length >= 2) return [hits[1].name, hits[0].name]; // เก่ากว่า -> ใหม่กว่า
  // fallback mock
  return ["backup-2025-09-05.txt", "backup-2025-10-01.txt"];
}

function getDriftLines(device) {
  // UI-only: สร้างตัวอย่าง diff ต่ออุปกรณ์
  const preset = {
    "core-sw1": [
      "+ Added VLAN 30 on dist-sw2",
      "~ Gi1/0/24: access → trunk",
      "− Removed logging host 10.10.1.10",
    ],
    "dist-sw2": [
      "+ Enabled port-security on Gi1/0/5",
      "− Removed VLAN 40",
      "~ NTP server 10.10.1.10 → 10.10.1.11",
    ],
    "access-sw3": [
      "~ Updated description on Gi1/0/7",
    ],
  };
  return preset[device] || ["No config changes detected"];
}
/* ===== Topology helpers & Graph (no extra libs) ===== */



// 2) กราฟอย่างง่ายด้วย SVG (จัดวางแบบวงกลม)
const TopoGraph = ({ nodes = [], links = [], getNodeTooltip, onNodeClick }) => {
  const size = { w: 780, h: 420 };
  const R = Math.min(size.w, size.h) * 0.36;
  const cx = size.w / 2, cy = size.h / 2;

  // จัดวาง: โหนดแรก (ถ้า role=Core) อยู่กลาง, ที่เหลือวางรอบวง
  const coreIdx = nodes.findIndex(n => n.role === "Core");
  const ordered = coreIdx >= 0 ? [nodes[coreIdx], ...nodes.filter((_,i)=>i!==coreIdx)] : nodes;
  const positions = {};
  ordered.forEach((n, i) => {
    if (i === 0 && n.role === "Core") {
      positions[n.id] = { x: cx, y: cy };
    } else {
      const k = (i - (ordered[0]?.role === "Core" ? 1 : 0));
      const theta = (2 * Math.PI * k) / Math.max(1, (ordered.length - (ordered[0]?.role === "Core" ? 1 : 0)));
      positions[n.id] = { x: cx + R * Math.cos(theta), y: cy + R * Math.sin(theta) };
    }
  });

  // สีโหนดตามบทบาท
  const colorByRole = (role) =>
    role === "Core" ? "#2563eb" : role === "Distribution" ? "#16a34a" : "#f59e0b";

  // tooltip state
  const [tip, setTip] = useState(null); // {x,y,text}

  return (
    <div className="relative">
      <svg viewBox={`0 0 ${size.w} ${size.h}`} className="w-full h-[360px]">
        {/* edges */}
        {links.map((l, i) => {
          const a = positions[l.source], b = positions[l.target];
          if (!a || !b) return null;
          return (
            <g key={i}>
              <line x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                    stroke={l.type === "uplink" ? "#94a3b8" : "#cbd5e1"}
                    strokeWidth={l.type === "uplink" ? 2.5 : 1.5}
                    strokeDasharray={l.type === "uplink" ? "0" : "4 3"}
              />
            </g>
          );
        })}

        {/* nodes */}
        {ordered.map((n) => {
          const p = positions[n.id];
          return (
            <g key={n.id} transform={`translate(${p.x},${p.y})`}
               onMouseEnter={(e)=>{
                 const rect = e.currentTarget.ownerSVGElement.getBoundingClientRect();
                 setTip({
                   x: (p.x / size.w) * rect.width,
                   y: (p.y / size.h) * rect.height,
                   text: getNodeTooltip ? getNodeTooltip(n.id) : n.id
                 });
               }}
               onMouseLeave={()=>setTip(null)}
               onClick={()=> onNodeClick && onNodeClick(n.id)}
               style={{cursor:"pointer"}}
            >
              <circle r={18} fill={colorByRole(n.role)} stroke="#0b1220" strokeWidth="2"></circle>
              <text y={34} textAnchor="middle" fontSize="11" fill="#cbd5e1">{n.id}</text>
            </g>
          );
        })}
      </svg>

      {/* tooltip */}
      {tip && (
        <div
          className="absolute z-10 text-xs bg-[#0F172A] text-gray-100 border border-[#1F2937] rounded-lg p-2 whitespace-pre"
          style={{ left: tip.x + 8, top: tip.y + 8, pointerEvents: "none", maxWidth: 360 }}
        >
          {tip.text}
        </div>
      )}
    </div>
  );
};







/** Simple rule-based edges for mock:
 * - connect core ↔ distribution
 * - connect core ↔ access
 * - if any interface description contains 'Uplink to core' -> connect to core
 */


/* ===== Device Image Upload Component ===== */
const DeviceImageUpload = ({ project, deviceName, authedUser, setProjects }) => {
  const [imageUrl, setImageUrl] = React.useState(null);
  const [uploading, setUploading] = React.useState(false);
  const [error, setError] = React.useState(null);
  const fileInputRef = React.useRef(null);
  
  // Check if user can edit
  const projectMember = project?.members?.find(m => m.username === authedUser?.username);
  const isManager = authedUser?.role === "admin" || projectMember?.role === "manager";
  const canEdit = isManager;
  
  // Load existing image from project state or API
  React.useEffect(() => {
    const loadImage = async () => {
      try {
        const projectId = project?.project_id || project?.id;
        // First try to get from project state (device_images)
        const deviceImages = project?.device_images || {};
        if (deviceImages[deviceName]) {
          // Check if it's PNG or JPEG based on data format
          const imageData = deviceImages[deviceName];
          const imageFormat = imageData.startsWith('/9j/') ? 'jpeg' : 'png';
          setImageUrl(`data:image/${imageFormat};base64,${imageData}`);
          return;
        }
        
        // If not in project state, try to fetch from API
        try {
          const result = await api.getDeviceImage(projectId, deviceName);
          if (result.image) {
            // Check if it's PNG or JPEG based on data format
            const imageData = result.image;
            const imageFormat = imageData.startsWith('/9j/') ? 'jpeg' : 'png';
            setImageUrl(`data:image/${imageFormat};base64,${imageData}`);
            // Update project state with fetched image
            if (setProjects) {
              setProjects(prev => prev.map(p => {
                const pId = p.project_id || p.id;
                if (pId === projectId) {
                  const updatedDeviceImages = { ...(p.device_images || {}), [deviceName]: result.image };
                  return { ...p, device_images: updatedDeviceImages };
                }
                return p;
              }));
            }
          }
        } catch (apiErr) {
          // Image not found in API, that's okay
          if (apiErr.message && !apiErr.message.includes("404")) {
            console.error("Failed to load device image from API:", apiErr);
          }
        }
      } catch (err) {
        console.error("Failed to load device image:", err);
      }
    };
    loadImage();
  }, [project, deviceName, setProjects]);
  
  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    if (!file.type.startsWith("image/")) {
      setError("Please select an image file");
      return;
    }
    
    setUploading(true);
    setError(null);
    
    try {
      const projectId = project?.project_id || project?.id;
      await api.uploadDeviceImage(projectId, deviceName, file);
      
      // Reload image from API
      const result = await api.getDeviceImage(projectId, deviceName);
      // Check if it's PNG or JPEG based on data format
      const imageData = result.image;
      const imageFormat = imageData.startsWith('/9j/') ? 'jpeg' : 'png';
      const newImageUrl = `data:image/${imageFormat};base64,${imageData}`;
      setImageUrl(newImageUrl);
      
      // Update project state with new device_images
      if (setProjects) {
        setProjects(prev => prev.map(p => {
          const pId = p.project_id || p.id;
          if (pId === projectId) {
            const deviceImages = p.device_images || {};
            return {
              ...p,
              device_images: {
                ...deviceImages,
                [deviceName]: result.image
              }
            };
          }
          return p;
        }));
      }
    } catch (err) {
      console.error("Upload failed:", err);
      setError(err.message || "Failed to upload image");
    } finally {
      setUploading(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };
  
  const handleDelete = async () => {
    if (!confirm("Delete device image?")) return;
    
    try {
      const projectId = project?.project_id || project?.id;
      await api.deleteDeviceImage(projectId, deviceName);
      setImageUrl(null);
      
      // Update project state to remove device image
      if (setProjects) {
        setProjects(prev => prev.map(p => {
          const pId = p.project_id || p.id;
          if (pId === projectId) {
            const deviceImages = { ...(p.device_images || {}) };
            delete deviceImages[deviceName];
            return {
              ...p,
              device_images: deviceImages
            };
          }
          return p;
        }));
      }
    } catch (err) {
      console.error("Delete failed:", err);
      setError(err.message || "Failed to delete image");
    }
  };
  
  return (
    <div className="space-y-3">
      {imageUrl ? (
        <div className="flex items-start gap-4">
          <img 
            src={imageUrl} 
            alt={`${deviceName} device`}
            className="w-32 h-32 object-contain border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800"
          />
          {canEdit && (
            <div className="flex flex-col gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
              >
                {uploading ? "Uploading..." : "Change Image"}
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={handleDelete}
                disabled={uploading}
              >
                Delete Image
              </Button>
            </div>
          )}
        </div>
      ) : (
        <div className="flex items-center gap-4">
          <div className="w-32 h-32 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg flex items-center justify-center bg-gray-50 dark:bg-gray-800">
            <span className="text-sm text-gray-500 dark:text-gray-400">No image</span>
          </div>
          {canEdit && (
            <Button
              variant="secondary"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
            >
              {uploading ? "Uploading..." : "Upload Image"}
            </Button>
          )}
        </div>
      )}
      {error && (
        <div className="text-sm text-rose-600 dark:text-rose-400">{error}</div>
      )}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleFileSelect}
        className="hidden"
      />
      {canEdit && (
        <div className="text-xs text-gray-500 dark:text-gray-400">
          Upload an image to replace the default device icon in topology view. Max size: 600x600px (auto-resized). PNG format recommended for transparent backgrounds.
        </div>
      )}
    </div>
  );
};

/* ===== Network Device Icon Component ===== */
const NetworkDeviceIcon = ({ role, isSelected, isLinkStart, size = 8, imageUrl = null }) => {
  // If image is provided, show image instead of SVG icon
  if (imageUrl) {
    // Make image much larger - 8x the base size for much better visibility
    const imageSize = size * 8;
    return (
      <g>
        {/* Display image directly - no background, no clipPath, preserves transparency */}
        <image
          href={imageUrl}
          x={-imageSize/2}
          y={-imageSize/2}
          width={imageSize}
          height={imageSize}
          preserveAspectRatio="xMidYMid meet"
          opacity={isSelected || isLinkStart ? 1 : 0.95}
          style={{ imageRendering: 'auto' }}
        />
        {/* Border highlight when selected - only border, no background fill */}
        {(isSelected || isLinkStart) && (
          <rect
            x={-imageSize/2 - 1}
            y={-imageSize/2 - 1}
            width={imageSize + 2}
            height={imageSize + 2}
            fill="none"
            stroke={isLinkStart ? "#10b981" : "#3b82f6"}
            strokeWidth="0.8"
            rx="3"
          />
        )}
      </g>
    );
  }
  
  // Fallback to SVG icon if no image
  const baseColor = isLinkStart ? "#10b981" : isSelected ? "#3b82f6" : "#F59E0B";
  const strokeColor = isSelected || isLinkStart ? "#ffffff" : "#0B1220";
  const strokeWidth = isSelected || isLinkStart ? "1.5" : "0.5";
  
  // Router shape (for core)
  if (role === "core") {
    return (
      <g>
        {/* Router body */}
        <rect x={-size} y={-size*0.6} width={size*2} height={size*1.2} rx={size*0.2} 
              fill={baseColor} stroke={strokeColor} strokeWidth={strokeWidth} />
        {/* Antenna lines */}
        <line x1={-size*0.8} y1={-size*0.6} x2={-size*0.8} y2={-size*0.9} 
              stroke={strokeColor} strokeWidth={strokeWidth*0.7} />
        <line x1={size*0.8} y1={-size*0.6} x2={size*0.8} y2={-size*0.9} 
              stroke={strokeColor} strokeWidth={strokeWidth*0.7} />
        {/* Port indicators */}
        <circle cx={-size*0.5} cy={size*0.3} r={size*0.15} fill={strokeColor} />
        <circle cx={0} cy={size*0.3} r={size*0.15} fill={strokeColor} />
        <circle cx={size*0.5} cy={size*0.3} r={size*0.15} fill={strokeColor} />
      </g>
    );
  }
  
  // Switch shape (for distribution/access)
  return (
    <g>
      {/* Switch body */}
      <rect x={-size} y={-size*0.5} width={size*2} height={size} rx={size*0.15} 
            fill={baseColor} stroke={strokeColor} strokeWidth={strokeWidth} />
      {/* Port rows */}
      <line x1={-size*0.7} y1={-size*0.2} x2={size*0.7} y2={-size*0.2} 
            stroke={strokeColor} strokeWidth={strokeWidth*0.5} />
      <line x1={-size*0.7} y1={0} x2={size*0.7} y2={0} 
            stroke={strokeColor} strokeWidth={strokeWidth*0.5} />
      <line x1={-size*0.7} y1={size*0.2} x2={size*0.7} y2={size*0.2} 
            stroke={strokeColor} strokeWidth={strokeWidth*0.5} />
      {/* Status indicator */}
      <circle cx={size*0.6} cy={-size*0.3} r={size*0.2} fill={strokeColor} />
    </g>
  );
};

/* ===== จัดบทบาทโดยเดาชื่อ (core/distribution/access) ===== */
function classifyRoleByName(name = "") {
  const n = (name || "").toLowerCase();
  if (n.includes("core")) return "core";
  if (n.includes("dist")) return "distribution";
  if (n.includes("access")) return "access";
  if (n.includes("router")) return "router";
  return "unknown";
}

/* ===== TopologyGraph (SVG) ===== */
const TopologyGraph = ({ project, onOpenDevice, can, authedUser, setProjects, setTopologyLLMMetrics, topologyLLMMetrics }) => {
  // Helper function for default positioning - defined first to avoid hoisting issues
  const getDefaultPos = (nodeId, role, index = 0, totalByRole = {}) => {
    const centerX = 50;
    const centerY = 50;
    
    // Normalize role to lowercase for consistent matching
    const normalizedRole = (role || "default").toLowerCase();
    
    // Count nodes by role for better distribution
    const coreCount = totalByRole.core || 0;
    const distCount = totalByRole.distribution || 0;
    const accessCount = totalByRole.access || 0;
    const routerCount = totalByRole.router || 0;
    
    switch (normalizedRole) {
      case "core": {
        // Core nodes: arrange in horizontal line at top-center
        if (coreCount <= 1) {
          return { x: centerX, y: 20 };
        }
        const coreSpacing = 25;
        const coreStartX = centerX - ((coreCount - 1) * coreSpacing) / 2;
        return { x: coreStartX + (index * coreSpacing), y: 20 };
      }
        
      case "distribution": {
        // Distribution nodes: arrange in horizontal line below core
        if (distCount <= 1) {
          return { x: centerX, y: 45 };
        }
        const distSpacing = 22;
        const distStartX = centerX - ((distCount - 1) * distSpacing) / 2;
        return { x: distStartX + (index * distSpacing), y: 45 };
      }
        
      case "access": {
        // Access nodes: arrange in two rows below distribution
        if (accessCount <= 1) {
          return { x: centerX, y: 70 };
        }
        const accessPerRow = Math.ceil(accessCount / 2);
        const accessSpacing = 20;
        const row = Math.floor(index / accessPerRow);
        const col = index % accessPerRow;
        const accessStartX = centerX - ((accessPerRow - 1) * accessSpacing) / 2;
        return { x: accessStartX + (col * accessSpacing), y: 70 + (row * 20) };
      }
        
      case "router": {
        // Router nodes: arrange at bottom
        if (routerCount <= 1) {
          return { x: centerX, y: 85 };
        }
        const routerSpacing = 20;
        const routerStartX = centerX - ((routerCount - 1) * routerSpacing) / 2;
        return { x: routerStartX + (index * routerSpacing), y: 85 };
      }
        
      default: {
        // Default: arrange in grid
        const defaultSpacing = 15;
        const defaultTotal = totalByRole.default || totalByRole[normalizedRole] || 1;
        const defaultCols = Math.ceil(Math.sqrt(defaultTotal));
        const row = Math.floor(index / defaultCols);
        const col = index % defaultCols;
        return { x: 20 + (col * defaultSpacing), y: 20 + (row * defaultSpacing) };
      }
    }
  };

  const [generatingTopology, setGeneratingTopology] = React.useState(false);
  const [topologyError, setTopologyError] = React.useState(null);
  
  const rows = project.summaryRows || [];
  // Base nodes from project summary rows - compute first
  const baseNodes = rows.map(r => ({
    id: r.device,
    label: r.device,
    role: classifyRoleByName(r.device),
    type: classifyRoleByName(r.device), // For compatibility with AI-generated topology
    model: r.model, mgmtIp: r.mgmtIp,
    routing: r.routing, stpMode: r.stpMode
  }));
  
  // Topology nodes state - will be updated when topology is generated
  const [topologyNodes, setTopologyNodes] = useState(() => {
    // Initialize from project.topoNodes if available, otherwise compute baseNodes inline
    if (project.topoNodes && project.topoNodes.length > 0) {
      return project.topoNodes.map(n => ({
        id: n.id || n.device_id,
        label: n.label || n.id || n.device_id,
        role: (n.type || n.role || "access")?.toLowerCase(),
        type: n.type || "Switch",
        model: n.model,
        mgmtIp: n.ip || n.management_ip,
        routing: n.routing,
        stpMode: n.stpMode
      }));
    }
    // Compute baseNodes inline for useState initializer
    const summaryRows = project.summaryRows || [];
    return summaryRows.map(r => ({
      id: r.device,
      label: r.device,
      role: classifyRoleByName(r.device),
      type: classifyRoleByName(r.device),
      model: r.model, mgmtIp: r.mgmtIp,
      routing: r.routing, stpMode: r.stpMode
    }));
  });
  
  // Use topology nodes if available, otherwise use base nodes
  const nodes = topologyNodes.length > 0 ? topologyNodes : baseNodes;

  // Check if user is manager in this project
  const projectMember = project?.members?.find(m => m.username === authedUser?.username);
  const isManager = authedUser?.role === "admin" || projectMember?.role === "manager";
  const canEdit = isManager && can("project-setting", project);

  const [editMode, setEditMode] = useState(false);
  
  // Zoom and Pan state
  const [zoom, setZoom] = useState(1.0);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });
  
  const [positions, setPositions] = useState(() => {
    if (project.topoPositions) {
      return project.topoPositions;
    }
    const pos = {};
    // Count nodes by role for better distribution - compute baseNodes inline
    const summaryRows = project.summaryRows || [];
    const initialNodes = summaryRows.map(r => ({
      id: r.device,
      label: r.device,
      role: classifyRoleByName(r.device),
      type: classifyRoleByName(r.device),
      model: r.model, mgmtIp: r.mgmtIp,
      routing: r.routing, stpMode: r.stpMode
    }));
    const roleCounts = {};
    const roleIndices = {};
    initialNodes.forEach(n => {
      const role = (n.role || "default").toLowerCase();
      roleCounts[role] = (roleCounts[role] || 0) + 1;
    });
    // Use initialNodes for positioning
    initialNodes.forEach(n => {
      const role = (n.role || "default").toLowerCase();
      roleIndices[role] = (roleIndices[role] || 0);
      pos[n.id] = getDefaultPos(n.id, role, roleIndices[role], roleCounts);
      roleIndices[role]++;
    });
    return pos;
  });

  const [links, setLinks] = useState(() => {
    if (project.topoLinks) {
      return project.topoLinks;
    }
    return deriveLinksFromProject(project);
  });
  
  // Load topology layout from backend on mount
  React.useEffect(() => {
    const loadTopologyLayout = async () => {
      const projectId = project.project_id || project.id;
      if (!projectId) return;
      
      try {
        const topologyData = await api.getTopology(projectId);
        if (topologyData.layout) {
          if (topologyData.layout.positions && Object.keys(topologyData.layout.positions).length > 0) {
            setPositions(topologyData.layout.positions);
          }
          if (topologyData.layout.links && topologyData.layout.links.length > 0) {
            setLinks(topologyData.layout.links);
          }
          if (topologyData.layout.node_labels) {
            setNodeLabels(topologyData.layout.node_labels);
          }
          if (topologyData.layout.node_roles) {
            setNodeRoles(topologyData.layout.node_roles);
          }
        }
        // Load LLM metrics from database if available
        if (topologyData.llm_metrics) {
          setTopologyLLMMetrics(topologyData.llm_metrics);
        }
        // Store last modified date if available
        if (topologyData.updated_at || topologyData.last_modified) {
          setProjects(prev => prev.map(p => {
            if ((p.project_id || p.id) === projectId) {
              return { ...p, topoUpdatedAt: topologyData.updated_at || topologyData.last_modified };
            }
            return p;
          }));
        }
      } catch (error) {
        console.error("Failed to load topology layout:", error);
        // Fallback to project data (already set in useState)
      }
    };
    
    loadTopologyLayout();
  }, [project.project_id || project.id]);
  
  // Generate topology using AI
  const handleGenerateTopology = async () => {
    const projectId = project.project_id || project.id;
    if (!projectId) {
      setTopologyError("Project ID not found");
      return;
    }
    
    setGeneratingTopology(true);
    setTopologyError(null);
    
    try {
      const result = await api.generateTopology(projectId);
      
      // Check for errors first
      if (result.analysis_summary && result.analysis_summary.includes("[ERROR]")) {
        setTopologyError(result.analysis_summary);
        return;
      }
      
      if (result.topology && result.topology.nodes && result.topology.edges) {
        // Convert AI-generated topology to internal format
        const aiNodes = result.topology.nodes || [];
        const aiEdges = result.topology.edges || [];
        
        console.log("[Topology] LLM Response:", {
          nodes: aiNodes,
          edges: aiEdges,
          analysis_summary: result.analysis_summary,
          metrics: result.metrics
        });
        
        // Store LLM metrics for display (if setter provided)
        if (result.metrics && setTopologyLLMMetrics) {
          setTopologyLLMMetrics(result.metrics);
        }
        
        if (aiNodes.length === 0 && aiEdges.length === 0) {
          setTopologyError("ไม่พบข้อมูล topology จาก AI. กรุณาตรวจสอบว่า Ollama ทำงานอยู่และมีข้อมูล devices ใน project");
          return;
        }
        
        // Convert AI nodes to internal format and merge with existing
        const nodeMap = new Map();
        // First, add all existing nodes (from topologyNodes or baseNodes)
        const currentNodes = topologyNodes.length > 0 ? topologyNodes : baseNodes;
        currentNodes.forEach(n => {
          nodeMap.set(n.id, { ...n });
        });
        // Then, update/add AI nodes
        aiNodes.forEach(aiNode => {
          const nodeId = aiNode.id;
          const existingNode = nodeMap.get(nodeId);
          if (existingNode) {
            // Update existing node
            nodeMap.set(nodeId, {
              ...existingNode,
              label: aiNode.label || existingNode.label,
              role: (aiNode.type || existingNode.role)?.toLowerCase() || existingNode.role,
              type: aiNode.type || existingNode.type
            });
          } else {
            // Add new node from AI
            nodeMap.set(nodeId, {
              id: nodeId,
              label: aiNode.label || nodeId,
              role: (aiNode.type || "access")?.toLowerCase(),
              type: aiNode.type || "Switch",
              model: aiNode.model,
              mgmtIp: aiNode.ip || aiNode.management_ip
            });
          }
        });
        
        const updatedNodes = Array.from(nodeMap.values());
        
        // Convert edges to internal format (a/b instead of from/to)
        const convertedEdges = aiEdges.map(edge => ({
          a: edge.from,
          b: edge.to,
          label: edge.label || "",
          evidence: edge.evidence || "",
          type: "trunk" // Default type
        }));
        
        // Create default positions for new nodes with better distribution
        const updatedPositions = { ...positions };
        
        // Count nodes by role for better distribution
        const roleCounts = {};
        const roleIndices = {};
        updatedNodes.forEach(node => {
          const role = (node.role || "default").toLowerCase();
          roleCounts[role] = (roleCounts[role] || 0) + 1;
        });
        
        updatedNodes.forEach((node, idx) => {
          if (!updatedPositions[node.id]) {
            // Assign default position based on role with index
            const role = (node.role || "access").toLowerCase();
            roleIndices[role] = (roleIndices[role] || 0);
            updatedPositions[node.id] = getDefaultPos(node.id, role, roleIndices[role], roleCounts);
            roleIndices[role]++;
          }
        });
        
        // Update states
        setTopologyNodes(updatedNodes);
        setLinks(convertedEdges);
        setPositions(updatedPositions);
        
        // Update project state (will be saved when user clicks Save)
        setProjects(prev => prev.map(p => {
          if (p.id === project.id) {
            return {
              ...p,
              topoLinks: convertedEdges,
              topoNodes: aiNodes,
              topoPositions: updatedPositions
            };
          }
          return p;
        }));
        
        // Show success message
        alert(`✅ Topology generated successfully!\n\n${result.analysis_summary || `Found ${aiNodes.length} nodes and ${convertedEdges.length} links.`}\n\nClick "แก้ไขกราฟ" แล้ว "บันทึก" to save the topology.`);
      } else {
        setTopologyError(result.analysis_summary || "Failed to generate topology. No topology data returned.");
      }
    } catch (error) {
      console.error("Failed to generate topology:", error);
      setTopologyError(error.message || "Failed to generate topology");
    } finally {
      setGeneratingTopology(false);
    }
  };

  const [dragging, setDragging] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [linkStart, setLinkStart] = useState(null);
  const [selectedLink, setSelectedLink] = useState(null);
  const [showLinkDialog, setShowLinkDialog] = useState(false);
  const [showNodeDialog, setShowNodeDialog] = useState(false);
  const [editingNode, setEditingNode] = useState(null);
  const [linkTooltip, setLinkTooltip] = useState(null); // {x, y, text} for link hover
  const [nodeLabels, setNodeLabels] = useState(() => {
    if (project.topoNodeLabels) {
      return project.topoNodeLabels;
    }
    const labels = {};
    // Use baseNodes initially
    baseNodes.forEach(n => {
      labels[n.id] = n.label;
    });
    return labels;
  });
  const [nodeRoles, setNodeRoles] = useState(() => {
    if (project.topoNodeRoles) {
      return project.topoNodeRoles;
    }
    const roles = {};
    // Use baseNodes initially
    baseNodes.forEach(n => {
      roles[n.id] = n.role;
    });
    return roles;
  });
  const [linkMode, setLinkMode] = useState("none"); // "none", "add", "edit"
  const [reroutingLink, setReroutingLink] = useState(null); // For re-routing link connectors
  
  // Load topology layout from backend on mount
  // Handle zoom
  const handleZoomIn = () => {
    setZoom(prev => Math.min(prev + 0.2, 3.0));
  };
  
  const handleZoomOut = () => {
    setZoom(prev => Math.max(prev - 0.2, 0.5));
  };
  
  const handleZoomReset = () => {
    setZoom(1.0);
    setPan({ x: 0, y: 0 });
  };
  
  // Handle pan (drag background) - works in both edit and view mode
  const handlePanStart = (e) => {
    // Don't pan if already dragging a node or starting a link
    if (dragging || linkStart || e.button !== 0) return;
    
    // Check if clicking on empty space (SVG background, pan area rect, or line, not on nodes)
    const target = e.target;
    const isClickingEmptySpace = target.tagName === 'svg' || 
                                  target.tagName === 'line' ||
                                  (target.classList && target.classList.contains('pan-area')) ||
                                  (target.tagName === 'rect' && target.getAttribute('fill') === 'transparent');
    
    if (editMode) {
      // In edit mode: Ctrl/Shift/Cmd+drag or drag empty space (but not on nodes)
      if (e.ctrlKey || e.metaKey || e.shiftKey || isClickingEmptySpace) {
        setIsPanning(true);
        setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
        e.preventDefault();
        e.stopPropagation();
      }
    } else {
      // In view mode: always allow panning on empty space (SVG background, pan area, or lines)
      if (isClickingEmptySpace) {
        setIsPanning(true);
        setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
        e.preventDefault();
        e.stopPropagation();
      }
    }
  };
  
  const handlePanMove = (e) => {
    if (isPanning) {
      // Reduce panning speed by dividing by 1.5
      setPan({
        x: (e.clientX - panStart.x) / 1.5,
        y: (e.clientY - panStart.y) / 1.5
      });
    }
  };
  
  const handlePanEnd = () => {
    setIsPanning(false);
  };
  
  // Handle node drag
  const handleMouseDown = (nodeId, e) => {
    if (!editMode) {
      if (!e.ctrlKey && !e.metaKey) {
        onOpenDevice?.(nodeId);
      }
      return;
    }
    
    // In edit mode: Check if panning with modifier keys
    if (editMode && (e.ctrlKey || e.metaKey || e.shiftKey)) {
      handlePanStart(e);
      return;
    }
    
    // Don't start dragging if we're panning
    if (isPanning) {
      return;
    }
    
    e.stopPropagation();
    setDragging(nodeId);
    setSelectedNode(nodeId);
  };

  const handleMouseMove = (e) => {
    // Handle panning
    if (isPanning) {
      handlePanMove(e);
      return;
    }
    
    // Handle node dragging
    if (!dragging || !editMode) return;
    const svg = e.currentTarget;
    const rect = svg.getBoundingClientRect();
    const viewBox = svg.viewBox.baseVal;
    
    // Calculate position accounting for zoom and pan
    const x = ((e.clientX - rect.left) / rect.width) * viewBox.width / zoom - pan.x / zoom;
    const y = ((e.clientY - rect.top) / rect.height) * viewBox.height / zoom - pan.y / zoom;
    
    setPositions(prev => ({
      ...prev,
      [dragging]: { x, y } // No position limits - allow free dragging
    }));
  };

  const handleMouseUp = () => {
    setDragging(null);
    handlePanEnd();
  };
  
  // Handle wheel zoom - works in both edit and view mode
  const handleWheel = (e) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    setZoom(prev => Math.max(0.5, Math.min(3.0, prev + delta)));
  };

  // Handle link creation and re-routing
  const handleNodeClick = (nodeId, e) => {
    if (!editMode) return;
    e.stopPropagation();
    
    // Re-route link connector mode
    if (reroutingLink !== null) {
      const linkIndex = reroutingLink;
      const link = links[linkIndex];
      
      // Determine which end to re-route (closest to clicked node)
      const posA = getPos(link.a);
      const posB = getPos(link.b);
      const posNode = getPos(nodeId);
      
      const distToA = Math.sqrt(Math.pow(posNode.x - posA.x, 2) + Math.pow(posNode.y - posA.y, 2));
      const distToB = Math.sqrt(Math.pow(posNode.x - posB.x, 2) + Math.pow(posNode.y - posB.y, 2));
      
      // Re-route the closer end
      setLinks(prev => prev.map((l, i) => {
        if (i === linkIndex) {
          if (distToA < distToB) {
            return { ...l, a: nodeId };
          } else {
            return { ...l, b: nodeId };
          }
        }
        return l;
      }));
      
      setReroutingLink(null);
      setSelectedLink(null);
      return;
    }
    
    if (linkMode === "add") {
      if (linkStart === null) {
        setLinkStart(nodeId);
        setSelectedNode(nodeId);
      } else if (linkStart !== nodeId) {
        // Create link if it doesn't exist
        const linkExists = links.some(l => 
          (l.a === linkStart && l.b === nodeId) || (l.a === nodeId && l.b === linkStart)
        );
        if (!linkExists) {
          setLinks(prev => [...prev, { a: linkStart, b: nodeId, type: "trunk", label: "" }]);
        }
        setLinkStart(null);
        setSelectedNode(null);
        setLinkMode("none");
      } else {
        setLinkStart(null);
        setSelectedNode(null);
        setLinkMode("none");
      }
    } else if (linkMode === "edit") {
      // In edit mode, clicking node opens edit dialog
      const node = nodes.find(n => n.id === nodeId);
      if (node) {
        setEditingNode(nodeId);
        setShowNodeDialog(true);
      }
    } else {
      setSelectedNode(nodeId);
      setLinkStart(null);
    }
  };

  // Handle node double-click to edit
  const handleNodeDoubleClick = (nodeId, e) => {
    if (!editMode || linkMode !== "none") return;
    e.stopPropagation();
    const node = nodes.find(n => n.id === nodeId);
    if (node) {
      setEditingNode(nodeId);
      setShowNodeDialog(true);
    }
  };

  // Handle link click
  const handleLinkClick = (linkIndex, e) => {
    if (!editMode) return;
    e.stopPropagation();
    
    if (linkMode === "edit") {
      setSelectedLink(linkIndex);
      setShowLinkDialog(true);
    } else if (reroutingLink === linkIndex) {
      // Cancel re-routing
      setReroutingLink(null);
      setSelectedLink(null);
    }
  };
  
  // Start re-routing link connector
  const startRerouteLink = (linkIndex) => {
    setReroutingLink(linkIndex);
    setSelectedLink(linkIndex);
    setLinkMode("none");
  };

  // Handle link deletion
  const handleLinkDelete = (linkIndex, e) => {
    if (!editMode) return;
    e.preventDefault();
    e.stopPropagation();
    setLinks(prev => prev.filter((_, i) => i !== linkIndex));
    setSelectedLink(null);
  };

  // Start add link mode
  const startAddLink = () => {
    setLinkMode("add");
    setSelectedNode(null);
    setLinkStart(null);
  };

  // Cancel link mode
  const cancelLinkMode = () => {
    setLinkMode("none");
    setLinkStart(null);
    setSelectedNode(null);
  };

  // Save node changes
  const handleSaveNode = () => {
    if (editingNode) {
      // Update node labels and roles in project
      setProjects(prev => prev.map(p => {
        if (p.id === project.id) {
          const updatedRows = (p.summaryRows || []).map(row => {
            if (row.device === editingNode) {
              return {
                ...row,
                device: nodeLabels[editingNode] || row.device,
                // Note: role is derived from name, so we might need to update the device name
              };
            }
            return row;
          });
          return { ...p, summaryRows: updatedRows };
        }
        return p;
      }));
    }
    setShowNodeDialog(false);
    setEditingNode(null);
  };

  // Save topology
  const handleSave = async () => {
    const projectId = project.project_id || project.id;
    if (!projectId) {
      alert("❌ Project ID not found");
      return;
    }
    
    try {
      // Save to backend
      await api.saveTopologyLayout(projectId, positions, links, nodeLabels, nodeRoles);
      
      // Update local state with current timestamp
      const now = new Date().toISOString();
      setProjects(prev => prev.map(p => 
        p.id === project.id 
          ? { ...p, topoPositions: positions, topoLinks: links, topoNodeLabels: nodeLabels, topoNodeRoles: nodeRoles, topoUpdatedAt: now }
          : p
      ));
      
      setEditMode(false);
      setLinkStart(null);
      setSelectedNode(null);
      setLinkMode("none");
      setSelectedLink(null);
      
      alert("✅ บันทึกตำแหน่ง topology สำเร็จ");
    } catch (error) {
      console.error("Failed to save topology layout:", error);
      alert(`❌ ไม่สามารถบันทึกได้: ${error.message}`);
    }
  };

  // Cancel edit
  const handleCancel = () => {
    // Reset positions
    if (project.topoPositions) {
      setPositions(project.topoPositions);
    } else {
      const pos = {};
      // Count nodes by role for better distribution
      const roleCounts = {};
      const roleIndices = {};
      nodes.forEach(n => {
        const role = (n.role || "default").toLowerCase();
        roleCounts[role] = (roleCounts[role] || 0) + 1;
      });
      nodes.forEach(n => {
        const role = (n.role || "default").toLowerCase();
        roleIndices[role] = (roleIndices[role] || 0);
        pos[n.id] = getDefaultPos(n.id, role, roleIndices[role], roleCounts);
        roleIndices[role]++;
      });
      setPositions(pos);
    }
    
    // Reset links
    if (project.topoLinks) {
      setLinks(project.topoLinks);
    } else {
      setLinks(deriveLinksFromProject(project));
    }
    
    // Reset node labels and roles
    if (project.topoNodeLabels) {
      setNodeLabels(project.topoNodeLabels);
    } else {
      const labels = {};
      nodes.forEach(n => {
        labels[n.id] = n.label;
      });
      setNodeLabels(labels);
    }
    
    if (project.topoNodeRoles) {
      setNodeRoles(project.topoNodeRoles);
    } else {
      const roles = {};
      nodes.forEach(n => {
        roles[n.id] = n.role;
      });
      setNodeRoles(roles);
    }
    
    // Reset all states
    setEditMode(false);
    setLinkStart(null);
    setSelectedNode(null);
    setLinkMode("none");
    setSelectedLink(null);
    setReroutingLink(null);
    setZoom(1.0);
    setPan({ x: 0, y: 0 });
  };

  const getPos = id => positions[id] || { x: 50, y: 50 };
  const getNodeName = id => nodeLabels[id] || nodes.find(n => n.id === id)?.label || id;
  const getNodeRole = id => nodeRoles[id] || nodes.find(n => n.id === id)?.role || "access";

  // Get last modified date from project or topology data
  const lastModified = project.topoUpdatedAt || project.updated_at || project.updated || null;
  const formatShortDate = (dateStr) => {
    if (!dateStr) return null;
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('th-TH', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch {
      return dateStr.split(' ')[0] || dateStr;
    }
  };

  return (
    <Card 
      title={
        <div className="flex items-center justify-between w-full py-1 gap-2">
          <span className="text-xs font-medium text-slate-300 flex-shrink-0">Topology</span>
          <div className="flex items-center gap-2 flex-1 justify-end min-w-0">
            {/* LLM info and last modified - larger format */}
            {topologyLLMMetrics && (
              <span className="text-[10px] text-slate-400 whitespace-nowrap">
                {topologyLLMMetrics.model_name?.split(':')[0] || '—'} | {topologyLLMMetrics.inference_time_ms ? `${(topologyLLMMetrics.inference_time_ms / 1000).toFixed(1)}s` : '—'}
              </span>
            )}
            {lastModified && (
              <span className="text-[10px] text-slate-400 whitespace-nowrap">
                {formatShortDate(lastModified)}
              </span>
            )}
            {/* Action buttons - larger and clearer */}
            <div className="flex gap-1 items-center flex-shrink-0">
              {!editMode && (
                <button
                  className="w-6 h-6 flex items-center justify-center rounded bg-blue-600 hover:bg-blue-700 text-white text-xs transition-colors disabled:opacity-50"
                  onClick={handleGenerateTopology}
                  disabled={generatingTopology}
                  title={generatingTopology ? "Generating..." : "Generate Topology"}
                >
                  {generatingTopology ? "⏳" : "🤖"}
                </button>
              )}
              {canEdit && (
                <>
                  {!editMode ? (
                    <button
                      className="w-6 h-6 flex items-center justify-center rounded border border-slate-600 hover:bg-slate-700 text-slate-300 text-xs transition-colors"
                      onClick={() => setEditMode(true)}
                      title="Edit Graph"
                    >
                      ✏️
                    </button>
                  ) : (
                    <>
                      <button
                        className="w-6 h-6 flex items-center justify-center rounded border border-slate-600 hover:bg-slate-700 text-slate-300 text-xs transition-colors"
                        onClick={handleCancel}
                        title="Cancel"
                      >
                        ✕
                      </button>
                      <button
                        className="w-6 h-6 flex items-center justify-center rounded bg-blue-600 hover:bg-blue-700 text-white text-xs transition-colors"
                        onClick={handleSave}
                        title="Save Layout"
                      >
                        ✓
                      </button>
                    </>
                  )}
                </>
              )}
              {/* Zoom controls - larger and clearer */}
              <div className="flex gap-1 ml-1 border-l border-slate-700 pl-1">
                <button
                  className="w-6 h-6 flex items-center justify-center rounded border border-slate-600 hover:bg-slate-700 text-slate-300 text-xs transition-colors"
                  onClick={handleZoomIn}
                  title="Zoom In"
                >
                  +
                </button>
                <button
                  className="w-6 h-6 flex items-center justify-center rounded border border-slate-600 hover:bg-slate-700 text-slate-300 text-xs transition-colors"
                  onClick={handleZoomOut}
                  title="Zoom Out"
                >
                  −
                </button>
                <button
                  className="w-6 h-6 flex items-center justify-center rounded border border-slate-600 hover:bg-slate-700 text-slate-300 text-xs transition-colors"
                  onClick={handleZoomReset}
                  title="Reset View"
                >
                  ↻
                </button>
              </div>
            </div>
          </div>
        </div>
      } 
      className="w-full"
      compact={true}
    >
      {topologyError && (
        <div className="mb-3 p-3 bg-rose-50 dark:bg-rose-900/20 border border-rose-300 dark:border-rose-700 rounded-lg">
          <div className="text-sm text-rose-700 dark:text-rose-400 whitespace-pre-line">
            <strong>⚠️ Error:</strong> {topologyError}
          </div>
        </div>
      )}
      {editMode && (
        <div className="mb-2 px-2 py-1 bg-gray-50 dark:bg-gray-800 rounded">
          <div className="flex items-center gap-1.5 flex-wrap">
            <Button 
              variant={linkMode === "add" ? "primary" : "secondary"} 
              className="text-[10px] px-2 py-0.5 h-6"
              onClick={linkMode === "add" ? cancelLinkMode : startAddLink}
            >
              {linkMode === "add" ? "Cancel" : "Add Link"}
            </Button>
            <Button 
              variant={linkMode === "edit" ? "primary" : "secondary"} 
              className="text-[10px] px-2 py-0.5 h-6"
              onClick={() => {
                setLinkMode(linkMode === "edit" ? "none" : "edit");
                setReroutingLink(null);
              }}
            >
              {linkMode === "edit" ? "Cancel" : "Edit"}
            </Button>
            {selectedLink !== null && linkMode === "edit" && (
              <Button 
                variant={reroutingLink === selectedLink ? "primary" : "secondary"} 
                className="text-[10px] px-2 py-0.5 h-6"
                onClick={() => {
                  if (reroutingLink === selectedLink) {
                    setReroutingLink(null);
                  } else {
                    startRerouteLink(selectedLink);
                  }
                }}
              >
                {reroutingLink === selectedLink ? "Cancel" : "Reroute"}
              </Button>
            )}
          </div>
        </div>
      )}
      <div className="relative h-[calc(100vh-380px)] min-h-[450px] rounded-xl bg-[#0B1220] overflow-hidden">
        <svg 
          viewBox="0 0 100 100" 
          className="w-full h-full"
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onMouseDown={handlePanStart}
          onWheel={handleWheel}
          style={{
            cursor: isPanning ? 'grabbing' : (!dragging ? 'grab' : 'default')
          }}
        >
          <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
          {/* Background pan area - unlimited size for dragging */}
          <rect 
            x="-10000" y="-10000" 
            width="20000" height="20000" 
            fill="transparent" 
            className="pan-area"
            onMouseDown={handlePanStart}
            style={{ cursor: isPanning ? 'grabbing' : (!dragging ? 'grab' : 'default'), pointerEvents: 'all' }}
          />
          {/* edges */}
          {links.map((e, i) => {
            const A = getPos(e.a), B = getPos(e.b);
            const isSelected = selectedLink === i;
            const isRerouting = reroutingLink === i;
            const midX = (A.x + B.x) / 2;
            const midY = (A.y + B.y) / 2;
            const linkLabel = e.label || e.evidence || "";
            return (
              <g key={i}>
                <line 
                  x1={A.x} y1={A.y} x2={B.x} y2={B.y}
                  stroke={isRerouting ? "#f59e0b" : (isSelected ? "#10b981" : "#5DA0FF")} 
                  strokeWidth={editMode ? (isSelected || isRerouting ? "1.5" : "1.2") : "1.0"} 
                  strokeDasharray={isRerouting ? "3,3" : "none"}
                  opacity={isRerouting ? "1" : "0.85"}
                  onClick={(evt) => handleLinkClick(i, evt)}
                  onContextMenu={(evt) => handleLinkDelete(i, evt)}
                  onMouseEnter={(evt) => {
                    if (linkLabel) {
                      const svg = evt.currentTarget.ownerSVGElement;
                      const rect = svg.getBoundingClientRect();
                      const viewBox = svg.viewBox.baseVal;
                      const xPercent = (midX / viewBox.width) * 100;
                      const yPercent = (midY / viewBox.height) * 100;
                      setLinkTooltip({
                        x: (xPercent / 100) * rect.width,
                        y: (yPercent / 100) * rect.height,
                        text: linkLabel
                      });
                    }
                  }}
                  onMouseLeave={() => setLinkTooltip(null)}
                  className={editMode ? "cursor-pointer" : (linkLabel ? "cursor-help" : "")}
                />
                {editMode && (
                  <line 
                    x1={A.x} y1={A.y} x2={B.x} y2={B.y}
                    stroke="transparent" 
                    strokeWidth="8"
                    onClick={(evt) => handleLinkClick(i, evt)}
                    onContextMenu={(evt) => handleLinkDelete(i, evt)}
                    className="cursor-pointer"
                  />
                )}
              </g>
            );
          })}
          {/* nodes */}
          {nodes.map((n) => {
            const p = getPos(n.id);
            const isSelected = selectedNode === n.id;
            const isLinkStart = linkStart === n.id;
            const deviceSize = editMode ? (isSelected || isLinkStart ? 5 : 4) : 3.5;
            
            // Get device image if available
            const deviceImages = project?.device_images || {};
            const deviceImageBase64 = deviceImages[n.id];
            // Detect format: PNG starts with iVBOR, JPEG starts with /9j/
            let deviceImageUrl = null;
            if (deviceImageBase64) {
              const imageFormat = deviceImageBase64.startsWith('iVBOR') ? 'png' : 'jpeg';
              deviceImageUrl = `data:image/${imageFormat};base64,${deviceImageBase64}`;
            }
            
            return (
              <g 
                key={n.id}
                transform={`translate(${p.x}, ${p.y})`}
                onMouseDown={(e) => handleMouseDown(n.id, e)}
                onClick={(e) => handleNodeClick(n.id, e)}
                onDoubleClick={(e) => handleNodeDoubleClick(n.id, e)}
                className={editMode && linkMode !== "add" ? "cursor-move" : "cursor-pointer"}
              >
                <NetworkDeviceIcon 
                  role={getNodeRole(n.id)} 
                  isSelected={isSelected}
                  isLinkStart={isLinkStart}
                  size={deviceSize}
                  imageUrl={deviceImageUrl}
                />
                <text 
                  x={0} 
                  y={deviceSize + 3} 
                  fontSize="2.4" 
                  fill="#C7D2FE"
                  textAnchor="middle"
                  pointerEvents="none"
                  className="select-none"
                >
                  {getNodeName(n.id)}
                </text>
                {/* hover tooltip */}
                <title>{`Role: ${n.role || "-"} • Model: ${n.model || "-"} • Mgmt: ${n.mgmtIp || "-"} • Routing: ${n.routing || "-"} • STP: ${n.stpMode || "-"}`}</title>
              </g>
            );
          })}
          </g>
        </svg>
        {/* Link tooltip */}
        {linkTooltip && (
          <div
            className="absolute z-10 text-xs bg-[#0F172A] text-gray-100 border border-[#1F2937] rounded-lg p-2 whitespace-pre"
            style={{ 
              left: linkTooltip.x + 8, 
              top: linkTooltip.y + 8, 
              pointerEvents: "none", 
              maxWidth: 360 
            }}
          >
            {linkTooltip.text}
          </div>
        )}
        <div className="absolute top-2 right-2 text-[10px] text-gray-500 dark:text-gray-400 bg-black/30 px-2 py-1 rounded">
          Zoom: {(zoom * 100).toFixed(0)}%
        </div>
      </div>

      {/* Link Edit Dialog */}
      {showLinkDialog && selectedLink !== null && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 max-w-md w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">
              แก้ไขลิงก์
            </h3>
            <div className="space-y-4">
              <div>
                <span className="text-sm text-gray-600 dark:text-gray-400">จาก:</span>
                <span className="ml-2 font-medium text-gray-900 dark:text-gray-100">
                  {getNodeName(links[selectedLink].a)}
                </span>
              </div>
              <div>
                <span className="text-sm text-gray-600 dark:text-gray-400">ไปยัง:</span>
                <span className="ml-2 font-medium text-gray-900 dark:text-gray-100">
                  {getNodeName(links[selectedLink].b)}
                </span>
              </div>
              <Field label="ประเภทลิงก์">
                <Select
                  value={links[selectedLink].type || "trunk"}
                  onChange={(value) => {
                    setLinks(prev => prev.map((l, i) => 
                      i === selectedLink ? { ...l, type: value } : l
                    ));
                  }}
                  options={[
                    { value: "trunk", label: "Trunk" },
                    { value: "access", label: "Access" },
                    { value: "uplink", label: "Uplink" }
                  ]}
                />
              </Field>
              <Field label="ป้ายกำกับ (ไม่บังคับ)">
                <Input
                  value={links[selectedLink].label || ""}
                  onChange={(e) => {
                    setLinks(prev => prev.map((l, i) => 
                      i === selectedLink ? { ...l, label: e.target.value } : l
                    ));
                  }}
                  placeholder="เช่น GigabitEthernet0/1"
                />
              </Field>
            </div>
            <div className="flex gap-2 mt-6 justify-end">
              <Button variant="secondary" onClick={() => {
                setShowLinkDialog(false);
                setSelectedLink(null);
              }}>
                ปิด
              </Button>
              <Button variant="primary" onClick={() => {
                setShowLinkDialog(false);
                setSelectedLink(null);
              }}>
                ตกลง
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Node Edit Dialog */}
      {showNodeDialog && editingNode && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 max-w-md w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">
              แก้ไขโหนด
            </h3>
            <div className="space-y-4">
              <Field label="ชื่อโหนด">
                <Input
                  value={nodeLabels[editingNode] || ""}
                  onChange={(e) => {
                    setNodeLabels(prev => ({ ...prev, [editingNode]: e.target.value }));
                  }}
                  placeholder="ชื่ออุปกรณ์"
                />
              </Field>
              <Field label="บทบาท">
                <Select
                  value={nodeRoles[editingNode] || "access"}
                  onChange={(value) => {
                    setNodeRoles(prev => ({ ...prev, [editingNode]: value }));
                  }}
                  options={[
                    { value: "core", label: "Core" },
                    { value: "distribution", label: "Distribution" },
                    { value: "access", label: "Access" }
                  ]}
                />
              </Field>
            </div>
            <div className="flex gap-2 mt-6 justify-end">
              <Button variant="secondary" onClick={() => {
                setShowNodeDialog(false);
                setEditingNode(null);
              }}>
                ปิด
              </Button>
              <Button variant="primary" onClick={handleSaveNode}>
                บันทึก
              </Button>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
};

/* ===== Topology helpers (fallback ถ้าไม่มี deriveLinksFromProject เดิม) ===== */
function deriveLinksFromProject(project) {
  // ถ้าคุณมีฟังก์ชันนี้อยู่แล้ว ให้ใช้ของเดิมได้เลย
  // ตรงนี้คือ fallback: เดาว่า core เชื่อม distribution และ access
  const names = (project.summaryRows || []).map(r => r.device);
  const core = names.find(n => /core/i.test(n));
  const dist = names.find(n => /dist|distribution/i.test(n));
  const access = names.find(n => /access/i.test(n));
  const links = [];
  if (core && dist) links.push({ a: core, b: dist, type: "trunk" });
  if (core && access) links.push({ a: core, b: access, type: "trunk" });
  return links;
}

/* ===== สรุปโครง STP โดยกว้าง ===== */
function summarizeStp(project) {
  const rows = project.summaryRows || [];
  const modeByDev = {};
  const rootStatus = {}; // "Yes"/"No"/undefined
  rows.forEach(r => {
    if (r.device) {
      modeByDev[r.device] = r.stpMode || "—";
      rootStatus[r.device] = r.stpRoot; // อาจเป็น "Yes"/"No"/"—"
    }
  });
  const rootCandidates = Object.entries(rootStatus)
    .filter(([, v]) => typeof v === "string" && /yes|root/i.test(v))
    .map(([k]) => k);

  return {
    modeByDev,
    rootCandidates, // ถ้าว่าง แปลว่ายังไม่รู้ว่าใครเป็น root
  };
}

/* ===== จัดบทบาทโดยเดาชื่อ (core/distribution/access) ===== */
// Note: classifyRoleByName is now defined before TopologyGraph component (see above)

/* ===== AI-like Device Narrative (เน้นความสัมพันธ์ + STP) ===== */
function buildDeviceNarrative(project, row) {
  if (!row) return "No device data.";
  const links = deriveLinksFromProject(project);
  const stp = summarizeStp(project);
  const neighbors = links.flatMap(e => (e.a === row.device ? [e.b] : e.b === row.device ? [e.a] : []));
  const uniqNeigh = Array.from(new Set(neighbors));
  const role = classifyRoleByName(row.device);

  const parts = [];
  parts.push(`สรุปอัตโนมัติของอุปกรณ์: ${row.device}`);
  parts.push([
    `• รุ่น/แพลตฟอร์ม: ${row.model || "—"} • OS/Version: ${row.osVersion || "—"}`,
    `• Serial: ${row.serial || "—"} • Mgmt IP: ${row.mgmtIp || "—"}`
  ].join("  |  "));
  if (row.ifaces) {
    parts.push(`• พอร์ตทั้งหมด ${row.ifaces.total} (Up ${row.ifaces.up}, Down ${row.ifaces.down}, AdminDown ${row.ifaces.adminDown})`);
    parts.push(`• Access ≈ ${row.accessCount ?? "—"}  |  Trunk ≈ ${row.trunkCount ?? "—"}`);
    if (row.allowedVlansShort) parts.push(`• Allowed VLANs (short): ${row.allowedVlansShort}`);
  }
  parts.push(`• VLAN ทั้งหมด: ${row.vlanCount ?? "—"}  |  STP: ${row.stpMode || "—"}${row.stpRoot ? ` (Root: ${row.stpRoot})` : ""}`);

  // L3
  const l3 = [];
  if (row.routing) l3.push(row.routing);
  if (row.ospfNeighbors != null) l3.push(`OSPF ${row.ospfNeighbors} neigh`);
  if (row.bgpAsn != null) l3.push(`BGP ${row.bgpAsn}/${row.bgpNeighbors ?? "0"}`);
  if (l3.length) parts.push(`• Routing: ${l3.join(" | ")}`);

  // Mgmt/Health
  parts.push(`• NTP: ${row.ntpStatus || "—"}  |  SNMP: ${row.snmp || "—"}  |  Syslog: ${row.syslog || "—"}  |  CPU ${row.cpu ?? "—"}% / MEM ${row.mem ?? "—"}%`);

  // ความสัมพันธ์จากกราฟ
  if (uniqNeigh.length) {
    parts.push(`• ความสัมพันธ์ในระบบ: เชื่อมต่อกับ ${uniqNeigh.join(", ")} (จากลิงก์กราฟ)`);
  } else {
    parts.push(`• ความสัมพันธ์ในระบบ: (ยังไม่พบจากกราฟ — แนะนำอัปโหลด show cdp/lldp neighbors)`);
  }

  // ภาพรวม STP ทั้งระบบ + บทบาทของตัวนี้
  if (Object.keys(stp.modeByDev).length) {
    const rootTxt = stp.rootCandidates.length
      ? `Root Bridge: ${stp.rootCandidates.join(", ")}`
      : "Root Bridge: (ยังไม่ระบุ — ไม่มีอุปกรณ์รายงานเป็น Root)";
    parts.push(`• ภาพรวม STP ทั่วระบบ: โหมดของแต่ละอุปกรณ์อาจเป็น ${[...new Set(Object.values(stp.modeByDev))].join(", ")} | ${rootTxt}`);
    if (row.stpRoot && /yes|root/i.test(row.stpRoot)) {
      parts.push(`• บทบาท STP ของอุปกรณ์นี้: Root Bridge`);
    } else if (role === "distribution" || role === "access") {
      parts.push(`• บทบาท STP ของอุปกรณ์นี้: Non-root (คาดว่าเชื่อม uplink ไปยัง ${uniqNeigh[0] ?? "core"}; พอร์ต access ควรอยู่สถานะ PortFast)`);
    }
  }

  // HSRP/VRRP จาก VLAN details (ถ้ามี)
  const hsrpHints = [];
  const vds = project.vlanDetails?.[row.device] || [];
  vds.forEach(v => { if (v.hsrpVip) hsrpHints.push(`VLAN${v.vlanId}→${v.hsrpVip}`); });
  if (hsrpHints.length) parts.push(`• HSRP/VRRP ที่เกี่ยวข้อง: ${hsrpHints.join(", ")}`);

  // บทบาทภาพรวม
  if (role === "core") parts.push("• บทบาทเชิงโครงข่าย: Core — จุดรวมการเชื่อมต่อ uplink/downlink และเส้นทางหลัก");
  else if (role === "distribution") parts.push("• บทบาทเชิงโครงข่าย: Distribution — รวมสายจาก Access ขึ้นสู่ Core");
  else if (role === "access") parts.push("• บทบาทเชิงโครงข่าย: Access — ให้บริการปลายทางผู้ใช้/อุปกรณ์");

  return parts.join("\n");
}

/* ===== คำแนะนำรายอุปกรณ์ (Config & Hygiene) ===== */
function buildDeviceRecommendations(project, row) {
  if (!row) return [];
  const links = deriveLinksFromProject(project);
  const neighbors = links.flatMap(e => (e.a === row.device ? [e.b] : e.b === row.device ? [e.a] : []));
  const uniqNeigh = Array.from(new Set(neighbors));
  const recs = [];
  const role = classifyRoleByName(row.device);

  // NTP
  if (!row.ntpStatus || !/sync/i.test(row.ntpStatus)) {
    recs.push("ตั้งค่า NTP ให้ Sync เพื่อความถูกต้องของTime (ตรวจสอบ server, key, timezone)");
  }
  // Syslog
  if (!row.syslog || row.syslog === "—") {
    recs.push("กำหนด logging host/syslog server เพื่อบันทึกเหตุการณ์ส่วนกลาง");
  }
  // STP
  if (row.stpMode && /pvst|rpvst/i.test(row.stpMode)) {
    if (role === "core") {
      recs.push("กำหนด STP priority (เช่น 4096) ให้ Core เป็น Root Primary สำหรับ VLAN หลัก");
    } else if (role === "distribution") {
      recs.push("กำหนด STP priority (เช่น 8192/12288) เป็น Root Secondary ตาม Policy และเปิด UplinkFast (ถ้ารองรับ)");
    } else if (role === "access") {
      recs.push("เปิด portfast และ bpduguard บนพอร์ต access เพื่อลดTime convergence และป้องกัน loop");
    }
  }
  // Trunk pruning
  if (row.allowedVlansShort && /,/.test(row.allowedVlansShort) && (row.trunkCount || 0) > 0) {
    recs.push("Prune VLAN บนลิงก์ trunk ให้เฉพาะ VLAN ที่ใช้งานจริง ลด broadcast domain");
  }
  // Interfaces health
  if (row.ifaces && row.ifaces.down > 10) {
    recs.push("ตรวจสอบพอร์ต Down จำนวนมาก: ยืนยันว่าเป็น admin down (ปิดใช้งาน) พร้อมคำอธิบาย/label");
  }
  // Routing sanity
  if (/BGP/i.test(row.routing || "") && (row.bgpAsn == null || row.bgpNeighbors == null)) {
    recs.push("ทบทวน BGP: ระบุ ASN/neighbor อย่างชัดเจน และจำกัด prefix ด้วย prefix-list/route-map");
  }
  if (/OSPF/i.test(row.routing || "") && (row.ospfNeighbors == null || row.ospfNeighbors === 0)) {
    recs.push("ตรวจสอบ OSPF neighbor บนลิงก์ที่ควรติด (area, network type, auth)");
  }
  // HSRP best-practice
  const hasHsrp = (project.vlanDetails?.[row.device] || []).some(v => v.hsrpVip);
  if (hasHsrp) {
    recs.push("ตรวจสอบ HSRP ให้มีการตั้ง preempt/priority ที่เหมาะสม และ track interface/obj เพื่อ failover ที่ถูกต้อง");
  }
  // AAA/SSH (ทั่วไป)
  recs.push("ยืนยัน AAA/SSHv2/SNMPv3/ACL management ตามมาตรฐานความปลอดภัยขององค์กร");

  // สัมพันธ์กับเพื่อนบ้าน
  if (uniqNeigh.length) {
    recs.push(`ทบทวนลิงก์กับ ${uniqNeigh.join(", ")}: ตรวจสอบความเร็ว/duplex/MTU/allowed VLAN ให้ตรงกันทั้งสองฝั่ง`);
  }
  return recs;
}
