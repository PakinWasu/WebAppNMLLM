# WebAppNMLLM - Network Project Management Platform

แพลตฟอร์มจัดการโปรเจคเครือข่าย (Network Project Management Platform) — ใช้ LLM (Ollama) สำหรับวิเคราะห์ config และสร้าง topology อัตโนมัติ

## 🚀 คุณสมบัติหลัก

- **🤖 AI-Powered Analysis**: วิเคราะห์ network configuration ด้วย LLM (Qwen2.5)
- **🌐 Topology Generation**: สร้าง network topology อัตโนมัติ
- **📁 Project Management**: จัดการโปรเจคเครือข่ายแบบมีระบบ
- **📄 Document Handling**: จัดการเอกสารและไฟล์ config
- **👥 User Management**: ระบบสมาชิกและสิทธิ์การใช้งาน
- **🔍 Config Analysis**: วิเคราะห์คอนฟิกกูเรชั่น Cisco และอื่นๆ

## 🏗️ สถาปัตยกรรมระบบ

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │     Database    │
│   (React)       │◄──►│   (FastAPI)     │◄──►│   (MongoDB)     │
│   Port: 8080    │    │   Port: 8001    │    │   Port: 27017   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   AI Engine     │
                       │   (Ollama)      │
                       │   Port: 11434   │
                       └─────────────────┘
```

## 📋 ความต้องการของระบบ

### ขั้นต่ำ (Minimum)
- **OS**: Ubuntu 20.04 LTS+ หรือ Linux ที่รองรับ Docker
- **RAM**: 8GB (แนะนำ 16GB+ สำหรับ LLM)
- **CPU**: 4+ cores
- **Storage**: 20GB+ พื้นที่ว่าง
- **Docker**: 20.10+ และ Docker Compose v2+

### แนะนำ (Recommended)
- **RAM**: 16GB+ สำหรับ LLM ขนาดใหญ่
- **CPU**: 8+ cores
- **GPU**: NVIDIA GPU (optional) สำหรับ LLM acceleration

## 🚀 การติดตั้ง

### บน Linux (แนะนำ)

📖 **ดูคู่มือการติดตั้งแบบละเอียด**: [INSTALL_LINUX.md](INSTALL_LINUX.md)

```bash
# 1. Clone repository
git clone <URL-REPO-ของคุณ>
cd WebAppNMLLM

# 2. รัน script ติดตั้งอัตโนมัติ
chmod +x scripts/install-linux.sh
./scripts/install-linux.sh

# 3. เข้าใช้งานระบบ
# Frontend: http://localhost:8080
# Username: admin, Password: admin123
```

### ด้วย Docker (ทุกระบบ)

```bash
# 1. สร้างไฟล์ .env สำหรับ backend
cp backend/.env.example backend/.env
# แก้ไฟล์ backend/.env ตามความต้องการ

# 2. รันด้วย Docker Compose
docker compose -f docker-compose.prod.yml up -d --build

# 3. ดาวน์โหลด LLM model
docker compose -f docker-compose.prod.yml exec ollama ollama pull qwen2.5:7b
```

## 📁 โครงสร้างโปรเจค

```
WebAppNMLLM/
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── core/             # Core settings และ security
│   │   ├── db/               # Database connection
│   │   ├── routers/          # API endpoints
│   │   └── services/         # Business logic
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                  # React Frontend
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── contexts/         # React contexts
│   │   └── hooks/            # Custom hooks
│   ├── Dockerfile.prod
│   └── package.json
├── scripts/                   # Utility scripts
│   ├── install-linux.sh      # Linux installation script
│   └── update-and-restart.sh # Update & restart script
├── storage/                   # File storage
├── docker-compose.yml         # Development
├── docker-compose.prod.yml    # Production
└── README.md
```

## ⚙️ การตั้งค่า

### Environment Variables (backend/.env)

```env
# MongoDB Configuration
MONGODB_URI=mongodb://mongodb:27017
MONGODB_DB_NAME=manage_network_projects

# JWT Security (สำคัญมาก!)
JWT_SECRET=<your-secure-random-secret-key>
JWT_ALG=HS256
ACCESS_TOKEN_EXPIRE_MIN=1440

# Ollama LLM Configuration
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_TIMEOUT=600
TOPOLOGY_USE_LLM=true
```

### การตั้งค่าที่สำคัญ

1. **JWT_SECRET**: ต้องเปลี่ยนเป็นค่าสุ่มที่ปลอดภัยใน production
2. **OLLAMA_MODEL**: เลือกโมเดลที่เหมาะกับ resource
   - `qwen2.5:7b` - เร็ว, ใช้ RAM ~4-6GB
   - `qwen2.5:14b` - คุณภาพดีกว่า, ใช้ RAM ~8-10GB
   - `qwen2.5:32b` - คุณภาพสูงสุด, ใช้ RAM ~16-20GB
3. **TOPOLOGY_USE_LLM**: เปิด/ปิดการใช้ LLM สำหรับสร้าง topology

## 🌐 การเข้าถึงระบบ

### Production URLs
- **Frontend**: http://localhost:8080
- **Backend API**: http://localhost:8001
- **API Documentation**: http://localhost:8001/docs
- **Ollama API**: http://localhost:11434

### Development URLs
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000

## 👤 การเข้าสู่ระบบ

**ค่าเริ่มต้น**:
- **Username**: admin
- **Password**: admin123

⚠️ **สำคัญ**: เปลี่ยนรหัสผ่านทันทีหลัง login ครั้งแรก!

## 🛠️ การจัดการระบบ

### คำสั่งที่ใช้บ่อย

```bash
# ดูสถานะ containers
docker compose -f docker-compose.prod.yml ps

# ดู logs
docker compose -f docker-compose.prod.yml logs -f

# Restart ระบบ
./scripts/update-and-restart.sh

# Update จาก git แล้ว restart
./scripts/update-and-restart.sh --pull

# Stop ระบบ
docker compose -f docker-compose.prod.yml down

# Start ระบบ
docker compose -f docker-compose.prod.yml up -d
```

### การจัดการ LLM Models

```bash
# ดู models ที่ติดตั้ง
docker compose -f docker-compose.prod.yml exec ollama ollama list

# ติดตั้ง model ใหม่
docker compose -f docker-compose.prod.yml exec ollama ollama pull <model-name>

# ลบ model
docker compose -f docker-compose.prod.yml exec ollama ollama rm <model-name>
```

## 📊 การ Monitor ระบบ

### Health Checks

```bash
# ตรวจสอบสถานะทั้งหมด
docker compose -f docker-compose.prod.yml ps

# ตรวจสอบ backend health
curl http://localhost:8001/

# ตรวจสอบ frontend health
curl http://localhost:8080/

# ตรวจสอบ Ollama
curl http://localhost:11434/api/tags
```

### Resource Usage

```bash
# ดู resource usage ของ containers
docker stats

# ดู disk usage
docker system df

# ดู logs ของ service ที่เฉพาะเจาะจง
docker compose -f docker-compose.prod.yml logs -f backend
```

## 🔧 การแก้ไขปัญหา

### ปัญหาที่พบบ่อย

1. **Ollama ใช้เวลานานในการดาวน์โหลดโมเดล**
   ```bash
   # เพิ่ม timeout ใน .env
   OLLAMA_TIMEOUT=1200
   ```

2. **MongoDB ไม่สามารถเชื่อมต่อได้**
   ```bash
   # ตรวจสอบ container
   docker compose -f docker-compose.prod.yml ps mongodb
   
   # ดู logs
   docker compose -f docker-compose.prod.yml logs mongodb
   ```

3. **Permission issues**
   ```bash
   # แก้ permission ของ storage
   sudo chmod -R 777 storage/
   ```

4. **Frontend ไม่โหลด**
   ```bash
   # ตรวจสอสอบ port
   netstat -tlnp | grep :8080
   
   # Restart frontend
   docker compose -f docker-compose.prod.yml restart frontend
   ```

## 📝 การ Backup และ Restore

### Backup MongoDB

```bash
# สร้าง backup
docker compose -f docker-compose.prod.yml exec mongodb mongodump --out /backup

# Copy ไฟล์ backup
docker cp mnp-mongo-prod:/backup ./mongo-backup-$(date +%Y%m%d)
```

### Restore MongoDB

```bash
# Copy ไฟล์ backup เข้า container
docker cp ./mongo-backup-20240301 mnp-mongo-prod:/backup

# Restore
docker compose -f docker-compose.prod.yml exec mongodb mongorestore /backup/20240301
```

## 🔒 ความปลอดภัย

### การตั้งค่าความปลอดภัย

1. **เปลี่ยน JWT_SECRET**: ใช้ค่าสุ่มที่ยาวอย่างน้อย 32 ตัวอักษร
2. **เปลี่ยนรหัสผ่าน admin**: ทันทีหลังการติดตั้ง
3. **จำกัดการเข้าถึง**: ใช้ firewall ถ้าจำเป็น
4. **Backup ข้อมูล**: สร้าง backup เป็นประจำ
5. **อัปเดตระบบ**: ตรวจสอบ updates เป็นประจำ

### SSL/TLS (Production)

สำหรับ production ควรตั้งค่า SSL/TLS:

```bash
# ใช้ nginx หรือ traefik เป็น reverse proxy
# ติดตั้ง SSL certificates
# ตั้งค่า HTTPS redirects
```

## 🤝 การพัฒนา

### Development Setup

```bash
# Backend development
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend development
cd frontend
npm install
npm run dev
```

### Contributing

1. Fork repository
2. สร้าง feature branch
3. Commit changes
4. Push to branch
5. สร้าง Pull Request

## 📄 License

[License Name] - [License Description]

## 📞 การติดต่อสนับสนุน

- **GitHub Issues**: [Repository Issues]
- **Documentation**: [Link to Documentation]
- **Email**: [Support Email]

---

## 🎯 Roadmap

- [ ] Multi-vendor device support
- [ ] Advanced topology algorithms
- [ ] Real-time collaboration
- [ ] Mobile app
- [ ] Cloud deployment options
- [ ] Advanced analytics dashboard

---

**ขอบคุณที่ใช้ WebAppNMLLM! 🚀**
