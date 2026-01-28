# Network Project Platform

แพลตฟอร์มจัดการโปรเจคเครือข่าย (Network Project Management Platform)

> **Last Updated**: 2026-01-28  
> **Version**: 0.1.0  
> **Status**: ✅ Production Ready

## 📋 สารบัญ

- [คุณสมบัติ](#คุณสมบัติ)
- [ความต้องการของระบบ](#ความต้องการของระบบ)
- [การติดตั้งบน Ubuntu Server](#การติดตั้งบน-ubuntu-server)
- [การใช้งาน Development](#การใช้งาน-development)
- [การใช้งาน Production](#การใช้งาน-production)
- [การ Backup และ Restore](#การ-backup-และ-restore)
- [การแก้ไขปัญหา](#การแก้ไขปัญหา)
- [เอกสารเพิ่มเติม](#เอกสารเพิ่มเติม)

## 📚 เอกสารเพิ่มเติม

### สำหรับการพัฒนา

- **[WINDOWS_DEVELOPMENT.md](WINDOWS_DEVELOPMENT.md)** - คู่มือการพัฒนาโปรเจคบน Windows PC
- **[GITHUB_WORKFLOW.md](GITHUB_WORKFLOW.md)** - Workflow การทำงานผ่าน GitHub (Windows ↔ Ubuntu Server)
- **[QUICK_START.md](QUICK_START.md)** - Quick Start Guide
- **[CHANGELOG.md](CHANGELOG.md)** - 📝 ประวัติการเปลี่ยนแปลงและ Bug Fixes

### สำหรับการ Deploy

- **[UBUNTU_SERVER_SETUP.md](UBUNTU_SERVER_SETUP.md)** - ⭐ คู่มือการติดตั้งบน Ubuntu Server (แนะนำ)
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - ⭐ คู่มือการ Deploy แบบละเอียด
- **[NGINX_SETUP.md](NGINX_SETUP.md)** - การตั้งค่า Nginx
- **[DOMAIN_SETUP.md](DOMAIN_SETUP.md)** - การตั้งค่า Domain Name
- **[STORAGE_FIX.md](STORAGE_FIX.md)** - การแก้ไขปัญหา Storage
- **[MONGODB_4.4_COMPATIBILITY.md](MONGODB_4.4_COMPATIBILITY.md)** - MongoDB Compatibility

### Scripts

- **Windows**: `scripts/windows/` - PowerShell scripts สำหรับ Windows
  - `setup-windows.ps1` - ⭐ ติดตั้งและตั้งค่า Windows PC
  - `dev-start.ps1` - เริ่ม development environment
  - `update-and-push.ps1` - ⭐ Pull, commit, และ push ไป GitHub
  - `git-push.ps1` - Push โค้ดไป GitHub
- **Ubuntu**: `scripts/ubuntu/` - Bash scripts สำหรับ Ubuntu Server
  - `setup-ubuntu-server.sh` - ⭐ สคริปต์ติดตั้งและตั้งค่า Ubuntu Server (แนะนำ)
  - `deploy.sh` - ⭐ Pull และ deploy บน Ubuntu Server
  - `complete-fix.sh` - แก้ไขปัญหาและตั้งค่า nginx
  - `nginx-setup.sh` - สคริปต์ตั้งค่า Nginx บน host

## ✨ คุณสมบัติ

- 🔐 ระบบ Authentication และ Authorization แบบ JWT
- 👥 จัดการผู้ใช้ (User Management)
- 📁 จัดการโปรเจค (Project Management)
- 📄 อัปโหลดและจัดการไฟล์ Configuration
- 🔍 Configuration Parser อัตโนมัติ (Huawei VRP, Cisco IOS)
- 📊 Summary Table แสดงสรุปข้อมูลอุปกรณ์
- 🔎 Device Details View (Overview, Interfaces, VLANs, STP, Routing, etc.)
- 💾 Download ไฟล์ Original Content และ Parsed JSON
- 🌓 Dark/Light Mode Toggle
- 🤖 AI Integration (Ollama)
- 🚀 Production-ready Docker configuration

## 🛠️ ความต้องการของระบบ

### สำหรับ Production (Ubuntu Server)

- **Ubuntu 20.04 LTS หรือใหม่กว่า**
- **Docker** 20.10+
- **Docker Compose** 2.0+
- **RAM**: อย่างน้อย 4GB (แนะนำ 8GB+)
- **Disk Space**: อย่างน้อย 20GB
- **GPU** (optional): สำหรับ Ollama AI features

### สำหรับ Development

- **Docker** และ **Docker Compose**
- หรือ:
  - **Node.js** 20+ (สำหรับ Frontend)
  - **Python** 3.11+ (สำหรับ Backend)
  - **MongoDB** 6.0+

## 🚀 การติดตั้งบน Ubuntu Server

> ⭐ **แนะนำ**: ใช้สคริปต์อัตโนมัติ `scripts/ubuntu/setup-ubuntu-server.sh` สำหรับการติดตั้งที่ง่ายและรวดเร็ว
> 
> ดูรายละเอียดเพิ่มเติมที่: **[UBUNTU_SERVER_SETUP.md](UBUNTU_SERVER_SETUP.md)**

### 1. ติดตั้ง Docker และ Docker Compose

```bash
# อัปเดตระบบ
sudo apt update && sudo apt upgrade -y

# ติดตั้ง Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# เพิ่ม user เข้า docker group (ไม่ต้องใช้ sudo)
sudo usermod -aG docker $USER
newgrp docker

# ติดตั้ง Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# ตรวจสอบการติดตั้ง
docker --version
docker-compose --version
```

### 2. Clone หรืออัปโหลดโปรเจค

```bash
# ถ้าใช้ Git
git clone <repository-url>
cd manage-network-project

# หรืออัปโหลดไฟล์ผ่าน SCP/SFTP
```

### 3. ตั้งค่า Environment Variables

สร้างไฟล์ `.env` ในโฟลเดอร์ `backend/`:

```bash
cd backend
nano .env
```

เนื้อหาที่ต้องตั้งค่า:

```env
# MongoDB
MONGODB_URI=mongodb://mongodb:27017
MONGODB_DB_NAME=manage_network_projects

# JWT Security (⚠️ เปลี่ยนเป็นค่าที่ปลอดภัย!)
JWT_SECRET=your-very-secure-random-secret-key-minimum-32-characters
JWT_ALG=HS256
ACCESS_TOKEN_EXPIRE_MIN=1440

# AI Model (Ollama)
AI_MODEL_NAME=qwen2.5:7b
AI_MODEL_VERSION=v1-desktop
AI_MODEL_ENDPOINT=http://host.docker.internal:11434
```

**⚠️ สำคัญ**: เปลี่ยน `JWT_SECRET` เป็นค่าที่ปลอดภัยและยาวพอ (อย่างน้อย 32 ตัวอักษร)

สร้าง secret key:
```bash
openssl rand -hex 32
```

### 4. Build และรัน Production

```bash
# Build และ start services
docker-compose -f docker-compose.prod.yml up -d --build

# ตรวจสอบสถานะ
docker-compose -f docker-compose.prod.yml ps

# ดู logs
docker-compose -f docker-compose.prod.yml logs -f
```

### 5. ตั้งค่า Firewall (ถ้าจำเป็น)

```bash
# อนุญาต HTTP (port 80)
sudo ufw allow 80/tcp

# อนุญาต HTTPS (port 443) - สำหรับ SSL ในอนาคต
sudo ufw allow 443/tcp

# อนุญาต SSH (port 22)
sudo ufw allow 22/tcp

# เปิดใช้งาน firewall
sudo ufw enable
```

### 6. ตั้งค่า Reverse Proxy (แนะนำ - สำหรับ SSL)

ติดตั้ง Nginx เป็น reverse proxy:

```bash
sudo apt install nginx -y
```

สร้างไฟล์ config `/etc/nginx/sites-available/mnp`:

```nginx
server {
    listen 80;
    server_name your-domain.com;  # เปลี่ยนเป็น domain ของคุณ

    location / {
        proxy_pass http://localhost:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/mnp /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 7. ตั้งค่า SSL ด้วย Let's Encrypt (แนะนำ)

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

### 8. เข้าใช้งาน

- **Frontend**: http://your-server-ip หรือ http://your-domain.com
- **Backend API**: http://your-server-ip:8000
- **API Docs**: http://your-server-ip:8000/docs

### ข้อมูล Login เริ่มต้น

- **Username**: `admin`
- **Password**: `admin123`

⚠️ **เปลี่ยนรหัสผ่านทันทีหลังจาก login ครั้งแรก!**

## 💻 การใช้งาน Development

### รัน Development Mode

```bash
# Start services
docker-compose up -d

# หรือดู logs แบบ real-time
docker-compose up
```

### Rebuild เมื่อมีการเปลี่ยนแปลง

```bash
# Rebuild frontend (เมื่อเพิ่ม dependencies)
docker-compose build frontend
docker-compose up -d frontend

# Rebuild backend
docker-compose build backend
docker-compose up -d backend

# Rebuild ทั้งหมด
docker-compose build
docker-compose up -d
```

## 🔄 การใช้งาน Production

### Start/Stop Services

```bash
# Start
docker-compose -f docker-compose.prod.yml up -d

# Stop
docker-compose -f docker-compose.prod.yml down

# Restart
docker-compose -f docker-compose.prod.yml restart

# View logs
docker-compose -f docker-compose.prod.yml logs -f [service-name]
```

### Update Application

```bash
# Pull latest code
git pull

# Rebuild และ restart
docker-compose -f docker-compose.prod.yml up -d --build

# หรือ rebuild เฉพาะ service
docker-compose -f docker-compose.prod.yml build frontend
docker-compose -f docker-compose.prod.yml up -d frontend
```

## 💾 การ Backup และ Restore

### Backup MongoDB

```bash
# สร้าง backup
docker exec mnp-mongo-prod mongodump --out /backup/$(date +%Y%m%d_%H%M%S)

# หรือ backup จาก host
docker exec mnp-mongo-prod mongodump --archive=/backup/backup-$(date +%Y%m%d).archive
docker cp mnp-mongo-prod:/backup/backup-$(date +%Y%m%d).archive ./backup-$(date +%Y%m%d).archive
```

### Restore MongoDB

```bash
# Restore จาก archive
docker cp ./backup-YYYYMMDD.archive mnp-mongo-prod:/backup/restore.archive
docker exec mnp-mongo-prod mongorestore --archive=/backup/restore.archive
```

### Backup Script (แนะนำ)

สร้างไฟล์ `backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup MongoDB
docker exec mnp-mongo-prod mongodump --archive=/backup/mongo-$DATE.archive
docker cp mnp-mongo-prod:/backup/mongo-$DATE.archive $BACKUP_DIR/

# Backup volumes (ถ้ามี)
docker run --rm -v manage-network-project_mongo-data:/data -v $(pwd)/$BACKUP_DIR:/backup alpine tar czf /backup/mongo-data-$DATE.tar.gz /data

# ลบ backup เก่ากว่า 7 วัน
find $BACKUP_DIR -name "*.archive" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
```

ตั้งค่าให้รันอัตโนมัติด้วย cron:

```bash
# แก้ไข crontab
crontab -e

# เพิ่มบรรทัดนี้เพื่อ backup ทุกวันเวลา 2:00 AM
0 2 * * * /path/to/manage-network-project/backup.sh
```

## 🔧 การแก้ไขปัญหา

### ตรวจสอบสถานะ Services

```bash
# ดูสถานะ containers
docker-compose -f docker-compose.prod.yml ps

# ดู logs
docker-compose -f docker-compose.prod.yml logs -f

# ดู logs ของ service เฉพาะ
docker-compose -f docker-compose.prod.yml logs -f frontend
docker-compose -f docker-compose.prod.yml logs -f backend
```

### Frontend ไม่แสดงผล

```bash
# ตรวจสอบว่า frontend container ทำงาน
docker ps | grep frontend

# ตรวจสอบ logs
docker logs mnp-frontend-prod

# Rebuild frontend
docker-compose -f docker-compose.prod.yml build frontend
docker-compose -f docker-compose.prod.yml up -d frontend
```

### Backend ไม่ทำงาน

```bash
# ตรวจสอบ logs
docker logs mnp-backend-prod

# ตรวจสอบ MongoDB connection
docker exec mnp-mongo-prod mongo --eval "db.runCommand('ping')"

# ตรวจสอบ environment variables
docker exec mnp-backend-prod env | grep -E "MONGODB|JWT"
```

### MongoDB Connection Error

```bash
# ตรวจสอบว่า MongoDB container healthy
docker ps | grep mongo

# ตรวจสอบ logs
docker logs mnp-mongo-prod

# Restart MongoDB
docker-compose -f docker-compose.prod.yml restart mongodb
```

### Port ถูกใช้งานแล้ว

```bash
# ตรวจสอบ port ที่ใช้งาน
sudo netstat -tulpn | grep :80
sudo netstat -tulpn | grep :8000

# เปลี่ยน port ใน docker-compose.prod.yml
# หรือหยุด service ที่ใช้ port นั้น
```

### Disk Space เต็ม

```bash
# ตรวจสอบ disk usage
df -h

# ลบ unused Docker resources
docker system prune -a

# ลบ old images
docker image prune -a

# ลบ old backups
find ./backups -name "*.archive" -mtime +30 -delete
```

### Performance Issues

```bash
# ตรวจสอบ resource usage
docker stats

# จำกัด memory สำหรับ containers (แก้ไขใน docker-compose.prod.yml)
# เพิ่ม:
#   deploy:
#     resources:
#       limits:
#         memory: 512M
```

## 📁 โครงสร้างโปรเจค

```
WebAppNMLLM/
├── backend/                 # FastAPI Backend
│   ├── app/
│   │   ├── core/           # Core settings, security
│   │   ├── db/             # Database connection
│   │   ├── routers/        # API routes
│   │   ├── services/       # Business logic
│   │   │   ├── parsers/    # Configuration parsers
│   │   │   │   ├── huawei.py  # Huawei VRP parser (Dictionary-based, Strict mode)
│   │   │   │   ├── cisco.py   # Cisco IOS parser
│   │   │   │   └── base.py    # Base parser class
│   │   │   ├── config_parser.py  # Main parser service
│   │   │   └── document_storage.py
│   │   └── main.py         # FastAPI app
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── scripts/            # Utility scripts
│   │   ├── test_parser.py
│   │   └── check_parsed_data.py
│   └── .env                # Environment variables
│
├── frontend/               # React + Vite Frontend
│   ├── src/
│   │   ├── App.jsx         # Main React component (with Download buttons)
│   │   ├── api.js          # API client
│   │   ├── index.css       # Global styles + Tailwind
│   │   └── main.jsx        # React entry point
│   ├── Dockerfile          # Development
│   ├── Dockerfile.prod     # Production (Nginx)
│   ├── nginx.conf          # Nginx configuration
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.js
│
├── scripts/                # Deployment scripts
│   ├── windows/            # PowerShell scripts
│   └── ubuntu/             # Bash scripts
│
├── mongo-data/            # MongoDB data (persistent)
├── mongo-backup/          # MongoDB backups
├── storage/               # Application storage
├── docker-compose.yml     # Development
├── docker-compose.prod.yml # Production
└── README.md             # This file
```

## 🔌 API Endpoints

ดูรายละเอียด API ทั้งหมดได้ที่: `http://your-server:8000/docs` (Swagger UI)

### Authentication
- `POST /auth/login` - Login
- `GET /auth/me` - Get current user
- `POST /auth/change-password` - Change password

### Users (Admin only)
- `GET /users` - List users
- `POST /users` - Create user
- `PUT /users/{username}` - Update user
- `DELETE /users/{username}` - Delete user

### Projects
- `GET /projects` - List projects
- `POST /projects` - Create project
- `GET /projects/{id}` - Get project
- `PUT /projects/{id}` - Update project
- `DELETE /projects/{id}` - Delete project

### Documents
- `POST /projects/{id}/documents` - Upload documents (triggers parser if folder="Config")
- `GET /projects/{id}/documents` - List documents
- `GET /projects/{id}/documents/{doc_id}` - Get document
- `DELETE /projects/{id}/documents/{doc_id}` - Delete document

### Summary
- `GET /projects/{id}/summary` - Get summary table (all devices)
- `GET /projects/{id}/summary/{device_name}` - Get device details

## 🔒 Security Best Practices

1. **เปลี่ยน JWT_SECRET** เป็นค่าที่ปลอดภัยและยาวพอ
2. **ใช้ HTTPS** ใน production (Let's Encrypt)
3. **ตั้งค่า Firewall** ให้อนุญาตเฉพาะ port ที่จำเป็น
4. **Backup ข้อมูล** เป็นประจำ
5. **อัปเดตระบบ** และ dependencies เป็นประจำ
6. **เปลี่ยนรหัสผ่าน admin** หลังจากติดตั้ง
7. **จำกัด access** ต่อ MongoDB port (27017) ให้เฉพาะ internal network

## 📝 Maintenance

### อัปเดต Dependencies

```bash
# Frontend
cd frontend
npm update
docker-compose -f docker-compose.prod.yml build frontend

# Backend
cd backend
pip list --outdated
# แก้ไข requirements.txt แล้ว rebuild
docker-compose -f docker-compose.prod.yml build backend
```

### Monitoring

แนะนำให้ใช้ monitoring tools เช่น:
- **Prometheus + Grafana** สำหรับ metrics
- **ELK Stack** สำหรับ logs
- **Uptime Kuma** สำหรับ uptime monitoring

## 📞 Support

สำหรับปัญหาหรือคำถามเพิ่มเติม กรุณาติดต่อทีมพัฒนา

## 📄 License

[ระบุ license ตามต้องการ]
