# 🚀 เริ่มต้นใช้งานที่นี่!

## ✅ ระบบพร้อมใช้งานแล้ว!

ระบบได้ถูกตั้งค่าเรียบร้อยแล้ว คุณสามารถเริ่มใช้งานได้เลย

## 📋 ขั้นตอนการใช้งาน

### 1. เริ่ม Development Environment

เปิด PowerShell ในโฟลเดอร์โปรเจค แล้วรัน:

```powershell
.\scripts\windows\dev-start.ps1
```

หรือใช้คำสั่ง Docker โดยตรง:

```powershell
docker compose up -d
```

### 2. เข้าถึง Application

หลังจาก services เริ่มทำงานแล้ว (รอประมาณ 30-60 วินาที):

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **MongoDB**: localhost:27017

### 3. Login

- **Username**: `admin`
- **Password**: `admin123`

⚠️ **เปลี่ยนรหัสผ่านทันทีหลังจาก login ครั้งแรก!**

## 🔄 Workflow การพัฒนา

### พัฒนาโค้ด

1. แก้ไขไฟล์ตามต้องการ
2. ทดสอบบน localhost
3. เมื่อพร้อมแล้ว commit และ push:

```powershell
.\scripts\windows\git-push.ps1 -Message "Description of changes"
```

### Deploy บน Ubuntu Server

1. SSH เข้า server
2. Pull และ deploy:

```bash
cd /path/to/WebAppNMLLM
./scripts/ubuntu/deploy.sh
```

## 📝 คำสั่งที่ใช้บ่อย

### Docker Commands

```powershell
# ดู logs
docker compose logs -f

# หยุด services
docker compose down

# Restart services
docker compose restart

# Rebuild
docker compose up -d --build
```

### Git Commands

```powershell
# ตรวจสอบสถานะ
git status

# Pull latest changes
git pull origin main

# Push changes
.\scripts\windows\git-push.ps1 -Message "Your message"
```

## 🐛 การแก้ไขปัญหา

### Services ไม่ทำงาน

```powershell
# ตรวจสอบสถานะ
docker compose ps

# ดู logs
docker compose logs -f

# Restart
docker compose restart
```

### Port ถูกใช้งานแล้ว

```powershell
# ตรวจสอบ port
netstat -ano | findstr :8000
netstat -ano | findstr :5173

# หยุด process (ใช้ PID จากคำสั่งด้านบน)
taskkill /PID <PID> /F
```

### Docker ไม่ทำงาน

1. เปิด Docker Desktop
2. รอให้ Docker เริ่มทำงาน (ไอคอน Docker ใน system tray ต้องเป็นสีเขียว)
3. ลองรัน `docker ps` เพื่อตรวจสอบ

## 📚 เอกสารเพิ่มเติม

- **WINDOWS_DEVELOPMENT.md** - คู่มือการพัฒนาบน Windows
- **GITHUB_WORKFLOW.md** - Workflow ผ่าน GitHub
- **QUICK_REFERENCE.md** - Quick Reference
- **README.md** - เอกสารหลัก

## ✅ Checklist

- [x] ไฟล์ `.env` ถูกสร้างแล้ว
- [x] JWT_SECRET ถูกสร้างแล้ว
- [x] โฟลเดอร์ `storage` ถูกสร้างแล้ว
- [x] Scripts พร้อมใช้งาน
- [x] Docker ติดตั้งแล้ว
- [x] Git ติดตั้งแล้ว

## 🎉 พร้อมใช้งาน!

เริ่มต้นด้วยการรัน:

```powershell
.\scripts\windows\dev-start.ps1
```

หรือ

```powershell
docker compose up -d
```

**Happy Coding! 🚀**
