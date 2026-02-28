# Network Project Platform

แพลตฟอร์มจัดการโปรเจคเครือข่าย (Network Project Management Platform) — ใช้ LLM (Ollama) สำหรับวิเคราะห์ config และ topology

## ความต้องการของระบบ

- **Docker** และ **Docker Compose**
- (Production) Ubuntu 20.04 LTS+ แนะนำ RAM 8GB+ สำหรับ LLM

## วิธีรัน

### 1. ตั้งค่า Backend

สร้างไฟล์ `backend/.env` (ดู `backend/.env.example`):

```env
MONGODB_URI=mongodb://mongodb:27017
MONGODB_DB_NAME=manage_network_projects
JWT_SECRET=<สร้างด้วย openssl rand -hex 32>
JWT_ALG=HS256
ACCESS_TOKEN_EXPIRE_MIN=1440
AI_MODEL_NAME=qwen2.5-coder:7b
AI_MODEL_ENDPOINT=http://ollama:11434
```

### 2. รันด้วย Docker

```bash
# Production
docker compose -f docker-compose.prod.yml up -d --build

# Development
docker compose up -d
```

### 3. อัปเดตแล้ว restart

หลังแก้โค้ด / .env / config ให้รัน:

```bash
./scripts/update-and-restart.sh
# หรือ pull จาก git ก่อน: ./scripts/update-and-restart.sh --pull
```

- **Frontend**: http://localhost:8080 (prod) หรือ http://localhost:5173 (dev)
- **API Docs**: http://localhost:8000/docs
- **Login เริ่มต้น**: admin / admin123 (ควรเปลี่ยนรหัสหลัง login ครั้งแรก)

## โครงสร้างโปรเจค

- `backend/` — FastAPI, MongoDB, LLM (Ollama)
- `frontend/` — React + Vite
- `docker-compose.yml` — development
- `docker-compose.prod.yml` — production
- `scripts/update-and-restart.sh` — อัปเดตและ restart Docker

## GitHub

- ใช้ `.gitignore` ที่รวมอยู่ — ไม่ commit `.env`, `mongo-data/`, `node_modules/`, `storage/` ฯลฯ
