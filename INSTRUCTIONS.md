# 📋 คำแนะนำการเริ่มต้นใช้งาน

## ✅ สิ่งที่เตรียมไว้ให้แล้ว

1. ✅ ไฟล์ `backend/.env` พร้อม JWT_SECRET ที่ปลอดภัย
2. ✅ Directories ที่จำเป็น (storage, mongo-data, mongo-backup)
3. ✅ สคริปต์ setup อัตโนมัติ

## 🚀 วิธีเริ่มต้นใช้งาน

### วิธีที่ 1: แก้ไข Docker Permission (แนะนำ)

```bash
# เพิ่ม user เข้า docker group
sudo usermod -aG docker $USER

# ออกจาก session และ login ใหม่ หรือใช้คำสั่งนี้:
newgrp docker

# ตรวจสอบว่าเข้า group แล้ว
groups | grep docker

# รันสคริปต์ setup
./setup-and-start.sh
```

### วิธีที่ 2: ใช้ sudo (ถ้าวิธีที่ 1 ไม่ได้)

```bash
# ใช้สคริปต์ที่เตรียมไว้ให้
./run-with-sudo.sh

# หรือรันคำสั่ง Docker โดยตรง
sudo docker-compose up -d --build
```

### วิธีที่ 3: รันคำสั่งทีละขั้นตอน

```bash
# 1. Build และ Start services
sudo docker-compose up -d --build

# 2. ตรวจสอบสถานะ
sudo docker-compose ps

# 3. Pull โมเดล LLM
sudo docker exec mnp-ollama ollama pull qwen2.5-coder:32b

# 4. สร้าง admin user
sudo docker exec mnp-backend python /app/scripts/seed_admin.py
```

## 📋 หลังจาก Start Services แล้ว

### ตรวจสอบสถานะ

```bash
# Development
docker-compose ps

# Production  
docker-compose -f docker-compose.prod.yml ps
```

### Pull โมเดล LLM

```bash
# ใช้สคริปต์
./pull-llm-model.sh

# หรือใช้คำสั่งโดยตรง
docker exec mnp-ollama ollama pull qwen2.5-coder:32b
```

### เข้าใช้งาน

- **Frontend**: http://localhost:5173 (dev) หรือ http://localhost:8080 (prod)
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Login**: `admin` / `admin123`

## 🔧 แก้ไขปัญหา

### ปัญหา: Permission denied

ดูที่: [FIX_DOCKER_PERMISSION.md](FIX_DOCKER_PERMISSION.md)

### ปัญหา: Port ถูกใช้งานแล้ว

```bash
# ตรวจสอบ port
sudo netstat -tulpn | grep :8000
sudo netstat -tulpn | grep :5173

# หยุด service ที่ใช้ port
sudo kill -9 <PID>
```

### ปัญหา: Container ไม่ start

```bash
# ดู logs
docker-compose logs

# หรือ
sudo docker-compose logs
```

## 📚 เอกสารเพิ่มเติม

- [START_NOW.md](START_NOW.md) - คู่มือเริ่มต้นใช้งาน
- [LLM_SETUP.md](LLM_SETUP.md) - คู่มือการตั้งค่า LLM
- [README.md](README.md) - คู่มือหลัก
