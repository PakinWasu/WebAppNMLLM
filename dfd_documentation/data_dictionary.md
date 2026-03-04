# WebAppNMLLM - Data Dictionary

## 1. Data Flows Dictionary

### 1.1 External Entity to System Flows

#### User to System Flows

| Flow ID | Data Flow Name | Source | Destination | Data Structure | Description |
|---------|---------------|--------|--------------|----------------|-------------|
| DF-001 | User Credentials | USER | P1.1 | {username: string, password: string} | ข้อมูลการเข้าสู่ระบบของผู้ใช้ |
| DF-002 | Registration Data | USER | P1.4 | {username: string, email: string, phone_number?: string} | ข้อมูลการสมัครสมาชิกใหม่ |
| DF-003 | Password Reset Request | USER | P1.5 | {email: string} | คำขอรีเซ็ตรหัสผ่าน |
| DF-004 | OTP Verification Data | USER | P1.6 | {email: string, otp_code: string} | ข้อมูลการตรวจสอบรหัส OTP |
| DF-005 | Profile Update Data | USER | P1.7 | {username: string, email: string, phone_number?: string} | ข้อมูลอัปเดตโปรไฟล์ผู้ใช้ |
| DF-006 | Project Creation Data | USER | P2.1 | {name: string, description?: string, visibility: string, backup_interval: string, status: string} | ข้อมูลการสร้างโปรเจคใหม่ |
| DF-007 | Project Update Data | USER | P2.1 | {project_id: string, name: string, description?: string, visibility?: string, backup_interval?: string, status?: string} | ข้อมูลการอัปเดตโปรเจค |
| DF-008 | Member Addition Data | USER | P2.1 | {project_id: string, username: string, role: string} | ข้อมูลการเพิ่มสมาชิกโปรเจค |
| DF-009 | Member Removal Data | USER | P2.1 | {project_id: string, username: string} | ข้อมูลการลบสมาชิกโปรเจค |
| DF-010 | Project List Request | USER | P2.1 | {user_id: string} | คำขอดูรายการโปรเจค |
| DF-011 | Project Deletion Request | USER | P2.1 | {project_id: string} | คำขอลบโปรเจค |
| DF-012 | Document File | USER | P3.1 | {file: binary, filename: string, content_type: string} | ไฟล์เอกสารที่อัปโหลด |
| DF-013 | Document Metadata | USER | P3.1 | {who: string, what: string, where?: string, when?: string, why?: string, description?: string} | ข้อมูลเมตาดาต้าของเอกสาร |
| DF-014 | Document Request | USER | P3.7 | {document_id: string} | คำขอดูเอกสาร |
| DF-015 | Document Deletion Request | USER | P3.8 | {document_id: string} | คำขอลบเอกสาร |
| DF-016 | Folder Creation Data | USER | P4.1 | {name: string, parent_id?: string} | ข้อมูลการสร้างโฟลเดอร์ |
| DF-017 | Folder Update Data | USER | P4.1 | {folder_id: string, name: string, parent_id?: string} | ข้อมูลการอัปเดตโฟลเดอร์ |
| DF-018 | Folder Deletion Request | USER | P4.1 | {folder_id: string} | คำขอลบโฟลเดอร์ |
| DF-019 | Document Move Request | USER | P4.1 | {document_id: string, target_folder_id: string} | คำขอย้ายเอกสาร |
| DF-020 | Folder Structure Request | USER | P4.1 | {project_id: string} | คำขอดูโครงสร้างโฟลเดอร์ |
| DF-021 | Analysis Request | USER | P5.1 | {project_id: string, device_name: string, analysis_type: string, custom_prompt?: string} | คำขอวิเคราะห์ AI |
| DF-022 | Analysis Verification Data | USER | P5.8 | {analysis_id: string, verified_content: object, comments?: string} | ข้อมูลการยืนยันผลการวิเคราะห์ |
| DF-023 | Topology Generation Request | USER | P6.1 | {project_id: string} | คำขอสร้าง Topology |
| DF-024 | Topology Layout Data | USER | P6.6 | {project_id: string, positions: object, links: array} | ข้อมูล Layout ของ Topology |
| DF-025 | Topology View Request | USER | P6.7 | {project_id: string} | คำขอดู Topology |
| DF-026 | Topology Export Request | USER | P6.8 | {project_id: string, format: string} | คำขอส่งออก Topology |
| DF-027 | Dashboard Request | USER | P7.1 | {project_id: string, filters?: object} | คำขอดู Dashboard |
| DF-028 | Report Generation Request | USER | P7.8 | {project_id: string, report_type: string, format: string} | คำขอสร้างรายงาน |
| DF-029 | Script Generation Request | USER | P8.1 | {project_id: string, device_ids: array, template_type: string} | คำขอสร้าง Script |
| DF-030 | Script Customization Data | USER | P8.4 | {script_id: string, custom_commands: array} | ข้อมูลการปรับแต่ง Script |

#### System to User Flows

| Flow ID | Data Flow Name | Source | Destination | Data Structure | Description |
|---------|---------------|--------|--------------|----------------|-------------|
| DF-101 | Authentication Token | P1.3 | USER | {token: string, expires_in: number, user_info: object} | JWT Token หลังการเข้าสู่ระบบ |
| DF-102 | Login Status | P1.2 | USER | {success: boolean, message: string} | สถานะการเข้าสู่ระบบ |
| DF-103 | Registration Confirmation | P1.4 | USER | {success: boolean, user_id: string, message: string} | การยืนยันการสมัครสมาชิก |
| DF-104 | Password Reset OTP | P1.5 | USER | {otp_sent: boolean, message: string} | การส่ง OTP สำหรับรีเซ็ตรหัสผ่าน |
| DF-105 | OTP Verification Status | P1.6 | USER | {success: boolean, reset_token?: string, message: string} | สถานะการตรวจสอบ OTP |
| DF-106 | Profile Update Confirmation | P1.7 | USER | {success: boolean, updated_fields: array, message: string} | การยืนยันการอัปเดตโปรไฟล์ |
| DF-107 | Project Creation Confirmation | P2.3 | USER | {success: boolean, project_id: string, message: string} | การยืนยันการสร้างโปรเจค |
| DF-108 | Project Update Confirmation | P2.4 | USER | {success: boolean, updated_fields: array, message: string} | การยืนยันการอัปเดตโปรเจค |
| DF-109 | Member Management Confirmation | P2.5/P2.6 | USER | {success: boolean, action: string, username: string, message: string} | การยืนยันการจัดการสมาชิก |
| DF-110 | Project List | P2.7 | USER | {projects: array[{project_id, name, description, created_at, role}]} | รายการโปรเจคที่ผู้ใช้มีสิทธิ์ |
| DF-111 | Project Deletion Confirmation | P2.8 | USER | {success: boolean, project_id: string, message: string} | การยืนยันการลบโปรเจค |
| DF-112 | Upload Confirmation | P3.5 | USER | {success: boolean, document_id: string, filename: string, message: string} | การยืนยันการอัปโหลดเอกสาร |
| DF-113 | Document File | P3.7 | USER | {file: binary, filename: string, content_type: string} | ไฟล์เอกสารที่ดาวน์โหลด |
| DF-114 | Document Details | P3.7 | USER | {document_id, filename, size, upload_date, metadata} | รายละเอียดเอกสาร |
| DF-115 | Document Deletion Confirmation | P3.8 | USER | {success: boolean, document_id: string, message: string} | การยืนยันการลบเอกสาร |
| DF-116 | Folder Management Confirmation | P4.2/P4.3/P4.4 | USER | {success: boolean, action: string, folder_id: string, message: string} | การยืนยันการจัดการโฟลเดอร์ |
| DF-117 | Document Move Confirmation | P4.5 | USER | {success: boolean, document_id: string, new_folder: string, message: string} | การยืนยันการย้ายเอกสาร |
| DF-118 | Folder Structure | P4.6 | USER | {folders: array[{id, name, parent_id, children}]} | โครงสร้างโฟลเดอร์ |
| DF-119 | Analysis Results | P5.6/P5.8 | USER | {analysis_id, device_name, analysis_type, results: object, status: string} | ผลการวิเคราะห์ AI |
| DF-120 | Analysis Status | P5.7 | USER | {analysis_id, status: string, progress: number} | สถานะการวิเคราะห์ |
| DF-121 | Topology Data | P6.7 | USER | {nodes: array, links: array, layout: object} | ข้อมูล Topology |
| DF-122 | Topology Layout Confirmation | P6.6 | USER | {success: boolean, message: string} | การยืนยันการอัปเดต Layout |
| DF-123 | Topology Export File | P6.8 | USER | {file: binary, filename: string, format: string} | ไฟล์ส่งออก Topology |
| DF-124 | Dashboard Data | P7.7 | USER | {summary: object, metrics: object, charts: array} | ข้อมูล Dashboard |
| DF-125 | Report File | P7.8 | USER | {file: binary, filename: string, report_type: string} | ไฟล์รายงาน |
| DF-126 | Generated Scripts | P8.7/P8.8 | USER | {scripts: array[{device_id, script_content, template_type}]} | Script ที่สร้างขึ้น |

### 1.2 System to External Entity Flows

#### System to Email Service Flows

| Flow ID | Data Flow Name | Source | Destination | Data Structure | Description |
|---------|---------------|--------|--------------|----------------|-------------|
| DF-201 | OTP Email Request | P1.5 | EMAIL | {to: string, subject: string, body: string, otp_code: string} | คำขอส่งอีเมล OTP |
| DF-202 | Email Notifications | P1.1 | EMAIL | {to: string, subject: string, body: string, type: string} | การแจ้งเตือนทางอีเมล |

#### Email Service to System Flows

| Flow ID | Data Flow Name | Source | Destination | Data Structure | Description |
|---------|---------------|--------|--------------|----------------|-------------|
| DF-301 | Email Delivery Status | EMAIL | P1.6 | {success: boolean, message_id: string, timestamp: string} | สถานะการส่งอีเมล |

#### System to LLM Flows

| Flow ID | Data Flow Name | Source | Destination | Data Structure | Description |
|---------|---------------|--------|--------------|----------------|-------------|
| DF-401 | LLM Prompts | P5.4 | LLM | {prompt: string, context: object, model: string} | คำสั่งที่ส่งไปยัง LLM |
| DF-402 | Configuration Data | P5.4 | LLM | {device_configs: array, analysis_type: string} | ข้อมูลคอนฟิกที่ส่งไปวิเคราะห์ |

#### LLM to System Flows

| Flow ID | Data Flow Name | Source | Destination | Data Structure | Description |
|---------|---------------|--------|--------------|----------------|-------------|
| DF-501 | LLM Responses | LLM | P5.5 | {response: string, analysis: object, confidence: number, tokens_used: number} | ผลการตอบกลับจาก LLM |
| DF-502 | Analysis Output | LLM | P5.5 | {findings: array, recommendations: array, risk_level: string} | ผลการวิเคราะห์จาก AI |

### 1.3 Process to Data Store Flows

#### Write Operations (Process → Data Store)

| Flow ID | Data Flow Name | Source | Destination | Data Structure | Description |
|---------|---------------|--------|--------------|----------------|-------------|
| DF-601 | User Data Write | P1.4/P1.7 | DS1 | {username, email, password_hash?, phone_number?, role, created_at, updated_at} | การเขียนข้อมูลผู้ใช้ |
| DF-602 | Project Data Write | P2.3/P2.4/P2.5/P2.6 | DS2 | {project_id, name, description, created_by, created_at, updated_at, members: array} | การเขียนข้อมูลโปรเจค |
| DF-603 | Document Data Write | P3.5/P3.6 | DS3 | {document_id, project_id, filename, file_path, file_hash, size, content_type, uploader, created_at, updated_at, version, metadata} | การเขียนข้อมูลเอกสาร |
| DF-604 | File Storage Write | P3.3 | DS6 | {file_path: string, file_content: binary, metadata: object} | การจัดเก็บไฟล์ |
| DF-605 | Parsed Config Write | P3.4 | DS4 | {device_name, config_type, parsed_data: object, upload_timestamp, project_id, document_id} | การเขียนข้อมูลคอนฟิกที่แยกวิเคราะห์ |
| DF-606 | Folder Data Write | P4.2/P4.3/P4.4 | DS7 | {folder_id, project_id, name, parent_id?, created_at, updated_at, deleted: boolean} | การเขียนข้อมูลโฟลเดอร์ |
| DF-607 | LLM Result Write | P5.6/P5.8 | DS5 | {analysis_id, project_id, device_name, analysis_type, ai_draft, human_review?, verified_version?, status, llm_metrics, accuracy_metrics?, created_at, created_by} | การเขียนผลการวิเคราะห์ LLM |
| DF-608 | Topology Data Write | P6.6 | DS8 | {project_id, topology_id, nodes: array, links: array, layout: object, created_at, updated_by} | การเขียนข้อมูล Topology |
| DF-609 | Script Data Write | P8.5 | DS9 | {script_id, project_id, device_ids: array, template_type, script_content, customizations, created_at, created_by} | การเขียนข้อมูล Script |

#### Read Operations (Data Store → Process)

| Flow ID | Data Flow Name | Source | Destination | Data Structure | Description |
|---------|---------------|--------|--------------|----------------|-------------|
| DF-701 | User Data Read | DS1 | P1.2/P1.6/P1.7/P2.2 | {username, email, password_hash, role, created_at, last_login_at} | การอ่านข้อมูลผู้ใช้ |
| DF-702 | Project Data Read | DS2 | P2.7/P2.9/P7.2 | {project_id, name, description, created_by, created_at, members: array, visibility, status} | การอ่านข้อมูลโปรเจค |
| DF-703 | Document Data Read | DS3 | P3.7/P4.5 | {document_id, project_id, filename, file_path, file_hash, size, content_type, uploader, created_at, version, metadata} | การอ่านข้อมูลเอกสาร |
| DF-704 | File Storage Read | DS6 | P3.7 | {file_path: string, file_content: binary} | การอ่านไฟล์จาก storage |
| DF-705 | Parsed Config Read | DS4 | P5.2/P6.2/P7.3/P8.2 | {device_name, config_type, parsed_data: object, upload_timestamp, project_id, interfaces: array, neighbors: array} | การอ่านข้อมูลคอนฟิกที่แยกวิเคราะห์ |
| DF-706 | Folder Data Read | DS7 | P4.6 | {folders: array[{folder_id, name, parent_id, children: array}]} | การอ่านข้อมูลโฟลเดอร์ |
| DF-707 | LLM Result Read | DS5 | P5.7/P7.4 | {analysis_id, project_id, device_name, analysis_type, ai_draft, human_review?, verified_version?, status, llm_metrics, accuracy_metrics} | การอ่านผลการวิเคราะห์ LLM |
| DF-708 | Topology Data Read | DS8 | P6.7/P6.8 | {topology_id, nodes: array, links: array, layout: object, created_at} | การอ่านข้อมูล Topology |
| DF-709 | Script Data Read | DS9 | P8.3/P8.8 | {script_id, project_id, device_ids: array, template_type, script_content, customizations} | การอ่านข้อมูล Script |

## 2. Data Stores Dictionary

### 2.1 D1: Users Collection

| Field Name | Data Type | Description | Constraints |
|------------|------------|-------------|--------------|
| _id | ObjectId | Primary key | Auto-generated |
| username | String | Unique username | Required, Unique |
| email | String | User email address | Required, Unique |
| password_hash | String | Hashed password | Required |
| role | String | User role | Required, Enum: ["admin", "manager", "engineer", "viewer"] |
| phone_number | String | Phone number | Optional |
| created_at | DateTime | Account creation timestamp | Required |
| last_login_at | DateTime | Last login timestamp | Optional |
| updated_at | DateTime | Last update timestamp | Required |

### 2.2 D2: Projects Collection

| Field Name | Data Type | Description | Constraints |
|------------|------------|-------------|--------------|
| _id | ObjectId | Primary key | Auto-generated |
| project_id | String | Unique project identifier | Required, Unique |
| name | String | Project name | Required |
| description | String | Project description | Optional |
| created_by | String | Creator username | Required |
| created_at | DateTime | Creation timestamp | Required |
| updated_at | DateTime | Last update timestamp | Required |
| visibility | String | Project visibility | Required, Enum: ["Public", "Private"] |
| backup_interval | String | Backup frequency | Required, Enum: ["Daily", "Weekly", "Monthly"] |
| status | String | Project status | Required, Enum: ["Planning", "Active", "Completed", "Archived"] |
| members | Array | Project members | Required, [{username, role, joined_at}] |
| topo_url | String | Topology URL | Optional |

### 2.3 D3: Documents Collection

| Field Name | Data Type | Description | Constraints |
|------------|------------|-------------|--------------|
| _id | ObjectId | Primary key | Auto-generated |
| document_id | String | Unique document identifier | Required, Unique |
| project_id | String | Project identifier | Required |
| filename | String | Original filename | Required |
| file_path | String | Storage file path | Required |
| file_hash | String | SHA-256 file hash | Required |
| size | Number | File size in bytes | Required |
| content_type | String | MIME content type | Required |
| uploader | String | Uploader username | Required |
| created_at | DateTime | Upload timestamp | Required |
| updated_at | DateTime | Last update timestamp | Required |
| version | Number | Document version | Required |
| parent_document_id | String | Parent document ID | Optional |
| upload_batch_id | String | Upload batch identifier | Required |
| metadata | Object | Document metadata | Required |
| folder_id | String | Folder identifier | Optional |
| is_latest | Boolean | Latest version flag | Required |

### 2.4 D4: Parsed Configs Collection

| Field Name | Data Type | Description | Constraints |
|------------|------------|-------------|--------------|
| _id | ObjectId | Primary key | Auto-generated |
| device_name | String | Device name | Required |
| project_id | String | Project identifier | Required |
| document_id | String | Source document ID | Required |
| config_type | String | Configuration type | Required, Enum: ["cisco", "huawei"] |
| parsed_data | Object | Parsed configuration data | Required |
| interfaces | Array | Network interfaces | Required |
| neighbors | Array | Neighbor devices | Required |
| upload_timestamp | DateTime | Upload timestamp | Required |
| parser_version | String | Parser version | Required |

### 2.5 D5: LLM Results Collection

| Field Name | Data Type | Description | Constraints |
|------------|------------|-------------|--------------|
| _id | ObjectId | Primary key | Auto-generated |
| analysis_id | String | Unique analysis identifier | Required, Unique |
| project_id | String | Project identifier | Required |
| device_name | String | Device name | Required |
| analysis_type | String | Analysis type | Required, Enum: ["security_audit", "performance_review", "configuration_compliance", "network_topology", "best_practices", "custom"] |
| context_data | Object | Analysis context | Required |
| ai_draft | Object | AI-generated draft | Required |
| ai_draft_text | String | Full AI response | Required |
| status | String | Analysis status | Required, Enum: ["pending_review", "verified", "rejected"] |
| human_review | Object | Human review data | Optional |
| verified_version | Object | Final verified version | Optional |
| llm_metrics | Object | LLM performance metrics | Required |
| accuracy_metrics | Object | Accuracy tracking | Optional |
| created_at | DateTime | Creation timestamp | Required |
| created_by | String | Creator username | Required |
| updated_at | DateTime | Last update timestamp | Required |

### 2.6 D6: File Storage

| Field Name | Data Type | Description | Constraints |
|------------|------------|-------------|--------------|
| file_path | String | Storage file path | Primary Key |
| file_content | Binary | File binary content | Required |
| metadata | Object | File metadata | Optional |
| created_at | DateTime | Creation timestamp | Required |
| access_count | Number | Access counter | Optional |

### 2.7 D7: Folders Collection

| Field Name | Data Type | Description | Constraints |
|------------|------------|-------------|--------------|
| _id | ObjectId | Primary key | Auto-generated |
| folder_id | String | Unique folder identifier | Required, Unique |
| project_id | String | Project identifier | Required |
| name | String | Folder name | Required |
| parent_id | String | Parent folder ID | Optional |
| created_at | DateTime | Creation timestamp | Required |
| updated_at | DateTime | Last update timestamp | Required |
| deleted | Boolean | Deletion flag | Required, Default: false |

### 2.8 D8: Topology Collection

| Field Name | Data Type | Description | Constraints |
|------------|------------|-------------|--------------|
| _id | ObjectId | Primary key | Auto-generated |
| topology_id | String | Unique topology identifier | Required, Unique |
| project_id | String | Project identifier | Required |
| nodes | Array | Network nodes | Required |
| links | Array | Network links | Required |
| layout | Object | Layout positions | Required |
| created_at | DateTime | Creation timestamp | Required |
| updated_by | String | Last updater | Required |
| updated_at | DateTime | Last update timestamp | Required |

### 2.9 D9: Scripts Collection

| Field Name | Data Type | Description | Constraints |
|------------|------------|-------------|--------------|
| _id | ObjectId | Primary key | Auto-generated |
| script_id | String | Unique script identifier | Required, Unique |
| project_id | String | Project identifier | Required |
| device_ids | Array | Target device IDs | Required |
| template_type | String | Template type | Required |
| script_content | String | Generated script content | Required |
| customizations | Object | Custom command modifications | Optional |
| created_at | DateTime | Creation timestamp | Required |
| created_by | String | Creator username | Required |

## 3. External Entities Dictionary

### 3.1 USER - Users

| Attribute | Data Type | Description | Values |
|-----------|------------|-------------|---------|
| user_types | Array | User role types | ["admin", "manager", "engineer", "viewer"] |
| authentication_methods | Array | Available auth methods | ["username/password", "email/otp"] |
| permissions | Object | Role-based permissions | {admin: ["all"], manager: ["project_management", "member_management"], engineer: ["document_upload", "analysis_request"], viewer: ["read_only"]} |

### 3.2 LLM - Ollama LLM Service

| Attribute | Data Type | Description | Values |
|-----------|------------|-------------|---------|
| model_name | String | LLM model name | "qwen2.5-coder" |
| model_version | String | Model version | "latest" |
| capabilities | Array | Supported capabilities | ["configuration_analysis", "security_audit", "recommendation_generation"] |
| input_limits | Object | Input constraints | {max_tokens: 32000, max_devices: 20} |

### 3.3 EMAIL - SMTP Email Service

| Attribute | Data Type | Description | Values |
|-----------|------------|-------------|---------|
| protocol | String | Email protocol | "SMTP" |
| supported_formats | Array | Supported formats | ["text", "html"] |
| functions | Array | Available functions | ["otp_sending", "notifications", "password_reset"] |
