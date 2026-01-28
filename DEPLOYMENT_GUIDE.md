# 🚀 Deployment Guide - คู่มือการ Deploy

คู่มือสำหรับการ deploy โปรเจคบน Windows PC (Development) และ Ubuntu Server (Production)

## 📋 สารบัญ

- [Quick Start](#quick-start)
- [Windows PC Setup (Development)](#windows-pc-setup-development)
- [Ubuntu Server Setup (Production)](#ubuntu-server-setup-production)
- [GitHub Workflow](#github-workflow)
- [Deployment Scripts](#deployment-scripts)
- [Troubleshooting](#troubleshooting)

## ⚡ Quick Start

### Windows PC (Development)

```powershell
# 1. Clone repository
git clone https://github.com/your-username/WebAppNMLLM.git
cd WebAppNMLLM

# 2. Setup environment
cd backend
copy .env.example .env
# แก้ไข .env ตามต้องการ

# 3. Start development
cd ..
docker compose up -d

# 4. Access
# Frontend: http://localhost:5173
# Backend: http://localhost:8000/docs
```

### Ubuntu Server (Production)

```bash
# 1. Clone repository
git clone https://github.com/your-username/WebAppNMLLM.git
cd WebAppNMLLM

# 2. Run setup script
chmod +x scripts/ubuntu/setup-ubuntu-server.sh
./scripts/ubuntu/setup-ubuntu-server.sh

# 3. Setup environment
cd backend
cp .env.example .env
nano .env  # แก้ไขตามต้องการ

# 4. Deploy
cd ..
docker compose -f docker-compose.prod.yml up -d --build

# 5. Access
# Frontend: http://your-server-ip
# Backend: http://your-server-ip:8000/docs
```

## 💻 Windows PC Setup (Development)

### Prerequisites

- Windows 10/11
- Docker Desktop
- Git
- VS Code (แนะนำ)

### Step-by-Step Setup

#### 1. Install Docker Desktop

1. Download จาก: https://www.docker.com/products/docker-desktop
2. Install และ restart
3. เปิด Docker Desktop

#### 2. Clone Repository

```powershell
git clone https://github.com/your-username/WebAppNMLLM.git
cd WebAppNMLLM
```

#### 3. Setup Environment

```powershell
cd backend
copy .env.example .env
notepad .env  # แก้ไขตามต้องการ
```

#### 4. Start Development

```powershell
# ใช้ Docker Compose (แนะนำ)
docker compose up -d

# หรือใช้ script
.\scripts\windows\dev-start.ps1
```

#### 5. Access Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000/docs
- **MongoDB**: localhost:27017

### Development Workflow

```powershell
# 1. Pull latest changes
git pull origin main

# 2. Make changes
# แก้ไขโค้ดใน VS Code

# 3. Test locally
docker compose restart backend  # ถ้าแก้ backend
docker compose restart frontend # ถ้าแก้ frontend

# 4. Commit and push
git add .
git commit -m "Description of changes"
git push origin main
```

## 🐧 Ubuntu Server Setup (Production)

### Prerequisites

- Ubuntu 20.04 LTS หรือใหม่กว่า
- SSH access
- sudo privileges

### Step-by-Step Setup

#### 1. Initial Setup (ครั้งแรกเท่านั้น)

```bash
# Clone repository
git clone https://github.com/your-username/WebAppNMLLM.git
cd WebAppNMLLM

# Run automated setup
chmod +x scripts/ubuntu/setup-ubuntu-server.sh
./scripts/ubuntu/setup-ubuntu-server.sh
```

สคริปต์จะทำการ:
- ✅ ติดตั้ง Docker และ Docker Compose
- ✅ ติดตั้ง Nginx และ dependencies
- ✅ ตั้งค่า Firewall
- ✅ สร้างไฟล์ .env
- ✅ สร้าง directories ที่จำเป็น

#### 2. Configure Environment

```bash
cd backend
cp .env.example .env
nano .env
```

**สำคัญ**: เปลี่ยน `JWT_SECRET` เป็นค่าที่ปลอดภัย:
```bash
openssl rand -hex 32
```

#### 3. Deploy

```bash
cd ..
docker compose -f docker-compose.prod.yml up -d --build
```

#### 4. Setup Nginx (ถ้ายังไม่ได้ตั้งค่า)

```bash
sudo bash scripts/ubuntu/complete-fix.sh
```

#### 5. Access Application

- **Frontend**: http://your-server-ip
- **Backend API**: http://your-server-ip:8000/docs
- **Default Login**: admin / admin123

### Production Workflow

```bash
# 1. SSH เข้า server
ssh user@your-server-ip

# 2. Pull latest changes
cd /path/to/WebAppNMLLM
git pull origin main

# 3. Deploy (ใช้ script)
chmod +x scripts/ubuntu/deploy.sh
./scripts/ubuntu/deploy.sh

# หรือ deploy manually
docker compose -f docker-compose.prod.yml up -d --build
```

## 🔄 GitHub Workflow

### Development → Production

```
Windows PC                    GitHub                    Ubuntu Server
    │                           │                            │
    │ 1. Develop & Test         │                            │
    │──────────────────────────▶│                            │
    │ 2. Commit & Push          │                            │
    │──────────────────────────▶│                            │
    │                           │ 3. Pull                    │
    │                           │───────────────────────────▶│
    │                           │ 4. Deploy                  │
    │                           │───────────────────────────▶│
    │                           │                            │
```

### Step-by-Step

#### บน Windows PC

```powershell
# 1. Pull latest (ถ้ามีคนอื่น push)
git pull origin main

# 2. Develop
# แก้ไขโค้ด...

# 3. Test
docker compose restart

# 4. Commit
git add .
git commit -m "feat: Add new feature"
git push origin main
```

#### บน Ubuntu Server

```bash
# 1. Pull latest
git pull origin main

# 2. Deploy
docker compose -f docker-compose.prod.yml up -d --build

# 3. Verify
docker compose -f docker-compose.prod.yml ps
curl http://localhost:8000/docs
```

## 📜 Deployment Scripts

### Windows Scripts

#### `scripts/windows/dev-start.ps1`
เริ่ม development environment

```powershell
.\scripts\windows\dev-start.ps1
```

#### `scripts/windows/git-push.ps1`
Commit และ push ไป GitHub

```powershell
.\scripts\windows\git-push.ps1 "Commit message"
```

### Ubuntu Scripts

#### `scripts/ubuntu/setup-ubuntu-server.sh`
ติดตั้งและตั้งค่า Ubuntu Server (ครั้งแรกเท่านั้น)

```bash
./scripts/ubuntu/setup-ubuntu-server.sh
```

#### `scripts/ubuntu/deploy.sh`
Pull และ deploy บน Ubuntu Server

```bash
./scripts/ubuntu/deploy.sh
```

#### `scripts/ubuntu/complete-fix.sh`
แก้ไขปัญหาและตั้งค่า nginx

```bash
sudo bash scripts/ubuntu/complete-fix.sh
```

## 🔧 Troubleshooting

### Windows Issues

#### Docker ไม่ทำงาน
```powershell
# Restart Docker Desktop
# หรือ
docker-compose down
docker-compose up -d
```

#### Port ถูกใช้งานแล้ว
```powershell
# ตรวจสอบ port
netstat -ano | findstr :8000
netstat -ano | findstr :5173

# หยุด process ที่ใช้ port
taskkill /PID <PID> /F
```

### Ubuntu Issues

#### Permission Denied
```bash
# เพิ่ม user เข้า docker group
sudo usermod -aG docker $USER
newgrp docker
```

#### Nginx ไม่ทำงาน
```bash
# ตรวจสอบ config
sudo nginx -t

# Restart
sudo systemctl restart nginx

# ดู logs
sudo tail -f /var/log/nginx/error.log
```

#### Container ไม่ start
```bash
# ดู logs
docker compose -f docker-compose.prod.yml logs

# Restart
docker compose -f docker-compose.prod.yml restart

# Rebuild
docker compose -f docker-compose.prod.yml up -d --build
```

## 📝 Best Practices

### 1. Environment Variables

- ✅ ใช้ `.env.example` เป็น template
- ✅ อย่า commit `.env` ไป GitHub
- ✅ ใช้ค่าที่แตกต่างกันระหว่าง dev และ prod

### 2. Git Workflow

- ✅ Commit บ่อยๆ พร้อม message ที่ชัดเจน
- ✅ Pull ก่อน push เสมอ
- ✅ Test ก่อน push

### 3. Deployment

- ✅ Backup ก่อน deploy (บน production)
- ✅ Deploy ในเวลาที่มีผู้ใช้น้อย
- ✅ Monitor logs หลัง deploy

### 4. Security

- ✅ เปลี่ยน default passwords
- ✅ ใช้ JWT_SECRET ที่ปลอดภัย
- ✅ ตั้งค่า firewall
- ✅ ใช้ HTTPS ใน production

## 📚 เอกสารเพิ่มเติม

- **[GITHUB_WORKFLOW.md](GITHUB_WORKFLOW.md)** - Workflow แบบละเอียด
- **[WINDOWS_DEVELOPMENT.md](WINDOWS_DEVELOPMENT.md)** - การพัฒนาบน Windows
- **[UBUNTU_SERVER_SETUP.md](UBUNTU_SERVER_SETUP.md)** - การตั้งค่าบน Ubuntu Server
- **[README.md](README.md)** - เอกสารหลัก

## 🆘 Support

ถ้ามีปัญหา:
1. ตรวจสอบ logs: `docker compose logs`
2. ดูเอกสาร troubleshooting
3. ตรวจสอบ GitHub Issues
