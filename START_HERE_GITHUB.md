# 🚀 เริ่มต้นที่นี่ - GitHub Workflow

คู่มือสั้นๆ สำหรับการใช้งานโปรเจคผ่าน GitHub ระหว่าง Windows PC และ Ubuntu Server

## ⚡ Quick Start

### Windows PC (Development)

```powershell
# 1. Clone repository
git clone https://github.com/your-username/WebAppNMLLM.git
cd WebAppNMLLM

# 2. Setup
.\scripts\windows\setup-windows.ps1

# 3. Start
docker compose up -d

# 4. Access: http://localhost:5173
```

### Ubuntu Server (Production)

```bash
# 1. Clone repository
git clone https://github.com/your-username/WebAppNMLLM.git
cd WebAppNMLLM

# 2. Setup (ครั้งแรก)
./scripts/ubuntu/setup-ubuntu-server.sh

# 3. Deploy
./scripts/ubuntu/deploy.sh

# 4. Access: http://your-server-ip
```

## 🔄 Workflow ทุกวัน

### บน Windows PC

```powershell
# 1. Pull latest
git pull origin main

# 2. Develop
# แก้ไขโค้ด...

# 3. Commit และ push
.\scripts\windows\update-and-push.ps1 "feat: Add new feature"
```

### บน Ubuntu Server

```bash
# Pull และ deploy
./scripts/ubuntu/deploy.sh
```

## 📚 เอกสารที่ควรอ่าน

1. **[QUICK_START_GITHUB.md](QUICK_START_GITHUB.md)** - Quick Start Guide
2. **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - คู่มือการ Deploy แบบละเอียด
3. **[GITHUB_SETUP.md](GITHUB_SETUP.md)** - การตั้งค่า GitHub
4. **[PREPARE_FOR_GITHUB.md](PREPARE_FOR_GITHUB.md)** - Checklist ก่อน Upload

## ✅ พร้อมใช้งาน!

โปรเจคพร้อมใช้งานทั้งบน Windows PC และ Ubuntu Server แล้ว!
