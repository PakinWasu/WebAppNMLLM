# ⚡ Quick Start - GitHub Workflow

คู่มือสั้นๆ สำหรับการทำงานกับ GitHub ระหว่าง Windows PC และ Ubuntu Server

## 🚀 สำหรับ Windows PC (Development)

### ครั้งแรก

```powershell
# 1. Clone repository
git clone https://github.com/your-username/WebAppNMLLM.git
cd WebAppNMLLM

# 2. Setup
.\scripts\windows\setup-windows.ps1

# 3. Start development
docker compose up -d

# 4. Access
# Frontend: http://localhost:5173
# Backend: http://localhost:8000/docs
```

### ทุกวัน

```powershell
# 1. Pull latest
git pull origin main

# 2. Develop
# แก้ไขโค้ด...

# 3. Commit และ push
.\scripts\windows\update-and-push.ps1 "feat: Add new feature"

# หรือ manual
git add .
git commit -m "feat: Add new feature"
git push origin main
```

## 🐧 สำหรับ Ubuntu Server (Production)

### ครั้งแรก

```bash
# 1. Clone repository
git clone https://github.com/your-username/WebAppNMLLM.git
cd WebAppNMLLM

# 2. Setup (ใช้สคริปต์อัตโนมัติ)
chmod +x scripts/ubuntu/setup-ubuntu-server.sh
./scripts/ubuntu/setup-ubuntu-server.sh

# 3. Setup environment
cd backend
cp .env.example .env
nano .env  # แก้ไขตามต้องการ

# 4. Deploy
cd ..
docker compose -f docker-compose.prod.yml up -d --build

# 5. Setup nginx
sudo bash scripts/ubuntu/complete-fix.sh
```

### อัปเดตโค้ด

```bash
# ใช้สคริปต์อัตโนมัติ (แนะนำ)
chmod +x scripts/ubuntu/deploy.sh
./scripts/ubuntu/deploy.sh

# หรือ manual
git pull origin main
docker compose -f docker-compose.prod.yml up -d --build
```

## 🔄 Workflow

```
Windows PC                    GitHub                    Ubuntu Server
    │                           │                            │
    │ 1. Develop                │                            │
    │ 2. Commit & Push ────────▶│                            │
    │                           │ 3. Pull                    │
    │                           │───────────────────────────▶│
    │                           │ 4. Deploy                  │
    │                           │───────────────────────────▶│
```

## 📝 คำสั่งที่ใช้บ่อย

### Windows

```powershell
# Pull latest
git pull origin main

# Commit และ push
git add .
git commit -m "Description"
git push origin main

# Start development
docker compose up -d

# Stop
docker compose down
```

### Ubuntu

```bash
# Pull และ deploy
git pull origin main
docker compose -f docker-compose.prod.yml up -d --build

# หรือใช้ script
./scripts/ubuntu/deploy.sh

# ดู logs
docker compose -f docker-compose.prod.yml logs -f

# Restart
docker compose -f docker-compose.prod.yml restart
```

## ✅ Checklist

### ก่อน Push

- [ ] ทดสอบว่าโค้ดทำงานได้
- [ ] ตรวจสอบว่าไม่มี sensitive data
- [ ] Commit message ที่ชัดเจน

### หลัง Pull บน Server

- [ ] Backup (ถ้าจำเป็น)
- [ ] Rebuild containers
- [ ] ตรวจสอบ logs
- [ ] ทดสอบ endpoints

## 📚 เอกสารเพิ่มเติม

- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - คู่มือการ deploy แบบละเอียด
- **[GITHUB_WORKFLOW.md](GITHUB_WORKFLOW.md)** - Workflow แบบละเอียด
- **[GITHUB_SETUP.md](GITHUB_SETUP.md)** - การตั้งค่า GitHub
