# 📦 GitHub Repository Setup

คู่มือสำหรับการเตรียมโปรเจคให้พร้อม upload ไป GitHub และใช้งานได้ทั้งบน Windows PC และ Ubuntu Server

## 🚀 Quick Start

### 1. Initialize Git Repository (ถ้ายังไม่มี)

```bash
# บน Windows หรือ Ubuntu
git init
git branch -M main
git remote add origin https://github.com/your-username/WebAppNMLLM.git
```

### 2. First Commit

```bash
# ตรวจสอบไฟล์ที่จะ commit
git status

# เพิ่มไฟล์ทั้งหมด
git add .

# Commit
git commit -m "Initial commit: Network Project Platform"

# Push ไป GitHub
git push -u origin main
```

## 📁 โครงสร้างโปรเจค

```
WebAppNMLLM/
├── backend/              # FastAPI Backend
│   ├── app/             # Application code
│   ├── .env.example     # Environment template
│   ├── Dockerfile       # Docker image
│   └── requirements.txt # Python dependencies
│
├── frontend/            # React Frontend
│   ├── src/            # Source code
│   ├── Dockerfile      # Development
│   ├── Dockerfile.prod # Production
│   └── package.json    # Node dependencies
│
├── scripts/            # Deployment scripts
│   ├── windows/        # Windows PowerShell scripts
│   └── ubuntu/         # Ubuntu Bash scripts
│
├── docker-compose.yml           # Development
├── docker-compose.prod.yml      # Production
├── .gitignore          # Git ignore rules
└── README.md          # Main documentation
```

## 🔄 Workflow: Windows ↔ Ubuntu Server

### Development บน Windows PC

```powershell
# 1. Clone หรือ pull
git pull origin main

# 2. พัฒนาโค้ด
# แก้ไขไฟล์...

# 3. ทดสอบ
docker compose up -d

# 4. Commit และ push
git add .
git commit -m "feat: Add new feature"
git push origin main
```

### Deploy บน Ubuntu Server

```bash
# 1. Pull latest
cd /path/to/WebAppNMLLM
git pull origin main

# 2. Deploy
docker compose -f docker-compose.prod.yml up -d --build
```

## 📝 ไฟล์ที่สำคัญ

### ต้องมีใน Repository

- ✅ `backend/.env.example` - Template สำหรับ environment variables
- ✅ `docker-compose.yml` - Development configuration
- ✅ `docker-compose.prod.yml` - Production configuration
- ✅ `.gitignore` - Git ignore rules
- ✅ `README.md` - เอกสารหลัก
- ✅ `scripts/` - Deployment scripts

### ไม่ควร commit

- ❌ `backend/.env` - Environment variables (มี secrets)
- ❌ `node_modules/` - Node dependencies
- ❌ `mongo-data/` - Database data
- ❌ `storage/` - Application storage
- ❌ `*.log` - Log files

## 🔐 Security Checklist

ก่อน push ไป GitHub:

- [ ] ตรวจสอบว่าไม่มี `.env` ใน repository
- [ ] ตรวจสอบว่าไม่มี passwords/secrets ในโค้ด
- [ ] ตรวจสอบว่า `.gitignore` ครอบคลุมไฟล์ที่ sensitive
- [ ] ใช้ `.env.example` แทน `.env`

## 📚 เอกสารที่ควรมี

- [x] `README.md` - เอกสารหลัก
- [x] `DEPLOYMENT_GUIDE.md` - คู่มือการ deploy
- [x] `GITHUB_WORKFLOW.md` - Workflow การทำงาน
- [x] `WINDOWS_DEVELOPMENT.md` - การพัฒนาบน Windows
- [x] `UBUNTU_SERVER_SETUP.md` - การตั้งค่าบน Ubuntu Server

## 🛠️ Scripts ที่มีให้

### Windows (`scripts/windows/`)

- `setup-windows.ps1` - ติดตั้งและตั้งค่า Windows PC
- `dev-start.ps1` - เริ่ม development environment
- `update-and-push.ps1` - Pull, commit, และ push
- `git-push.ps1` - Push ไป GitHub

### Ubuntu (`scripts/ubuntu/`)

- `setup-ubuntu-server.sh` - ติดตั้งและตั้งค่า Ubuntu Server
- `deploy.sh` - Pull และ deploy
- `complete-fix.sh` - แก้ไขปัญหาและตั้งค่า nginx

## ✅ Checklist ก่อน Push

- [ ] ทดสอบว่าโค้ดทำงานได้บน Windows
- [ ] ทดสอบว่าโค้ดทำงานได้บน Ubuntu (ถ้าเป็นไปได้)
- [ ] ตรวจสอบว่าไม่มี sensitive data ในโค้ด
- [ ] ตรวจสอบว่า `.gitignore` ถูกต้อง
- [ ] อัปเดตเอกสาร (ถ้ามีการเปลี่ยนแปลง)
- [ ] Commit message ที่ชัดเจน

## 🎯 Best Practices

### Commit Messages

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

### Branch Strategy (Optional)

```bash
# สร้าง branch สำหรับ feature
git checkout -b feature/new-feature

# พัฒนาและ commit
git add .
git commit -m "feat: Add new feature"

# Push branch
git push origin feature/new-feature

# สร้าง Pull Request บน GitHub
# Merge ผ่าน GitHub แล้ว pull main บน server
```

## 📞 Support

ถ้ามีปัญหา:
1. ตรวจสอบ logs
2. ดูเอกสาร troubleshooting
3. ตรวจสอบ GitHub Issues
