# 🚀 เริ่มต้นใช้งานทันที

## ⚡ วิธีที่ง่ายที่สุด (แนะนำ)

### 1. Setup และ Start ทุกอย่าง

```bash
# Development mode (แนะนำสำหรับการพัฒนา)
./setup-and-start.sh

# หรือ Production mode (สำหรับ production)
./setup-and-start.sh prod
```

สคริปต์นี้จะทำทุกอย่างให้อัตโนมัติ:
- ✅ สร้างไฟล์ `.env` พร้อม JWT_SECRET ที่ปลอดภัย
- ✅ สร้าง directories ที่จำเป็น
- ✅ Build และ start Docker containers
- ✅ รอให้ services พร้อมใช้งาน
- ✅ Pull โมเดล LLM (ถ้ายังไม่มี)
- ✅ สร้าง admin user

### 2. Pull โมเดล LLM (ถ้ายังไม่ได้ pull)

```bash
# Pull โมเดลที่กำหนดใน .env (qwen2.5-coder:32b)
./pull-llm-model.sh

# หรือ pull โมเดลอื่น
./pull-llm-model.sh llama3:8b
```

### 3. เข้าใช้งาน

**Development Mode:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

**Production Mode:**
- Frontend: http://localhost:8080
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

**ข้อมูล Login:**
- Username: `admin`
- Password: `admin123`

⚠️ **เปลี่ยนรหัสผ่านทันทีหลังจาก login ครั้งแรก!**

## 📋 คำสั่งที่มีประโยชน์

### ดูสถานะ Services

```bash
# Development
docker-compose ps

# Production
docker-compose -f docker-compose.prod.yml ps
```

### ดู Logs

```bash
# ทั้งหมด
docker-compose logs -f

# เฉพาะ backend
docker-compose logs -f backend

# เฉพาะ frontend
docker-compose logs -f frontend

# เฉพาะ ollama
docker-compose logs -f ollama
```

### Restart Services

```bash
# Restart ทั้งหมด
docker-compose restart

# Restart เฉพาะ service
docker-compose restart backend
```

### Stop Services

```bash
# Development
docker-compose down

# Production
docker-compose -f docker-compose.prod.yml down
```

### Quick Start (ครั้งถัดไป)

ถ้า setup แล้วและต้องการ start ใหม่:

```bash
./quick-start.sh        # Development mode
./quick-start.sh prod   # Production mode
```

## 🔧 การแก้ไขปัญหา

### ปัญหา: Permission denied เมื่อรัน Docker

**แก้ไข:**
```bash
# เพิ่ม user เข้า docker group
sudo usermod -aG docker $USER
newgrp docker

# หรือใช้ sudo
sudo ./setup-and-start.sh
```

### ปัญหา: Port ถูกใช้งานแล้ว

**แก้ไข:**
- ตรวจสอบ port ที่ใช้งาน: `sudo netstat -tulpn | grep :8000`
- หยุด service ที่ใช้ port นั้น
- หรือแก้ไข port ใน docker-compose.yml

### ปัญหา: Ollama ไม่สามารถ pull โมเดลได้

**แก้ไข:**
```bash
# Pull ด้วยตนเอง
docker exec mnp-ollama-prod ollama pull qwen2.5-coder:32b

# หรือใช้สคริปต์
./pull-llm-model.sh
```

### ปัญหา: Backend ไม่สามารถเชื่อมต่อกับ Ollama

**ตรวจสอบ:**
1. ตรวจสอบว่า Ollama container ทำงาน: `docker ps | grep ollama`
2. ตรวจสอบ endpoint ใน `.env`: `cat backend/.env | grep AI_MODEL_ENDPOINT`
   - ควรเป็น: `AI_MODEL_ENDPOINT=http://ollama:11434`
3. ตรวจสอบ logs: `docker logs mnp-ollama-prod`

## 📚 เอกสารเพิ่มเติม

- **[README.md](README.md)** - คู่มือหลัก
- **[LLM_SETUP.md](LLM_SETUP.md)** - คู่มือการตั้งค่า LLM แบบละเอียด
- **[QUICK_START.md](QUICK_START.md)** - Quick Start Guide แบบละเอียด
- **[WINDOWS_DEVELOPMENT.md](WINDOWS_DEVELOPMENT.md)** - สำหรับ Windows

## 🆘 ต้องการความช่วยเหลือ?

1. ตรวจสอบ logs: `docker-compose logs -f`
2. ตรวจสอบสถานะ: `docker-compose ps`
3. อ่านเอกสาร: [README.md](README.md)
4. ดู troubleshooting: [README.md#การแก้ไขปัญหา](README.md#การแก้ไขปัญหา)
