# 🚀 GitHub Setup Guide

คู่มือสำหรับการตั้งค่าและ upload โปรเจคไป GitHub

## 📋 สารบัญ

- [การเตรียมโปรเจค](#การเตรียมโปรเจค)
- [การสร้าง Repository บน GitHub](#การสร้าง-repository-บน-github)
- [การ Push โปรเจค](#การ-push-โปรเจค)
- [การทำงาน Cross-Platform](#การทำงาน-cross-platform)
- [Best Practices](#best-practices)

## 🔧 การเตรียมโปรเจค

### 1. ตรวจสอบไฟล์ที่ต้องมี

```bash
# ตรวจสอบว่าไฟล์สำคัญมีครบ
ls -la backend/.env.example
ls -la docker-compose.yml
ls -la docker-compose.prod.yml
ls -la .gitignore
ls -la README.md
```

### 2. ตรวจสอบ .gitignore

```bash
# ตรวจสอบว่าไฟล์ sensitive ไม่ถูก track
git status
# ไม่ควรเห็น:
# - backend/.env
# - node_modules/
# - mongo-data/
# - storage/
```

### 3. สร้างไฟล์ .env.example (ถ้ายังไม่มี)

```bash
# Copy .env.example จาก backend
cp backend/.env.example backend/.env.example.backup
```

## 🌐 การสร้าง Repository บน GitHub

### 1. สร้าง Repository ใหม่

1. ไปที่: https://github.com/new
2. ตั้งชื่อ repository: `WebAppNMLLM`
3. เลือก Public หรือ Private
4. **อย่า** check "Initialize with README"
5. Click "Create repository"

### 2. Copy Repository URL

```
https://github.com/your-username/WebAppNMLLM.git
```

## 📤 การ Push โปรเจค

### บน Windows PC

```powershell
# 1. Initialize git (ถ้ายังไม่มี)
git init
git branch -M main

# 2. Add remote
git remote add origin https://github.com/your-username/WebAppNMLLM.git

# 3. Add files
git add .

# 4. Commit
git commit -m "Initial commit: Network Project Platform"

# 5. Push
git push -u origin main
```

### บน Ubuntu Server

```bash
# 1. Clone repository
git clone https://github.com/your-username/WebAppNMLLM.git
cd WebAppNMLLM

# 2. Setup และ deploy
chmod +x scripts/ubuntu/setup-ubuntu-server.sh
./scripts/ubuntu/setup-ubuntu-server.sh
```

## 🔄 การทำงาน Cross-Platform

### Windows → GitHub → Ubuntu

```
Windows PC              GitHub              Ubuntu Server
    │                     │                      │
    │ 1. Develop          │                      │
    │ 2. Commit           │                      │
    │ 3. Push ────────────▶│                      │
    │                     │ 4. Pull              │
    │                     │─────────────────────▶│
    │                     │ 5. Deploy            │
    │                     │─────────────────────▶│
```

### Workflow

#### บน Windows PC

```powershell
# 1. Pull latest (ถ้ามีคนอื่น push)
git pull origin main

# 2. Develop
# แก้ไขโค้ด...

# 3. Test
docker compose up -d

# 4. Commit และ push
git add .
git commit -m "feat: Add new feature"
git push origin main
```

#### บน Ubuntu Server

```bash
# 1. Pull latest
cd /path/to/WebAppNMLLM
git pull origin main

# 2. Deploy
docker compose -f docker-compose.prod.yml up -d --build

# หรือใช้ script
./scripts/ubuntu/deploy.sh
```

## 📝 Best Practices

### 1. Commit Messages

ใช้รูปแบบที่ชัดเจน:

```
<type>: <subject>

<body>
```

**ตัวอย่าง:**
```
feat: Add user authentication

- Add login endpoint
- Add JWT token generation
- Add protected routes
```

### 2. Branch Strategy

```bash
# Main branch สำหรับ production
main

# Feature branches
feature/user-authentication
feature/project-management

# Hotfix branches
hotfix/critical-bug-fix
```

### 3. Environment Variables

- ✅ ใช้ `.env.example` เป็น template
- ✅ อย่า commit `.env` ไป GitHub
- ✅ ใช้ค่าที่แตกต่างกันระหว่าง dev และ prod

### 4. Testing

```powershell
# บน Windows: ทดสอบก่อน push
docker compose build
docker compose up -d
# ทดสอบทุกฟีเจอร์

# บน Ubuntu: ทดสอบหลัง deploy
docker compose -f docker-compose.prod.yml ps
curl http://localhost:8000/docs
```

## 🔐 Security

### Checklist ก่อน Push

- [ ] ไม่มี `.env` ใน repository
- [ ] ไม่มี passwords/secrets ในโค้ด
- [ ] `.gitignore` ครอบคลุมไฟล์ sensitive
- [ ] ใช้ `.env.example` แทน `.env`

### การจัดการ Secrets

```bash
# ใช้ environment variables
export JWT_SECRET="your-secret"

# หรือใช้ .env (ไม่ commit)
echo "JWT_SECRET=your-secret" > backend/.env
```

## 🛠️ Scripts ที่มีให้

### Windows

- `scripts/windows/setup-windows.ps1` - ติดตั้ง Windows PC
- `scripts/windows/update-and-push.ps1` - Pull, commit, push

### Ubuntu

- `scripts/ubuntu/setup-ubuntu-server.sh` - ติดตั้ง Ubuntu Server
- `scripts/ubuntu/deploy.sh` - Pull และ deploy

## 📚 เอกสารเพิ่มเติม

- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - คู่มือการ deploy
- **[GITHUB_WORKFLOW.md](GITHUB_WORKFLOW.md)** - Workflow แบบละเอียด
- **[README.md](README.md)** - เอกสารหลัก

## ✅ Checklist สุดท้าย

ก่อน push ไป GitHub:

- [ ] ทดสอบว่าโค้ดทำงานได้
- [ ] ตรวจสอบว่าไม่มี sensitive data
- [ ] ตรวจสอบว่า `.gitignore` ถูกต้อง
- [ ] อัปเดตเอกสาร
- [ ] Commit message ที่ชัดเจน

## 🎉 พร้อมแล้ว!

โปรเจคพร้อม upload ไป GitHub แล้ว!

```bash
git add .
git commit -m "Initial commit: Network Project Platform"
git push -u origin main
```
