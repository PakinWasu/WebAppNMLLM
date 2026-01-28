# GitHub Workflow - การทำงานผ่าน GitHub

เอกสารนี้อธิบาย workflow สำหรับการพัฒนาโปรเจคบน Windows PC และ deploy บน Ubuntu Server ผ่าน GitHub

## 📋 สารบัญ

- [ภาพรวม Workflow](#ภาพรวม-workflow)
- [การตั้งค่า Git](#การตั้งค่า-git)
- [Workflow สำหรับ Windows PC (Development)](#workflow-สำหรับ-windows-pc-development)
- [Workflow สำหรับ Ubuntu Server (Production)](#workflow-สำหรับ-ubuntu-server-production)
- [Best Practices](#best-practices)
- [การแก้ไขปัญหา](#การแก้ไขปัญหา)

## 🎯 ภาพรวม Workflow

```
┌─────────────────┐         ┌──────────┐         ┌──────────────────┐
│  Windows PC     │         │  GitHub  │         │  Ubuntu Server   │
│  (Development)  │────────▶│ (Central)│────────▶│  (Production)    │
└─────────────────┘         └──────────┘         └──────────────────┘
     │                            │                        │
     │ 1. Develop & Test          │                        │
     │ 2. Commit                  │                        │
     │ 3. Push                    │                        │
     │                            │                        │
     │                            │ 4. Pull                │
     │                            │ 5. Deploy              │
     │                            │                        │
     └────────────────────────────┴────────────────────────┘
```

### ขั้นตอนหลัก

1. **พัฒนาและทดสอบ** บน Windows PC
2. **Commit และ Push** ไปยัง GitHub
3. **Pull และ Deploy** บน Ubuntu Server

## ⚙️ การตั้งค่า Git

### บน Windows PC

```powershell
# ตั้งค่า user information
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# ตั้งค่า default branch
git config --global init.defaultBranch main

# ตั้งค่า credential helper (สำหรับ Windows)
git config --global credential.helper wincred

# ตั้งค่า line endings (Windows)
git config --global core.autocrlf true

# ตรวจสอบ remote
git remote -v
# ควรเห็น:
# origin  https://github.com/PakinWasu/WebAppNMLLM.git (fetch)
# origin  https://github.com/PakinWasu/WebAppNMLLM.git (push)
```

### บน Ubuntu Server

```bash
# ตั้งค่า user information
git config --global user.name "Server User"
git config --global user.email "server@example.com"

# ตั้งค่า credential helper (สำหรับ Linux)
git config --global credential.helper store

# ตั้งค่า line endings (Linux)
git config --global core.autocrlf input

# Clone หรือ pull โปรเจค
git clone https://github.com/PakinWasu/WebAppNMLLM.git
cd WebAppNMLLM
```

### การใช้ SSH Key (แนะนำ)

#### สร้าง SSH Key บน Windows

```powershell
# สร้าง SSH key
ssh-keygen -t ed25519 -C "your.email@example.com"

# ดู public key
cat ~/.ssh/id_ed25519.pub

# คัดลอก public key แล้วเพิ่มไป GitHub:
# https://github.com/settings/keys
```

#### เปลี่ยน Remote URL เป็น SSH

```powershell
# เปลี่ยน remote URL
git remote set-url origin git@github.com:PakinWasu/WebAppNMLLM.git

# ตรวจสอบ
git remote -v
```

## 💻 Workflow สำหรับ Windows PC (Development)

### 1. เริ่มต้นวันทำงาน

```powershell
# ไปที่โฟลเดอร์โปรเจค
cd "D:\0.Project End\WebAppNMLLM"

# Pull latest changes จาก GitHub
git pull origin main

# ตรวจสอบสถานะ
git status
```

### 2. พัฒนาโค้ด

```powershell
# เริ่ม development server
docker compose up -d

# หรือรันแบบ local
# Backend: cd backend && uvicorn app.main:app --reload
# Frontend: cd frontend && npm run dev
```

### 3. ทดสอบการเปลี่ยนแปลง

- ทดสอบบน local: http://localhost:5173
- ตรวจสอบ API: http://localhost:8000/docs
- ทดสอบทุกฟีเจอร์ที่แก้ไข

### 4. Commit และ Push

```powershell
# ตรวจสอบการเปลี่ยนแปลง
git status

# ดู diff
git diff

# เพิ่มไฟล์ที่แก้ไข
git add .

# หรือเพิ่มเฉพาะไฟล์ที่ต้องการ
git add path/to/file1 path/to/file2

# Commit
git commit -m "Description of changes"

# ตัวอย่าง commit messages:
# git commit -m "Add user authentication feature"
# git commit -m "Fix MongoDB connection issue"
# git commit -m "Update frontend UI components"

# Push ไป GitHub
git push origin main
```

### 5. ตรวจสอบบน GitHub

- ไปที่: https://github.com/PakinWasu/WebAppNMLLM
- ตรวจสอบว่า commit ถูก push แล้ว
- ตรวจสอบว่าไม่มี conflicts

## 🚀 Workflow สำหรับ Ubuntu Server (Production)

### 1. SSH เข้า Server

```bash
# SSH เข้า Ubuntu Server
ssh user@your-server-ip

# ไปที่โฟลเดอร์โปรเจค
cd /path/to/WebAppNMLLM
```

### 2. Pull Latest Changes

```bash
# ตรวจสอบสถานะ
git status

# Pull latest changes จาก GitHub
git pull origin main

# ถ้ามี conflicts จะต้องแก้ไขก่อน
```

### 3. Backup (แนะนำก่อน Deploy)

```bash
# Backup MongoDB
docker exec mnp-mongo-prod mongodump --archive=/backup/backup-$(date +%Y%m%d).archive

# หรือใช้ backup script
./backup.sh
```

### 4. Deploy

```bash
# Rebuild และ restart services
docker compose -f docker-compose.prod.yml up -d --build

# หรือ rebuild เฉพาะ service ที่เปลี่ยน
docker compose -f docker-compose.prod.yml build backend
docker compose -f docker-compose.prod.yml up -d backend
```

### 5. ตรวจสอบการ Deploy

```bash
# ตรวจสอบสถานะ services
docker compose -f docker-compose.prod.yml ps

# ดู logs
docker compose -f docker-compose.prod.yml logs -f

# ทดสอบ API
curl http://localhost:8000/docs
```

### 6. Rollback (ถ้าจำเป็น)

```bash
# กลับไป commit ก่อนหน้า
git log  # หา commit hash
git checkout <previous-commit-hash>

# Rebuild
docker compose -f docker-compose.prod.yml up -d --build

# หรือใช้ tag
git tag -a v1.0.0 -m "Stable version"
git push origin v1.0.0

# Rollback ไป tag
git checkout v1.0.0
docker compose -f docker-compose.prod.yml up -d --build
```

## 📝 Best Practices

### 1. Commit Messages

ใช้รูปแบบที่ชัดเจน:

```
<type>: <subject>

<body>

<footer>
```

**Types:**
- `feat`: ฟีเจอร์ใหม่
- `fix`: แก้ไข bug
- `docs`: เอกสาร
- `style`: formatting
- `refactor`: refactoring
- `test`: tests
- `chore`: maintenance

**ตัวอย่าง:**
```
feat: Add user authentication with JWT

- Add login endpoint
- Add JWT token generation
- Add protected routes

Closes #123
```

### 2. Branch Strategy (ถ้าต้องการ)

```powershell
# สร้าง branch สำหรับ feature
git checkout -b feature/user-authentication

# พัฒนาและ commit
git add .
git commit -m "feat: Add user authentication"

# Push branch
git push origin feature/user-authentication

# สร้าง Pull Request บน GitHub
# Merge ผ่าน GitHub แล้ว pull main บน server
```

### 3. .gitignore

ตรวจสอบว่าไฟล์ต่อไปนี้อยู่ใน `.gitignore`:

- `.env` - Environment variables
- `node_modules/` - Node dependencies
- `__pycache__/` - Python cache
- `mongo-data/` - Database data
- `storage/` - Application storage
- `*.log` - Log files

### 4. Environment Variables

**อย่า commit `.env` ไป GitHub!**

สร้างไฟล์ `.env.example`:

```env
# MongoDB
MONGODB_URI=mongodb://mongodb:27017
MONGODB_DB_NAME=manage_network_projects

# JWT Security
JWT_SECRET=your-secret-key-here
JWT_ALG=HS256
ACCESS_TOKEN_EXPIRE_MIN=1440

# AI Model (แนะนำ qwen2.5-coder:32b สำหรับ Network Configuration Analysis)
# สำหรับ Development บน Host: ใช้ http://host.docker.internal:11434
AI_MODEL_NAME=qwen2.5-coder:32b
AI_MODEL_VERSION=v2-coder-32b
AI_MODEL_ENDPOINT=http://host.docker.internal:11434
```

### 5. Testing ก่อน Push

```powershell
# ทดสอบ backend
cd backend
python -m pytest  # ถ้ามี tests

# ทดสอบ frontend
cd frontend
npm run build  # ตรวจสอบว่า build ผ่าน

# ทดสอบ Docker
docker compose build
docker compose up -d
# ทดสอบว่า services ทำงานได้
```

## 🔧 การแก้ไขปัญหา

### Merge Conflicts

```powershell
# บน Windows PC
git pull origin main
# ถ้ามี conflicts
# แก้ไขไฟล์ที่มี conflicts
git add .
git commit -m "Resolve merge conflicts"
git push origin main
```

### Push ถูก Reject

```powershell
# Pull ก่อน push
git pull origin main --rebase
git push origin main
```

### ลืม Commit บางไฟล์

```powershell
# เพิ่มไฟล์ที่ลืม
git add forgotten-file.py
git commit --amend --no-edit
git push origin main --force  # ระวัง! ใช้เฉพาะเมื่อแน่ใจ
```

### Server ไม่มี Internet

```bash
# บน Server: Pull จาก GitHub ผ่าน SSH tunnel หรือ
# Copy ไฟล์จาก Windows PC ผ่าน SCP

# จาก Windows PC
scp -r "D:\0.Project End\WebAppNMLLM" user@server:/path/to/
```

### Git Credentials Expired

```powershell
# Windows: ลบ saved credentials
# Control Panel > Credential Manager > Windows Credentials
# ลบ GitHub credentials

# หรือใช้ Personal Access Token
# สร้างที่: https://github.com/settings/tokens
```

## 📚 เอกสารเพิ่มเติม

- `WINDOWS_DEVELOPMENT.md` - การพัฒนาบน Windows
- `README.md` - เอกสารหลัก
- `QUICK_START.md` - Quick Start Guide
