# 🚀 คู่มือใช้งานโปรเจคให้ทำงานได้ปกติ

## ⚡ เริ่มต้นใช้งานทันที

### 1. Setup และ Start Services

```bash
# วิธีที่ 1: ใช้สคริปต์อัตโนมัติ (แนะนำ)
./setup-and-start.sh

# วิธีที่ 2: ใช้ Docker Compose โดยตรง
docker-compose up -d --build
```

### 2. ตรวจสอบและแก้ไขปัญหาอัตโนมัติ

```bash
# ตรวจสอบสถานะทั้งหมดและแก้ไขปัญหาอัตโนมัติ
./check-and-fix.sh
```

สคริปต์นี้จะ:
- ✅ ตรวจสอบไฟล์ .env
- ✅ ตรวจสอบ Docker containers
- ✅ ตรวจสอบ MongoDB, Backend, Ollama
- ✅ ตรวจสอบโมเดล LLM และดาวน์โหลดถ้ายังไม่มี
- ✅ ทดสอบการเชื่อมต่อระหว่าง services

### 3. Pull โมเดล LLM (ถ้ายังไม่ได้ pull)

```bash
# ใช้สคริปต์อัตโนมัติ
./pull-llm-model.sh

# หรือใช้คำสั่งโดยตรง
docker exec mnp-ollama-prod ollama pull qwen2.5-coder:32b
```

## 🔍 ตรวจสอบสถานะ

### ตรวจสอบ Health Check

```bash
# ตรวจสอบ Backend
curl http://localhost:8000/

# ตรวจสอบ LLM Service
curl http://localhost:8000/health/llm

# ตรวจสอบ Ollama
curl http://localhost:11434/api/tags
```

### ตรวจสอบ Logs

```bash
# Backend logs
docker logs mnp-backend-prod -f

# Ollama logs
docker logs mnp-ollama-prod -f

# MongoDB logs
docker logs mnp-mongo-prod -f

# ทั้งหมด
docker-compose logs -f
```

## 🔧 แก้ไขปัญหาที่พบบ่อย

### ปัญหา: Backend ไม่สามารถเชื่อมต่อกับ Ollama

**ตรวจสอบ:**
```bash
# 1. ตรวจสอบว่า Ollama container ทำงาน
docker ps | grep ollama

# 2. ตรวจสอบ network connectivity
docker exec mnp-backend-prod ping -c 3 ollama

# 3. ตรวจสอบ endpoint ใน .env
docker exec mnp-backend-prod env | grep AI_MODEL_ENDPOINT
# ควรแสดง: AI_MODEL_ENDPOINT=http://ollama:11434

# 4. ทดสอบการเชื่อมต่อ
docker exec mnp-backend-prod curl http://ollama:11434/api/tags
```

**แก้ไข:**
- ตรวจสอบว่า Ollama container อยู่ใน network เดียวกัน: `docker network inspect mnp-network`
- Restart services: `docker-compose restart`

### ปัญหา: โมเดลไม่พบ (404 Not Found)

**แก้ไข:**
```bash
# Pull โมเดล
./pull-llm-model.sh

# หรือ
docker exec mnp-ollama-prod ollama pull qwen2.5-coder:32b

# ตรวจสอบว่าโมเดลมีอยู่แล้ว
docker exec mnp-ollama-prod ollama list
```

### ปัญหา: Response ช้ามากหรือ Timeout

**สาเหตุที่เป็นไปได้:**
- โมเดลขนาดใหญ่ (32B) ใช้เวลานานในการ inference
- ไม่มี GPU (ใช้ CPU เท่านั้น)

**แก้ไข:**
- รอให้โมเดลทำงานเสร็จ (อาจใช้เวลาหลายนาที)
- หรือเปลี่ยนเป็นโมเดลที่เล็กกว่าใน `.env`:
  ```env
  AI_MODEL_NAME=qwen2.5-coder:14b  # หรือ 7b
  ```

### ปัญหา: Permission Denied

**แก้ไข:**
```bash
# เพิ่ม user เข้า docker group
sudo usermod -aG docker $USER
newgrp docker

# หรือใช้ sudo
sudo ./setup-and-start.sh
```

## 📋 URLs สำหรับเข้าใช้งาน

- **Frontend**: http://localhost:5173 (dev) หรือ http://localhost:8080 (prod)
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health/llm
- **Ollama API**: http://localhost:11434

## 👤 ข้อมูล Login

- **Username**: `admin`
- **Password**: `admin123`

⚠️ **เปลี่ยนรหัสผ่านทันทีหลังจาก login ครั้งแรก!**

## 🧪 ทดสอบการทำงานของ LLM

### 1. ทดสอบผ่าน API

```bash
# ทดสอบ basic connection
curl http://localhost:8000/ai/test

# ตรวจสอบ health
curl http://localhost:8000/health/llm
```

### 2. ทดสอบผ่าน Frontend

1. Login ที่ http://localhost:5173
2. สร้าง Project
3. Upload network configuration file
4. สร้าง Analysis และดูผลลัพธ์

### 3. ทดสอบโดยตรงกับ Ollama

```bash
docker exec mnp-ollama-prod ollama run qwen2.5-coder:32b "Analyze this network configuration: interface GigabitEthernet0/0/1 ip address 192.168.1.1 255.255.255.0"
```

## 📝 คำสั่งที่มีประโยชน์

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart services
docker-compose restart

# Rebuild และ start
docker-compose up -d --build

# ดูสถานะ
docker-compose ps

# ตรวจสอบและแก้ไขปัญหา
./check-and-fix.sh

# Pull โมเดล LLM
./pull-llm-model.sh
```

## 🆘 ต้องการความช่วยเหลือเพิ่มเติม?

1. รัน `./check-and-fix.sh` เพื่อตรวจสอบปัญหาอัตโนมัติ
2. ตรวจสอบ logs: `docker-compose logs -f`
3. อ่านเอกสาร: [LLM_SETUP.md](LLM_SETUP.md)
4. ดู troubleshooting: [README.md#การแก้ไขปัญหา](README.md#การแก้ไขปัญหา)
