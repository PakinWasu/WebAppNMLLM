# Quick Reference - คำสั่งที่ใช้บ่อย

เอกสารสรุปคำสั่งที่ใช้บ่อยสำหรับการพัฒนาและ deploy

## 🪟 Windows PC (Development)

### Git Commands

```powershell
# ตรวจสอบสถานะ
git status

# Pull latest changes
git pull origin main

# เพิ่มไฟล์
git add .

# Commit
git commit -m "Description"

# Push
git push origin main

# ดู history
git log --oneline
```

### Docker Commands

```powershell
# Start services
docker compose up -d

# Stop services
docker compose down

# View logs
docker compose logs -f

# View logs ของ service เฉพาะ
docker compose logs -f backend
docker compose logs -f frontend

# Restart service
docker compose restart backend

# Rebuild
docker compose build
docker compose up -d --build
```

### Scripts

```powershell
# เริ่ม development environment
.\scripts\windows\dev-start.ps1

# Push ไป GitHub
.\scripts\windows\git-push.ps1 -Message "Your commit message"

# Push โดยไม่ทดสอบ
.\scripts\windows\git-push.ps1 -Message "Your commit message" -SkipTest
```

### Access URLs

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **MongoDB**: localhost:27017

## 🐧 Ubuntu Server (Production)

### Git Commands

```bash
# Pull latest changes
git pull origin main

# ตรวจสอบสถานะ
git status

# ดู history
git log --oneline

# Rollback
git checkout <commit-hash>
```

### Docker Commands

```bash
# Start services
docker compose -f docker-compose.prod.yml up -d

# Stop services
docker compose -f docker-compose.prod.yml down

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Restart service
docker compose -f docker-compose.prod.yml restart backend

# Rebuild และ restart
docker compose -f docker-compose.prod.yml up -d --build
```

### Deploy Script

```bash
# Pull และ deploy
./scripts/ubuntu/deploy.sh

# หรือ manual
git pull origin main
docker compose -f docker-compose.prod.yml up -d --build
```

### Backup

```bash
# Backup MongoDB
docker exec mnp-mongo-prod mongodump --archive=/backup/backup-$(date +%Y%m%d).archive
docker cp mnp-mongo-prod:/backup/backup-$(date +%Y%m%d).archive ./backup-$(date +%Y%m%d).archive
```

### Access URLs

- **Frontend**: http://your-server-ip หรือ http://your-domain.com
- **Backend API**: http://your-server-ip:8000/docs
- **MongoDB**: localhost:27017 (internal only)

## 🔄 Typical Workflow

### บน Windows PC

```powershell
# 1. เริ่มทำงาน
.\scripts\windows\dev-start.ps1

# 2. พัฒนาโค้ด
# ... แก้ไขไฟล์ ...

# 3. ทดสอบ
# ... ทดสอบบน localhost ...

# 4. Commit และ Push
.\scripts\windows\git-push.ps1 -Message "Add new feature"
```

### บน Ubuntu Server

```bash
# 1. SSH เข้า server
ssh user@your-server-ip

# 2. ไปที่โฟลเดอร์โปรเจค
cd /path/to/WebAppNMLLM

# 3. Pull และ Deploy
./scripts/ubuntu/deploy.sh

# หรือ manual
git pull origin main
docker compose -f docker-compose.prod.yml up -d --build
```

## 🐛 Troubleshooting

### Windows

```powershell
# Docker ไม่ทำงาน
# เปิด Docker Desktop

# Port ถูกใช้งาน
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Git authentication
# ใช้ Personal Access Token หรือ SSH key
```

### Ubuntu

```bash
# ตรวจสอบ services
docker compose -f docker-compose.prod.yml ps

# ดู logs
docker compose -f docker-compose.prod.yml logs -f

# Restart service
docker compose -f docker-compose.prod.yml restart <service-name>

# ตรวจสอบ disk space
df -h

# ลบ unused Docker resources
docker system prune -a
```

## 📝 Environment Variables

### สร้าง .env จาก template

**Windows:**
```powershell
Copy-Item backend\.env.example backend\.env
# แก้ไข backend\.env
```

**Ubuntu:**
```bash
cp backend/.env.example backend/.env
# แก้ไข backend/.env
nano backend/.env
```

### สร้าง JWT_SECRET

**Windows (PowerShell):**
```powershell
-join ((65..90) + (97..122) + (48..57) | Get-Random -Count 64 | ForEach-Object {[char]$_})
```

**Ubuntu (Bash):**
```bash
openssl rand -hex 32
```

## 🔗 Links

- **GitHub**: https://github.com/PakinWasu/WebAppNMLLM
- **API Docs**: http://localhost:8000/docs (local) หรือ http://your-server:8000/docs (production)

## 📚 เอกสารเพิ่มเติม

- `WINDOWS_DEVELOPMENT.md` - คู่มือการพัฒนาบน Windows
- `GITHUB_WORKFLOW.md` - Workflow ผ่าน GitHub
- `README.md` - เอกสารหลัก
