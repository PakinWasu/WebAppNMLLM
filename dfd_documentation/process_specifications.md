# WebAppNMLLM - Process Specifications

## 1. Level 1 Process Specifications

### 1.1 Process 1: Authentication & User Management

**Process ID**: P1  
**Process Name**: Authentication & User Management  
**Description**: จัดการการยืนยันตัวตนผู้ใช้ การสมัครสมาชิก และการจัดการข้อมูลผู้ใช้ในระบบ

**Input Data Flows**:
- DF-001: User Credentials (username, password)
- DF-002: Registration Data (username, email, phone_number)
- DF-003: Password Reset Request (email)
- DF-004: OTP Verification Data (email, otp_code)
- DF-005: Profile Update Data (username, email, phone_number)

**Output Data Flows**:
- DF-101: Authentication Token (JWT token, expires_in, user_info)
- DF-102: Login Status (success, message)
- DF-103: Registration Confirmation (success, user_id, message)
- DF-104: Password Reset OTP (otp_sent, message)
- DF-105: OTP Verification Status (success, reset_token, message)
- DF-106: Profile Update Confirmation (success, updated_fields, message)

**Data Store Access**:
- Read: DF-701 User Data Read
- Write: DF-601 User Data Write

**External Entity Interactions**:
- Send: DF-201 OTP Email Request, DF-202 Email Notifications
- Receive: DF-301 Email Delivery Status

**Processing Logic**:
```
IF action == "login" THEN
    Validate credentials against D1
    IF valid THEN Generate JWT token
    ELSE Return error message
ELSE IF action == "register" THEN
    Validate registration data
    Check for duplicate username/email
    Create new user record in D1
    Send confirmation email
ELSE IF action == "password_reset" THEN
    Generate OTP
    Store OTP in D1
    Send OTP email
ELSE IF action == "verify_otp" THEN
    Validate OTP against D1
    IF valid THEN Generate reset token
    ELSE Return error
ELSE IF action == "update_profile" THEN
    Validate update data
    Update user record in D1
    Return confirmation
END IF
```

**Error Handling**:
- Invalid credentials: Return DF-102 with success=false
- Duplicate registration: Return DF-103 with appropriate error
- OTP expired/invalid: Return DF-105 with error message
- Unauthorized access: Return appropriate HTTP status codes

---

### 1.2 Process 2: Project Management

**Process ID**: P2  
**Process Name**: Project Management  
**Description**: จัดการการสร้าง แก้ไข ลบ และจัดการสมาชิกในโปรเจคต่างๆ

**Input Data Flows**:
- DF-006: Project Creation Data (name, description, visibility, backup_interval, status)
- DF-007: Project Update Data (project_id, name, description, visibility, backup_interval, status)
- DF-008: Member Addition Data (project_id, username, role)
- DF-009: Member Removal Data (project_id, username)
- DF-010: Project List Request (user_id)
- DF-011: Project Deletion Request (project_id)

**Output Data Flows**:
- DF-107: Project Creation Confirmation (success, project_id, message)
- DF-108: Project Update Confirmation (success, updated_fields, message)
- DF-109: Member Management Confirmation (success, action, username, message)
- DF-110: Project List (projects array)
- DF-111: Project Deletion Confirmation (success, project_id, message)

**Data Store Access**:
- Read: DF-701 User Data Read, DF-702 Project Data Read
- Write: DF-602 Project Data Write

**Processing Logic**:
```
Validate user permissions from D1
IF action == "create" THEN
    Validate project data
    Generate unique project_id
    Create project record in D2
    Add creator as admin member
ELSE IF action == "update" THEN
    Check user permissions for project
    Update project record in D2
ELSE IF action == "add_member" THEN
    Check if user is manager/admin
    Validate member exists in D1
    Add member to project in D2
ELSE IF action == "remove_member" THEN
    Check if user is manager/admin
    Remove member from project in D2
ELSE IF action == "list" THEN
    Get user's accessible projects from D2
    Filter based on user role
ELSE IF action == "delete" THEN
    Check if user is project owner/admin
    Delete project record from D2
END IF
```

**Business Rules**:
- Only admin can delete projects
- Manager can add/remove members (except other managers/admins)
- Users can only see projects they are members of
- Project must have at least one admin member

---

### 1.3 Process 3: Document Management

**Process ID**: P3  
**Process Name**: Document Management  
**Description**: จัดการการอัปโหลด จัดเก็บ แยกวิเคราะห์ และดาวน์โหลดเอกสารคอนฟิกเครือข่าย

**Input Data Flows**:
- DF-012: Document File (file, filename, content_type)
- DF-013: Document Metadata (who, what, where, when, why, description)
- DF-014: Document Request (document_id)
- DF-015: Document Deletion Request (document_id)

**Output Data Flows**:
- DF-112: Upload Confirmation (success, document_id, filename, message)
- DF-113: Document File (file, filename, content_type)
- DF-114: Document Details (document_id, filename, size, upload_date, metadata)
- DF-115: Document Deletion Confirmation (success, document_id, message)

**Data Store Access**:
- Read: DF-703 Document Data Read, DF-704 File Storage Read
- Write: DF-603 Document Data Write, DF-604 File Storage Write, DF-605 Parsed Config Write

**Processing Logic**:
```
IF action == "upload" THEN
    Validate file type and size
    Generate file hash
    Store file in D6
    Parse configuration from file
    Store document metadata in D3
    Store parsed config in D4
ELSE IF action == "download" THEN
    Get document info from D3
    Retrieve file from D6
    Update access count
ELSE IF action == "delete" THEN
    Check user permissions
    Delete document record from D3
    Delete file from D6
    Delete parsed config from D4
END IF
```

**File Type Support**:
- Cisco configuration files (.cfg, .txt)
- Huawei configuration files (.cfg, .txt)
- Network documentation (.pdf, .doc, .docx)
- Network diagrams (.visio, .png, .jpg)

**Configuration Parsing**:
- Extract interfaces, VLANs, routing protocols
- Identify neighbor relationships
- Parse security policies and ACLs
- Extract device information and capabilities

---

### 1.4 Process 4: Folder Management

**Process ID**: P4  
**Process Name**: Folder Management  
**Description**: จัดการโครงสร้างโฟลเดอร์สำหรับการจัดระเบียบเอกสารในโปรเจค

**Input Data Flows**:
- DF-016: Folder Creation Data (name, parent_id)
- DF-017: Folder Update Data (folder_id, name, parent_id)
- DF-018: Folder Deletion Request (folder_id)
- DF-019: Document Move Request (document_id, target_folder_id)
- DF-020: Folder Structure Request (project_id)

**Output Data Flows**:
- DF-116: Folder Management Confirmation (success, action, folder_id, message)
- DF-117: Document Move Confirmation (success, document_id, new_folder, message)
- DF-118: Folder Structure (folders array)

**Data Store Access**:
- Read: DF-706 Folder Data Read, DF-703 Document Data Read
- Write: DF-606 Folder Data Write, DF-603 Document Data Write

**Processing Logic**:
```
IF action == "create_folder" THEN
    Validate folder name uniqueness
    Generate unique folder_id
    Create folder record in D7
ELSE IF action == "update_folder" THEN
    Update folder record in D7
    Update child folders if name changed
ELSE IF action == "delete_folder" THEN
    Check if folder is empty
    Mark folder as deleted in D7
    Move documents to parent folder
ELSE IF action == "move_document" THEN
    Update document folder_id in D3
ELSE IF action == "get_structure" THEN
    Build hierarchical folder tree from D7
END IF
```

**Folder Structure Rules**:
- Maximum folder depth: 10 levels
- Folder names must be unique within parent
- Cannot delete non-empty folders
- System "Config" folder cannot be deleted

---

### 1.5 Process 5: AI Analysis

**Process ID**: P5  
**Process Name**: AI Analysis  
**Description**: ดำเนินการวิเคราะห์คอนฟิกเครือข่ายโดยใช้ AI และจัดการกระบวนการตรวจสอบโดยมนุษย์

**Input Data Flows**:
- DF-021: Analysis Request (project_id, device_name, analysis_type, custom_prompt)
- DF-022: Analysis Verification Data (analysis_id, verified_content, comments)

**Output Data Flows**:
- DF-119: Analysis Results (analysis_id, device_name, analysis_type, results, status)
- DF-120: Analysis Status (analysis_id, status, progress)

**Data Store Access**:
- Read: DF-705 Parsed Config Read, DF-707 LLM Result Read
- Write: DF-607 LLM Result Write

**External Entity Interactions**:
- Send: DF-401 LLM Prompts, DF-402 Configuration Data
- Receive: DF-501 LLM Responses, DF-502 Analysis Output

**Processing Logic**:
```
IF action == "request_analysis" THEN
    Get device configurations from D4
    Prepare analysis context
    Generate LLM prompt based on analysis_type
    Send to LLM service
    Store AI draft in D5 with status "pending_review"
ELSE IF action == "verify_analysis" THEN
    Get analysis from D5
    Update with human review data
    Calculate accuracy metrics
    Update status to "verified"
    Store verified version in D5
END IF
```

**Analysis Types**:
- Security Audit: ตรวจสอบช่องโหว่และการตั้งค่าความปลอดภัย
- Performance Review: วิเคราะห์ประสิทธิภาพและการใช้ทรัพยากร
- Configuration Compliance: ตรวจสอบความสอดคล้องกับมาตรฐาน
- Network Topology: วิเคราะห์โครงสร้างเครือข่าย
- Best Practices: ตรวจสอบการปฏิบัติตาม best practices
- Custom: การวิเคราะห์แบบกำหนดเอง

**Human-in-the-Loop Workflow**:
1. AI generates initial analysis draft
2. Human expert reviews and edits
3. System tracks accuracy metrics
4. Final verified version stored

---

### 1.6 Process 6: Network Topology

**Process ID**: P6  
**Process Name**: Network Topology  
**Description**: สร้างและจัดการภาพ topology ของเครือข่ายจากข้อมูลคอนฟิก

**Input Data Flows**:
- DF-023: Topology Generation Request (project_id)
- DF-024: Topology Layout Data (project_id, positions, links)
- DF-025: Topology View Request (project_id)
- DF-026: Topology Export Request (project_id, format)

**Output Data Flows**:
- DF-121: Topology Data (nodes, links, layout)
- DF-122: Topology Layout Confirmation (success, message)
- DF-123: Topology Export File (file, filename, format)

**Data Store Access**:
- Read: DF-705 Parsed Config Read, DF-708 Topology Data Read
- Write: DF-608 Topology Data Write

**Processing Logic**:
```
IF action == "generate_topology" THEN
    Get all device configs from D4
    Extract device information
    Identify neighbor relationships
    Generate initial node positions
    Create network links
    Store topology in D8
ELSE IF action == "update_layout" THEN
    Update node positions in D8
    Update link information
ELSE IF action == "view_topology" THEN
    Get topology from D8
    Return formatted topology data
ELSE IF action == "export_topology" THEN
    Get topology from D8
    Convert to requested format
    Generate export file
END IF
```

**Topology Generation Algorithm**:
1. Extract devices from parsed configurations
2. Identify interfaces and neighbor relationships
3. Calculate initial layout using force-directed graph
4. Apply device-specific positioning rules
5. Generate visual representation

**Export Formats**:
- JSON: For web visualization
- GraphML: For network analysis tools
- Visio: For documentation
- PNG/SVG: For presentations

---

### 1.7 Process 7: Dashboard & Summary

**Process ID**: P7  
**Process Name**: Dashboard & Summary  
**Description**: สร้างภาพรวมข้อมูลโปรเจคและสรุปข้อมูลสำคัญสำหรับการตัดสินใจ

**Input Data Flows**:
- DF-027: Dashboard Request (project_id, filters)
- DF-028: Report Generation Request (project_id, report_type, format)

**Output Data Flows**:
- DF-124: Dashboard Data (summary, metrics, charts)
- DF-125: Report File (file, filename, report_type)

**Data Store Access**:
- Read: DF-702 Project Data Read, DF-705 Parsed Config Read, DF-707 LLM Result Read

**Processing Logic**:
```
IF action == "dashboard" THEN
    Get project info from D2
    Get device statistics from D4
    Get analysis results from D5
    Calculate summary metrics
    Generate chart data
    Format dashboard response
ELSE IF action == "generate_report" THEN
    Collect relevant data from D2, D4, D5
    Apply report template
    Generate report in requested format
END IF
```

**Dashboard Components**:
- Project Overview: ข้อมูลทั่วไปโปรเจค
- Device Summary: จำนวนและประเภทอุปกรณ์
- Configuration Status: สถานะคอนฟิก
- Analysis Results: สรุปผลการวิเคราะห์
- Network Health: สถานะสุขภาพเครือข่าย
- Recent Activities: กิจกรรมล่าสุด

**Report Types**:
- Executive Summary: สรุปสำหรับผู้บริหาร
- Technical Report: รายละเอียดสำหรับวิศวกร
- Compliance Report: รายงานความสอดคล้อง
- Security Assessment: รายงานความปลอดภัย

---

### 1.8 Process 8: Script Generation

**Process ID**: P8  
**Process Name**: Script Generation  
**Description**: สร้าง script สำหรับการจัดการอุปกรณ์เครือข่ายจาก template และข้อมูลคอนฟิก

**Input Data Flows**:
- DF-029: Script Generation Request (project_id, device_ids, template_type)
- DF-030: Script Customization Data (script_id, custom_commands)

**Output Data Flows**:
- DF-126: Generated Scripts (scripts array with device_id, script_content, template_type)

**Data Store Access**:
- Read: DF-705 Parsed Config Read, DF-709 Script Data Read
- Write: DF-609 Script Data Write

**Processing Logic**:
```
IF action == "generate_script" THEN
    Get device configurations from D4
    Get script template from D9
    Apply template to device data
    Generate device-specific scripts
    Store scripts in D9
ELSE IF action == "customize_script" THEN
    Get existing script from D9
    Apply customizations
    Update script in D9
END IF
```

**Script Templates**:
- Cisco Commands: คำสั่งสำหรับอุปกรณ์ Cisco
- Huawei Commands: คำสั่งสำหรับอุปกรณ์ Huawei
- Backup Scripts: Script สำหรับ backup คอนฟิก
- Audit Scripts: Script สำหรับตรวจสอบคอนฟิก
- Configuration Updates: Script สำหรับอัปเดตคอนฟิก

**Customization Options**:
- Add custom commands
- Modify existing commands
- Set execution order
- Add conditional logic
- Include error handling

## 2. Level 2 Process Specifications

### 2.1 Process 1 Sub-processes

#### 1.1 Receive Login Request (P1.1)
**Input**: DF-001 User Credentials  
**Output**: Login credentials to P1.2  
**Logic**: Validate input format, sanitize data

#### 1.2 Validate Credentials (P1.2)
**Input**: Login credentials from P1.1, DF-701 User Data Read  
**Output**: Validation result to P1.3, DF-102 Login Status  
**Logic**: Hash password, compare with stored hash, check account status

#### 1.3 Generate JWT Token (P1.3)
**Input**: Validation result from P1.2  
**Output**: DF-101 Authentication Token  
**Logic**: Generate JWT with user info, set expiration

#### 1.4 Handle Registration (P1.4)
**Input**: DF-002 Registration Data  
**Output**: DF-103 Registration Confirmation, DF-601 User Data Write  
**Logic**: Validate data, check duplicates, hash password, create user

#### 1.5 Generate OTP (P1.5)
**Input**: DF-003 Password Reset Request  
**Output**: DF-104 Password Reset OTP, DF-201 OTP Email Request, DF-601 User Data Write  
**Logic**: Generate random OTP, store with expiration, send email

#### 1.6 Verify OTP (P1.6)
**Input**: DF-004 OTP Verification Data, DF-301 Email Delivery Status  
**Output**: DF-105 OTP Verification Status  
**Logic**: Validate OTP, check expiration, generate reset token

#### 1.7 Update User Profile (P1.7)
**Input**: DF-005 Profile Update Data  
**Output**: DF-106 Profile Update Confirmation, DF-601 User Data Write  
**Logic**: Validate data, update user record, log changes

### 2.2 Process 2 Sub-processes

#### 2.1 Receive Project Request (P2.1)
**Input**: Various project management requests  
**Output**: Request type and data to P2.2  
**Logic**: Parse request, validate format, determine action type

#### 2.2 Validate User Permissions (P2.2)
**Input**: Request data from P2.1, DF-701 User Data Read  
**Output**: Validated request to appropriate sub-process  
**Logic**: Check user role, verify project access rights

#### 2.3 Create Project (P2.3)
**Input**: Validated creation request from P2.2  
**Output**: DF-107 Project Creation Confirmation, DF-602 Project Data Write  
**Logic**: Generate project_id, create project record, add creator as admin

#### 2.4 Update Project (P2.4)
**Input**: Validated update request from P2.2  
**Output**: DF-108 Project Update Confirmation, DF-602 Project Data Write  
**Logic**: Validate changes, update project record, log modifications

#### 2.5 Add Project Member (P2.5)
**Input**: Validated member addition from P2.2  
**Output**: DF-109 Member Management Confirmation, DF-602 Project Data Write  
**Logic**: Validate user exists, check permissions, add to project members

#### 2.6 Remove Project Member (P2.6)
**Input**: Validated member removal from P2.2  
**Output**: DF-109 Member Management Confirmation, DF-602 Project Data Write  
**Logic**: Check permissions, remove member, update project record

#### 2.7 Retrieve Project List (P2.7)
**Input**: Validated list request from P2.2  
**Output**: DF-110 Project List  
**Logic**: Get user's projects, filter by role, format response

#### 2.8 Delete Project (P2.8)
**Input**: Validated deletion request from P2.2  
**Output**: DF-111 Project Deletion Confirmation, DF-602 Project Data Write  
**Logic**: Check permissions, mark as deleted, cleanup related data

### 2.3 Process 3 Sub-processes

#### 3.1 Receive Document Upload (P3.1)
**Input**: DF-012 Document File, DF-013 Document Metadata  
**Output**: File and metadata to P3.2  
**Logic**: Validate file type, size limits, metadata format

#### 3.2 Validate Document File (P3.2)
**Input**: File and metadata from P3.1  
**Output**: Validated file to P3.3  
**Logic**: Check file integrity, scan for malware, validate format

#### 3.3 Store Document File (P3.3)
**Input**: Validated file from P3.2  
**Output**: File path to P3.4, DF-604 File Storage Write  
**Logic**: Generate unique filename, store in file system, return path

#### 3.4 Parse Configuration (P3.4)
**Input**: File path from P3.3  
**Output**: Parsed config to P3.5, DF-605 Parsed Config Write  
**Logic**: Detect config type, parse using appropriate parser, extract structured data

#### 3.5 Save Document Metadata (P3.5)
**Input**: Parsed config from P3.4  
**Output**: DF-112 Upload Confirmation, DF-603 Document Data Write  
**Logic**: Generate document_id, store metadata, link to parsed config

#### 3.6 Create Document Version (P3.6)
**Input**: Document ID from P3.5  
**Output**: Version update to D3  
**Logic**: Check for existing versions, create new version record

#### 3.7 Retrieve Document (P3.7)
**Input**: DF-014 Document Request  
**Output**: DF-113 Document File, DF-114 Document Details  
**Logic**: Get document info, retrieve file, update access count

#### 3.8 Delete Document (P3.8)
**Input**: DF-015 Document Deletion Request  
**Output**: DF-115 Document Deletion Confirmation  
**Logic**: Check permissions, delete file, remove records

### 2.4 Process 4 Sub-processes

#### 4.1 Receive Folder Request (P4.1)
**Input**: Various folder management requests  
**Output**: Request type and data to appropriate sub-process  
**Logic**: Parse request, validate format, route to handler

#### 4.2 Create New Folder (P4.2)
**Input**: Folder creation data from P4.1  
**Output**: DF-116 Folder Management Confirmation, DF-606 Folder Data Write  
**Logic**: Validate name uniqueness, generate folder_id, create record

#### 4.3 Update Folder Name (P4.3)
**Input**: Folder update data from P4.1  
**Output**: DF-116 Folder Management Confirmation, DF-606 Folder Data Write  
**Logic**: Validate permissions, update folder name, update child references

#### 4.4 Delete Folder (P4.4)
**Input**: Folder deletion request from P4.1  
**Output**: DF-116 Folder Management Confirmation, DF-606 Folder Data Write  
**Logic**: Check if empty, mark as deleted, move contents to parent

#### 4.5 Move Documents (P4.5)
**Input**: Document move request from P4.1  
**Output**: DF-117 Document Move Confirmation, DF-603 Document Data Write  
**Logic**: Validate permissions, update document folder_id, log move

#### 4.6 Retrieve Folder Structure (P4.6)
**Input**: Folder structure request from P4.1  
**Output**: DF-118 Folder Structure  
**Logic**: Build hierarchical tree, filter deleted folders, format response

### 2.5 Process 5 Sub-processes

#### 5.1 Receive Analysis Request (P5.1)
**Input**: DF-021 Analysis Request  
**Output**: Analysis parameters to P5.2  
**Logic**: Validate request format, check permissions, determine analysis type

#### 5.2 Prepare Analysis Context (P5.2)
**Input**: Analysis parameters from P5.1, DF-705 Parsed Config Read  
**Output**: Analysis context to P5.3  
**Logic**: Gather relevant configs, format context data, limit size

#### 5.3 Generate LLM Prompt (P5.3)
**Input**: Analysis context from P5.2  
**Output**: Formatted prompt to P5.4  
**Logic**: Apply prompt template, include context, add instructions

#### 5.4 Send to LLM (P5.4)
**Input**: Formatted prompt from P5.3  
**Output**: DF-401 LLM Prompts, DF-402 Configuration Data  
**Logic**: Send request to LLM service, handle timeouts, retry logic

#### 5.5 Process LLM Response (P5.5)
**Input**: DF-501 LLM Responses, DF-502 Analysis Output  
**Output**: Processed response to P5.6  
**Logic**: Parse response, extract analysis data, calculate metrics

#### 5.6 Save Analysis Draft (P5.6)
**Input**: Processed response from P5.5  
**Output**: DF-119 Analysis Results, DF-607 LLM Result Write  
**Logic**: Store draft with pending status, generate analysis_id

#### 5.7 Present for Review (P5.7)
**Input**: Analysis ID from P5.6, DF-707 LLM Result Read  
**Output**: DF-120 Analysis Status  
**Logic**: Format analysis for human review, include diff tools

#### 5.8 Process Verification (P5.8)
**Input**: DF-022 Analysis Verification Data  
**Output**: Updated analysis status, DF-607 LLM Result Write  
**Logic**: Apply human changes, calculate accuracy, update status

### 2.6 Process 6 Sub-processes

#### 6.1 Receive Topology Request (P6.1)
**Input**: DF-023 Topology Generation Request  
**Output**: Request parameters to P6.2  
**Logic**: Validate request, check permissions, determine action type

#### 6.2 Extract Network Devices (P6.2)
**Input**: Request parameters from P6.1, DF-705 Parsed Config Read  
**Output**: Device list to P6.3  
**Logic**: Extract device info, identify types, gather capabilities

#### 6.3 Generate Network Nodes (P6.3)
**Input**: Device list from P6.2  
**Output**: Network nodes to P6.4  
**Logic**: Create node objects, assign types, set initial positions

#### 6.4 Create Network Links (P6.4)
**Input**: Network nodes from P6.3, DF-705 Parsed Config Read  
**Output**: Network links to P6.5  
**Logic**: Identify connections, create link objects, determine link types

#### 6.5 Calculate Layout (P6.5)
**Input**: Network links from P6.4  
**Output**: Calculated layout to P6.6  
**Logic**: Apply layout algorithm, optimize positioning, prevent overlaps

#### 6.6 Save Topology Layout (P6.6)
**Input**: Calculated layout from P6.5, DF-024 Topology Layout Data  
**Output**: DF-122 Topology Layout Confirmation, DF-608 Topology Data Write  
**Logic**: Store layout positions, update topology record, log changes

#### 6.7 Retrieve Topology (P6.7)
**Input**: DF-025 Topology View Request  
**Output**: DF-121 Topology Data  
**Logic**: Get topology from D8, format for visualization, include metadata

#### 6.8 Export Topology (P6.8)
**Input**: DF-026 Topology Export Request  
**Output**: DF-123 Topology Export File  
**Logic**: Convert to requested format, generate file, handle download

### 2.7 Process 7 Sub-processes

#### 7.1 Receive Dashboard Request (P7.1)
**Input**: DF-027 Dashboard Request  
**Output**: Dashboard parameters to data collection processes  
**Logic**: Parse request, validate filters, determine data needs

#### 7.2 Collect Project Statistics (P7.2)
**Input**: Dashboard parameters from P7.1, DF-702 Project Data Read  
**Output**: Project statistics to P7.5  
**Logic**: Calculate project metrics, aggregate data, compute trends

#### 7.3 Collect Configuration Overview (P7.3)
**Input**: Dashboard parameters from P7.1, DF-705 Parsed Config Read  
**Output**: Configuration overview to P7.5  
**Logic**: Summarize device configs, identify issues, categorize by type

#### 7.4 Collect Analysis Results (P7.4)
**Input**: Dashboard parameters from P7.1, DF-707 LLM Result Read  
**Output**: Analysis summary to P7.5  
**Logic**: Aggregate analysis results, compute accuracy, identify patterns

#### 7.5 Generate Summary Metrics (P7.5)
**Input**: Data from P7.2, P7.3, P7.4  
**Output**: Summary metrics to P7.6  
**Logic**: Combine data sources, calculate KPIs, generate insights

#### 7.6 Format Dashboard Data (P7.6)
**Input**: Summary metrics from P7.5  
**Output**: Formatted data to P7.7  
**Logic**: Structure for UI, create chart data, add metadata

#### 7.7 Display Dashboard (P7.7)
**Input**: Formatted data from P7.6  
**Output**: DF-124 Dashboard Data  
**Logic**: Final formatting, add caching headers, optimize for delivery

#### 7.8 Generate Reports (P7.8)
**Input**: DF-028 Report Generation Request  
**Output**: DF-125 Report File  
**Logic**: Apply report template, populate with data, generate file

### 2.8 Process 8 Sub-processes

#### 8.1 Receive Script Request (P8.1)
**Input**: DF-029 Script Generation Request  
**Output**: Script parameters to P8.2  
**Logic**: Validate request, check permissions, determine template type

#### 8.2 Select Target Devices (P8.2)
**Input**: Script parameters from P8.1, DF-705 Parsed Config Read  
**Output**: Selected devices to P8.3  
**Logic**: Filter devices by criteria, validate access, gather config data

#### 8.3 Choose Command Templates (P8.3)
**Input**: Selected devices from P8.2, DF-709 Script Data Read  
**Output**: Selected templates to P8.4  
**Logic**: Match templates to device types, validate compatibility

#### 8.4 Customize Commands (P8.4)
**Input**: Selected templates from P8.3, DF-030 Script Customization Data  
**Output**: Customized commands to P8.5  
**Logic**: Apply customizations, validate syntax, optimize commands

#### 8.5 Generate Scripts (P8.5)
**Input**: Customized commands from P8.4  
**Output**: Generated scripts to P8.6, DF-609 Script Data Write  
**Logic**: Apply template to device data, generate per-device scripts

#### 8.6 Validate Scripts (P8.6)
**Input**: Generated scripts from P8.5  
**Output**: Validation results to P8.7  
**Logic**: Check syntax, validate commands, test against device types

#### 8.7 Preview Scripts (P8.7)
**Input**: Validation results from P8.6  
**Output**: DF-126 Generated Scripts  
**Logic**: Format for preview, add syntax highlighting, include metadata

#### 8.8 Export Scripts (P8.8)
**Input**: Export request from user  
**Output**: Script export file  
**Logic**: Package scripts, generate download file, handle compression

---

## 3. Cross-Process Interactions

### 3.1 Data Dependencies

| Process | Depends On | Data Required |
|---------|------------|--------------|
| P2 (Project Management) | P1 (Authentication) | User permissions, roles |
| P3 (Document Management) | P2 (Project Management) | Project access rights |
| P4 (Folder Management) | P2 (Project Management) | Project context |
| P5 (AI Analysis) | P3 (Document Management) | Parsed configurations |
| P6 (Network Topology) | P3 (Document Management) | Device configurations |
| P7 (Dashboard) | P2, P3, P5 | Project, config, analysis data |
| P8 (Script Generation) | P3 (Document Management) | Device configurations |

### 3.2 Event Triggers

| Event | Trigger Process | Affected Processes | Action |
|-------|----------------|-------------------|--------|
| User Login | P1 | All | Set user context |
| Project Created | P2 | P3, P4, P6, P7, P8 | Initialize project data |
| Document Uploaded | P3 | P5, P6, P7, P8 | Trigger analysis/topology |
| Analysis Completed | P5 | P7 | Update dashboard |
| Topology Updated | P6 | P7 | Update visualization |

### 3.3 Error Propagation

| Error Type | Source Process | Impact | Handling |
|------------|----------------|---------|----------|
| Authentication Failed | P1 | All | Block access, return 401 |
| Permission Denied | P2, P3, P4 | Specific actions | Return 403, log attempt |
| Invalid Configuration | P3 | P5, P6, P8 | Skip processing, notify user |
| LLM Service Unavailable | P5 | P5, P7 | Queue request, notify admin |
| File Storage Full | P3, P6 | Upload operations | Return error, cleanup old files |

---

## 4. Performance Considerations

### 4.1 Processing Limits

| Process | Max Concurrent | Timeout | Retry Policy |
|---------|-----------------|----------|-------------|
| P1 (Authentication) | 100 | 5 seconds | No retry |
| P3 (Document Upload) | 10 | 30 seconds | 3 retries |
| P5 (AI Analysis) | 5 | 120 seconds | 2 retries |
| P6 (Topology Generation) | 3 | 60 seconds | 1 retry |

### 4.2 Data Volume Limits

| Operation | Max Data Size | Reason |
|-----------|---------------|---------|
| File Upload | 100MB | Storage limits |
| LLM Context | 32K tokens | Model limits |
| Dashboard Query | 1000 devices | Performance |
| Script Generation | 500 devices | Memory limits |

### 4.3 Caching Strategy

| Data Type | Cache Duration | Cache Location |
|------------|----------------|-----------------|
| User Sessions | 24 hours | Redis |
| Project Lists | 1 hour | Memory |
| Parsed Configs | 6 hours | Redis |
| Analysis Results | 12 hours | Memory |
| Topology Data | 2 hours | Redis |

---

## 5. Security Considerations

### 5.1 Access Control

| Process | Access Level | Required Permissions |
|---------|--------------|---------------------|
| P1 (Authentication) | Public | None |
| P2 (Project Management) | Authenticated | Project-specific |
| P3 (Document Management) | Authenticated | Project-specific |
| P5 (AI Analysis) | Authenticated | LLM permission |
| P7 (Dashboard) | Authenticated | Read permission |

### 5.2 Data Validation

| Input Type | Validation Rules | Sanitization |
|------------|------------------|--------------|
| User Credentials | Format, length, complexity | Hash password |
| File Uploads | Type, size, content | Virus scan |
| LLM Prompts | Length, content filtering | Escape special chars |
| Configuration Data | Syntax validation | Parse and validate |

### 5.3 Audit Trail

| Action | Logged Fields | Retention |
|---------|--------------|-----------|
| User Login | User, IP, timestamp, success | 1 year |
| Document Upload | User, file, project, timestamp | 2 years |
| Analysis Request | User, device, type, timestamp | 2 years |
| Configuration Changes | User, field, old, new, timestamp | 3 years |
