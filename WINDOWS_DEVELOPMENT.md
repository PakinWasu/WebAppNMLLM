# การพัฒนาโปรเจคบน Windows PC

เอกสารนี้สำหรับการตั้งค่าและพัฒนาโปรเจคบน Windows PC แล้ว sync ไปยัง Ubuntu Server ผ่าน GitHub

## 📋 สารบัญ

- [ความต้องการของระบบ](#ความต้องการของระบบ)
- [การติดตั้ง Tools ที่จำเป็น](#การติดตั้ง-tools-ที่จำเป็น)
- [การตั้งค่าโปรเจค](#การตั้งค่าโปรเจค)
- [การรัน Development Mode](#การรัน-development-mode)
- [Workflow ผ่าน GitHub](#workflow-ผ่าน-github)
- [การแก้ไขปัญหา](#การแก้ไขปัญหา)

## 🛠️ ความต้องการของระบบ

### Software ที่ต้องติดตั้ง

1. **Git for Windows**
   - ดาวน์โหลด: https://git-scm.com/download/win
   - หรือใช้: `winget install Git.Git`

2. **Docker Desktop for Windows**
   - ดาวน์โหลด: https://www.docker.com/products/docker-desktop
   - หรือใช้: `winget install Docker.DockerDesktop`
   - ต้องเปิดใช้งาน WSL 2 backend

3. **Visual Studio Code** (แนะนำ)
   - ดาวน์โหลด: https://code.visualstudio.com/
   - หรือใช้: `winget install Microsoft.VisualStudioCode`

4. **Node.js** (ถ้าต้องการรัน frontend แบบ local)
   - ดาวน์โหลด: https://nodejs.org/ (แนะนำ LTS version)
   - หรือใช้: `winget install OpenJS.NodeJS.LTS`

5. **Python** (ถ้าต้องการรัน backend แบบ local)
   - ดาวน์โหลด: https://www.python.org/downloads/
   - หรือใช้: `winget install Python.Python.3.11`

## 🚀 การติดตั้ง Tools ที่จำเป็น

### 1. ติดตั้ง Git

```powershell
# ตรวจสอบว่า Git ติดตั้งแล้วหรือยัง
git --version

# ถ้ายังไม่มี ติดตั้งผ่าน winget
winget install Git.Git

# ตั้งค่า Git (ถ้ายังไม่ได้ตั้งค่า)
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### 2. ติดตั้ง Docker Desktop

```powershell
# ตรวจสอบว่า Docker ติดตั้งแล้วหรือยัง
docker --version

# ถ้ายังไม่มี ติดตั้งผ่าน winget
winget install Docker.DockerDesktop
```

**หลังติดตั้ง Docker Desktop:**
1. เปิด Docker Desktop
2. ไปที่ Settings > General
3. เปิดใช้งาน "Use the WSL 2 based engine"
4. ไปที่ Settings > Resources > WSL Integration
5. เปิดใช้งาน integration กับ WSL distro ที่ใช้

### 3. Clone โปรเจค (ถ้ายังไม่ได้ clone)

```powershell
# ไปที่โฟลเดอร์ที่ต้องการ
cd D:\0.Project End

# Clone จาก GitHub
git clone https://github.com/PakinWasu/WebAppNMLLM.git
cd WebAppNMLLM
```

## ⚙️ การตั้งค่าโปรเจค

### 1. ตั้งค่า Environment Variables

สร้างไฟล์ `.env` ในโฟลเดอร์ `backend/`:

```powershell
# สร้างไฟล์ .env
cd backend
New-Item -Path .env -ItemType File -Force
```

เนื้อหาที่ต้องตั้งค่า (ใช้ Notepad หรือ VS Code):

```env
# MongoDB
MONGODB_URI=mongodb://mongodb:27017
MONGODB_DB_NAME=manage_network_projects

# JWT Security (⚠️ เปลี่ยนเป็นค่าที่ปลอดภัย!)
JWT_SECRET=your-very-secure-random-secret-key-minimum-32-characters
JWT_ALG=HS256
ACCESS_TOKEN_EXPIRE_MIN=1440

# AI Model (Ollama)
AI_MODEL_NAME=qwen2.5:7b
AI_MODEL_VERSION=v1-desktop
AI_MODEL_ENDPOINT=http://host.docker.internal:11434
```

**สร้าง JWT_SECRET ที่ปลอดภัย:**

```powershell
# ใช้ PowerShell สร้าง random secret
-join ((65..90) + (97..122) + (48..57) | Get-Random -Count 64 | ForEach-Object {[char]$_})
```

### 2. ตรวจสอบ Git Remote

```powershell
# ตรวจสอบ remote repository
git remote -v

# ควรเห็น:
# origin  https://github.com/PakinWasu/WebAppNMLLM.git (fetch)
# origin  https://github.com/PakinWasu/WebAppNMLLM.git (push)
```

## 💻 การรัน Development Mode

### วิธีที่ 1: ใช้ Docker Compose (แนะนำ)

```powershell
# ตรวจสอบว่า Docker ทำงาน
docker ps

# Start services
docker compose up -d

# ดู logs
docker compose logs -f

# ดู logs ของ service เฉพาะ
docker compose logs -f backend
docker compose logs -f frontend
```

**เข้าถึง Application:**
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **MongoDB**: localhost:27017

### วิธีที่ 2: รันแบบ Local (ไม่ใช้ Docker)

#### Backend (Python)

```powershell
# ไปที่โฟลเดอร์ backend
cd backend

# สร้าง virtual environment
python -m venv venv

# เปิดใช้งาน virtual environment
.\venv\Scripts\Activate.ps1

# ติดตั้ง dependencies
pip install -r requirements.txt

# รัน server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend (Node.js)

```powershell
# ไปที่โฟลเดอร์ frontend
cd frontend

# ติดตั้ง dependencies
npm install

# รัน development server
npm run dev
```

## 🔄 Workflow ผ่าน GitHub

ดูเอกสาร `GITHUB_WORKFLOW.md` สำหรับรายละเอียด

### สรุป Workflow

1. **พัฒนาโค้ดบน Windows PC**
2. **Commit และ Push ไป GitHub**
3. **Pull บน Ubuntu Server และ Deploy**

### คำสั่งพื้นฐาน

```powershell
# ตรวจสอบสถานะ
git status

# เพิ่มไฟล์ที่แก้ไข
git add .

# Commit
git commit -m "Description of changes"

# Push ไป GitHub
git push origin main

# Pull จาก GitHub (ถ้ามีคนอื่น push)
git pull origin main
```

## 🔧 การแก้ไขปัญหา

### Docker ไม่ทำงาน

```powershell
# ตรวจสอบว่า Docker Desktop เปิดอยู่
Get-Process "Docker Desktop" -ErrorAction SilentlyContinue

# Restart Docker Desktop
# เปิด Docker Desktop แล้วรอให้เริ่มทำงาน
```

### Port ถูกใช้งานแล้ว

```powershell
# ตรวจสอบ port ที่ใช้งาน
netstat -ano | findstr :8000
netstat -ano | findstr :5173
netstat -ano | findstr :27017

# หยุด process ที่ใช้ port (ใช้ PID จากคำสั่งด้านบน)
taskkill /PID <PID> /F
```

### MongoDB Connection Error

```powershell
# ตรวจสอบว่า MongoDB container ทำงาน
docker ps | Select-String mongo

# ตรวจสอบ logs
docker logs mnp-mongo

# Restart MongoDB
docker compose restart mongodb
```

### Git Authentication Error

```powershell
# ใช้ Personal Access Token แทน password
# สร้าง token ที่: https://github.com/settings/tokens

# ตั้งค่า credential helper
git config --global credential.helper wincred

# หรือใช้ SSH key (แนะนำ)
# สร้าง SSH key
ssh-keygen -t ed25519 -C "your.email@example.com"

# เพิ่ม SSH key ไป GitHub
# คัดลอก public key: cat ~/.ssh/id_ed25519.pub
# เพิ่มที่: https://github.com/settings/keys

# เปลี่ยน remote URL เป็น SSH
git remote set-url origin git@github.com:PakinWasu/WebAppNMLLM.git
```

### WSL 2 Issues

```powershell
# ตรวจสอบ WSL version
wsl --list --verbose

# อัปเดต WSL
wsl --update

# ตั้งค่า default version เป็น WSL 2
wsl --set-default-version 2
```

### Storage Permissions

```powershell
# สร้างโฟลเดอร์ storage (ถ้ายังไม่มี)
New-Item -ItemType Directory -Force -Path storage

# ตั้งค่า permissions (Windows)
icacls storage /grant Everyone:F /T
```

## 📝 หมายเหตุ

- **ใช้ Docker Compose V2**: คำสั่งคือ `docker compose` (มี space) ไม่ใช่ `docker-compose`
- **Line Endings**: Git จะจัดการ CRLF/LF อัตโนมัติ แต่ถ้ามีปัญหา ใช้ `git config --global core.autocrlf true`
- **File Permissions**: Windows ไม่สนับสนุน Unix permissions แต่ Docker จะจัดการให้
- **Path Separators**: ใช้ `/` หรือ `\` ใน PowerShell ได้ทั้งคู่

## 📚 เอกสารเพิ่มเติม

- `GITHUB_WORKFLOW.md` - Workflow ผ่าน GitHub
- `README.md` - เอกสารหลัก
- `QUICK_START.md` - Quick Start Guide
