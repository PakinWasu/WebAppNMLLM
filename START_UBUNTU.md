# 🚀 เริ่มต้นใช้งานบน Ubuntu Server

คู่มือสั้นๆ สำหรับการติดตั้งและใช้งานโปรเจคบน Ubuntu Server

## ⚡ Quick Start (3 ขั้นตอน)

### 1. รันสคริปต์ Setup

```bash
chmod +x scripts/ubuntu/setup-ubuntu-server.sh
./scripts/ubuntu/setup-ubuntu-server.sh
```

สคริปต์จะทำการติดตั้งทุกอย่างให้อัตโนมัติ:
- ✅ Docker และ Docker Compose
- ✅ Nginx และ dependencies
- ✅ Firewall configuration
- ✅ Environment variables
- ✅ Required directories

### 2. Build และ Start Services

#### แบบที่ 1: ใช้ Nginx ใน Docker (แนะนำสำหรับเริ่มต้น)

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

#### แบบที่ 2: ใช้ Nginx บน Host (แนะนำสำหรับ Production)

```bash
# ตั้งค่า Nginx บน host
./scripts/ubuntu/nginx-setup.sh

# Build และ start
docker compose -f docker-compose.prod-nginx-host.yml up -d --build
```

### 3. เข้าใช้งาน

- **Frontend**: `http://<server-ip>`
- **Backend API**: `http://<server-ip>:8000/docs`
- **Login**: `admin` / `admin123`

⚠️ **เปลี่ยนรหัสผ่านทันทีหลังจาก login!**

## 📋 คำสั่งที่ใช้บ่อย

```bash
# ดูสถานะ
docker compose -f docker-compose.prod.yml ps

# ดู logs
docker compose -f docker-compose.prod.yml logs -f

# Restart
docker compose -f docker-compose.prod.yml restart

# Stop
docker compose -f docker-compose.prod.yml down

# Update
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

## 🔧 การแก้ไขปัญหา

### ไม่สามารถเข้าถึง Frontend

```bash
# ตรวจสอบ containers
docker ps

# ตรวจสอบ firewall
sudo ufw status
sudo ufw allow 80/tcp

# ทดสอบจาก server
curl http://localhost
```

### Nginx ไม่ทำงาน (แบบที่ 2)

```bash
# ตรวจสอบสถานะ
sudo systemctl status nginx

# ตรวจสอบ config
sudo nginx -t

# Reload
sudo systemctl reload nginx
```

## 📚 เอกสารเพิ่มเติม

- **[UBUNTU_SERVER_SETUP.md](UBUNTU_SERVER_SETUP.md)** - คู่มือละเอียด
- **[README.md](README.md)** - เอกสารหลัก
- **[NGINX_SETUP.md](NGINX_SETUP.md)** - การตั้งค่า Nginx

## 🆘 ต้องการความช่วยเหลือ?

ตรวจสอบ logs:
```bash
docker compose -f docker-compose.prod.yml logs
```

หรือดูเอกสารเพิ่มเติมใน `UBUNTU_SERVER_SETUP.md`
