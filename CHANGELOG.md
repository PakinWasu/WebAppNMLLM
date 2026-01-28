# Changelog - à¸›à¸£à¸°à¸§à¸±à¸•à¸´à¸à¸²à¸£à¹€à¸›à¸¥à¸µà¹ˆà¸¢à¸™à¹à¸›à¸¥à¸‡

## [Latest] - 2026-01-28

### âœ¨ Features Added
- **Download Button**: à¹€à¸žà¸´à¹ˆà¸¡à¸›à¸¸à¹ˆà¸¡à¸”à¸²à¸§à¸™à¹Œà¹‚à¸«à¸¥à¸”à¹„à¸Ÿà¸¥à¹Œ TXT à¹à¸¥à¸° JSON à¹ƒà¸™à¸«à¸™à¹‰à¸² More Details (Raw tab)
- **Parser Improvements**: à¸›à¸£à¸±à¸šà¸›à¸£à¸¸à¸‡ Huawei VRP parser à¹ƒà¸«à¹‰à¹€à¸›à¹‡à¸™ Dictionary-based à¹à¸¥à¸° Strict mode

### ðŸ› Bug Fixes

#### Parser Fixes
1. **Hostname Extraction**: à¹à¸à¹‰à¹„à¸‚à¹ƒà¸«à¹‰à¹ƒà¸Šà¹‰ sysname command à¸à¹ˆà¸­à¸™à¹€à¸ªà¸¡à¸­ à¹à¸—à¸™à¸—à¸µà¹ˆà¸ˆà¸°à¹ƒà¸Šà¹‰ prompt <Huawei>
   - ACC4 à¸ˆà¸°à¸–à¸¹à¸à¸£à¸°à¸šà¸¸à¹€à¸›à¹‡à¸™ "ACC4" à¹à¸—à¸™ "Huawei"
   - à¸£à¸­à¸‡à¸£à¸±à¸šà¸£à¸¹à¸›à¹à¸šà¸š [Huawei]sysname ACC4

2. **Ether-Trunk Duplication**: à¹à¸à¹‰à¹„à¸‚à¸à¸²à¸£à¸‹à¹‰à¸³à¸‹à¹‰à¸­à¸™à¸‚à¸­à¸‡ Eth-Trunk entries
   - à¹ƒà¸Šà¹‰ Dictionary keyed by trunk ID à¹à¸—à¸™ list
   - à¹ƒà¸Šà¹‰ Set à¸ªà¸³à¸«à¸£à¸±à¸š members à¹€à¸žà¸·à¹ˆà¸­à¸›à¹‰à¸­à¸‡à¸à¸±à¸™ duplicates
   - Eth-Trunk1 à¸ˆà¸°à¸›à¸£à¸²à¸à¸à¹€à¸žà¸µà¸¢à¸‡à¸„à¸£à¸±à¹‰à¸‡à¹€à¸”à¸µà¸¢à¸§

3. **MAC/ARP Interface Field**: à¹à¸à¹‰à¹„à¸‚à¹ƒà¸«à¹‰ interface field à¹„à¸¡à¹ˆà¹€à¸›à¹‡à¸™ null
   - à¹ƒà¸Šà¹‰ flexible column parsing à¹à¸—à¸™ fixed position
   - à¸•à¸£à¸§à¸ˆà¸ªà¸­à¸šà¸ˆà¸²à¸à¸—à¹‰à¸²à¸¢à¹„à¸›à¸«à¸™à¹‰à¸²à¹€à¸žà¸·à¹ˆà¸­à¸«à¸² interface name
   - à¹€à¸žà¸´à¹ˆà¸¡ MAC address validation (XXXX-XXXX-XXXX format)

4. **Garbage Data Filtering**: à¹€à¸žà¸´à¹ˆà¸¡ guard clauses à¹€à¸žà¸·à¹ˆà¸­à¸à¸£à¸­à¸‡ garbage data
   - à¸à¸£à¸­à¸‡ headers: Total:, Dynamic:, Static:, MAC Address, IP ADDRESS
   - à¸à¸£à¸­à¸‡ separator lines: ---, ===
   - Validate IP addresses à¹à¸¥à¸° MAC addresses

5. **ACL Parsing**: à¹à¸à¹‰à¹„à¸‚ regex à¹€à¸žà¸·à¹ˆà¸­à¸«à¸¥à¸µà¸à¹€à¸¥à¸µà¹ˆà¸¢à¸‡à¸à¸²à¸£ capture keywords
   - à¸›à¸£à¸±à¸š regex: 'acl\s+(?:number\s+)?(?:name\s+)?(\S+)(?:\s+(?:advance|basic|match-order))?'
   - à¸à¸£à¸­à¸‡ keywords: "is", "name", "number", "advance", "basic"

6. **VLAN Duplication**: à¹ƒà¸Šà¹‰ Set à¹à¸—à¸™ List à¹€à¸žà¸·à¹ˆà¸­à¸›à¹‰à¸­à¸‡à¸à¸±à¸™ duplicates
   - à¹ƒà¸Šà¹‰ lan_set à¸£à¸°à¸«à¸§à¹ˆà¸²à¸‡ collection
   - à¹à¸›à¸¥à¸‡à¹€à¸›à¹‡à¸™ sorted list à¸à¹ˆà¸­à¸™ return

7. **Error Handling**: à¸›à¸£à¸±à¸šà¸›à¸£à¸¸à¸‡ error handling à¹ƒà¸™ parser
   - à¹à¸•à¹ˆà¸¥à¸° section à¸¡à¸µ try-except à¹à¸¢à¸à¸à¸±à¸™
   - à¸–à¹‰à¸² section à¸«à¸™à¸¶à¹ˆà¸‡à¸¥à¹‰à¸¡à¹€à¸«à¸¥à¸§ à¸ˆà¸°à¹„à¸¡à¹ˆà¸—à¸³à¹ƒà¸«à¹‰à¸—à¸±à¹‰à¸‡ parser à¸¥à¹‰à¸¡à¹€à¸«à¸¥à¸§
   - Log errors à¸žà¸£à¹‰à¸­à¸¡ traceback

### ðŸ”§ Technical Improvements

#### Parser Architecture
- **Dictionary-Based Approach**: à¹ƒà¸Šà¹‰ Dictionary keyed by unique ID à¹à¸—à¸™ list à¹€à¸žà¸·à¹ˆà¸­à¸›à¹‰à¸­à¸‡à¸à¸±à¸™ duplicates
- **State Machine**: à¹ƒà¸Šà¹‰ state machine à¸ªà¸³à¸«à¸£à¸±à¸š interface parsing à¹€à¸žà¸·à¹ˆà¸­à¸•à¸´à¸”à¸•à¸²à¸¡ context
- **Validation Functions**: à¹€à¸žà¸´à¹ˆà¸¡ helper functions:
  - is_valid_ipv4(): à¸•à¸£à¸§à¸ˆà¸ªà¸­à¸š IP address format
  - is_valid_interface_name(): à¸•à¸£à¸§à¸ˆà¸ªà¸­à¸š interface name format
  - is_valid_mac_address(): à¸•à¸£à¸§à¸ˆà¸ªà¸­à¸š MAC address format (XXXX-XXXX-XXXX)
  - is_valid_username(): à¸à¸£à¸­à¸‡ separator usernames

#### Frontend Improvements
- à¹€à¸žà¸´à¹ˆà¸¡à¸›à¸¸à¹ˆà¸¡ Download TXT à¹à¸¥à¸° Download JSON à¹ƒà¸™à¸«à¸™à¹‰à¸² More Details
- à¸›à¸¸à¹ˆà¸¡à¸ˆà¸°à¹à¸ªà¸”à¸‡à¹€à¸ªà¸¡à¸­ (disabled à¹€à¸¡à¸·à¹ˆà¸­à¹„à¸¡à¹ˆà¸¡à¸µà¸‚à¹‰à¸­à¸¡à¸¹à¸¥)
- à¸Šà¸·à¹ˆà¸­à¹„à¸Ÿà¸¥à¹Œà¸ˆà¸°à¹ƒà¸Šà¹‰ device_name à¸«à¸£à¸·à¸­ deviceId à¹€à¸›à¹‡à¸™ fallback

### ðŸ“ Documentation Updates
- à¸­à¸±à¸žà¹€à¸”à¸• README.md à¹ƒà¸«à¹‰à¸£à¸§à¸¡à¸Ÿà¸µà¹€à¸ˆà¸­à¸£à¹Œà¹ƒà¸«à¸¡à¹ˆ
- à¹€à¸žà¸´à¹ˆà¸¡ CHANGELOG.md à¹€à¸žà¸·à¹ˆà¸­à¸•à¸´à¸”à¸•à¸²à¸¡à¸à¸²à¸£à¹€à¸›à¸¥à¸µà¹ˆà¸¢à¸™à¹à¸›à¸¥à¸‡

### ðŸ”„ Code Quality
- à¸›à¸£à¸±à¸šà¸›à¸£à¸¸à¸‡ error handling à¹ƒà¸«à¹‰à¸„à¸£à¸­à¸šà¸„à¸¥à¸¸à¸¡à¸¡à¸²à¸à¸‚à¸¶à¹‰à¸™
- à¹€à¸žà¸´à¹ˆà¸¡ validation à¹€à¸žà¸·à¹ˆà¸­à¸›à¹‰à¸­à¸‡à¸à¸±à¸™ garbage data
- à¹ƒà¸Šà¹‰ Set à¹à¸¥à¸° Dictionary à¹€à¸žà¸·à¹ˆà¸­à¸›à¹‰à¸­à¸‡à¸à¸±à¸™ duplicates

---

## Previous Versions

### Initial Release
- Basic authentication à¹à¸¥à¸° user management
- Project management
- Document upload à¹à¸¥à¸° storage
- Basic configuration parsing
