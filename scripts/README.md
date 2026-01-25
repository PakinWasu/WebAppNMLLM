# Scripts Directory

โฟลเดอร์นี้เก็บ scripts สำหรับช่วยในการพัฒนาและ deploy

## 📁 โครงสร้าง

```
scripts/
├── windows/          # PowerShell scripts สำหรับ Windows PC
│   ├── dev-start.ps1    # เริ่ม development environment
│   └── git-push.ps1     # Push โค้ดไป GitHub
└── ubuntu/           # Bash scripts สำหรับ Ubuntu Server
    └── deploy.sh        # Pull และ deploy บน Ubuntu Server
```

## 🪟 Windows Scripts

### dev-start.ps1

สคริปต์สำหรับเริ่ม development environment บน Windows

**Usage:**
```powershell
.\scripts\windows\dev-start.ps1
```

**Features:**
- ตรวจสอบ Docker
- Pull latest changes (optional)
- Start Docker services
- ตรวจสอบ service health
- แสดง URLs สำหรับเข้าถึง

### git-push.ps1

สคริปต์สำหรับ commit และ push โค้ดไป GitHub

**Usage:**
```powershell
# ใช้ commit message ที่ถาม
.\scripts\windows\git-push.ps1

# ระบุ commit message
.\scripts\windows\git-push.ps1 -Message "Add new feature"

# Skip tests
.\scripts\windows\git-push.ps1 -Message "Quick fix" -SkipTest
```

**Features:**
- ตรวจสอบ git status
- Pull ก่อน push
- Commit และ push
- แสดง next steps

## 🐧 Ubuntu Scripts

### deploy.sh

สคริปต์สำหรับ pull และ deploy บน Ubuntu Server

**Usage:**
```bash
# ให้ executable permission
chmod +x scripts/ubuntu/deploy.sh

# Run
./scripts/ubuntu/deploy.sh
```

**Features:**
- Backup MongoDB (optional)
- Pull latest changes
- Rebuild และ restart services
- ตรวจสอบ service health
- แสดง deployment status

## 🔧 การแก้ไขปัญหา

### Windows Scripts

**Error: Execution Policy**

```powershell
# ตั้งค่า execution policy
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Error: Script not found**

```powershell
# ตรวจสอบ path
Get-Location
# ควรอยู่ที่ root ของโปรเจค
```

### Ubuntu Scripts

**Error: Permission denied**

```bash
# ให้ executable permission
chmod +x scripts/ubuntu/deploy.sh
```

**Error: Command not found**

```bash
# ตรวจสอบว่า docker compose ติดตั้งแล้ว
docker compose version
```

## 📝 หมายเหตุ

- Scripts เหล่านี้เป็น helper scripts เท่านั้น
- สามารถแก้ไขได้ตามความต้องการ
- ควรทดสอบก่อนใช้ใน production
