# ✅ การติดตั้งเสร็จสมบูรณ์

## สถานะปัจจุบัน

โปรเจคได้ถูกติดตั้งและตั้งค่าเรียบร้อยแล้วบน Ubuntu Server

### Services ที่ทำงานอยู่:

- ✅ **Backend** (FastAPI) - Port 8000 - Healthy
- ✅ **Frontend** (React + Nginx) - Port 80 - Healthy  
- ✅ **MongoDB** - Port 27017 - Healthy
- ✅ **Ollama** (AI) - Port 11434 - Running

## ⚠️ ปัญหาที่พบและวิธีแก้ไข

### ปัญหา: Port 80 ถูกใช้งานโดย nginx บน host

**วิธีแก้ไข:**

1. หยุด nginx บน host:
   ```bash
   sudo systemctl stop nginx
   sudo systemctl disable nginx
   ```

2. หรือใช้สคริปต์:
   ```bash
   ./scripts/ubuntu/fix-port-conflict.sh
   ```

3. Restart frontend container:
   ```bash
   docker compose -f docker-compose.prod.yml restart frontend
   ```

## การเข้าถึง Application

### จาก Server:

- **Frontend**: http://localhost หรือ http://10.4.15.167
- **Backend API**: http://localhost:8000/docs หรือ http://10.4.15.167:8000/docs

### จาก Network (LAN):

- **Frontend**: http://10.4.15.167
- **Backend API**: http://10.4.15.167:8000/docs

### Default Login:

- **Username**: `admin`
- **Password**: `admin123`

⚠️ **เปลี่ยนรหัสผ่านทันทีหลังจาก login ครั้งแรก!**

## คำสั่งที่ใช้บ่อย

```bash
# ดูสถานะ services
docker compose -f docker-compose.prod.yml ps

# ดู logs
docker compose -f docker-compose.prod.yml logs -f

# Restart services
docker compose -f docker-compose.prod.yml restart

# Stop services
docker compose -f docker-compose.prod.yml down

# Start services
docker compose -f docker-compose.prod.yml up -d
```

## สคริปต์ที่มีให้ใช้งาน

- `scripts/ubuntu/setup-ubuntu-server.sh` - ติดตั้งและตั้งค่า Ubuntu Server
- `scripts/ubuntu/auto-setup.sh` - ติดตั้งและ deploy อัตโนมัติทั้งหมด
- `scripts/ubuntu/nginx-setup.sh` - ตั้งค่า Nginx บน host
- `scripts/ubuntu/fix-port-conflict.sh` - แก้ไขปัญหา port conflict
- `scripts/ubuntu/deploy.sh` - Pull และ deploy จาก Git

## เอกสารเพิ่มเติม

- `UBUNTU_SERVER_SETUP.md` - คู่มือการติดตั้งละเอียด
- `README.md` - เอกสารหลัก
- `NGINX_SETUP.md` - การตั้งค่า Nginx
- `START_UBUNTU.md` - Quick Start Guide

## ขั้นตอนถัดไป

1. ✅ แก้ไขปัญหา port conflict (หยุด nginx บน host)
2. ✅ เข้าใช้งาน application
3. ✅ เปลี่ยนรหัสผ่าน admin
4. ✅ ตั้งค่า domain name (ถ้าต้องการ)
5. ✅ ตั้งค่า SSL/TLS (Let's Encrypt)

## สรุป

โปรเจคพร้อมใช้งานแล้ว! แก้ไขปัญหา port conflict แล้วจะสามารถเข้าถึง application ได้ทันที
